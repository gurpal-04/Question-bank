from google.cloud import firestore
from typing import List, Optional
from datetime import datetime
import logging

from app.models.resource import (
    ResourceDocument,
    CreateResourceRequest,
    UpdateResourceRequest,
    ResourceResponse,
    ResourceListResponse,
    ResourceType,
)

logger = logging.getLogger(__name__)

# Firestore collection name
RESOURCES_COLLECTION = "resources"


class ResourceService:
    """Service for managing learning resources in Firestore"""

    def __init__(self, db: firestore.Client):
        self.db = db
        self.collection = db.collection(RESOURCES_COLLECTION)

    def _doc_to_response(self, doc_id: str, data: dict) -> ResourceResponse:
        """Convert Firestore document to ResourceResponse"""
        created_at = data.get("created_at", datetime.utcnow())
        updated_at = data.get("updated_at", datetime.utcnow())

        # Handle Firestore Timestamp conversion
        if hasattr(created_at, "to_datetime"):
            created_at = created_at.to_datetime()
        if hasattr(updated_at, "to_datetime"):
            updated_at = updated_at.to_datetime()

        return ResourceResponse(
            id=doc_id,
            url=data.get("url", ""),
            title=data.get("title", ""),
            type=data.get("type", ResourceType.ARTICLE),
            tags=data.get("tags", []),
            summary=data.get("summary"),
            is_embedded=data.get("is_embedded", False),
            created_at=created_at,
            updated_at=updated_at,
        )

    async def create_resource(self, request: CreateResourceRequest) -> ResourceResponse:
        """Create a new resource in Firestore"""
        now = datetime.utcnow()

        resource_data = {
            "url": request.url,
            "title": request.title,
            "type": request.type.value,
            "tags": request.tags,
            "summary": request.summary,
            "is_embedded": False,
            "created_at": now,
            "updated_at": now,
        }

        # Add to Firestore
        _, doc_ref = self.collection.add(resource_data)
        logger.info(f"Created resource with ID: {doc_ref.id}")

        return self._doc_to_response(doc_ref.id, resource_data)

    async def get_resource(self, resource_id: str) -> Optional[ResourceResponse]:
        """Get a single resource by ID"""
        doc_ref = self.collection.document(resource_id)
        doc = doc_ref.get()

        if not doc.exists:
            return None

        return self._doc_to_response(doc.id, doc.to_dict())

    async def list_resources(
        self,
        resource_type: Optional[ResourceType] = None,
        tags: Optional[List[str]] = None,
        is_embedded: Optional[bool] = None,
        limit: int = 100,
    ) -> ResourceListResponse:
        """
        List resources with optional filters.

        Args:
            resource_type: Filter by resource type
            tags: Filter by tags (resources must have ALL specified tags)
            is_embedded: Filter by embedding status
            limit: Maximum number of resources to return
        """
        query = self.collection

        # Apply filters
        if resource_type is not None:
            query = query.where(
                field_path="type", op_string="==", value=resource_type.value
            )

        if is_embedded is not None:
            query = query.where(
                field_path="is_embedded", op_string="==", value=is_embedded
            )

        # Note: Firestore doesn't support array-contains-all for multiple tags
        # We'll filter for one tag and then filter the rest in memory
        if tags and len(tags) > 0:
            query = query.where(
                field_path="tags", op_string="array_contains", value=tags[0]
            )

        # Apply limit
        query = query.limit(limit)

        # Execute query
        docs = query.stream()
        resources = []

        for doc in docs:
            data = doc.to_dict()

            # Additional tag filtering in memory if multiple tags specified
            if tags and len(tags) > 1:
                doc_tags = set(data.get("tags", []))
                if not all(tag in doc_tags for tag in tags):
                    continue

            resources.append(self._doc_to_response(doc.id, data))

        return ResourceListResponse(resources=resources, total=len(resources))

    async def update_resource(
        self, resource_id: str, request: UpdateResourceRequest
    ) -> Optional[ResourceResponse]:
        """Update a resource (partial update)"""
        doc_ref = self.collection.document(resource_id)
        doc = doc_ref.get()

        if not doc.exists:
            return None

        # Build update dict with only provided fields
        update_data = {"updated_at": datetime.utcnow()}

        if request.url is not None:
            update_data["url"] = request.url
        if request.title is not None:
            update_data["title"] = request.title
        if request.type is not None:
            update_data["type"] = request.type.value
        if request.tags is not None:
            update_data["tags"] = request.tags
        if request.summary is not None:
            update_data["summary"] = request.summary

        # If content changed (url, title, or summary), reset is_embedded flag
        if any(key in update_data for key in ["url", "title", "summary"]):
            update_data["is_embedded"] = False

        doc_ref.update(update_data)
        logger.info(f"Updated resource: {resource_id}")

        # Fetch and return updated document
        updated_doc = doc_ref.get()
        return self._doc_to_response(updated_doc.id, updated_doc.to_dict())

    async def delete_resource(self, resource_id: str) -> bool:
        """Delete a resource"""
        doc_ref = self.collection.document(resource_id)
        doc = doc_ref.get()

        if not doc.exists:
            return False

        doc_ref.delete()
        logger.info(f"Deleted resource: {resource_id}")
        return True

    async def get_unembedded_resources(self, limit: int = 50) -> List[ResourceResponse]:
        """
        Get resources that haven't been embedded in ChromaDB yet.
        Used by the ingestion service.
        """
        query = self.collection.where(
            field_path="is_embedded", op_string="==", value=False
        ).limit(limit)

        docs = query.stream()
        resources = [self._doc_to_response(doc.id, doc.to_dict()) for doc in docs]

        return resources

    async def mark_as_embedded(self, resource_id: str) -> bool:
        """Mark a resource as embedded in ChromaDB"""
        doc_ref = self.collection.document(resource_id)
        doc = doc_ref.get()

        if not doc.exists:
            return False

        doc_ref.update(
            {
                "is_embedded": True,
                "updated_at": datetime.utcnow(),
            }
        )
        logger.info(f"Marked resource as embedded: {resource_id}")
        return True
