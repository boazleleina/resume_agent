# Changelog

All notable changes to the `resume_agent` project will be documented in this file.

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
