"""HTTP fetching utilities with multiple fallbacks."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class FetchResult:
    """Container for a fetched HTTP response."""

    url: str
    status_code: int
    content: str
    strategy: str


class HTTPFetcher:
    """Try several libraries to download web content.

    The fetcher will try the available strategies in order until one succeeds.
    This makes the downloader resilient against environments where a
    particular HTTP client is not available or fails for a specific request.
    """

    def __init__(self, user_agent: str, timeout: float = 15.0, pause: float = 1.0):
        self.user_agent = user_agent
        self.timeout = timeout
        self.pause = pause
        self._strategies: List[Callable[[str], Optional[FetchResult]]] = [
            self._fetch_with_requests,
            self._fetch_with_httpx,
            self._fetch_with_urllib,
        ]

    def fetch(self, url: str) -> FetchResult:
        last_error: Optional[Exception] = None
        for strategy in self._strategies:
            try:
                result = strategy(url)
                if result:
                    if self.pause:
                        time.sleep(self.pause)
                    return result
            except Exception as exc:  # pragma: no cover - defensive
                logger.debug("%s failed for %s: %s", strategy.__name__, url, exc)
                last_error = exc
        raise RuntimeError(f"Failed to fetch {url}") from last_error

    # Individual strategies -------------------------------------------------

    def _fetch_with_requests(self, url: str) -> Optional[FetchResult]:
        try:
            import requests
        except ImportError:  # pragma: no cover - fallback only
            return None

        headers = {"User-Agent": self.user_agent}
        response = requests.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        return FetchResult(url=url, status_code=response.status_code, content=response.text, strategy="requests")

    def _fetch_with_httpx(self, url: str) -> Optional[FetchResult]:
        try:
            import httpx
        except ImportError:  # pragma: no cover - fallback only
            return None

        headers = {"User-Agent": self.user_agent}
        with httpx.Client(follow_redirects=True, timeout=self.timeout, headers=headers) as client:
            response = client.get(url)
            response.raise_for_status()
            text = response.text
            return FetchResult(url=url, status_code=response.status_code, content=text, strategy="httpx")

    def _fetch_with_urllib(self, url: str) -> Optional[FetchResult]:
        from urllib import request

        req = request.Request(url, headers={"User-Agent": self.user_agent})
        with request.urlopen(req, timeout=self.timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            text = response.read().decode(charset, errors="replace")
            status = getattr(response, "status", 200)
            return FetchResult(url=url, status_code=status, content=text, strategy="urllib")
