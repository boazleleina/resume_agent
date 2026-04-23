from pydantic import BaseModel, Field
from typing import List


class ResumeEdit(BaseModel):
    section: str = Field(description="Which resume section to edit.")
    suggestion: str = Field(description="Specific actionable edit.")
    traceability: str = Field(
        description="One of: 'supported by source text' | 'formatting improvement' | "
                    "'generic strengthening suggestion' | 'missing but unverifiable, ask user to supply' | "
                    "'already present in resume — rephrase for emphasis'"
    )


class GradingResult(BaseModel):
    match_score: int = Field(ge=0, le=100, description="How well the candidate fits this specific role, 0-100.")
    strongest_angle: str = Field(description="1-2 sentence explanation of the candidate's best selling point for this role.")
    honest_gaps: List[str] = Field(default_factory=list, description="Real weaknesses, not vague filler.")
    top_3_edits: List[ResumeEdit] = Field(default_factory=list, description="Exactly 3 actionable resume edits.")
