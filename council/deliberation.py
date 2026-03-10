"""
Council deliberation — Stage 1 (opinions) and Stage 2 (cross-review).

All 4 agents run in **parallel** via asyncio.gather (never sequential).
"""

from __future__ import annotations

import asyncio
import logging

from council.agents import AGENT_CONFIGS, call_agent
from council.models import AgentResponse, CrossReview

logger = logging.getLogger(__name__)

# The four specialist agents (not chairman)
SPECIALIST_KEYS = ["evidence", "skeptic", "connector", "methodology"]

# Semaphore to limit concurrent API calls (avoid rate limits)
_api_semaphore = asyncio.Semaphore(2)  # Max 2 concurrent requests


# ── Stage 1: Independent opinions (parallel) ─────────────────────────────────


async def stage1_opinions(query: str, context: str) -> list[AgentResponse]:
    """
    Run all 4 specialist agents in parallel on the same query + context.

    Returns list of AgentResponse objects.
    """
    user_message = (
        f"Research Query: {query}\n\n"
        f"Retrieved Context (knowledge graph + paper chunks):\n{context}\n\n"
        "Provide your analysis based on your role."
    )

    async def _run_one(key: str) -> AgentResponse:
        async with _api_semaphore:
            config = AGENT_CONFIGS[key]
            # Add delay between requests to avoid rate limits
            await asyncio.sleep(2)
            text, tokens = await call_agent(config, user_message)
            logger.info("Agent '%s' responded (%d tokens)", config.name, tokens)
            return AgentResponse(
                agent_name=config.name,
                role=config.role,
                model=config.model,
                response=text,
                token_usage=tokens,
            )

    # Run ALL 4 agents in parallel — never sequential
    responses = await asyncio.gather(*[_run_one(k) for k in SPECIALIST_KEYS])
    total_tokens = sum(r.token_usage for r in responses)
    logger.info("Stage 1 complete — %d agents, %d total tokens", len(responses), total_tokens)
    return list(responses)


# ── Stage 2: Cross-review (parallel) ─────────────────────────────────────────


async def stage2_cross_review(
    query: str,
    stage1_responses: list[AgentResponse],
) -> list[CrossReview]:
    """
    Each agent reviews ALL OTHER agents' responses (anonymized).

    Returns list of CrossReview objects.
    """
    # Build anonymized summary of all responses
    anonymized_parts = []
    for i, resp in enumerate(stage1_responses):
        anonymized_parts.append(
            f"--- Agent {i+1} ({resp.role}) ---\n{resp.response}\n"
        )
    all_responses_text = "\n".join(anonymized_parts)

    async def _review(reviewer_key: str, reviewed_idx: int) -> CrossReview:
        reviewer_config = AGENT_CONFIGS[reviewer_key]
        reviewed_resp = stage1_responses[reviewed_idx]

        prompt = (
            f"Original query: {query}\n\n"
            f"All agent responses:\n{all_responses_text}\n\n"
            f"You are reviewing Agent {reviewed_idx+1} ({reviewed_resp.role})'s response.\n"
            "Rate your agreement (0.0=disagree, 1.0=fully agree), provide a critique, "
            "and list 2-3 key points. Be concise."
        )

        text, tokens = await call_agent(reviewer_config, prompt)

        # Parse agreement score from response (best-effort)
        agreement = _extract_agreement_score(text)

        return CrossReview(
            reviewer=reviewer_config.name,
            reviewed_agent=reviewed_resp.agent_name,
            agreement_score=agreement,
            critique=text,
            key_points=[],  # Could be parsed from structured output
        )

    # Each agent reviews every OTHER agent → 4×3 = 12 reviews
    # Run in small batches to avoid Groq rate-limit bursts
    review_args = [
        (reviewer_key, idx)
        for reviewer_key in SPECIALIST_KEYS
        for idx, resp in enumerate(stage1_responses)
        if resp.role != reviewer_key
    ]

    BATCH_SIZE = 1
    DELAY_BETWEEN_BATCHES = 5  # seconds delay between batches
    reviews: list[CrossReview] = []
    for i in range(0, len(review_args), BATCH_SIZE):
        batch = review_args[i : i + BATCH_SIZE]
        batch_results = await asyncio.gather(*[_review(rk, ri) for rk, ri in batch])
        reviews.extend(batch_results)
        # Add delay between batches to avoid rate limits
        if i + BATCH_SIZE < len(review_args):
            await asyncio.sleep(DELAY_BETWEEN_BATCHES)

    logger.info("Stage 2 complete — %d cross-reviews", len(reviews))
    return reviews


def _extract_agreement_score(text: str) -> float:
    """Best-effort extraction of agreement score from free-text response."""
    import re

    # Look for patterns like "Agreement: 0.7" or "Score: 0.8" or just "0.7"
    patterns = [
        r"agreement[:\s]+([01]\.?\d*)",
        r"score[:\s]+([01]\.?\d*)",
        r"\b([01]\.\d+)\b",
    ]
    for pat in patterns:
        match = re.search(pat, text.lower())
        if match:
            try:
                val = float(match.group(1))
                return min(max(val, 0.0), 1.0)
            except ValueError:
                continue
    return 0.5  # default if we can't parse
