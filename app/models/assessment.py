from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.models.questions import QuestionResponse


class Assessment(BaseModel):
    """Assessment model for Firestore"""

    id: Optional[str] = None  # Firestore document ID
    user_id: str  # User ID (can be guest_xyz or authenticated user ID)
    topic: str
    level: str  # Beginner, Intermediate, Advanced
    questions: List[Dict[str, Any]]  # List of question dictionaries
    result_id: Optional[str] = None  # ID of the result if assessment is completed
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class AssessmentResult(BaseModel):
    """Assessment result model for Firestore"""

    id: Optional[str] = None  # Firestore document ID
    user_id: str  # User ID (can be guest_xyz or authenticated user ID)
    assessment_id: str  # Reference to assessment document ID
    user_answers: Dict[str, str]  # Dictionary mapping question ID to user's answer
    score: float
    max_score: float
    correct_questions: List[str]  # List of question IDs that were correct
    incorrect_questions: List[str]  # List of question IDs that were incorrect
    feedback: Optional[str] = None  # AI-generated feedback
    weak_topics: List[str] = []
    resources: List[Dict[str, str]] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class GenerateAssessmentRequest(BaseModel):
    topic: str = Field(
        ..., description="Topic for the assessment (e.g., React, Python)"
    )
    level: str = Field(
        ..., description="Difficulty level: Beginner, Intermediate, or Advanced"
    )
    user_id: Optional[str] = Field(
        None, description="User ID (optional for guest users)"
    )


class GenerateAssessmentResponse(BaseModel):
    assessment_id: str
    topic: str
    level: str
    questions: List["QuestionResponse"]
    created_at: datetime


class SubmitAssessmentRequest(BaseModel):
    assessment_id: str = Field(..., description="ID of the assessment")
    user_answers: Dict[str, str] = Field(
        ..., description="Dictionary mapping question ID to user's answer"
    )
    user_id: Optional[str] = Field(
        None, description="User ID (optional for guest users)"
    )


class SubmitAssessmentResponse(BaseModel):
    score: float
    max_score: float
    feedback: str
    weak_topics: List[str]
    resources: List[Dict[str, str]]
    correct_questions: List[str]
    incorrect_questions: List[str]
    result_id: str


class ResultResponse(BaseModel):
    id: str
    assessment_id: str
    score: float
    max_score: float
    feedback: Optional[str]
    weak_topics: List[str] = []
    resources: List[Dict[str, str]] = []
    correct_questions: List[str]
    incorrect_questions: List[str]
    created_at: datetime


class ResultsListResponse(BaseModel):
    results: List[ResultResponse]


class AssessmentSummary(BaseModel):
    id: str
    topic: str
    level: str
    created_at: datetime
    questions_count: int
    result_id: Optional[str] = None


class AssessmentListResponse(BaseModel):
    assessments: List[AssessmentSummary]
