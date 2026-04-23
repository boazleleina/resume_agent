"""
Ollama implementation of LLMBase.

Handles retries, timeouts, think-block stripping, and structured logging.
Only this file changes if Ollama's API or payload shape changes.
"""
import asyncio
import json
import logging
import re

import httpx

from app.config import LLM_EXTRACTION_MODEL, LLM_GRADING_MODEL, OLLAMA_CHAT_URL
from .base import LLMBase
from .exceptions import LLMServiceException

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_BASE_DELAY = 2.0
CTX_WINDOW = 8192
CTX_WARNING_THRESHOLD = 6000


class OllamaClient(LLMBase):
    async def prompt_model(
        self,
        system_prompt: str,
        user_prompt: str,
        think: bool = False,
    ) -> str:
        model = LLM_GRADING_MODEL if think else LLM_EXTRACTION_MODEL
        payload = {
            "model": model,
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
        estimated_tokens = len(system_prompt + user_prompt) // 4
        timeout = 180.0 if not think else 600.0

        if estimated_tokens > CTX_WARNING_THRESHOLD:
            logger.warning(
                f"Token estimate {estimated_tokens} exceeds {CTX_WARNING_THRESHOLD} "
                f"(ctx_window={CTX_WINDOW}). Input may be truncated."
            )

        last_error = None
        async with httpx.AsyncClient(timeout=timeout) as client:
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    response = await client.post(OLLAMA_CHAT_URL, json=payload)

                    if 400 <= response.status_code < 500:
                        raise LLMServiceException(
                            f"Ollama returned {response.status_code}: {response.text}. "
                            f"This is likely a payload or config error."
                        )

                    response.raise_for_status()
                    result = response.json()
                    _log_response_metrics(result, model, think, prompt_chars)

                    message = result.get("message")
                    if not message or "content" not in message:
                        raise LLMServiceException(
                            f"Unexpected Ollama response structure. "
                            f"Expected 'message.content', got: {json.dumps(result)[:500]}"
                        )

                    return _clean_response(message["content"])

                except httpx.HTTPStatusError as e:
                    last_error = e
                    if attempt < MAX_RETRIES:
                        delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                        logger.warning(
                            f"Ollama 5xx (attempt {attempt}/{MAX_RETRIES}), "
                            f"retrying in {delay}s: {e}"
                        )
                        await asyncio.sleep(delay)
                    else:
                        raise LLMServiceException(
                            f"Ollama failed after {MAX_RETRIES} attempts: {e}"
                        )

                except httpx.TimeoutException:
                    raise LLMServiceException(
                        f"Ollama timed out after {timeout}s "
                        f"(think={think}, prompt_chars={prompt_chars})."
                    )

                except httpx.HTTPError as e:
                    raise LLMServiceException(
                        f"Failed to communicate with Ollama: {e}"
                    )

        raise LLMServiceException(f"Ollama call failed unexpectedly: {last_error}")


def _clean_response(text: str) -> str:
    """Strip think-blocks and markdown fences Qwen3 emits despite think=False."""
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    text = re.sub(r'```(?:json)?\s*', '', text)
    return text.strip()


def _log_response_metrics(result: dict, model: str, think: bool, prompt_chars: int) -> None:
    eval_count = result.get("eval_count", "?")
    total_duration_sec = round(result.get("total_duration", 0) / 1e9, 2)
    logger.info(
        f"Ollama response: model={model} think={think} "
        f"tokens={eval_count} duration={total_duration_sec}s "
        f"prompt_chars={prompt_chars}"
    )
