import pytest
from app.domain.jd_parsing import is_valid_url

def test_is_valid_url_success():
    assert is_valid_url("https://greenhouse.io/jobs/123") is True
    assert is_valid_url("http://linkedin.com/posting") is True

def test_is_valid_url_rejections():
    # Rejects raw paragraphs
    assert is_valid_url("Looking for a backend engineer.") is False
    
    # Rejects paragraphs that just happen to start with a URL
    assert is_valid_url("https://google.com is where we work. Apply now.") is False
    
    # Missing scheme
    assert is_valid_url("www.lever.co/jobs") is False

def test_is_valid_url_ssrf_blocking():
    # Blocks localhost aliases
    assert is_valid_url("http://localhost:8000/attack") is False
    assert is_valid_url("https://local/test") is False
    assert is_valid_url("http://invalid/route") is False
    
    # Blocks strict private IPs
    assert is_valid_url("http://127.0.0.1/attack") is False
    assert is_valid_url("http://192.168.1.1:8080/pwn") is False
    assert is_valid_url("http://169.254.169.254/latest/meta-data") is False
