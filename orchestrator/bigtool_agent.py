"""
bigtool agent — dynamic tool loading via semantic search.

Instead of passing all 50+ tools to the agent (wasting context tokens),
we embed tool descriptions and select only the 2–4 most relevant per query.
"""

from __future__ import annotations

import logging
from typing import Any

from tools.evidence_tools import register_evidence_tools
from tools.graph_tools import register_graph_tools
from tools.paper_tools import register_paper_tools
from tools.registry import index_tools, search_tools

logger = logging.getLogger(__name__)

_TOOLS_INDEXED = False


def ensure_tools_indexed() -> None:
    """Register and index all tools (idempotent)."""
    global _TOOLS_INDEXED
    if _TOOLS_INDEXED:
        return

    register_graph_tools()
    register_paper_tools()
    register_evidence_tools()
    index_tools()
    _TOOLS_INDEXED = True
    logger.info("All tools registered and indexed")


def select_tools(query: str, n: int = 4) -> list[dict[str, Any]]:
    """
    Semantically search for the best tools for this query.

    Returns up to *n* tool dicts with name, description, score, func.
    """
    ensure_tools_indexed()
    return search_tools(query, n_results=n)


def execute_tool(tool_name: str, **kwargs) -> Any:
    """Execute a tool by name with given kwargs."""
    ensure_tools_indexed()
    tools = search_tools(tool_name, n_results=1)
    if not tools or tools[0]["func"] is None:
        raise ValueError(f"Tool not found: {tool_name}")
    return tools[0]["func"](**kwargs)
