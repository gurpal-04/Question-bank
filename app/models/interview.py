from pydantic import BaseModel, Field
from typing import List, Literal, Optional, Dict, Any, TYPE_CHECKING
from datetime import datetime
from enum import Enum
import uuid

if TYPE_CHECKING:
    from app.models.gap_analysis import GapAnalysisOutput


# === Orchestrator Decision Enum ===
class OrchestratorDecision(str, Enum):
    """Possible decisions the orchestrator can make after processing an answer."""

    ASK_FOLLOWUP = "ASK_FOLLOWUP"
    ASK_NEW_PRIMARY = "ASK_NEW_PRIMARY"
    END_INTERVIEW = "END_INTERVIEW"


# === Request/Response Models for Interview Primary Question ===


class GeneratePrimaryQuestionRequest(BaseModel):
    role: str = Field(
        ...,
        description="The job role being interviewed for (e.g., 'Frontend Engineer', 'Backend Engineer')",
        min_length=1,
    )
    experience_range: str = Field(
        ...,
        description="The candidate's experience level (e.g., '0-3 years', '3-5 years', '5+ years')",
        min_length=1,
    )
    difficulty: Literal["Easy", "Medium", "Hard"] = Field(
        ..., description="The difficulty level of the interview"
    )
    interview_context: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional pre-generated interview context. If not provided, will be generated automatically.",
    )
    seed: Optional[str] = Field(
        None,
        description="Optional seed for deterministic randomness in skill/archetype selection",
    )


class GapAnalysisRequest(BaseModel):
    question: str = Field(..., description="The interview question asked")
    answer: str = Field(..., description="The candidate's answer")
    expected_concepts: List[str] = Field(
        ..., description="List of concepts expected in the answer"
    )


class SubmitAnswerRequest(BaseModel):
    question_id: str = Field(..., description="The ID of the question to answer")
    answer: str = Field(..., description="The candidate's answer")


class GenerateFollowupQuestionRequest(BaseModel):
    session_id: str = Field(..., description="The interview session ID")


class SelectedSkillResponse(BaseModel):
    id: str
    label: str
    level: str
    description: str


class SelectedArchetypeResponse(BaseModel):
    id: str
    label: str
    description: str


class PrimaryQuestionResponse(BaseModel):
    question: str
    archetype: str
    skill_id: str


class GeneratePrimaryQuestionResponse(BaseModel):
    interview_context: Dict[str, Any] = Field(
        ..., description="The interview context used for question generation"
    )
    selected_skill: SelectedSkillResponse = Field(
        ..., description="The skill that was selected for the primary question"
    )
    selected_archetype: SelectedArchetypeResponse = Field(
        ..., description="The question archetype that was selected"
    )
    primary_question: PrimaryQuestionResponse = Field(
        ..., description="The generated primary interview question"
    )


# === Interview Session Model (DB Persistence) ===
class CalibrationData(BaseModel):
    selected_skill: Dict[str, Any]
    selected_archetype: Dict[str, Any]


class InterviewQuestion(BaseModel):
    question_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sequence: int
    question_type: Literal["primary", "follow_up"]
    skill_id: Optional[str] = Field(
        None, description="Skill ID this question belongs to (set on primary questions)"
    )
    archetype: Optional[str] = None
    intent: Optional[str] = None
    question: str
    evaluation_contract: Optional[Dict[str, Any]] = Field(
        None, description="Question-specific evaluation criteria"
    )
    answer: Optional[str] = None
    answered_at: Optional[datetime] = None
    gap_analysis: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class InterviewSession(BaseModel):
    id: Optional[str] = None  # Firestore doc id
    user_id: str
    role: str
    experience_range: str
    difficulty: str
    interview_context: Dict[str, Any]
    calibration: Optional[CalibrationData] = None
    questions: List[InterviewQuestion] = []
    interview_summary: Optional[Dict[str, Any]] = None
    status: str = Field(
        default="pending",
        description="Interview status: pending, in_progress, or completed",
    )
    created_at: datetime
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class InterviewSessionListResponse(BaseModel):
    sessions: List[InterviewSession]


class InterviewListItem(BaseModel):
    """Simplified interview session model for list endpoints"""

    id: str = Field(description="Interview session ID")
    role: str = Field(description="Job role")
    experience: str = Field(description="Experience range", alias="experience_range")
    difficulty: str = Field(description="Difficulty level")
    status: str = Field(
        description="Interview status: completed, in_progress, or pending"
    )
    created: datetime = Field(description="Creation timestamp", alias="created_at")

    class Config:
        populate_by_name = True


class InterviewListResponse(BaseModel):
    """Response model for GET /interview endpoint"""

    sessions: List[InterviewListItem]


# === New Orchestrator API Models ===


class InterviewState(BaseModel):
    """
    Read-only computed state derived from session data.
    Used for debugging, frontend display, and orchestrator decisions.
    """

    total_questions_asked: int = Field(
        description="Total number of questions asked so far"
    )
    current_skill_id: Optional[str] = Field(
        None, description="ID of the current skill being probed"
    )
    current_skill_label: Optional[str] = Field(
        None, description="Label of the current skill being probed"
    )
    followups_for_current_skill: int = Field(
        0, description="Number of follow-up questions asked for current skill"
    )
    skills_covered: List[str] = Field(
        default_factory=list,
        description="List of skill IDs already used for primary questions",
    )
    max_questions: int = Field(10, description="Maximum total questions allowed")
    max_followups_per_skill: int = Field(
        2, description="Maximum follow-ups allowed per skill"
    )


class StartInterviewRequest(BaseModel):
    """Request model for POST /interview/start"""

    session_id: str = Field(
        ...,
        description="The interview session ID created from /v1/interview-context/generate",
        min_length=1,
    )


class StartInterviewResponse(BaseModel):
    """Response model for POST /interview/start"""

    interview_id: str = Field(description="The unique interview session ID")
    question: InterviewQuestion = Field(description="The first interview question")
    interview_state: InterviewState = Field(
        description="Current computed state of the interview"
    )


class AnswerRequest(BaseModel):
    """Request model for POST /interview/answer"""

    interview_id: str = Field(..., description="The interview session ID")
    answer_text: str = Field(
        ..., description="The candidate's answer to the current question"
    )


class AnswerResponse(BaseModel):
    """Response model for POST /interview/answer"""

    decision: OrchestratorDecision = Field(
        description="The orchestrator's decision for what happens next"
    )
    reason: str = Field(description="Human-readable explanation for the decision")
    next_question: Optional[InterviewQuestion] = Field(
        None, description="The next question (if decision is not END_INTERVIEW)"
    )
    gap_analysis: Optional[Dict[str, Any]] = Field(
        None, description="Gap analysis result from evaluating the answer"
    )
    interview_state: InterviewState = Field(
        description="Updated computed state of the interview"
    )
    is_complete: bool = Field(False, description="Whether the interview has ended")
