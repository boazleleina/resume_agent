# Resume Agent

An AI-powered resume grading agent that parses your resume, compares it against a job description, and returns actionable, traceable improvement suggestions — all running locally with no data leaving your machine.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python + FastAPI |
| LLM Engine | Local Ollama — `qwen3:4b` (extraction) + `qwen3:8b` (grading) |
| Parsers | `pdfplumber` (PDF), `python-docx` (DOCX) |
| JD Extraction | 4-layer pipeline: JSON-LD → Trafilatura → BeautifulSoup heading walker → merge/dedupe |
| Skill Matching | Exact match → fuzzy match (`rapidfuzz`) → semantic (planned) |
| Cache | In-memory L1 + `shelve` disk L2 (7-day TTL, survives restarts) |
| Testing | `pytest` |

---

## Pipeline

1. **Upload** — Resume file (PDF/DOCX) validated via magic-byte check and classified as a real resume.
2. **Parse** — Text extracted and normalized into a Canonical Resume JSON (single source of truth).
3. **JD Resolution** — URL or pasted text processed through a 4-layer extraction pipeline. Sites that block scraping return a user-friendly 422 with instructions to paste instead.
4. **Extraction** — Fast LLM pass (`qwen3:4b`, no thinking) structures both resume and JD into Pydantic schemas. VERBATIM enforcement strips hallucinated fields.
5. **Skill Matching** — Deterministic (no LLM). Exact match → fuzzy match. Prose requirements (sentences) bypass matching and go straight to the grader for qualitative reasoning.
6. **Grading** — Reasoning LLM pass (`qwen3:8b`, thinking enabled) produces a match score, honest gaps, and 3 traceable edits. Post-processing catches suggestions naming skills already in the resume.
7. **Human Review** — User reviews and approves/rejects proposed patches. *(frontend pending)*
8. **Regenerate** — Approved patches applied to Canonical JSON; ATS-optimized PDF generated. *(v2)*

---

## Hallucination Prevention

Every recommendation must carry one of five traceability tags:

1. `"supported by source text"` — evidence literally in resume; downgrades automatically if not verifiable
2. `"formatting improvement"` — presentation only, no factual claim
3. `"generic strengthening suggestion"` — valid advice, not resume-specific
4. `"missing but unverifiable, ask user to supply"` — real gap, user must confirm
5. `"already present in resume — rephrase for emphasis"` — auto-applied when suggestion names a skill already in the resume

The model is never allowed to invent metrics or experience. It only proposes patches.

---

## Project Structure

```text
resume_agent/
├── app/
│   ├── config.py                  # All env-overridable settings (LLM_PROVIDER, models, cache)
│   ├── main.py
│   ├── routes.py                  # Thin FastAPI transport layer
│   ├── domain/
│   │   ├── classification.py      # Heuristic resume vs non-resume detection
│   │   ├── exceptions.py
│   │   ├── grading_models.py      # Pydantic schema for grading output
│   │   ├── jd_models.py           # Pydantic schema for job descriptions
│   │   ├── jd_parsing.py          # 4-layer JD extraction pipeline
│   │   ├── resume_models.py       # Canonical resume schema with VERBATIM enforcement
│   │   └── validation.py          # Magic-byte file validation
│   ├── parsers/
│   │   ├── docx_parser.py
│   │   ├── pdf_parser.py
│   │   └── registry.py            # Dynamic parser switchboard
│   └── services/
│       ├── jd_service.py          # URL fetching (SSRF-safe) + raw text cleanup
│       ├── resume_service.py
│       └── llm/
│           ├── base.py            # LLMBase ABC — defines prompt_model() interface
│           ├── ollama_client.py   # OllamaClient(LLMBase) — Ollama-specific implementation
│           ├── factory.py         # Provider registry + get_client()
│           ├── extraction.py      # Step 1: Structured extraction
│           ├── matching.py        # Step 2: Deterministic skill matching
│           ├── grading.py         # Step 3: Reasoning + traceability enforcement
│           ├── prompts.py         # All prompt strings in one place
│           ├── skill_aliases.py   # Alias map + compound skill expansion
│           ├── cache.py           # Two-layer cache (L1 memory + L2 shelve)
│           └── exceptions.py
├── data/
│   └── llm_cache                  # Persistent shelve cache (auto-created)
├── tests/
│   ├── domain/
│   ├── parsers/
│   └── services/
│       ├── test_jd_service.py     # Scraping failure + raw text tests
│       └── test_llm_matching.py   # Skill normalization + fuzzy matching tests
├── ARCHITECTURE.md
├── CHANGELOG.md
├── README.md
└── requirements.txt
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/upload-resume/` | Upload and parse a resume (PDF/DOCX). |
| POST | `/process-jd/` | Submit a JD (URL or raw text). Returns cleaned text. |
| POST | `/analyze/` | Unified endpoint — resume file + JD in one request. Returns full grading payload. |

---

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Pull both Ollama models:
   ```bash
   ollama pull qwen3:4b   # fast extraction model
   ollama pull qwen3:8b   # reasoning/grading model
   ```

3. Start the server:
   ```bash
   uvicorn app.main:app --reload
   ```

4. Test at `http://127.0.0.1:8000/docs`

### Switching LLM provider

All LLM settings are env-var controlled. To point at a remote Ollama instance:
```bash
export OLLAMA_BASE_URL=http://your-server:11434
export LLM_EXTRACTION_MODEL=qwen3:14b
export LLM_GRADING_MODEL=qwen3:32b
```

To add a new provider (e.g. Gemini): implement `LLMBase.prompt_model()` in a new file, add one entry to `factory._REGISTRY`, set `LLM_PROVIDER=gemini`.

---

## Testing

```bash
./venv/bin/pytest tests/ -v
```
