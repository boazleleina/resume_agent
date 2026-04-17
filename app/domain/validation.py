def is_safe_file_type(file_bytes: bytes, ext: str) -> bool:
    if ext == "pdf":
        return file_bytes.startswith(b"%PDF-")
    elif ext == "docx":
        # DOCX files are zip archives, which always start with PK
        return file_bytes.startswith(b"PK")
    return False
