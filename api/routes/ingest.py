"""
POST /ingest — add papers to the knowledge base.

Fetches from PubMed/arXiv, parses, chunks, embeds into ChromaDB,
and extracts entities into Neo4j.
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException

from api.models import IngestRequest, IngestResponse
from graph.kg_builder import ingest_paper_to_graph
from ingestion.arxiv_fetcher import search_arxiv
from ingestion.chunker import chunk_text
from ingestion.embedding_pipeline import store_chunks
from ingestion.pubmed_fetcher import search_and_fetch

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
async def ingest_papers(req: IngestRequest) -> IngestResponse:
    """
    Fetch papers from PubMed and/or arXiv, then ingest into the knowledge base.

    Pipeline: fetch → chunk → embed (ChromaDB) → extract entities (Neo4j).
    """
    papers_fetched = 0
    papers_ingested = 0
    total_chunks = 0
    total_entities = 0

    try:
        # ── PubMed ────────────────────────────────────────
        if req.pubmed_query:
            pm_papers = search_and_fetch(req.pubmed_query, max_results=req.max_results)
            papers_fetched += len(pm_papers)

            for p in pm_papers:
                # Chunk the abstract
                chunks = chunk_text(p.abstract, source_id=p.pmid)
                n_stored = store_chunks(chunks)
                total_chunks += n_stored

                # Extract entities & build graph
                entities = await ingest_paper_to_graph(
                    paper_id=p.pmid,
                    title=p.title,
                    abstract=p.abstract,
                    year=p.year,
                    doi=p.doi,
                    journal=p.journal,
                    authors=p.authors,
                    graph_storage=req.graph_storage,
                )
                total_entities += sum(
                    len(entities.get(k, []))
                    for k in ("genes", "drugs", "diseases", "proteins", "pathways")
                )
                papers_ingested += 1

        # ── arXiv ─────────────────────────────────────────
        if req.arxiv_query:
            arxiv_papers = search_arxiv(req.arxiv_query, max_results=req.max_results)
            papers_fetched += len(arxiv_papers)

            for p in arxiv_papers:
                chunks = chunk_text(p.abstract, source_id=p.arxiv_id)
                n_stored = store_chunks(chunks)
                total_chunks += n_stored

                entities = await ingest_paper_to_graph(
                    paper_id=p.arxiv_id,
                    title=p.title,
                    abstract=p.abstract,
                    year=None,
                    doi=p.doi,
                    authors=p.authors,
                    graph_storage=req.graph_storage,
                )
                total_entities += sum(
                    len(entities.get(k, []))
                    for k in ("genes", "drugs", "diseases", "proteins", "pathways")
                )
                papers_ingested += 1

        # ── Semantic Scholar ───────────────────────────────
        if req.semantic_scholar_query:
            # For Semantic Scholar, we search and fetch papers
            from ingestion.semantic_scholar import search_semantic_scholar
            ss_papers = search_semantic_scholar(req.semantic_scholar_query, max_results=req.max_results)
            papers_fetched += len(ss_papers)

            for p in ss_papers:
                chunks = chunk_text(p.abstract, source_id=p.paper_id)
                n_stored = store_chunks(chunks)
                total_chunks += n_stored

                entities = await ingest_paper_to_graph(
                    paper_id=p.paper_id,
                    title=p.title,
                    abstract=p.abstract,
                    year=p.year,
                    doi=p.doi,
                    journal=p.venue,
                    authors=p.authors,
                    graph_storage=req.graph_storage,
                )
                total_entities += sum(
                    len(entities.get(k, []))
                    for k in ("genes", "drugs", "diseases", "proteins", "pathways")
                )
                papers_ingested += 1

    except Exception as e:
        logger.error("Ingestion failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    return IngestResponse(
        papers_fetched=papers_fetched,
        papers_ingested=papers_ingested,
        chunks_stored=total_chunks,
        entities_extracted=total_entities,
    )
