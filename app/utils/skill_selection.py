import random
from typing import List, Optional
from app.core.config.skillMaps.base import Skill


EXPERIENCE_TO_LEVELS = {
    "beginner": {"foundational"},
    "intermediate": {"foundational", "intermediate"},
    "advanced": {"intermediate", "advanced"},
}


def select_primary_skill(
    skills: List[Skill],
    experience_level: str,
    past_skill_signals: Optional[dict] = None,  # unused in MVP
) -> Skill:
    """
    Selects exactly ONE primary skill for Q1 calibration.

    Deterministic filters + controlled randomness.
    """

    if experience_level not in EXPERIENCE_TO_LEVELS:
        raise ValueError(f"Invalid experience level: {experience_level}")

    allowed_levels = EXPERIENCE_TO_LEVELS[experience_level]

    # STEP 1: Interview-safe only
    eligible = [
        skill
        for skill in skills
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


def select_next_skill_by_importance(
    skills: List[Skill],
    used_skill_ids: List[str],
    experience_level: str,
) -> Optional[Skill]:
    """
    Select the highest-importance unused skill for a new primary question.

    Selection criteria:
    - interview_safe = True
    - appropriate for experience level
    - not in used_skill_ids

    Returns:
        The highest-importance eligible skill, or None if no skills available.
    """
    if experience_level not in EXPERIENCE_TO_LEVELS:
        # Fallback to intermediate if invalid level
        allowed_levels = EXPERIENCE_TO_LEVELS.get(
            "intermediate", {"foundational", "intermediate"}
        )
    else:
        allowed_levels = EXPERIENCE_TO_LEVELS[experience_level]

    # Filter eligible skills
    eligible = [
        skill
        for skill in skills
        if skill.interview_safe
        and skill.level in allowed_levels
        and skill.id not in used_skill_ids
    ]

    if not eligible:
        return None

    # Sort by importance (descending) and return the highest
    eligible.sort(key=lambda s: s.importance, reverse=True)

    return eligible[0]
