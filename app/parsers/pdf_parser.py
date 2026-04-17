import io
import pdfplumber

def extract_text_from_pdf(file_bytes: bytes) -> str:
    # Use io.BytesIO to safely read byte streams in memory
    text = ""
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
    return text
