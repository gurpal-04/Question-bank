from typing import List
from .base import Skill

ML_SKILL_MAP: List[Skill] = [
    # ========== FOUNDATIONAL ==========
    Skill(
        id="ml_fundamentals",
        label="ML Fundamentals",
        level="foundational",
        description=(
            "Supervised vs unsupervised learning, model training, "
            "evaluation metrics, and overfitting/underfitting."
        ),
        importance=5,
        interview_safe=True,
    ),
    Skill(
        id="feature_engineering",
        label="Feature Engineering",
        level="foundational",
        description=(
            "Feature selection, transformation, encoding categorical variables, "
            "and handling missing data."
        ),
        importance=5,
        interview_safe=True,
    ),
    Skill(
        id="ml_algorithms",
        label="ML Algorithms",
        level="foundational",
        description=(
            "Linear regression, decision trees, random forests, "
            "gradient boosting, and neural networks basics."
        ),
        importance=4,
        interview_safe=True,
    ),
    # ========== INTERMEDIATE ==========
    Skill(
        id="model_evaluation",
        label="Model Evaluation & Tuning",
        level="intermediate",
        description=(
            "Cross-validation, hyperparameter tuning, "
            "bias-variance tradeoff, and model selection."
        ),
        importance=4,
        interview_safe=True,
    ),
    Skill(
        id="deep_learning",
        label="Deep Learning",
        level="intermediate",
        description=(
            "Neural networks, CNNs, RNNs, transformers, "
            "PyTorch/TensorFlow, and training techniques."
        ),
        importance=4,
        interview_safe=True,
    ),
    Skill(
        id="ml_deployment",
        label="ML Model Deployment",
        level="intermediate",
        description=(
            "Model serving, API endpoints, containerization, "
            "and production ML systems."
        ),
        importance=3,
        interview_safe=True,
    ),
    # ========== ADVANCED ==========
    Skill(
        id="mlops",
        label="MLOps & Production ML",
        level="advanced",
        description=(
            "ML pipelines, model monitoring, A/B testing, "
            "feature stores, and ML system design."
        ),
        importance=3,
        interview_safe=False,
    ),
    Skill(
        id="advanced_ml_topics",
        label="Advanced ML Topics",
        level="advanced",
        description=(
            "Reinforcement learning, GANs, transfer learning, "
            "model interpretability, and fairness."
        ),
        importance=2,
        interview_safe=False,
    ),
]
