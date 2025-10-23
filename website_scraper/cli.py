"""Command line interface for the website scraper."""
from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import List

from .services import DEFAULT_USER_AGENT, ScrapeParameters, perform_scrape
from .utils import normalize_base_url


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

    params = ScrapeParameters(
        url=args.url,
        max_pages=args.max_pages,
        max_search_results=args.max_search_results,
        timeout=args.timeout,
        pause=args.pause,
        user_agent=args.user_agent,
    )

    outcome = perform_scrape(params)

    if not outcome.pages:
        logging.warning("No pages were scraped. Please check the URL or increase the limits.")
        return

    output_dir: Path = args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    text_path = output_dir / "scraped_content.txt"
    pdf_path = output_dir / "scraped_content.pdf"

    text_path.write_text(outcome.rendered_text, encoding="utf-8")
    logging.info("Saved text export to %s", text_path)

    pdf_path.write_bytes(outcome.pdf_bytes)
    logging.info("Saved PDF export to %s using %s", pdf_path, outcome.pdf_strategy)

    logging.info("Scraped %d pages.", len(outcome.pages))


def _normalize_base_url(url: str) -> str:
    """Backward compatible shim for earlier CLI scripts."""

    return normalize_base_url(url)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
