"""
Evidence tools — agent-callable functions for analysing contradictions,
evidence strength, and consensus across papers.
"""

from __future__ import annotations

import logging
from typing import Any

from graph.retriever import hybrid_retrieve, vector_search
from graph.schema import get_driver
from tools.registry import register_tool

logger = logging.getLogger(__name__)


# ── Tool implementations ─────────────────────────────────────────────────────


def tool_find_contradictions(topic: str) -> dict[str, Any]:
    """
    Find contradicting evidence on a topic by combining vector search with
    the CONTRADICTS relationship in the knowledge graph.

    Args:
        topic: Research topic or claim to check for contradictions.

    Returns:
        Dict with vector_matches (semantic) and graph_contradictions (explicit).
    """
    # Semantic search for the topic
    chunks = vector_search(topic, n_results=10)
    paper_ids = list({c["source_id"] for c in chunks if c["source_id"]})

    # Check explicit CONTRADICTS edges
    contradictions: list[dict] = []
    driver = get_driver()
    with driver.session() as session:
        for pid in paper_ids:
            result = session.run(
                """
                MATCH (p:Paper {id: $id})-[:CONTRADICTS]-(other:Paper)
                RETURN p.title AS paper_a, other.title AS paper_b,
                       p.id AS id_a, other.id AS id_b,
                       other.abstract AS abstract_b
                """,
                id=pid,
            )
            for rec in result:
                contradictions.append(dict(rec))
    driver.close()

    return {
        "topic": topic,
        "relevant_chunks": len(chunks),
        "papers_checked": len(paper_ids),
        "explicit_contradictions": contradictions,
        "top_chunks": chunks[:5],  # return top 5 for context
    }


def tool_score_evidence_strength(topic: str) -> dict[str, Any]:
    """
    Score the overall evidence strength for a topic.

    Heuristic scoring based on:
    - Number of papers
    - Presence of contradictions
    - Recency of papers
    - Diversity of sources

    Args:
        topic: Research topic to assess.

    Returns:
        Evidence strength report with score (0.0–1.0) and breakdown.
    """
    context = hybrid_retrieve(topic, n_vector=10, n_graph=5)

    n_papers = len(context["paper_ids"])
    n_chunks = len(context["chunks"])
    n_graph_facts = len(context["graph_context"])

    # Check for contradictions
    driver = get_driver()
    n_contradictions = 0
    n_supports = 0
    with driver.session() as session:
        for pid in context["paper_ids"]:
            result = session.run(
                """
                MATCH (p:Paper {id: $id})
                OPTIONAL MATCH (p)-[:CONTRADICTS]-()
                WITH p, count(*) AS contras
                OPTIONAL MATCH (p)-[:SUPPORTS]-()
                RETURN contras, count(*) AS supports
                """,
                id=pid,
            )
            for rec in result:
                n_contradictions += rec["contras"]
                n_supports += rec["supports"]
    driver.close()

    # Simple heuristic score
    paper_score = min(n_papers / 10, 1.0)  # more papers = higher
    consistency_score = 1.0 - min(n_contradictions / max(n_papers, 1), 1.0)
    coverage_score = min(n_graph_facts / 20, 1.0)

    overall = round((paper_score * 0.4 + consistency_score * 0.4 + coverage_score * 0.2), 2)

    return {
        "topic": topic,
        "overall_score": overall,
        "breakdown": {
            "paper_volume": round(paper_score, 2),
            "consistency": round(consistency_score, 2),
            "knowledge_coverage": round(coverage_score, 2),
        },
        "stats": {
            "papers_found": n_papers,
            "chunks_retrieved": n_chunks,
            "graph_facts": n_graph_facts,
            "contradictions": n_contradictions,
            "supports": n_supports,
        },
    }


def tool_get_evidence_trail(query: str) -> dict[str, Any]:
    """
    Get a full provenance trail for a research query: which papers,
    which entities, and how they connect.

    Args:
        query: Research question to trace evidence for.

    Returns:
        Full hybrid context: chunks + graph connections + paper IDs.
    """
    return hybrid_retrieve(query, n_vector=5, n_graph=5)


# ── Register all evidence tools ──────────────────────────────────────────────


def register_evidence_tools() -> None:
    """Register all evidence tools in the tool registry."""
    register_tool(
        name="find_contradictions",
        description="Find contradicting evidence on a biomedical topic by combining semantic search with explicit CONTRADICTS relationships in the knowledge graph. Surfaces scientific disagreements.",
        func=tool_find_contradictions,
        category="evidence",
    )
    register_tool(
        name="score_evidence_strength",
        description="Score the overall evidence strength for a topic on a 0-1 scale. Considers paper volume, consistency (contradictions vs supports), and knowledge graph coverage.",
        func=tool_score_evidence_strength,
        category="evidence",
    )
    register_tool(
        name="get_evidence_trail",
        description="Get a full provenance trail for a research question: relevant paper chunks, connected entities in the knowledge graph, and how they relate. Use for building cited answers.",
        func=tool_get_evidence_trail,
        category="evidence",
    )
