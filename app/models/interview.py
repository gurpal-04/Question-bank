from pydantic import BaseModel, Field
from typing import List, Literal, Optional, Dict, Any
from datetime import datetime

# === Request/Response Models for Interview First Question ===

class GenerateFirstQuestionRequest(BaseModel):
    role: str = Field(..., description="The job role being interviewed for (e.g., 'Frontend Engineer', 'Backend Engineer')", min_length=1)
    experience_range: str = Field(..., description="The candidate's experience level (e.g., '0-3 years', '3-5 years', '5+ years')", min_length=1)
    difficulty: Literal["Easy", "Medium", "Hard"] = Field(..., description="The difficulty level of the interview")
    interview_context: Optional[Dict[str, Any]] = Field(
        None, description="Optional pre-generated interview context. If not provided, will be generated automatically.")
    seed: Optional[str] = Field(None, description="Optional seed for deterministic randomness in skill/archetype selection")

class SelectedSkillResponse(BaseModel):
    id: str
    label: str
    level: str
    description: str

class SelectedArchetypeResponse(BaseModel):
    id: str
    label: str
    description: str

class FirstQuestionResponse(BaseModel):
    question: str
    archetype: str
    skill_id: str

class GenerateFirstQuestionResponse(BaseModel):
    interview_context: Dict[str, Any] = Field(..., description="The interview context used for question generation")
    selected_skill: SelectedSkillResponse = Field(..., description="The skill that was selected for the first question")
    selected_archetype: SelectedArchetypeResponse = Field(..., description="The question archetype that was selected")
    first_question: FirstQuestionResponse = Field(..., description="The generated first interview question")

# === Interview Session Model (DB Persistence) ===
class InterviewSession(BaseModel):
    id: Optional[str] = None  # Firestore doc id
    user_id: str
    role: str
    experience_range: str
    difficulty: str
    interview_context: Dict[str, Any]
    selected_skill: Dict[str, Any]
    selected_archetype: Dict[str, Any]
    first_question: Dict[str, Any]
    created_at: datetime

class InterviewSessionListResponse(BaseModel):
    sessions: List[InterviewSession]
