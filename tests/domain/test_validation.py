from app.domain.validation import is_safe_file_type

def test_is_safe_file_type_pdf_valid():
    valid_pdf_bytes = b"%PDF-1.4...\n..."
    assert is_safe_file_type(valid_pdf_bytes, "pdf") is True

def test_is_safe_file_type_pdf_invalid():
    invalid_pdf_bytes = b"MZ\x90\x00..." # Executable
    assert is_safe_file_type(invalid_pdf_bytes, "pdf") is False

def test_is_safe_file_type_docx_valid():
    valid_docx_bytes = b"PK\x03\x04..." # Zip signature
    assert is_safe_file_type(valid_docx_bytes, "docx") is True

def test_is_safe_file_type_docx_invalid():
    invalid_docx_bytes = b"MZ\x90\x00..." 
    assert is_safe_file_type(invalid_docx_bytes, "docx") is False

def test_is_safe_file_type_unsupported_ext():
    valid_pdf_bytes = b"%PDF-1.4..."
    assert is_safe_file_type(valid_pdf_bytes, "txt") is False
