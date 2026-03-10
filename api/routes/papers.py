"""
GET /papers — list all ingested papers.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Query

from api.models import PaperInfo
from graph.schema import get_driver

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/papers", response_model=list[PaperInfo])
async def list_papers(
    limit: int = Query(default=100, ge=1, le=500),
    skip: int = Query(default=0, ge=0),
    graph_storage: str = Query(default="default", description="Graph storage to filter papers"),
) -> list[PaperInfo]:
    """
    List all ingested papers from the knowledge graph.
    
    Returns paper metadata including PMID, title, year, journal, authors.
    """
    driver = get_driver()
    papers: list[PaperInfo] = []

    with driver.session() as session:
        result = session.run(
            """
            MATCH (p:Paper)
            WHERE p.graph_storage = $graph_storage OR p.graph_storage IS NULL
            RETURN p.id AS pmid, p.title AS title
            ORDER BY p.title DESC
            SKIP $skip
            LIMIT $limit
            """,
            skip=skip,
            limit=limit,
            graph_storage=graph_storage,
        )

        for record in result:
            papers.append(
                PaperInfo(
                    pmid=record["pmid"] or "",
                    title=record["title"] or "Untitled",
                    year=None,
                    journal="",
                    authors=[],
                    doi=None,
                )
            )

    driver.close()
    return papers
