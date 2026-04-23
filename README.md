# Resume Agent

A human-in-the-loop, AI-powered agent designed to parse your resume, compare it against a Job Description, and provide actionable, traceable patches to improve your resume—all strictly controlled to prevent LLM hallucination.

## Tech Stack
* **Backend:** Python + FastAPI
* **LLM Engine:** Local Ollama (Qwen 3 8B)
* **Parsers:** `pdfplumber` (PDF), `python-docx` (Word)
* **JD Extraction:** 4-layer pipeline using `trafilatura` (recall-mode) + `beautifulsoup4` (heading walker) + JSON-LD structured data
* **Architecture:** Domain-Driven Design (DDD) & Stateless processing for clean PDF generation and accurate iteration.
* **Testing:** `pytest`

---

## The 8-Stage Architecture Pipeline

1. **Upload:** User uploads their PDF/DOCX resume to the FastAPI backend. *Security checks run here to reject disguised malware via magic-byte validation.*
2. **Parse:** Backend extracts pure text and layout-aware structure. *Heuristic validation rejects non-resume files (e.g., invoices) dynamically.*
3. **Normalize:** Raw text is converted into a canonical `Resume JSON` (Single Source of Truth).
4. **Job Description Resolution:** 
   - User inputs a JD via text or URL.
   - Backend runs a 4-layer extraction pipeline: JSON-LD structured data -> Trafilatura recall-mode -> BeautifulSoup heading walker -> merge & deduplicate. This ensures stacked headings and requirement lists are never dropped.
5. **Grade:** The local Qwen 3 model compares the Canonical JSON against the JD. It outputs a strictly enforced JSON object containing: `score`, `strengths`, `weaknesses`, and `recommendations`.
6. **Recommend:** Improvements are strictly limited to existing evidence or generic advice using Traceability Categories to prevent inventing metrics.
7. **Human Review:** User reviews and approves/rejects proposed patches on the frontend.
8. **Rewrite & Regenerate:** The approved patches are applied to the Canonical JSON, and a new, standardized, ATS-friendly PDF is generated statelessly.

---

## Data Governance & Hallucination Prevention
To prevent hallucination, the agent uses strict Data governance. The model is **never** allowed to randomly rewrite the resume in one shot. It only proposes **patches**. 

Every recommendation must evaluate to one of four traceability tracking tags:
1. `"supported by source text"`
2. `"formatting improvement"`
3. `"generic strengthening suggestion"`
4. `"missing but unverifiable, ask user to supply"`

If a user lacks a specific measurable outcome (e.g., "Increased sales by X%"), the agent is structurally forbidden from inventing one.

---

## Project Structure (Domain-Driven Design)

The codebase rests on a clear separation of concerns inside the `app/` directory:
- `app/domain/`: Pure business logic (classification, file validation, JD extraction pipeline), Pydantic data models (`resume_models.py`, `jd_models.py`), and custom exceptions.
- `app/parsers/`: Decoupled text ingestion logic (`pdfplumber` and `python-docx`) dynamically resolved via an internal registry.
- `app/services/`: High-level operations bridging domain and integration layers (resume upload, JD resolution). 
- `app/routes.py`: Lean API endpoints that offload core processing to the services layer.
- `tests/`: End-to-end `pytest` coverage (25 tests) validating domain heuristics, parser flows, SSRF protections, and schema integrity.

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/upload-resume/` | Upload and parse a resume (PDF/DOCX). Returns extracted text. |
| POST | `/process-jd/` | Submit a JD (URL or raw text). Returns cleaned text via 4-layer pipeline. |
| POST | `/analyze/` | Unified endpoint. Accepts resume file + JD in one request. Returns both processed results and (soon) LLM grading. |

### Directory Tree

```text
resume_agent/
├── app/
│   ├── config.py
│   ├── main.py
│   ├── routes.py
│   ├── domain/
│   │   ├── classification.py
│   │   ├── exceptions.py
│   │   ├── jd_models.py          # Pydantic schema for Job Descriptions
│   │   ├── jd_parsing.py         # 4-layer JD extraction pipeline
│   │   ├── resume_models.py      # Pydantic canonical resume schema
│   │   └── validation.py
│   ├── parsers/
│   │   ├── docx_parser.py
│   │   ├── pdf_parser.py
│   │   └── registry.py
│   └── services/
│       ├── jd_service.py         # JD URL fetching & raw text cleanup
│       ├── resume_service.py
│       └── llm/                  # Modular 3-step LLM pipeline
│           ├── extraction.py     # Step 1: Structured extraction
│           ├── matching.py       # Step 2: Deterministic skill matching
│           ├── grading.py        # Step 3: Reasoning & analysis
│           └── prompts.py        # Centralized prompt management
├── tests/
│   ├── domain/
│   │   ├── test_classification.py
│   │   ├── test_jd_models.py
│   │   ├── test_jd_parsing.py
│   │   ├── test_resume_models.py
│   │   └── test_validation.py
│   ├── parsers/
│   │   └── test_registry.py
│   └── services/
│       ├── test_jd_service.py
│       └── test_llm_matching.py  # Tests for skill normalization
├── ARCHITECTURE.md
├── CHANGELOG.md
├── README.md
└── requirements.txt
```

---

## Roadmap & Future Enhancements

### 1. Semantic Similarity Matching (v2)
Currently, skill matching relies on a deterministic `SKILL_ALIASES` map. While effective for tech keywords, it can miss semantic synonyms.
- **Planned**: Replace the alias map with `sentence-transformers` embeddings (~80MB model).
- **Goal**: Compute cosine similarity between vectors to catch matches like "cross-functional leadership" ≈ "led distributed teams" without manual rules.

### 2. PDF Generation (v2)
- **Goal**: Implement `services/pdf_generator.py` to produce a finalized, ATS-optimized PDF incorporating the "Top 3 Edits." This will be stateless, using the Canonical JSON as the source.

### 3. Pipeline Progress
1. **Upload** (Done)
2. **Parse** (Done)
3. **Normalize** (Done)
4. **JD Resolution** (Done)
5. **Grade** (Done)
6. **Recommend** (Done)
7. **Human Review** (Pending Frontend)
8. **Regenerate** (Pending v2)

---

## Setup & Running Locally

1. Install dependencies from the requirements file:
   ```bash
   pip install -r requirements.txt
   ```
2. **Local LLM Setup:** Ensure [Ollama](https://ollama.ai/) is installed and the `qwen3:8b` model is pulled:
   ```bash
   ollama pull qwen3:8b
   ```
3. Start the FastAPI development server:
   ```bash
   uvicorn app.main:app --reload
   ```
4. Open `http://127.0.0.1:8000/docs` to test the API endpoints (`/upload-resume/`, `/process-jd/`, `/analyze/`).

## Testing

To run the automated test suite, execute:
```bash
./venv/bin/pytest tests/ -v
```

*(This README is a living document and will be updated as the agent is built!)*
