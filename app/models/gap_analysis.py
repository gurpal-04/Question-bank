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
    followup_intent: Optional [Literal[
        "clarify_confusion",
        "fill_gap",
        "probe_depth",
        "ground_in_practice",
        "validate_understanding",
    ] | None] = Field(description="The selected follow-up intent based on the analysis rules")
