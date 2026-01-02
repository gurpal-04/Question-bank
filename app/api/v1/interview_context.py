from app.services.ai_agents.Interview.interview_context_agent.agent import generate_interview_context
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Literal

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
    status_code=status.HTTP_200_OK,
    summary="Generate interview context",
    description="Generate a stable interview context based on role, experience, and difficulty. "
                "This context will be used by all downstream agents in the interview process.",
)
async def generate_context(
    request: GenerateInterviewContextRequest,
) -> InterviewContextResponse:
   
    try:
        result = await generate_interview_context(
            role=request.role,
            experience_range=request.experience_range,
            difficulty=request.difficulty,
        )
        return InterviewContextResponse(**result)
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

