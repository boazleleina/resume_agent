"""
Two-layer LLM response cache: in-memory L1 + shelve (disk) L2.

L1: dict — zero latency, lost on restart.
L2: shelve — persists across restarts, survives CTRL+C.

On read:  L1 hit → return. L1 miss → check L2 → promote to L1 if found.
On write: write both layers.
TTL checked on every read; stale entries are evicted lazily.

shelve uses pickle internally — Pydantic v2 models are picklable.
Threading lock covers both layers so concurrent async tasks don't race.
"""
import hashlib
import logging
import shelve
import threading
import time

from app.config import CACHE_PATH, CACHE_TTL_SECONDS

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_l1: dict[str, tuple[object, float]] = {}


def cache_key(*args: str) -> str:
    combined = "|".join(args)
    return hashlib.sha256(combined.encode()).hexdigest()


def cache_get(key: str):
    with _lock:
        # L1
        if key in _l1:
            result, ts = _l1[key]
            if time.time() - ts < CACHE_TTL_SECONDS:
                logger.info(f"Cache L1 hit {key[:12]}...")
                return result
            del _l1[key]

        # L2
        try:
            with shelve.open(CACHE_PATH) as db:
                if key in db:
                    result, ts = db[key]
                    if time.time() - ts < CACHE_TTL_SECONDS:
                        logger.info(f"Cache L2 hit {key[:12]}...")
                        _l1[key] = (result, ts)   # promote to L1
                        return result
                    del db[key]
        except Exception as e:
            logger.warning(f"Cache L2 read error: {e}")

    return None


def cache_set(key: str, result: object) -> None:
    ts = time.time()
    with _lock:
        _l1[key] = (result, ts)
        try:
            with shelve.open(CACHE_PATH) as db:
                db[key] = (result, ts)
        except Exception as e:
            logger.warning(f"Cache L2 write error: {e}")


def cache_clear() -> None:
    """Wipe both layers. Useful for testing or forced refresh."""
    with _lock:
        _l1.clear()
        try:
            with shelve.open(CACHE_PATH) as db:
                db.clear()
        except Exception as e:
            logger.warning(f"Cache L2 clear error: {e}")
