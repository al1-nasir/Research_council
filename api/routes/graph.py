"""
GET /graph — explore the knowledge graph.

Returns nodes and edges for visualization (D3 / Cytoscape.js).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Query, HTTPException

from api.models import GraphEdgeOut, GraphNodeOut, GraphResponse, GraphStorageCreate, GraphStorageResponse, RemovePaperRequest
from graph.schema import get_driver

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/graph", response_model=GraphResponse)
async def explore_graph(
    entity_name: str | None = Query(default=None, description="Filter by entity name"),
    label: str = Query(default="Paper", description="Node label to search"),
    limit: int = Query(default=50, ge=1, le=200),
    graph_storage: str = Query(default="default", description="Graph storage name to query from"),
) -> GraphResponse:
    """
    Explore the knowledge graph. Returns nodes and edges for visualization.

    - No entity_name → returns recent Paper nodes and their connections.
    - With entity_name → returns that entity's neighborhood.
    """
    driver = get_driver()
    nodes: list[GraphNodeOut] = []
    edges: list[GraphEdgeOut] = []

    with driver.session() as session:
        if entity_name:
            result = session.run(
                """
                MATCH (n {name: $name})-[r]-(m)
                RETURN labels(n) AS n_labels, properties(n) AS n_props,
                       type(r) AS rel_type,
                       labels(m) AS m_labels, properties(m) AS m_props
                LIMIT $limit
                """,
                name=entity_name,
                limit=limit,
            )
        else:
            result = session.run(
                """
                MATCH (p:Paper)-[r]-(m)
                WHERE p.graph_storage = $graph_storage
                RETURN labels(p) AS n_labels, properties(p) AS n_props,
                       type(r) AS rel_type,
                       labels(m) AS m_labels, properties(m) AS m_props
                ORDER BY p.year DESC
                LIMIT $limit
                """,
                graph_storage=graph_storage,
                limit=limit,
            )

        seen_nodes: set[str] = set()
        for rec in result:
            # Source node
            n_id = _node_id(rec["n_props"])
            if n_id not in seen_nodes:
                nodes.append(GraphNodeOut(labels=rec["n_labels"], properties=rec["n_props"]))
                seen_nodes.add(n_id)

            # Target node
            m_id = _node_id(rec["m_props"])
            if m_id not in seen_nodes:
                nodes.append(GraphNodeOut(labels=rec["m_labels"], properties=rec["m_props"]))
                seen_nodes.add(m_id)

            # Edge
            edges.append(GraphEdgeOut(source=n_id, target=m_id, rel_type=rec["rel_type"]))

    driver.close()

    return GraphResponse(
        nodes=nodes,
        edges=edges,
        total_nodes=len(nodes),
        total_edges=len(edges),
        graph_storage=graph_storage,
    )


# ── Graph Storage Management ───────────────────────────────────────────────────


@router.get("/graph/storages", response_model=list[str])
async def list_graph_storages() -> list[str]:
    """
    List all available graph storage names.
    """
    driver = get_driver()
    storages = set()
    
    with driver.session() as session:
        # Get storages from Paper nodes
        result = session.run(
            """
            MATCH (p:Paper)
            RETURN DISTINCT COALESCE(p.graph_storage, 'default') AS storage
            """
        )
        for rec in result:
            storage = rec["storage"]
            if storage:
                storages.add(storage)
        
        # Also get explicit GraphStorage nodes
        result2 = session.run(
            """
            MATCH (s:GraphStorage)
            RETURN s.name AS name
            """
        )
        for rec in result2:
            name = rec["name"]
            if name:
                storages.add(name)
    
    driver.close()
    
    # Always include default
    storages.add("default")
    return sorted(list(storages))


@router.post("/graph/storages", response_model=GraphStorageResponse)
async def create_graph_storage(req: GraphStorageCreate) -> GraphStorageResponse:
    """
    Create a new graph storage.
    """
    import datetime
    
    driver = get_driver()
    created_at = datetime.datetime.utcnow().isoformat()
    
    with driver.session() as session:
        # Create a placeholder node to represent the storage
        session.run(
            """
            MERGE (s:GraphStorage {name: $name})
            SET s.created_at = $created_at
            """,
            name=req.name,
            created_at=created_at
        )
    
    driver.close()
    
    return GraphStorageResponse(
        name=req.name,
        paper_count=0,
        created_at=created_at
    )


@router.delete("/graph/storages/{storage_name}")
async def delete_graph_storage(storage_name: str) -> dict:
    """
    Delete a graph storage and all its papers.
    """
    driver = get_driver()
    
    with driver.session() as session:
        # Delete all papers in this storage (only exact match)
        result = session.run(
            """
            MATCH (p:Paper)
            WHERE p.graph_storage = $storage
            DETACH DELETE p
            RETURN count(p) AS deleted_count
            """,
            storage=storage_name
        )
        deleted_count = result.single()["deleted_count"]
        
        # Also delete the GraphStorage node
        session.run(
            """
            MATCH (s:GraphStorage {name: $storage})
            DELETE s
            """,
            storage=storage_name
        )
    
    driver.close()
    
    return {"message": f"Deleted {deleted_count} papers from storage '{storage_name}'"}


@router.delete("/graph/papers/{paper_id}")
async def remove_paper_from_graph(paper_id: str, req: RemovePaperRequest) -> dict:
    """
    Remove a paper and its associated entities from the graph.
    """
    driver = get_driver()
    
    with driver.session() as session:
        # First get all entities connected to this paper (only match exact storage)
        result = session.run(
            """
            MATCH (p:Paper)
            WHERE p.id = $paper_id AND p.graph_storage = $graph_storage
            OPTIONAL MATCH (p)-[r]-(entity)
            RETURN id(p) AS paper_node_id, id(entity) AS entity_id, labels(entity) AS entity_labels
            """,
            paper_id=paper_id,
            graph_storage=req.graph_storage
        )
        
        records = list(result)
        
        if not records:
            driver.close()
            raise HTTPException(status_code=404, detail=f"Paper '{paper_id}' not found in storage '{req.graph_storage}'")
        
        # Delete the paper and its connections
        session.run(
            """
            MATCH (p:Paper)
            WHERE p.id = $paper_id AND p.graph_storage = $graph_storage
            DETACH DELETE p
            """,
            paper_id=paper_id,
            graph_storage=req.graph_storage
        )
        
        # Clean up orphaned entities (entities that have no more connections)
        session.run(
            """
            MATCH (entity)
            WHERE NOT (entity)--()
            DELETE entity
            """
        )
    
    driver.close()
    
    return {"message": f"Removed paper '{paper_id}' from storage '{req.graph_storage}'"}


def _node_id(props: dict) -> str:
    """Extract a stable ID from node properties."""
    return props.get("id") or props.get("name") or props.get("symbol") or str(hash(str(props)))
