from typing import List
from .base import Skill

FULLSTACK_SKILL_MAP: List[Skill] = [
    # ========== FOUNDATIONAL ==========
    Skill(
        id="fullstack_fundamentals",
        label="Full-Stack Fundamentals",
        level="foundational",
        description=(
            "Understanding of both frontend and backend concepts, "
            "client-server architecture, and HTTP basics."
        ),
        importance=5,
        interview_safe=True,
    ),
    Skill(
        id="database_web_integration",
        label="Database & Web Integration",
        level="foundational",
        description=(
            "Connecting databases to web applications, ORMs, "
            "and basic CRUD operations."
        ),
        importance=5,
        interview_safe=True,
    ),
    Skill(
        id="api_development",
        label="API Development",
        level="foundational",
        description=(
            "Building RESTful APIs, handling requests/responses, "
            "and API design patterns."
        ),
        importance=4,
        interview_safe=True,
    ),
    # ========== INTERMEDIATE ==========
    Skill(
        id="state_management",
        label="State Management",
        level="intermediate",
        description=(
            "Managing application state across frontend and backend, "
            "Redux/Context API, and session management."
        ),
        importance=4,
        interview_safe=True,
    ),
    Skill(
        id="authentication_authorization",
        label="Authentication & Authorization",
        level="intermediate",
        description=(
            "Implementing auth flows, JWT, OAuth, session management, "
            "and role-based access control."
        ),
        importance=4,
        interview_safe=True,
    ),
    Skill(
        id="deployment_basics",
        label="Deployment Basics",
        level="intermediate",
        description=(
            "Deploying full-stack applications, environment configuration, "
            "and basic CI/CD concepts."
        ),
        importance=3,
        interview_safe=True,
    ),
    # ========== ADVANCED ==========
    Skill(
        id="system_architecture",
        label="System Architecture",
        level="advanced",
        description=(
            "Designing scalable full-stack systems, microservices vs monolith, "
            "and architectural patterns."
        ),
        importance=3,
        interview_safe=False,
    ),
    Skill(
        id="performance_optimization",
        label="End-to-End Performance",
        level="advanced",
        description=(
            "Optimizing full-stack performance, caching strategies, "
            "database optimization, and frontend optimization."
        ),
        importance=2,
        interview_safe=False,
    ),
]
