# M5 Pro Upgrade Implementation Plan

**Hardware context:** MacBook Pro M5 Pro, 18-core CPU / 20-core GPU, 64GB unified memory (previously: base M4, 16GB). The 16GB constraint drove two design compromises this plan removes:

1. **Skill matching** relies on a hand-maintained alias map (`skill_aliases.py`) + fuzzy string matching. Semantic synonyms ("REST APIs" ≈ "RESTful services", "customer service" ≈ "client relations") are missed unless manually added — unmaintainable at scale, and useless for non-technical resumes.
2. **LLM models** are small (qwen3:4b extraction, qwen3:8b grading) with an 8192-token context window.

---

## Change 1: LLM Semantic Skill Matching (Layer 3)

### Current pipeline (`app/services/llm/matching.py`)

```
JD terms + resume terms
  → expand_skill()        (split compounds, strip parens/API suffix)
  → normalize_skill()     (lowercase + SKILL_ALIASES lookup)   ← Layer 0
  → exact set match                                             ← Layer 1
  → rapidfuzz token_sort_ratio ≥ 85                             ← Layer 2
  → remaining = "missing"
```

The docstring in `matching.py` already anticipates this: *"Three-layer skill matching: exact → fuzzy → (semantic, future)."* This change implements that third layer.

### Approach: LLM adjudication

After exact + fuzzy matching, send the still-unmatched JD terms plus the full resume skill list to the LLM in a single call and ask it to judge which JD requirements are genuinely covered. Why the LLM instead of embedding cosine similarity:

- **Context-aware equivalence.** Embeddings place "Java" near "JavaScript" (false positive) and struggle with implication — a resume listing "React" satisfies a JD asking for "JavaScript frameworks"; "PyTorch" satisfies "deep learning experience". An LLM judges these correctly; cosine similarity cannot.
- **Domain-agnostic.** Works identically for technical, nursing, sales, finance, or trades resumes with no per-domain threshold tuning. This is the property that makes the agent work for *all* resumes and JDs.
- **No new infrastructure.** Reuses the existing `LLMBase` client, factory, retry logic, and shelve cache. No embedding endpoint, no cosine math, no threshold constant to tune.

**Cost:** one extra LLM call per analysis (~2–5s on qwen3:8b). Negligible next to the 30s+ grading call. Results are cached, so repeat analyses are free.

**Guardrails (all three are mandatory):**

1. **Subset validation.** Every `jd_term` and `covered_by` value in the LLM output must be a member of the input sets — anything else is discarded and logged. This makes hallucinated matches structurally impossible.
2. **Conservative prompt.** Explicit rules: match only on genuine equivalence or direct implication, never on "related field" (Java ≠ JavaScript, Photoshop ≠ Illustrator). When unsure, don't match — a false "missing skill" is recoverable by the user; a false "matched" hides a real gap.
3. **Graceful degradation.** Any failure (timeout, bad JSON, Ollama down) logs a warning and returns fuzzy-only results. This layer must never fail a request.

**Keep Layers 0–2, but freeze the alias map.** `skill_aliases.py` stays for two reasons, with a much smaller role:

- `expand_skill()` (structural cleanup — splitting "JavaScript/TypeScript", stripping parentheticals) stays: splitting compounds before matching is free and deterministic, and gives the LLM cleaner inputs.
- `SKILL_ALIASES` shrinks to a frozen set of **ambiguous abbreviations only** ("tf", "go", "k8s", "ml", "js"...). Resolving these deterministically at Layer 0 costs nothing and removes ambiguity before the LLM sees them. Everything else (spelled-out synonyms like "postgres"→"postgresql", "amazon web services"→"aws") can be removed — Layer 3 handles those reliably.

The maintenance burden ends: no entry is ever added again unless it's an ambiguous abbreviation. Long-tail synonyms — technical and non-technical — are Layer 3's job.

### Step-by-step

#### Step 1.1 — Matching prompt (`app/services/llm/prompts.py`)

Add:

```python
SEMANTIC_MATCHING_SYSTEM = """You judge whether a candidate's skills satisfy job requirements.

You receive two lists:
- "jd_terms": requirements from a job description that did not string-match
- "resume_skills": every skill the candidate listed

For each jd_term, decide if any resume skill genuinely covers it. Rules:
- Match on equivalence ("client relations" covers "customer service") or direct
  implication ("React" covers "JavaScript frameworks", "PyTorch" covers "deep
  learning frameworks").
- Do NOT match merely related skills: Java does not cover JavaScript,
  Photoshop does not cover Illustrator, bookkeeping does not cover auditing.
- When unsure, do not match. A missed match is recoverable; a false match
  hides a real gap from the candidate.

Respond with JSON only:
{"matches": [{"jd_term": "<exact string from jd_terms>",
              "covered_by": "<exact string from resume_skills>",
              "reason": "<one short sentence>"}]}

If nothing matches, respond {"matches": []}.
Both jd_term and covered_by MUST be copied verbatim from the input lists."""
```

#### Step 1.2 — Semantic layer in `matching.py`

Make `compute_skill_match` **async** and add Layer 3 after fuzzy:

