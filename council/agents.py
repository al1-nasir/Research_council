"""
Council agents — 4 specialist agents + Chairman definition.

All inference is via **Groq** (speed) and **OpenRouter** (multi-model chairman).
No local Ollama models — everything goes through API.

LLM calls are traced with Langfuse for observability.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Literal

import asyncio

import httpx
from groq import AsyncGroq, BadRequestError, RateLimitError
from tenacity import (
    retry,
    retry_if_exception_type,
    retry_if_not_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from api.langfuse_client import LangfuseLLMTracker, is_enabled
from config import GROQ_API_KEY, OPENROUTER_API_KEY, OPENROUTER_BASE_URL

# Serialise Groq calls so we never exceed the free-tier 6 000 TPM limit.
_groq_semaphore = asyncio.Semaphore(1)

logger = logging.getLogger(__name__)

# ── Agent definitions ─────────────────────────────────────────────────────────

Provider = Literal["groq", "openrouter"]


@dataclass
class AgentConfig:
    name: str
    role: str
    model: str
    provider: Provider
    system_prompt: str


AGENT_CONFIGS: dict[str, AgentConfig] = {
    "evidence": AgentConfig(
        name="Evidence Agent",
        role="evidence",
        model="llama-3.3-70b-versatile",
        provider="groq",
        system_prompt=(
            "You are a rigorous evidence analyst reviewing scientific literature. "
            "Given a knowledge graph subgraph and paper abstracts, summarize what "
            "the evidence actually shows. Be precise about sample sizes, study types, "
            "and effect sizes. Never speculate beyond what the data shows."
        ),
    ),
    "skeptic": AgentConfig(
        name="Skeptic Agent",
        role="skeptic",
        model="openai/gpt-oss-120b",
        provider="openrouter",
        system_prompt=(
            "You are a critical reviewer. Your job is to find weaknesses: "
            "biased study designs, underpowered samples, conflicting results, "
            "publication bias, or methodological flaws. Be constructively critical, "
            "not dismissive."
        ),
    ),
    "connector": AgentConfig(
        name="Connector Agent",
        role="connector",
        model="llama-3.1-8b-instant",
        provider="groq",
        system_prompt=(
            "You are a cross-domain knowledge connector. Find non-obvious links "
            "between concepts in the graph — drug repurposing opportunities, "
            "analogous mechanisms from other diseases, or techniques from adjacent "
            "fields that apply here."
        ),
    ),
    "methodology": AgentConfig(
        name="Methodology Agent",
        role="methodology",
        model="qwen/qwen3-32b",
        provider="openrouter",
        system_prompt=(
            "You evaluate research methodology. Assess whether experimental designs "
            "are appropriate, controls are adequate, statistical methods are sound, "
            "and whether conclusions are justified by the methods used."
        ),
    ),
    "chairman": AgentConfig(
        name="Chairman",
        role="chairman",
        model="openai/gpt-oss-20b",
        provider="openrouter",
        system_prompt=(
            "You are the Chairman of a research council. You receive responses from "
            "4 specialist agents and their cross-reviews. Synthesize them into a "
            "single authoritative answer. Assign a confidence score (0.0–1.0). "
            "Every claim must cite a specific paper node from the knowledge graph. "
            "Format your response as JSON with keys: summary, confidence, "
            "key_findings (list), contradictions (list), citations (list of "
            "{claim, paper_id, paper_title, confidence}), methodology_notes, "
            "agent_agreement (float)."
        ),
    ),
}


# ── LLM call wrappers ────────────────────────────────────────────────────────


@retry(
    stop=stop_after_attempt(6),
    wait=wait_exponential(min=2, max=60),
    retry=(
        retry_if_exception_type(RateLimitError)
        | retry_if_not_exception_type((BadRequestError, RateLimitError))
    ),
)
async def call_groq(
    model: str,
    system_prompt: str,
    user_message: str,
    temperature: float = 0.3,
    max_tokens: int = 800,
    agent_role: str | None = None,
) -> tuple[str, int]:
    """
    Call Groq API asynchronously, one request at a time (semaphore).

    Returns (response_text, token_count).
    
    Args:
        model: Groq model name
        system_prompt: System prompt for the agent
        user_message: User message/prompt
        temperature: Sampling temperature
        max_tokens: Maximum tokens to generate
        agent_role: Optional agent role for Langfuse tracking (e.g., "evidence", "chairman")
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]
    
    # Track with Langfuse if enabled
    tracker = None
    if is_enabled() and agent_role:
        tracker = LangfuseLLMTracker(agent_role, model)
        tracker.start(messages)
    
    try:
        async with _groq_semaphore:
            client = AsyncGroq(api_key=GROQ_API_KEY)
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            text = response.choices[0].message.content or ""
            tokens = response.usage.total_tokens if response.usage else 0
            
            # Extract token usage
            usage = {}
            if response.usage:
                usage = {
                    "input_tokens": response.usage.prompt_tokens or 0,
                    "output_tokens": response.usage.completion_tokens or 0,
                    "total_tokens": response.usage.total_tokens or 0,
                }
            
            # End Langfuse tracking
            if tracker:
                tracker.end(output=text, usage=usage)
            
            return text, tokens
    except Exception as e:
        # End Langfuse tracking with error
        if tracker:
            tracker.end(error=str(e))
        raise


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=15))
async def call_openrouter(
    model: str,
    system_prompt: str,
    user_message: str,
    temperature: float = 0.3,
    max_tokens: int = 2000,
    agent_role: str | None = None,
) -> tuple[str, int]:
    """
    Call OpenRouter API asynchronously (OpenAI-compatible endpoint).

    Returns (response_text, token_count).
    
    Args:
        model: OpenRouter model name
        system_prompt: System prompt for the agent
        user_message: User message/prompt
        temperature: Sampling temperature
        max_tokens: Maximum tokens to generate
        agent_role: Optional agent role for Langfuse tracking
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]
    
    # Track with Langfuse if enabled
    tracker = None
    if is_enabled() and agent_role:
        tracker = LangfuseLLMTracker(agent_role, model)
        tracker.start(messages)
    
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            resp.raise_for_status()

        data = resp.json()
        text = data["choices"][0]["message"]["content"] or ""
        
        # Extract token usage
        usage = {}
        if "usage" in data:
            usage = {
                "input_tokens": data["usage"].get("prompt_tokens", 0),
                "output_tokens": data["usage"].get("completion_tokens", 0),
                "total_tokens": data["usage"].get("total_tokens", 0),
            }
        
        tokens = usage.get("total_tokens", 0)
        
        # End Langfuse tracking
        if tracker:
            tracker.end(output=text, usage=usage)
        
        return text, tokens
    except Exception as e:
        # End Langfuse tracking with error
        if tracker:
            tracker.end(error=str(e))
        raise


async def call_agent(config: AgentConfig, user_message: str) -> tuple[str, int]:
    """
    Dispatch to the correct provider based on agent config.

    Returns (response_text, token_count).
    """
    if config.provider == "groq":
        return await call_groq(
            config.model, 
            config.system_prompt, 
            user_message,
            agent_role=config.role,
        )
    elif config.provider == "openrouter":
        return await call_openrouter(
            config.model, 
            config.system_prompt, 
            user_message,
            agent_role=config.role,
        )
    else:
        raise ValueError(f"Unknown provider: {config.provider}")
