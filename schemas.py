import json
import re
from enum import Enum
from typing import List, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    RootModel,
    field_validator,
)

# SOC CODES
with open('lookup_soc_titles.json', 'r') as file:
    SOC_TITLES = json.load(file)
    
########################################
# Pydantic V2 Models (With Descriptions)
########################################

class EducationLevel(str, Enum):
    less_than_high_school = "Less than High School"
    high_school = "High School Diploma or Equivalent"
    postsecondary_training = "Postsecondary training but not a college degree"
    associates_degree = "Associate's or 2 year Degree"
    bachelors_degree = "Bachelor's or 4 year Degree"
    masters_degree = "Master's Degree"
    doctoral_degree = "Doctoral Degree (including MD, JD)"
    other = "Other"
    not_specified = "Not specified"

# Mapping of truncated names to enum values
EDUCATION_MAPPING = {
    "less than high school": EducationLevel.less_than_high_school,
    "high school": EducationLevel.high_school,
    "associate": EducationLevel.associates_degree,
    "rn": EducationLevel.associates_degree,
    "school of nursing": EducationLevel.associates_degree,
    "registered nurse": EducationLevel.associates_degree,
    "2 year degree": EducationLevel.associates_degree,
    "bachelor": EducationLevel.bachelors_degree,
    "4 year degree": EducationLevel.bachelors_degree,
    "bs/ba": EducationLevel.bachelors_degree,
    "b.a": EducationLevel.bachelors_degree,
    "b.s": EducationLevel.bachelors_degree,
    "bsn": EducationLevel.bachelors_degree,
    "master": EducationLevel.masters_degree,
    "m.a": EducationLevel.masters_degree,
    "m.s": EducationLevel.masters_degree,
    "mba": EducationLevel.masters_degree,
    "mfa": EducationLevel.masters_degree,
    "m.ed": EducationLevel.masters_degree,
    "m.arch": EducationLevel.masters_degree,
    "llm": EducationLevel.masters_degree,
    "phd": EducationLevel.doctoral_degree,
    "ph.d": EducationLevel.doctoral_degree,
    "doctor": EducationLevel.doctoral_degree,
    "md": EducationLevel.doctoral_degree,
    "m.d": EducationLevel.doctoral_degree,
    "jd": EducationLevel.doctoral_degree,
    "j.d": EducationLevel.doctoral_degree,
    "pharmd": EducationLevel.doctoral_degree,
    "dpharm": EducationLevel.doctoral_degree,
    "edd": EducationLevel.doctoral_degree,
    "dmd": EducationLevel.doctoral_degree,
    "dph": EducationLevel.doctoral_degree,
    "dpt": EducationLevel.doctoral_degree,
    "psy.d": EducationLevel.doctoral_degree,
    "dds": EducationLevel.doctoral_degree,
    "other": EducationLevel.other,
    "grade school": EducationLevel.other,
    "technical diploma": EducationLevel.postsecondary_training,
    "technical degree": EducationLevel.postsecondary_training,
    "vocational": EducationLevel.postsecondary_training,
    "medical assistant": EducationLevel.postsecondary_training,
    "2 or more years of college": EducationLevel.postsecondary_training,
    "practical nurs": EducationLevel.postsecondary_training,
    "vocational nurs": EducationLevel.postsecondary_training,
    "lpn": EducationLevel.postsecondary_training,
    "lvn": EducationLevel.postsecondary_training,
    "some college": EducationLevel.postsecondary_training,
    "surgical technology program": EducationLevel.postsecondary_training,
    "unknown": EducationLevel.not_specified,
    "not known": EducationLevel.not_specified,
    "cdl": EducationLevel.not_specified,
    "not specified": EducationLevel.not_specified,
    "experience": EducationLevel.not_specified,
    "aptitude": EducationLevel.not_specified,
    "knowledge": EducationLevel.not_specified,
    "cpr": EducationLevel.not_specified,
    "bsee": EducationLevel.not_specified,
    "license": EducationLevel.not_specified,
    "rt/aart": EducationLevel.not_specified,
    "ts/sci": EducationLevel.not_specified,
}

EDUCATION_ORDER = {
    EducationLevel.less_than_high_school: 0,
    EducationLevel.high_school: 1,
    EducationLevel.postsecondary_training: 2,
    EducationLevel.associates_degree: 3,
    EducationLevel.bachelors_degree: 4,
    EducationLevel.masters_degree: 5,
    EducationLevel.doctoral_degree: 6,
    EducationLevel.other: 7,
    EducationLevel.not_specified: 8,
}

class DegreeOptions(str, Enum):
    not_mentioned = "Not mentioned"
    required = "Required"
    preferred_or_can_be_substituted = "Preferred/Can be substituted with experience"
    other = "Other"

# Mapping of truncated names to enum values
DEGREE_MAPPING = {
    "req": DegreeOptions.required,
    "pref": DegreeOptions.preferred_or_can_be_substituted,
    "sub":  DegreeOptions.preferred_or_can_be_substituted,
    "exper": DegreeOptions.preferred_or_can_be_substituted,
    "another": DegreeOptions.other,
    "addition": DegreeOptions.other,
    "mention": DegreeOptions.not_mentioned,
}

class PayUnit(str, Enum):
    hourly = "hourly"
    annual = "annual"
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"
    other = "other"
    not_specified = "not specified"

PAY_UNIT_MAPPING = {
    "hourly": PayUnit.hourly,
    "per hour": PayUnit.hourly,
    "annual": PayUnit.annual,
    "per year": PayUnit.annual,
    "yearly": PayUnit.annual,
    "daily": PayUnit.daily,
    "per day": PayUnit.daily,
    "weekly": PayUnit.weekly,
    "per week": PayUnit.weekly,
    "monthly": PayUnit.monthly,
    "per month": PayUnit.monthly,
    "other": PayUnit.other,
    "commission": PayUnit.other,
    "unknown": PayUnit.not_specified,
    "not known": PayUnit.not_specified,
    "doesn't specify": PayUnit.not_specified,
    "does not specify": PayUnit.not_specified,
    "not specified": PayUnit.not_specified,
}

