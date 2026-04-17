from fastapi import APIRouter, File, UploadFile, HTTPException
from app.services.resume_service import process_resume_upload
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
