from fastapi import APIRouter, Depends, HTTPException, status, Query
from google.cloud import firestore

from app.core.database import get_db
from app.core.security import get_current_user, get_optional_user
from app.models.user import User
from app.models.feature_request import (
    CreateFeatureRequestRequest,
    VoteRequest,
    FeatureRequestResponse,
    FeatureRequestListResponse,
    CreateFeatureRequestCommentRequest,
    FeatureRequestCommentResponse,
    FeatureRequestCommentListResponse,
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
    current_user: User = Depends(get_optional_user),
    db: firestore.Client = Depends(get_db),
):
    service = FeatureRequestService(db)
    if current_user:
        return await service.list_feature_requests_with_user_vote(
            user=current_user, sort=sort, limit=limit
        )
    return await service.list_feature_requests(sort=sort, limit=limit)


@router.get(
    "/{feature_request_id}",
    response_model=FeatureRequestResponse,
    summary="Get a feature request by ID",
)
async def get_feature_request(
    feature_request_id: str,
    current_user: User = Depends(get_optional_user),
    db: firestore.Client = Depends(get_db),
):
    service = FeatureRequestService(db)
    if current_user:
        feature_request = await service.get_feature_request_with_user_vote(
            feature_request_id, current_user
        )
    else:
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


@router.post(
    "/{feature_request_id}/comments",
    response_model=FeatureRequestCommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a comment to a feature request",
)
async def add_comment(
    feature_request_id: str,
    request: CreateFeatureRequestCommentRequest,
    current_user: User = Depends(get_current_user),
    db: firestore.Client = Depends(get_db),
):
    service = FeatureRequestService(db)
    comment = await service.add_comment(feature_request_id, request, current_user)

    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature request with ID '{feature_request_id}' not found",
        )

    return comment


@router.get(
    "/{feature_request_id}/comments",
    response_model=FeatureRequestCommentListResponse,
    summary="List comments for a feature request",
)
async def list_comments(
    feature_request_id: str,
    limit: int = Query(100, ge=1, le=500, description="Maximum number to return"),
    db: firestore.Client = Depends(get_db),
):
    service = FeatureRequestService(db)
    comments = await service.list_comments(feature_request_id, limit=limit)

    if not comments:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature request with ID '{feature_request_id}' not found",
        )

    return comments
