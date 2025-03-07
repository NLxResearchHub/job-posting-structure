import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from hashlib import sha256

import boto3
import duckdb
import pandas as pd
import pyarrow as pa
from pydantic import ValidationError

from jobstruct.prompts import Prompts
from schemas import ExtractSchema, SkillsSchema, ExtractBreakoutSchema

########################################
# CONFIGURATION / CONSTANTS
########################################

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

# Local directory with job Parquet files
JOBS_PARQUET_DIR = "/data/nlx/job"

# Maximum concurrent batches to schedule
MAX_CONCURRENT_JOBS = 2

# Batch size for each Bedrock submission
BATCH_SIZE = 1000

# Maximum number of times to retry a failed batch
MAX_RETRIES = 1

# How many days back from "today" to begin processing
DEFAULT_LOOKBACK_DAYS = 40

# SKILLS TAXONOMY
with open("skills_taxonomy.md", "r") as file:
    SKILLS_TAXONOMY = file.read()

# GLOBAL DAY-BY-DAY STATE
_DAY_STATE = {"current_day": None}

# SET EDUCATION PARSING TYPE
EDUCATION_TYPE = 'Breakout'
#Bundled

# Model Selections
EXTRACT_MODEL_ID = "anthropic.claude-3-5-haiku-20241022-v1:0"
# 
# "anthropic.claude-3-haiku-20240307-v1:0"
# "anthropic.claude-3-5-sonnet-20240620-v1:0"
SKILLS_MODEL_ID = "amazon.nova-pro-v1:0"
# "amazon.nova-pro-v1:0"
# "anthropic.claude-3-5-sonnet-20240620-v1:0"

if "3-5-haiku" in EXTRACT_MODEL_ID:
    # AWS clients
    bedrock_client = boto3.client("bedrock",
                                 region_name='us-west-2')
    s3_client = boto3.client("s3",
                            region_name='us-west-2')
    # Bedrock output bucket (S3)
    INPUT_BUCKET = "nlx-job-description-parsing-inputs-west-2"
    OUTPUT_BUCKET = "nlx-job-description-parsing-outputs-west-2"
else:
    # AWS clients
    bedrock_client = boto3.client("bedrock",
                                 region_name='us-east-1')
    s3_client = boto3.client("s3",
                            region_name='us-east-1')
    # Bedrock output bucket (S3)
    INPUT_BUCKET = "nlx-job-description-parsing-inputs"
    OUTPUT_BUCKET = "nlx-job-description-parsing-outputs"

# Maximum number of skills to include in the skills parser output
MAX_SKILLS_ITEMS = 25
    
# Precompute the machine-readable JSON schemas
extract_schema_json = json.dumps(ExtractSchema.model_json_schema(), indent=2)
extract_breakout_schema_json = json.dumps(ExtractBreakoutSchema.model_json_schema(), indent=2)
skills_schema_json = json.dumps(SkillsSchema.model_json_schema(), indent=2)

########################################
# DUCKDB SETUP / HELPER FUNCTIONS
########################################

