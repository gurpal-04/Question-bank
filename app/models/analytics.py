"""
Analytics Data Models

Defines all data structures for post-interview analytics.
Supports the 8 analytics views requested by PM.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime


# ============================================================================
# DIMENSION SCORES (View 2: Dimension Breakdown)
# ============================================================================

class DimensionScore(BaseModel):
    """Score for a single dimension with benchmark comparison."""
    
    score: float = Field(
        ge=1.0,
        le=5.0,
        description="Actual score achieved (1-5)"
    )
    target: float = Field(
        ge=1.0,
        le=5.0,
        description="Target score for experience level (1-5)"
    )
    status: Literal["Below Bar", "At Bar", "Exceeds Bar"] = Field(
        description="Performance relative to target"
    )
    feedback_snippet: str = Field(
        description="1-2 sentence explanation of the score"
    )


class DimensionScores(BaseModel):
    """All dimension scores with benchmarks."""
    
    structure: DimensionScore
    depth: DimensionScore
    tradeoffs: DimensionScore
    clarity: DimensionScore


# ============================================================================
# CONCEPT MASTERY (View 3: Concept Mastery Analysis)
# ============================================================================

class ConceptDetail(BaseModel):
    """Concept with explanation."""
    
    concept: str
    explanation: Optional[str] = None


class ConceptMastery(BaseModel):
    """Aggregated concept coverage across all questions."""
    
    covered_well: List[str] = Field(
        default_factory=list,
        description="Concepts clearly and correctly explained"
    )
    partially_covered: List[ConceptDetail] = Field(
        default_factory=list,
        description="Concepts mentioned but not fully explained"
    )
    missing: List[str] = Field(
        default_factory=list,
        description="Expected concepts not mentioned at all"
    )
    incorrect: List[ConceptDetail] = Field(
        default_factory=list,
        description="Concepts explained incorrectly with explanation"
    )


# ============================================================================
# SKILL PERFORMANCE (View 4: Skill-by-Skill Breakdown)
# ============================================================================

class QuestionPerformance(BaseModel):
    """Performance on a single question."""
    
    question_id: str
    question_text: str
    question_type: Literal["primary", "follow_up"]
    overall_score: float = Field(
        ge=1.0,
        le=5.0,
        description="Average of dimension scores (1-5)"
    )
    key_gaps: List[str] = Field(
        default_factory=list,
        description="Top 2-3 missing concepts for this question"
    )


class SkillPerformance(BaseModel):
    """Performance on a specific skill."""
    
    skill_id: str
    skill_label: str
    questions_asked: int
    avg_score: float = Field(
        ge=1.0,
        le=5.0,
        description="Average score across all questions for this skill (1-5)"
    )
    questions: List[QuestionPerformance]


# ============================================================================
# PATTERNS (View 5: Confidence & Clarity Patterns)
# ============================================================================

class Distribution(BaseModel):
    """Distribution of confidence or clarity levels."""
    
    high: int = Field(ge=0, description="Count of 'high' answers")
    medium: int = Field(ge=0, description="Count of 'medium' answers")
    low: int = Field(ge=0, description="Count of 'low' answers")


# ============================================================================
# FOLLOW-UP ANALYSIS (View 6: Follow-Up Intent Analysis)
# ============================================================================

class FollowUpAnalysis(BaseModel):
    """Analysis of follow-up patterns."""
    
    total_followups: int = Field(ge=0)
    followup_ratio: float = Field(
        ge=0.0,
        description="Follow-ups per question (e.g., 0.5 = 2 follow-ups in 4 questions)"
    )
    intent_distribution: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of each follow-up intent type"
    )
    benchmark_ratio: float = Field(
        ge=0.0,
        description="Expected follow-up ratio for experience level"
    )


# ============================================================================
# MAIN ANALYTICS MODEL (All Views Combined)
# ============================================================================

class InterviewAnalytics(BaseModel):
    """
    Complete analytics for a single interview session.
    Supports all 8 analytics views requested by PM.
    """
    
    session_id: str
    
    # ========================================================================
    # VIEW 1: OVERALL INTERVIEW PERFORMANCE
    # ========================================================================
    
    overall_score: float = Field(
        ge=0,
        le=100,
        description="Overall readiness score (0-100)"
    )
    readiness_level: Literal[
        "Not Ready",
        "Needs Improvement",
        "Interview Ready",
        "Exceeds Expectations"
    ]
    benchmark_score: float = Field(
        ge=0,
        le=100,
        description="Target score for experience level"
    )
    total_questions_answered: int = Field(ge=0)
    average_response_time: Optional[str] = Field(
        None,
        description="Average time per answer (e.g., '3m 42s')"
    )
    skills_covered: List[str] = Field(
        default_factory=list,
        description="List of skill labels covered in interview"
    )
    
    # ========================================================================
    # VIEW 2: DIMENSION BREAKDOWN
    # ========================================================================
    
    dimension_scores: DimensionScores
    
    # ========================================================================
    # VIEW 3: CONCEPT MASTERY ANALYSIS
    # ========================================================================
    
    concept_mastery: ConceptMastery
    
    # ========================================================================
    # VIEW 4: SKILL-BY-SKILL BREAKDOWN
    # ========================================================================
    
    skill_performance: List[SkillPerformance] = Field(default_factory=list)
    weakest_skill: Optional[SkillPerformance] = None
    
    # ========================================================================
    # VIEW 5: CONFIDENCE & CLARITY PATTERNS
    # ========================================================================
    
    confidence_distribution: Distribution
    clarity_distribution: Distribution
    confusion_signals: List[str] = Field(
        default_factory=list,
        description="All confusion signals detected across questions"
    )
    pattern_insight: Optional[str] = Field(
        None,
        description="AI-generated or rule-based pattern observation"
    )
    
    # ========================================================================
    # VIEW 6: FOLLOW-UP INTENT ANALYSIS
    # ========================================================================
    
    followup_analysis: FollowUpAnalysis
    
    # ========================================================================
    # VIEW 7: RECOMMENDED NEXT STEPS
    # ========================================================================
    
    recommended_actions: List[str] = Field(
        default_factory=list,
        description="Prioritized action items for improvement"
    )
    
    # ========================================================================
    # METADATA
    # ========================================================================
    
    computed_at: datetime = Field(default_factory=datetime.utcnow)
    analytics_version: str = Field(
        default="1.0",
        description="Version of analytics computation logic"
    )
    
    # Note: View 8 (Historical Comparison) will be a separate endpoint
    # that queries multiple InterviewAnalytics documents
