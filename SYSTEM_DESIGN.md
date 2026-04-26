# Resume Agent: System Design & Architecture

This document outlines the software engineering principles, design patterns, design decisions, and constraints used to build the Resume Agent backend.

## 1. Local Development Environment & Constraints

The application is designed to run locally, prioritizing privacy and avoiding expensive cloud LLM API costs.

*   **Operating System**: macOS
*   **AI Backend**: Local Ollama (GPU-accelerated)
*   **The Constraint**: Running LLMs locally places immense pressure on system memory (RAM).
*   **The Multi-Model Solution**: 
    To balance speed and capability on a local Mac, the pipeline was split into a **Multi-Model Architecture**:
    *   **Qwen 3 (4B)**: Used exclusively for data extraction (`think=False`). It acts as a deterministic "robot" to rapidly pull facts from text. Its smaller size allows it to process large context windows quickly without locking up the system.
    *   **Qwen 3 (8B)**: Used exclusively for grading and recommendations (`think=True`). It acts as the "strategist", utilizing its deeper reasoning capabilities. Reserving the heavy model only for the final, synthesized step prevents the Mac from overheating or running out of memory during the initial parsing phases.

## 2. Software Engineering Principles

The application strictly adheres to several core software engineering philosophies to ensure maintainability, testability, and security.

### Domain-Driven Design (DDD)
The codebase is heavily stratified, separating business rules from infrastructure:
*   **Domain Layer (`app/domain/`)**: The unquestionable source of truth. It contains no external dependencies or networking code. It enforces the anti-hallucination logic, defines data schemas (Pydantic), and houses deterministic business rules (like Document Classification).
*   **Infrastructure Layer (`app/parsers/`)**: The "dumb" layer. It only knows how to turn binary files (PDFs, DOCX) into text. It does not understand what a resume is.
*   **Service Layer (`app/services/`)**: The Orchestrator. It dictates the workflow but contains no raw business logic.
*   **Transport Layer (`app/routes.py`)**: The FastAPI edge. It simply routes HTTP traffic to the Service Layer and translates Python exceptions into standard HTTP status codes.

### SOLID Principles
*   **Dependency Inversion**: The core extraction logic relies on abstract contracts (`LLMBase`), not concrete implementations (like `OllamaClient`).
*   **Single Responsibility**: Files are highly specialized. `pdf_parser.py` only extracts text. `cache.py` only handles caching.

## 3. Design Patterns Utilized

To keep the codebase modular, several Gang of Four (GoF) design patterns were implemented:

1.  **The Factory Pattern (`app/services/llm/factory.py`)**
    *   *Usage*: Instantiates the correct LLM client based on the `.env` configuration.
    *   *Decision*: Allows the application to seamlessly switch between local Ollama and cloud providers (like OpenAI) without altering the core pipeline logic.
2.  **The Adapter / Strategy Pattern (`app/services/llm/base.py`)**
    *   *Usage*: Forces any LLM client (Ollama, Anthropic, etc.) to conform to a strict `prompt_model` interface.
    *   *Decision*: Decouples the application from specific vendor APIs.
3.  **The Façade Pattern (`app/services/llm/__init__.py`)**
    *   *Usage*: Explicitly exports only the required top-level functions (Extraction, Matching, Grading) via `__all__`.
    *   *Decision*: Hides the complex internal machinery (caching, clients, prompts) of the `llm` package from the rest of the application.
4.  **The Registry Pattern (`app/parsers/registry.py`)**
    *   *Usage*: Maps file extensions dynamically to their respective parsing functions.
    *   *Decision*: Makes adding support for new file types (e.g., `.pages`) trivial without modifying core logic.

## 4. Key Design Decisions

### A. The Anti-Hallucination Strategy (VERBATIM vs MUTABLE)
LLMs are probabilistic and prone to inventing facts. Instead of relying solely on prompt engineering, the system relies on structural Python code.
*   **Decision**: Schema fields are strictly categorized as `VERBATIM` (must exist in the source document, e.g., Job Titles) or `MUTABLE` (can be rephrased, e.g., bullet points).
*   **Implementation**: A Pydantic `@model_validator` acts as an absolute gatekeeper. It cross-references the LLM's JSON output against the immutable `raw_text` extracted from the PDF. If the LLM hallucinates a skill, the Python validator silently deletes it.

### B. Deterministic Mathematical Matching
*   **Decision**: The LLM is NOT used to calculate the skill match percentage between the Resume and the Job Description.
*   **Implementation**: `app/services/llm/matching.py` uses deterministic set intersections and Fuzzy Matching (Levenshtein Distance) to generate a scorecard. This scorecard is then fed to the LLM during the grading phase. This prevents the LLM from struggling with counting tasks.

### C. Streaming UX (Server-Sent Events)
*   **Decision**: Running sequential LLM tasks takes 30-60 seconds locally. Waiting for a single HTTP response creates poor UX.
*   **Implementation**: `app/routes.py` uses Python Async Generators to yield Server-Sent Events (SSE). As each pipeline step (Resume Parse -> JD Parse -> Match -> Grade) completes, the JSON is streamed instantly to the frontend, allowing for a highly responsive, progressive UI.

### D. Security-First Scraping
*   **Decision**: Allowing users to input Job Description URLs exposes the server to SSRF (Server-Side Request Forgery) and Out-Of-Memory attacks.
*   **Implementation**: 
    *   `is_valid_url`: Explicitly blocks `localhost` and private IP spaces.
    *   `httpx.stream`: Downloads HTML payloads chunk-by-chunk, forcibly aborting the connection if the server lies about file size or exceeds the 5MB safe limit.

## 5. Caching Strategy
*   **Decision**: Prevent identical LLM requests from wasting local compute time and API delays.
*   **Implementation**: A two-layer caching system (`cache.py`). 
    *   **L1 (In-Memory)**: Instant access for immediate page reloads.
    *   **L2 (Disk - `shelve`)**: Persists across server restarts.
    *   Uses SHA-256 hashing of combined prompts to guarantee absolute cache-key uniqueness. Data older than the configured TTL (default 7 days) is automatically evicted.
