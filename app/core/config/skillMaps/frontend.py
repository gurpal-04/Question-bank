from typing import List
from .base import Skill

# ========= Legacy Alias for Backward Compatibility =========
FrontendSkill = Skill

FRONTEND_SKILL_MAP: List[Skill] = [
    # ========== FOUNDATIONAL ==========
    # High-signal, interview-safe for Q1
    Skill(
        id="js_fundamentals",
        label="JavaScript Fundamentals",
        level="foundational",
        description=(
            "Core JavaScript concepts such as variables, scope, closures, "
            "and execution context."
        ),
        importance=5,
        interview_safe=True,
    ),
    Skill(
        id="browser_rendering",
        label="Browser Rendering & DOM",
        level="foundational",
        description=(
            "How browsers parse HTML/CSS, build the DOM/CSSOM, " "and render pages."
        ),
        importance=5,
        interview_safe=True,
    ),
    Skill(
        id="html_css_basics",
        label="HTML & CSS Basics",
        level="foundational",
        description=(
            "Semantic HTML, CSS layout basics, and how styles affect rendering."
        ),
        importance=4,
        interview_safe=True,
    ),
    # ========== INTERMEDIATE ==========
    # Used only if experience allows
    Skill(
        id="js_execution_model",
        label="JavaScript Execution Model",
        level="intermediate",
        description=(
            "Call stack, event loop, microtasks, macrotasks, " "and async behavior."
        ),
        importance=4,
        interview_safe=True,
    ),
    Skill(
        id="react_rendering_basics",
        label="React Rendering Basics",
        level="intermediate",
        description=("Component rendering, reconciliation, and state-driven updates."),
        importance=4,
        interview_safe=True,
    ),
    Skill(
        id="frontend_performance_basics",
        label="Frontend Performance Basics",
        level="intermediate",
        description=(
            "Bundle size, rendering performance, and basic optimization strategies."
        ),
        importance=3,
        interview_safe=True,
    ),
    # ========== ADVANCED ==========
    Skill(
        id="rendering_optimizations",
        label="Rendering Optimizations",
        level="advanced",
        description=(
            "Advanced rendering strategies, memoization, " "and performance tuning."
        ),
        importance=3,
        interview_safe=False,
    ),
    Skill(
        id="memory_management",
        label="Memory Management & Leaks",
        level="advanced",
        description=(
            "Memory profiling, garbage collection behavior, " "and leak prevention."
        ),
        importance=2,
        interview_safe=False,
    ),
]
