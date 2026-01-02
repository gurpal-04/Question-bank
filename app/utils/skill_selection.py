import random
from typing import List, Optional
from app.core.config.skillMaps.frontend import FrontendSkill, FRONTEND_SKILL_MAP


EXPERIENCE_TO_LEVELS = {
    "beginner": {"foundational"},
    "intermediate": {"foundational", "intermediate"},
    "advanced": {"intermediate", "advanced"},
}


def select_primary_skill(
    skills: List[FrontendSkill],
    experience_level: str,
    past_skill_signals: Optional[dict] = None,  # unused in MVP
) -> FrontendSkill:
    """
    Selects exactly ONE primary skill for Q1 calibration.

    Deterministic filters + controlled randomness.
    """

    if experience_level not in EXPERIENCE_TO_LEVELS:
        raise ValueError(f"Invalid experience level: {experience_level}")

    allowed_levels = EXPERIENCE_TO_LEVELS[experience_level]

    # STEP 1: Interview-safe only
    eligible = [
        skill for skill in skills
        if skill.interview_safe and skill.level in allowed_levels
    ]

    if not eligible:
        raise RuntimeError("No eligible skills found for Q1")

    # STEP 2: Sort by importance (descending)
    eligible.sort(key=lambda s: s.importance, reverse=True)

    # STEP 3: Pick from top 3
    top_candidates = eligible[:3]

    # STEP 4: Random choice
    selected_skill = random.choice(top_candidates)

    return selected_skill
