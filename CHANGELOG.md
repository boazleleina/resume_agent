# Changelog

All notable changes to the `resume_agent` project will be documented in this file.

## [0.2.1] - 2026-04-20

### Added
- `app/domain/resume_models.py` defining the strict Pydantic Canonical Resume schema (Stage 3).
- Strict Server-Side Request Forgery (SSRF) and size-limit protections (Stage 4).
- `app/services/jd_service.py` to securely fetch URLs natively.
- Zero-shot HTML scraping via `trafilatura` to algorithmically map websites into clean Job Descriptions.
- `[POST] /process-jd/` endpoint exposed on FastAPI layer.

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
