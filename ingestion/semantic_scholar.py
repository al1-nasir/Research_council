"""
Semantic Scholar fetcher — search paper metadata via Semantic Scholar API.

API: https://api.semanticscholar.org/graph/v1/
Free tier: 100 requests/minute with API key
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import httpx

from config import SEMANTIC_SCHOLAR_API_KEY

logger = logging.getLogger(__name__)

SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1"
HEADERS = {}
if SEMANTIC_SCHOLAR_API_KEY:
    HEADERS["x-api-key"] = SEMANTIC_SCHOLAR_API_KEY


@dataclass
class SemanticScholarPaper:
    """Minimal representation of a Semantic Scholar paper."""

    paper_id: str
    title: str
    abstract: str = ""
    authors: list[str] = field(default_factory=list)
    year: Optional[int] = None
    venue: str = ""
    doi: Optional[str] = None
    citation_count: int = 0
    url: Optional[str] = None
    pdf_url: Optional[str] = None
    fields_of_study: list[str] = field(default_factory=list)
    source: str = "semantic_scholar"


def search_semantic_scholar(
    query: str,
    max_results: int = 20,
    fields: str = "paperId,title,abstract,authors,year,venue,doi,citationCount,url,openAccessPdf,fieldsOfStudy",
) -> list[SemanticScholarPaper]:
    """Search Semantic Scholar and return paper metadata."""
    papers: list[SemanticScholarPaper] = []

    try:
        params = {
            "query": query,
            "limit": max_results,
            "fields": fields,
            "offset": 0,
        }

        with httpx.Client(timeout=30) as client:
            response = client.get(
                f"{SEMANTIC_SCHOLAR_API}/paper/search",
                headers=HEADERS,
                params=params,
            )
            response.raise_for_status()
            data = response.json()

        for item in data.get("data", []):
            # Get PDF URL from open access or paper
            pdf_url = None
            if item.get("openAccessPdf"):
                pdf_url = item["openAccessPdf"].get("url")
            elif item.get("url"):
                # Semantic Scholar URL can be used to get PDF
                pdf_url = f"{item['url']}/pdf"

            authors = []
            for author in item.get("authors", []):
                author_name = author.get("name", "")
                if author_name:
                    authors.append(author_name)

            papers.append(
                SemanticScholarPaper(
                    paper_id=item.get("paperId", ""),
                    title=item.get("title", ""),
                    abstract=item.get("abstract", ""),
                    authors=authors,
                    year=item.get("year"),
                    venue=item.get("venue", ""),
                    doi=item.get("doi"),
                    citation_count=item.get("citationCount", 0),
                    url=item.get("url"),
                    pdf_url=pdf_url,
                    fields_of_study=item.get("fieldsOfStudy", []),
                    source="semantic_scholar",
                )
            )

        logger.info("Semantic Scholar search '%s' → %d results", query, len(papers))

    except Exception as e:
        logger.error("Semantic Scholar search failed: %s", e, exc_info=True)

    return papers


def fetch_paper_details(paper_ids: list[str]) -> list[SemanticScholarPaper]:
    """Fetch detailed information for specific papers by ID."""
    papers: list[SemanticScholarPaper] = []

    if not paper_ids:
        return papers

    try:
        # Fetch in batches of 100 (API limit)
        batch_size = 100
        for i in range(0, len(paper_ids), batch_size):
            batch = paper_ids[i : i + batch_size]
            ids = ",".join(batch)

            params = {
                "fields": "paperId,title,abstract,authors,year,venue,doi,citationCount,url,openAccessPdf,fieldsOfStudy",
            }

            with httpx.Client(timeout=30) as client:
                response = client.get(
                    f"{SEMANTIC_SCHOLAR_API}/paper/batch?ids={ids}",
                    headers=HEADERS,
                    params=params,
                )
                response.raise_for_status()
                data = response.json()

            for item in data:
                if not item:
                    continue

                pdf_url = None
                if item.get("openAccessPdf"):
                    pdf_url = item["openAccessPdf"].get("url")

                authors = []
                for author in item.get("authors", []):
                    author_name = author.get("name", "")
                    if author_name:
                        authors.append(author_name)

                papers.append(
                    SemanticScholarPaper(
                        paper_id=item.get("paperId", ""),
                        title=item.get("title", ""),
                        abstract=item.get("abstract", ""),
                        authors=authors,
                        year=item.get("year"),
                        venue=item.get("venue", ""),
                        doi=item.get("doi"),
                        citation_count=item.get("citationCount", 0),
                        url=item.get("url"),
                        pdf_url=pdf_url,
                        fields_of_study=item.get("fieldsOfStudy", []),
                        source="semantic_scholar",
                    )
                )

        logger.info("Fetched details for %d Semantic Scholar papers", len(papers))

    except Exception as e:
        logger.error("Semantic Scholar batch fetch failed: %s", e, exc_info=True)

    return papers
