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
LLM_EXTRACTION_MODEL = os.environ.get("LLM_EXTRACTION_MODEL", "qwen3:4b")
LLM_GRADING_MODEL = os.environ.get("LLM_GRADING_MODEL", "qwen3:8b")

# --- Cache Config ---
_project_root = Path(__file__).parent.parent
CACHE_DIR = Path(os.environ.get("CACHE_DIR", str(_project_root / "data")))
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_PATH = str(CACHE_DIR / "llm_cache")   # shelve appends .db/.dir/.bak
CACHE_TTL_SECONDS = int(os.environ.get("CACHE_TTL_SECONDS", 86400 * 7))  # 7 days
