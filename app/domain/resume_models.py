from pydantic import BaseModel, Field
from typing import List, Optional

VERBATIM_DESC = "VERBATIM: Must copy exactly from source text. If no information is found naturally, leave as null. Do not invent or summarize."
MUTABLE_DESC = "MUTABLE: Can be modified or formulated by the agent."

class ContactInfo(BaseModel):
    name: Optional[str] = Field(default=None, description=VERBATIM_DESC)
    email: Optional[str] = Field(default=None, description=VERBATIM_DESC)
    phone: Optional[str] = Field(default=None, description=VERBATIM_DESC)
    location: Optional[str] = Field(default=None, description=VERBATIM_DESC)
    links: List[str] = Field(default_factory=list, description=VERBATIM_DESC)

class ExperienceInfo(BaseModel):
    title: str = Field(description=VERBATIM_DESC)
    company: str = Field(description=VERBATIM_DESC)
    start_date: Optional[str] = Field(default=None, description=VERBATIM_DESC)
    end_date: Optional[str] = Field(default=None, description=VERBATIM_DESC)
    bullets: List[str] = Field(default_factory=list, description=MUTABLE_DESC)

class EducationInfo(BaseModel):
    degree: str = Field(description=VERBATIM_DESC)
    institution: str = Field(description=VERBATIM_DESC)
    graduation_date: Optional[str] = Field(default=None, description=VERBATIM_DESC)
    gpa: Optional[str] = Field(default=None, description=VERBATIM_DESC)

class ProjectInfo(BaseModel):
    name: str = Field(description=VERBATIM_DESC)
    description: Optional[str] = Field(default=None, description=MUTABLE_DESC)
    link: Optional[str] = Field(default=None, description=VERBATIM_DESC)
    bullets: List[str] = Field(default_factory=list, description=MUTABLE_DESC)

class ResumeSkills(BaseModel):
    all_terms: List[str] = Field(default_factory=list, description="Ground truth explicit skills extracted before patching.")

class CanonicalResume(BaseModel):
    # State tracking layers (our grounding anchor)
    raw_text: str = Field(description="The immutable raw string parsed from the document. The absolute ground truth.")
    metrics_found: List[str] = Field(default_factory=list, description="All numerical metrics and quantifiable outputs extracted naturally.")
    
    # Core mappings
    contact: ContactInfo = Field(default_factory=ContactInfo)
    summary: Optional[str] = Field(default=None, description=MUTABLE_DESC)
    experience: List[ExperienceInfo] = Field(default_factory=list)
    education: List[EducationInfo] = Field(default_factory=list)
    projects: List[ProjectInfo] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list, description=VERBATIM_DESC)
    skills: ResumeSkills = Field(default_factory=ResumeSkills)
