"""
Papers with Code fetcher — search papers with implementation links.

API: https://github.com/paperswithcode/api
Free: Yes, no API key required for basic usage
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

PAPERS_WITH_CODE_API = "https://api.paperswithcode.com/v1"


@dataclass
class PaperWithCode:
    """Minimal representation of a paper with code."""

    pwc_id: str
    title: str
    abstract: str = ""
    authors: list[str] = field(default_factory=list)
    year: Optional[int] = None
    venue: str = ""
    doi: Optional[str] = None
    url: str = ""
    pdf_url: Optional[str] = None
    code_url: Optional[str] = None
    dataset_urls: list[str] = field(default_factory=list)
    methods: list[str] = field(default_factory=list)
    tasks: list[str] = field(default_factory=list)
    source: str = "paperswithcode"


def search_papers_with_code(
    query: str,
    max_results: int = 20,
) -> list[PaperWithCode]:
    """Search Papers with Code and return paper metadata."""
    papers: list[PaperWithCode] = []

    try:
        params = {"q": query, "page": 1, "page_size": max_results}

        with httpx.Client(timeout=30) as client:
            response = client.get(
                f"{PAPERS_WITH_CODE_API}/papers",
                params=params,
            )
            response.raise_for_status()
            data = response.json()

        for item in data.get("results", []):
            # Extract authors
            authors = []
            for author in item.get("authors", []):
                if isinstance(author, dict):
                    authors.append(author.get("name", ""))
                elif isinstance(author, str):
                    authors.append(author)

            # Extract methods and tasks
            methods = []
            for method in item.get("methods", []):
                if isinstance(method, dict):
                    methods.append(method.get("name", ""))
                elif isinstance(method, str):
                    methods.append(method)

            tasks = []
            for task in item.get("tasks", []):
                if isinstance(task, dict):
                    tasks.append(task.get("name", ""))
                elif isinstance(task, str):
                    tasks.append(task)

            papers.append(
                PaperWithCode(
                    pwc_id=item.get("id", ""),
                    title=item.get("title", ""),
                    abstract=item.get("abstract", ""),
                    authors=authors,
                    year=item.get("year"),
                    venue=item.get("venue", ""),
                    doi=item.get("doi"),
                    url=item.get("url", ""),
                    pdf_url=item.get("pdf_url"),
                    code_url=item.get("code_url"),
                    dataset_urls=item.get("dataset_urls", []),
                    methods=methods,
                    tasks=tasks,
                    source="paperswithcode",
                )
            )

        logger.info("Papers with Code search '%s' → %d results", query, len(papers))

    except Exception as e:
        logger.error("Papers with Code search failed: %s", e, exc_info=True)

    return papers


def get_paper_by_doi(doi: str) -> Optional[PaperWithCode]:
    """Fetch paper details by DOI from Papers with Code."""
    try:
        # Clean DOI
        doi = doi.replace("https://doi.org/", "").replace("doi:", "")

        with httpx.Client(timeout=30) as client:
            response = client.get(f"{PAPERS_WITH_CODE_API}/papers/{doi}")
            if response.status_code == 404:
                return None
            response.raise_for_status()
            item = response.json()

        authors = []
        for author in item.get("authors", []):
            if isinstance(author, dict):
                authors.append(author.get("name", ""))
            elif isinstance(author, str):
                authors.append(author)

        methods = []
        for method in item.get("methods", []):
            if isinstance(method, dict):
                methods.append(method.get("name", ""))
            elif isinstance(method, str):
                methods.append(method)

        tasks = []
        for task in item.get("tasks", []):
            if isinstance(task, dict):
                tasks.append(task.get("name", ""))
            elif isinstance(task, str):
                tasks.append(task)

        return PaperWithCode(
            pwc_id=item.get("id", ""),
            title=item.get("title", ""),
            abstract=item.get("abstract", ""),
            authors=authors,
            year=item.get("year"),
            venue=item.get("venue", ""),
            doi=item.get("doi"),
            url=item.get("url", ""),
            pdf_url=item.get("pdf_url"),
            code_url=item.get("code_url"),
            dataset_urls=item.get("dataset_urls", []),
            methods=methods,
            tasks=tasks,
            source="paperswithcode",
        )

    except Exception as e:
        logger.error("Papers with Code fetch by DOI failed: %s", e, exc_info=True)
        return None
