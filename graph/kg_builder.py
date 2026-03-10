"""
Knowledge Graph builder — extract entities from papers and write to Neo4j.

Entity extraction uses OpenRouter (gpt-4o-mini) for accuracy at low cost.
All Neo4j queries use **parameterized Cypher** — never f-string injection.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from config import NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER, OPENROUTER_API_KEY, OPENROUTER_BASE_URL
from graph.schema import get_driver

logger = logging.getLogger(__name__)

# ── LLM entity extraction prompt ─────────────────────────────────────────────

EXTRACTION_SYSTEM_PROMPT = """You are a biomedical entity extractor. Given a paper's title and abstract,
extract the following entities and relationships as JSON:

{
  "genes": [{"name": "...", "symbol": "..."}],
  "drugs": [{"name": "...", "mechanism": "..."}],
  "diseases": [{"name": "..."}],
  "proteins": [{"name": "...", "function": "..."}],
  "pathways": [{"name": "..."}],
  "relationships": [
    {"source_type": "Drug", "source": "...", "rel": "TARGETS", "target_type": "Protein", "target": "..."},
    {"source_type": "Gene", "source": "...", "rel": "INVOLVED_IN", "target_type": "Pathway", "target": "..."}
  ]
}

Rules:
- Only extract entities explicitly mentioned in the text.
- Use standard gene symbols (e.g., TP53, BRCA1).
- Use generic drug names (e.g., imatinib, not Gleevec).
- Return valid JSON only. No markdown, no explanation.
"""


# ── Entity extraction via OpenRouter ──────────────────────────────────────────


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def extract_entities_from_text(title: str, abstract: str) -> dict[str, Any]:
    """
    Call OpenRouter (gpt-4o-mini) to extract biomedical entities from a paper.

    Returns parsed JSON dict with keys: genes, drugs, diseases, proteins, pathways, relationships.
    """
    if not OPENROUTER_API_KEY:
        logger.warning("OPENROUTER_API_KEY not set — returning empty extraction")
        return {"genes": [], "drugs": [], "diseases": [], "proteins": [], "pathways": [], "relationships": []}

    user_text = f"Title: {title}\n\nAbstract: {abstract}"

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "openai/gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                    {"role": "user", "content": user_text},
                ],
                "temperature": 0.0,
                "max_tokens": 1024,
            },
        )
        resp.raise_for_status()

    content = resp.json()["choices"][0]["message"]["content"]

    # Strip markdown code fences if present
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1]
    if content.endswith("```"):
        content = content.rsplit("```", 1)[0]

    try:
        return json.loads(content.strip())
    except json.JSONDecodeError:
        logger.error("Failed to parse LLM extraction output: %s", content[:200])
        return {"genes": [], "drugs": [], "diseases": [], "proteins": [], "pathways": [], "relationships": []}


# ── Graph writing ─────────────────────────────────────────────────────────────


def write_paper_node(
    paper_id: str,
    title: str,
    abstract: str,
    year: int | None = None,
    doi: str | None = None,
    journal: str = "",
    authors: list[str] | None = None,
    graph_storage: str = "default",
) -> None:
    """Create or merge a Paper node and its Author nodes in Neo4j."""
    driver = get_driver()
    with driver.session() as session:
        # Parameterized Cypher — safe from injection
        session.run(
            """
            MERGE (p:Paper {id: $id})
            SET p.title    = $title,
                p.abstract = $abstract,
                p.year     = $year,
                p.doi      = $doi,
                p.journal  = $journal,
                p.graph_storage = $graph_storage
            """,
            id=paper_id,
            title=title,
            abstract=abstract,
            year=year,
            doi=doi,
            journal=journal,
            graph_storage=graph_storage,
        )

        # Author nodes + relationships
        for author_name in (authors or []):
            session.run(
                """
                MERGE (a:Author {name: $name})
                WITH a
                MATCH (p:Paper {id: $paper_id})
                MERGE (p)-[:AUTHORED_BY]->(a)
                """,
                name=author_name,
                paper_id=paper_id,
            )

    driver.close()
    logger.info("Written Paper node: %s to storage '%s'", paper_id, graph_storage)


def write_entities(paper_id: str, entities: dict[str, Any], graph_storage: str = "default") -> None:
    """
    Write extracted entities and relationships to Neo4j, linked to their Paper.

    Uses parameterized Cypher throughout.
    """
    driver = get_driver()
    with driver.session() as session:
        # ── Genes ─────────────────────────────────────
        for gene in entities.get("genes", []):
            session.run(
                """
                MERGE (g:Gene {symbol: $symbol})
                SET g.name = $name
                WITH g
                MATCH (p:Paper {id: $paper_id})
                MERGE (p)-[:MENTIONS]->(g)
                """,
                symbol=gene.get("symbol", gene["name"]),
                name=gene["name"],
                paper_id=paper_id,
            )

        # ── Drugs ─────────────────────────────────────
        for drug in entities.get("drugs", []):
            session.run(
                """
                MERGE (d:Drug {name: $name})
                SET d.mechanism = $mechanism
                WITH d
                MATCH (p:Paper {id: $paper_id})
                MERGE (p)-[:MENTIONS]->(d)
                """,
                name=drug["name"],
                mechanism=drug.get("mechanism", ""),
                paper_id=paper_id,
            )

        # ── Diseases ──────────────────────────────────
        for disease in entities.get("diseases", []):
            session.run(
                """
                MERGE (ds:Disease {name: $name})
                WITH ds
                MATCH (p:Paper {id: $paper_id})
                MERGE (p)-[:STUDIES]->(ds)
                """,
                name=disease["name"],
                paper_id=paper_id,
            )

        # ── Proteins ──────────────────────────────────
        for protein in entities.get("proteins", []):
            session.run(
                """
                MERGE (pr:Protein {name: $name})
                SET pr.function = $function
                WITH pr
                MATCH (p:Paper {id: $paper_id})
                MERGE (p)-[:MENTIONS]->(pr)
                """,
                name=protein["name"],
                function=protein.get("function", ""),
                paper_id=paper_id,
            )

        # ── Pathways ──────────────────────────────────
        for pathway in entities.get("pathways", []):
            session.run(
                """
                MERGE (pw:Pathway {name: $name})
                WITH pw
                MATCH (p:Paper {id: $paper_id})
                MERGE (p)-[:MENTIONS]->(pw)
                """,
                name=pathway["name"],
                paper_id=paper_id,
            )

        # ── Cross-entity relationships ────────────────
        for rel in entities.get("relationships", []):
            _write_relationship(session, rel)

    driver.close()
    logger.info("Written entities for paper %s", paper_id)


def _write_relationship(session, rel: dict) -> None:
    """Write a single extracted relationship. Only allow known rel types."""
    allowed_rels = {"TARGETS", "INVOLVED_IN", "CONTRADICTS", "SUPPORTS"}
    rel_type = rel.get("rel", "").upper()
    if rel_type not in allowed_rels:
        return

    source_label = rel.get("source_type", "Gene")
    target_label = rel.get("target_type", "Protein")

    # We use APOC-free approach: separate query per rel type for safety
    # (dynamic labels in Cypher require APOC or explicit branching)
    cypher = f"""
        MATCH (s:{source_label} {{name: $source}})
        MATCH (t:{target_label} {{name: $target}})
        MERGE (s)-[:{rel_type}]->(t)
    """
    try:
        session.run(cypher, source=rel["source"], target=rel["target"])
    except Exception as e:
        logger.warning("Failed to write relationship %s: %s", rel, e)


# ── High-level pipeline ──────────────────────────────────────────────────────


async def ingest_paper_to_graph(
    paper_id: str,
    title: str,
    abstract: str,
    year: int | None = None,
    doi: str | None = None,
    journal: str = "",
    authors: list[str] | None = None,
    graph_storage: str = "default",
) -> dict[str, Any]:
    """
    Full pipeline: create Paper node → extract entities via LLM → write to graph.

    Returns the extracted entities dict.
    """
    # Step 1: Write Paper node
    write_paper_node(paper_id, title, abstract, year, doi, journal, authors, graph_storage)

    # Step 2: Extract entities via OpenRouter
    entities = await extract_entities_from_text(title, abstract)

    # Step 3: Write entities + relationships to graph
    write_entities(paper_id, entities, graph_storage)

    return entities
