import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI

from app.config import LLM_EXTRACTION_MODEL, LLM_GRADING_MODEL, OLLAMA_TAGS_URL
from app.routes import router

# ---------------------------------------------------------------------------
# Logging setup — must run BEFORE any module-level loggers are created
# ---------------------------------------------------------------------------
Path("logs").mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)-40s | %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/app.log"),
    ],
)

# Quiet down noisy third-party libraries — their INFO logs drown out ours
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan: Ollama health check at startup
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs once at server startup. Checks that:
    1. Ollama is reachable at the configured URL
    2. The required model (e.g. qwen3:8b) is actually pulled and available
    
    Fails fast at boot so you see the error immediately in the terminal,
    not 60 seconds later on the first user request.
    """
    logger.info("Starting Resume Agent backend...")
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(OLLAMA_TAGS_URL)
            response.raise_for_status()
            
            available_models = [
                m.get("name", "") for m in response.json().get("models", [])
            ]
            
            required_models = {LLM_EXTRACTION_MODEL, LLM_GRADING_MODEL}
            missing = [m for m in required_models if not any(m in a for a in available_models)]

            if missing:
                logger.warning(
                    f"Models not found in Ollama: {missing}. "
                    f"Available: {available_models}. "
                    f"Run: ollama pull <model>"
                )
            else:
                logger.info(f"Ollama OK: extraction={LLM_EXTRACTION_MODEL}, grading={LLM_GRADING_MODEL}")
                
    except httpx.HTTPError:
        logger.warning(
            f"Cannot reach Ollama at {OLLAMA_TAGS_URL}. "
            f"Make sure Ollama is running: ollama serve"
        )
    except Exception as e:
        logger.warning(f"Ollama health check failed: {e}")
    
    yield  # Server starts accepting requests after this point
    
    logger.info("Shutting down Resume Agent backend...")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(lifespan=lifespan)
app.include_router(router)


@app.get("/")
def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)