"""High level orchestration helpers for scraping and exporting websites."""
from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from typing import List, Sequence
from urllib.parse import urlparse

from .duckduckgo import DuckDuckGoSearcher
from .exporters import PDFExporter, TextExporter
from .fetchers import HTTPFetcher
from .scraper import PageContent, SiteScraper
from .utils import normalize_base_url

logger = logging.getLogger(__name__)


DEFAULT_USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 " \
    "(KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"


@dataclass(slots=True)
class ScrapeParameters:
    """Configuration options accepted by the orchestrator."""

    url: str
    max_pages: int = 50
    max_search_results: int = 100
    timeout: float = 15.0
    pause: float = 1.0
    user_agent: str = DEFAULT_USER_AGENT


@dataclass(slots=True)
class ScrapedPage:
    """Serializable snapshot of a scraped page."""

    url: str
    title: str
    fetch_strategy: str

    @classmethod
    def from_page(cls, page: PageContent) -> "ScrapedPage":
        return cls(url=page.url, title=page.title, fetch_strategy=page.fetch_strategy)


@dataclass(slots=True)
class ScrapeOutcome:
    """Result of a scraping session."""

    base_url: str
    domain: str
    pages: Sequence[PageContent]
    rendered_text: str
    pdf_bytes: bytes
    pdf_strategy: str
    serialized_pages: Sequence[ScrapedPage]

    def text_as_base64(self) -> str:
        return base64.b64encode(self.rendered_text.encode("utf-8")).decode("ascii")

    def pdf_as_base64(self) -> str:
        if not self.pdf_bytes:
            return ""
        return base64.b64encode(self.pdf_bytes).decode("ascii")


def perform_scrape(params: ScrapeParameters) -> ScrapeOutcome:
    """Execute the full search + scrape + export pipeline."""

    base_url = normalize_base_url(params.url)
    domain = urlparse(base_url).netloc

    logger.info("Using DuckDuckGo to search for pages under %s", domain)

    fetcher = HTTPFetcher(user_agent=params.user_agent, timeout=params.timeout, pause=params.pause)
    searcher = DuckDuckGoSearcher(user_agent=params.user_agent, timeout=params.timeout)
    search_results = searcher.search(domain, max_results=params.max_search_results)

    seed_urls: List[str] = [base_url]
    for result in search_results:
        if urlparse(result).netloc == domain and result not in seed_urls:
            seed_urls.append(result)

    scraper = SiteScraper(base_url=base_url, fetcher=fetcher, max_pages=params.max_pages)
    pages = scraper.scrape(seed_urls)

    text_exporter = TextExporter()
    rendered_text = text_exporter.render(pages)

    pdf_exporter = PDFExporter()
    pdf_bytes: bytes = b""
    pdf_strategy = ""
    if pages:
        pdf_strategy, pdf_bytes = pdf_exporter.export_to_bytes(pages)

    serialized_pages = [ScrapedPage.from_page(page) for page in pages]

    return ScrapeOutcome(
        base_url=base_url,
        domain=domain,
        pages=pages,
        rendered_text=rendered_text,
        pdf_bytes=pdf_bytes,
        pdf_strategy=pdf_strategy,
        serialized_pages=serialized_pages,
    )
