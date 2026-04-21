import urllib.parse
import ipaddress
import trafilatura
from app.domain.exceptions import ResumeAppError

class JobDescriptionException(ResumeAppError):
    """Raised when Job Description specific parsing fails."""
    pass

def is_valid_url(text: str) -> bool:
    """
    Heuristic to determine if the input text is a URL versus raw pasted text.
    Must start with http/https and contain no whitespace to prevent 
    a paragraph starting with a URL from being routed to the HTTP client.
    """
    text = text.strip()
    if not (text.startswith("http://") or text.startswith("https://")):
        return False
    
    if " " in text or "\n" in text:
        return False
        
    try:
        result = urllib.parse.urlparse(text)
        if not all([result.scheme, result.netloc]):
            return False
            
        domain = result.netloc.split(':')[0].lower()
        
        # Block explicit local hostnames
        if domain in ("localhost", "local", "invalid", "test"):
            return False
            
        # Block explicit private IPs
        try:
            ip = ipaddress.ip_address(domain)
            if ip.is_private or ip.is_loopback or ip.is_link_local:
                return False
        except ValueError:
            # Not an IP address string, which means it's a domain name
            pass
            
        return True
    except ValueError:
        return False

def extract_text_from_html(html_content: str) -> str:
    """
    Uses Trafilatura to zero-shot extract main body text from raw HTML.
    Automatically strips navigation, headers, footers, and advertisements.
    """
    if not html_content or not html_content.strip():
        raise JobDescriptionException("HTML content provided to parser is empty.")

    extracted_text = trafilatura.extract(
        html_content, 
        include_links=True,   # Helpful if the JD links out to specific tools or requirements
        include_images=False, 
        include_tables=True   # Some companies put requirements in tables
    )
    
    if not extracted_text:
        raise JobDescriptionException("Parser could not identify the main body text of the webpage. This might be a highly dynamic JavaScript page.")
        
    return extracted_text.strip()