```python
import json
import logging

from .factory import get_client
from .cache import cache_get, cache_key, cache_set
from .prompts import SEMANTIC_MATCHING_SYSTEM

logger = logging.getLogger(__name__)


async def compute_skill_match(resume, jd) -> dict:
    ...
    # Layer 2: fuzzy (unchanged)
    ...
    matched = exact_matched | fuzzy_matched

    # Layer 3: LLM semantic adjudication on survivors
    still_unmatched = (jd_required | jd_preferred | jd_tech) - matched
    semantic_matches = await _semantic_match(still_unmatched, resume_skills)
    semantic_matched = set(semantic_matches)
    matched |= semantic_matched
    ...
    return {
        ...,
        "semantic_matched": sorted(semantic_matched),
        "semantic_match_details": semantic_matches,  # {jd_term: {covered_by, reason}} for UI
        ...
    }


async def _semantic_match(jd_terms: set[str], resume_skills: set[str]) -> dict:
    """
    LLM-adjudicated matching. Returns {jd_term: {"covered_by": ..., "reason": ...}}.
    Output is validated to be a subset of the inputs; degrades to {} on any failure.
    """
    if not jd_terms or not resume_skills:
        return {}

    from app.config import LLM_EXTRACTION_MODEL
    key = cache_key(
        "semantic_match",
        LLM_EXTRACTION_MODEL,
        json.dumps(sorted(jd_terms)),
        json.dumps(sorted(resume_skills)),
    )
    if (cached := cache_get(key)) is not None:
        return cached

    user_prompt = json.dumps({
        "jd_terms": sorted(jd_terms),
        "resume_skills": sorted(resume_skills),
    }, indent=2)

    try:
        raw = await get_client().prompt_model(
            SEMANTIC_MATCHING_SYSTEM, user_prompt, think=False
        )
        parsed = json.loads(raw)
    except Exception as e:
        logger.warning(f"Semantic matching unavailable, falling back to fuzzy-only: {e}")
        return {}

    # Guardrail: only accept matches whose terms exist verbatim in the inputs
    result = {}
    for m in parsed.get("matches", []):
        jd_term = m.get("jd_term")
        covered_by = m.get("covered_by")
        if jd_term in jd_terms and covered_by in resume_skills:
            result[jd_term] = {"covered_by": covered_by, "reason": m.get("reason", "")}
            logger.info(f"Semantic match: '{jd_term}' ← '{covered_by}'")
        else:
            logger.warning(f"Discarded hallucinated semantic match: {m}")

    cache_set(key, result)
    return result
```

Notes:

- `think=False` routes to the extraction model (qwen3:8b) — this is a classification task, not deep reasoning. If match quality proves insufficient during verification, switching to the grading model is a one-line change (`think=True`), at the cost of latency.
- The cache key includes the model name and both term lists, so it self-invalidates on model changes (unlike the current grading/extraction keys — see Step 2.5).
- `semantic_match_details` carries `covered_by` + `reason` so the UI can show *why* a requirement counts as covered ("JavaScript frameworks — covered by React").

#### Step 1.3 — Call-site updates (`app/routes.py`)

Two sites (`routes.py:147` and `routes.py:209`):

```python
skill_match = await compute_skill_match(resume, jd)
```

The SSE route's comment "Skill match (deterministic, instant)" should change to "Skill match (exact/fuzzy + LLM semantic, ~2-5s)".

#### Step 1.4 — Grader prompt (`app/services/llm/grading.py`)

Add semantic matches to `_build_grading_user_prompt` alongside the existing fuzzy line:

```python
- Semantically-matched skills (equivalent or implied by resume skills — do NOT list these as gaps): {skill_match.get('semantic_matched', [])}
```

#### Step 1.5 — Trim `skill_aliases.py`

Reduce `SKILL_ALIASES` to ambiguous abbreviations only:

```python
SKILL_ALIASES = {
    "k8s": "kubernetes",
    "ml": "machine learning",
    "dl": "deep learning",
    "nlp": "natural language processing",
    "llm": "large language model",
    "llms": "large language model",
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
    "tf": "terraform",
    "golang": "go",
    "c sharp": "c#",
    "dot net": ".net",
    "dotnet": ".net",
}
```

Deleted entries ("postgres", "node", "amazon web services", "fast api", "mongo"...) are handled by fuzzy or Layer 3. Update the module docstring to state the new policy: *frozen; only ambiguous abbreviations belong here.*

#### Step 1.6 — Tests (`tests/services/test_llm_matching.py`)

- Convert existing tests to async (`pytest.mark.asyncio`; add `pytest-asyncio` to `requirements.txt`). Mock `get_client` to return `{"matches": []}` so existing exact/fuzzy assertions pass unchanged.
- New tests:
  - LLM returns valid match → term lands in `semantic_matched`, removed from `missing_required`.
  - **Hallucination guardrail:** LLM returns a `jd_term` not in the input → discarded, logged, not matched.
  - LLM failure (exception / invalid JSON) → result identical to fuzzy-only.
  - Cache hit: second identical call does not invoke the client (assert mock called once).
  - Non-technical pair through the real prompt (integration test, marked `@pytest.mark.slow`, skipped in CI): "client relations" covers "customer service".

