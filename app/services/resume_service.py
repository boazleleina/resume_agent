from app.config import ALLOWED_EXTENSIONS, MAX_FILE_SIZE_BYTES, MAX_FILE_SIZE_MB
from app.domain.validation import is_safe_file_type
from app.domain.classification import classify_document
from app.parsers.registry import parse_document
from app.domain.exceptions import (
    UnsupportedFileTypeError,
    FileSizeExceededError,
    FileSignatureMismatchError,
    DocumentClassificationError
)

def process_resume_upload(filename: str, content: bytes, content_type: str) -> dict:
    if not filename:
        raise ValueError("No filename provided")

    ext = filename.split(".")[-1].lower()
    
    if ext not in ALLOWED_EXTENSIONS:
        raise UnsupportedFileTypeError(f"Unsupported file type: {ext}. Allowed types are PDF and DOCX.")
    
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise FileSizeExceededError(f"File too large. Maximum allowed size is {MAX_FILE_SIZE_MB}MB.")
        
    if not is_safe_file_type(content, ext):
        raise FileSignatureMismatchError("File signature mismatch. The file might be corrupted or maliciously disguised.")
        
    # parse document
    parsed_text = parse_document(content, ext)

    # classification
    classification = classify_document(parsed_text)
    
    if classification == "cover_letter":
        raise DocumentClassificationError("Document rejected: Appears to be a cover letter, not a resume.")
    elif classification == "other_document":
        raise DocumentClassificationError("Document rejected: Unrecognized document type. Please upload a structured resume.")
    elif classification == "uncertain":
        raise DocumentClassificationError("Document rejected: The system is uncertain if this is a valid resume. Please ensure it has standard headings.")

    return {
        "filename": filename,
        "content_type": content_type,
        "parsed_text": parsed_text.strip(),
        "message": "File successfully parsed!"
    }
