from typing import List
from .base import Skill

DEVOPS_SKILL_MAP: List[Skill] = [
    # ========== FOUNDATIONAL ==========
    Skill(
        id="linux_fundamentals",
        label="Linux & Shell Scripting",
        level="foundational",
        description=(
            "Linux command line, bash scripting, file systems, "
            "processes, and system administration basics."
        ),
        importance=5,
        interview_safe=True,
    ),
    Skill(
        id="version_control",
        label="Version Control & Git",
        level="foundational",
        description=(
            "Git workflows, branching strategies, merge conflicts, "
            "and collaboration patterns."
        ),
        importance=5,
        interview_safe=True,
    ),
    Skill(
        id="cicd_basics",
        label="CI/CD Fundamentals",
        level="foundational",
        description=(
            "Continuous integration, continuous deployment, "
            "Jenkins/GitHub Actions, and automated testing."
        ),
        importance=4,
        interview_safe=True,
    ),
    # ========== INTERMEDIATE ==========
    Skill(
        id="containerization",
        label="Containerization",
        level="intermediate",
        description=(
            "Docker, container images, Dockerfile best practices, "
            "and container orchestration basics."
        ),
        importance=4,
        interview_safe=True,
    ),
    Skill(
        id="infrastructure_as_code",
        label="Infrastructure as Code",
        level="intermediate",
        description=(
            "Terraform, CloudFormation, infrastructure provisioning, "
            "and configuration management."
        ),
        importance=4,
        interview_safe=True,
    ),
    Skill(
        id="monitoring_logging",
        label="Monitoring & Logging",
        level="intermediate",
        description=(
            "Prometheus, Grafana, ELK stack, log aggregation, "
            "and observability practices."
        ),
        importance=3,
        interview_safe=True,
    ),
    # ========== ADVANCED ==========
    Skill(
        id="kubernetes",
        label="Kubernetes & Orchestration",
        level="advanced",
        description=(
            "K8s architecture, deployments, services, ingress, "
            "scaling, and cluster management."
        ),
        importance=3,
        interview_safe=False,
    ),
    Skill(
        id="cloud_architecture",
        label="Cloud Architecture & SRE",
        level="advanced",
        description=(
            "AWS/GCP/Azure, high availability, disaster recovery, "
            "SRE principles, and incident management."
        ),
        importance=2,
        interview_safe=False,
    ),
]
