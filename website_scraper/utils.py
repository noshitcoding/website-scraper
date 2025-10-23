"""Utility helpers for the website scraper package."""
from __future__ import annotations

from urllib.parse import urlparse


def normalize_base_url(url: str) -> str:
    """Ensure the provided URL has a scheme and network location.

    DuckDuckGo search results often omit the protocol. This helper mirrors the
    CLI behaviour by upgrading bare domains to HTTPS and cleaning up the
    resulting URL for downstream components.
    """

    parsed = urlparse(url)
    if not parsed.scheme:
        parsed = parsed._replace(scheme="https")
    if not parsed.netloc:
        parsed = parsed._replace(netloc=parsed.path, path="")
    return parsed.geturl()
