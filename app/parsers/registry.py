from app.parsers.pdf_parser import extract_text_from_pdf
from app.parsers.docx_parser import extract_text_from_docx
from app.domain.exceptions import DocumentParsingError

def parse_document(file_bytes: bytes, ext: str) -> str:
    try:
        if ext == "pdf":
            return extract_text_from_pdf(file_bytes)
        elif ext == "docx":
            return extract_text_from_docx(file_bytes)
        else:
            raise DocumentParsingError(f"No parser found for extension: {ext}")
    except Exception as e:
        if isinstance(e, DocumentParsingError):
            raise
        raise DocumentParsingError(f"Failed to parse document: {str(e)}")
