import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.jd_service import process_job_description
from app.domain.jd_parsing import ScrapingBlockedException, JobDescriptionException


@pytest.mark.anyio
async def test_process_job_description_raw_text():
    raw_input = "   We are looking for a senior engineer with 10 years of Python experience.   "
    result = await process_job_description(raw_input)
    assert result == "We are looking for a senior engineer with 10 years of Python experience."


def _mock_client(stream_cm):
    """
    Build an AsyncClient mock where .stream() returns an async context manager.
    .stream() itself is sync (MagicMock), not a coroutine — it returns the cm directly.
    """
    mock_client = MagicMock()
    mock_client.stream = MagicMock(return_value=stream_cm)

    client_cm = AsyncMock()
    client_cm.__aenter__ = AsyncMock(return_value=mock_client)
    client_cm.__aexit__ = AsyncMock(return_value=False)
    return client_cm


def _blocking_stream(status_code: int):
    """Stream context manager that raises HTTPStatusError on raise_for_status()."""
    response = MagicMock(spec=httpx.Response)
    response.status_code = status_code
    response.headers = {}
    response.raise_for_status.side_effect = httpx.HTTPStatusError(
        message=f"Client error '{status_code}'",
        request=MagicMock(),
        response=MagicMock(status_code=status_code),
    )

    stream_cm = MagicMock()
    stream_cm.__aenter__ = AsyncMock(return_value=response)
    stream_cm.__aexit__ = AsyncMock(return_value=False)
    return stream_cm


def _timeout_stream():
    """Stream context manager that raises TimeoutException on entry."""
    stream_cm = MagicMock()
    stream_cm.__aenter__ = AsyncMock(side_effect=httpx.TimeoutException("timed out"))
    stream_cm.__aexit__ = AsyncMock(return_value=False)
    return stream_cm


def _ok_stream(body: bytes):
    """Stream context manager that returns a 200 response with given body."""
    response = MagicMock(spec=httpx.Response)
    response.status_code = 200
    response.headers = {}
    response.raise_for_status = MagicMock()

    async def aiter_bytes():
        yield body

    response.aiter_bytes = aiter_bytes

    stream_cm = MagicMock()
    stream_cm.__aenter__ = AsyncMock(return_value=response)
    stream_cm.__aexit__ = AsyncMock(return_value=False)
    return stream_cm


@pytest.mark.anyio
async def test_403_raises_scraping_blocked():
    client_cm = _mock_client(_blocking_stream(403))
    with patch("app.services.jd_service.httpx.AsyncClient", return_value=client_cm):
        with pytest.raises(ScrapingBlockedException) as exc_info:
            await process_job_description("https://blocked-site.com/job/123")

    msg = str(exc_info.value).lower()
    assert "couldn't" in msg
    assert "paste" in msg


@pytest.mark.anyio
async def test_429_raises_scraping_blocked():
    client_cm = _mock_client(_blocking_stream(429))
    with patch("app.services.jd_service.httpx.AsyncClient", return_value=client_cm):
        with pytest.raises(ScrapingBlockedException) as exc_info:
            await process_job_description("https://rate-limited.com/job/123")

    assert "paste" in str(exc_info.value).lower()


@pytest.mark.anyio
async def test_timeout_raises_scraping_blocked():
    client_cm = _mock_client(_timeout_stream())
    with patch("app.services.jd_service.httpx.AsyncClient", return_value=client_cm):
        with pytest.raises(ScrapingBlockedException) as exc_info:
            await process_job_description("https://slow-site.com/job/123")

    assert "paste" in str(exc_info.value).lower()


@pytest.mark.anyio
async def test_js_only_page_raises_scraping_blocked():
    """Page fetches OK (200) but content is empty shell — JS-rendered."""
    empty_html = b"<html><body><div id='app'></div></body></html>"
    client_cm = _mock_client(_ok_stream(empty_html))
    with patch("app.services.jd_service.httpx.AsyncClient", return_value=client_cm):
        with pytest.raises(ScrapingBlockedException) as exc_info:
            await process_job_description("https://js-app.com/job/123")

    assert "paste" in str(exc_info.value).lower()


def test_scraping_blocked_is_subclass_of_jd_exception():
    assert issubclass(ScrapingBlockedException, JobDescriptionException)