---

## Change 2: Bigger Models + Larger Context

### Recommendation

| Role | Current | New | Why |
|------|---------|-----|-----|
| Extraction + semantic matching (`think=False`) | `qwen3:4b` | `qwen3:8b` (already pulled) | Structured JSON output and match adjudication — 8b is noticeably more reliable at schema adherence, still fast. |
| Grading (`think=True`) | `qwen3:8b` | `qwen3:30b-a3b` | See below. |

**Why `qwen3:30b-a3b` over dense `qwen3:32b`:** it's a Mixture-of-Experts model — 30B total parameters but only ~3B active per token. On Apple Silicon this means roughly 32B-class reasoning quality at near-8b generation speed (~50+ tok/s vs ~10–12 tok/s for dense 32b on an M5 Pro). Q4 weights are ~19GB — comfortable in 64GB with room for the extraction model and a large KV cache simultaneously. Grading latency should *drop* versus the old 8b-on-16GB setup despite the quality jump.

If maximum quality matters more than latency, dense `qwen3:32b` (~20GB Q4) is the alternative — expect grading to take several minutes with `think=True`. Start with 30b-a3b; the config change to try 32b later is one env var.

### Context window

`CTX_WINDOW = 8192` in `ollama_client.py` was a 16GB compromise — the warning threshold at 6000 tokens fires on any long resume + JD. With 64GB, raise to **32768** and make it configurable.

### Step-by-step

#### Step 2.1 — Pull models

```bash
ollama pull qwen3:30b-a3b     # ~19GB download
```

#### Step 2.2 — Config (`app/config.py`)

```python
LLM_EXTRACTION_MODEL = os.environ.get("LLM_EXTRACTION_MODEL", "qwen3:8b")
LLM_GRADING_MODEL = os.environ.get("LLM_GRADING_MODEL", "qwen3:30b-a3b")
OLLAMA_NUM_CTX = int(os.environ.get("OLLAMA_NUM_CTX", "32768"))
```

#### Step 2.3 — `app/services/llm/ollama_client.py`

- Replace the module constants:

```python
from app.config import OLLAMA_NUM_CTX
CTX_WINDOW = OLLAMA_NUM_CTX
CTX_WARNING_THRESHOLD = int(CTX_WINDOW * 0.75)
```

- Keep timeouts as-is (180s extraction / 600s grading) — 30b-a3b generates fast enough that 600s has ample headroom; revisit only if switching to dense 32b.

#### Step 2.4 — Keep Ollama models warm (optional, recommended)

Cold-loading 19GB takes ~10–20s on first request. Either accept the first-request hit, or:

```bash
export OLLAMA_KEEP_ALIVE=30m       # in the shell that runs `ollama serve`
export OLLAMA_MAX_LOADED_MODELS=2  # grading + extraction resident together
```

#### Step 2.5 — Cache invalidation (confirmed issue)

Verified: `cache_key` in `grading.py:24` and (presumably) `extraction.py` hashes only the prompt inputs — **not the model name**. After the model swap, cached qwen3:8b results would be served as if they came from 30b-a3b.

Fix properly (preferred over one-time cache wipe) — include the model in the key:

```python
# grading.py
key = cache_key("grade", LLM_GRADING_MODEL, clean_jd, ...)
# extraction.py — same pattern with LLM_EXTRACTION_MODEL
```

This makes every future model change self-invalidating. (The semantic matching cache key in Step 1.2 already follows this pattern.)

---

## Execution order

1. `ollama pull qwen3:30b-a3b` (do first; large download)
2. Change 2 (config + client constants + cache-key fix) — smallest diff, immediately testable
3. Verify: run one full grade through the UI, check `logs/` for duration/token metrics
4. Change 1 (matching prompt → semantic layer → routes → grading prompt → alias trim → tests)
5. `pytest tests/` — all green
6. End-to-end verification, both domains:
   - Technical: resume with "RESTful services" against JD requiring "REST API" — lands in `semantic_matched`, not `missing_required`
   - Non-technical: resume with "client relations" against JD requiring "customer service" — same
   - Negative control: resume with "Java" against JD requiring "JavaScript" — stays in `missing_required`
7. If false positives appear, tighten the prompt rules (add the observed pair as an explicit negative example); if obvious equivalences miss, consider `think=True` routing for the matcher

## Rollback

Every change is env-var reversible:

```bash
export LLM_GRADING_MODEL=qwen3:8b
export LLM_EXTRACTION_MODEL=qwen3:4b
export OLLAMA_NUM_CTX=8192
```

The semantic layer degrades to fuzzy-only automatically on any LLM failure, so no code rollback is needed for Change 1 either.

## Memory budget sanity check (64GB)

| Component | RAM |
|-----------|-----|
| qwen3:30b-a3b (Q4) + 32k KV cache | ~22GB |
| qwen3:8b (Q4) + KV cache | ~7GB |
| macOS + app + browser | ~10–15GB |
| **Total** | **~40–45GB** — comfortable headroom |
