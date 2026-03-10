"""
Writeback — persist Council conclusions back to the Neo4j knowledge graph.

Every Chairman conclusion becomes a :Conclusion node linked to its source papers,
making the graph smarter with every query.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from graph.schema import get_driver

logger = logging.getLogger(__name__)


def write_conclusion(
    text: str,
    confidence: float,
    query: str,
    source_paper_ids: list[str],
    about_entities: list[dict[str, str]] | None = None,
) -> str:
    """
    Write a Council conclusion to Neo4j.

    Creates a :Conclusion node and links it to source :Paper nodes via :BASED_ON,
    and optionally to entity nodes via :ABOUT.

    Returns the generated conclusion ID.
    """
    conclusion_id = f"conclusion_{uuid.uuid4().hex[:12]}"
    created_at = datetime.now(timezone.utc).isoformat()

    driver = get_driver()
    with driver.session() as session:
        # Create Conclusion node
        session.run(
            """
            CREATE (c:Conclusion {
                id: $id,
                text: $text,
                confidence: $confidence,
                query: $query,
                created_at: $created_at
            })
            """,
            id=conclusion_id,
            text=text,
            confidence=confidence,
            query=query,
            created_at=created_at,
        )

        # Link to source papers
        for paper_id in source_paper_ids:
            session.run(
                """
                MATCH (c:Conclusion {id: $conclusion_id})
                MATCH (p:Paper {id: $paper_id})
                MERGE (c)-[:BASED_ON]->(p)
                """,
                conclusion_id=conclusion_id,
                paper_id=paper_id,
            )

        # Link to entities the conclusion is about
        for entity in (about_entities or []):
            label = entity.get("label", "Gene")
            name = entity.get("name", "")
            if not name:
                continue
            try:
                session.run(
                    f"""
                    MATCH (c:Conclusion {{id: $conclusion_id}})
                    MATCH (e:{label} {{name: $name}})
                    MERGE (c)-[:ABOUT]->(e)
                    """,
                    conclusion_id=conclusion_id,
                    name=name,
                )
            except Exception as e:
                logger.warning("Failed to link conclusion to %s '%s': %s", label, name, e)

    driver.close()
    logger.info("Written Conclusion %s (confidence=%.2f) linked to %d papers", conclusion_id, confidence, len(source_paper_ids))
    return conclusion_id
