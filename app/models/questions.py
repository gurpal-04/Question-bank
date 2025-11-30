from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class Metadata(BaseModel):
    """Metadata for a question"""

    topic: str = Field(..., description="Main topic of the question.")
    subtopic: Optional[str] = Field(None, description="Optional subtopic.")
    type: str = Field("MCQ", description="Type of question, default is MCQ.")


class Question(BaseModel):
    """A single multiple-choice question"""

    id: Optional[str] = Field(None, description="Unique identifier for the question.")
    question: str = Field(..., description="The main question text.")
    options: List[str] = Field(..., description="List of multiple-choice options.")
    correct_answer: str = Field(..., description="The correct answer to the question.")
    explanation: str = Field(
        ..., description="Short explanation or reasoning behind the correct answer."
    )
    difficulty: str = Field(
        ..., description="Difficulty level of the question (easy, medium, hard)."
    )
    metadata: Metadata = Field(..., description="Structured metadata for the question.")


class QuestionsList(BaseModel):
    """List of questions for an assessment"""

    questions: List[Question] = Field(
        ..., description="A list of high-quality generated MCQs."
    )


class QuestionResponse(BaseModel):
    id: str
    question: str
    options: List[str]
    correct_answer: str
    explanation: str
    difficulty: str
    metadata: Dict[str, Any]
