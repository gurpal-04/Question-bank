"""
User Dashboard Data Models

Defines all data structures for user dashboard views.
Aggregates data across multiple interview sessions.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime


# ============================================================================
# HERO SECTION: USER OVERVIEW
# ============================================================================

class UserOverview(BaseModel):
    """High-level user statistics for hero section."""
    
    user_id: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    member_since: datetime
    
    total_interviews_completed: int = Field(
        ge=0,
        description="Total number of completed interviews"
    )
    average_readiness_score: Optional[float] = Field(
        None,
        ge=0,
        le=100,
        description="Average overall score across all interviews"
    )
    improvement_trend: Optional[float] = Field(
        None,
        description="Score change in last 30 days (positive = improvement)"
    )
    total_practice_time: Optional[str] = Field(
        None,
        description="Total time spent in interviews (e.g., '4h 23m')"
    )
    current_readiness_level: Optional[Literal[
        "Not Ready",
        "Needs Improvement", 
        "Interview Ready",
        "Exceeds Expectations"
    ]] = None


# ============================================================================
# INTERVIEW HISTORY
# ============================================================================

class InterviewHistoryItem(BaseModel):
    """Single interview in history list."""
    
    session_id: str
    role: str
    experience_range: str
    difficulty: str
    
    overall_score: Optional[float] = Field(None, ge=0, le=100)
    readiness_level: Optional[str] = None
    
    total_questions: int = Field(ge=0)
    total_time: Optional[str] = None
    
    created_at: datetime
    status: str  # "completed", "in_progress", "pending"


class InterviewHistory(BaseModel):
    """List of recent interviews."""
    
    interviews: List[InterviewHistoryItem] = Field(default_factory=list)
    total_count: int = Field(ge=0, description="Total interviews (for pagination)")


# ============================================================================
# SKILLS MASTERY OVERVIEW
# ============================================================================

class SkillMasteryItem(BaseModel):
    """Aggregated skill performance across interviews."""
    
    skill_id: str
    skill_label: str
    
    average_score: float = Field(ge=1.0, le=5.0)
    times_practiced: int = Field(ge=0)
    
    category: Literal["strong", "developing", "needs_work"]
    trend: Optional[Literal["improving", "stable", "declining"]] = None


class SkillsMastery(BaseModel):
    """Grouped skills by mastery level."""
    
    strong_skills: List[SkillMasteryItem] = Field(default_factory=list)
    developing_skills: List[SkillMasteryItem] = Field(default_factory=list)
    needs_work_skills: List[SkillMasteryItem] = Field(default_factory=list)


# ============================================================================
# DIMENSION TRENDS
# ============================================================================

class DimensionTrendPoint(BaseModel):
    """Single data point in dimension trend."""
    
    date: datetime
    score: float = Field(ge=1.0, le=5.0)
    session_id: str


class DimensionTrend(BaseModel):
    """Trend data for a single dimension."""
    
    dimension_name: Literal["structure", "depth", "tradeoffs", "clarity"]
    data_points: List[DimensionTrendPoint] = Field(default_factory=list)
    
    current_score: Optional[float] = Field(None, ge=1.0, le=5.0)
    target_score: Optional[float] = Field(None, ge=1.0, le=5.0)
    trend: Optional[Literal["improving", "stable", "declining"]] = None


class DimensionTrends(BaseModel):
    """All dimension trends over time."""
    
    structure: DimensionTrend
    depth: DimensionTrend
    tradeoffs: DimensionTrend
    clarity: DimensionTrend


# ============================================================================
# CONCEPT MASTERY TRACKER
# ============================================================================

class ConceptFrequency(BaseModel):
    """Frequency tracking for a concept."""
    
    concept: str
    times_covered: int = Field(ge=0)
    times_missed: int = Field(ge=0)
    times_incorrect: int = Field(ge=0)
    total_appearances: int = Field(ge=0)
    
    coverage_rate: float = Field(
        ge=0.0,
        le=1.0,
        description="Ratio of times covered to total appearances"
    )


class ConceptMasteryTracker(BaseModel):
    """Aggregated concept mastery across all interviews."""
    
    mastered_concepts: List[ConceptFrequency] = Field(
        default_factory=list,
        description="Concepts covered consistently (coverage_rate >= 0.8)"
    )
    partial_concepts: List[ConceptFrequency] = Field(
        default_factory=list,
        description="Concepts sometimes covered (0.3 <= coverage_rate < 0.8)"
    )
    missing_concepts: List[ConceptFrequency] = Field(
        default_factory=list,
        description="Concepts frequently missed (coverage_rate < 0.3)"
    )


# ============================================================================
# READINESS SCORE PROGRESS
# ============================================================================

class ReadinessProgressPoint(BaseModel):
    """Single data point in readiness progress."""
    
    date: datetime
    score: float = Field(ge=0, le=100)
    readiness_level: str
    session_id: str


class ReadinessProgress(BaseModel):
    """Readiness score progression over time."""
    
    current_score: Optional[float] = Field(None, ge=0, le=100)
    target_score: Optional[float] = Field(None, ge=0, le=100)
    gap: Optional[float] = None
    
    progress_points: List[ReadinessProgressPoint] = Field(default_factory=list)
    
    trend: Optional[Literal["improving", "stable", "declining"]] = None
    trend_value: Optional[float] = Field(
        None,
        description="Points gained/lost over time"
    )


# ============================================================================
# RECOMMENDED ACTIONS
# ============================================================================

class ActionItem(BaseModel):
    """Single recommended action."""
    
    priority: Literal["high", "medium", "low"]
    category: Literal["practice", "study", "improve"]
    title: str
    description: str
    reason: Optional[str] = None


class RecommendedActions(BaseModel):
    """Personalized action plan."""
    
    top_priorities: List[ActionItem] = Field(default_factory=list)
    study_recommendations: List[str] = Field(default_factory=list)
    next_interview_suggestion: Optional[Dict[str, Any]] = None


# ============================================================================
# STATISTICS & ACHIEVEMENTS
# ============================================================================

class Milestone(BaseModel):
    """Achievement milestone."""
    
    id: str
    title: str
    description: str
    achieved: bool
    achieved_at: Optional[datetime] = None
    progress: Optional[int] = Field(None, description="Progress towards milestone (if not achieved)")
    target: Optional[int] = Field(None, description="Target value for milestone")


class UserStatistics(BaseModel):
    """Detailed user statistics."""
    
    total_questions_answered: int = Field(ge=0)
    average_questions_per_interview: Optional[float] = None
    
    most_practiced_role: Optional[str] = None
    most_practiced_role_count: Optional[int] = None
    
    favorite_difficulty: Optional[str] = None
    favorite_difficulty_count: Optional[int] = None
    
    best_score: Optional[float] = Field(None, ge=0, le=100)
    best_score_date: Optional[datetime] = None
    
    longest_streak: Optional[int] = Field(None, description="Most interviews in 7 days")
    current_streak: Optional[int] = Field(None, description="Interviews in last 7 days")


class Achievements(BaseModel):
    """User achievements and stats."""
    
    milestones: List[Milestone] = Field(default_factory=list)
    statistics: UserStatistics
    badges: List[str] = Field(
        default_factory=list,
        description="Badge IDs earned by user"
    )


# ============================================================================
# ASSESSMENTS OVERVIEW
# ============================================================================

class AssessmentSummaryItem(BaseModel):
    """Summary of a single assessment."""
    
    assessment_id: str
    topic: str
    level: str
    score: Optional[float] = Field(None, ge=0)
    max_score: Optional[float] = Field(None, ge=0)
    percentage: Optional[float] = Field(None, ge=0, le=100)
    questions_count: int = Field(ge=0)
    correct_count: Optional[int] = Field(None, ge=0)
    incorrect_count: Optional[int] = Field(None, ge=0)
    weak_topics: List[str] = Field(default_factory=list)
    created_at: datetime
    has_result: bool = Field(description="Whether assessment has been completed")


class AssessmentsByTopic(BaseModel):
    """Assessments grouped by topic."""
    
    topic: str
    total_assessments: int = Field(ge=0)
    completed_assessments: int = Field(ge=0)
    average_score: Optional[float] = Field(None, ge=0, le=100)
    best_score: Optional[float] = Field(None, ge=0, le=100)
    assessments: List[AssessmentSummaryItem] = Field(default_factory=list)


class AssessmentsOverview(BaseModel):
    """Complete assessments overview."""
    
    total_assessments: int = Field(ge=0)
    completed_assessments: int = Field(ge=0)
    pending_assessments: int = Field(ge=0)
    
    overall_average_score: Optional[float] = Field(None, ge=0, le=100)
    
    recent_assessments: List[AssessmentSummaryItem] = Field(
        default_factory=list,
        description="Last 10 assessments"
    )
    
    by_topic: List[AssessmentsByTopic] = Field(
        default_factory=list,
        description="Assessments grouped by topic"
    )
    
    common_weak_topics: List[str] = Field(
        default_factory=list,
        description="Most common weak topics across all assessments"
    )


# ============================================================================
# COMPLETE DASHBOARD
# ============================================================================

class UserDashboard(BaseModel):
    """
    Complete user dashboard data.
    Aggregates all views into a single response.
    """
    
    overview: UserOverview
    interview_history: InterviewHistory
    skills_mastery: SkillsMastery
    dimension_trends: DimensionTrends
    concept_mastery: ConceptMasteryTracker
    readiness_progress: ReadinessProgress
    recommended_actions: RecommendedActions
    # achievements: Achievements  # Removed for performance
    assessments: AssessmentsOverview
    
    computed_at: datetime = Field(default_factory=datetime.utcnow)
    dashboard_version: str = Field(
        default="1.0",
        description="Version of dashboard computation logic"
    )
