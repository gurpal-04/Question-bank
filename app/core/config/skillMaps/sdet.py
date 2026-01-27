from typing import List
from .base import Skill

SDET_SKILL_MAP: List[Skill] = [
    # ========== FOUNDATIONAL ==========
    Skill(
        id="programming_for_testing",
        label="Programming for Testing",
        level="foundational",
        description=(
            "Core programming concepts (variables, loops, functions), "
            "data structures, and coding for test automation."
        ),
        importance=5,
        interview_safe=True,
    ),
    Skill(
        id="test_automation_frameworks",
        label="Test Automation Frameworks",
        level="foundational",
        description=(
            "Selenium, Playwright, Cypress, TestNG/JUnit, "
            "and framework architecture patterns (Page Object Model)."
        ),
        importance=5,
        interview_safe=True,
    ),
    Skill(
        id="version_control_ci",
        label="Version Control & CI/CD",
        level="foundational",
        description=(
            "Git basics, GitHub/GitLab, CI/CD pipelines (Jenkins/GitHub Actions), "
            "and integrating tests into build processes."
        ),
        importance=4,
        interview_safe=True,
    ),
    # ========== INTERMEDIATE ==========
    Skill(
        id="api_automation",
        label="API Test Automation",
        level="intermediate",
        description=(
            "REST Assured, API testing frameworks, "
            "request/response validation, and contract testing automation."
        ),
        importance=4,
        interview_safe=True,
    ),
    Skill(
        id="test_data_management",
        label="Test Data Management",
        level="intermediate",
        description=(
            "Test data generation, database interactions, "
            "mocking/stubbing, and data-driven testing."
        ),
        importance=4,
        interview_safe=True,
    ),
    Skill(
        id="debugging_troubleshooting",
        label="Debugging & Troubleshooting",
        level="intermediate",
        description=(
            "Debugging test failures, log analysis, "
            "flaky test identification, and root cause analysis."
        ),
        importance=3,
        interview_safe=True,
    ),
    # ========== ADVANCED ==========
    Skill(
        id="test_infrastructure",
        label="Test Infrastructure & Scaling",
        level="advanced",
        description=(
            "Distributed test execution, Selenium Grid/Docker, "
            "cloud testing platforms, and parallel execution strategies."
        ),
        importance=3,
        interview_safe=False,
    ),
    Skill(
        id="advanced_automation_patterns",
        label="Advanced Automation Patterns",
        level="advanced",
        description=(
            "Custom framework development, design patterns in testing, "
            "BDD/TDD implementation, and test architecture."
        ),
        importance=2,
        interview_safe=False,
    ),
]
