"""DuckDuckGo search helpers."""
from __future__ import annotations

import logging
from typing import Iterable, List, Set
from urllib.parse import parse_qs, urlencode, urlparse, unquote

from .fetchers import HTTPFetcher

try:  # pragma: no cover - optional dependency used when available
    from duckduckgo_search import DDGS  # type: ignore
except ImportError:  # pragma: no cover - handled gracefully
    DDGS = None

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class DuckDuckGoSearcher:
    """Search DuckDuckGo for pages that belong to a given domain."""

    def __init__(self, user_agent: str, timeout: float = 15.0):
        self.user_agent = user_agent
        self.fetcher = HTTPFetcher(user_agent=user_agent, timeout=timeout, pause=0.0)
        self._strategies = [
            self._search_via_library,
            self._search_html_endpoint,
            self._search_lite_endpoint,
        ]

    def search(self, domain: str, max_results: int = 50) -> List[str]:
        query = f"site:{domain}"
        found: List[str] = []
        seen: Set[str] = set()
        for strategy in self._strategies:
            try:
                for url in strategy(query, max_results):
                    cleaned = self._clean_result_url(url)
                    if cleaned and cleaned not in seen:
                        seen.add(cleaned)
                        found.append(cleaned)
                        if len(found) >= max_results:
                            break
            except Exception as exc:  # pragma: no cover - defensive logging only
                logger.debug("DuckDuckGo strategy %s failed: %s", strategy.__name__, exc)
            if len(found) >= max_results:
                break
        return found

    # Individual strategies -------------------------------------------------

    def _search_via_library(self, query: str, max_results: int) -> Iterable[str]:
        if DDGS is None:  # pragma: no cover - optional fallback
            return []

        with DDGS() as ddgs:  # type: ignore[attr-defined]
            for result in ddgs.text(query, max_results=max_results):  # type: ignore[call-arg]
                url = result.get("href") or result.get("url")
                cleaned = self._clean_result_url(url) if url else None
                if cleaned:
                    yield cleaned

    def _search_html_endpoint(self, query: str, max_results: int) -> Iterable[str]:
        params = urlencode({"q": query})
        url = f"https://duckduckgo.com/html/?{params}"
        return self._parse_results(url, css_selector="a.result__a", max_results=max_results)

    def _search_lite_endpoint(self, query: str, max_results: int) -> Iterable[str]:
        params = urlencode({"q": query})
        url = f"https://lite.duckduckgo.com/lite/?{params}"
        return self._parse_results(url, css_selector="a", max_results=max_results)

    def _parse_results(self, url: str, css_selector: str, max_results: int) -> Iterable[str]:
        response = self.fetcher.fetch(url)
        soup = BeautifulSoup(response.content, "html.parser")
        count = 0
        for link in soup.select(css_selector):
            href = link.get("href")
            if not href:
                continue
            cleaned = self._clean_result_url(href)
            if cleaned:
                yield cleaned
            count += 1
            if count >= max_results:
                break

    def _clean_result_url(self, url: str | None) -> str | None:
        if not url:
            return None

        parsed = urlparse(url)
        if parsed.netloc.endswith("duckduckgo.com") and parsed.path.startswith("/l/"):
            params = parse_qs(parsed.query)
            target = params.get("uddg")
            if target:
                return unquote(target[0])
        return url
