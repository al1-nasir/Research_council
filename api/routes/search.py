"""
POST /search — unified search across multiple sources.

Searches arXiv, PubMed, Semantic Scholar, and Papers with Code.
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException

from api.models import (
    SearchSource,
    UnifiedSearchRequest,
    UnifiedSearchResponse,
    UnifiedPaperOut,
)
from ingestion.arxiv_fetcher import search_arxiv
from ingestion.pubmed_fetcher import search_and_fetch
from ingestion.semantic_scholar import search_semantic_scholar
from ingestion.papers_with_code import search_papers_with_code

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/search", response_model=UnifiedSearchResponse)
async def unified_search(req: UnifiedSearchRequest) -> UnifiedSearchResponse:
    """
    Search across multiple sources.
    
    Sources: arxiv, pubmed, semantic_scholar, paperswithcode
    Use "all" to search all sources at once.
    """
    # Determine sources to search
    if SearchSource.ALL in req.sources or len(req.sources) == 0:
        sources_to_search = [
            SearchSource.ARXIV,
            SearchSource.PUBMED,
            # SearchSource.SEMANTIC_SCHOLAR,  # Add API key to enable
            SearchSource.PAPERS_WITH_CODE,
        ]
    else:
        sources_to_search = req.sources

    papers: list[UnifiedPaperOut] = []
    sources_searched: list[str] = []

    # Run searches concurrently
    tasks = []
    for source in sources_to_search:
        if source == SearchSource.ARXIV:
            tasks.append(_search_arxiv(req.query, req.max_results))
            sources_searched.append("arxiv")
        elif source == SearchSource.PUBMED:
            tasks.append(_search_pubmed(req.query, req.max_results))
            sources_searched.append("pubmed")
        elif source == SearchSource.SEMANTIC_SCHOLAR:
            tasks.append(_search_semantic_scholar(req.query, req.max_results))
            sources_searched.append("semantic_scholar")
        elif source == SearchSource.PAPERS_WITH_CODE:
            tasks.append(_search_papers_with_code(req.query, req.max_results))
            sources_searched.append("paperswithcode")

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Collect results
    for result in results:
        if isinstance(result, Exception):
            logger.warning(f"Search failed: {result}")
            continue
        papers.extend(result)

    # Sort by relevance (year as proxy)
    papers.sort(key=lambda p: (p.year or 0), reverse=True)

    # Limit results
    papers = papers[: req.max_results * len(sources_searched)]

    return UnifiedSearchResponse(
        papers=papers,
        total_results=len(papers),
        query=req.query,
        sources_searched=sources_searched,
    )


async def _search_arxiv(query: str, max_results: int) -> list[UnifiedPaperOut]:
    """Search arXiv and convert to unified format."""
    try:
        # Run in thread pool since arxiv library is synchronous
        loop = asyncio.get_event_loop()
        papers = await loop.run_in_executor(
            None, search_arxiv, query, max_results
        )

        return [
            UnifiedPaperOut(
                id=p.arxiv_id,
                title=p.title,
                abstract=p.abstract,
                authors=p.authors,
                year=int(p.published[:4]) if p.published else None,
                venue="arXiv",
                doi=p.doi,
                pdf_url=p.pdf_url,
                source="arxiv",
            )
            for p in papers
        ]
    except Exception as e:
        logger.error(f"arXiv search failed: {e}")
        return []


async def _search_pubmed(query: str, max_results: int) -> list[UnifiedPaperOut]:
    """Search PubMed and convert to unified format."""
    try:
        loop = asyncio.get_event_loop()
        papers = await loop.run_in_executor(
            None, search_and_fetch, query, max_results
        )

        return [
            UnifiedPaperOut(
                id=p.pmid,
                title=p.title,
                abstract=p.abstract,
                authors=p.authors,
                year=p.year,
                venue=p.journal,
                doi=p.doi,
                source="pubmed",
            )
            for p in papers
        ]
    except Exception as e:
        logger.error(f"PubMed search failed: {e}")
        return []


async def _search_semantic_scholar(
    query: str, max_results: int
) -> list[UnifiedPaperOut]:
    """Search Semantic Scholar and convert to unified format."""
    try:
        loop = asyncio.get_event_loop()
        papers = await loop.run_in_executor(
            None, search_semantic_scholar, query, max_results
        )

        return [
            UnifiedPaperOut(
                id=p.paper_id,
                title=p.title,
                abstract=p.abstract,
                authors=p.authors,
                year=p.year,
                venue=p.venue,
                doi=p.doi,
                pdf_url=p.pdf_url,
                source="semantic_scholar",
                citation_count=p.citation_count,
            )
            for p in papers
        ]
    except Exception as e:
        logger.error(f"Semantic Scholar search failed: {e}")
        return []


async def _search_papers_with_code(
    query: str, max_results: int
) -> list[UnifiedPaperOut]:
    """Search Papers with Code and convert to unified format."""
    try:
        loop = asyncio.get_event_loop()
        papers = await loop.run_in_executor(
            None, search_papers_with_code, query, max_results
        )

        return [
            UnifiedPaperOut(
                id=p.pwc_id,
                title=p.title,
                abstract=p.abstract,
                authors=p.authors,
                year=p.year,
                venue=p.venue,
                doi=p.doi,
                pdf_url=p.pdf_url,
                source="paperswithcode",
                code_url=p.code_url,
                dataset_urls=p.dataset_urls,
                methods=p.methods,
                tasks=p.tasks,
            )
            for p in papers
        ]
    except Exception as e:
        logger.error(f"Papers with Code search failed: {e}")
        return []
