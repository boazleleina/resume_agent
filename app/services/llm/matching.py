from app.domain.resume_models import CanonicalResume
from app.domain.jd_models import JobDescriptionSchema
from .skill_aliases import normalize_skill


def compute_skill_match(
    resume: CanonicalResume, 
    jd: JobDescriptionSchema
) -> dict:
    """
    Pure Python set operations. No LLM, no tokens, no hallucination risk.
    
    Applies alias normalization so 'PostgreSQL' matches 'Postgres',
    'Node.js' matches 'NodeJS', etc.
    
    Separates tech_stack from core_requirements so candidates with
    adjacent stacks aren't unfairly penalized on missing_required.
    
    Passes explicit match percentages to the Step 3 LLM.
    """
    # Defensive defaults — if the LLM extracted no skills, use empty sets
    resume_terms = resume.skills.all_terms if resume.skills and resume.skills.all_terms else []
    jd_req_terms = jd.core_requirements if jd.core_requirements else []
    jd_pref_terms = jd.preferred_qualifications if jd.preferred_qualifications else []
    jd_tech_terms = jd.tech_stack if jd.tech_stack else []

    # Normalize through alias map
    resume_skills = {normalize_skill(s) for s in resume_terms}
    jd_required = {normalize_skill(s) for s in jd_req_terms}
    jd_preferred = {normalize_skill(s) for s in jd_pref_terms}
    jd_tech = {normalize_skill(s) for s in jd_tech_terms}
    
    # Separate matching: tech_stack is its own category
    all_jd_skills = jd_required | jd_preferred | jd_tech
    
    matched = resume_skills & all_jd_skills
    missing_required = jd_required - resume_skills
    missing_tech = jd_tech - resume_skills
    missing_preferred = jd_preferred - resume_skills
    
    # Explicit match percentages so the LLM doesn't have to guess ratios
    total_jd = len(all_jd_skills)
    match_pct = round(len(matched) / total_jd * 100, 1) if total_jd > 0 else 0.0
    required_match_pct = (
        round((len(jd_required) - len(missing_required)) / len(jd_required) * 100, 1) 
        if jd_required else 100.0
    )
    tech_match_pct = (
        round((len(jd_tech) - len(missing_tech)) / len(jd_tech) * 100, 1) 
        if jd_tech else 100.0
    )

    return {
        "resume_skills": sorted(resume_skills),
        "jd_required": sorted(jd_required),
        "jd_preferred": sorted(jd_preferred),
        "jd_tech": sorted(jd_tech),
        "matched": sorted(matched),
        "missing_required": sorted(missing_required),
        "missing_tech": sorted(missing_tech),
        "missing_preferred": sorted(missing_preferred),
        "overall_match_pct": match_pct,
        "required_match_pct": required_match_pct,
        "tech_match_pct": tech_match_pct,
    }

def _pct(numerator: int, denominator: int) -> float:
    """Safe percentage calc — empty denominator returns 100 (no requirements = perfect match)."""
    if denominator == 0:
        return 100.0
    return round(numerator / denominator * 100, 1)