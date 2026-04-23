"""
Low-level Ollama HTTP client with retries, timeouts, and structured logging.

Everything else in the llm/ package calls call_ollama() — they don't
know about httpx, retry counts, or payload shape. This is the only file
that changes if you swap Ollama for OpenAI or vLLM.
"""
import asyncio
import json
import logging

import httpx

from app.config import LLM_MODEL_TAG, OLLAMA_CHAT_URL

from .exceptions import LLMServiceException

logger = logging.getLogger(__name__)

# Retry config for transient 5xx errors (Ollama warming up or overloaded)
MAX_RETRIES = 3
RETRY_BASE_DELAY = 2.0  # seconds, doubles each attempt

# Context window limits
CTX_WINDOW = 8192
CTX_WARNING_THRESHOLD = 6000


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token for English text."""
    return len(text) // 4


async def call_ollama(system_prompt: str, user_prompt: str, think: bool = False) -> str:
    """
    Sends a chat request to the local Ollama server.
    
    Features:
      - Retry with exponential backoff on 5xx (Ollama warming up)
      - No retry on 4xx (those are our bugs)
      - Structured logging of token count, duration, prompt length
      - Explicit error on unexpected response shape
    
    Args:
        system_prompt: Role/context instructions for the model.
        user_prompt: The actual content to process.
        think: Enables Qwen3 reasoning mode. Off for extraction (fast),
               on for grading (slower but nuanced).
    
    Returns:
        The raw string content from the model's response.
    
    Raises:
        LLMServiceException: On any communication or structural failure.
    """
    payload = {
        "model": LLM_MODEL_TAG,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "format": "json",
        "stream": False,
        "options": {
            "temperature": 0.0,
            "num_ctx": CTX_WINDOW,
        },
        "think": think,
    }

    prompt_chars = len(system_prompt) + len(user_prompt)
    estimated_tokens = _estimate_tokens(system_prompt + user_prompt)
    # 90s for extraction — covers cold-start (10s) + prompt encoding (3s) + generation of ~1500 tokens (60s) + buffer (17s).
    # Handles the worst-case real resume comfortably.
    # 300s for grading. With thinking mode on a 3000-token resume and 2500-token JD, grading can produce 2000+ output tokens plus thinking tokens.
    # 5 minutes gives breathing room.
    timeout = 90.0 if not think else 300.0
    last_error = None

    if estimated_tokens > CTX_WARNING_THRESHOLD:
        logger.warning(
            f"Token estimate {estimated_tokens} exceeds {CTX_WARNING_THRESHOLD} "
            f"(ctx_window={CTX_WINDOW}). Input may be truncated."
        )

    async with httpx.AsyncClient(timeout=timeout) as client:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = await client.post(OLLAMA_CHAT_URL, json=payload)

                # 4xx = our bug (bad payload, wrong model). Don't retry.
                if 400 <= response.status_code < 500:
                    raise LLMServiceException(
                        f"Ollama returned {response.status_code}: {response.text}. "
                        f"This is likely a payload or config error."
                    )

                response.raise_for_status()
                result = response.json()

                _log_response_metrics(result, think, prompt_chars)

                message = result.get("message")
                if not message or "content" not in message:
                    raise LLMServiceException(
                        f"Unexpected Ollama response structure. "
                        f"Expected 'message.content', got: {json.dumps(result)[:500]}"
                    )

                return message["content"]

            except httpx.HTTPStatusError as e:
                # 5xx: transient, retry with backoff
                last_error = e
                if attempt < MAX_RETRIES:
                    delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                    logger.warning(
                        f"Ollama 5xx error (attempt {attempt}/{MAX_RETRIES}), "
                        f"retrying in {delay}s: {str(e)}"
                    )
                    await asyncio.sleep(delay)
                else:
                    raise LLMServiceException(
                        f"Ollama failed after {MAX_RETRIES} attempts: {str(e)}"
                    )

            except httpx.TimeoutException:
                raise LLMServiceException(
                    f"Ollama timed out after {timeout}s "
                    f"(think={think}, prompt_chars={prompt_chars}). "
                    f"The model may need a larger timeout or the input is too long."
                )

            except httpx.HTTPError as e:
                raise LLMServiceException(f"Failed to communicate with Ollama: {str(e)}")

    raise LLMServiceException(f"Ollama call failed unexpectedly: {last_error}")


def _log_response_metrics(result: dict, think: bool, prompt_chars: int) -> None:
    """Emit structured log line with token count, duration, prompt size."""
    eval_count = result.get("eval_count", "?")
    total_duration_ns = result.get("total_duration", 0)
    total_duration_sec = round(total_duration_ns / 1e9, 2)
    logger.info(
        f"Ollama response: model={LLM_MODEL_TAG} think={think} "
        f"tokens={eval_count} duration={total_duration_sec}s "
        f"prompt_chars={prompt_chars}"
    )