import pytest
from app.domain.jd_models import JobDescriptionSchema

def test_jd_schema_initializes_empty_arrays_safely():
    # If the LLM doesn't find a company name or any nice-to-haves, it should safely initialize
    jd = JobDescriptionSchema()
    
    assert jd.company_name is None
    assert jd.role_title is None
    
    # Assert missing fields safely initialize to empty lists rather than None
    assert jd.tech_stack == []
    assert jd.core_responsibilities == []
    assert jd.must_have_requirements == []
    assert jd.nice_to_have_requirements == []

def test_jd_schema_instantiation():
    jd = JobDescriptionSchema(
        company_name="JITX",
        role_title="Senior Software Engineer",
        must_have_requirements=["Strong algorithmic problem-solving skills", "Mathematical maturity"],
        tech_stack=["Python", "C++", "TypeScript", "React", "Ansys HFSS"]
    )
    
    assert jd.company_name == "JITX"
    assert len(jd.tech_stack) == 5
    assert jd.tech_stack[0] == "Python"
    # Even though we didn't pass it, nice_to_have safely defaults
    assert len(jd.nice_to_have_requirements) == 0