def init_duckdb(db_path: str = ":memory:") -> duckdb.DuckDBPyConnection:
    """
    Initialize a DuckDB connection and ensure the job_extract table exists.
    Also create a 'batch_status' table to track batch job errors/retries if needed.
    """
    con = duckdb.connect(db_path)


    if EDUCATION_TYPE == 'Breakout':
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS job_extract (
                job_id INT NOT NULL,
                job_description_hash TEXT NOT NULL,
                job_title TEXT ,
                details TEXT,
                high_school_diploma_or_equivalent TEXT,
                vocational_or_technical_degree TEXT,
                associates_or_2_year_degree TEXT,
                bachelors_or_four_year_degree TEXT,
                masters_degree TEXT,
                doctoral_degree_including_jd_md TEXT,
                required_preferred_major TEXT,
                required_preferred_experience SMALLINT,
                required_preferred_qualifications TEXT,
                benefits TEXT,
                pay_min DECIMAL(10, 2),
                pay_max DECIMAL(10, 2),
                pay_unit TEXT,
                entry_level_up_to_3_years_experience TEXT,
                part_time TEXT,
                remote TEXT,
                soc_occupation_code TEXT,
                skills TEXT[],
                extract_at TIMESTAMP,
                skills_at TIMESTAMP
            );
            """
        )


    else:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS job_extract (
                job_id INT NOT NULL,
                job_description_hash TEXT NOT NULL,
                job_title TEXT ,
                details TEXT,
                required_education TEXT,
                required_major TEXT,
                required_experience SMALLINT,
                required_qualifications TEXT,
                preferred_education TEXT,
                preferred_major TEXT,
                preferred_experience SMALLINT,
                preferred_qualifications TEXT,
                benefits TEXT,
                pay_min DECIMAL(10, 2),
                pay_max DECIMAL(10, 2),
                pay_unit TEXT,
                entry_level TEXT,
                part_time TEXT,
                remote TEXT,
                soc_occupation_code TEXT,
                skills TEXT[],
                extract_at TIMESTAMP,
                skills_at TIMESTAMP
            );
            """
        )

    con.execute(
        """
        CREATE TABLE IF NOT EXISTS batch_status (
            batch_name TEXT PRIMARY KEY,
            job_arn TEXT,
            prompt_type TEXT,
            status TEXT,
            retry_count INT,
            last_error TEXT
        );
        """
    )
    return con


def insert_job_hash_mapping(con: duckdb.DuckDBPyConnection, df: pd.DataFrame) -> None:
    """
    Insert the job_id + job_description_hash mapping (and empty placeholders for title, details)
    into job_extract if not already present. This ensures we have a firm job_id-hash link prior
    to Amazon Bedrock processing.
    """
    if df.empty:
        return

    # We'll insert minimal placeholders for `title` and `details` since the schema requires NOT NULL
    # The rest can remain NULL or default.
    mini_df = df[["job_id", "job_description_hash"]].copy()

    arrow_table = pa.Table.from_pandas(mini_df)

    con.execute("CREATE TEMP TABLE _hash_mapping_stage AS SELECT * FROM arrow_table;")

    # Insert only if it doesn't exist
    con.execute("""
        INSERT INTO job_extract (
            job_id, job_description_hash
        )
        SELECT s.job_id, s.job_description_hash
        FROM _hash_mapping_stage s
        WHERE NOT EXISTS (
            SELECT 1 FROM job_extract t
            WHERE t.job_id = s.job_id AND t.job_description_hash = s.job_description_hash
        );
    """)

    con.execute("DROP TABLE _hash_mapping_stage;")


def validate_and_prepare_for_decimal(dataframe: pd.DataFrame, columns: list) -> pd.DataFrame:
    """
    Ensures the values in the specified columns of the DataFrame fit within DECIMAL(10,2).

    Parameters:
    - dataframe: The Pandas DataFrame to process.
    - columns: A list of column names to validate and transform.

    Returns:
    - A DataFrame with the specified columns validated and rounded.
    """
    # Define the range limits for DECIMAL(10,2)
    min_value = 0.00
    max_value = 99999999.99

    # Process each column in the list
    for column in columns:
        if column in dataframe.columns:
            # Clip values to fit within range
            dataframe[column] = dataframe[column].clip(lower=min_value, upper=max_value)

            # Round to two decimal places
            dataframe[column] = dataframe[column].round(2)
        else:
            raise ValueError(f"Column '{column}' does not exist in the DataFrame.")

    return dataframe

def convert_to_integers_with_range(dataframe: pd.DataFrame, columns: list, min_value: int = 0, max_value: int = 30) -> pd.DataFrame:
    """
    Converts all non-null values in the specified columns of a DataFrame to integers,
    and replaces values outside the specified range with None.

    Parameters:
    - dataframe: The Pandas DataFrame to process.
    - columns: A list of column names to validate and transform.
    - min_value: Minimum acceptable integer value. Values below this will be set to None.
    - max_value: Maximum acceptable integer value. Values above this will be set to None.

    Returns:
    - A DataFrame with the specified columns' non-null values converted to integers,
      and out-of-range values replaced with None.
    """
    for column in columns:
        if column in dataframe.columns:
            # Process each column
            dataframe[column] = dataframe[column].apply(
                lambda x: int(x) if pd.notnull(x) and min_value <= x <= max_value else None
            )
        else:
            raise ValueError(f"Column '{column}' does not exist in the DataFrame.")
    return dataframe
    
