from app.domain.jd_models import JobDescriptionSchema
from app.services.llm.extraction import _strip_people_terms


def test_people_terms_stripped_from_competencies():
    jd = JobDescriptionSchema(
        role_title="Dev",
        key_competencies=[
            "microservices",
            "AI Researchers",
            "Forward-Deployed Engineers (FDEs)",
            "business SMEs",
            "Cross-Functional Teams",
            "DevOps practices",
        ],
    )
    _strip_people_terms(jd)
    assert jd.key_competencies == ["microservices", "DevOps practices"]
