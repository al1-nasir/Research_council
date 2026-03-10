"""
Langfuse client — centralized observability for LLM calls and tool usage.

This module provides:
- Langfuse client initialization
- LLM call tracing with token usage
- Tool call tracing
"""

from __future__ import annotations

import logging
from typing import Any

from langfuse import Langfuse

import config

logger = logging.getLogger(__name__)

# Lazy-initialized Langfuse client
_langfuse_client: Langfuse | None = None


def get_langfuse() -> Langfuse | None:
    """
    Get the Langfuse client, initializing if needed.
    
    Returns None if Langfuse is not configured (missing API keys).
    """
    global _langfuse_client
    
    if _langfuse_client is not None:
        return _langfuse_client
    
    # Check if Langfuse is configured
    if not config.LANGFUSE_PUBLIC_KEY or not config.LANGFUSE_SECRET_KEY:
        logger.warning(
            "Langfuse not configured — set LANGFUSE_PUBLIC_KEY and "
            "LANGFUSE_SECRET_KEY in .env to enable observability"
        )
        return None
    
    try:
        _langfuse_client = Langfuse(
            public_key=config.LANGFUSE_PUBLIC_KEY,
            secret_key=config.LANGFUSE_SECRET_KEY,
            host=config.LANGFUSE_HOST,
        )
        logger.info("Langfuse initialized: %s", config.LANGFUSE_HOST)
        return _langfuse_client
    except Exception as e:
        logger.error("Failed to initialize Langfuse: %s", e)
        return None


def is_enabled() -> bool:
    """Check if Langfuse is available and configured."""
    langfuse = get_langfuse()
    if not langfuse:
        return False
    try:
        langfuse.auth_check()
        return True
    except Exception:
        return False


# ── LLM Call Tracking ──────────────────────────────────────────────────────────


class LangfuseLLMTracker:
    """
    Simple tracker for LLM calls with Langfuse.
    
    Usage:
        tracker = LangfuseLLMTracker("specialist", model_name)
        tracker.start(messages)
        # ... make LLM call ...
        tracker.end(output, usage)
    """
    
    def __init__(self, name: str, model: str, metadata: dict[str, Any] | None = None):
        self.name = name
        self.model = model
        self.metadata = metadata or {}
        self._observation = None
    
    def start(self, messages: list[dict[str, str]]) -> None:
        """Start tracking with messages."""
        langfuse = get_langfuse()
        if langfuse:
            try:
                self._observation = langfuse.start_observation(
                    name=self.name,
                    input={"messages": messages},
                    metadata={
                        **self.metadata,
                        "model": self.model,
                    },
                )
            except Exception as e:
                logger.warning("Failed to create Langfuse observation: %s", e)
                self._observation = None
    
    def end(
        self,
        output: str | None = None,
        usage: dict[str, int] | None = None,
        error: str | None = None,
    ) -> None:
        """
        End the observation.
        
        Args:
            output: The LLM response text
            usage: Token usage dict with input_tokens, output_tokens, total_tokens
            error: Error message if the call failed
        """
        if self._observation is None:
            return
        
        try:
            # Update with output
            if output:
                self._observation.update(output=output)
            
            # End the observation
            if error:
                self._observation.end()
            else:
                self._observation.end()
                
        except Exception as e:
            logger.warning("Error ending Langfuse observation: %s", e)


# ── Tool Call Tracing ──────────────────────────────────────────────────────────


def trace_tool(
    name: str,
    input_data: dict[str, Any] | None = None,
    output: Any = None,
    error: Exception | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """
    Trace a tool call in Langfuse.
    """
    langfuse = get_langfuse()
    if not langfuse:
        return
    
    try:
        obs = langfuse.start_observation(
            name=name,
            input=input_data,
            metadata=metadata or {},
        )
        
        if error:
            obs.end()
        elif output is not None:
            obs.update(output=str(output)[:1000])  # Truncate long outputs
            obs.end()
        else:
            obs.end()
            
    except Exception as e:
        logger.warning("Failed to trace tool call %s: %s", name, e)


# ── Score / Feedback ────────────────────────────────────────────────────────────


def log_score(
    trace_id: str,
    name: str,
    value: float,
    comment: str | None = None,
) -> None:
    """
    Log a score/feedback for a trace.
    """
    langfuse = get_langfuse()
    if not langfuse:
        return
    
    try:
        langfuse.create_score(
            trace_id=trace_id,
            name=name,
            value=value,
            comment=comment,
        )
    except Exception as e:
        logger.warning("Failed to log score: %s", e)


# ── Flush / Shutdown ────────────────────────────────────────────────────────────


def flush() -> None:
    """Flush any pending Langfuse data."""
    langfuse = get_langfuse()
    if langfuse:
        try:
            langfuse.flush()
        except Exception as e:
            logger.warning("Error flushing Langfuse: %s", e)
