"""
Stored Dashboard Models

Models for pre-computed dashboard data stored in Firestore.
Optimized for fast reads.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

from app.models.user_dashboard import (
    UserOverview,
    InterviewHistory,
    SkillsMastery,
    DimensionTrends,
    ConceptMasteryTracker,
    ReadinessProgress,
    RecommendedActions,
    AssessmentsOverview,
)


class StoredDashboard(BaseModel):
    """
    Pre-computed dashboard stored in Firestore.
    Stored in 'user_dashboards' collection with user_id as document ID.
    """
    
    user_id: str = Field(description="User ID (document ID)")
    
    # All dashboard sections
    overview: UserOverview
    interview_history: InterviewHistory
    skills_mastery: SkillsMastery
    dimension_trends: DimensionTrends
    concept_mastery: ConceptMasteryTracker
    readiness_progress: ReadinessProgress
    recommended_actions: RecommendedActions
    assessments: AssessmentsOverview
    
    # Metadata
    computed_at: datetime = Field(default_factory=datetime.utcnow)
    dashboard_version: str = Field(default="1.0")
    
    # Tracking
    last_interview_id: Optional[str] = Field(
        None,
        description="ID of last interview included in computation"
    )
    last_assessment_id: Optional[str] = Field(
        None,
        description="ID of last assessment included in computation"
    )
    interviews_count: int = Field(
        ge=0,
        description="Number of interviews included"
    )
    assessments_count: int = Field(
        ge=0,
        description="Number of assessments included"
    )
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class DashboardUpdateTrigger(BaseModel):
    """
    Trigger for dashboard update.
    Used to queue dashboard updates after interview/assessment completion.
    """
    
    user_id: str
    trigger_type: str = Field(
        description="Type of trigger: 'interview_completed' or 'assessment_completed'"
    )
    trigger_id: str = Field(
        description="ID of interview or assessment that triggered update"
    )
    triggered_at: datetime = Field(default_factory=datetime.utcnow)
    processed: bool = Field(default=False)
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
