import pytest
from app.services.jd_service import process_job_description

@pytest.mark.anyio
async def test_process_job_description_raw_text():
    # If the user passes raw text (not a URL), it should skip httpx and return the stripped text
    raw_input = "   We are looking for a senior engineer with 10 years of Python experience.   "
    result = await process_job_description(raw_input)
    
    # Assert whitespace is stripped and network wasn't hit
    assert result == "We are looking for a senior engineer with 10 years of Python experience."
