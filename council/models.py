"""
Pydantic models for Council agent responses, cross-reviews, and final synthesis.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class AgentResponse(BaseModel):
    """Single agent's initial response to the research query."""

    agent_name: str
    role: str
    model: str
    response: str
    token_usage: int = 0


class CrossReview(BaseModel):
    """An agent's review of another agent's response."""

    reviewer: str
    reviewed_agent: str
    agreement_score: float = Field(ge=0.0, le=1.0, description="0=disagree, 1=fully agree")
    critique: str
    key_points: list[str] = Field(default_factory=list)


class SourceCitation(BaseModel):
    """A single citation linking a claim to a paper."""

    claim: str
    paper_id: str
    paper_title: str = ""
    confidence: float = Field(ge=0.0, le=1.0)


class ChairmanSynthesis(BaseModel):
    """Chairman's final synthesized answer."""

    summary: str
    confidence: float = Field(ge=0.0, le=1.0)
    key_findings: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    citations: list[SourceCitation] = Field(default_factory=list)
    methodology_notes: str = ""
    agent_agreement: float = Field(ge=0.0, le=1.0, description="How much agents agreed")


class CouncilResult(BaseModel):
    """Full result of a council deliberation."""

    query: str
    stage1_responses: list[AgentResponse] = Field(default_factory=list)
    stage2_reviews: list[CrossReview] = Field(default_factory=list)
    synthesis: ChairmanSynthesis | None = None
    paper_ids_used: list[str] = Field(default_factory=list)
    total_tokens: int = 0
