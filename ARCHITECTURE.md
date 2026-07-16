# System Architecture

The Resume Agent uses a Domain-Driven Design (DDD) structure to maintain strict boundaries between input layers, processing engines, and business logic. This ensures traceability and enables safe iteration with the local LLM.

## Module Breakdown (`app/`)

### 1. `domain/`
Pure business logic, custom exceptions, and core data models — independent of FastAPI or any external framework.
- `exceptions.py`: Application-specific errors mapped to clean HTTP status codes.
- `validation.py`: Magic-byte file validation (prevents disguised executables from reaching parsers).
- `classification.py`: Heuristic scoring to reject non-resume documents (cover letters, invoices).
- `resume_models.py`: Pydantic canonical resume schema with VERBATIM/MUTABLE field annotations and tiered hallucination enforcement via `model_validator`. Uses `object.__setattr__` for in-validator mutations to avoid `validate_assignment` recursion.
- `jd_models.py`: Pydantic schema for structured JD extraction (`core_requirements`, `preferred_qualifications`, `tech_stack`, `key_competencies` — recruiter-scan concepts pulled from prose responsibilities and headings).
- `jd_parsing.py`: 4-layer JD extraction pipeline (JSON-LD → Trafilatura recall → BS4 heading walker → merge/dedupe). Raises `ScrapingBlockedException` when content cannot be extracted.

### 2. `parsers/`
Decoupled text ingestion.
- `pdf_parser.py` / `docx_parser.py`: Thin wrappers around `pdfplumber` and `python-docx`.
- `registry.py`: Dynamic switchboard — services request a parser by file type, no if/else chains in calling code.

### 3. `services/`
Orchestration layer bridging domain logic and the API.
- `resume_service.py`: Chains validation → parser registry → classification.
- `jd_service.py`: Handles URL fetching (SSRF protection, 5MB memory-safe streaming) and raw text cleanup. Raises `ScrapingBlockedException` on blocked/timed-out/JS-only pages, returning HTTP 422 with a user-facing message.

### 4. `services/llm/`
Modular LLM pipeline. Designed so swapping providers requires adding one file and one line — no changes to extraction or grading logic.

#### Provider abstraction
- `base.py`: `LLMBase` ABC defining `prompt_model(system, user, think=False, model_role="extraction") → str`. All providers implement this interface. `model_role` selects the model; `think` independently toggles reasoning mode — decoupled so the large model can run without thinking (fast) or with it (deep, minutes slower).
- `ollama_client.py`: `OllamaClient(LLMBase)`. Handles Ollama-specific payload shape, retries, timeouts, keep-alive, `<think>` block stripping, and structured logging. Selects `LLM_EXTRACTION_MODEL` or `LLM_GRADING_MODEL` based on `model_role`.
- `factory.py`: `_REGISTRY` maps provider name strings to classes. `get_client()` reads `LLM_PROVIDER` from config and returns the right instance. Adding a provider = one new file + one `_REGISTRY` entry.

#### Pipeline steps
- `extraction.py`: Step 1 — fast structured extraction (`think=False`). Injects `raw_text` after LLM parse (not in prompt) to save ~1000 tokens per call. JD extraction runs a verbatim hallucination guard plus a deterministic people-filter that strips role/team terms mislabeled as competencies.
- `matching.py`: Step 2 — three-layer skill matching (async): exact match → fuzzy match (`rapidfuzz`, threshold 85) → LLM semantic adjudication. Layer 3 asks the LLM for a verdict on EVERY unmatched JD term (`covered_by: <resume skill> | null`); forced per-term enumeration prevents both lazy empty output and volunteered false matches. Every verdict is validated verbatim against the input lists (hallucinated matches structurally impossible) and the layer degrades to fuzzy-only on any LLM failure. Prose requirements (>5 words) bypass string matching and go directly to the grader.
- `grading.py`: Step 3 — analysis on `LLM_GRADING_MODEL` (thinking off by default; `LLM_GRADING_THINK=true` re-enables at 1–2 min/call). Post-processes traceability tags: downgrades unsupported "source text" claims and catches suggestions naming skills already present in the resume.
- `prompts.py`: All prompt strings in one file. Prompt changes never touch pipeline logic. Prompt text is part of every cache key, so prompt iteration self-invalidates stale entries.
- `skill_aliases.py`: FROZEN abbreviation map (`k8s`, `tf`, `js`, …) + `expand_skill()` for compound normalization (`"AWS (EC2, S3)"` → `"aws"`, `"JavaScript/TypeScript"` → `["javascript", "typescript"]`). No longer a coverage mechanism — only ambiguous short tokens belong here; the semantic layer handles synonyms.
- `cache.py`: Two-layer cache — in-memory L1 (zero-latency, lost on restart) backed by `shelve` L2 (persists to `data/llm_cache`, 7-day TTL). Each pipeline step caches independently by SHA256 of its inputs, model name, thinking flag, and system prompt.

