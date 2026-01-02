# app/logic/archetype_selector.py

import random
from typing import Optional
from app.core.config.question_archetypes import QUESTION_ARCHETYPES, QuestionArchetype


def select_question_archetype(
    *,
    role: str,
    experience: str,
    seed: Optional[str] = None,
) -> QuestionArchetype:
    """
    Selects a question archetype for the FIRST interview question.

    Rules:
    - Experience-gated
    - Weighted randomness
    - Deterministic if seed is provided
    - No LLM involvement
    """

    # 1. Filter by experience
    eligible_archetypes = [
        archetype
        for archetype in QUESTION_ARCHETYPES.values()
        if experience in archetype.allowed_experience
    ]

    if not eligible_archetypes:
        raise ValueError(f"No archetypes available for experience={experience}")

    # 2. Apply deterministic randomness if seed exists
    if seed:
        random.seed(seed)

    # 3. Weighted random selection
    weights = [a.base_weight for a in eligible_archetypes]

    selected = random.choices(
        population=eligible_archetypes,
        weights=weights,
        k=1
    )[0]

    return selected
