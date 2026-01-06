import asyncio
from fastapi import APIRouter, HTTPException, status, Depends
from google.cloud import firestore
from typing import Optional
from app.core.database import get_db
from app.core.security import get_optional_user, User
from app.models.interview import (
    GenerateFirstQuestionRequest,
    GenerateFirstQuestionResponse,
    InterviewSession,
    InterviewSessionListResponse,
    GapAnalysisRequest,
)
from pydantic import BaseModel, Field
from app.models.gap_analysis import GapAnalysisOutput
from app.services.interview_service import InterviewService

router = APIRouter()


@router.post(
    "/generate-first-question",
    response_model=InterviewSession,
    status_code=status.HTTP_201_CREATED,
    summary="Generate & Store First Interview Question",
)
async def generate_first_question(
    request: GenerateFirstQuestionRequest,
    db: firestore.Client = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Generate the first interview question, persist it as an InterviewSession for the user, return the saved session object.
    """
    # User must be authenticated (no guest user support for now)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )
    user_id = current_user.id
    service = InterviewService(db)
    try:
        session = await service.generate_and_store_first_question(
            user_id=user_id,
            role=request.role,
            experience_range=request.experience_range,
            difficulty=request.difficulty,
            interview_context=request.interview_context,
            seed=request.seed,
        )
        return session
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error generating or saving session: {e}"
        )


@router.get(
    "/",
    response_model=InterviewSessionListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get All Sessions For User",
)
async def get_interview_sessions(
    user_id: Optional[str] = None,
    db: firestore.Client = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Get all InterviewSessions for a user (from auth or query param).
    """
    target_user_id = current_user.id if current_user else user_id
    if not target_user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    service = InterviewService(db)
    sessions = await asyncio.to_thread(service.get_sessions_by_user, target_user_id)
    return InterviewSessionListResponse(sessions=sessions)


@router.get(
    "/{session_id}",
    response_model=InterviewSession,
    status_code=status.HTTP_200_OK,
    summary="Get Session By ID",
)
async def get_interview_session_by_id(
    session_id: str,
    db: firestore.Client = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Fetch InterviewSession by document ID.
    """
    service = InterviewService(db)
    session = await asyncio.to_thread(service.get_session_by_id, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Interview session not found"
        )
    return session


@router.post(
    "/gap-analysis",
    response_model=GapAnalysisOutput,
    status_code=status.HTTP_200_OK,
    summary="Analyze Answer Gaps",
)
async def analyze_answer_gaps(
    request: GapAnalysisRequest,
    db: firestore.Client = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Analyze a candidate's answer to identify missing concepts and provide follow-up intent.
    """
    service = InterviewService(db)
    try:
        result = await service.perform_gap_analysis(
            question=request.question,
            answer=request.answer,
            expected_concepts=request.expected_concepts,
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error performing gap analysis: {e}"
        )


class SubmitAnswerRequest(BaseModel):
    question_id: str = Field(..., description="The ID of the question to answer")
    answer: str = Field(..., description="The candidate's answer")


@router.post(
    "/{session_id}/submit",
    response_model=GapAnalysisOutput,
    status_code=status.HTTP_200_OK,
    summary="Submit Answer & Get Analysis",
)
async def submit_answer(
    session_id: str,
    request: SubmitAnswerRequest,
    db: firestore.Client = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Submit answer for a specific question in a session.
    Runs gap analysis and saves the result.
    """
    service = InterviewService(db)
    try:
        result = await service.submit_answer(
            session_id=session_id,
            question_id=request.question_id,
            answer=request.answer,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error submitting answer: {e}")
