import json
from typing import AsyncGenerator

from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.services.resume_service import process_resume_upload
from app.services.jd_service import process_job_description
from app.domain.jd_parsing import JobDescriptionException, ScrapingBlockedException
from app.config import MAX_FILE_SIZE_BYTES, MAX_FILE_SIZE_MB
from app.domain.exceptions import (
    UnsupportedFileTypeError,
    FileSizeExceededError,
    FileSignatureMismatchError,
    DocumentClassificationError,
    DocumentParsingError
)

from app.services.llm import (
    LLMServiceException,
    extract_resume_facts,
    extract_jd_facts,
    compute_skill_match,
    grade_and_recommend,
)



router = APIRouter()

@router.post("/upload-resume/")
async def upload_resume(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
        
    # Pre-check size using ASGI headers if available
    if file.size and file.size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413, 
            detail=f"File too large. Maximum allowed size is {MAX_FILE_SIZE_MB}MB."
        )

    content = await file.read()

    try:
        result = process_resume_upload(file.filename, content, file.content_type or "application/octet-stream")
        return result
    except UnsupportedFileTypeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileSizeExceededError as e:
        raise HTTPException(status_code=413, detail=str(e))
    except FileSignatureMismatchError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DocumentClassificationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DocumentParsingError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

class JobDescriptionRequest(BaseModel):
    jd_input: str

@router.post("/process-jd/")
async def process_jd(request: JobDescriptionRequest):
    if not request.jd_input.strip():
        raise HTTPException(status_code=400, detail="Job description input cannot be empty.")
        
    try:
        clean_text = await process_job_description(request.jd_input)
        return {"clean_text": clean_text}
    except ScrapingBlockedException as e:
        raise HTTPException(status_code=422, detail=str(e))
    except JobDescriptionException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@router.post("/analyze/")
async def analyze(
    file: UploadFile = File(...),
    jd_input: str = Form(...)
):
    """
    Unified endpoint: accepts a resume file AND a job description
    (URL or raw text) in a single request. Processes both internally
    and returns the grading result.
    
    Postman usage:
      - Body -> form-data
      - Row 1: key="file", type=File, value=your_resume.pdf
      - Row 2: key="jd_input", type=Text, value="paste JD or URL here"
    """
    # --- Validate inputs ---
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")
    
    if not jd_input.strip():
        raise HTTPException(status_code=400, detail="Job description input cannot be empty.")
    
    if file.size and file.size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum allowed size is {MAX_FILE_SIZE_MB}MB."
        )

    content = await file.read()

    # --- Step 1: Parse the resume (reuses existing logic) ---
    try:
        resume_result = process_resume_upload(
            file.filename, content, file.content_type or "application/octet-stream"
        )
    except (UnsupportedFileTypeError, FileSizeExceededError, 
            FileSignatureMismatchError, DocumentClassificationError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DocumentParsingError as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    resume_text = resume_result.get("parsed_text", "")
    if not resume_text.strip():
        raise HTTPException(
            status_code=422,
            detail="Resume parsed but no text was extracted. The file may be a scanned image without OCR."
        )

    # --- Step 2: Clean the JD text (reuses existing logic) ---
    try:
        clean_jd = await process_job_description(jd_input)
    except ScrapingBlockedException as e:
        raise HTTPException(status_code=422, detail=str(e))
    except JobDescriptionException as e:
        raise HTTPException(status_code=400, detail=str(e))

    # --- Step 3: Extract structured facts ---
    # Sequential: local Ollama is single-threaded, so parallel calls queue anyway.
    # Running sequentially avoids the second call timing out while waiting in Ollama's queue.
    try:
        resume = await extract_resume_facts(resume_text)
        jd = await extract_jd_facts(clean_jd)
    except LLMServiceException as e:
        raise HTTPException(status_code=502, detail=f"LLM extraction failed: {str(e)}")

    # --- Step 4: Compute deterministic skill match ---
    skill_match = compute_skill_match(resume, jd)

    # --- Step 5: Grade and recommend (deep reasoning, ~60-120s) ---
    try:
        grading = await grade_and_recommend(resume, clean_jd, skill_match)
    except LLMServiceException as e:
        raise HTTPException(status_code=502, detail=f"LLM grading failed: {str(e)}")

    return {
        "resume_text": resume_text,
        "clean_jd": clean_jd,
        "structured_resume": resume.model_dump(),
        "structured_jd": jd.model_dump(),
        "skill_match": skill_match,
        "grading": grading.model_dump(),
    }


# ---------------------------------------------------------------------------
# Streaming endpoint
# ---------------------------------------------------------------------------

def _sse(event: str, data: dict) -> str:
    """Format one Server-Sent Event frame."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def _analyze_stream(
    resume_text: str,
    clean_jd: str,
) -> AsyncGenerator[str, None]:
    """
    Yields SSE frames as each pipeline step completes.

    Event sequence:
      resume      → structured resume JSON
      jd          → structured JD JSON
      skill_match → deterministic match result (instant)
      grading     → LLM grading result
      done        → signals stream end
      error       → emitted on any failure (stream then closes)
    """
    # Step 1: Resume extraction
    try:
        resume = await extract_resume_facts(resume_text)
        yield _sse("resume", resume.model_dump())
    except LLMServiceException as e:
        yield _sse("error", {"step": "resume", "detail": str(e)})
        return

    # Step 2: JD extraction
    try:
        jd = await extract_jd_facts(clean_jd)
        yield _sse("jd", jd.model_dump())
    except LLMServiceException as e:
        yield _sse("error", {"step": "jd", "detail": str(e)})
        return

    # Step 3: Skill match (deterministic, instant)
    skill_match = compute_skill_match(resume, jd)
    yield _sse("skill_match", skill_match)

    # Step 4: Grading
    try:
        grading = await grade_and_recommend(resume, clean_jd, skill_match)
        yield _sse("grading", grading.model_dump())
    except LLMServiceException as e:
        yield _sse("error", {"step": "grading", "detail": str(e)})
        return

    yield _sse("done", {})


@router.post("/analyze/stream/")
async def analyze_stream(
    file: UploadFile = File(...),
    jd_input: str = Form(...),
):
    """
    Streaming version of /analyze/.
    Returns text/event-stream — each pipeline step emits as it completes.

    Events: resume | jd | skill_match | grading | done | error

    Postman: Body -> form-data, key=file (File) + key=jd_input (Text).
    Set "Accept: text/event-stream" header to see events as they arrive.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")
    if not jd_input.strip():
        raise HTTPException(status_code=400, detail="Job description cannot be empty.")
    if file.size and file.size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum allowed size is {MAX_FILE_SIZE_MB}MB."
        )

    content = await file.read()

    try:
        resume_result = process_resume_upload(
            file.filename, content, file.content_type or "application/octet-stream"
        )
    except (UnsupportedFileTypeError, FileSizeExceededError,
            FileSignatureMismatchError, DocumentClassificationError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DocumentParsingError as e:
        raise HTTPException(status_code=500, detail=str(e))

    resume_text = resume_result.get("parsed_text", "")
    if not resume_text.strip():
        raise HTTPException(
            status_code=422,
            detail="Resume parsed but no text extracted. File may be a scanned image."
        )

    try:
        clean_jd = await process_job_description(jd_input)
    except ScrapingBlockedException as e:
        raise HTTPException(status_code=422, detail=str(e))
    except JobDescriptionException as e:
        raise HTTPException(status_code=400, detail=str(e))

    return StreamingResponse(
        _analyze_stream(resume_text, clean_jd),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
