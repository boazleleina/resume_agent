from app.config import LLM_PROVIDER
from .base import LLMBase
from .ollama_client import OllamaClient
from .exceptions import LLMServiceException

_REGISTRY: dict[str, type[LLMBase]] = {
    "ollama": OllamaClient,
}


def get_client() -> LLMBase:
    """Return the configured LLM client. Add new providers to _REGISTRY."""
    cls = _REGISTRY.get(LLM_PROVIDER)
    if not cls:
        raise LLMServiceException(
            f"Unknown LLM_PROVIDER '{LLM_PROVIDER}'. "
            f"Available: {list(_REGISTRY)}"
        )
    return cls()
