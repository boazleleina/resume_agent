import httpx
from httpx_sse import connect_sse
import json

def stream_analysis_sync(resume_bytes: bytes, filename: str, content_type: str, jd_input: str):
    """
    Synchronous generator that connects to the FastAPI SSE endpoint
    and yields parsed events as dictionaries.
    """
    url = "http://127.0.0.1:8000/analyze/stream/"
    files = {"file": (filename, resume_bytes, content_type)}
    data = {"jd_input": jd_input}
    
    # The LLM grading step can take over 60 seconds locally. 
    # We need a large read timeout.
    timeout = httpx.Timeout(10.0, read=300.0)
    
    with httpx.Client(timeout=timeout) as client:
        with connect_sse(client, "POST", url, data=data, files=files) as event_source:
            for sse in event_source.iter_sse():
                if sse.event == "error":
                    # Handle backend error events gracefully
                    error_data = json.loads(sse.data)
                    detail = error_data.get("detail", "Unknown error")
                    raise Exception(detail)
                
                if sse.event == "done":
                    yield {"event": "done", "data": {}}
                    break
                
                yield {"event": sse.event, "data": json.loads(sse.data)}
