# Resume Agent 🚀

A human-in-the-loop, AI-powered agent designed to parse your resume, compare it against a Job Description, and provide actionable, traceable patches to improve your resume—all strictly controlled to prevent LLM hallucination.

## Tech Stack
* **Backend:** Python + FastAPI
* **LLM Engine:** Local Ollama (Qwen 3 8B)
* **Parsers:** `pdfplumber` (PDF), `python-docx` (Word)
* **Architecture:** Domain-Driven Design (DDD) & Stateless processing for clean PDF generation and accurate iteration.
* **Testing:** `pytest`

---

## The 8-Stage Architecture Pipeline

1. **Upload:** User uploads their PDF/DOCX resume to the FastAPI backend. *Security checks run here to reject disguised malware via magic-byte validation.*
2. **Parse:** Backend extracts pure text and layout-aware structure. *Heuristic validation rejects non-resume files (e.g., invoices) dynamically.*
3. **Normalize:** Raw text is converted into a canonical `Resume JSON` (Single Source of Truth).
4. **Job Description Resolution:** 
   - User inputs a JD via text or URL.
   - Backend extracts and normalizes the job description into plain text.
5. **Grade:** The local Qwen 3 model compares the Canonical JSON against the JD. It outputs a strictly enforced JSON object containing: `score`, `strengths`, `weaknesses`, and `recommendations`.
6. **Recommend:** Improvements are strictly limited to existing evidence or generic advice using Traceability Categories to prevent inventing metrics.
7. **Human Review:** User reviews and approves/rejects proposed patches on the frontend.
8. **Rewrite & Regenerate:** The approved patches are applied to the Canonical JSON, and a new, standardized, ATS-friendly PDF is generated statelessly.

---

## 🔒 Data Governance & Hallucination Prevention
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
- `app/domain/`: Pure business logic (classification heuristic algorithms, file validation) and custom exceptions.
- `app/parsers/`: Decoupled text ingestion logic (`pdfplumber` and `python-docx`) dynamically resolved via an internal registry.
- `app/services/`: High-level operations bridging domain and integration layers (e.g., handling the resume upload workflow). 
- `app/routes.py`: Lean API endpoints that offload core processing to the services layer.
- `tests/`: End-to-end `pytest` coverage validating domain heuristics, parser flows, and error handling.

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
│   │   └── validation.py
│   ├── parsers/
│   │   ├── docx_parser.py
│   │   ├── pdf_parser.py
│   │   └── registry.py
│   └── services/
│       └── resume_service.py
├── tests/
│   ├── domain/
│   │   ├── test_classification.py
│   │   └── test_validation.py
│   └── parsers/
│       └── test_registry.py
├── ARCHITECTURE.md
├── CHANGELOG.md
├── README.md
└── requirements.txt
```

---

## Setup & Running Locally

1. Install dependencies from the requirements file:
   ```bash
   pip install -r requirements.txt
   ```
2. Start the FastAPI development server:
   ```bash
   uvicorn app.main:app --reload
   ```
3. Open `http://127.0.0.1:8000/docs` to test the API endpoints (like `/upload-resume/`).

## Testing

To run the automated test suite, execute:
```bash
pytest tests/
```

*(This README is a living document and will be updated as the agent is built!)*
