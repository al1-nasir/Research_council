"""
ResearchState — the TypedDict that flows through the LangGraph state machine.

Every node reads/writes fields on this state object.
"""

from __future__ import annotations

from typing import Any, TypedDict

from council.models import AgentResponse, ChairmanSynthesis, CouncilResult, CrossReview


class ResearchState(TypedDict, total=False):
    """State object for the LangGraph research orchestrator."""

    # ── Input ──────────────────────────────────────────────
    query: str                          # user's research question

    # ── Tool selection ─────────────────────────────────────
    selected_tools: list[dict[str, Any]]  # tools chosen by bigtool agent

    # ── Retrieval ──────────────────────────────────────────
    chunks: list[dict[str, Any]]        # vector search results
    graph_context: list[dict[str, Any]]  # graph neighborhood expansion
    paper_ids: list[str]                # unique paper IDs found

    # ── Assembled context ──────────────────────────────────
    context: str                        # compact text sent to council (~2k tokens)

    # ── Council ────────────────────────────────────────────
    stage1_responses: list[AgentResponse]
    stage2_reviews: list[CrossReview]
    synthesis: ChairmanSynthesis | None

    # ── Output ─────────────────────────────────────────────
    council_result: CouncilResult | None
    conclusion_id: str                  # Neo4j node ID after writeback

    # ── Metadata ───────────────────────────────────────────
    total_tokens: int
    error: str | None
