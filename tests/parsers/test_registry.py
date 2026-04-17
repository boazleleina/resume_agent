import pytest
from unittest.mock import patch
from app.parsers.registry import parse_document
from app.domain.exceptions import DocumentParsingError

@patch("app.parsers.registry.extract_text_from_pdf")
def test_parse_document_pdf(mock_extract_pdf):
    mock_extract_pdf.return_value = "Mock PDF Content"
    result = parse_document(b"dummy_bytes", "pdf")
    assert result == "Mock PDF Content"
    mock_extract_pdf.assert_called_once_with(b"dummy_bytes")

@patch("app.parsers.registry.extract_text_from_docx")
def test_parse_document_docx(mock_extract_docx):
    mock_extract_docx.return_value = "Mock DOCX Content"
    result = parse_document(b"dummy_bytes", "docx")
    assert result == "Mock DOCX Content"
    mock_extract_docx.assert_called_once_with(b"dummy_bytes")

def test_parse_document_unsupported_ext():
    with pytest.raises(DocumentParsingError, match="No parser found for extension: txt"):
        parse_document(b"dummy_bytes", "txt")

@patch("app.parsers.registry.extract_text_from_pdf")
def test_parse_document_exception_handling(mock_extract_pdf):
    mock_extract_pdf.side_effect = Exception("Corrupt file")
    with pytest.raises(DocumentParsingError, match="Failed to parse document: Corrupt file"):
        parse_document(b"dummy_bytes", "pdf")
