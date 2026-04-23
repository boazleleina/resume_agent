# Changelog

All notable changes to the `resume_agent` project will be documented in this file.

## [0.4.0] - 2026-04-23

### Added
- **LLM provider abstraction**: `LLMBase` ABC with `prompt_model()` interface. `OllamaClient` implements it. `factory.py` holds a `_REGISTRY` map — adding a new provider (e.g. Gemini) requires one new file and one line in the registry, zero changes to extraction/grading logic.
- **Split extraction/grading models**: `LLM_EXTRACTION_MODEL` (default `qwen3:4b`, fast, no thinking) and `LLM_GRADING_MODEL` (default `qwen3:8b`, reasoning). Both overridable via environment variables.
- **Two-layer persistent cache**: In-memory L1 (zero-latency within session) backed by `shelve` L2 (survives server restarts). 7-day TTL. Stored at `data/llm_cache`. Each pipeline step caches independently — changing only the JD re-runs JD extraction and grading, not resume extraction.
- **Fuzzy skill matching** via `rapidfuzz`: After exact match, unmatched JD terms run `token_sort_ratio ≥ 85` against all resume skills. Catches minor variants without a static alias rule per term.
- **Prose requirement separation**: JD requirements with more than 5 words are classified as prose and excluded from string matching (which always fails on sentences). They are passed directly to the grading LLM as a separate `prose_requirements` field for qualitative reasoning.
- **Compound skill expansion** (`expand_skill()`): `"JavaScript/TypeScript"` → `["javascript", "typescript"]`, `"AWS (EC2, S3)"` → `["aws"]`, `"OpenAI API"` → `["openai"]`, `"REST + GraphQL"` → `["rest", "graphql"]`. Slash split only fires when both sides are ≥ 3 chars, preventing `CI/CD`, `A/B`, and `C++` from being mangled.
- **Section header filter** in `resume_models.py`: Regex strips category labels (`"Languages & Frameworks"`, `"Cloud & MLOps"`, etc.) from `skills.all_terms` before VERBATIM validation. Prompt also instructs model not to include them.
- **Traceability tag** `"already present in resume — rephrase for emphasis"`: Post-processing checks all edit suggestions for capitalized tech tokens already in `raw_text`. False "missing" claims are re-tagged automatically and logged.
- **`ScrapingBlockedException`**: Distinct subclass of `JobDescriptionException` for URL fetch failures (blocked, timed out, JS-only). Returns HTTP 422 with a user-facing message instead of a 400 with a technical error string.
- Unit tests for scraping failure cases: 403, 429, timeout, JS-only page, and subclass hierarchy.

### Changed
- `LLM_PROVIDER` env var added to `config.py` (default `"ollama"`). Changing provider requires no code edits.
- Grading prompt explicitly labels matched skills as "confirmed present — do NOT list as gaps" to prevent the grader from hallucinating missing skills.
- `_enforce_edit_traceability` now runs two passes: downgrades unsupported "supported by source text" claims, and catches "missing but unverifiable" / "generic strengthening" suggestions that name skills already in the resume.
- Scraping error messages rewritten to be user-facing ("We couldn't access that job posting...") rather than exposing HTTP status codes.

### Fixed
- `ImportError: cannot import name 'LLM_MODEL_TAG'`: config refactored to split models, client updated to match.
- `JSONDecodeError` on resume extraction: Qwen3 emits `<think>...</think>` blocks in message content even with `think=False`. `_clean_response()` strips them before JSON parse. `"raw_text": null` removed from extraction schema prompt (model was filling it in, returning wrong shape).
- `RecursionError` in Pydantic validator: `validate_assignment=True` on `CanonicalResume` caused `setattr()` inside the `model_validator` to re-trigger the validator infinitely. Fixed by using `object.__setattr__()` for all mutations inside the validator.
- Skill normalization garbage (`"a"`, `"b testing"`, `"ci"`, `"cd"`) from over-aggressive `/` and `+` splitting. Slash split now requires both sides ≥ 3 chars; `+` split requires surrounding spaces.

## [0.3.1] - 2026-04-21

### Added
- `[POST] /analyze/` unified endpoint accepting both resume file and JD input in a single multipart request.

### Fixed
- Dedup normalization: lines differing only by leading bullets (`-`, `*`), bold markers (`**`), or casing are now correctly caught as duplicates, preventing bloated LLM context windows.
- Resume text returning empty from `/analyze/` due to mismatched dictionary key (`extracted_text` -> `parsed_text`).

## [0.3.0] - 2026-04-20

### Added
- `app/domain/resume_models.py` defining the strict Pydantic Canonical Resume schema (Stage 3).
- `app/domain/jd_models.py` defining the Pydantic Job Description schema (`core_requirements`, `preferred_qualifications`, `tech_stack`).
- `app/domain/jd_parsing.py` implementing a 4-layer JD extraction pipeline: JSON-LD -> Trafilatura recall-mode -> BeautifulSoup heading walker -> merge & deduplicate.
- `app/services/jd_service.py` for secure URL fetching with SSRF protection, 5MB memory-safe streaming, and raw text cleanup (`html.unescape`, `\r\n` stripping).
- `[POST] /process-jd/` endpoint exposed on FastAPI layer.
- Strict Server-Side Request Forgery (SSRF) filtering blocking `localhost`, private IPs, and link-local addresses.
- `beautifulsoup4` added to dependencies alongside `trafilatura`.

### Fixed
- Trafilatura dropping requirement lists when H1/H3 headings were stacked back-to-back (resolved by the BS4 heading walker safety net).

## [0.2.0] - 2026-04-17

### Added
- `ARCHITECTURE.md` file documenting the Domain-Driven Design (DDD) module breakdown
- Comprehensive unit tests using `pytest` for domain logic and parsers
- Explicit file directory tree in `README.md`
- Local Git version control initialized and `.gitignore` file mapping rules

### Changed
- Refactored single-file backend into an organized Domain-Driven Design architecture (`app/` directory)
- Overhauled documentation (`README.md`) to reflect the new architecture and testing methods
- Migrated legacy timestamp-based changelog to `AUDIT_TRAIL.md`

## [0.1.0] - 2026-04-16

### Added
- Initial FastAPI project setup
- Basic file upload and multi-format parsing (PDF, DOCX) functionality
