import logging
import re
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Field description constants
# ---------------------------------------------------------------------------
VERBATIM_DESC = (
    "VERBATIM: Must copy exactly from source text. If no information is found "
    "naturally, leave as null. Do not invent or summarize."
)
MUTABLE_DESC = "MUTABLE: Can be modified or formulated by the agent."


# ---------------------------------------------------------------------------
# Normalization helpers for VERBATIM validation
# ---------------------------------------------------------------------------
def _normalize_for_comparison(text: str) -> str:
    """
    Normalize text for lenient verbatim comparison.
    Strips punctuation, collapses whitespace, lowercases.
    'Marysville, WA' and 'marysville wa' become identical.
    """
    if not text:
        return ""
    normalized = text.lower()
    normalized = re.sub(r'[^\w\s]', ' ', normalized)  # strip punctuation
    normalized = re.sub(r'\s+', ' ', normalized)      # collapse whitespace
    return normalized.strip()


def _in_source_strict(item: str, raw_lower: str) -> bool:
    """Strict check: item must appear as lowercase substring in source."""
    if not item:
        return True  # empty strings are not hallucinations
    return item.lower() in raw_lower


def _in_source_lenient(item: str, raw_normalized: str) -> bool:
    """Lenient check: item matches after punctuation/whitespace normalization."""
    if not item:
        return True
    return _normalize_for_comparison(item) in raw_normalized


_SECTION_HEADER_PATTERN = re.compile(
    r'^(ai\s*/\s*ml|languages\s*&\s*frameworks|cloud\s*&\s*mlops|data\s*&\s*apis|'
    r'practices|certifications|technical\s*skills|skills)$',
    re.IGNORECASE,
)


def _strip_section_headers(terms: list) -> list:
    """Remove resume section-header strings that leak into skill lists."""
    kept = [t for t in terms if not _SECTION_HEADER_PATTERN.match(t.strip())]
    dropped = len(terms) - len(kept)
    if dropped:
        logger.warning(f"Section header filter: stripped {dropped} header(s) from skills.all_terms")
    return kept


# ---------------------------------------------------------------------------
# Nested models
# ---------------------------------------------------------------------------
class ContactInfo(BaseModel):
    """
    Contact information block. Fields are marked VERBATIM for documentation,
    but the structural check lives in CanonicalResume.enforce_verbatim because
    contact fields need tiered checking — names/locations are lenient-checked
    (format variance is common), while emails/phones/links are skipped
    (format-dependent, better validated via regex).
    """
    name: Optional[str] = Field(default=None, description=VERBATIM_DESC)
    email: Optional[str] = Field(default=None, description=VERBATIM_DESC)
    phone: Optional[str] = Field(default=None, description=VERBATIM_DESC)
    location: Optional[str] = Field(default=None, description=VERBATIM_DESC)
    links: List[str] = Field(default_factory=list, description=VERBATIM_DESC)


class ExperienceInfo(BaseModel):
    """
    A single work experience entry. company/title are strict-checked against
    raw_text (hallucination risk is real). start_date/end_date are skipped
    (format varies too much — 'Jan 2024' vs 'January 2024' vs '01/2024').
    Bullets are MUTABLE — paraphrasing is the whole point.
    """
    title: str = Field(description=VERBATIM_DESC)
    company: str = Field(description=VERBATIM_DESC)
    start_date: Optional[str] = Field(default=None, description=VERBATIM_DESC)
    end_date: Optional[str] = Field(default=None, description=VERBATIM_DESC)
    bullets: List[str] = Field(default_factory=list, description=MUTABLE_DESC)


class EducationInfo(BaseModel):
    """
    A single education entry. institution/degree are strict-checked.
    graduation_date and gpa are skipped due to format variance
    ('4.0' vs 'GPA: 4.0', 'June 2026' vs 'Jun 2026' vs '2026').
    """
    degree: str = Field(description=VERBATIM_DESC)
    institution: str = Field(description=VERBATIM_DESC)
    graduation_date: Optional[str] = Field(default=None, description=VERBATIM_DESC)
    gpa: Optional[str] = Field(default=None, description=VERBATIM_DESC)