def duckdb_upsert_extract(
    con: duckdb.DuckDBPyConnection, 
    rows: list[dict], 
    now_ts: str
) -> None:
    """
    Upsert the 'extract' prompt data into job_extract table.
    Sets extract_at = now_ts for updated or inserted records.
    """
    if not rows:
        return
    df = pd.DataFrame(rows)
    df["extract_at"] = now_ts
    df = validate_and_prepare_for_decimal(df, ["pay_max","pay_min"])
    
    if EDUCATION_TYPE == 'Breakout':
        df = convert_to_integers_with_range(df, ["required_preferred_experience"])
    else:
        df = convert_to_integers_with_range(df, ["required_experience","preferred_experience"])
        
    arrow_table = pa.Table.from_pandas(df)

    con.execute("CREATE TEMP TABLE _extract_stage AS SELECT * FROM arrow_table;")


    if EDUCATION_TYPE == 'Breakout':
        # Update existing records
        con.execute("""
            UPDATE job_extract t
            SET 
                job_title = s.job_title,
                details = s.details,
                high_school_diploma_or_equivalent = s.high_school_diploma_or_equivalent,
                vocational_or_technical_degree = s.vocational_or_technical_degree,
                associates_or_2_year_degree = s.associates_or_2_year_degree,
                bachelors_or_four_year_degree = s.bachelors_or_four_year_degree,
                masters_degree = s.masters_degree,
                doctoral_degree_including_jd_md = s.doctoral_degree_including_jd_md,
                required_preferred_major = s.required_preferred_major,
                required_preferred_experience = s.required_preferred_experience,
                required_preferred_qualifications = s.required_preferred_qualifications,
                benefits = s.benefits,
                pay_min = s.pay_min,
                pay_max = s.pay_max,
                pay_unit = s.pay_unit,
                entry_level_up_to_3_years_experience = s.entry_level_up_to_3_years_experience,
                part_time = s.part_time,
                remote = s.remote,
                soc_occupation_code = s.soc_occupation_code,
                extract_at = s.extract_at
            FROM _extract_stage s
            WHERE t.job_description_hash = s.job_description_hash;
        """)

    else:
        # Update existing records
        con.execute("""
            UPDATE job_extract t
            SET 
                job_title = s.job_title,
                details = s.details,
                required_education = s.required_education,
                required_major = s.required_major,
                required_experience = s.required_experience,
                required_qualifications = s.required_qualifications,
                preferred_education = s.preferred_education,
                preferred_major = s.preferred_major,
                preferred_experience = s.preferred_experience,
                preferred_qualifications = s.preferred_qualifications,
                benefits = s.benefits,
                pay_min = s.pay_min,
                pay_max = s.pay_max,
                pay_unit = s.pay_unit,
                entry_level = s.entry_level,
                part_time = s.part_time,
                remote = s.remote,
                soc_occupation_code = s.soc_occupation_code,
                extract_at = s.extract_at
            FROM _extract_stage s
            WHERE t.job_description_hash = s.job_description_hash;
        """)

    con.execute("DROP TABLE _extract_stage;")


def duckdb_upsert_skills(
    con: duckdb.DuckDBPyConnection, 
    rows: list[dict], 
    now_ts: str
) -> None:
    """
    For each parsed record from the 'skills' prompt, update the "skills" array
    and set skills_at = now_ts. If the row doesn't exist, create a minimal entry.
    """
    
    if not rows:
        return
    df = pd.DataFrame(rows)
    df["skills_at"] = now_ts
    arrow_table = pa.Table.from_pandas(df)

    con.execute("CREATE TEMP TABLE _skills_stage AS SELECT * FROM arrow_table;")

    # Update existing records
    con.execute("""
        UPDATE job_extract t
        SET 
            skills = s.skills,
            skills_at = s.skills_at
        FROM _skills_stage s
        WHERE t.job_description_hash = s.job_description_hash;
    """)

    con.execute("DROP TABLE _skills_stage;")

