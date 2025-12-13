from fastapi import APIRouter, Depends, HTTPException, status
from google.cloud import firestore
from typing import Optional

from app.core.database import get_db
from app.core.security import get_optional_user
from app.models.user import User
from app.models.assessment import (
    GenerateAssessmentRequest,
    GenerateAssessmentResponse,
    SubmitAssessmentRequest,
    SubmitAssessmentResponse,
    AssessmentListResponse,
)
from app.services.assessment_service import AssessmentService

router = APIRouter()


@router.post(
    "/generate",
    response_model=GenerateAssessmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_assessment(
    request: GenerateAssessmentRequest,
    db: firestore.Client = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Generate a new assessment with questions based on topic and level.
    """
    # Determine user_id: use authenticated user if available, otherwise use from request
    user_id = current_user.id if current_user else request.user_id
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id is required for guest users",
        )

    service = AssessmentService(db)
    return await service.generate_assessment(request, user_id)


@router.post(
    "/submit",
    response_model=SubmitAssessmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_assessment(
    request: SubmitAssessmentRequest,
    db: firestore.Client = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Submit answers for an assessment and get results with feedback.
    """
    # Determine user_id: use authenticated user if available, otherwise use from request
    user_id = current_user.id if current_user else request.user_id
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id is required for guest users",
        )

    service = AssessmentService(db)
    return await service.submit_assessment(request, user_id)


@router.get(
    "/",
    response_model=AssessmentListResponse,
    status_code=status.HTTP_200_OK,
)
async def get_user_assessments(
    user_id: Optional[str] = None,
    db: firestore.Client = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Get all assessments created by the current user.
    """
    # Determine user_id: use authenticated user if available, otherwise use query param
    target_user_id = current_user.id if current_user else user_id

    if not target_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id is required",
        )

    service = AssessmentService(db)
    return await service.get_user_assessments(target_user_id)


@router.get(
    "/{assessment_id}",
    response_model=GenerateAssessmentResponse,
    status_code=status.HTTP_200_OK,
)
async def get_assessment(
    assessment_id: str,
    db: firestore.Client = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
    user_id: Optional[
        str
    ] = None,  # For guest users who might pass user_id as query param
):
    """
    Get a specific assessment by ID.
    """
    # Determine user_id: use authenticated user if available, otherwise use query param
    target_user_id = current_user.id if current_user else user_id

    if not target_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id is required",
        )

    service = AssessmentService(db)
    return await service.get_assessment(assessment_id, target_user_id)


@router.post(
    "/test-normalizer",
    summary="Test Topic Normalizer Agent",
)
async def test_normalizer(
    topics: list[str],
    db: firestore.Client = Depends(get_db),
):
    """
    Test the Topic Normalizer Agent directly.
    Takes a list of raw topics and returns normalized versions.
    """
    from app.services.assessment_service import AssessmentService
    from app.services.ai_agents.topic_normalizer.agent import (
        topic_normalizer_runner,
        topic_normalizer_agent,
    )

    service = AssessmentService(db)
    prompt = f"Normalize these topics: {topics}"

    try:
        response = await service.run_agent(
            topic_normalizer_runner,
            topic_normalizer_agent,
            prompt,
        )
        return {"input": topics, "response": response}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error running normalizer agent: {str(e)}",
        )
