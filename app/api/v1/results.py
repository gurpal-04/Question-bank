from fastapi import APIRouter, Depends, HTTPException, status
from google.cloud import firestore
from typing import Optional

from app.core.database import get_db
from app.models.assessment import ResultResponse, ResultsListResponse
from app.models.user import User
from app.core.security import get_optional_user
from app.services.result_service import ResultService

router = APIRouter()


@router.get("/{result_id}", response_model=ResultResponse)
async def get_result(result_id: str, db: firestore.Client = Depends(get_db)):
    """
    Get a specific assessment result by its ID.
    """
    service = ResultService(db)
    return await service.get_result(result_id)


@router.get(
    "/",
    response_model=ResultsListResponse,
    status_code=status.HTTP_200_OK,
)
async def get_user_results(
    user_id: Optional[str] = None,
    db: firestore.Client = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Get all assessment results for the current user.
    """
    # Determine user_id: use authenticated user if available, otherwise use query param
    target_user_id = current_user.id if current_user else user_id

    if not target_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id is required",
        )

    service = ResultService(db)
    return await service.get_user_results(target_user_id)
