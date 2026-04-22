from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from pydantic import BaseModel
from app.services.resume_service import process_resume_upload
from app.services.jd_service import process_job_description
from app.domain.jd_parsing import JobDescriptionException
from app.config import MAX_FILE_SIZE_BYTES, MAX_FILE_SIZE_MB
from app.domain.exceptions import (
    UnsupportedFileTypeError,
    FileSizeExceededError,
    FileSignatureMismatchError,
    DocumentClassificationError,
    DocumentParsingError
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

    # --- Step 2: Clean the JD text (reuses existing logic) ---
    try:
        clean_jd = await process_job_description(jd_input)
    except JobDescriptionException as e:
        raise HTTPException(status_code=400, detail=str(e))

    # --- Step 3: LLM Grading (placeholder - wired next) ---
    # This is where we will call:
    #   grade_result = await grade_resume(canonical_resume, clean_jd)

    return {
        "resume_text": resume_result.get("parsed_text", ""),
        "clean_jd": clean_jd,
        "grading": "LLM grading not yet connected. This will return score, matched_skills, and missing_skills."
    }
