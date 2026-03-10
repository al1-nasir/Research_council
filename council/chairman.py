"""
Chairman — Stage 3 synthesis via OpenRouter (best available model).

Takes all Stage 1 opinions + Stage 2 cross-reviews and produces a single
authoritative, confidence-scored, fully-cited conclusion.
"""

from __future__ import annotations

import json
import logging

from council.agents import AGENT_CONFIGS, call_agent
from council.models import (
    AgentResponse,
    ChairmanSynthesis,
    CouncilResult,
    CrossReview,
    SourceCitation,
)

logger = logging.getLogger(__name__)


async def stage3_chairman_synthesis(
    query: str,
    stage1_responses: list[AgentResponse],
    stage2_reviews: list[CrossReview],
    paper_ids: list[str],
) -> ChairmanSynthesis:
    """
    Chairman synthesizes all agent responses and cross-reviews into a final answer.

    Uses OpenRouter (Claude Sonnet) for best synthesis quality.
    Returns a structured ChairmanSynthesis.
    """
    # Build the chairman prompt with all context
    opinions_text = "\n\n".join(
        f"### {r.agent_name} ({r.role})\n{r.response}" for r in stage1_responses
    )

    reviews_text = "\n\n".join(
        f"- {rev.reviewer} reviewing {rev.reviewed_agent}: "
        f"agreement={rev.agreement_score:.1f} — {rev.critique[:200]}"
        for rev in stage2_reviews
    )

    papers_text = ", ".join(paper_ids[:20])  # cap for token budget

    prompt = (
        f"Research Query: {query}\n\n"
        f"## Agent Opinions (Stage 1)\n{opinions_text}\n\n"
        f"## Cross-Reviews (Stage 2)\n{reviews_text}\n\n"
        f"## Paper IDs available for citation: {papers_text}\n\n"
        "Synthesize into a JSON response with these exact keys:\n"
        "summary, confidence (0.0-1.0), key_findings (list of strings), "
        "contradictions (list of strings), citations (list of objects with "
        "claim/paper_id/paper_title/confidence), methodology_notes (string), "
        "agent_agreement (float 0.0-1.0).\n\n"
        "Return ONLY valid JSON."
    )

    chairman_config = AGENT_CONFIGS["chairman"]
    text, tokens = await call_agent(chairman_config, prompt)
    logger.info("Chairman responded (%d tokens)", tokens)

    # Parse JSON response
    synthesis = _parse_chairman_response(text)
    return synthesis


def _parse_chairman_response(text: str) -> ChairmanSynthesis:
    """Parse Chairman's JSON response into a structured object."""
    # Strip markdown code fences
    clean = text.strip()
    if clean.startswith("```"):
        clean = clean.split("\n", 1)[1] if "\n" in clean else clean[3:]
    if clean.endswith("```"):
        clean = clean.rsplit("```", 1)[0]

    try:
        data = json.loads(clean.strip())
    except json.JSONDecodeError:
        logger.warning("Chairman response not valid JSON — using raw text")
        return ChairmanSynthesis(
            summary=text,
            confidence=0.5,
            key_findings=[],
            contradictions=[],
            citations=[],
            methodology_notes="",
            agent_agreement=0.5,
        )

    citations = []
    for c in data.get("citations", []):
        citations.append(
            SourceCitation(
                claim=c.get("claim", ""),
                paper_id=c.get("paper_id", ""),
                paper_title=c.get("paper_title", ""),
                confidence=c.get("confidence", 0.5),
            )
        )

    return ChairmanSynthesis(
        summary=data.get("summary", ""),
        confidence=data.get("confidence", 0.5),
        key_findings=data.get("key_findings", []),
        contradictions=data.get("contradictions", []),
        citations=citations,
        methodology_notes=data.get("methodology_notes", ""),
        agent_agreement=data.get("agent_agreement", 0.5),
    )


# ── Full council run ─────────────────────────────────────────────────────────


async def run_full_council(
    query: str,
    context: str,
    paper_ids: list[str],
) -> CouncilResult:
    """
    Execute the complete 3-stage council deliberation:

    1. Stage 1 — 4 agents give independent opinions (parallel)
    2. Stage 2 — cross-review (parallel)
    3. Stage 3 — Chairman synthesis (OpenRouter)

    Returns a fully structured CouncilResult.
    """
    from council.deliberation import stage1_opinions, stage2_cross_review

    # Stage 1: parallel opinions
    logger.info("=== STAGE 1: Agent Opinions ===")
    stage1 = await stage1_opinions(query, context)

    # Stage 2: cross-review
    logger.info("=== STAGE 2: Cross-Review ===")
    stage2 = await stage2_cross_review(query, stage1)

    # Stage 3: chairman synthesis
    logger.info("=== STAGE 3: Chairman Synthesis ===")
    synthesis = await stage3_chairman_synthesis(query, stage1, stage2, paper_ids)

    total_tokens = sum(r.token_usage for r in stage1)
    logger.info(
        "Council complete — confidence=%.2f, tokens=%d",
        synthesis.confidence,
        total_tokens,
    )

    return CouncilResult(
        query=query,
        stage1_responses=stage1,
        stage2_reviews=stage2,
        synthesis=synthesis,
        paper_ids_used=paper_ids,
        total_tokens=total_tokens,
    )
