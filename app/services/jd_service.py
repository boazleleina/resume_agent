import httpx
import html
from app.domain.jd_parsing import is_valid_url, extract_text_from_html, JobDescriptionException, ScrapingBlockedException

# We want to protect against memory DoS, so if a payload exceeds 5MB, we sever the connection.
MAX_PAYLOAD_SIZE = 5 * 1024 * 1024  # 5 MB

async def process_job_description(input_data: str) -> str:
    """
    Orchestrates Job Description resolution. 
    Checks if the input is a secure URL. If it is, fetches heavily constrained HTML bytes 
    and runs the 4-layer extraction pipeline.
    If it's raw text, cleans browser artifacts and returns it for downstream LLM processing.
    """
    # 1. Fallback / Base Case: It's just raw text pasted by the user.
    if not is_valid_url(input_data):
        clean_raw = html.unescape(input_data)       # Convert &nbsp; → space
        clean_raw = clean_raw.replace("\r\n", "\n")  # Strip Windows carriage returns
        return clean_raw.strip()

    # 2. URL Case: Fetch it securely
    try:
        # We use strict timeouts. If the server takes over 5 seconds to reply, we abort.
        async with httpx.AsyncClient(timeout=5.0) as client:
            
            # We enforce max limits by reading bytes as a stream to avoid memory crashing
            async with client.stream("GET", input_data.strip()) as response:
                response.raise_for_status()
                
                # Check headers first if the server provides them
                content_length = response.headers.get("Content-Length")
                if content_length and int(content_length) > MAX_PAYLOAD_SIZE:
                    raise JobDescriptionException("URL payload exceeds the 5MB safe memory limit.")
                
                # Drain the stream chunk by chunk, checking total size on the fly
                html_bytes = b""
                async for chunk in response.aiter_bytes():
                    html_bytes += chunk
                    if len(html_bytes) > MAX_PAYLOAD_SIZE:
                        raise JobDescriptionException("URL payload stream exceeded the 5MB safe memory limit. Aborting.")
                        
            # Safely decode the bytes into an HTML string
            html_content = html_bytes.decode('utf-8', errors='ignore')
            
    except httpx.HTTPStatusError as e:
        raise ScrapingBlockedException(
            "We couldn't access that job posting — the site blocked automated access. "
            "Copy the job description text from the page and paste it directly into the field."
        )
    except (httpx.TimeoutException, httpx.ConnectError):
        raise ScrapingBlockedException(
            "We couldn't reach that URL — the site may be down or blocking requests. "
            "Copy the job description text from the page and paste it directly into the field."
        )
    except httpx.HTTPError:
        raise ScrapingBlockedException(
            "We couldn't load that job posting. "
            "Copy the job description text from the page and paste it directly into the field."
        )

    # 3. Execution Case: Delegate the HTML string to Trafilatura
    clean_text = extract_text_from_html(html_content)
    return clean_text
