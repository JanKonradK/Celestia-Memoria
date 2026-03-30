"""PDF to Markdown conversion preserving document structure."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

import pymupdf4llm

logger = logging.getLogger(__name__)


def parse_pdf_to_markdown(file_path: str | Path) -> str:
    """Convert a PDF file to structured Markdown using pymupdf4llm.

    Preserves headings, tables, lists, and page boundaries. Returns the full
    markdown text of the document.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"PDF not found: {file_path}")
    if not file_path.suffix.lower() == ".pdf":
        raise ValueError(f"Expected a PDF file, got: {file_path.suffix}")

    logger.info("Parsing PDF: %s (%d bytes)", file_path.name, file_path.stat().st_size)

    md_text = pymupdf4llm.to_markdown(
        str(file_path),
        show_progress=False,
    )

    logger.info(
        "Parsed %s: %d characters of markdown", file_path.name, len(md_text)
    )
    return md_text


async def parse_pdf_from_url(url: str, filename: str = "document.pdf") -> str:
    """Download a PDF from a URL and convert it to Markdown."""
    import httpx

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.get(url)
        response.raise_for_status()

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(response.content)
        tmp_path = tmp.name

    try:
        return parse_pdf_to_markdown(tmp_path)
    finally:
        Path(tmp_path).unlink(missing_ok=True)
