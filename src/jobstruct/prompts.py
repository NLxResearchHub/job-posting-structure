# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# Copyright National Association of State Workforce Agencies. All Rights Reserved.
# SPDX-License-Identifier: CC-BY-NC-SA-4.0

from textwrap import dedent


class Prompts:
    """
    Preconstructed prompts for generative AI operations.
    Each prompt includes placeholders for {schema_json} 
    so we can inject the actual machine-readable JSON schema from Pydantic at runtime.
    """

    extract = dedent("""
        Your task is to read the job post inside the <text></text> tags and accurately extract relevant information in the Pydantic JSON schema shown in <schema></schema>.
        <instructions>
         1. Read the job post carefully and thoroughly, line by line.
         2. Do not make any assumptions or leave out any details.
         3. Extract the information according to the instructions in, and in the format of, the Pydantic JSON schema.
        </instructions>
        <text>
        {text}
        </text>
        Return the information in JSON format using the schema below.
        <schema>
            {schema_json}
         </schema>
        Do not provide any rationale or explanation in your response. Only output valid JSON in the requested schema.""")

    skills = dedent("""
        Your task is to read the job requirements in the <text></text> tags and map each given qualification to relevant skills
        given within the <skills></skills> tags. Make sure to map each qualification from the job description and only include skills from the provided taxonomy. 
        Read the qualifications in the job description carefully, and make the correct mapping to the given set of skills from the job description below:
        <text>
        {text}
        </text>
        Understand the qualifications from the job description above, and map them to this skills taxonomy below:
        <skills>
        {skills}
        </skills>
        Do not provide any rationale or explanation in your response. Only output valid JSON in the requested schema.
        Be careful, think, check your answers and only then return your response. 
        ONLY INCLUDE SKILLS FROM THE PROVIDED SKILLS TAXONOMY.
        
        You must produce valid JSON that exactly matches the following Pydantic JSON schema:
        {schema_json}
        """)

    occupation = dedent("""
        You are a helpful assistant.
        <task>
        You must select the two most relevant Standard Occupational Classification (SOC) codes for the job description
         provided within the <text></text> tags.
        </task>
        <instructions>
        Here are some important rules for the task:
        - Read the entire job description within <text></text> carefully.
        <text>
        {text}
        </text>
        - Based on your complete understanding of the job description, identify the two most relevant Standard Occupational
          Classification (SOC) major occupation code that best corresponds to the job description.
           Only and only if you are ambiguous about categorizing the job description into one single code, then return two codes.
           Otherwise you must return one code.
        </instructions>
        Return one or two codes using the schema below.
        <schema>
            ```json {{
                'occupation': <>Return a list of codes.</>
            }}```
        </schema>
        Skip the preamble and the explanation.
        Be careful, think, check your answers and only then return your response. 
        You must not select skills at random, it must be through careful examination.""")

    embedding = ""

    taxonomy_enrich = dedent("""
        You are a helpful assistant.
        Your task is to read the skills taxonomy containing the parent node - leaf node combination within <tree></tree> 
        tags and expand only the leaf node. You must make use of all your knowledge on job postings and expand the leaf 
        nodes using the related skills only. You must be very careful.
        <tree>
        {text}
        </tree>
        <note>
        - You must return your response in the same format of the tree.
        - You are free to expand the leaf nodes up to whatever depth you feel necessary, however make sure to add only 
        relevant skills as nodes. Use all your knowledge to create an expanded tree and make it comprehensive.
        </note>
        Review your output for correctness and check if all instructions have been followed. Skip the explanation and 
        the preamble and return your verified response only.""")

    taxonomy_refine = dedent("""
        You are a helpful assistant.
        Your task is to review the skills taxonomy contained in the <tree></tree> tags, remove skills that are duplicates or too specific, and add any important skills that are missing.
        <tree>
        {text}
        </tree>
        <note>
        - You must return your response in the same format of the tree.
        - Make sure the tree contains new and emerging skills that are important in the labor market.
        </note>
        Review your output for correctness and check if all instructions have been followed. Skip the explanation and the preamble and return your verified response only.""")

    taxonomy_prune = dedent("""
        You are a helpful assistant.
        Your task is to review the skills contained in the <tree></tree> tags.
        Some skills are duplicates with different parents. For each duplicate, you need to select one to keep based on the context (parent skills) and suggest removal of the rest.
        <tree>
        {text}
        </tree>
        <note>
        - Return your response in the same tree format, with duplicate skills removed.
        - For each removed skill, list it under a "removed" key in the output.
        - Ensure the remaining skill fits well with the parent nodes and the overall tree.
        - Do not change any skills unless they are duplicates.
        </note>
        Review your output for correctness and check if all instructions have been followed. Skip the explanation and the preamble and return your verified response only.
    """)
