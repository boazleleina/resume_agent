import pytest
from app.domain.resume_models import CanonicalResume, ResumeSkills
from app.domain.jd_models import JobDescriptionSchema
from app.services.llm.matching import compute_skill_match

def test_compute_skill_match_basic():
    # Setup mock resume
    resume = CanonicalResume(
        raw_text="I know Python, Postgres, and React.",
        skills=ResumeSkills(all_terms=["Python", "Postgres", "React"])
    )
    
    # Setup mock JD
    jd = JobDescriptionSchema(
        role_title="Dev",
        core_requirements=["Python", "PostgreSQL"],  # Postgres != PostgreSQL without normalization
        tech_stack=["React", "NodeJS"]
    )
    
    match = compute_skill_match(resume, jd)
    
    # Postgres and PostgreSQL should match due to normalization
    assert "postgresql" in match["matched"]
    assert "python" in match["matched"]
    assert "react" in match["matched"]
    
    # Missing stack
    assert "node.js" in match["missing_tech"]
    
    # Percentages
    # Total JD skills: python, postgresql, react, node.js (4)
    # Matched: python, postgresql, react (3)
    # 3/4 = 75%
    assert match["overall_match_pct"] == 75.0

def test_compute_skill_match_empty():
    resume = CanonicalResume(raw_text="Empty", skills=ResumeSkills(all_terms=[]))
    jd = JobDescriptionSchema(role_title="Job", core_requirements=["Python"])
    
    match = compute_skill_match(resume, jd)
    
    assert match["overall_match_pct"] == 0.0
    assert "python" in match["missing_required"]
