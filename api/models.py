"""
Request / response Pydantic models for the FastAPI endpoints.
"""

from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


# ── Query endpoint ────────────────────────────────────────────────────────────


class QueryRequest(BaseModel):
    """POST /query request body."""

    query: str = Field(..., description="Research question to investigate")
    max_papers: int = Field(default=10, ge=1, le=50, description="Max papers to retrieve")
    graph_storage: str = Field(default="default", description="Graph storage name to query from")


class CitationOut(BaseModel):
    claim: str
    paper_id: str
    paper_title: str = ""
    confidence: float


class AgentResponseOut(BaseModel):
    agent_name: str
    role: str
    model: str
    response: str


class QueryResponse(BaseModel):
    """POST /query response body."""

    query: str
    summary: str
    confidence: float
    key_findings: list[str] = []
    contradictions: list[str] = []
    citations: list[CitationOut] = []
    methodology_notes: str = ""
    agent_agreement: float = 0.0
    agent_responses: list[AgentResponseOut] = []
    conclusion_id: str = ""
    total_tokens: int = 0


# ── Ingest endpoint ───────────────────────────────────────────────────────────


class IngestRequest(BaseModel):
    """POST /ingest request body."""

    pubmed_query: str | None = Field(default=None, description="PubMed search query")
    arxiv_query: str | None = Field(default=None, description="arXiv search query")
    semantic_scholar_query: str | None = Field(default=None, description="Semantic Scholar search query")
    max_results: int = Field(default=20, ge=1, le=100)
    graph_storage: str = Field(default="default", description="Graph storage name to ingest papers into")


class IngestResponse(BaseModel):
    """POST /ingest response body."""

    papers_fetched: int
    papers_ingested: int
    chunks_stored: int
    entities_extracted: int


# ── Graph endpoint ────────────────────────────────────────────────────────────


class GraphQueryRequest(BaseModel):
    """GET /graph query params."""

    entity_name: str | None = None
    label: str = "Gene"
    limit: int = Field(default=50, ge=1, le=200)
    graph_storage: str = Field(default="default", description="Graph storage name to query from")


class GraphNodeOut(BaseModel):
    labels: list[str]
    properties: dict


class GraphEdgeOut(BaseModel):
    source: str
    target: str
    rel_type: str


class GraphResponse(BaseModel):
    """GET /graph response body."""

    nodes: list[GraphNodeOut] = []
    edges: list[GraphEdgeOut] = []
    total_nodes: int = 0
    total_edges: int = 0
    graph_storage: str = "default"


# ── Graph Storage Management ──────────────────────────────────────────────────


class GraphStorageCreate(BaseModel):
    """POST /graph/storages request body."""
    name: str = Field(..., description="Name of the graph storage")


class GraphStorageResponse(BaseModel):
    """Graph storage response."""
    name: str
    paper_count: int = 0
    created_at: str = ""


class RemovePaperRequest(BaseModel):
    """DELETE /graph/papers/{paper_id} request body."""
    graph_storage: str = Field(default="default", description="Graph storage name")


# ── PubMed search endpoint ────────────────────────────────────────────────────


class PubMedPaperOut(BaseModel):
    """Single PubMed paper in search results."""

    pmid: str
    title: str
    abstract: str
    authors: list[str] = []
    journal: str = ""
    year: int | None = None
    doi: str | None = None


class PubMedSearchRequest(BaseModel):
    """POST /pubmed/search request body."""

    query: str = Field(..., description="Search query for PubMed")
    max_results: int = Field(default=20, ge=1, le=100, description="Maximum number of results")


class PubMedSearchResponse(BaseModel):
    """POST /pubmed/search response body."""

    papers: list[PubMedPaperOut]
    total_results: int
    query: str


# ── Papers endpoint ────────────────────────────────────────────────────────


class PaperInfo(BaseModel):
    """Paper information from the knowledge base."""

    pmid: str
    title: str
    year: int | None = None
    journal: str = ""
    authors: list[str] = []
    doi: str | None = None


# ── Unified Search endpoint ──────────────────────────────────────────────────


class SearchSource(str, Enum):
    ARXIV = "arxiv"
    PUBMED = "pubmed"
    SEMANTIC_SCHOLAR = "semantic_scholar"
    PAPERS_WITH_CODE = "paperswithcode"
    ALL = "all"


class UnifiedSearchRequest(BaseModel):
    """POST /search request body."""

    query: str = Field(..., description="Search query")
    sources: list[SearchSource] = Field(
        default=[SearchSource.ALL],
        description="List of sources to search from"
    )
    max_results: int = Field(default=20, ge=1, le=100)


class UnifiedPaperOut(BaseModel):
    """Unified paper output from any source."""

    id: str
    title: str
    abstract: str
    authors: list[str] = []
    year: int | None = None
    venue: str = ""
    doi: str | None = None
    pdf_url: str | None = None
    source: str
    # Extra fields
    citation_count: int | None = None
    code_url: str | None = None
    dataset_urls: list[str] = []
    methods: list[str] = []
    tasks: list[str] = []


class UnifiedSearchResponse(BaseModel):
    """POST /search response body."""

    papers: list[UnifiedPaperOut]
    total_results: int
    query: str
    sources_searched: list[str]


# ── Upload endpoint ────────────────────────────────────────────────────────


class UploadResponse(BaseModel):
    """POST /upload response body."""

    document_id: str
    filename: str
    file_size: int
    text_length: int
    chunks_created: int
    chunks_stored: int
    status: str
