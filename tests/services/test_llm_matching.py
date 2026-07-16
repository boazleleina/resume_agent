import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domain.resume_models import CanonicalResume, ResumeSkills
from app.domain.jd_models import JobDescriptionSchema
from app.services.llm.matching import compute_skill_match


def _mock_client(verdicts):
    """Patch matching.get_client so prompt_model returns the given verdicts JSON."""
    client = MagicMock()
    client.prompt_model = AsyncMock(return_value=json.dumps({"verdicts": verdicts}))
    return patch("app.services.llm.matching.get_client", return_value=client)


def _no_cache():
    """Disable the shelve cache so each test's LLM stub is actually exercised."""
    return patch.multiple(
        "app.services.llm.matching",
        cache_get=MagicMock(return_value=None),
        cache_set=MagicMock(),
    )


@pytest.mark.anyio
async def test_compute_skill_match_basic():
    resume = CanonicalResume(
        raw_text="I know Python, Postgres, and React.",
        skills=ResumeSkills(all_terms=["Python", "Postgres", "React"]),
    )
    jd = JobDescriptionSchema(
        role_title="Dev",
        core_requirements=["Python", "PostgreSQL"],  # Postgres≈PostgreSQL via fuzzy
        tech_stack=["React", "NodeJS"],
    )

    with _no_cache(), _mock_client([]):  # LLM finds no extra matches
        match = await compute_skill_match(resume, jd)

    assert "postgresql" in match["matched"]  # fuzzy match, alias removed
    assert "python" in match["matched"]
    assert "react" in match["matched"]

    assert "nodejs" in match["missing_tech"]  # no resume skill covers it

    # Total JD skills: python, postgresql, react, nodejs (4); matched 3 → 75%
    assert match["overall_match_pct"] == 75.0


@pytest.mark.anyio
async def test_compute_skill_match_empty():
    resume = CanonicalResume(raw_text="Empty", skills=ResumeSkills(all_terms=[]))
    jd = JobDescriptionSchema(role_title="Job", core_requirements=["Python"])

    # Empty resume skills → Layer 3 short-circuits, client never called
    with _no_cache(), _mock_client([]):
        match = await compute_skill_match(resume, jd)

    assert match["overall_match_pct"] == 0.0
    assert "python" in match["missing_required"]


@pytest.mark.anyio
async def test_semantic_match_covers_missing_requirement():
    resume = CanonicalResume(
        raw_text="Experienced in client relations.",
        skills=ResumeSkills(all_terms=["client relations"]),
    )
    jd = JobDescriptionSchema(
        role_title="Support",
        core_requirements=["customer service"],  # no string match
    )

    llm_matches = [{"jd_term": "customer service",
                    "covered_by": "client relations",
                    "reason": "equivalent skill"}]

    with _no_cache(), _mock_client(llm_matches):
        match = await compute_skill_match(resume, jd)

    assert "customer service" in match["semantic_matched"]
    assert "customer service" not in match["missing_required"]
    assert match["semantic_match_details"]["customer service"]["covered_by"] == "client relations"


@pytest.mark.anyio
async def test_semantic_match_discards_hallucinated_terms():
    resume = CanonicalResume(
        raw_text="Java developer.",
        skills=ResumeSkills(all_terms=["Java"]),
    )
    jd = JobDescriptionSchema(role_title="Dev", core_requirements=["JavaScript"])

    # LLM returns a jd_term/covered_by not present in the inputs → must be discarded
    llm_matches = [
        {"jd_term": "JavaScript", "covered_by": "TypeScript", "reason": "hallucinated"},
        {"jd_term": "Golang", "covered_by": "Java", "reason": "not in jd_terms"},
    ]

    with _no_cache(), _mock_client(llm_matches):
        match = await compute_skill_match(resume, jd)

    assert match["semantic_matched"] == []
    assert "javascript" in match["missing_required"]


@pytest.mark.anyio
async def test_semantic_match_degrades_on_llm_failure():
    resume = CanonicalResume(
        raw_text="Python developer.",
        skills=ResumeSkills(all_terms=["Python"]),
    )
    jd = JobDescriptionSchema(role_title="Dev", core_requirements=["Rust"])

    client = MagicMock()
    client.prompt_model = AsyncMock(side_effect=RuntimeError("ollama down"))

    with _no_cache(), patch("app.services.llm.matching.get_client", return_value=client):
        match = await compute_skill_match(resume, jd)

    # Failure → fuzzy-only result, no crash
    assert match["semantic_matched"] == []
    assert "rust" in match["missing_required"]


@pytest.mark.anyio
async def test_semantic_match_uses_cache():
    resume = CanonicalResume(
        raw_text="Experienced in client relations.",
        skills=ResumeSkills(all_terms=["client relations"]),
    )
    jd = JobDescriptionSchema(role_title="Support", core_requirements=["customer service"])

    cached = {"customer service": {"covered_by": "client relations", "reason": "cached"}}
    client = MagicMock()
    client.prompt_model = AsyncMock()

    with patch("app.services.llm.matching.cache_get", return_value=cached), \
         patch("app.services.llm.matching.get_client", return_value=client):
        match = await compute_skill_match(resume, jd)

    client.prompt_model.assert_not_called()  # cache hit → no LLM call
    assert "customer service" in match["semantic_matched"]


@pytest.mark.anyio
async def test_key_competencies_are_matched():
    resume = CanonicalResume(
        raw_text="Built microservices with CI/CD pipelines.",
        skills=ResumeSkills(all_terms=["microservices", "CI/CD"]),
    )
    jd = JobDescriptionSchema(
        role_title="Backend",
        tech_stack=["Python"],
        key_competencies=["microservices", "DevOps", "distributed computing"],
    )

    llm_matches = [{"jd_term": "devops", "covered_by": "ci/cd", "reason": "CI/CD is a DevOps practice"}]

    with _no_cache(), _mock_client(llm_matches):
        match = await compute_skill_match(resume, jd)

    assert "microservices" in match["matched"]            # exact
    assert "devops" in match["semantic_matched"]           # LLM implication
    assert "distributed computing" in match["missing_competencies"]
    assert "python" in match["missing_tech"]
    # competencies pct: 2 of 3 matched
    assert match["competencies_match_pct"] == 66.7


@pytest.mark.anyio
async def test_competencies_deduped_from_other_buckets():
    resume = CanonicalResume(
        raw_text="Python dev.",
        skills=ResumeSkills(all_terms=["Python"]),
    )
    jd = JobDescriptionSchema(
        role_title="Dev",
        tech_stack=["Python"],
        key_competencies=["Python", "observability"],  # Python duplicates tech_stack
    )

    with _no_cache(), _mock_client([]):
        match = await compute_skill_match(resume, jd)

    # Duplicate must not inflate totals: JD terms = python, observability (2), matched 1 → 50%
    assert match["jd_competencies"] == ["observability"]
    assert match["overall_match_pct"] == 50.0


@pytest.mark.anyio
@pytest.mark.skipif(
    not os.environ.get("RUN_SLOW"),
    reason="live Ollama integration test; run with RUN_SLOW=1",
)
async def test_semantic_match_live_non_technical():
    """Real prompt against local Ollama: non-technical equivalence + negative control."""
    from app.services.llm.matching import _semantic_match

    result = await _semantic_match(
        jd_terms={"customer service", "javascript"},
        resume_skills={"client relations", "java"},
    )

    assert "customer service" in result  # equivalence must match
    assert "javascript" not in result    # Java must NOT cover JavaScript