### 5. `config.py`
All environment-overridable settings in one place:
- `LLM_PROVIDER` — which client class to use (default `"ollama"`)
- `LLM_EXTRACTION_MODEL` / `LLM_GRADING_MODEL` — both default `qwen3:30b-a3b`: one resident model avoids Ollama load-thrash (18GB reloads per role switch caused multi-minute stalls), and the MoE architecture (3B active params) keeps generation fast
- `LLM_GRADING_THINK` / `LLM_MATCHING_THINK` — reasoning mode per step (default `false`)
- `OLLAMA_NUM_CTX` — context window (default 32768)
- `OLLAMA_KEEP_ALIVE` — model residency between requests (default `30m`)
- `CACHE_PATH`, `CACHE_TTL_SECONDS` — persistent cache location and TTL
- `OLLAMA_BASE_URL` — remote Ollama server override for Docker/cloud deployments

### 6. `routes.py`
Thin FastAPI transport layer. Fields requests, delegates to services, catches domain exceptions, formats REST responses. No business logic lives here.

### 7. `template/` (Frontend)
The user-facing Streamlit application.
- `app.py`: The main router and state machine (`input` -> `analyzing` -> `results`). It heavily overrides Streamlit's default components using raw CSS injected via `st.markdown(unsafe_allow_html=True)` to create a premium Dark Theme aesthetic.
- `api.py`: A synchronous wrapper using `httpx-sse` to stream server-sent events from the FastAPI backend. It explicitly intercepts non-SSE HTTP responses (e.g., 400 Bad Request) to extract raw JSON error payloads and bubble them up to the UI.
- `components.py` & `styles.py`: Extracted styling and component builders for UI maintainability.

---

## Data Flow

```mermaid
graph TD
    User["User"] -->|"Interacts with UI"| Streamlit["Streamlit Frontend\n(template/app.py)"]
    Streamlit -->|"POST /analyze/stream"| Routes["routes.py"]

    Routes --> ResumeService["resume_service.py\n(validate → parse → classify)"]
    Routes --> JDService["jd_service.py\n(fetch/clean JD text)"]

    ResumeService -->|"raw_text"| Extraction["llm/extraction.py\n(Step 1: Structured extraction)"]
    JDService -->|"clean_jd"| Extraction

    Extraction -->|"CanonicalResume + JD"| Matching["llm/matching.py\n(Step 2: Skill matching)"]
    Matching -->|"skill_match dict"| Grading["llm/grading.py\n(Step 3: Grading + edits)"]

    Extraction & Matching & Grading -->|"prompt_model()"| Factory["llm/factory.py\nget_client()"]
    Factory --> OllamaClient["OllamaClient\n(implements LLMBase)"]

    Grading -->|"GradingResult"| Routes
    Routes -->|"SSE Stream / JSON"| Streamlit
    Streamlit -->|"Updates UI"| User

    classDef provider fill:#005,color:#fff;
    class OllamaClient provider
```

---

## Hallucination Prevention

Every LLM output is validated at multiple layers:

| Layer | Mechanism |
|---|---|
| Extraction | VERBATIM validator strips invented skills, companies, metrics not found in `raw_text`; JD competencies also pass a deterministic people-filter |
| Skill matching | Layers 1–2 are deterministic set operations. Layer 3 (LLM) validates every verdict verbatim against the input lists — a match naming a term that wasn't in the inputs is discarded and logged, making hallucinated matches structurally impossible |
| Grading prompt | Matched skills explicitly labeled "do NOT list as gaps" |
| Traceability enforcement | Post-processing re-tags edits that name skills already in the resume |
| Traceability tags | Every edit suggestion must carry one of 5 tags (see below) |

**Traceability tags:**
1. `"supported by source text"` — evidence literally in resume
2. `"formatting improvement"` — structure/presentation only
3. `"generic strengthening suggestion"` — valid advice, not resume-specific
4. `"missing but unverifiable, ask user to supply"` — real gap, user must confirm
5. `"already present in resume — rephrase for emphasis"` — auto-applied by post-processor when suggestion names skills already found in `raw_text`

---

## Roadmap

### PDF generation (v2)
`services/pdf_generator.py` producing an ATS-optimized PDF from the Canonical JSON + approved edits. Stateless by design.

### Pipeline progress
1. Upload (done)
2. Parse (done)
3. Normalize (done)
4. JD Resolution (done)
5. Match — exact/fuzzy/LLM-semantic (done, v0.5)
6. Grade (done)
7. Recommend (done)
8. Human Review (pending frontend)
9. Regenerate (pending v2)
