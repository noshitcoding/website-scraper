"""Website scraping core logic."""
from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Set
from urllib.parse import urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup

from .fetchers import FetchResult, HTTPFetcher

logger = logging.getLogger(__name__)


@dataclass
class PageContent:
    """Structured representation of a single scraped page."""

    url: str
    title: str
    text: str
    raw_html: str
    fetch_strategy: str


class SiteScraper:
    """Scrape a website breadth-first and collect text content."""

    def __init__(
        self,
        base_url: str,
        fetcher: HTTPFetcher,
        *,
        max_pages: int = 50,
        allowed_domains: Optional[Sequence[str]] = None,
    ) -> None:
        self.base_url = base_url
        self.fetcher = fetcher
        self.max_pages = max_pages
        parsed = urlparse(base_url)
        default_domains = {parsed.netloc}
        if parsed.netloc.startswith("www."):
            default_domains.add(parsed.netloc[4:])
        elif parsed.netloc:
            default_domains.add(f"www.{parsed.netloc}")
        self.allowed_domains: Set[str] = set(allowed_domains or []) or default_domains

    def scrape(self, seed_urls: Sequence[str]) -> List[PageContent]:
        queue: deque[str] = deque()
        visited: Set[str] = set()
        for url in seed_urls:
            normalized = self._normalize(url)
            if normalized and normalized not in visited:
                queue.append(normalized)

        results: List[PageContent] = []

        while queue and len(results) < self.max_pages:
            url = queue.popleft()
            if url in visited:
                continue
            if not self._is_allowed(url):
                logger.debug("Skipping %s because it is outside the allowed domains", url)
                continue

            visited.add(url)
            try:
                fetch_result = self.fetcher.fetch(url)
            except Exception as exc:  # pragma: no cover - network dependent
                logger.warning("Failed to fetch %s: %s", url, exc)
                continue

            page = self._parse_page(fetch_result)
            results.append(page)

            for link in self._extract_links(page.raw_html, page.url):
                normalized_link = self._normalize(link)
                if not normalized_link:
                    continue
                if normalized_link in visited:
                    continue
                if normalized_link in queue:
                    continue
                queue.append(normalized_link)

        return results

    # Helpers -----------------------------------------------------------------

    def _parse_page(self, fetch_result: FetchResult) -> PageContent:
        soup = BeautifulSoup(fetch_result.content, "html.parser")
        title = soup.title.string.strip() if soup.title and soup.title.string else fetch_result.url
        text_parts = [segment.strip() for segment in soup.stripped_strings]
        text = "\n".join(part for part in text_parts if part)
        return PageContent(
            url=fetch_result.url,
            title=title,
            text=text,
            raw_html=fetch_result.content,
            fetch_strategy=fetch_result.strategy,
        )

    def _extract_links(self, html: str, base_url: str) -> Iterable[str]:
        soup = BeautifulSoup(html, "html.parser")
        for link in soup.find_all("a"):
            href = link.get("href")
            if not href:
                continue
            absolute = urljoin(base_url, href)
            if self._is_allowed(absolute):
                yield absolute

    def _is_allowed(self, url: str) -> bool:
        parsed = urlparse(url)
        if not parsed.scheme.startswith("http"):
            return False
        return parsed.netloc in self.allowed_domains

    def _normalize(self, url: str) -> Optional[str]:
        if not url:
            return None
        parsed = urlparse(url)
        if not parsed.scheme:
            parsed = parsed._replace(scheme=urlparse(self.base_url).scheme)
        if not parsed.netloc:
            parsed = parsed._replace(netloc=urlparse(self.base_url).netloc)
        if not parsed.scheme.startswith("http"):
            return None
        normalized_path = parsed.path or "/"
        normalized = parsed._replace(fragment="", path=normalized_path)
        return urlunparse(normalized)
