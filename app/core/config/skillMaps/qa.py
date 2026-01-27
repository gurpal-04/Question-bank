from typing import List
from .base import Skill

QA_SKILL_MAP: List[Skill] = [
    # ========== FOUNDATIONAL ==========
    Skill(
        id="testing_fundamentals",
        label="Testing Fundamentals",
        level="foundational",
        description=(
            "Core testing concepts including test types (unit, integration, system), "
            "test case design, and bug reporting."
        ),
        importance=5,
        interview_safe=True,
    ),
    Skill(
        id="manual_testing",
        label="Manual Testing Techniques",
        level="foundational",
        description=(
            "Exploratory testing, regression testing, smoke testing, "
            "and test execution strategies."
        ),
        importance=5,
        interview_safe=True,
    ),
    Skill(
        id="test_planning",
        label="Test Planning & Strategy",
        level="foundational",
        description=(
            "Test plan creation, test coverage analysis, "
            "risk-based testing, and prioritization."
        ),
        importance=4,
        interview_safe=True,
    ),
    # ========== INTERMEDIATE ==========
    Skill(
        id="automation_basics",
        label="Test Automation Basics",
        level="intermediate",
        description=(
            "Introduction to automation frameworks, Selenium/Playwright, "
            "and when to automate vs manual test."
        ),
        importance=4,
        interview_safe=True,
    ),
    Skill(
        id="api_testing",
        label="API Testing",
        level="intermediate",
        description=(
            "REST API testing, Postman/REST Assured, "
            "validating responses, and contract testing."
        ),
        importance=4,
        interview_safe=True,
    ),
    Skill(
        id="defect_management",
        label="Defect Management & Tracking",
        level="intermediate",
        description=(
            "Bug lifecycle, severity vs priority, "
            "JIRA/bug tracking tools, and defect metrics."
        ),
        importance=3,
        interview_safe=True,
    ),
    # ========== ADVANCED ==========
    Skill(
        id="performance_testing",
        label="Performance & Load Testing",
        level="advanced",
        description=(
            "JMeter/k6, performance metrics, bottleneck analysis, "
            "and scalability testing."
        ),
        importance=3,
        interview_safe=False,
    ),
    Skill(
        id="security_testing",
        label="Security Testing",
        level="advanced",
        description=(
            "OWASP Top 10, penetration testing basics, "
            "security scanning tools, and vulnerability assessment."
        ),
        importance=2,
        interview_safe=False,
    ),
]
