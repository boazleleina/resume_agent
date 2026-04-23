"""
Step 1 of the pipeline: fast structured extraction.

Runs Qwen3 with think=False for speed. The LLM reads raw text (resume
or JD) and returns JSON matching our Pydantic schemas. Structural
VERBATIM enforcement happens in the schema itself (see resume_models),
so we rely on Pydantic validation to catch hallucinated fields.
"""
import json
import logging

from pydantic import ValidationError

from app.domain.jd_models import JobDescriptionSchema
from app.domain.resume_models import CanonicalResume

from .cache import cache_get, cache_key, cache_set
from .exceptions import LLMServiceException
from .factory import get_client
from .prompts import JD_EXTRACTION_SYSTEM, RESUME_EXTRACTION_SYSTEM

logger = logging.getLogger(__name__)


async def extract_resume_facts(raw_text: str) -> CanonicalResume:
    """
    Extracts structured resume data from raw text.
    
    raw_text is injected into the model after LLM parsing rather than
    asking the LLM to echo it — saves ~1000 tokens per call. VERBATIM
    enforcement is handled by CanonicalResume's model_validator.
    """
    key = cache_key("resume", raw_text)
    if cached := cache_get(key):
        return cached

    user_prompt = f"Parse this resume:\n\n{raw_text}"
    llm_output = await get_client().prompt_model(RESUME_EXTRACTION_SYSTEM, user_prompt, think=False)

    try:
        parsed = json.loads(llm_output)
    except json.JSONDecodeError:
        raise LLMServiceException(f"LLM returned invalid JSON for resume: {llm_output[:500]}")

    parsed["raw_text"] = raw_text

    try:
        resume = CanonicalResume.model_validate(parsed)
    except ValidationError as e:
        raise LLMServiceException(f"Resume schema validation failed: {e.errors()}")

    cache_set(key, resume)
    return resume


async def extract_jd_facts(clean_jd: str) -> JobDescriptionSchema:
    """
    Extracts structured job description data from cleaned JD text.
    
    Runs a hallucination guard: every extracted skill/requirement must
    appear (case-insensitive) in the source text. Invented items are
    stripped and logged, not raised — the pipeline continues with clean data.
    """
    key = cache_key("jd", clean_jd)
    if cached := cache_get(key):
        return cached

    user_prompt = f"Parse this job description:\n\n{clean_jd}"
    llm_output = await get_client().prompt_model(JD_EXTRACTION_SYSTEM, user_prompt, think=False)

    try:
        jd = JobDescriptionSchema.model_validate_json(llm_output)
    except json.JSONDecodeError:
        raise LLMServiceException(f"LLM returned invalid JSON for JD: {llm_output[:500]}")
    except ValidationError as e:
        raise LLMServiceException(f"JD schema validation failed: {e.errors()}")

    _apply_jd_hallucination_guard(jd, clean_jd)
    cache_set(key, jd)
    return jd


def _apply_jd_hallucination_guard(jd: JobDescriptionSchema, source_text: str) -> None:
    """Mutates jd in place, stripping any extracted items not in source."""
    source_lower = source_text.lower()

    for field_name in ("tech_stack", "core_requirements", "preferred_qualifications"):
        items = getattr(jd, field_name)
        kept = [s for s in items if s.lower() in source_lower]
        dropped = [s for s in items if s.lower() not in source_lower]
        if dropped:
            logger.warning(
                f"Hallucination guard ({field_name}): "
                f"stripped {len(dropped)} of {len(items)} items: {dropped}"
            )
        setattr(jd, field_name, kept)