########################################
# QUERY JOBS TABLE TO GET JOBS TO PROCESS
########################################

def get_jobs_to_process(
    con: duckdb.DuckDBPyConnection,
    prompt_type: str,
    start_date: datetime,
    limit: int = BATCH_SIZE
) -> pd.DataFrame:
    """
    Day-by-day approach:
      1) On the first call, find the max date_compiled >= start_date
      2) Repeatedly query that day for unprocessed jobs
      3) Insert job_id + job_description_hash mapping into job_extract prior to returning
      4) Return up to limit
    """
    global _DAY_STATE
    
    # Create or replace 'jobs' from the local Parquet
    con.execute(f"""
        CREATE OR REPLACE TABLE jobs AS 
        SELECT * 
        FROM READ_PARQUET('{JOBS_PARQUET_DIR}/unredacted__job__2024-12.parquet');
    """)

    # If we haven't initialized current_day, find the max date_compiled >= start_date
    if _DAY_STATE["current_day"] is None:
        con.execute(f"""
            SELECT max(date_compiled::date)
            FROM jobs
            WHERE date_compiled >= '{start_date.strftime('%Y-%m-%d')}'
        """)
        max_day = con.fetchone()[0]
        if not max_day:
            # No data at all in that range
            return pd.DataFrame(columns=["job_id","description","date_compiled","job_description_hash"])
        _DAY_STATE["current_day"] = max_day

    # We'll keep trying until we find some unprocessed for the current day, or go below start_date
    while True:
        current_day = _DAY_STATE["current_day"]
        if current_day < start_date.date():
            return pd.DataFrame(columns=["job_id","description","date_compiled","job_description_hash"])

        # Pull all jobs from that day
        con.execute(f"""
            SELECT *
            FROM jobs
            WHERE date_compiled::date = '{current_day}'
            ORDER BY date_compiled DESC
        """)
        df = con.fetch_df()

        if "description" not in df.columns:
            df["description"] = ""

        # Create job_description_hash
        df["job_description_hash"] = df["description"].apply(
            lambda x: sha256(x.encode("utf8")).hexdigest() if x else ""
        )

        # Exclude already processed
        if prompt_type == "extract":
            con.execute("SELECT job_description_hash FROM job_extract WHERE extract_at IS NOT NULL")
        else:
            con.execute("SELECT job_description_hash FROM job_extract WHERE skills_at IS NOT NULL")

        skip_hashes = {r[0] for r in con.fetchall()}
        df = df.loc[~df["job_description_hash"].isin(skip_hashes)].copy()

        if df.empty:
            # No unprocessed records remain for this day -> move to previous day
            _DAY_STATE["current_day"] = current_day - timedelta(days=1)
            continue
        else:
            # FIRST: Insert the job_id + job_description_hash mapping so we have the record in job_extract
            insert_job_hash_mapping(con, df)

            # Return up to limit
            return df.head(limit)


########################################
# BEDROCK & BATCH JOB LOGIC
########################################

