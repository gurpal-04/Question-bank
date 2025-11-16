from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


class Assessment(BaseModel):
    """Assessment model for Firestore"""
    id: Optional[str] = None  # Firestore document ID
    topic: str
    level: str  # Beginner, Intermediate, Advanced
    questions: List[Dict[str, Any]]  # List of question dictionaries
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AssessmentResult(BaseModel):
    """Assessment result model for Firestore"""
    id: Optional[str] = None  # Firestore document ID
    assessment_id: str  # Reference to assessment document ID
    user_answers: Dict[int, str]  # Dictionary mapping question index to user's answer
    score: float
    max_score: float
    correct_questions: List[int]  # List of question indices that were correct
    incorrect_questions: List[int]  # List of question indices that were incorrect
    feedback: Optional[str] = None  # AI-generated feedback
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
