from rapidfuzz import fuzz

from app.domain.resume_models import CanonicalResume
from app.domain.jd_models import JobDescriptionSchema
from .skill_aliases import expand_skill

FUZZY_THRESHOLD = 85  # token_sort_ratio score to count as a match
PROSE_WORD_THRESHOLD = 5  # requirements with more words than this are prose, not keywords


def compute_skill_match(
    resume: CanonicalResume,
    jd: JobDescriptionSchema,
) -> dict:
    """
    Three-layer skill matching: exact → fuzzy → (semantic, future).

    Prose requirements (sentences) are separated from keyword requirements
    before matching and passed directly to the grader for qualitative reasoning.
    String matching on prose always produces 0% — the LLM handles it better.
    """
    resume_terms = resume.skills.all_terms if resume.skills and resume.skills.all_terms else []
    jd_req_terms = jd.core_requirements if jd.core_requirements else []
    jd_pref_terms = jd.preferred_qualifications if jd.preferred_qualifications else []
    jd_tech_terms = jd.tech_stack if jd.tech_stack else []

    # Split prose reqs out before any matching
    keyword_req_terms, prose_req_terms = _split_prose(jd_req_terms)
    keyword_pref_terms, prose_pref_terms = _split_prose(jd_pref_terms)

    # Expand compounds and normalize
    resume_skills = {norm for s in resume_terms for norm in expand_skill(s)}
    jd_required = {norm for s in keyword_req_terms for norm in expand_skill(s)}
    jd_preferred = {norm for s in keyword_pref_terms for norm in expand_skill(s)}
    jd_tech = {norm for s in jd_tech_terms for norm in expand_skill(s)}

    # Layer 1: exact match
    exact_matched = resume_skills & (jd_required | jd_preferred | jd_tech)

    # Layer 2: fuzzy match on still-unmatched JD terms
    unmatched_tech = jd_tech - exact_matched
    unmatched_required = jd_required - exact_matched
    unmatched_preferred = jd_preferred - exact_matched

    fuzzy_matched_tech = _fuzzy_match(unmatched_tech, resume_skills)
    fuzzy_matched_required = _fuzzy_match(unmatched_required, resume_skills)
    fuzzy_matched_preferred = _fuzzy_match(unmatched_preferred, resume_skills)
    fuzzy_matched = fuzzy_matched_tech | fuzzy_matched_required | fuzzy_matched_preferred

    matched = exact_matched | fuzzy_matched
    missing_required = jd_required - matched
    missing_tech = jd_tech - matched
    missing_preferred = jd_preferred - matched

    all_jd_skills = jd_required | jd_preferred | jd_tech
    total_jd = len(all_jd_skills)

    return {
        "resume_skills": sorted(resume_skills),
        "jd_required": sorted(jd_required),
        "jd_preferred": sorted(jd_preferred),
        "jd_tech": sorted(jd_tech),
        "prose_requirements": sorted(set(prose_req_terms + prose_pref_terms)),
        "matched": sorted(matched),
        "fuzzy_matched": sorted(fuzzy_matched),
        "missing_required": sorted(missing_required),
        "missing_tech": sorted(missing_tech),
        "missing_preferred": sorted(missing_preferred),
        "overall_match_pct": _pct(len(matched), total_jd),
        "required_match_pct": _pct(len(jd_required) - len(missing_required), len(jd_required)),
        "tech_match_pct": _pct(len(jd_tech) - len(missing_tech), len(jd_tech)),
    }


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
