"""
POST /pubmed/search — search PubMed without ingesting into knowledge base.

Returns paper metadata (title, abstract, authors, etc.) for the user to browse.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from api.models import PubMedSearchRequest, PubMedSearchResponse, PubMedPaperOut
from ingestion.pubmed_fetcher import search_and_fetch

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/pubmed/search", response_model=PubMedSearchResponse)
async def search_pubmed(req: PubMedSearchRequest) -> PubMedSearchResponse:
    """
    Search PubMed and return paper metadata.
    
    This endpoint searches PubMed and returns paper details without
    ingesting them into the knowledge base. Use this for browsing
    and discovering papers before deciding to ingest them.
    """
    try:
        papers = search_and_fetch(req.query, max_results=req.max_results)
        
        paper_outs = [
            PubMedPaperOut(
                pmid=p.pmid,
                title=p.title,
                abstract=p.abstract,
                authors=p.authors,
                journal=p.journal,
                year=p.year,
                doi=p.doi,
            )
            for p in papers
        ]
        
        logger.info("PubMed search '%s' returned %d results", req.query, len(paper_outs))
        
        return PubMedSearchResponse(
            papers=paper_outs,
            total_results=len(paper_outs),
            query=req.query,
        )
        
    except Exception as e:
        logger.error("PubMed search failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
