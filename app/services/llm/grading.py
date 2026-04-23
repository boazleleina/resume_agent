import json
import logging

from pydantic import ValidationError

from app.domain.grading_models import GradingResult
from app.domain.resume_models import CanonicalResume

from .cache import cache_get, cache_key, cache_set
from .exceptions import LLMServiceException
from .ollama_client import call_ollama
from .prompts import GRADING_SYSTEM

logger = logging.getLogger(__name__)


async def grade_and_recommend(
    resume: CanonicalResume,
    clean_jd: str,
    skill_match: dict,
) -> GradingResult:
    """Grade resume/JD match and propose edits. think=True (deep reasoning)."""
    key = cache_key(
        "grade",
        clean_jd,
        resume.model_dump_json(),
        json.dumps(skill_match, sort_keys=True),
    )
    if cached := cache_get(key):
        return cached

    resume_context = _build_resume_context(resume)
    user_prompt = _build_grading_user_prompt(resume_context, clean_jd, skill_match)
    llm_output = await call_ollama(GRADING_SYSTEM, user_prompt, think=True)

    try:
        grading = GradingResult.model_validate_json(llm_output)
    except json.JSONDecodeError:
        raise LLMServiceException(f"LLM returned invalid JSON for grading: {llm_output[:500]}")
    except ValidationError as e:
        raise LLMServiceException(f"Grading schema validation failed: {e.errors()}")

    _enforce_edit_traceability(grading, resume)
    cache_set(key, grading)
    return grading


def _build_resume_context(resume: CanonicalResume) -> dict:
    """Structured resume view for the grading prompt — excludes raw_text to save tokens."""
    return {
        "name": resume.contact.name,
        "summary": resume.summary,
        "skills": resume.skills.all_terms if resume.skills else [],
        "experience": [
            {"title": e.title, "company": e.company, "bullets": e.bullets}
            for e in resume.experience
        ],
        "education": [
            {"degree": e.degree, "institution": e.institution, "gpa": e.gpa}
            for e in resume.education
        ],
        "projects": [
            {"name": p.name, "bullets": p.bullets}
            for p in resume.projects
        ],
        "certifications": resume.certifications,
        "metrics_found": resume.metrics_found,
    }


def _build_grading_user_prompt(resume_context: dict, clean_jd: str, skill_match: dict) -> str:
    return f"""Resume:
{json.dumps(resume_context, indent=2)}

Job Description:
{clean_jd}

Pre-computed skill match:
- Overall match: {skill_match['overall_match_pct']}%
- Required skills match: {skill_match['required_match_pct']}%
- Tech stack match: {skill_match['tech_match_pct']}%
- Matched skills: {skill_match['matched']}
- Missing required: {skill_match['missing_required']}
- Missing tech stack: {skill_match['missing_tech']}
- Missing preferred: {skill_match['missing_preferred']}

Analyze and grade this candidate."""


def _enforce_edit_traceability(grading: GradingResult, resume: CanonicalResume) -> None:
    """
    Downgrades edits tagged 'supported by source text' when no evidence
    for them appears in the resume. Mutates grading in place.
    """
    resume_lower = resume.raw_text.lower() if resume.raw_text else ""
    if not resume_lower:
        return

    for edit in grading.top_3_edits:
        if edit.traceability != "supported by source text":
            continue
        if not _suggestion_has_evidence(edit.suggestion.lower(), resume_lower):
            logger.warning(
                f"Traceability override: '{edit.suggestion[:80]}...' "
                f"tagged as 'supported by source text' but no evidence found in resume."
            )
            edit.traceability = "missing but unverifiable, ask user to supply"


def _suggestion_has_evidence(suggestion: str, resume_text: str) -> bool:
    """
    Looks for any 3+ word phrase from the suggestion in the resume.
    Crude but zero-cost. Upgrade to evidence-field-on-model when the
    schema supports it (see LLM_SCHEMA_TODO).
    """
    words = suggestion.split()
    for i in range(len(words) - 2):
        phrase = " ".join(words[i:i + 3])
        if len(phrase) < 10:
            continue
        if phrase in resume_text:
            return True
    return False