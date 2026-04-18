import pytest
from pydantic import ValidationError
from app.domain.resume_models import CanonicalResume

def test_new_grad_resume_defaults():
    # Only supply raw text, simulating an empty parsed result
    resume = CanonicalResume(raw_text="Empty resume with no sections")
    
    # Assert missing fields safely initialized to empty lists rather than None
    assert resume.experience == []
    assert resume.education == []
    assert resume.projects == []
    assert resume.certifications == []
    assert resume.skills.all_terms == []
    assert resume.metrics_found == []
    
    # Root strings initialize carefully
    assert resume.raw_text == "Empty resume with no sections"
    assert resume.summary is None
    
def test_pydantic_schema_exports_verbatim_rules():
    schema = CanonicalResume.model_json_schema()
    
    # Let's ensure our verbatim instructions propagated through to the actual JSON schema
    experience_schema = schema['$defs']['ExperienceInfo']
    assert "VERBATIM" in experience_schema['properties']['title']['description']
    assert "MUTABLE" in experience_schema['properties']['bullets']['description']
    
def test_missing_raw_text_fails():
    with pytest.raises(ValidationError):
        # raw_text is strictly required to enforce grounding
        CanonicalResume()

def test_full_instantiation():
    resume = CanonicalResume(
        raw_text="Extracted text",
        metrics_found=["50%"],
        experience=[{"title": "Engineer", "company": "Google", "bullets": ["Built stuff"]}]
    )
    assert len(resume.experience) == 1
    assert resume.experience[0].title == "Engineer"
