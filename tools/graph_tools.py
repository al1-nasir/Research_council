"""
Graph tools — agent-callable functions for querying the Neo4j knowledge graph.

Each tool is self-contained and returns JSON-serializable output.
"""

from __future__ import annotations

import logging
from typing import Any

from graph.retriever import (
    find_path,
    get_contradicting_papers,
    get_neighbors,
    get_supporting_papers,
    query_entity,
)
from tools.registry import register_tool

logger = logging.getLogger(__name__)


# ── Tool implementations ─────────────────────────────────────────────────────


def tool_query_entity(entity_name: str, label: str = "Gene") -> list[dict[str, Any]]:
    """
    Find an entity in the knowledge graph and return its neighborhood.

    Args:
        entity_name: The name of the entity to search for (e.g., "BRCA1", "imatinib").
        label: Node label — one of Gene, Drug, Disease, Protein, Pathway.

    Returns:
        List of connections: entity details, relationship types, connected nodes.
    """
    return query_entity(entity_name, label)


def tool_find_path(source: str, target: str, max_hops: int = 4) -> list[dict]:
    """
    Find the shortest path between two entities in the knowledge graph.

    Args:
        source: Name of the starting entity.
        target: Name of the ending entity.
        max_hops: Maximum number of hops (default 4).

    Returns:
        List of paths with nodes and relationship types.
    """
    return find_path(source, target, max_hops)


def tool_get_neighbors(entity_name: str, rel_type: str | None = None) -> list[dict]:
    """
    Get all neighbors of an entity, optionally filtered by relationship type.

    Args:
        entity_name: The entity to explore.
        rel_type: Optional filter — e.g., "TARGETS", "MENTIONS", "STUDIES".

    Returns:
        List of neighbor nodes with their relationship and properties.
    """
    return get_neighbors(entity_name, rel_type, limit=20)


def tool_get_contradictions(paper_id: str) -> list[dict]:
    """
    Find papers that contradict a given paper.

    Args:
        paper_id: The PubMed ID or arXiv ID of the paper.

    Returns:
        List of contradicting papers with title, year, abstract.
    """
    return get_contradicting_papers(paper_id)


def tool_get_supporting(paper_id: str) -> list[dict]:
    """
    Find papers that support a given paper's findings.

    Args:
        paper_id: The PubMed ID or arXiv ID of the paper.

    Returns:
        List of supporting papers with title, year, abstract.
    """
    return get_supporting_papers(paper_id)


# ── Register all graph tools ─────────────────────────────────────────────────


def register_graph_tools() -> None:
    """Register all graph tools in the tool registry."""
    register_tool(
        name="query_entity",
        description="Find a specific gene, drug, disease, protein, or pathway in the knowledge graph and return all its connections, including papers that mention it and related entities.",
        func=tool_query_entity,
        category="graph",
    )
    register_tool(
        name="find_path",
        description="Find the shortest path between two biomedical entities in the knowledge graph. Useful for discovering how a drug connects to a disease through proteins and pathways.",
        func=tool_find_path,
        category="graph",
    )
    register_tool(
        name="get_neighbors",
        description="Get all entities connected to a given entity in the graph, optionally filtered by relationship type (TARGETS, MENTIONS, STUDIES, INVOLVED_IN).",
        func=tool_get_neighbors,
        category="graph",
    )
    register_tool(
        name="get_contradictions",
        description="Find papers in the knowledge graph that explicitly contradict a given paper's findings. Critical for identifying scientific disagreements.",
        func=tool_get_contradictions,
        category="graph",
    )
    register_tool(
        name="get_supporting",
        description="Find papers that support or confirm a given paper's findings. Useful for assessing consensus.",
        func=tool_get_supporting,
        category="graph",
    )
