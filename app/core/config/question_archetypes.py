# app/config/question_archetypes.py

from typing import Dict, List
from dataclasses import dataclass


@dataclass(frozen=True)
class QuestionArchetype:
    id: str
    label: str
    description: str
    base_weight: float
    allowed_experience: List[str]  # ["0-1", "1-3", "3-5", "5-7", "7-10", "10+"]


QUESTION_ARCHETYPES: Dict[str, QuestionArchetype] = {
    "CORE_EXPLANATION": QuestionArchetype(
        id="CORE_EXPLANATION",
        label="Core Concept Explanation",
        description="Explain a core concept clearly and sequentially.",
        base_weight=0.45,
        allowed_experience=["0-1", "1-3", "3-5", "5-7", "7-10", "10+"],
    ),
    "CONCEPT_USAGE": QuestionArchetype(
        id="CONCEPT_USAGE",
        label="Concept + Real-World Usage",
        description="Explain a concept and how it applies in real scenarios.",
        base_weight=0.25,
        allowed_experience=["1-3", "3-5", "5-7", "7-10", "10+"],
    ),
    "TRADEOFF": QuestionArchetype(
        id="TRADEOFF",
        label="Comparison / Trade-off",
        description="Discuss trade-offs between approaches or decisions.",
        base_weight=0.15,
        allowed_experience=["3-5", "5-7", "7-10", "10+"],
    ),
    "INTERNALS_HIGH_LEVEL": QuestionArchetype(
        id="INTERNALS_HIGH_LEVEL",
        label="High-Level Internals",
        description="Explain internal workings at a high level.",
        base_weight=0.10,
        allowed_experience=["3-5", "5-7", "7-10", "10+"],
    ),
    "PSEUDO_IMPLEMENTATION": QuestionArchetype(
        id="PSEUDO_IMPLEMENTATION",
        label="Pseudo Implementation",
        description="Describe how you would implement something at a high level.",
        base_weight=0.05,
        allowed_experience=["5-7", "7-10", "10+"],
    ),
}
