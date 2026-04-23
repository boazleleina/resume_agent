"""
Simple in-memory cache for LLM responses.

Keyed by SHA256 of concatenated input strings. TTL-based expiration
avoids stale grading results when inputs change. No size limit yet —
add LRU eviction via cachetools when memory becomes a concern.
"""
import hashlib
import logging
import time

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 3600  # 1 hour

_response_cache: dict[str, tuple[object, float]] = {}


def cache_key(*args: str) -> str:
    """SHA256 hash of concatenated inputs for cache lookup."""
    combined = "|".join(args)
    return hashlib.sha256(combined.encode()).hexdigest()


def cache_get(key: str):
    """Returns cached result if within TTL, else None."""
    if key in _response_cache:
        result, ts = _response_cache[key]
        if time.time() - ts < CACHE_TTL_SECONDS:
            logger.info(f"Cache hit for key {key[:12]}...")
            return result
        del _response_cache[key]
    return None


def cache_set(key: str, result: object) -> None:
    """Store result in cache with current timestamp."""
    _response_cache[key] = (result, time.time())