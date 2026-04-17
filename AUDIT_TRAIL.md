# Changelog

All notable changes to the `resume_agent` project will be documented in this file.

## [2026-04-17 05:20:00 -07:00]

### Added
- `CHANGELOG.md` file to track ongoing updates and modifications to the project directory.

### Changed
- **Architectural Refactor**: Transitioned the single-file layout (`main.py`) into a Domain-Driven Design layout within an `app/` directory.
  - Moved API routing to `app/routes.py`.
  - Moved domain business logic to `app/domain/exceptions.py`, `app/domain/validation.py`, and `app/domain/classification.py`.
  - Split document parsing logic into isolated modules: `app/parsers/pdf_parser.py`, `app/parsers/docx_parser.py`, and `app/parsers/registry.py`.
  - Centralized application processing flow under `app/services/resume_service.py`.
  - Centralized shared variables and limits into `app/config.py`.

### Removed
- `main.py` at the project root which previously handled all application logic. The application is now launched from `app/main.py`.

---

## [2026-04-17 05:31:00 -07:00]

### Added
- `pytest` testing library and created a test suite (`tests/` directory).
- Unit tests for domain logic (`tests/domain/test_validation.py`, `tests/domain/test_classification.py`).
- Unit tests for parser flow (`tests/parsers/test_registry.py`).

---

## [2026-04-17 05:33:00 -07:00]

### Changed
- **Documentation**: Overhauled `README.md` to reflect the new Domain-Driven Design layout, added testing instructions, and documented the new `uvicorn` launch command.

---

## [2026-04-17 05:46:00 -07:00]

### Added
- `ARCHITECTURE.md` file documenting the Domain-Driven Design (DDD) module breakdown, data flow mermaid diagram, and the 8-stage pipeline goals.

---

## [2026-04-17 05:50:00 -07:00]

### Changed
- **Documentation**: Inserted explicit file directory tree syntax into `README.md` to map out the DDD restructure.
