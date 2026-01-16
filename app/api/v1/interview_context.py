from app.services.ai_agents.Interview.interview_context_agent.agent import generate_interview_context
from app.core.database import get_db
from app.core.security import get_optional_user, User
from fastapi import APIRouter, HTTPException, status, Depends
from google.cloud import firestore
from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from datetime import datetime

router = APIRouter()

class GenerateInterviewContextRequest(BaseModel):
    """
    Request model for generating interview context.
    """
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
        ...,
        description="The difficulty level of the interview",
    )


class InterviewContextResponse(BaseModel):
    """
    Response model for interview context generation.
    """
    session_id: str = Field(
        ...,
        description="The interview session ID created in the database",
    )
    role_expectations: str = Field(
        ...,
        description="A clear description of what the interviewer expects from a candidate at this level",
    )
    expected_concepts: List[str] = Field(
        ...,
        description="A list of 6-10 core technical concepts that a strong answer would touch",
    )


@router.post(
    "/generate",
    response_model=InterviewContextResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate interview context and create session",
    description="Generate a stable interview context based on role, experience, and difficulty. "
                "Creates a new interview session in the database with the context. "
                "This context will be used by all downstream agents in the interview process.",
)
async def generate_context(
    request: GenerateInterviewContextRequest,
    db: firestore.Client = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
) -> InterviewContextResponse:
    """
    Generate interview context and create a session entry in the database.
    
    - Generates the interview context
    - Creates a new interview session in DB with context (no questions yet)
    - Returns session_id along with the context
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    
    try:
        # 1. Generate interview context
        context_result = await generate_interview_context(
            role=request.role,
            experience_range=request.experience_range,
            difficulty=request.difficulty,
        )
        
        # 2. Create session entry in DB with context
        session_data = {
            "user_id": current_user.id,
            "role": request.role,
            "experience_range": request.experience_range,
            "difficulty": request.difficulty,
            "interview_context": context_result,
            "questions": [],  # No questions yet
            "status": "pending",  # Will be updated to "in_progress" when first question is generated
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        
        doc_ref = db.collection("interview_sessions").document()
        doc_ref.set(session_data)
        session_id = doc_ref.id
        
        # 3. Return session_id along with context
        return InterviewContextResponse(
            session_id=session_id,
            role_expectations=context_result["role_expectations"],
            expected_concepts=context_result["expected_concepts"],
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating interview context: {str(e)}",
        )

