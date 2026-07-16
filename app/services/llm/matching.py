import json
import logging

from rapidfuzz import fuzz

from app.config import LLM_EXTRACTION_MODEL, LLM_MATCHING_THINK
from app.domain.resume_models import CanonicalResume
from app.domain.jd_models import JobDescriptionSchema
from .cache import cache_get, cache_key, cache_set
from .factory import get_client
from .prompts import SEMANTIC_MATCHING_SYSTEM
from .skill_aliases import expand_skill

logger = logging.getLogger(__name__)

FUZZY_THRESHOLD = 85  # token_sort_ratio score to count as a match
PROSE_WORD_THRESHOLD = 5  # requirements with more words than this are prose, not keywords


async def compute_skill_match(
    resume: CanonicalResume,
    jd: JobDescriptionSchema,
) -> dict:
    """
    Three-layer skill matching: exact → fuzzy → LLM semantic adjudication.

    Layer 3 sends JD terms still unmatched after exact+fuzzy, plus the full
    resume skill list, to the LLM to judge genuine equivalence/implication.
    Domain-agnostic — works for technical and non-technical resumes alike.
    It degrades to fuzzy-only on any LLM failure and validates every returned
    match against the inputs so hallucinated matches are impossible.

    Prose requirements (sentences) are separated from keyword requirements
    before matching and passed directly to the grader for qualitative reasoning.
    String matching on prose always produces 0% — the LLM handles it better.
    """
    resume_terms = resume.skills.all_terms if resume.skills and resume.skills.all_terms else []
    jd_req_terms = jd.core_requirements if jd.core_requirements else []
    jd_pref_terms = jd.preferred_qualifications if jd.preferred_qualifications else []
    jd_tech_terms = jd.tech_stack if jd.tech_stack else []
    jd_comp_terms = getattr(jd, "key_competencies", None) or []

    # Split prose reqs out before any matching
    keyword_req_terms, prose_req_terms = _split_prose(jd_req_terms)
    keyword_pref_terms, prose_pref_terms = _split_prose(jd_pref_terms)
    keyword_comp_terms, prose_comp_terms = _split_prose(jd_comp_terms)

    # Expand compounds and normalize
    resume_skills = {norm for s in resume_terms for norm in expand_skill(s)}
    jd_required = {norm for s in keyword_req_terms for norm in expand_skill(s)}
    jd_preferred = {norm for s in keyword_pref_terms for norm in expand_skill(s)}
    jd_tech = {norm for s in jd_tech_terms for norm in expand_skill(s)}
    jd_competencies = {norm for s in keyword_comp_terms for norm in expand_skill(s)}
    # Competencies extracted from prose may duplicate explicit requirements
    jd_competencies -= jd_required | jd_preferred | jd_tech

    all_jd_skills = jd_required | jd_preferred | jd_tech | jd_competencies

    # Layer 1: exact match
    exact_matched = resume_skills & all_jd_skills

    # Layer 2: fuzzy match on still-unmatched JD terms
    fuzzy_matched = _fuzzy_match(all_jd_skills - exact_matched, resume_skills)

    matched = exact_matched | fuzzy_matched

    # Layer 3: LLM semantic adjudication on terms that survived exact + fuzzy
    still_unmatched = all_jd_skills - matched
    semantic_match_details = await _semantic_match(still_unmatched, resume_skills)
    semantic_matched = set(semantic_match_details)
    matched |= semantic_matched

    missing_required = jd_required - matched
    missing_tech = jd_tech - matched
    missing_preferred = jd_preferred - matched
    missing_competencies = jd_competencies - matched

    total_jd = len(all_jd_skills)

    return {
        "resume_skills": sorted(resume_skills),
        "jd_required": sorted(jd_required),
        "jd_preferred": sorted(jd_preferred),
        "jd_tech": sorted(jd_tech),
        "jd_competencies": sorted(jd_competencies),
        "prose_requirements": sorted(set(prose_req_terms + prose_pref_terms + prose_comp_terms)),
        "matched": sorted(matched),
        "fuzzy_matched": sorted(fuzzy_matched),
        "semantic_matched": sorted(semantic_matched),
        "semantic_match_details": semantic_match_details,
        "missing_required": sorted(missing_required),
        "missing_tech": sorted(missing_tech),
        "missing_preferred": sorted(missing_preferred),
        "missing_competencies": sorted(missing_competencies),
        "overall_match_pct": _pct(len(matched), total_jd),
        "required_match_pct": _pct(len(jd_required) - len(missing_required), len(jd_required)),
        "tech_match_pct": _pct(len(jd_tech) - len(missing_tech), len(jd_tech)),
        "competencies_match_pct": _pct(len(jd_competencies) - len(missing_competencies), len(jd_competencies)),
    }


async def _semantic_match(jd_terms: set[str], resume_skills: set[str]) -> dict:
    """
    LLM-adjudicated matching. Returns {jd_term: {"covered_by": ..., "reason": ...}}.

    Output is validated to be a subset of the inputs (no hallucinated matches);
    degrades to {} on any LLM/JSON failure so this layer never fails a request.
    """
    if not jd_terms or not resume_skills:
        return {}

    # Prompt text is part of the key so prompt iteration invalidates old entries
    key = cache_key(
        "semantic_match",
        LLM_EXTRACTION_MODEL,
        str(LLM_MATCHING_THINK),
        SEMANTIC_MATCHING_SYSTEM,
        json.dumps(sorted(jd_terms)),
        json.dumps(sorted(resume_skills)),
    )
    if (cached := cache_get(key)) is not None:
        return cached

    user_prompt = json.dumps(
        {"jd_terms": sorted(jd_terms), "resume_skills": sorted(resume_skills)},
        indent=2,
    )

    try:
        raw = await get_client().prompt_model(
            SEMANTIC_MATCHING_SYSTEM, user_prompt, think=LLM_MATCHING_THINK
        )
        parsed = json.loads(raw)
    except Exception as e:
        logger.warning(f"Semantic matching unavailable, falling back to fuzzy-only: {e}")
        return {}

    result = {}
    for v in parsed.get("verdicts", []):
        jd_term = v.get("jd_term")
        covered_by = v.get("covered_by")
        if not covered_by:
            continue  # explicit non-match verdict
        if jd_term in jd_terms and covered_by in resume_skills:
            result[jd_term] = {"covered_by": covered_by, "reason": v.get("reason", "")}
            logger.info(f"Semantic match: '{jd_term}' <- '{covered_by}'")
        else:
            logger.warning(f"Discarded hallucinated semantic match: {v}")

    cache_set(key, result)
    return result


def _split_prose(terms: list[str]) -> tuple[list[str], list[str]]:
    """Separate keyword terms from prose sentences by word count."""
    keywords = [t for t in terms if len(t.split()) <= PROSE_WORD_THRESHOLD]
    prose = [t for t in terms if len(t.split()) > PROSE_WORD_THRESHOLD]
    return keywords, prose


def _fuzzy_match(jd_terms: set[str], resume_skills: set[str]) -> set[str]:
    """Return subset of jd_terms that fuzzy-match any resume skill above threshold."""
    fuzzy_matched = set()
    for jd_term in jd_terms:
        for resume_skill in resume_skills:
            if fuzz.token_sort_ratio(jd_term, resume_skill) >= FUZZY_THRESHOLD:
                fuzzy_matched.add(jd_term)
                break
    return fuzzy_matched


def _pct(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 100.0
    return round(numerator / denominator * 100, 1)
