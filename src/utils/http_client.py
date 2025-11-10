from typing import Optional
import logging
import os
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import requests
from requests import Response

logger = logging.getLogger(__name__)

class HttpError(Exception):
    pass

class HttpClient:
    """
    Minimal HTTP client with retries. Supports:
    - Standard GET requests with cookies and user-agent
    - file:// scheme for local HTML testing
    """

    def __init__(self, cookies: str = "", user_agent: str = "") -> None:
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": user_agent
                or "StoreleadsScraper/1.0 (+https://example.com/bot)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            }
        )
        if cookies:
            self.session.headers.update({"Cookie": cookies})

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.4, min=0.4, max=3),
        retry=retry_if_exception_type(HttpError),
    )
    def _do_get(self, url: str) -> Response:
        if url.startswith("file://"):
            # Local file read (for offline testing)
            path = url.replace("file://", "", 1)
            if not os.path.exists(path):
                raise HttpError(f"Local file not found: {path}")
            with open(path, "rb") as f:
                content = f.read()
            # Fake response object
            r = requests.Response()
            r.status_code = 200
            r._content = content
            r.url = url
            r.headers["Content-Type"] = "text/html; charset=utf-8"
            return r

        r = self.session.get(url, timeout=20)
        if r.status_code >= 400:
            raise HttpError(f"GET {url} -> {r.status_code}")
        return r

    def get_text(self, url: str, encoding: Optional[str] = None) -> str:
        resp = self._do_get(url)
        if encoding:
            resp.encoding = encoding
        return resp.text