from dataclasses import dataclass
from typing import Literal

SkillLevel = Literal["foundational", "intermediate", "advanced"]


@dataclass(frozen=True)
class Skill:
    """
    Base class for skill definitions.
    """

    id: str
    label: str
    level: SkillLevel
    description: str
    importance: int  # 1–5 (used for weighted selection)
    interview_safe: bool  # allowed as Q1 skill
