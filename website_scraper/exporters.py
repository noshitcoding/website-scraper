"""Export scraped content into multiple file formats."""
from __future__ import annotations

import logging
import textwrap
from pathlib import Path
from typing import Iterable, Sequence

from .scraper import PageContent

logger = logging.getLogger(__name__)


class TextExporter:
    """Write the collected pages into a single UTF-8 encoded text file."""

    def render(self, pages: Sequence[PageContent]) -> str:
        """Return the textual representation used for exports.

        The render step is split out so that the CLI and HTTP API can both
        reuse the formatting logic without duplicating file system access.
        """

        lines: list[str] = []
        for page in pages:
            lines.append(f"# {page.title}\n")
            lines.append(f"URL: {page.url}\n")
            lines.append(f"Fetched via: {page.fetch_strategy}\n\n")
            lines.append(page.text)
            lines.append("\n\n" + "=" * 80 + "\n\n")
        return "".join(lines)

    def export(self, pages: Sequence[PageContent], destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        rendered = self.render(pages)
        with destination.open("w", encoding="utf-8") as handle:
            handle.write(rendered)
    def export(self, pages: Sequence[PageContent], destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("w", encoding="utf-8") as handle:
            for page in pages:
                handle.write(f"# {page.title}\n")
                handle.write(f"URL: {page.url}\n")
                handle.write(f"Fetched via: {page.fetch_strategy}\n\n")
                handle.write(page.text)
                handle.write("\n\n" + "=" * 80 + "\n\n")


class PDFExporter:
    """Persist scraped pages into a PDF document using multiple backends."""

    def __init__(self) -> None:
        self._strategies = [
            self._export_with_fpdf,
            self._export_with_reportlab,
        ]

    def export(self, pages: Sequence[PageContent], destination: Path) -> str:
        destination.parent.mkdir(parents=True, exist_ok=True)
        last_error: Exception | None = None
        for strategy in self._strategies:
            try:
                strategy(pages, destination)
                return strategy.__name__
            except ImportError as exc:  # pragma: no cover - optional fallback
                logger.debug("PDF strategy %s not available: %s", strategy.__name__, exc)
                last_error = exc
            except Exception as exc:  # pragma: no cover - runtime fallback
                logger.debug("PDF strategy %s failed: %s", strategy.__name__, exc)
                last_error = exc
        raise RuntimeError("Unable to export PDF with any available backend") from last_error

    def _export_with_fpdf(self, pages: Sequence[PageContent], destination: Path) -> None:
        from fpdf import FPDF  # type: ignore

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_margins(left=15, top=15, right=15)
        for page in pages:
            pdf.add_page()
            pdf.set_font("Arial", "B", 14)
            pdf.multi_cell(0, 10, page.title)
            pdf.set_font("Arial", size=10)
            pdf.multi_cell(0, 8, page.url)
            pdf.ln(4)
            pdf.set_font("Arial", size=12)
            wrapped = _wrap_text_for_pdf(page.text)
            for paragraph in wrapped:
                pdf.multi_cell(0, 7, paragraph)
                pdf.ln(1)
        pdf.output(str(destination))

    def _export_with_reportlab(self, pages: Sequence[PageContent], destination: Path) -> None:
        from reportlab.lib.pagesizes import letter  # type: ignore
        from reportlab.pdfgen import canvas  # type: ignore

        page_width, page_height = letter
        canvas_obj = canvas.Canvas(str(destination), pagesize=letter)
        text_object = canvas_obj.beginText(40, page_height - 50)
        text_object.setFont("Helvetica-Bold", 14)
        for idx, page in enumerate(pages, start=1):
            if idx > 1:
                canvas_obj.drawText(text_object)
                canvas_obj.showPage()
                text_object = canvas_obj.beginText(40, page_height - 50)
                text_object.setFont("Helvetica-Bold", 14)
            text_object.textLine(page.title)
            text_object.setFont("Helvetica", 10)
            text_object.textLine(page.url)
            text_object.setFont("Helvetica", 12)
            for paragraph in _wrap_text_for_pdf(page.text):
                for line in textwrap.wrap(paragraph, width=90):
                    text_object.textLine(line)
                text_object.textLine("")
        canvas_obj.drawText(text_object)
        canvas_obj.save()

    def export_to_bytes(self, pages: Sequence[PageContent]) -> tuple[str, bytes]:
        """Return the PDF bytes alongside the strategy that produced them."""

        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as tmpdir:
            destination = Path(tmpdir) / "scraped_content.pdf"
            strategy = self.export(pages, destination)
            data = destination.read_bytes()
        return strategy, data


def _wrap_text_for_pdf(text: str, width: int = 95) -> Iterable[str]:
    paragraphs = text.split("\n")
    for paragraph in paragraphs:
        cleaned = paragraph.strip()
        if not cleaned:
            yield ""
            continue
        yield from textwrap.wrap(cleaned, width=width) or [cleaned]