def create_jsonl_for_prompt(
    df: pd.DataFrame, 
    output_file: str, 
    prompt_type: str, 
    model_id: str,
    skill_list: str = SKILLS_TAXONOMY,
    
):
    """
    Create JSONL file with the selected prompt (extract or skills),
    referencing Pydantic-based schemas in the prompt text.
    """
    logger.info(f"Creating JSONL for prompt: {prompt_type} -> {output_file}")

    if prompt_type == "extract":
        if EDUCATION_TYPE == 'Breakout':
            schema_str = extract_breakout_schema_json
        else:
            schema_str = extract_schema_json
            
        base_prompt = Prompts.extract
        system_text = (
            "You are an expert in job description analysis and data extraction. "
            "You must produce valid JSON that EXACTLY follows the provided JSON Schema, including field descriptions."
        )
    else:
        schema_str = skills_schema_json
        base_prompt = Prompts.skills
        system_text = (
            "You are an expert in job description skill mapping."
            "You must produce valid JSON that EXACTLY follows the provided JSON Schema. "
        )

    with open(output_file, "w", encoding="utf-8") as fout:
        for _, row in df.iterrows():
            prompt_body = base_prompt.format(
                text=row["description"],
                skills=skill_list,
                schema_json=schema_str
            )

            anthropic_model_input = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4096,
                "temperature": 0.0,
                "top_k": 250,
                "top_p": 0.9,
                "system": system_text,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt_body
                            }
                        ]
                    }
                ]
            }

            amazon_model_input = model_input = {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "text": system_text + "\n\n" + prompt_body
                            }
                        ]
                    }
                ],
                "inferenceConfig": {
                    "max_new_tokens": 4096,
                    "temperature": 0.0,
                    "top_p": 0.9,
                    "top_k": 250
                }
            }

            if 'anthropic' in model_id:
                model_input = anthropic_model_input
            elif 'amazon' in model_id:
                model_input = amazon_model_input

            record = {
                "recordId": row["job_description_hash"],
                "modelInput": model_input
            }
            fout.write(json.dumps(record) + "\n")


def generate_unique_job_name(prefix: str) -> str:
    return f"{prefix}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"


def create_bedrock_job(
    job_name: str,
    prompt_type: str,
    input_jsonl_path: str,
    role_arn: str,
    model_id: str = "anthropic.claude-3-haiku-20240307-v1:0"
) -> dict:
    logger.info(f"Creating Bedrock job for {prompt_type}: {job_name}")
    input_s3_url = f"s3://{INPUT_BUCKET}/batch/inputs/{os.path.basename(input_jsonl_path)}"
    output_s3_url = f"s3://{OUTPUT_BUCKET}/batch/outputs/{job_name}/"

    input_data_config = {"s3InputDataConfig": {"s3Uri": input_s3_url}}
    output_data_config = {"s3OutputDataConfig": {"s3Uri": output_s3_url}}

    response = bedrock_client.create_model_invocation_job(
        roleArn=role_arn,
        modelId=model_id,
        jobName=job_name,
        inputDataConfig=input_data_config,
        outputDataConfig=output_data_config,
    )
    return response


def upload_to_s3(local_path: str, s3_uri: str) -> None:
    if not s3_uri.startswith("s3://"):
        raise ValueError(f"Invalid S3 URI: {s3_uri}")
    without_scheme = s3_uri.replace("s3://", "")
    bucket, *key_parts = without_scheme.split("/")
    key = "/".join(key_parts)

    logger.info(f"Uploading {local_path} -> {s3_uri}")
    s3_client.upload_file(local_path, bucket, key)
    logger.info("Upload complete.")


def retrieve_bedrock_output(job_name: str, local_dir: str = "/tmp") -> list[str]:
    prefix = f"batch/outputs/{job_name}/"
    local_job_dir = os.path.join(local_dir, job_name)
    os.makedirs(local_job_dir, exist_ok=True)

    response = s3_client.list_objects_v2(Bucket=OUTPUT_BUCKET, Prefix=prefix)
    if "Contents" not in response:
        logger.warning(f"No output files found for job_name={job_name} in s3://{OUTPUT_BUCKET}/{prefix}")
        return []

    downloaded_files = []
    for obj in response["Contents"]:
        key = obj["Key"]
        if key.endswith("/"):
            continue
        filename = os.path.basename(key)
        local_filepath = os.path.join(local_job_dir, filename)
        logger.info(f"Downloading s3://{OUTPUT_BUCKET}/{key} -> {local_filepath}")
        s3_client.download_file(OUTPUT_BUCKET, key, local_filepath)
        downloaded_files.append(local_filepath)
    return downloaded_files

