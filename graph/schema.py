"""
Graph schema — node labels, relationship types, and constraint/index DDL.

Run ``apply_schema()`` once to create constraints and indexes in Neo4j.
"""

from __future__ import annotations

import logging

from neo4j import GraphDatabase

from config import NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER

logger = logging.getLogger(__name__)

# ── Node Labels ───────────────────────────────────────────────────────────────
NODE_LABELS = [
    "Paper",
    "Gene",
    "Drug",
    "Disease",
    "Protein",
    "Pathway",
    "Author",
    "Conclusion",
]

# ── Relationship Types ────────────────────────────────────────────────────────
RELATIONSHIP_TYPES = [
    "MENTIONS",       # Paper → Gene/Drug
    "STUDIES",        # Paper → Disease
    "TARGETS",        # Drug → Protein
    "INVOLVED_IN",    # Gene → Pathway
    "CONTRADICTS",    # Paper ↔ Paper
    "SUPPORTS",       # Paper ↔ Paper
    "CITES",          # Paper → Paper
    "BASED_ON",       # Conclusion → Paper (provenance)
    "ABOUT",          # Conclusion → Gene/Drug/Disease
    "AUTHORED_BY",    # Paper → Author
]

# ── Schema DDL ────────────────────────────────────────────────────────────────

CONSTRAINTS = [
    "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Paper) REQUIRE p.id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (g:Gene) REQUIRE g.symbol IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (d:Drug) REQUIRE d.name IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (ds:Disease) REQUIRE ds.name IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (pr:Protein) REQUIRE pr.uniprot_id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (pw:Pathway) REQUIRE pw.kegg_id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (a:Author) REQUIRE a.name IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Conclusion) REQUIRE c.id IS UNIQUE",
]

INDEXES = [
    "CREATE INDEX IF NOT EXISTS FOR (p:Paper) ON (p.title)",
    "CREATE INDEX IF NOT EXISTS FOR (p:Paper) ON (p.year)",
    "CREATE INDEX IF NOT EXISTS FOR (p:Paper) ON (p.doi)",
]


def get_driver():
    """Return a Neo4j driver instance."""
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


def apply_schema() -> None:
    """Apply all constraints and indexes to the Neo4j database."""
    driver = get_driver()
    with driver.session() as session:
        for stmt in CONSTRAINTS + INDEXES:
            session.run(stmt)
            logger.info("Applied: %s", stmt[:80])
    driver.close()
    logger.info("Schema applied — %d constraints, %d indexes", len(CONSTRAINTS), len(INDEXES))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    apply_schema()
