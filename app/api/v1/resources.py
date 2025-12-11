from fastapi import APIRouter, Depends, HTTPException, status, Query
from google.cloud import firestore
from typing import Optional, List

from app.core.database import get_db
from app.models.resource import (
    CreateResourceRequest,
    UpdateResourceRequest,
    ResourceResponse,
    ResourceListResponse,
    ResourceType,
)
from app.services.resource_service import ResourceService

router = APIRouter()


@router.post(
    "",
    response_model=ResourceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new resource",
)
async def create_resource(
    request: CreateResourceRequest,
    db: firestore.Client = Depends(get_db),
):
    """
    Create a new learning resource.

    The resource will be stored in Firestore and marked as not embedded.
    The ingestion service will later generate embeddings and add to ChromaDB.
    """
    service = ResourceService(db)
    return await service.create_resource(request)


@router.get(
    "",
    response_model=ResourceListResponse,
    summary="List resources",
)
async def list_resources(
    type: Optional[ResourceType] = Query(None, description="Filter by resource type"),
    tags: Optional[str] = Query(
        None, description="Comma-separated list of tags to filter by"
    ),
    is_embedded: Optional[bool] = Query(None, description="Filter by embedding status"),
    limit: int = Query(
        100, ge=1, le=500, description="Maximum number of resources to return"
    ),
    db: firestore.Client = Depends(get_db),
):
    """
    List resources with optional filters.

    - **type**: Filter by resource type (blog, video, article, course, documentation, tutorial)
    - **tags**: Comma-separated list of tags (resources must have ALL specified tags)
    - **is_embedded**: Filter by whether resource is embedded in ChromaDB
    - **limit**: Maximum number of resources to return (default: 100, max: 500)
    """
    service = ResourceService(db)

    # Parse tags from comma-separated string
    tag_list = None
    if tags:
        tag_list = [t.strip().lower() for t in tags.split(",") if t.strip()]

    return await service.list_resources(
        resource_type=type,
        tags=tag_list,
        is_embedded=is_embedded,
        limit=limit,
    )


@router.get(
    "/{resource_id}",
    response_model=ResourceResponse,
    summary="Get a resource by ID",
)
async def get_resource(
    resource_id: str,
    db: firestore.Client = Depends(get_db),
):
    """Get a single resource by its ID."""
    service = ResourceService(db)
    resource = await service.get_resource(resource_id)

    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resource with ID '{resource_id}' not found",
        )

    return resource


@router.patch(
    "/{resource_id}",
    response_model=ResourceResponse,
    summary="Update a resource",
)
async def update_resource(
    resource_id: str,
    request: UpdateResourceRequest,
    db: firestore.Client = Depends(get_db),
):
    """
    Update a resource (partial update).

    Only provided fields will be updated. If url, title, or summary are changed,
    the is_embedded flag will be reset to False so the ingestion service
    will re-embed the resource.
    """
    service = ResourceService(db)
    resource = await service.update_resource(resource_id, request)

    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resource with ID '{resource_id}' not found",
        )

    return resource


@router.delete(
    "/{resource_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a resource",
)
async def delete_resource(
    resource_id: str,
    db: firestore.Client = Depends(get_db),
):
    """
    Delete a resource.

    Note: This will also need to be removed from ChromaDB.
    The ingestion service handles this during its next sync.
    """
    service = ResourceService(db)
    deleted = await service.delete_resource(resource_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resource with ID '{resource_id}' not found",
        )

    return None
