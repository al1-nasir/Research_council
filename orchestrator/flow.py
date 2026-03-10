"""
LangGraph flow — the main StateGraph that wires:

    query → tool selection → retrieval → context assembly → council → writeback

Each node is a pure function that takes ResearchState and returns a partial update.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from langgraph.graph import END, StateGraph

from council.chairman import run_full_council
from graph.retriever import hybrid_retrieve
from graph.writeback import write_conclusion
from orchestrator.bigtool_agent import ensure_tools_indexed, select_tools
from orchestrator.state import ResearchState

logger = logging.getLogger(__name__)


# ── Node functions ────────────────────────────────────────────────────────────


def node_select_tools(state: ResearchState) -> dict[str, Any]:
    """Select 2-4 relevant tools based on the query."""
    query = state["query"]
    tools = select_tools(query, n=4)
    logger.info("Selected tools: %s", [t["name"] for t in tools])
    return {"selected_tools": tools}


def node_retrieve(state: ResearchState) -> dict[str, Any]:
    """Run hybrid retrieval (vector + graph) to gather evidence."""
    query = state["query"]
    graph_storage = state.get("graph_storage", "default")
    result = hybrid_retrieve(query, n_vector=5, n_graph=5, graph_storage=graph_storage)
    return {
        "chunks": result["chunks"],
        "graph_context": result["graph_context"],
        "paper_ids": result["paper_ids"],
    }


def node_assemble_context(state: ResearchState) -> dict[str, Any]:
    """
    Assemble a compact context string (~2,000 tokens) for the council.

    Combines top chunks + graph facts into a single text block.
    Never dumps 20k tokens — always stays lean.
    """
    parts: list[str] = []

    # Top chunks (capped at 5)
    chunks = state.get("chunks", [])[:5]
    if chunks:
        parts.append("## Relevant Paper Excerpts")
        for i, c in enumerate(chunks):
            parts.append(f"[{c.get('source_id', 'unknown')}] {c['text'][:400]}")

    # Graph context (capped at 15 facts)
    graph_ctx = state.get("graph_context", [])[:15]
    if graph_ctx:
        parts.append("\n## Knowledge Graph Facts")
        for g in graph_ctx:
            parts.append(
                f"- {g.get('paper_title', '?')} → {g.get('relationship', '?')} → "
                f"{g.get('entity_type', '?')}: {g.get('entity_name', '?')}"
            )

    context = "\n".join(parts)
    # Hard cap at ~2500 words ≈ ~2000 tokens
    words = context.split()
    if len(words) > 2500:
        context = " ".join(words[:2500]) + "\n[...truncated for token budget]"

    return {"context": context}


async def node_council(state: ResearchState) -> dict[str, Any]:
    """Run the full 3-stage council deliberation."""
    query = state["query"]
    context = state.get("context", "")
    paper_ids = state.get("paper_ids", [])

    result = await run_full_council(query, context, paper_ids)
    return {
        "stage1_responses": result.stage1_responses,
        "stage2_reviews": result.stage2_reviews,
        "synthesis": result.synthesis,
        "council_result": result,
        "total_tokens": result.total_tokens,
    }


def node_writeback(state: ResearchState) -> dict[str, Any]:
    """Write the conclusion back to Neo4j."""
    synthesis = state.get("synthesis")
    if not synthesis:
        return {"conclusion_id": "", "error": "No synthesis to write back"}

    try:
        conclusion_id = write_conclusion(
            text=synthesis.summary,
            confidence=synthesis.confidence,
            query=state["query"],
            source_paper_ids=state.get("paper_ids", []),
        )
        return {"conclusion_id": conclusion_id}
    except Exception as e:
        logger.error("Writeback failed: %s", e)
        return {"conclusion_id": "", "error": str(e)}


# ── Build the graph ───────────────────────────────────────────────────────────


def build_research_graph() -> StateGraph:
    """
    Build and compile the LangGraph research flow.

    Flow: select_tools → retrieve → assemble_context → council → writeback
    """
    graph = StateGraph(ResearchState)

    # Add nodes
    graph.add_node("select_tools", node_select_tools)
    graph.add_node("retrieve", node_retrieve)
    graph.add_node("assemble_context", node_assemble_context)
    graph.add_node("council", node_council)
    graph.add_node("writeback", node_writeback)

    # Wire edges (linear for now; can add branching later)
    graph.set_entry_point("select_tools")
    graph.add_edge("select_tools", "retrieve")
    graph.add_edge("retrieve", "assemble_context")
    graph.add_edge("assemble_context", "council")
    graph.add_edge("council", "writeback")
    graph.add_edge("writeback", END)

    return graph


def get_compiled_graph():
    """Return the compiled LangGraph app, ready to invoke."""
    graph = build_research_graph()
    return graph.compile()


# ── Convenience runner ────────────────────────────────────────────────────────


async def run_research_query(query: str, graph_storage: str = "default") -> ResearchState:
    """
    Execute a full research query through the pipeline.

    Returns the final ResearchState with all results.
    """
    ensure_tools_indexed()
    app = get_compiled_graph()
    initial_state: ResearchState = {
        "query": query,
        "graph_storage": graph_storage,
    }  # type: ignore[typeddict-item]

    # LangGraph invoke — handles async nodes
    result = await app.ainvoke(initial_state)
    return result
