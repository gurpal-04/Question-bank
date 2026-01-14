from typing import Dict, Any, Literal

EXPERIENCE_BENCHMARKS = {
    "0-3 years": {
        "overall_target": 60,
        "readiness_threshold": {
            "not_ready": 0,
            "needs_improvement": 40,
            "interview_ready": 60,
            "exceeds_expectations": 80,
        },
        "dimension_targets": {
            "structure": 3.0,
            "depth": 2.5,
            "tradeoffs": 2.0,
            "clarity": 3.0,
        },
        "followup_ratio_target": 0.6,
    },
    "3-5 years": {
        "overall_target": 75,
        "readiness_threshold": {
            "not_ready": 0,
            "needs_improvement": 55,
            "interview_ready": 75,
            "exceeds_expectations": 90,
        },
        "dimension_targets": {
            "structure": 3.5,
            "depth": 3.5,
            "tradeoffs": 3.0,
            "clarity": 3.5,
        },
        "followup_ratio_target": 0.4,
    },
    "5+ years": {
        "overall_target": 85,
        "readiness_threshold": {
            "not_ready": 0,
            "needs_improvement": 65,
            "interview_ready": 85,
            "exceeds_expectations": 95,
        },
        "dimension_targets": {
            "structure": 4.0,
            "depth": 4.5,
            "tradeoffs": 4.0,
            "clarity": 4.0,
        },
        "followup_ratio_target": 0.3,
    },
}

DIMENSION_WEIGHTS = {
    "structure": 0.20,
    "depth": 0.35,
    "tradeoffs": 0.20,
    "clarity": 0.25,
}


def get_benchmark(experience_range: str) -> Dict[str, Any]:
    return EXPERIENCE_BENCHMARKS.get(
        experience_range, EXPERIENCE_BENCHMARKS["0-3 years"]
    )


def get_dimension_target(experience_range: str, dimension: str) -> float:
    benchmark = get_benchmark(experience_range)
    return benchmark["dimension_targets"].get(dimension, 3.0)


def get_readiness_level(overall_score: float, experience_range: str) -> str:
    benchmark = get_benchmark(experience_range)
    thresholds = benchmark["readiness_threshold"]

    if overall_score >= thresholds["exceeds_expectations"]:
        return "Exceeds Expectations"
    elif overall_score >= thresholds["interview_ready"]:
        return "Interview Ready"
    elif overall_score >= thresholds["needs_improvement"]:
        return "Needs Improvement"
    else:
        return "Not Ready"


def get_dimension_status(score: float, target: float) -> str:
    tolerance = 0.3
    if score >= target + tolerance:
        return "Exceeds Bar"
    elif score >= target - tolerance:
        return "At Bar"
    else:
        return "Below Bar"
