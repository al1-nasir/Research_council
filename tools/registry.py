"""
Tool registry — register all tools for langgraph-bigtool dynamic loading.

Instead of passing 50+ tool schemas to the agent (wasting tokens),
we embed tool descriptions and let the agent search for relevant tools
at query time. Only 2-4 tools get loaded per query.

Tool calls are traced with Langfuse for observability.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from api.langfuse_client import trace_tool
from ingestion.embedding_pipeline import embed_texts, get_or_create_collection

logger = logging.getLogger(__name__)

# ── In-memory tool catalog ───────────────────────────────────────────────────

_TOOL_CATALOG: dict[str, dict] = {}


def register_tool(
    name: str,
    description: str,
    func: Callable,
    category: str = "general",
) -> None:
    """Register a tool in the catalog with its description for semantic search."""
    _TOOL_CATALOG[name] = {
        "name": name,
        "description": description,
        "func": func,
        "category": category,
    }
    logger.debug("Registered tool: %s (%s)", name, category)


def get_tool(name: str) -> Callable | None:
    """Get a tool function by name."""
    entry = _TOOL_CATALOG.get(name)
    return entry["func"] if entry else None


def get_all_tools() -> dict[str, dict]:
    """Return the full tool catalog (for indexing, not for passing to agents)."""
    return _TOOL_CATALOG


# ── Tool execution with tracing ────────────────────────────────────────────────


def execute_tool(name: str, **kwargs: Any) -> Any:
    """
    Execute a tool by name with Langfuse tracing.
    
    Args:
        name: Tool name
        **kwargs: Arguments to pass to the tool function
        
    Returns:
        The tool's return value
    """
    func = get_tool(name)
    if not func:
        raise ValueError(f"Tool not found: {name}")
    
    # Trace the tool call with Langfuse
    trace_tool(
        name=name,
        input_data=kwargs,
    )
    
    try:
        result = func(**kwargs)
        
        # Trace successful result (truncated)
        trace_tool(
            name=name,
            input_data=kwargs,
            output=result,
        )
        
        return result
    except Exception as e:
        # Trace failed execution
        trace_tool(
            name=name,
            input_data=kwargs,
            error=e,
        )
        raise


# ── Tool search (embed + retrieve) ─────────────────────────────────────────--

_TOOL_COLLECTION = "tool_embeddings"


def index_tools() -> int:
    """
    Embed all registered tool descriptions and store in ChromaDB.

    Call this once after all tools are registered (e.g., at startup).
    Returns number of tools indexed.
    """
    if not _TOOL_CATALOG:
        logger.warning("No tools registered — nothing to index")
        return 0

    collection = get_or_create_collection(_TOOL_COLLECTION)

    names = list(_TOOL_CATALOG.keys())
    descriptions = [_TOOL_CATALOG[n]["description"] for n in names]
    categories = [_TOOL_CATALOG[n]["category"] for n in names]

    embeddings = embed_texts(descriptions)

    collection.upsert(
        ids=names,
        documents=descriptions,
        embeddings=embeddings,
        metadatas=[{"category": c} for c in categories],
    )

    logger.info("Indexed %d tools in collection '%s'", len(names), _TOOL_COLLECTION)
    return len(names)


def search_tools(query: str, n_results: int = 4) -> list[dict]:
    """
    Semantically search the tool registry for tools relevant to *query*.

    Returns up to *n_results* tool entries (name, description, category, score).
    """
    collection = get_or_create_collection(_TOOL_COLLECTION)
    query_embedding = embed_texts([query])[0]

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(n_results, 4),  # never load more than 4 tools
    )

    tools = []
    for name, desc, dist in zip(
        results.get("ids", [[]])[0],
        results.get("documents", [[]])[0],
        results.get("distances", [[]])[0],
    ):
        tools.append(
            {
                "name": name,
                "description": desc,
                "score": 1 - dist,
                "func": _TOOL_CATALOG[name]["func"] if name in _TOOL_CATALOG else None,
            }
        )

    logger.info("Tool search '%s' → %d tools selected", query[:50], len(tools))
    return tools
