from fastapi import APIRouter, Depends, HTTPException, status, Query
from google.cloud import firestore

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.feature_request import (
    CreateFeatureRequestRequest,
    VoteRequest,
    FeatureRequestResponse,
    FeatureRequestListResponse,
)
from app.services.feature_request_service import FeatureRequestService

router = APIRouter()


@router.post(
    "",
    response_model=FeatureRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a feature request",
)
async def create_feature_request(
    request: CreateFeatureRequestRequest,
    current_user: User = Depends(get_current_user),
    db: firestore.Client = Depends(get_db),
):
    service = FeatureRequestService(db)
    return await service.create_feature_request(request, current_user)


@router.get(
    "",
    response_model=FeatureRequestListResponse,
    summary="List feature requests",
)
async def list_feature_requests(
    sort: str = Query(
        "new", description="Sort order: 'new' (default) or 'top'"
    ),
    limit: int = Query(100, ge=1, le=500, description="Maximum number to return"),
    db: firestore.Client = Depends(get_db),
):
    service = FeatureRequestService(db)
    return await service.list_feature_requests(sort=sort, limit=limit)


@router.get(
    "/{feature_request_id}",
    response_model=FeatureRequestResponse,
    summary="Get a feature request by ID",
)
async def get_feature_request(
    feature_request_id: str,
    db: firestore.Client = Depends(get_db),
):
    service = FeatureRequestService(db)
    feature_request = await service.get_feature_request(feature_request_id)

    if not feature_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature request with ID '{feature_request_id}' not found",
        )

    return feature_request


@router.post(
    "/{feature_request_id}/vote",
    response_model=FeatureRequestResponse,
    summary="Upvote or downvote a feature request",
)
async def vote_feature_request(
    feature_request_id: str,
    request: VoteRequest,
    current_user: User = Depends(get_current_user),
    db: firestore.Client = Depends(get_db),
):
    service = FeatureRequestService(db)
    updated = await service.vote_feature_request(
        feature_request_id, current_user, request.vote
    )

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature request with ID '{feature_request_id}' not found",
        )

    return updated
