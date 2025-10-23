"""Command line interface for the website scraper."""
from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import List
from urllib.parse import urlparse

from .duckduckgo import DuckDuckGoSearcher
from .exporters import PDFExporter, TextExporter
from .fetchers import HTTPFetcher
from .scraper import SiteScraper

DEFAULT_USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 " \
    "(KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"


def parse_args(argv: List[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape an entire site using DuckDuckGo results")
    parser.add_argument("url", help="Start URL or domain to scrape")
    parser.add_argument("--output", type=Path, default=Path("output"), help="Directory to store the exports")
    parser.add_argument("--max-pages", type=int, default=50, help="Maximum number of pages to scrape")
    parser.add_argument("--max-search-results", type=int, default=100, help="Number of DuckDuckGo results to consider")
    parser.add_argument("--timeout", type=float, default=15.0, help="Timeout for HTTP requests in seconds")
    parser.add_argument("--pause", type=float, default=1.0, help="Delay between HTTP requests in seconds")
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT, help="Custom User-Agent header")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    return parser.parse_args(argv)


def main(argv: List[str] | None = None) -> None:
    args = parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s: %(message)s")

    base_url = _normalize_base_url(args.url)
    domain = urlparse(base_url).netloc

    logging.info("Using DuckDuckGo to search for pages under %s", domain)
    fetcher = HTTPFetcher(user_agent=args.user_agent, timeout=args.timeout, pause=args.pause)
    searcher = DuckDuckGoSearcher(user_agent=args.user_agent, timeout=args.timeout)
    search_results = searcher.search(domain, max_results=args.max_search_results)

    seed_urls = [base_url]
    for result in search_results:
        if urlparse(result).netloc == domain and result not in seed_urls:
            seed_urls.append(result)

    scraper = SiteScraper(base_url=base_url, fetcher=fetcher, max_pages=args.max_pages)
    pages = scraper.scrape(seed_urls)

    if not pages:
        logging.warning("No pages were scraped. Please check the URL or increase the limits.")
        return

    output_dir: Path = args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    text_path = output_dir / "scraped_content.txt"
    pdf_path = output_dir / "scraped_content.pdf"

    text_exporter = TextExporter()
    text_exporter.export(pages, text_path)
    logging.info("Saved text export to %s", text_path)

    pdf_exporter = PDFExporter()
    strategy = pdf_exporter.export(pages, pdf_path)
    logging.info("Saved PDF export to %s using %s", pdf_path, strategy)

    logging.info("Scraped %d pages.", len(pages))


def _normalize_base_url(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.scheme:
        parsed = parsed._replace(scheme="https")
    if not parsed.netloc:
        parsed = parsed._replace(netloc=parsed.path, path="")
    return parsed.geturl()


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
