from pydantic import BaseModel, Field
from typing import List, Optional

EXTRACT_DESC = "EXTRACT: Pull exactly as stated from the source text. Do not invent info. If missing, leave as null/empty array."

class JobDescriptionSchema(BaseModel):
    # Core Metadata
    company_name: Optional[str] = Field(default=None, description=EXTRACT_DESC)
    role_title: Optional[str] = Field(default=None, description=EXTRACT_DESC)
    
    # Responsibilities
    core_responsibilities: List[str] = Field(
        default_factory=list, 
        description="A list of bullet points explaining what the candidate will actually do day-to-day. EXTRACT verbatim if possible."
    )
    
    # Requirements
    core_requirements: List[str] = Field(
        default_factory=list, 
        description="The primary qualifications for the job. This includes 'Must Haves', 'Basic Qualifications', or 'We're looking for people with...'."
    )
    preferred_qualifications: List[str] = Field(
        default_factory=list, 
        description="Optional skills, 'bonus' qualifications, or 'Nice-to-haves'."
    )
    
    # Technology Mapping
    tech_stack: List[str] = Field(
        default_factory=list, 
        description="A flat list of explicit tools, software, algorithms, or coding languages (e.g., Python, Ansys HFSS, React) mentioned anywhere in the posting."
    )
