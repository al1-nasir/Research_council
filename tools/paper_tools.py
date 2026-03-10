"""
Paper tools — agent-callable functions for searching and fetching scientific papers.

Uses ChromaDB vector search + PubMed/arXiv APIs.
"""

from __future__ import annotations

import logging
from typing import Any

from graph.retriever import vector_search
from ingestion.pubmed_fetcher import fetch_details, search_pubmed
from tools.registry import register_tool

logger = logging.getLogger(__name__)


# ── Tool implementations ─────────────────────────────────────────────────────


def tool_search_papers(query: str, n_results: int = 10) -> list[dict[str, Any]]:
    """
    Semantic search over ingested paper chunks using vector similarity.

    Args:
        query: Natural language research question.
        n_results: Number of results (max 10).

    Returns:
        List of relevant text chunks with source paper IDs and similarity scores.
    """
    return vector_search(query, n_results=min(n_results, 10))


def tool_fetch_abstract(pmid: str) -> dict[str, Any]:
    """
    Fetch the abstract and metadata of a specific PubMed paper by PMID.

    Args:
        pmid: PubMed ID (e.g., "12345678").

    Returns:
        Dict with title, abstract, authors, journal, year, doi.
    """
    papers = fetch_details([pmid])
    if not papers:
        return {"error": f"Paper {pmid} not found"}

    p = papers[0]
    return {
        "pmid": p.pmid,
        "title": p.title,
        "abstract": p.abstract,
        "authors": p.authors[:5],  # cap for token efficiency
        "journal": p.journal,
        "year": p.year,
        "doi": p.doi,
    }


def tool_search_pubmed_live(query: str, max_results: int = 10) -> list[dict[str, Any]]:
    """
    Search PubMed live for papers matching a query (uses Entrez API).

    Args:
        query: PubMed search query (supports MeSH terms).
        max_results: Maximum papers to return (max 10).

    Returns:
        List of paper metadata dicts.
    """
    pmids = search_pubmed(query, max_results=min(max_results, 10))
    papers = fetch_details(pmids)
    return [
        {
            "pmid": p.pmid,
            "title": p.title,
            "abstract": p.abstract[:300],  # truncate for token budget
            "year": p.year,
            "journal": p.journal,
        }
        for p in papers
    ]


# ── Register all paper tools ─────────────────────────────────────────────────


def register_paper_tools() -> None:
    """Register all paper tools in the tool registry."""
    register_tool(
        name="search_papers",
        description="Semantic search over all ingested scientific papers using vector similarity. Returns the most relevant text chunks for a research question.",
        func=tool_search_papers,
        category="papers",
    )
    register_tool(
        name="fetch_abstract",
        description="Fetch the full abstract and metadata of a specific PubMed paper by its PMID. Use when you need details about a specific paper.",
        func=tool_fetch_abstract,
        category="papers",
    )
    register_tool(
        name="search_pubmed_live",
        description="Search PubMed in real-time for papers on a topic. Returns titles, abstracts, and metadata. Use when the knowledge graph may not contain relevant papers yet.",
        func=tool_search_pubmed_live,
        category="papers",
    )
