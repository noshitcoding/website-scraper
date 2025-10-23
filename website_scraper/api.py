"""FastAPI service exposing the website scraper over HTTP."""
from __future__ import annotations

from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .services import (
    DEFAULT_USER_AGENT,
    ScrapeOutcome,
    ScrapeParameters,
    perform_scrape,
)

app = FastAPI(title="Website Scraper", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PageInfo(BaseModel):
    """Serialisable information about a scraped page."""

    url: str
    title: str
    fetch_strategy: str


class ScrapeRequest(BaseModel):
    """Parameters accepted by the scrape endpoint."""

    url: str = Field(..., description="URL or domain to scrape")
    max_pages: int = Field(50, ge=1, le=500, description="Maximum number of pages to crawl")
    max_search_results: int = Field(
        100, ge=1, le=200, description="How many DuckDuckGo results should be inspected"
    )
    timeout: float = Field(15.0, gt=0, description="HTTP timeout in seconds")
    pause: float = Field(1.0, ge=0, description="Delay between HTTP requests in seconds")
    user_agent: str = Field(DEFAULT_USER_AGENT, description="User-Agent header to send")


class ScrapeResponse(BaseModel):
    """Payload returned by a successful scrape."""

    base_url: str
    domain: str
    page_count: int
    pdf_strategy: str
    text_content: str
    pdf_base64: str
    pages: List[PageInfo]


@app.get("/", tags=["meta"])
async def root() -> dict[str, str]:
    """Simple landing endpoint used for smoke testing."""

    return {"message": "Website scraper API is running."}


@app.get("/api/health", tags=["meta"])
async def health() -> dict[str, str]:
    """Return a healthy status payload."""

    return {"status": "ok"}


@app.post("/api/scrape", response_model=ScrapeResponse, tags=["scrape"])
async def scrape_site(request: ScrapeRequest) -> ScrapeResponse:
    """Trigger the scraper and return the exported artifacts."""

    params = ScrapeParameters(
        url=request.url,
        max_pages=request.max_pages,
        max_search_results=request.max_search_results,
        timeout=request.timeout,
        pause=request.pause,
        user_agent=request.user_agent,
    )

    outcome: ScrapeOutcome = await run_in_threadpool(perform_scrape, params)

    if not outcome.pages:
        raise HTTPException(status_code=404, detail="No pages could be scraped for the provided URL")

    return ScrapeResponse(
        base_url=outcome.base_url,
        domain=outcome.domain,
        page_count=len(outcome.pages),
        pdf_strategy=outcome.pdf_strategy,
        text_content=outcome.rendered_text,
        pdf_base64=outcome.pdf_as_base64(),
        pages=[
            PageInfo(url=page.url, title=page.title, fetch_strategy=page.fetch_strategy)
            for page in outcome.serialized_pages
        ],
    )


def get_app() -> FastAPI:
    """Expose the ASGI app for external runners."""

    return app


if __name__ == "__main__":  # pragma: no cover - manual launch helper
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8006)