def parse_bedrock_jsonl_extract(jsonl_file: str) -> list[dict]:
    """
    Parse a Bedrock output JSONL file for the 'extract' prompt, 
    using Pydantic's model_validate_json(...) directly on the entire string.
    We assume the LLM outputs pure JSON with no extraneous text.
    """
    results = []

    with open(jsonl_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            # 1) The line is a JSON object describing the record: 
            #    { "recordId": "...", "modelOutput": { "content": [ { "type": "text", "text": "...some JSON..." } ] } }
            data = json.loads(line)
            record_id = data.get("recordId")
            content_list = data.get("modelOutput", {}).get("content", [])
            if not content_list:
                continue

            # 2) The actual LLM output is the entire string in "text"
            text_str = content_list[0].get("text", "")

            # 3) Attempt to parse directly via model_validate_json
            try:
                if EDUCATION_TYPE == 'Breakout':
                    validated = ExtractBreakoutSchema.model_validate_json(text_str)
                else:
                    validated = ExtractSchema.model_validate_json(text_str)
            except ValidationError as ve:
                logger.warning(f"[extract] ValidationError for record {record_id}:\n{ve}")
                continue
            except json.JSONDecodeError as e:
                logger.warning(f"[extract] JSON decode error for record {record_id}: {e}")
                continue

            # 4) Convert validated model -> final dict for upsert
            pay_min, pay_max = None, None
            if len(validated.pay_range or []) == 1:
                pay_min = validated.pay_range[0]
                pay_max = validated.pay_range[0]
            elif len(validated.pay_range or []) >= 2:
                pay_min, pay_max = validated.pay_range[0], validated.pay_range[1]

            if EDUCATION_TYPE == 'Breakout':
                row = {
                    "job_description_hash": record_id,
                    "job_title": (validated.job_title or "").strip(),
                    "details": "\n".join(validated.details or []),
                    "high_school_diploma_or_equivalent": validated.required_preferred.high_school_diploma_or_equivalent if validated.required_preferred else "Not mentioned",
                    "vocational_or_technical_degree": validated.required_preferred.vocational_or_technical_degree if validated.required_preferred else "Not mentioned",
                    "associates_or_2_year_degree": validated.required_preferred.associates_or_2_year_degree if validated.required_preferred else "Not mentioned",
                    "bachelors_or_four_year_degree": validated.required_preferred.bachelors_or_four_year_degree if validated.required_preferred else "Not mentioned",
                    "masters_degree": validated.required_preferred.masters_degree if validated.required_preferred else "Not mentioned",
                    "doctoral_degree_including_jd_md": validated.required_preferred.doctoral_degree_including_jd_md  if validated.required_preferred else "Not mentioned",
                    "required_preferred_major": ", ".join(validated.required_preferred.major) if validated.required_preferred and validated.required_preferred.major else "",
                    "required_preferred_experience": validated.required_preferred.experience if validated.required_preferred else 0,
                    "required_preferred_qualifications": ", ".join(validated.required_preferred.qualifications) if validated.required_preferred and validated.required_preferred.qualifications else "",
                    "benefits": ", ".join(validated.benefits) if validated.benefits else None,
                    "pay_min": pay_min,
                    "pay_max": pay_max,
                    "pay_unit": validated.pay_unit,
                    "entry_level_up_to_3_years_experience": validated.entry_level_up_to_3_years_experience,
                    "part_time": validated.part_time,
                    "remote": validated.remote,
                    "soc_occupation_code": validated.soc_occupation_code,
                }
            else:
                row = {
                    "job_description_hash": record_id,
                    "job_title": (validated.job_title or "").strip(),
                    "details": "\n".join(validated.details or []),
                    "required_education": validated.required.education.value if validated.required and validated.required.education else None,
                    "required_major": ", ".join(validated.required.major) if validated.required and validated.required.major else "",
                    "required_experience": validated.required.experience if validated.required else 0,
                    "required_qualifications": ", ".join(validated.required.qualifications) if validated.required and validated.required.qualifications else "",
                    "preferred_education": validated.preferred.education.value if validated.preferred and validated.preferred.education else None,
                    "preferred_major": ", ".join(validated.preferred.major) if validated.preferred and validated.preferred.major else "",
                    "preferred_experience": validated.preferred.experience if validated.preferred else 0,
                    "preferred_qualifications": ", ".join(validated.preferred.qualifications) if validated.preferred and validated.preferred.qualifications else "",
                    "benefits": ", ".join(validated.benefits) if validated.benefits else None,
                    "pay_min": pay_min,
                    "pay_max": pay_max,
                    "pay_unit": validated.pay_unit,
                    "entry_level": validated.entry_level,
                    "part_time": validated.part_time,
                    "remote": validated.remote,
                    "soc_occupation_code": validated.soc_occupation_code,
                }
            results.append(row)
    return results


def parse_bedrock_jsonl_skills(jsonl_file: str) -> list[dict]:
    """
    Parse a Bedrock output JSONL for the 'skills' prompt
    using Pydantic SkillsSchema for validation.
    Returns a list of dicts ready to upsert into job_extract.
    """
    results = []
    with open(jsonl_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            data = json.loads(line)
            record_id = data.get("recordId")
            #Anthropic Content
            content_list = data.get("modelOutput", {}).get("content", [])
            if not content_list:
                #Nova Pro Content
                content_list = data.get("modelOutput", {}).get("output", {}).get("message",{}).get("content",[])
                if not content_list:
                    continue

            text_str = content_list[0].get("text", "")

            try:
                validated = SkillsSchema.model_validate_json(text_str)
            except ValidationError as ve:
                logger.warning(f"[skills] ValidationError for record {record_id}:\n{ve}")
                continue
            except json.JSONDecodeError as e:
                logger.warning(f"[skills] JSON decode error for record {record_id}: {e}")
                continue

            row = {
                "job_description_hash": record_id,
                "skills": validated.root
            }
            results.append(row)
    return results


########################################
# MAIN ORCHESTRATION
########################################

def process_prompt_loop(
    con: duckdb.DuckDBPyConnection,
    prompt_type: str,
    start_date: datetime,
    max_concurrent: int = MAX_CONCURRENT_JOBS
):
    """
    Orchestrate the repeated process for a given prompt ("extract" or "skills"):
      1) Pull up to BATCH_SIZE records from local parquet files
         and insert (job_id, job_description_hash) into job_extract table
      2) Schedule up to max_concurrent at a time
      3) Monitor each job until final
      4) On success, parse+upsert results
    """
    active_batches = []
    done = False
    role_arn = "arn:aws:iam::214173262954:role/nlx-llm-bedrock-service-role"

    while not done:
        # Remove completed/failed from active list
        active_batches = [b for b in active_batches if b["status"] not in ("COMPLETED", "FAILED")]

        # If we have capacity for more batches
        while len(active_batches) < max_concurrent:
            df = get_jobs_to_process(con, prompt_type, start_date, limit=BATCH_SIZE)
            if df.empty:
                done = True
                break

            batch_name = generate_unique_job_name(f"bedrock-{prompt_type}")
            local_jsonl = f"/tmp/{batch_name}.jsonl"
            if prompt_type == 'extract':
                create_jsonl_for_prompt(df, local_jsonl, prompt_type, EXTRACT_MODEL_ID)
            else:
                create_jsonl_for_prompt(df, local_jsonl, prompt_type, SKILLS_MODEL_ID)

            input_s3_uri = f"s3://{INPUT_BUCKET}/batch/inputs/{os.path.basename(local_jsonl)}"
            upload_to_s3(local_jsonl, input_s3_uri)

            if prompt_type == "extract":
                model_id = EXTRACT_MODEL_ID
            else:
                model_id = SKILLS_MODEL_ID
            
            resp = create_bedrock_job(batch_name, prompt_type, local_jsonl, role_arn, model_id=model_id)
            job_arn = resp.get("jobArn", "")

            con.execute("""
                INSERT INTO batch_status (batch_name, job_arn, prompt_type, status, retry_count)
                VALUES (?, ?, ?, ?, 0)
                ON CONFLICT (batch_name) 
                DO UPDATE SET
                    job_arn=excluded.job_arn,
                    prompt_type=excluded.prompt_type,
                    status=excluded.status,
                    retry_count=excluded.retry_count
            """, [batch_name, job_arn, prompt_type, "IN_PROGRESS"])

            active_batches.append({
                "name": batch_name,
                "job_arn": job_arn,
                "prompt_type": prompt_type,
                "records": df,
                "status": "IN_PROGRESS",
                "attempts": 1,
                "local_jsonl": local_jsonl
            })

        if not active_batches and done:
            break

        # Wait, then poll each batch
        time.sleep(90)
        for batch in active_batches:
            if batch["status"] == "IN_PROGRESS":
                try:
                    res = bedrock_client.get_model_invocation_job(jobIdentifier=batch["job_arn"])
                except Exception as e:
                    logger.warning(f"Error checking job status for {batch['job_arn']}: {e}")
                    continue

                st = res["status"]
                logger.info(f"[{batch['job_arn']}] status={st}")

                final_states = ["COMPLETED", "FAILED", "STOPPED", "PARTIALLYCOMPLETED", "EXPIRED"]
                st_upper = st.upper()

                if st_upper == "COMPLETED":
                    batch["status"] = "COMPLETED"
                    output_files = retrieve_bedrock_output(batch["name"], local_dir="./tmp")
                    now_ts = datetime.utcnow().isoformat()

                    if prompt_type == "extract":
                        # parse & upsert
                        all_rows = []
                        for fpath in output_files:
                            if fpath.endswith(".jsonl.out"):
                                subrows = parse_bedrock_jsonl_extract(fpath)
                                all_rows.extend(subrows)
                                
                        duckdb_upsert_extract(con, all_rows, now_ts)

                    else:  # "skills"
                        all_rows = []
                        for fpath in output_files:
                            if fpath.endswith(".jsonl.out"):
                                subrows = parse_bedrock_jsonl_skills(fpath)
                                all_rows.extend(subrows)
                        duckdb_upsert_skills(con, all_rows, now_ts)

                    con.execute("UPDATE batch_status SET status='COMPLETED' WHERE batch_name=?", [batch["name"]])

                elif st_upper in final_states:
                    batch["status"] = "FAILED"
                    logger.error(f"Batch {batch['name']} ended in status: {st_upper}")
                    con.execute("SELECT retry_count FROM batch_status WHERE batch_name=?", [batch["name"]])
                    retry_count = con.fetchone()[0]

                    if retry_count < MAX_RETRIES:
                        logger.info(f"Retrying batch {batch['name']} (attempt {retry_count+1})...")
                        new_name = generate_unique_job_name(batch["name"])
                        resp = create_bedrock_job(new_name, prompt_type, batch["local_jsonl"], role_arn, model_id=model_id)
                        new_arn = resp.get("jobArn", "")

                        con.execute("""
                            INSERT INTO batch_status (batch_name, job_arn, prompt_type, status, retry_count)
                            VALUES (?, ?, ?, ?, ?)
                            ON CONFLICT (batch_name) DO UPDATE SET
                                job_arn=excluded.job_arn,
                                prompt_type=excluded.prompt_type,
                                status=excluded.status,
                                retry_count=excluded.retry_count
                        """, [new_name, new_arn, prompt_type, "IN_PROGRESS", retry_count+1])

                        batch["name"] = new_name
                        batch["job_arn"] = new_arn
                        batch["status"] = "IN_PROGRESS"
                        batch["attempts"] = retry_count + 1
                    else:
                        con.execute("""
                            UPDATE batch_status 
                            SET status='FAILED', 
                                last_error='Max retries reached' 
                            WHERE batch_name=? 
                        """, [batch["name"]])


def main(db_path: str = "nlx_jobs.duckdb"):
    """
    1) Initialize DuckDB.
    2) Process "extract" prompt (inserting job_id & hash before scheduling).
    3) Process "skills" prompt similarly if desired.
    """
    con = init_duckdb(db_path)
    start_date = datetime.utcnow() - timedelta(days=DEFAULT_LOOKBACK_DAYS)

    # 1) extract
    process_prompt_loop(con, "extract", start_date)

    # 2) skills
    # process_prompt_loop(con, "skills", start_date)

    logger.info("All prompts processed. Exiting.")


if __name__ == "__main__":
    main()
