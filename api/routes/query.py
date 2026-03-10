"""
POST /query — main research endpoint.

Runs the full LangGraph pipeline: tool selection → retrieval → council → writeback.

All LLM calls and tool usage are traced with Langfuse for observability.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, HTTPException

from api.langfuse_client import flush, get_langfuse, is_enabled
from api.models import AgentResponseOut, CitationOut, QueryRequest, QueryResponse
from orchestrator.flow import run_research_query

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/query", response_model=QueryResponse)
async def research_query(req: QueryRequest) -> QueryResponse:
    """
    Submit a research question to the Research Council.

    The system will:
    1. Select relevant tools dynamically
    2. Retrieve evidence from the knowledge graph + vector store
    3. Run a 4-agent council deliberation (Groq, parallel)
    4. Synthesize via Chairman (OpenRouter)
    5. Write conclusion back to Neo4j

    Returns a confidence-scored, cited answer with full agent reasoning.
    """
    # Generate a trace ID for this query
    trace_id = str(uuid.uuid4())
    
    # Create top-level Langfuse trace if enabled
    langfuse = get_langfuse()
    span = None
    if langfuse and is_enabled():
        try:
            span = langfuse.start_as_current_span(
                name="research_query",
                metadata={
                    "query": req.query,
                    "graph_storage": req.graph_storage,
                    "trace_id": trace_id,
                },
            )
            logger.info("Created Langfuse trace: %s", trace_id)
        except Exception as e:
            logger.warning("Failed to create Langfuse trace: %s", e)
    
    try:
        state = await run_research_query(req.query, graph_storage=req.graph_storage)
    except Exception as e:
        logger.error("Query failed: %s", e, exc_info=True)
        # Log error to Langfuse if available
        if span:
            try:
                span.end(error={"message": str(e)})
            except Exception:
                pass
        raise HTTPException(status_code=500, detail=str(e))

    # Build response
    synthesis = state.get("synthesis")
    if not synthesis:
        raise HTTPException(status_code=500, detail="Council produced no synthesis")

    agent_responses = [
        AgentResponseOut(
            agent_name=r.agent_name,
            role=r.role,
            model=r.model,
            response=r.response,
        )
        for r in state.get("stage1_responses", [])
    ]

    citations = [
        CitationOut(
            claim=c.claim,
            paper_id=c.paper_id,
            paper_title=c.paper_title,
            confidence=c.confidence,
        )
        for c in synthesis.citations
    ]

    response = QueryResponse(
        query=req.query,
        summary=synthesis.summary,
        confidence=synthesis.confidence,
        key_findings=synthesis.key_findings,
        contradictions=synthesis.contradictions,
        citations=citations,
        methodology_notes=synthesis.methodology_notes,
        agent_agreement=synthesis.agent_agreement,
        agent_responses=agent_responses,
        conclusion_id=state.get("conclusion_id", ""),
        total_tokens=state.get("total_tokens", 0),
    )

    # End the span with final metadata
    if span:
        try:
            span.end(
                metadata={
                    "confidence": synthesis.confidence,
                    "agent_agreement": synthesis.agent_agreement,
                    "num_citations": len(citations),
                    "total_tokens": state.get("total_tokens", 0),
                },
                output=synthesis.summary[:500],  # First 500 chars
            )
        except Exception as e:
            logger.warning("Failed to end Langfuse span: %s", e)

    # Flush Langfuse data
    flush()
    
    return response
