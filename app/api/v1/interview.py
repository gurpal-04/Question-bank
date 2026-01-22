import asyncio
from fastapi import APIRouter, HTTPException, status, Depends
from google.cloud import firestore
from typing import Optional
from app.core.database import get_db
from app.core.security import get_optional_user, User
from app.models.interview import (
    GeneratePrimaryQuestionRequest,
    GeneratePrimaryQuestionResponse,
    InterviewSession,
    InterviewSessionListResponse,
    InterviewListItem,
    InterviewListResponse,
    GapAnalysisRequest,
    SubmitAnswerRequest,
    GenerateFollowupQuestionRequest,
    # New orchestrator API models
    StartInterviewRequest,
    StartInterviewResponse,
    AnswerRequest,
    AnswerResponse,
)
from app.models.gap_analysis import GapAnalysisOutput
from app.services.interview_service import InterviewService

router = APIRouter()


# =============================================================================
# NEW ORCHESTRATOR API ENDPOINTS
# =============================================================================


@router.post(
    "/start",
    response_model=StartInterviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Start Interview",
    description="Generate the first question for an existing interview session. "
                "The session should be created via /v1/interview-context/generate first. "
                "The backend controls all flow decisions.",
)
async def start_interview(
    request: StartInterviewRequest,
    db: firestore.Client = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Start an interview by generating the first question.

    - Loads existing session from DB (created via /v1/interview-context/generate)
    - Selects the first skill (highest importance, interview-safe)
    - Generates the first primary question
    - Updates session with first question and sets status to "in_progress"
    - Returns the interview ID, first question, and current state
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    service = InterviewService(db)
    try:
        response = await service.start_interview(
            session_id=request.session_id,
            user_id=current_user.id,
        )
        return response
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error starting interview: {e}",
        )


@router.post(
    "/answer",
    response_model=AnswerResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit Answer",
    description="Submit an answer to the current question. "
                "The backend automatically decides what happens next.",
)
async def submit_answer_orchestrated(
    request: AnswerRequest,
    db: firestore.Client = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Submit an answer and get the orchestrated next action.

    Flow:
    1. Evaluates the answer using gap analysis
    2. Updates interview state
    3. Determines next action (follow-up, new skill, or end)
    4. Generates the next question if applicable
    5. Returns decision, reason, next question, and updated state

    The frontend NEVER chooses which agent to call - the backend decides.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    service = InterviewService(db)
    try:
        response = await service.process_answer(
            interview_id=request.interview_id,
            answer_text=request.answer_text,
        )
        return response
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing answer: {e}",
        )


# =============================================================================
# LEGACY ENDPOINTS (DEPRECATED)
# =============================================================================


@router.post(
    "/generate-primary-question",
    response_model=InterviewSession,
    status_code=status.HTTP_201_CREATED,
    summary="[DEPRECATED] Generate & Store Primary Interview Question",
    deprecated=True,
)
async def generate_primary_question(
    request: GeneratePrimaryQuestionRequest,
    db: firestore.Client = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    DEPRECATED: Use POST /interview/start instead.

    Generate the primary interview question, persist it as an InterviewSession for the user, return the saved session object.
    """
    # User must be authenticated (no guest user support for now)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )
    user_id = current_user.id
    service = InterviewService(db)
    try:
        session = await service.generate_and_store_primary_question(
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
    response_model=InterviewListResponse,
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
    Returns simplified session data: id, role, experience, difficulty, status, created.
    
    Works with both authenticated users (JWT or Firebase tokens) and guest users (Firebase anonymous tokens).
    """
    target_user_id = current_user.id if current_user else user_id
    if not target_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id is required. Provide either a valid authentication token or user_id query parameter."
        )
    service = InterviewService(db)
    sessions = await asyncio.to_thread(service.get_sessions_by_user, target_user_id)
    
    # Map full sessions to simplified list items
    session_items = [
        InterviewListItem(
            id=session.id or "",
            role=session.role,
            experience_range=session.experience_range,
            difficulty=session.difficulty,
            status=session.status or "pending",
            created_at=session.created_at,
        )
        for session in sessions
    ]
    
    return InterviewListResponse(sessions=session_items)


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


@router.post(
    "/{session_id}/submit",
    response_model=GapAnalysisOutput,
    status_code=status.HTTP_200_OK,
    summary="[DEPRECATED] Submit Answer & Get Analysis",
    deprecated=True,
)
async def submit_answer(
    session_id: str,
    request: SubmitAnswerRequest,
    db: firestore.Client = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    DEPRECATED: Use POST /interview/answer instead.

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


@router.post(
    "/{session_id}/generate-followup",
    response_model=InterviewSession,
    status_code=status.HTTP_200_OK,
    summary="[DEPRECATED] Generate Followup Question",
    deprecated=True,
)
async def generate_followup_question(
    session_id: str,
    db: firestore.Client = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    DEPRECATED: Use POST /interview/answer instead.

    Generate a followup question based on the last answer and gap analysis.
    The followup question is appended to the session's questions array.
    """
    service = InterviewService(db)
    try:
        session = await service.generate_and_store_followup_question(
            session_id=session_id
        )
        return session
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error generating followup question: {e}"
        )