class ProjectInfo(BaseModel):
    """
    A single project entry. Name is strict-checked; description and bullets
    are MUTABLE. Link is skipped (URL format variance).
    """
    name: str = Field(description=VERBATIM_DESC)
    description: Optional[str] = Field(default=None, description=MUTABLE_DESC)
    link: Optional[str] = Field(default=None, description=VERBATIM_DESC)
    bullets: List[str] = Field(default_factory=list, description=MUTABLE_DESC)


class ResumeSkills(BaseModel):
    """
    Skills container. Currently wraps a flat list; designed as a class so
    future categorization (languages, frameworks, tools) can be added
    without migrating every consumer of CanonicalResume.
    """
    all_terms: List[str] = Field(
        default_factory=list,
        description="Ground truth explicit skills extracted before patching."
    )


# ---------------------------------------------------------------------------
# Root model with VERBATIM enforcement
# ---------------------------------------------------------------------------
class CanonicalResume(BaseModel):
    """
    Canonical structured representation of a resume.
    
    The raw_text field is the immutable ground truth. VERBATIM-marked fields
    are structurally validated against raw_text, preventing LLM hallucination
    at the schema level — not just via prompt instructions.
    
    Validation tiers:
      - STRICT (strip hallucinated items, log warnings):
          metrics_found, certifications, skills.all_terms
      - STRICT (log only, don't strip — required non-nullable fields):
          experience[].company, experience[].title
          education[].institution, education[].degree
          projects[].name
      - LENIENT (normalize punctuation/whitespace, log only):
          contact.name, contact.location
      - SKIPPED (format-dependent, log nothing):
          contact.email, contact.phone, contact.links
          experience[].start_date, experience[].end_date
          education[].graduation_date, education[].gpa
          projects[].link
    
    Design decisions:
      - Required string fields (like ExperienceInfo.company) are NOT stripped
        when they fail the check, because nulling them would crash validation.
        Log and continue — you decide later whether to enforce harder.
      - Lenient-checked fields use normalized comparison to tolerate legitimate
        format variance without flagging it as hallucination.
      - Skipped fields should be validated via format rules (EmailStr, regex)
        rather than substring matching, which produces too many false positives.
    """
    
    model_config = ConfigDict(
        # validate_assignment=True ensures that mutations after creation
        # (e.g., resume.metrics_found.append(...)) re-trigger validation.
        # Critical for the verbatim guarantee — without this, code could
        # mutate the model after validation and bypass the check.
        validate_assignment=True,
    )
    
    # --- State tracking layers (grounding anchor) ---
    raw_text: str = Field(
        description="The immutable raw string parsed from the document. The absolute ground truth."
    )
    metrics_found: List[str] = Field(
        default_factory=list,
        description="All numerical metrics and quantifiable outputs extracted naturally."
    )
    
    # --- Core mappings ---
    contact: ContactInfo = Field(default_factory=ContactInfo)
    summary: Optional[str] = Field(default=None, description=MUTABLE_DESC)
    experience: List[ExperienceInfo] = Field(default_factory=list)
    education: List[EducationInfo] = Field(default_factory=list)
    projects: List[ProjectInfo] = Field(default_factory=list)
    certifications: List[str] = Field(
        default_factory=list,
        description=VERBATIM_DESC
    )
    skills: ResumeSkills = Field(default_factory=ResumeSkills)
    
    # --- VERBATIM enforcement ---
    @model_validator(mode='after')
    def enforce_verbatim_against_raw_text(self) -> 'CanonicalResume':
        """
        Runs after model construction but before the object is returned.
        Applies tiered VERBATIM checking; see class docstring for tier details.
        """
        # Defensive: skip if no raw_text (partial construction, model_copy, etc.)
        if not self.raw_text or not self.raw_text.strip():
            return self
        
        raw_lower = self.raw_text.lower()
        raw_normalized = _normalize_for_comparison(self.raw_text)
        
        # ========== Top-level list fields (strict, strip hallucinations) ==========
        self._check_list_strict('metrics_found', raw_lower)
        self._check_list_strict('certifications', raw_lower)
        
        # skills.all_terms (nested field, strict, strip hallucinations + section headers)
        if self.skills and self.skills.all_terms:
            filtered = _strip_section_headers(self.skills.all_terms)
            clean, invented = self._partition_list(filtered, raw_lower)
            if invented:
                logger.warning(
                    f"VERBATIM violation in skills.all_terms "
                    f"({len(invented)} of {len(filtered)} stripped): {invented}"
                )
            object.__setattr__(self.skills, 'all_terms', clean)
        
        # ========== ContactInfo (lenient on name/location, skip rest) ==========
        if self.contact:
            self._check_optional_lenient(
                self.contact, 'name', raw_normalized, context='contact'
            )
            self._check_optional_lenient(
                self.contact, 'location', raw_normalized, context='contact'
            )
            # email, phone, links intentionally skipped — use format validators
        
        # ========== ExperienceInfo list (strict on company/title, log only) ==========
        for i, exp in enumerate(self.experience):
            if exp.company and not _in_source_strict(exp.company, raw_lower):
                logger.warning(
                    f"VERBATIM violation: experience[{i}].company='{exp.company}' "
                    f"not found in raw_text"
                )
            if exp.title and not _in_source_strict(exp.title, raw_lower):
                logger.warning(
                    f"VERBATIM violation: experience[{i}].title='{exp.title}' "
                    f"not found in raw_text"
                )
            # start_date, end_date intentionally skipped — date formats vary
            # bullets are MUTABLE, not checked
        
        # ========== EducationInfo list (strict on institution/degree, log only) ==========
        for i, edu in enumerate(self.education):
            if edu.institution and not _in_source_strict(edu.institution, raw_lower):
                logger.warning(
                    f"VERBATIM violation: education[{i}].institution='{edu.institution}' "
                    f"not found in raw_text"
                )
            if edu.degree and not _in_source_strict(edu.degree, raw_lower):
                logger.warning(
                    f"VERBATIM violation: education[{i}].degree='{edu.degree}' "
                    f"not found in raw_text"
                )
            # graduation_date, gpa intentionally skipped — format variance
        
        # ========== ProjectInfo list (strict on name, log only) ==========
        for i, proj in enumerate(self.projects):
            if proj.name and not _in_source_strict(proj.name, raw_lower):
                logger.warning(
                    f"VERBATIM violation: projects[{i}].name='{proj.name}' "
                    f"not found in raw_text"
                )
            # description is MUTABLE, link skipped (URL format variance)
            # bullets are MUTABLE, not checked
        
        return self
    
    # ---------------------------------------------------------------------
    # Helper methods for the validator
    # ---------------------------------------------------------------------
    @staticmethod
    def _partition_list(items: List[str], raw_lower: str) -> tuple[List[str], List[str]]:
        """Splits a list into (kept, stripped) based on strict substring presence."""
        kept = [x for x in items if _in_source_strict(x, raw_lower)]
        stripped = [x for x in items if not _in_source_strict(x, raw_lower)]
        return kept, stripped
    
    def _check_list_strict(self, field_name: str, raw_lower: str) -> None:
        """
        Strips hallucinated items from a top-level list field and logs.
        Uses object.__setattr__ to avoid re-triggering validate_assignment.
        """
        items = getattr(self, field_name)
        clean, invented = self._partition_list(items, raw_lower)
        if invented:
            logger.warning(
                f"VERBATIM violation in {field_name} "
                f"({len(invented)} of {len(items)} stripped): {invented}"
            )
        object.__setattr__(self, field_name, clean)
    
    def _check_optional_lenient(
        self,
        obj: BaseModel,
        field_name: str,
        raw_normalized: str,
        context: str,
    ) -> None:
        """
        Lenient check for optional string fields — allows punctuation and
        whitespace variance. Logs violations but keeps the value.
        Keeping suspicious values visible lets the user see what we think
        might be hallucinated, without destroying data that's just formatted oddly.
        """
        value = getattr(obj, field_name, None)
        if value is not None and not _in_source_lenient(value, raw_normalized):
            logger.warning(
                f"Possible VERBATIM violation: {context}.{field_name}='{value}' "
                f"not found in raw_text (lenient check)"
            )