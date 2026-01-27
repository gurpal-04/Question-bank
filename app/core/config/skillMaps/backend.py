from typing import List
from .base import Skill

BACKEND_SKILL_MAP: List[Skill] = [
    # ========== FOUNDATIONAL ==========
    Skill(
        id="api_design",
        label="REST API Design",
        level="foundational",
        description=(
            "Principles of RESTful APIs, resource naming, HTTP methods, "
            "status codes, and standard patterns."
        ),
        importance=5,
        interview_safe=True,
    ),
    Skill(
        id="database_basics",
        label="Database Fundamentals",
        level="foundational",
        description=(
            "Relational database concepts, SQL basics, ACID properties, "
            "and basic schema design."
        ),
        importance=5,
        interview_safe=True,
    ),
    Skill(
        id="backend_security_basics",
        label="Backend Security Basics",
        level="foundational",
        description=(
            "Authentication (JWT/Session), Authorization (RBAC), "
            "and protection against common vulnerabilities like SQL Injection."
        ),
        importance=4,
        interview_safe=True,
    ),
    # ========== INTERMEDIATE ==========
    Skill(
        id="concurrency_model",
        label="Execution Model & Concurrency",
        level="intermediate",
        description=(
            "Process vs Thread, Async/Await models, Event Loops, "
            "and handling concurrent requests."
        ),
        importance=4,
        interview_safe=True,
    ),
    Skill(
        id="caching_strategies",
        label="Caching Strategies",
        level="intermediate",
        description=(
            "In-memory caching (Redis/Memcached), cache invalidation, "
            "and CDN integration."
        ),
        importance=4,
        interview_safe=True,
    ),
    Skill(
        id="testing_backend",
        label="Backend Testing",
        level="intermediate",
        description=(
            "Unit testing, Integration testing, Mocking, "
            "and Test-Driven Development (TDD) for backend services."
        ),
        importance=3,
        interview_safe=True,
    ),
    # ========== ADVANCED ==========
    Skill(
        id="distributed_systems",
        label="Distributed Systems",
        level="advanced",
        description=(
            "Microservices architecture, consistency models (CAP theorem), "
            "distributed transactions, and message queues."
        ),
        importance=4,
        interview_safe=False,
    ),
    Skill(
        id="database_optimization",
        label="Database Performance & Scaling",
        level="advanced",
        description=(
            "Indexing strategies, query optimization, sharding, "
            "replication, and NoSQL alternatives."
        ),
        importance=3,
        interview_safe=False,
    ),
]
