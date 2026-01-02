"""
Utility functions to map between different experience level formats used across the system.

Formats:
- API format: "0-3 years", "3-5 years", "5+ years"
- Archetype format: "0-1", "1-3", "3-5", "5-7", "7-10", "10+"
- Skill level format: "beginner", "intermediate", "advanced"
"""


def normalize_experience_for_archetype(experience_range: str) -> str:
    """
    Convert API experience range format to archetype selector format.
    
    Args:
        experience_range: Experience in API format (e.g., "0-3 years", "3-5 years", "5+ years")
    
    Returns:
        Experience in archetype format (e.g., "1-3", "3-5", "5-7")
    
    Examples:
        "0-3 years" -> "1-3"
        "3-5 years" -> "3-5"
        "5+ years" -> "5-7" (defaults to 5-7 for 5+)
    """
    experience_range = experience_range.strip().lower()
    
    # Remove "years" suffix if present
    if experience_range.endswith(" years"):
        experience_range = experience_range[:-6].strip()
    
    # Map to archetype format
    if experience_range in ["0-3", "0-1", "1-3"]:
        return "1-3"
    elif experience_range in ["3-5"]:
        return "3-5"
    elif experience_range in ["5+", "5-7", "7-10", "10+"]:
        # For 5+, default to 5-7 (most common for mid-level)
        # This could be made more sophisticated later
        if experience_range == "5+":
            return "5-7"
        return experience_range
    else:
        # Try to parse and map
        if "-" in experience_range:
            parts = experience_range.split("-")
            if len(parts) == 2:
                try:
                    start = int(parts[0])
                    end = int(parts[1])
                    if start < 3:
                        return "1-3"
                    elif start < 5:
                        return "3-5"
                    else:
                        return "5-7"
                except ValueError:
                    pass
        
        # Default fallback
        raise ValueError(f"Unable to map experience range: {experience_range}")


def normalize_experience_for_skill(experience_range: str) -> str:
    """
    Convert API experience range format to skill selector format.
    
    Args:
        experience_range: Experience in API format (e.g., "0-3 years", "3-5 years", "5+ years")
    
    Returns:
        Experience in skill format: "beginner", "intermediate", or "advanced"
    
    Examples:
        "0-3 years" -> "beginner"
        "3-5 years" -> "intermediate"
        "5+ years" -> "advanced"
    """
    experience_range = experience_range.strip().lower()
    
    # Remove "years" suffix if present
    if experience_range.endswith(" years"):
        experience_range = experience_range[:-6].strip()
    
    # Map to skill level
    if experience_range in ["0-3", "0-1", "1-3"]:
        return "beginner"
    elif experience_range in ["3-5"]:
        return "intermediate"
    elif experience_range in ["5+", "5-7", "7-10", "10+"]:
        return "advanced"
    else:
        # Try to parse and map
        if "-" in experience_range:
            parts = experience_range.split("-")
            if len(parts) == 2:
                try:
                    start = int(parts[0])
                    if start < 3:
                        return "beginner"
                    elif start < 5:
                        return "intermediate"
                    else:
                        return "advanced"
                except ValueError:
                    pass
        elif experience_range.endswith("+"):
            # For "5+" format
            try:
                start = int(experience_range[:-1])
                if start >= 5:
                    return "advanced"
            except ValueError:
                pass
        
        # Default fallback
        raise ValueError(f"Unable to map experience range to skill level: {experience_range}")

