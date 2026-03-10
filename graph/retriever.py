"""
Hybrid retriever — combines Neo4j Cypher graph queries with ChromaDB vector search.

Returns compact context (~2 000 tokens) for the LLM Council.
"""

from __future__ import annotations

import logging
from typing import Any

from graph.schema import get_driver
from ingestion.embedding_pipeline import query_similar

logger = logging.getLogger(__name__)


# ── Vector search ─────────────────────────────────────────────────────────────


def vector_search(query: str, n_results: int = 10) -> list[dict[str, Any]]:
    """
    Semantic search over paper chunks in ChromaDB.

    Returns list of dicts with keys: text, source_id, score.
    """
    raw = query_similar(query, n_results=n_results)

    results = []
    for doc, meta, dist in zip(
        raw.get("documents", [[]])[0],
        raw.get("metadatas", [[]])[0],
        raw.get("distances", [[]])[0],
    ):
        results.append(
            {
                "text": doc,
                "source_id": meta.get("source_id", ""),
                "chunk_index": meta.get("chunk_index", 0),
                "score": 1 - dist,  # cosine distance → similarity
            }
        )

    logger.info("Vector search → %d results", len(results))
    return results


# ── Graph queries (parameterized Cypher) ──────────────────────────────────────


def query_entity(entity_name: str, label: str = "Gene") -> list[dict[str, Any]]:
    """
    Find a specific entity and its immediate neighborhood in the knowledge graph.

    Returns list of dicts representing connected nodes.
    """
    driver = get_driver()
    with driver.session() as session:
        result = session.run(
            """
            MATCH (n {name: $name})
            WHERE $label IN labels(n)
            OPTIONAL MATCH (n)-[r]-(m)
            RETURN n, type(r) AS rel_type, labels(m) AS m_labels, m
            LIMIT 50
            """,
            name=entity_name,
            label=label,
        )
        records = [
            {
                "entity": dict(record["n"]),
                "rel_type": record["rel_type"],
                "connected_labels": record["m_labels"],
                "connected": dict(record["m"]) if record["m"] else None,
            }
            for record in result
        ]
    driver.close()
    logger.info("Entity query '%s' (%s) → %d connections", entity_name, label, len(records))
    return records


def find_path(source_name: str, target_name: str, max_hops: int = 4) -> list[dict]:
    """Find shortest path between two entities in the graph."""
    driver = get_driver()
    with driver.session() as session:
        result = session.run(
            """
            MATCH (a {name: $source}), (b {name: $target}),
                  path = shortestPath((a)-[*..{max_hops}]-(b))
            RETURN [n IN nodes(path) | {labels: labels(n), props: properties(n)}] AS nodes,
                   [r IN relationships(path) | type(r)] AS rels
            """.replace("{max_hops}", str(int(max_hops))),
            source=source_name,
            target=target_name,
        )
        paths = [{"nodes": r["nodes"], "relationships": r["rels"]} for r in result]
    driver.close()
    return paths


def get_neighbors(entity_name: str, rel_type: str | None = None, limit: int = 20) -> list[dict]:
    """Get neighbors of an entity, optionally filtered by relationship type."""
    driver = get_driver()
    cypher = """
        MATCH (n {name: $name})-[r]-(m)
        WHERE $rel_type IS NULL OR type(r) = $rel_type
        RETURN type(r) AS rel_type, labels(m) AS labels, properties(m) AS props
        LIMIT $limit
    """
    with driver.session() as session:
        result = session.run(cypher, name=entity_name, rel_type=rel_type, limit=limit)
        neighbors = [
            {"rel_type": r["rel_type"], "labels": r["labels"], "props": r["props"]}
            for r in result
        ]
    driver.close()
    return neighbors


def get_contradicting_papers(paper_id: str) -> list[dict]:
    """Find papers that contradict a given paper."""
    driver = get_driver()
    with driver.session() as session:
        result = session.run(
            """
            MATCH (p:Paper {id: $id})-[:CONTRADICTS]-(other:Paper)
            RETURN other.id AS id, other.title AS title, other.year AS year,
                   other.abstract AS abstract
            """,
            id=paper_id,
        )
        papers = [dict(r) for r in result]
    driver.close()
    return papers


def get_supporting_papers(paper_id: str) -> list[dict]:
    """Find papers that support a given paper."""
    driver = get_driver()
    with driver.session() as session:
        result = session.run(
            """
            MATCH (p:Paper {id: $id})-[:SUPPORTS]-(other:Paper)
            RETURN other.id AS id, other.title AS title, other.year AS year,
                   other.abstract AS abstract
            """,
            id=paper_id,
        )
        papers = [dict(r) for r in result]
    driver.close()
    return papers


# ── Hybrid retrieval (vector + graph) ────────────────────────────────────────


def hybrid_retrieve(query: str, n_vector: int = 5, n_graph: int = 5, graph_storage: str = "default") -> dict[str, Any]:
    """
    Combine vector similarity search with graph neighborhood expansion.

    1. Vector search → top chunks
    2. For each unique source paper, fetch graph neighborhood
    3. Merge into compact context dict

    Returns:
        {
            "chunks": [...],          # from vector search
            "graph_context": [...],   # entity neighborhoods
            "paper_ids": [...]        # unique paper IDs involved
        }
    """
    # Step 1: Vector search
    chunks = vector_search(query, n_results=n_vector)

    # Step 2: Expand via graph
    paper_ids = list({c["source_id"] for c in chunks if c["source_id"]})
    graph_context: list[dict] = []

    driver = get_driver()
    with driver.session() as session:
        for pid in paper_ids[:n_graph]:  # cap to avoid explosion
            result = session.run(
                """
                MATCH (p:Paper)-[r]-(entity)
                WHERE p.id = $id AND (p.graph_storage = $graph_storage OR p.graph_storage IS NULL)
                RETURN p.title AS paper_title, type(r) AS rel,
                       labels(entity) AS entity_labels, entity.name AS entity_name
                LIMIT 20
                """,
                id=pid,
                graph_storage=graph_storage,
            )
            for rec in result:
                graph_context.append(
                    {
                        "paper_title": rec["paper_title"],
                        "relationship": rec["rel"],
                        "entity_type": rec["entity_labels"][0] if rec["entity_labels"] else "",
                        "entity_name": rec["entity_name"],
                    }
                )
    driver.close()

    logger.info("Hybrid retrieval → %d chunks, %d graph facts", len(chunks), len(graph_context))
    return {
        "chunks": chunks,
        "graph_context": graph_context,
        "paper_ids": paper_ids,
    }
