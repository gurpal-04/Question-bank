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


# Static routes MUST come before dynamic routes like /{resource_id}


@router.post(
    "/ingest",
    summary="Ingest unembedded resources into vector database",
)
async def ingest_resources(
    limit: int = Query(50, ge=1, le=100, description="Maximum resources to process"),
    db: firestore.Client = Depends(get_db),
):
    """
    Trigger ingestion of unembedded resources.

    This will:
    1. Fetch resources where is_embedded=False
    2. Generate summaries using Gemini LLM
    3. Create embeddings using Gemini embedding model
    4. Store in ChromaDB vector database
    5. Mark resources as embedded in Firestore
    """
    from app.services.ingestion_service import IngestionService

    service = IngestionService(db)
    return await service.ingest_unembedded_resources(limit=limit)


@router.get(
    "/search/semantic",
    summary="Semantic search for resources",
)
async def search_resources(
    q: str = Query(..., description="Search query"),
    n: int = Query(5, ge=1, le=20, description="Number of results"),
    type: Optional[ResourceType] = Query(None, description="Filter by resource type"),
    db: firestore.Client = Depends(get_db),
):
    """
    Search for resources using semantic similarity.

    Uses Gemini embeddings to find resources most relevant to the query.
    Returns resources ranked by similarity score.
    """
    from app.services.ingestion_service import IngestionService

    service = IngestionService(db)
    results = await service.search_resources(
        query=q, n_results=n, filter_type=type.value if type else None
    )

    return {"query": q, "results": results, "total": len(results)}


@router.get(
    "/stats",
    summary="Get vector store statistics",
)
async def get_stats(
    db: firestore.Client = Depends(get_db),
):
    """Get statistics about the vector store and ingestion service."""
    from app.services.ingestion_service import IngestionService

    service = IngestionService(db)
    return service.get_stats()


@router.delete(
    "/{resource_id}/embedding",
    summary="Remove resource from vector database only",
)
async def remove_embedding(
    resource_id: str,
    db: firestore.Client = Depends(get_db),
):
    """
    Remove a resource from ChromaDB and mark as unembedded in Firestore.

    This keeps the resource in Firestore but removes its embedding from ChromaDB.
    Useful for re-indexing resources - run /ingest after to re-embed.
    """
    from app.services.vector_store import get_vector_store

    service = ResourceService(db)

    # Check if resource exists
    resource = await service.get_resource(resource_id)
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resource with ID '{resource_id}' not found",
        )

    # Delete from vector store
    vector_store = get_vector_store()
    vector_store.delete_resource(resource_id)

    # Mark as unembedded in Firestore
    doc_ref = db.collection("resources").document(resource_id)
    doc_ref.update({"is_embedded": False})

    return {
        "message": f"Resource '{resource_id}' removed from vector store and marked as unembedded",
        "resource_id": resource_id,
    }


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
    Delete a resource from both Firestore and ChromaDB vector store.
    """
    from app.services.vector_store import get_vector_store

    service = ResourceService(db)
    deleted = await service.delete_resource(resource_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resource with ID '{resource_id}' not found",
        )

    # Also delete from vector store
    vector_store = get_vector_store()
    vector_store.delete_resource(resource_id)

    return None
