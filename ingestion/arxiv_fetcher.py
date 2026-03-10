"""
arXiv / bioRxiv fetcher — search & download paper metadata.

Uses the `arxiv` Python library for arXiv; bioRxiv uses their REST API via httpx.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import arxiv
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


@dataclass
class ArxivPaper:
    """Minimal representation of an arXiv / bioRxiv paper."""

    arxiv_id: str
    title: str
    abstract: str
    authors: list[str] = field(default_factory=list)
    published: Optional[str] = None
    pdf_url: Optional[str] = None
    doi: Optional[str] = None
    source: str = "arxiv"  # "arxiv" or "biorxiv"


# ── arXiv ─────────────────────────────────────────────────────────────────────


def search_arxiv(query: str, max_results: int = 20) -> list[ArxivPaper]:
    """Search arXiv and return paper metadata."""
    client = arxiv.Client()
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance,
    )

    papers: list[ArxivPaper] = []
    for result in client.results(search):
        papers.append(
            ArxivPaper(
                arxiv_id=result.entry_id.split("/abs/")[-1],
                title=result.title,
                abstract=result.summary,
                authors=[a.name for a in result.authors],
                published=result.published.isoformat() if result.published else None,
                pdf_url=result.pdf_url,
                doi=result.doi,
                source="arxiv",
            )
        )

    logger.info("arXiv search '%s' → %d results", query, len(papers))
    return papers


# ── bioRxiv ───────────────────────────────────────────────────────────────────

BIORXIV_API = "https://api.biorxiv.org/details/biorxiv"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def search_biorxiv(
    query: str,
    server: str = "biorxiv",
    interval: str = "2023-01-01/2026-03-09",
    max_results: int = 20,
) -> list[ArxivPaper]:
    """
    Search bioRxiv / medRxiv recent papers by date interval.

    The bioRxiv API doesn't support keyword search natively, so we fetch
    recent papers in the interval and do a simple title/abstract filter.
    For production, pair with Semantic Scholar or OpenAlex for keyword search.
    """
    url = f"https://api.biorxiv.org/details/{server}/{interval}/0/{max_results}"
    resp = httpx.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    query_lower = query.lower()
    papers: list[ArxivPaper] = []

    for item in data.get("collection", []):
        title = item.get("title", "")
        abstract = item.get("abstract", "")
        if query_lower not in title.lower() and query_lower not in abstract.lower():
            continue

        papers.append(
            ArxivPaper(
                arxiv_id=item.get("doi", ""),
                title=title,
                abstract=abstract,
                authors=item.get("authors", "").split("; "),
                published=item.get("date", ""),
                pdf_url=None,
                doi=item.get("doi"),
                source="biorxiv",
            )
        )

    logger.info("bioRxiv search '%s' → %d results", query, len(papers))
    return papers
