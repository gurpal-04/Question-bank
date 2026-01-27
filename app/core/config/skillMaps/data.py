from typing import List
from .base import Skill

DATA_SKILL_MAP: List[Skill] = [
    # ========== FOUNDATIONAL ==========
    Skill(
        id="data_modeling",
        label="Data Modeling",
        level="foundational",
        description=(
            "Designing data schemas, normalization, denormalization, "
            "and data warehouse concepts."
        ),
        importance=5,
        interview_safe=True,
    ),
    Skill(
        id="sql_fundamentals",
        label="SQL & Query Optimization",
        level="foundational",
        description=(
            "Advanced SQL queries, joins, aggregations, window functions, "
            "and query performance tuning."
        ),
        importance=5,
        interview_safe=True,
    ),
    Skill(
        id="etl_basics",
        label="ETL/ELT Fundamentals",
        level="foundational",
        description=(
            "Extract, Transform, Load processes, data pipelines, "
            "and batch vs streaming processing."
        ),
        importance=4,
        interview_safe=True,
    ),
    # ========== INTERMEDIATE ==========
    Skill(
        id="data_pipeline_tools",
        label="Data Pipeline Tools",
        level="intermediate",
        description=(
            "Apache Airflow, dbt, data orchestration, " "and workflow management."
        ),
        importance=4,
        interview_safe=True,
    ),
    Skill(
        id="big_data_processing",
        label="Big Data Processing",
        level="intermediate",
        description=(
            "Spark, distributed computing, partitioning, "
            "and handling large-scale data."
        ),
        importance=4,
        interview_safe=True,
    ),
    Skill(
        id="data_quality",
        label="Data Quality & Validation",
        level="intermediate",
        description=(
            "Data validation, testing data pipelines, "
            "monitoring data quality, and handling data anomalies."
        ),
        importance=3,
        interview_safe=True,
    ),
    # ========== ADVANCED ==========
    Skill(
        id="data_architecture",
        label="Data Architecture",
        level="advanced",
        description=(
            "Data lake vs warehouse, lakehouse architecture, "
            "data mesh, and scalable data systems."
        ),
        importance=3,
        interview_safe=False,
    ),
    Skill(
        id="streaming_systems",
        label="Real-Time Streaming",
        level="advanced",
        description=(
            "Kafka, stream processing, real-time analytics, "
            "and event-driven architectures."
        ),
        importance=2,
        interview_safe=False,
    ),
]
