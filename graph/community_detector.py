"""
Community detector — cluster related concepts in the knowledge graph.

Uses Neo4j's built-in GDS-free approach: connected component detection
via Cypher. For larger graphs, install Neo4j GDS plugin and use Louvain.
"""

from __future__ import annotations

import logging
from typing import Any

from graph.schema import get_driver

logger = logging.getLogger(__name__)


def detect_communities_by_disease() -> list[dict[str, Any]]:
    """
    Group papers + entities by disease — a simple community proxy.

    Returns list of communities, each with a disease name and connected entities.
    """
    driver = get_driver()
    with driver.session() as session:
        result = session.run(
            """
            MATCH (d:Disease)<-[:STUDIES]-(p:Paper)-[:MENTIONS]->(entity)
            WITH d.name AS community, collect(DISTINCT p.title) AS papers,
                 collect(DISTINCT entity.name) AS entities,
                 count(DISTINCT p) AS paper_count
            WHERE paper_count > 1
            RETURN community, papers, entities, paper_count
            ORDER BY paper_count DESC
            LIMIT 20
            """
        )
        communities = [
            {
                "community": rec["community"],
                "papers": rec["papers"],
                "entities": rec["entities"],
                "paper_count": rec["paper_count"],
            }
            for rec in result
        ]
    driver.close()
    logger.info("Detected %d disease-based communities", len(communities))
    return communities


def detect_entity_clusters(label: str = "Gene", min_connections: int = 2) -> list[dict[str, Any]]:
    """
    Find clusters of entities that co-occur in the same papers.

    Returns groups of entities connected through shared papers.
    """
    driver = get_driver()
    with driver.session() as session:
        result = session.run(
            """
            MATCH (e1)-[:MENTIONS|STUDIES]-(p:Paper)-[:MENTIONS|STUDIES]-(e2)
            WHERE $label IN labels(e1) AND id(e1) < id(e2)
            WITH e1.name AS entity1, e2.name AS entity2,
                 count(p) AS shared_papers
            WHERE shared_papers >= $min_conn
            RETURN entity1, entity2, shared_papers
            ORDER BY shared_papers DESC
            LIMIT 50
            """,
            label=label,
            min_conn=min_connections,
        )
        clusters = [
            {
                "entity1": rec["entity1"],
                "entity2": rec["entity2"],
                "shared_papers": rec["shared_papers"],
            }
            for rec in result
        ]
    driver.close()
    logger.info("Found %d co-occurrence pairs for %s", len(clusters), label)
    return clusters
