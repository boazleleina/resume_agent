import urllib.parse
import ipaddress
import json
import trafilatura
from bs4 import BeautifulSoup, NavigableString
from app.domain.exceptions import ResumeAppError

class JobDescriptionException(ResumeAppError):
    """Raised when Job Description specific parsing fails."""
    pass


class ScrapingBlockedException(JobDescriptionException):
    """Raised when a URL cannot be scraped (blocked, paywalled, JS-only)."""
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


# ---------------------------------------------------------------------------
# Layer 1: JSON-LD JobPosting Extraction
# ---------------------------------------------------------------------------
def _extract_jsonld_description(html_content: str) -> str | None:
    """
    Many job sites (LinkedIn, Indeed, Greenhouse) embed a hidden 
    <script type="application/ld+json"> tag containing the full job posting
    as structured JSON following the Schema.org JobPosting standard.
    If it exists, this is the cleanest possible source.
    
    The 'description' field inside JSON-LD often contains raw HTML tags
    (e.g. <strong>, <ul>, <li>), so we strip them into plain text.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    for script_tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script_tag.string or "")
            
            # Handle both single objects and arrays of objects
            if isinstance(data, list):
                for item in data:
                    if item.get("@type") == "JobPosting":
                        raw_desc = item.get("description", "")
                        return _strip_html_tags(raw_desc)
            elif isinstance(data, dict):
                if data.get("@type") == "JobPosting":
                    raw_desc = data.get("description", "")
                    return _strip_html_tags(raw_desc)
        except (json.JSONDecodeError, AttributeError):
            continue
            
    return None


def _strip_html_tags(text: str) -> str:
    """
    Converts any embedded HTML (e.g. <strong>Python</strong>, <li>FastAPI</li>)
    into clean, readable plain text. Uses BeautifulSoup to parse the HTML
    and extract text with newline separators so list items stay on their own lines.
    """
    if not text:
        return ""
    return BeautifulSoup(text, 'html.parser').get_text(separator='\n', strip=True)


# ---------------------------------------------------------------------------
# Layer 2: Trafilatura Recall-Mode Extraction
# ---------------------------------------------------------------------------
def _extract_trafilatura_recall(html_content: str) -> str | None:
    """
    Runs Trafilatura in 'recall' mode, which makes it greedy — it keeps
    MORE text rather than aggressively pruning. Combined with 
    include_formatting=True, it preserves heading hierarchy instead of 
    flattening everything into a single paragraph.
    """
    result = trafilatura.extract(
        html_content,
        favor_recall=True,       # Keep more text, even if some noise slips through
        include_formatting=True, # Preserve heading markers and list structure
        include_links=True,
        include_images=False,
        include_tables=True
    )
    return result if result else None


# ---------------------------------------------------------------------------
# Layer 3: BeautifulSoup Heading Walker
# ---------------------------------------------------------------------------
def _extract_bs4_heading_sections(html_content: str) -> str | None:
    """
    Safety net for the exact bug you found: when H1 and H3 tags are stacked
    back-to-back, Trafilatura thinks it's a nav menu and deletes the section.
    
    This function walks every heading tag (h1-h6), and for each heading,
    collects everything that follows it (paragraphs, lists, bold text)
    until it hits the next heading. This guarantees requirement lists 
    under headings like 'Must-haves:' are never dropped.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove pure noise elements first
    for element in soup(["script", "style", "nav", "footer", "meta", "noscript"]):
        element.decompose()
    
    heading_tags = {"h1", "h2", "h3", "h4", "h5", "h6"}
    sections = []
    
    for heading in soup.find_all(heading_tags):
        heading_text = heading.get_text(strip=True)
        if not heading_text:
            continue
            
        # Collect all sibling content until the next heading
        section_lines = [heading_text]
        
        for sibling in heading.next_siblings:
            # Stop when we hit another heading
            if hasattr(sibling, 'name') and sibling.name in heading_tags:
                break
            
            # Skip empty whitespace nodes
            if isinstance(sibling, NavigableString):
                text = sibling.strip()
                if text:
                    section_lines.append(text)
                continue
                
            # Extract text from paragraphs, lists, divs, etc.
            if hasattr(sibling, 'get_text'):
                text = sibling.get_text(separator='\n', strip=True)
                if text:
                    section_lines.append(text)
        
        if len(section_lines) > 1:  # Only keep sections that have content after the heading
            sections.append('\n'.join(section_lines))
    
    if sections:
        return '\n\n'.join(sections)
    return None


# ---------------------------------------------------------------------------
# Layer 4: Merge and Deduplicate
# ---------------------------------------------------------------------------
def _normalize_for_dedup(line: str) -> str:
    """
    Strips formatting noise so two lines that say the same thing
    but differ by a leading bullet or bold markers are caught as duplicates.
    
    Examples:
      '- Build integrations with Tableau'  ->  'build integrations with tableau'
      '**Build integrations with Tableau**' ->  'build integrations with tableau'
      '1. Build integrations with Tableau'  ->  'build integrations with tableau'
    """
    import re
    text = line.strip()
    text = re.sub(r'^\s*[-*•]\s+', '', text)       # Strip leading bullets: - * •
    text = re.sub(r'^\s*\d+\.\s+', '', text)        # Strip numbered lists: 1. 2.
    text = text.replace('**', '')                     # Strip bold markers
    text = text.replace('__', '')                     # Strip underline markers
    return text.strip().lower()


def _merge_and_deduplicate(*text_sources: str | None) -> str:
    """
    Takes text from all extraction layers, splits into individual lines,
    normalizes each line (stripping bullets, bold, casing) for comparison,
    and removes duplicates while preserving the original formatting of
    the first occurrence. This prevents the LLM context window from being
    bloated with redundant content.
    """
    seen_normalized = set()
    merged_lines = []
    
    for source in text_sources:
        if not source:
            continue
        for line in source.split('\n'):
            clean_line = line.strip()
            if not clean_line:
                continue
            
            normalized = _normalize_for_dedup(clean_line)
            if normalized and normalized not in seen_normalized:
                seen_normalized.add(normalized)
                merged_lines.append(clean_line)
    
    return '\n'.join(merged_lines)


# ---------------------------------------------------------------------------
# Main Extraction Orchestrator
# ---------------------------------------------------------------------------
def extract_text_from_html(html_content: str) -> str:
    """
    4-layer extraction pipeline for Job Descriptions:
      1. Try JSON-LD JobPosting (cleanest structured data)
      2. Run Trafilatura in recall mode (greedy text extraction)
      3. Walk headings with BS4 (catches stacked H1→H3 requirement lists)
      4. Merge all results and deduplicate lines
    """
    if not html_content or not html_content.strip():
        raise JobDescriptionException("HTML content provided to parser is empty.")

    # Layer 1: Check for structured JSON-LD data
    jsonld_text = _extract_jsonld_description(html_content)
    
    # Layer 2: Trafilatura recall-mode pass
    trafilatura_text = _extract_trafilatura_recall(html_content)
    
    # Layer 3: BS4 heading walker pass
    bs4_text = _extract_bs4_heading_sections(html_content)
    
    # Layer 4: Merge everything together
    final_text = _merge_and_deduplicate(jsonld_text, trafilatura_text, bs4_text)
    
    if not final_text:
        raise ScrapingBlockedException(
            "We couldn't extract text from that page — it may load content dynamically with JavaScript. "
            "Copy the job description text from the page and paste it directly into the field."
        )
        
    return final_text

