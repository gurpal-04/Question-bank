from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class GapAnalysisOutput(BaseModel):
    covered_concepts: List[str] = Field(
        description="Concepts clearly and correctly mentioned or explained"
    )
    missing_concepts: List[str] = Field(
        description="Expected concepts not mentioned at all"
    )
    incorrect_concepts: List[str] = Field(
        description="Concepts mentioned but explained incorrectly"
    )
    confusion_signals: List[str] = Field(
        description="Short phrases describing unclear reasoning or contradictions"
    )
    confidence_level: Literal["low", "medium", "high"] = Field(
        description="Reflects certainty and assertiveness of the answer"
    )
    clarity_level: Literal["low", "medium", "high"] = Field(
        description="Reflects structure and signal-to-noise"
    )
    followup_intent: Literal[
        "clarify_confusion",
        "fill_gap",
        "probe_depth",
        "ground_in_practice",
        "validate_understanding",
    ] = Field(description="The selected follow-up intent based on the analysis rules")

    # New scoring fields
    structure_score: float = Field(
        ge=1.0,
        le=5.0,
        description="Rating of answer organization and flow (1.0-5.0)",
    )
    depth_score: float = Field(
        ge=1.0,
        le=5.0,
        description="Rating of technical depth and detail (1.0-5.0)",
    )
    tradeoffs_score: float = Field(
        ge=1.0,
        le=5.0,
        description="Rating of pros/cons and contextual awareness (1.0-5.0)",
    )
    clarity_score: float = Field(
        ge=1.0,
        le=5.0,
        description="Rating of communication clarity (1.0-5.0)",
    )
    agent_version: str = Field("2.0", description="Version of the gap analysis agent")
