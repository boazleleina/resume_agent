import os

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
LLM_MODEL_TAG = os.environ.get("LLM_MODEL_TAG", "qwen3:8b")