PAY_UNIT_ORDER = {
    PayUnit.hourly: 0,
    PayUnit.daily: 1,
    PayUnit.weekly: 2,
    PayUnit.monthly: 3,
    PayUnit.annual: 4,
    PayUnit.other: 5,
    PayUnit.not_specified: 6,
}

class RemoteOption(str, Enum):
    in_person = "In-person"
    hybrid = "Hybrid"
    remote_with_location_restrictions = "Remote with location restrictions"
    fully_remote = "Fully remote"
    not_specified = "Not specified"

class EntryLevelOption(str, Enum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    NOT_SPECIFIED = "Not specified"

class PartTimeOption(str, Enum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    NOT_SPECIFIED = "Not specified"

def clean_soc_code(soc_code):
    """
    Clean and standardize a SOC code to a 6-digit format without hyphens.
    """
    return "".join(filter(str.isdigit, soc_code))

class RequiredPreferred(BaseModel):
    """
    This sub-model defines fields for required or preferred attributes of a job candidate.
    """
    model_config = ConfigDict(
        extra="ignore",
        title="RequiredPreferred",
        description=(
            "Defines the required or preferred attributes of a job candidate (education, major, experience, and qualifications)."
        )
    )

    education: Optional[EducationLevel] = Field(
        default=EducationLevel.not_specified,
        description=(
            "Return the LOWEST educational level required or preferred.\n"
            "Acceptable values include: \n"
            "- Less than High School \n"
            "- High School Diploma or Equivalent \n"
            "- Postsecondary training but not a college degree \n"
            "- Associate's or 2 year Degree \n"
            "- Bachelor's or 4 year Degree \n"
            "- Master's Degree \n"
            "- Doctoral Degree (including MD, JD) \n"
            "- Other \n"
            "- Not specified \n"
            "Note: Code as an education from this list ONLY if there is an EXPLICIT MENTION of a required/preferred degree, school, or program. "
            "If required or preferred education is NOT mentioned, code as 'Not speicifed'. "
            "School or program completion that is not a traditional degree (e.g., nursing school or vocational training) should be coded as 'Postsecondary training but not a college degree'. "
            "Mentions of licenses, certifications, or other similar things should not be coded as required/preferred education. "
            "Current enrollment in a college or other postsecondary program, or requirement/preference of just some college class(es) should be coded as Postsecondary training but not a college degree. \n"
            "Note: 'Doctoral Degree (including MD, JD)' includes PhD as well. \n"
            "Note: 'Other' includes all other required/prefererred education and should only be used if the required/preferred education in the job description is known."
        )
    )
    major: Optional[List[str]] = Field(
        default_factory=list,
        description="Return a list of required or preferred majors or areas of study."
    )
    experience: Optional[int] = Field(
        default=None,
        description="Return the required or preferred years of experience as an INTEGER only."
    )
    @field_validator("experience", mode="before")
    def validate_experience(cls, value):
        if value is None:
            return None
        
        if isinstance(value, int):
            return value
        
        if isinstance(value, float):
            return int(value)

        return None
    
    qualifications: Optional[List[str]] = Field(
        default_factory=list,
        description="Return a list of all required or preferred qualifications, abilities, knowledge, skills, certifications, training, and licenses."
    )

    @field_validator("education", mode="before")
    def validate_education(cls, value):
        if value is None:
            return EducationLevel.not_specified

        if value.upper() in ['NONE','UNKNOWN',"DOESN'T SPECIFY","NOT SPECIFIED"]:
            return EducationLevel.not_specified

        if value.strip() == 'Postsecondary training but not a college degree':
            return EducationLevel.postsecondary_training
        
        if isinstance(value, EducationLevel):
            return value
        
        if isinstance(value, str):
            value_lower = value.lower().strip()
            matches = [v for k, v in EDUCATION_MAPPING.items() if k in value_lower]
            
            if matches:
                return min(matches, key=lambda x: EDUCATION_ORDER[x])
            else:
                return EducationLevel.not_specified
                # raise ValueError(f"Invalid education level: {value}")

        return EducationLevel.not_specified
        # raise ValueError(f"Invalid type for education: {type(value)}")

class RequiredPreferredBreakout(BaseModel):
    """
    This sub-model defines fields for required or preferred attributes of a job candidate.
    """
    model_config = ConfigDict(
        extra="ignore",
        title="RequiredPreferred",
        description=(
            "Defines the required or preferred attributes of a job candidate (education, major, experience, and qualifications)."
        )
    )

    high_school_diploma_or_equivalent: Optional[DegreeOptions] = Field(
        default=DegreeOptions.not_mentioned,
        description=(
            "For High School Diploma or Equivalent: Return 'Required' if the job description explicitly states that a High School Diploma or Equivalent is mandatory; "
            "return 'Preferred/Can be substituted with experience' if it is mentioned as preferred or can be substituted with work experience; "
            "return 'Other' if a non-standard requirement is specified; otherwise, return 'Not mentioned' if there is no explicit mention."
        )
    )
    @field_validator("high_school_diploma_or_equivalent", mode="before")
    def validate_hs_diploma(cls, value):
        if value is None:
            return "Not mentioned"
        
        if isinstance(value, DegreeOptions):
            return value
        
        if isinstance(value, str):
            value_lower = value.lower().strip()
            matches = [v for k, v in DEGREE_MAPPING.items() if k in value_lower]

            if len(matches) == 1:
                return matches[0]
            else:
                return DegreeOptions.not_mentioned
            
        return DegreeOptions.not_mentioned
    
    vocational_or_technical_degree: Optional[DegreeOptions] = Field(
        default=DegreeOptions.not_mentioned,
        description=(
            "For Vocational or Technical Degree: Return 'Required' if the job description mandates vocational or technical training or certification; "
            "return 'Preferred/Can be substituted with experience' if such training is noted as a preference or can be substituted with experience; "
            "return 'Other' if an alternative qualification is indicated; otherwise, return 'Not mentioned' if no details are provided. "
        )
    )
    @field_validator("vocational_or_technical_degree", mode="before")
    def validate_vocational_or_technical_degree(cls, value):
        if value is None:
            return "Not mentioned"
        
        if isinstance(value, DegreeOptions):
            return value
        
        if isinstance(value, str):
            value_lower = value.lower().strip()
            matches = [v for k, v in DEGREE_MAPPING.items() if k in value_lower]

            if len(matches) == 1:
                return matches[0]
            else:
                return DegreeOptions.not_mentioned
            
        return DegreeOptions.not_mentioned
    
    associates_or_2_year_degree: Optional[DegreeOptions] = Field(
        default=DegreeOptions.not_mentioned,
        description=(
            "This refers to any Associate's or general undergraduate degree mentioned in the job description. "
            "Return 'Required' if the job explicitly requires an Associate's or 2-year degree; "
            "return 'Preferred/Can be substituted with experience' if the degree is preferred but may be substituted with relevant experience; "
            "return 'Other' if a different alternative is provided; otherwise, return 'Not mentioned' if not specified. "
        )
    )
    @field_validator("associates_or_2_year_degree", mode="before")
    def validate_associates_or_2_year_degree(cls, value):
        if value is None:
            return "Not mentioned"
        
        if isinstance(value, DegreeOptions):
            return value
        
        if isinstance(value, str):
            value_lower = value.lower().strip()
            matches = [v for k, v in DEGREE_MAPPING.items() if k in value_lower]

            if len(matches) == 1:
                return matches[0]
            else:
                return DegreeOptions.not_mentioned
            
        return DegreeOptions.not_mentioned
        
    bachelors_or_four_year_degree: Optional[DegreeOptions] = Field(
        default=DegreeOptions.not_mentioned,
        description=(
            "This refers to any Bachelor's, Bachelor of Arts, Bachelor of Science , or general undergraduate degree mentioned in the job description. "
            "Return 'Required' if the job mandates a bachelor's degree; "
            "return 'Preferred/Can be substituted with experience' if a bachelor's is preferred or can be substituted with work experience; "
            "return 'Other' if a non-standard requirement is mentioned; otherwise, return 'Not mentioned' if no explicit information is provided about a bachelor's degree. "
        )
    )
    @field_validator("bachelors_or_four_year_degree", mode="before")
    def validate_bachelors_or_four_year_degree(cls, value):
        if value is None:
            return "Not mentioned"
        
        if isinstance(value, DegreeOptions):
            return value
        
        if isinstance(value, str):
            value_lower = value.lower().strip()
            matches = [v for k, v in DEGREE_MAPPING.items() if k in value_lower]

            if len(matches) == 1:
                return matches[0]
            else:
                return DegreeOptions.not_mentioned
            
        return DegreeOptions.not_mentioned
    
    masters_degree: Optional[DegreeOptions] = Field(
        default=DegreeOptions.not_mentioned,
        description=(
            "This refers to any Master's, Master of Arts, Master of Science, or general advanced degree or graduate degree mentioned in the job description. "
            "Return 'Required' if the job explicitly mandates a master's degree or advanced degree; "
            "return 'Preferred/Can be substituted with experience' if a master's degree or advanced degree is preferred or can be substituted with experience; "
            "return 'Other' if an alternative requirement is provided; otherwise, return 'Not mentioned' if there is no explicit mention. "
        )
    )
    @field_validator("masters_degree", mode="before")
    def validate_masters_degree(cls, value):
        if value is None:
            return "Not mentioned"
        
        if isinstance(value, DegreeOptions):
            return value
        
        if isinstance(value, str):
            value_lower = value.lower().strip()
            matches = [v for k, v in DEGREE_MAPPING.items() if k in value_lower]

            if len(matches) == 1:
                return matches[0]
            else:
                return DegreeOptions.not_mentioned
            
        return DegreeOptions.not_mentioned
        
    doctoral_degree_including_jd_md: Optional[DegreeOptions] = Field(
        default=DegreeOptions.not_mentioned,
        description=(
            "This refers to any Doctorate, PhD, JD, MD or general advanced degree or graduate degree mentioned in the job description. "
            "Return 'Required' if the job requires a doctoral-level degree; "
            "return 'Preferred/Can be substituted with experience' if a doctoral degree is preferred but not mandatory; "
            "return 'Other' if a non-standard requirement is specified; otherwise, return 'Not mentioned' if the degree is not mentioned. "
        )
    )
    @field_validator("doctoral_degree_including_jd_md", mode="before")
    def validate_doctoral_degree(cls, value):
        if value is None:
            return "Not mentioned"
        
        if isinstance(value, DegreeOptions):
            return value
        
        if isinstance(value, str):
            value_lower = value.lower().strip()
            matches = [v for k, v in DEGREE_MAPPING.items() if k in value_lower]

            if len(matches) == 1:
                return matches[0]
            else:
                return DegreeOptions.not_mentioned
            
        return DegreeOptions.not_mentioned
    
    major: Optional[List[str]] = Field(
        default_factory=list,
        description="Return a list of required or preferred majors or areas of study."
    )
    experience: Optional[int] = Field(
        default=None,
        description="Return the required or preferred years of experience as an INTEGER only."
    )
    @field_validator("experience", mode="before")
    def validate_experience(cls, value):
        if value is None:
            return None
        
        if isinstance(value, int):
            return value
        
        if isinstance(value, float):
            return int(value)

        return None
    
    qualifications: Optional[List[str]] = Field(
        default_factory=list,
        description="Return a list of all required or preferred qualifications, abilities, knowledge, skills, certifications, training, and licenses."
    )

class Required(BaseModel):
    """
    This sub-model defines fields for required qualifications.
    """
    model_config = ConfigDict(
        extra="ignore",
        title="Required",
        description=(
            "Defines the required attributes of a job candidate (education, major, experience, and qualifications)."
        )
    )

    education: Optional[EducationLevel] = Field(
        default=EducationLevel.not_specified,
        description=(
            "Return the LOWEST educational level REQUIRED. Do not include preferred education in this field. \n"
            "Acceptable values include: \n"
            "- Less than High School \n"
            "- High School Diploma or Equivalent \n"
            "- Postsecondary training but not a college degree \n"
            "- Associate's or 2 year Degree \n"
            "- Bachelor's or 4 year Degree \n"
            "- Master's Degree \n"
            "- Doctoral Degree (including MD, JD) \n"
            "- Other \n"
            "- Not specified \n"
            "Note: Code as an education from this list ONLY if there is an EXPLICIT MENTION of a required degree, school, or program. "
            "If no required education is mentioned, code as 'Not specified'. "
            "School or program completion that is not a traditional degree (e.g., nursing school or vocational training) should be coded as 'Postsecondary training but not a college degree'. "
            "Mentions of licenses, certifications, or other similar things should not be coded as required education. "
            "Current enrollment in a college or other postsecondary program, or requirement of just some college class(es) should be coded as Postsecondary training but not a college degree. \n"
            "Note: 'Doctoral Degree (including MD, JD)' includes PhD as well. \n"
            "Note: 'Other' includes all other required educational and should only be used if the required education in the job description is known."
        )
    )
    major: Optional[List[str]] = Field(
        default_factory=list,
        description="Return a list of required majors or areas of study."
    )
    experience: Optional[int] = Field(
        default=None,
        description="Return the required years of experience as an INTEGER only."
    )
    @field_validator("experience", mode="before")
    def validate_experience(cls, value):
        if value is None:
            return None
        
        if isinstance(value, int):
            return value
        
        if isinstance(value, float):
            return int(value)

        return None
        
    qualifications: Optional[List[str]] = Field(
        default_factory=list,
        description="Return a list of all required qualifications, abilities, knowledge, skills, certifications, training, and licenses."
    )

    @field_validator("education", mode="before")
    def validate_education(cls, value):
        if value is None:
            return EducationLevel.not_specified

        if value.upper() in ['NONE','UNKNOWN',"DOESN'T SPECIFY", "NOT SPECIFIED"]:
            return EducationLevel.not_specified

        if value.strip() == 'Postsecondary training but not a college degree':
            return EducationLevel.postsecondary_training
        
        if isinstance(value, str):
            value_lower = value.lower().strip()
            matches = [v for k, v in EDUCATION_MAPPING.items() if k in value_lower]
            
            if matches:
                return min(matches, key=lambda x: EDUCATION_ORDER[x])
            else:
                return EducationLevel.not_specified
                # raise ValueError(f"Invalid education level: {value}")

        return EducationLevel.not_specified
        # raise ValueError(f"Invalid type for education: {type(value)}")

class Preferred(BaseModel):
    """
    This sub-model defines fields for preferred qualifications.
    """
    model_config = ConfigDict(
        extra="ignore",
        title="Preferred",
        description=(
            "Defines the preferred attributes of a job candidate (education, major, experience, and qualifications)."
        )
    )

    education: Optional[EducationLevel] = Field(
        default=EducationLevel.not_specified,
        description=(
            "Return the LOWEST educational level PREFERRED. Do not include required education in this field. \n"
            "Acceptable values include: \n"
            "- Less than High School \n"
            "- High School Diploma or Equivalent \n"
            "- Postsecondary training but not a college degree \n"
            "- Associate's or 2 year Degree \n"
            "- Bachelor's or 4 year Degree \n"
            "- Master's Degree \n"
            "- Doctoral Degree (including MD, JD) \n"
            "- Other \n"
            "- Not specified \n"
            "Note: Code as an education from this list ONLY if there is an EXPLICIT MENTION of a preferred degree, school, or program. "
            "If preferred education is NOT mentioned, code as 'Not specified'. "
            "School or program completion that is not a traditional degree (e.g., nursing school or vocational training) should be coded as 'Postsecondary training but not a college degree'. "
            "Mentions of licenses, certifications, or other similar things should not be coded as preferred education. "
            "Current enrollment in a college or other postsecondary program, or preference for just some college class(es) should be coded as Postsecondary training but not a college degree. \n"
            "Note: 'Doctoral Degree (including MD, JD)' includes PhD as well. \n"
            "Note: 'Other' includes all other preferred education and should only be used if the preferred education in the job description is known."
        )
    )
    major: Optional[List[str]] = Field(
        default_factory=list,
        description="Return a list of preferred majors or areas of study."
    )
    experience: Optional[int] = Field(
        default=None,
        description="Return the preferred years of experience as an INTEGER only."
    )
    @field_validator("experience", mode="before")
    def validate_experience(cls, value):
        if value is None:
            return None
        
        if isinstance(value, int):
            return value
        
        if isinstance(value, float):
            return int(value)

        return None
        
    qualifications: Optional[List[str]] = Field(
        default_factory=list,
        description="Return a list of all preferred qualifications, abilities, knowledge, skills, certifications, training, and licenses."
    )

    @field_validator("education", mode="before")
    def validate_education(cls, value):
        if value is None:
            return EducationLevel.not_specified

        if value.upper() in ['NONE','UNKNOWN',"DOESN'T SPECIFY", "NOT SPECIFIED"]:
            return EducationLevel.not_specified

        if value.strip() == 'Postsecondary training but not a college degree':
            return EducationLevel.postsecondary_training
        
        if isinstance(value, EducationLevel):
            return value
        
        if isinstance(value, str):
            value_lower = value.lower().strip()
            matches = [v for k, v in EDUCATION_MAPPING.items() if k in value_lower]
            
            if matches:
                return min(matches, key=lambda x: EDUCATION_ORDER[x])
            else:
                return EducationLevel.not_specified
                # raise ValueError(f"Invalid education level: {value}")

        return EducationLevel.not_specified
        # raise ValueError(f"Invalid type for education: {type(value)}")

class RequiredPreferredEducationMajor(BaseModel):
    """
    This sub-model defines fields for required or preferred education and major of a job candidate.
    """
    model_config = ConfigDict(
        extra="ignore",
        title="RequiredPreferredEducationMajor",
        description=(
            "Defines the required or preferred education and major of a job candidate."
        )
    )

    education: Optional[EducationLevel] = Field(
        default=EducationLevel.not_specified,
        description=(
            "Return the LOWEST educational level required or preferred.\n"
            "Acceptable values include: \n"
            "- Less than High School \n"
            "- High School Diploma or Equivalent \n"
            "- Postsecondary training but not a college degree \n"
            "- Associate's or 2 year Degree \n"
            "- Bachelor's or 4 year Degree \n"
            "- Master's Degree \n"
            "- Doctoral Degree (including MD, JD) \n"
            "- Other \n"
            "- Not specified \n"
            "Note: Code as an education from this list ONLY if there is an EXPLICIT MENTION of a required/preferred degree, school, or program. "
            "If required or preferred education is NOT mentioned, code as 'Not speicifed'. "
            "School or program completion that is not a traditional degree (e.g., nursing school or vocational training) should be coded as 'Postsecondary training but not a college degree'. "
            "Mentions of licenses, certifications, or other similar things should not be coded as required/preferred education. "
            "Current enrollment in a college or other postsecondary program, or requirement/preference of just some college class(es) should be coded as Postsecondary training but not a college degree. \n"
            "Note: 'Doctoral Degree (including MD, JD)' includes PhD as well. \n"
            "Note: 'Other' includes all other required/prefererred education and should only be used if the required/preferred education in the job description is known."
        )
    )
    major: Optional[List[str]] = Field(
        default_factory=list,
        description="Return a list of required or preferred majors or areas of study."
    )

    @field_validator("education", mode="before")
    def validate_education(cls, value):
        if value is None:
            return EducationLevel.not_specified

        if value.upper() in ['NONE','UNKNOWN',"DOESN'T SPECIFY","NOT SPECIFIED"]:
            return EducationLevel.not_specified

        if value.strip() == 'Postsecondary training but not a college degree':
            return EducationLevel.postsecondary_training
        
        if isinstance(value, EducationLevel):
            return value
        
        if isinstance(value, str):
            value_lower = value.lower().strip()
            matches = [v for k, v in EDUCATION_MAPPING.items() if k in value_lower]
            
            if matches:
                return min(matches, key=lambda x: EDUCATION_ORDER[x])
            else:
                return EducationLevel.not_specified

        return EducationLevel.not_specified

class RequiredPreferredExperienceQualifications(BaseModel):
    """
    This sub-model defines fields for required or preferred attributes of a job candidate.
    """
    model_config = ConfigDict(
        extra="ignore",
        title="RequiredPreferredExperienceQualifications",
        description=(
            "Defines the required or preferred experience and qualifications of a job candidate."
        )
    )

    experience: Optional[int] = Field(
        default=None,
        description="Return the required or preferred years of experience as an INTEGER only."
    )
    @field_validator("experience", mode="before")
    def validate_experience(cls, value):
        if value is None:
            return None
        
        if isinstance(value, int):
            return value
        
        if isinstance(value, float):
            return int(value)

        return None
        
    qualifications: Optional[List[str]] = Field(
        default_factory=list,
        description="Return a list of all required or preferred qualifications, abilities, knowledge, skills, certifications, training, and licenses."
    )

class ExtractSchema(BaseModel):
    """
    Pydantic model for information to be extracted from the job description in JSON format.
    """
    
    model_config = ConfigDict(
        extra="ignore",
        title="ExtractSchema",
        description=(
            "This schema represents all fields to extract from the job description."
        )
    )

    job_title: Optional[str] = Field(
        default=None,
        description="Return the job title."
    )
    details: Optional[List[str]] = Field(
        default_factory=list,
        description="Return a list of all duties and responsibilities associated with the job. Include all information."
    )
    required: Optional[RequiredPreferred] = Field(
        default_factory=dict,
        description="Return the required fields, including education, major, experience, and qualifications."
    )
    preferred: Optional[RequiredPreferred] = Field(
        default_factory=dict,
        description="Return the preferred fields, including education, major, experience, and qualifications."
    )
    benefits: Optional[List[str]] = Field(
        default=None,
        description="Return a list of the benefits offered."
    )
    pay_range: Optional[List[Optional[float]]] = Field(
        default_factory=list,
        description="""Return a list with ONLY the minimum and maximum USD pay range of the position as floating point numbers, formatted with no commas or dollar signs, if this information exists in the job description.
        
If multiple pay ranges appear in the job description, use the minimum and maximum across ALL pay ranges.

If the median or average pay appears in the job description, please only return the minimum and maximum values available.

If only one value for the pay range appears in the job description, please return that value twice as the minimum and maximum.
"""
    )
    @field_validator("pay_range", mode="before")
    def clean_pay_range(cls, value):
        if value is None:
            return value
        if isinstance(value, list):
            cleaned_values = []
            for item in value:
                if item is None:
                    cleaned_values.append(None)
                elif isinstance(item, str):
                    cleaned_item = re.sub(r"[^\d.]", "", item)
                    if cleaned_item:
                        try:
                            cleaned_values.append(float(cleaned_item))
                        except ValueError:
                            raise ValueError(f"Invalid value in pay_range: {item}")
                    else:
                        raise ValueError(f"Invalid value in pay_range: {item}")
                elif isinstance(item, (int, float)):
                    cleaned_values.append(float(item))
                else:
                    raise ValueError(f"Unexpected type in pay_range: {type(item).__name__}")
            return cleaned_values
        return value
    
    pay_unit: Optional[PayUnit] = Field(default=PayUnit.not_specified, description="Return the best pay per unit value from the set ('annual', 'monthly', 'weekly', 'daily', 'hourly', 'other', and 'not specified'). If no EXPLICIT MENTION of the pay_unit exists, code as 'not specified'.")

    @field_validator("pay_unit", mode="before")
    def validate_pay_unit(cls, value):
        if value is None:
            return PayUnit.not_specified
            
        if isinstance(value, PayUnit):
            return value
        
        if isinstance(value, str):
            value_lower = value.lower().strip()
            matches = [v for k, v in PAY_UNIT_MAPPING.items() if k in value_lower]
            
            if len(matches) == 1:
                return matches[0]
            elif len(matches) > 1:
                return min(matches, key=lambda x: PAY_UNIT_ORDER[x])
            else:
                return PayUnit.not_specified
        
        return PayUnit.not_specified
        # raise ValueError(f"Invalid type for pay unit: {type(value)}")

    entry_level: Optional[EntryLevelOption] = Field(
        default=EntryLevelOption.NOT_SPECIFIED,
        description=(
            "Return 'TRUE' if the position requires 3 or fewer years of experience (e.g. 1, 1-3, 2-4), "
            "return 'FALSE' if it requires more (e.g. Four plus, 3-5, 3+, 7). "
            "If the job description does not provide specific information about the experience required, "
            "then return 'Not specified'."
        )
    )
    @field_validator("entry_level", mode="before")
    def validate_entry_level(cls, value):
        if value is None:
            return EntryLevelOption.NOT_SPECIFIED
            
        if isinstance(value, EntryLevelOption):
            return value
        
        return EntryLevelOption.NOT_SPECIFIED

    soc_occupation_code: Optional[str] = Field(
        default=None,
        description=(
            "Provide the most appropriate 6-digit Standard Occupational Classification Code for the job, "
            "formatted as two digits, a dash, and then four digits (e.g. '11-1111')."
        )
    )

    @field_validator("soc_occupation_code", mode="before")
    def validate_soc_occupation_code(cls, value):
        if isinstance(value, str):
            # Clean the input code
            cleaned = clean_soc_code(value)
            if len(cleaned) == 6:
                # Return the code formatted as XX-XXXX
                return f"{cleaned[:2]}-{cleaned[2:]}"
            else:
                return None
        elif isinstance(value, int):
            # Convert integer to a zero-padded 6-digit string
            s = str(value).zfill(6)
            return f"{s[:2]}-{s[2:]}"
        else:
            return None

    
    part_time: Optional[PartTimeOption] = Field(
        default=PartTimeOption.NOT_SPECIFIED,
        description=(
            "Return 'TRUE' if the position is explicitly listed as part-time or explicitly states a part-time schedule; "
            "return 'FALSE' if the position is explicitly listed as full-time or explicitly states a full-time schedule; "
            "otherwise, return 'Not specified' if no explicit information is available."
        )
    )
    @field_validator("part_time", mode="before")
    def validate_part_time(cls, value):
        if value is None:
            return PartTimeOption.NOT_SPECIFIED
            
        if isinstance(value, PartTimeOption):
            return value
        
        return PartTimeOption.NOT_SPECIFIED

    remote: Optional[RemoteOption] = Field(
    default=RemoteOption.not_specified,
    description=(
        "Return 'In-person' only if the job description explicitly states in-person work or if job responsibilities "
        "indicate in-person activities with a specific location (i.e. city, address, or office location) provided. " 
        "Return 'Hybrid', 'Fully remote', or 'Remote with location restrictions' only if the job description explicitly states that the position "
        "is a hybrid role, fully remote role, or a remote role with location restrictions. Otherwise, return 'Not specified'."
    )
    )
    @field_validator("remote", mode="before")
    def validate_remote(cls, value):
        if value is None:
            return RemoteOption.not_specified
            
        if isinstance(value, RemoteOption):
            return value
        
        return RemoteOption.not_specified


class ExtractBreakoutSchema(BaseModel):
    """
    Pydantic model for information to be extracted from the job description in JSON format.
    """
    
    model_config = ConfigDict(
        extra="ignore",
        title="ExtractBreakoutSchema",
        description=(
            "This schema represents all fields to extract from the job description."
        )
    )

    job_title: Optional[str] = Field(
        default=None,
        description="Return the job title."
    )
    details: Optional[List[str]] = Field(
        default_factory=list,
        description="Return a list of all duties and responsibilities associated with the job. Include all information."
    )
    required_preferred: Optional[RequiredPreferredBreakout] = Field(
        default_factory=dict,
        description="Return the required/preferred education levels, major, experience, and qualifications."
        "For Education Fields: Extract only explicitly mentioned degrees and training/vocational programs. Do not infer based on occupation, tasks, or related credentials/certifications. Categorize whether a degree type is Required, Preferred/Can be substituted with experience, or Not mentioned."
    )
    benefits: Optional[List[str]] = Field(
        default=None,
        description="Return a list of the benefits offered."
    )
    pay_range: Optional[List[Optional[float]]] = Field(
        default_factory=list,
        description="""Return a list with ONLY the minimum and maximum USD pay range of the position as floating point numbers, formatted with no commas or dollar signs, if this information exists in the job description.
        
If multiple pay ranges appear in the job description, use the minimum and maximum across ALL pay ranges.

If the median or average pay appears in the job description, please only return the minimum and maximum values available.

If only one value for the pay range appears in the job description, please return that value twice as the minimum and maximum.
"""
    )
    @field_validator("pay_range", mode="before")
    def clean_pay_range(cls, value):
        if value is None:
            return value
        if isinstance(value, list):
            cleaned_values = []
            for item in value:
                if item is None:
                    cleaned_values.append(None)
                elif isinstance(item, str):
                    cleaned_item = re.sub(r"[^\d.]", "", item)
                    if cleaned_item:
                        try:
                            cleaned_values.append(float(cleaned_item))
                        except ValueError:
                            raise ValueError(f"Invalid value in pay_range: {item}")
                    else:
                        raise ValueError(f"Invalid value in pay_range: {item}")
                elif isinstance(item, (int, float)):
                    cleaned_values.append(float(item))
                else:
                    raise ValueError(f"Unexpected type in pay_range: {type(item).__name__}")
            return cleaned_values
        return value
    
    pay_unit: Optional[PayUnit] = Field(default=PayUnit.not_specified, description="Return the best pay per unit value from the set ('annual', 'monthly', 'weekly', 'daily', 'hourly', 'other', and 'not specified'). If no EXPLICIT MENTION of the pay_unit exists, code as 'not specified'.")

    @field_validator("pay_unit", mode="before")
    def validate_pay_unit(cls, value):
        if value is None:
            return PayUnit.not_specified
            
        if isinstance(value, PayUnit):
            return value
        
        if isinstance(value, str):
            value_lower = value.lower().strip()
            matches = [v for k, v in PAY_UNIT_MAPPING.items() if k in value_lower]
            
            if len(matches) == 1:
                return matches[0]
            elif len(matches) > 1:
                return min(matches, key=lambda x: PAY_UNIT_ORDER[x])
            else:
                return PayUnit.not_specified
        
        return PayUnit.not_specified
        # raise ValueError(f"Invalid type for pay unit: {type(value)}")

    entry_level_up_to_3_years_experience: Optional[EntryLevelOption] = Field(
        default=EntryLevelOption.NOT_SPECIFIED,
        description=(
            "- Return 'TRUE' if the job requires 3 or fewer years of experience (including 1 year, 1-3 years, 2-4 years). \n"
            "- Return 'FALSE' if the job requires more than three years of experience (including Four plus years, 3-5 years, 3+ years, 7 years). \n"
            "- If the job posting does not provide specific information about the experience required, "
            "then return 'Not specified'. Do not make assumptions based on the job responsibilities."
        )
    )
    @field_validator("entry_level_up_to_3_years_experience", mode="before")
    def validate_entry_level(cls, value):
        if value.lower() == 'true':
            return EntryLevelOption.TRUE
        elif value.lower() == 'false':
            return EntryLevelOption.FALSE
        else:    
            return EntryLevelOption.NOT_SPECIFIED

    soc_occupation_code: Optional[str] = Field(
        default=None,
        description=(
            "Provide the most appropriate 6-digit Standard Occupational Classification Code for the job, "
            "formatted as two digits, a dash, and then four digits (e.g. '11-1111')."
        )
    )

    @field_validator("soc_occupation_code", mode="before")
    def validate_soc_occupation_code(cls, value):
        if isinstance(value, str):
            # Clean the input code
            cleaned = clean_soc_code(value)
            if len(cleaned) == 6:
                # Return the code formatted as XX-XXXX
                return f"{cleaned[:2]}-{cleaned[2:]}"
            else:
                return None
        elif isinstance(value, int):
            # Convert integer to a zero-padded 6-digit string
            s = str(value).zfill(6)
            return f"{s[:2]}-{s[2:]}"
        else:
            return None

    
    part_time: Optional[PartTimeOption] = Field(
        default=PartTimeOption.NOT_SPECIFIED,
        description=(
            "- Return 'TRUE' if the position is listed as part-time or states a part-time schedule. \n"
            "- Return 'FALSE' if the position is listed as full-time or states a full-time schedule. \n"
            "- Return 'Not specified' if no explicit information is available."
        )
    )
    @field_validator("part_time", mode="before")
    def validate_part_time(cls, value):
        if value.lower() == 'true':
            return PartTimeOption.TRUE
        elif value.lower() == 'false':
            return PartTimeOption.FALSE
        else:    
            return PartTimeOption.NOT_SPECIFIED

    remote: Optional[RemoteOption] = Field(
    default=RemoteOption.not_specified,
    description=(
        "Return 'In-person' only if the job posting explicitly states in-person work or if job responsibilities "
        "indicate in-person activities with a specific location (i.e. city, address, or office location) provided. " 
        "Return 'Hybrid', 'Fully remote', or 'Remote with location restrictions' only if the job description explicitly states that the position "
        "is hybrid, remote, or a remote role with location restrictions. Otherwise, return 'Not specified'."
    )
    )
    @field_validator("remote", mode="before")
    def validate_remote(cls, value):
        if value.lower() in ["in-person","in person"]:
            return RemoteOption.in_person
        elif value.lower() in ["hybrid"]:
            return RemoteOption.hybrid
        elif value.lower() in ["remote with location restrictions"] or "location rest" in value.lower():
            return RemoteOption.remote_with_location_restrictions
        elif value.lower() in ["fully remote"]:
            return RemoteOption.fully_remote
        else:    
            return RemoteOption.not_specified

class ExtractEducationSchema(BaseModel):
    """
    Pydantic model for educational information to be extracted from the job description in JSON format.
    """
    
    model_config = ConfigDict(
        extra="ignore",
        title="ExtractEducationSchema",
        description=(
            "This schema represents all educational fields to extract from the job description."
        )
    )
    required: Optional[RequiredPreferredEducationMajor] = Field(
        default_factory=dict,
        description="Return the required education and major from the job description in the provided format."
    )
    preferred: Optional[RequiredPreferredEducationMajor] = Field(
        default_factory=dict,
        description="Return the preferred education and major from the job description in the provided format."
    )

class ExtractQualificationsSchema(BaseModel):
    """
    Pydantic model for qualifications to be extracted from the job description in JSON format.
    """
    
    model_config = ConfigDict(
        extra="ignore",
        title="ExtractQualificationsSchema",
        description=(
            "This schema represents all qualifications and experience-related information to extract from the job description."
        )
    )

    required: Optional[RequiredPreferredExperienceQualifications] = Field(
        default_factory=dict,
        description="Return the required experience and qualifications for the job from the job description."
    )
    preferred: Optional[RequiredPreferredExperienceQualifications] = Field(
        default_factory=dict,
        description="Return the preferred experience and qualifications for the job from the job description."
    )
    entry_level: Optional[EntryLevelOption] = Field(
        default=EntryLevelOption.NOT_SPECIFIED,
        description=(
            "Return 'TRUE' if the position requires 3 or fewer years of experience (e.g. 1, 1-3, 2-4), "
            "return 'FALSE' if it requires more (e.g. Four plus, 3-5, 3+, 7). "
            "If the job description does not provide specific information about the experience required, "
            "then return 'Not specified'."
        )
    )
    @field_validator("entry_level", mode="before")
    def validate_entry_level(cls, value):
        if value is None:
            return EntryLevelOption.NOT_SPECIFIED
            
        if isinstance(value, EntryLevelOption):
            return value
        
        return EntryLevelOption.NOT_SPECIFIED

class ExtractDetailsSchema(BaseModel):
    """
    Pydantic model for job details to be extracted from the job description in JSON format.
    """
    
    model_config = ConfigDict(
        extra="ignore",
        title="ExtractDetailsSchema",
        description=(
            "This schema represents all job details to extract from the job description."
        )
    )
    job_title: Optional[str] = Field(
        default=None,
        description="Return the job title."
    )
    details: Optional[List[str]] = Field(
        default_factory=list,
        description="Return a list of all duties and responsibilities associated with the job. Include all information."
    )
    benefits: Optional[List[str]] = Field(
        default=None,
        description="Return a list of the benefits offered."
    )
    pay_range: Optional[List[Optional[float]]] = Field(
        default_factory=list,
        description="""Return a list with ONLY the minimum and maximum USD pay range of the position as floating point numbers, formatted with no commas or dollar signs, if this information exists in the job description.
        
If multiple pay ranges appear in the job description, use the minimum and maximum across ALL pay ranges.

If the median or average pay appears in the job description, please only return the minimum and maximum values available.

If only one value for the pay range appears in the job description, please return that value twice as the minimum and maximum.
"""
    )
    @field_validator("pay_range", mode="before")
    def clean_pay_range(cls, value):
        if value is None:
            return value
        if isinstance(value, list):
            cleaned_values = []
            for item in value:
                if item is None:
                    cleaned_values.append(None)
                elif isinstance(item, str):
                    cleaned_item = re.sub(r"[^\d.]", "", item)
                    if cleaned_item:
                        try:
                            cleaned_values.append(float(cleaned_item))
                        except ValueError:
                            raise ValueError(f"Invalid value in pay_range: {item}")
                    else:
                        raise ValueError(f"Invalid value in pay_range: {item}")
                elif isinstance(item, (int, float)):
                    cleaned_values.append(float(item))
                else:
                    raise ValueError(f"Unexpected type in pay_range: {type(item).__name__}")
            return cleaned_values
        return value
    
    pay_unit: Optional[PayUnit] = Field(default=PayUnit.not_specified, description="Return the best pay per unit value from the set ('annual', 'monthly', 'weekly', 'daily', 'hourly', 'other', and 'not specified'). If no EXPLICIT MENTION of the pay_unit exists, code as 'not specified'.")

    @field_validator("pay_unit", mode="before")
    def validate_pay_unit(cls, value):
        if value is None:
            return PayUnit.not_specified
            
        if isinstance(value, PayUnit):
            return value
        
        if isinstance(value, str):
            value_lower = value.lower().strip()
            matches = [v for k, v in PAY_UNIT_MAPPING.items() if k in value_lower]
            
            if len(matches) == 1:
                return matches[0]
            elif len(matches) > 1:
                return min(matches, key=lambda x: PAY_UNIT_ORDER[x])
            else:
                return PayUnit.not_specified
        
        return PayUnit.not_specified

    entry_level: Optional[EntryLevelOption] = Field(
        default=EntryLevelOption.NOT_SPECIFIED,
        description=(
            "Return 'TRUE' if the position requires 3 or fewer years of experience (e.g. 1, 1-3, 2-4), "
            "return 'FALSE' if it requires more (e.g. Four plus, 3-5, 3+, 7). "
            "If the job description does not provide specific information about the experience required, "
            "then return 'Not specified'."
        )
    )
    @field_validator("entry_level", mode="before")
    def validate_entry_level(cls, value):
        if value is None:
            return EntryLevelOption.NOT_SPECIFIED
            
        if isinstance(value, EntryLevelOption):
            return value
        
        return EntryLevelOption.NOT_SPECIFIED

    soc_occupation_code: Optional[str] = Field(
        default=None,
        description=(
            "Provide the most appropriate 6-digit Standard Occupational Classification Code for the job, "
            "formatted as two digits, a dash, and then four digits (e.g. '11-1111')."
        )
    )

    @field_validator("soc_occupation_code", mode="before")
    def validate_soc_occupation_code(cls, value):
        if isinstance(value, str):
            # Clean the input code
            cleaned = clean_soc_code(value)
            if len(cleaned) == 6:
                # Return the code formatted as XX-XXXX
                return f"{cleaned[:2]}-{cleaned[2:]}"
            else:
                return None
        elif isinstance(value, int):
            # Convert integer to a zero-padded 6-digit string
            s = str(value).zfill(6)
            return f"{s[:2]}-{s[2:]}"
        else:
            return None
    
    part_time: Optional[PartTimeOption] = Field(
        default=PartTimeOption.NOT_SPECIFIED,
        description=(
            "Return 'TRUE' if the position is explicitly listed as part-time or explicitly states a part-time schedule; "
            "return 'FALSE' if the position is explicitly listed as full-time or explicitly states a full-time schedule; "
            "otherwise, return 'Not specified' if no explicit information is available."
        )
    )
    @field_validator("part_time", mode="before")
    def validate_part_time(cls, value):
        if value is None:
            return PartTimeOption.NOT_SPECIFIED
            
        if isinstance(value, PartTimeOption):
            return value
        
        return PartTimeOption.NOT_SPECIFIED

    remote: Optional[RemoteOption] = Field(
    default=RemoteOption.not_specified,
    description=(
        "Return 'In-person' only if the job description explicitly states in-person work or if job responsibilities "
        "indicate in-person activities with a specific location (i.e. city, address, or office location) provided. " 
        "Return 'Hybrid', 'Fully remote', or 'Remote with location restrictions' only if the job description explicitly states that the position "
        "is a hybrid role, fully remote role, or a remote role with location restrictions. Otherwise, return 'Not specified'."
    )
    )
    @field_validator("remote", mode="before")
    def validate_remote(cls, value):
        if value is None:
            return RemoteOption.not_specified
            
        if isinstance(value, RemoteOption):
            return value
        
        return RemoteOption.not_specified


class SkillsSchema(RootModel[List[str]]):
    """
    Pydantic JSON model for the skills to be extracted from the job description.
    """
    model_config = ConfigDict(
        title="SkillsSchema",
        description="Return a JSON list of skills from the provided taxonomy."
    )
