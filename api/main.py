"""
FastAPI application entrypoint.

Startup:
    uvicorn api.main:app --reload --port 8000
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import graph, ingest, papers, pubmed, query, search, upload

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(name)-30s │ %(levelname)-7s │ %(message)s",
    datefmt="%H:%M:%S",
)

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Research Council API",
    description=(
        "Agentic AI for scientific research — GraphRAG knowledge graph + "
        "Multi-LLM Council deliberation. Returns confidence-scored, cited answers."
    ),
    version="0.1.0",
)

# ── CORS (allow React frontend on different port) ────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(query.router, tags=["Research"])
app.include_router(pubmed.router, tags=["PubMed"])
app.include_router(ingest.router, tags=["Ingestion"])
app.include_router(papers.router, tags=["Papers"])
app.include_router(search.router, tags=["Search"])
app.include_router(upload.router, tags=["Upload"])
app.include_router(graph.router, tags=["Knowledge Graph"])


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "service": "research-council"}


# ── Startup event ─────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    """Pre-warm: register + index tools so first query isn't slow."""
    from orchestrator.bigtool_agent import ensure_tools_indexed

    try:
        ensure_tools_indexed()
        logging.getLogger(__name__).info("Tools indexed on startup")
    except Exception as e:
        logging.getLogger(__name__).warning("Tool indexing deferred: %s", e)
