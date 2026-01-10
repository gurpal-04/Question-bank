from pydantic import BaseModel, Field
from typing import List, Literal, Optional, Dict, Any
from typing import List, Literal, Optional, Dict, Any
from datetime import datetime
import uuid

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
    archetype: Optional[str] = None
    intent: Optional[str] = None
    question: str
    answer: Optional[str] = None
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
    created_at: datetime
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class InterviewSessionListResponse(BaseModel):
    sessions: List[InterviewSession]
