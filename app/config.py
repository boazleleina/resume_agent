import os
from pathlib import Path

# --- File Upload Config ---
ALLOWED_EXTENSIONS = {"pdf", "docx"}
MAX_FILE_SIZE_MB = 5
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# --- LLM / Ollama Config ---
# Override these with environment variables when deploying to Docker or a remote machine.
# Example: export OLLAMA_API_URL=http://ollama-server:11434/api/chat
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_CHAT_URL = f"{OLLAMA_BASE_URL}/api/chat"
OLLAMA_TAGS_URL = f"{OLLAMA_BASE_URL}/api/tags"
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "ollama")  # add new providers to factory._REGISTRY
# Same model for both roles by default: qwen3:30b-a3b is MoE (3B active params)
# so it generates as fast as a small dense model, and keeping ONE model resident
# avoids Ollama load-thrash (18GB reload per role switch caused multi-minute stalls).
LLM_EXTRACTION_MODEL = os.environ.get("LLM_EXTRACTION_MODEL", "qwen3:30b-a3b")
LLM_GRADING_MODEL = os.environ.get("LLM_GRADING_MODEL", "qwen3:30b-a3b")
OLLAMA_NUM_CTX = int(os.environ.get("OLLAMA_NUM_CTX", "32768"))
OLLAMA_KEEP_ALIVE = os.environ.get("OLLAMA_KEEP_ALIVE", "30m")  # keep model resident between requests
# Thinking mode for grading: hidden reasoning tokens add 1-2 min per call.
# 30b-a3b without thinking beats the old 8b with thinking — off by default.
LLM_GRADING_THINK = os.environ.get("LLM_GRADING_THINK", "false").lower() == "true"
# Thinking mode for semantic matching. The per-verdict prompt makes non-think
# accurate (forced ruling on every term), so thinking is off by default —
# it adds ~1.5 min on real-size skill lists for marginal gain.
LLM_MATCHING_THINK = os.environ.get("LLM_MATCHING_THINK", "false").lower() == "true"

# --- Cache Config ---
_project_root = Path(__file__).parent.parent
CACHE_DIR = Path(os.environ.get("CACHE_DIR", str(_project_root / "data")))
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_PATH = str(CACHE_DIR / "llm_cache")   # shelve appends .db/.dir/.bak
CACHE_TTL_SECONDS = int(os.environ.get("CACHE_TTL_SECONDS", 86400 * 7))  # 7 days
