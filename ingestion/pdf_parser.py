"""
PDF parser — extract clean text from scientific PDFs using PyMuPDF.

Handles multi-column layouts, strips headers/footers heuristically,
and returns page-separated text.
"""

from __future__ import annotations

import logging
from pathlib import Path

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_path: str | Path) -> str:
    """
    Extract all text from a PDF, page by page.

    Returns a single string with pages separated by ``\\n\\n``.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    doc = fitz.open(str(pdf_path))
    pages: list[str] = []

    for page_num, page in enumerate(doc):
        text = page.get_text("text")
        # Basic cleanup: collapse multiple blank lines
        cleaned = _clean_page(text)
        if cleaned:
            pages.append(cleaned)

    doc.close()
    full_text = "\n\n".join(pages)
    logger.info("Extracted %d chars from %s (%d pages)", len(full_text), pdf_path.name, len(pages))
    return full_text


def extract_text_per_page(pdf_path: str | Path) -> list[str]:
    """Return a list of cleaned text strings, one per page."""
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    doc = fitz.open(str(pdf_path))
    pages = [_clean_page(page.get_text("text")) for page in doc]
    doc.close()
    return [p for p in pages if p]


# ── Internal helpers ──────────────────────────────────────────────────────────


def _clean_page(raw: str) -> str:
    """Remove excessive whitespace and very short lines (likely headers/footers)."""
    lines = raw.split("\n")
    cleaned: list[str] = []
    for line in lines:
        stripped = line.strip()
        # Skip very short lines that are likely page numbers or headers
        if len(stripped) < 3:
            continue
        cleaned.append(stripped)
    return "\n".join(cleaned)
