from typing import List
from app.core.config.skillMaps.base import Skill
from app.core.config.skillMaps.frontend import FRONTEND_SKILL_MAP
from app.core.config.skillMaps.backend import BACKEND_SKILL_MAP
from app.core.config.skillMaps.qa import QA_SKILL_MAP
from app.core.config.skillMaps.sdet import SDET_SKILL_MAP
from app.core.config.skillMaps.fullstack import FULLSTACK_SKILL_MAP
from app.core.config.skillMaps.data import DATA_SKILL_MAP
from app.core.config.skillMaps.ml import ML_SKILL_MAP
from app.core.config.skillMaps.devops import DEVOPS_SKILL_MAP


def get_skill_map_for_role(role: str) -> List[Skill]:
    """
    Returns the appropriate skill map based on the role.
    Supports both value-based matching (from frontend) and keyword-based matching.

    Frontend sends values like: "frontend", "backend", "fullstack", "data", "ml", "devops"
    Also supports keyword matching for backward compatibility.
    """
    role_lower = role.lower()

    # Value-based matching (from frontend dropdown)
    if role_lower == "frontend":
        return FRONTEND_SKILL_MAP
    elif role_lower == "backend":
        return BACKEND_SKILL_MAP
    elif role_lower == "fullstack":
        return FULLSTACK_SKILL_MAP
    elif role_lower == "data":
        return DATA_SKILL_MAP
    elif role_lower == "ml":
        return ML_SKILL_MAP
    elif role_lower == "devops":
        return DEVOPS_SKILL_MAP

    # Keyword-based matching (backward compatibility)
    elif "backend" in role_lower:
        return BACKEND_SKILL_MAP
    elif "qa" in role_lower or "quality assurance" in role_lower:
        return QA_SKILL_MAP
    elif "sdet" in role_lower or "software development engineer in test" in role_lower:
        return SDET_SKILL_MAP
    elif (
        "fullstack" in role_lower
        or "full-stack" in role_lower
        or "full stack" in role_lower
    ):
        return FULLSTACK_SKILL_MAP
    elif "data" in role_lower:
        return DATA_SKILL_MAP
    elif "ml" in role_lower or "machine learning" in role_lower:
        return ML_SKILL_MAP
    elif "devops" in role_lower:
        return DEVOPS_SKILL_MAP

    # Default to frontend for backward compatibility
    return FRONTEND_SKILL_MAP
