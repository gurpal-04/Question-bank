import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
import logging
import os

logger = logging.getLogger(__name__)

# Default persistent storage path
DEFAULT_PERSIST_DIRECTORY = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "chroma_data",
)

# Collection name for resources
RESOURCES_COLLECTION = "resources"


class VectorStore:
    """
    ChromaDB wrapper for resource embeddings.
    Provides persistent storage and similarity search capabilities.
    """

    def __init__(self, persist_directory: Optional[str] = None):
        """
        Initialize ChromaDB client with persistent storage.

        Args:
            persist_directory: Path to store ChromaDB data. Defaults to ./chroma_data
        """
        self.persist_directory = persist_directory or DEFAULT_PERSIST_DIRECTORY

        # Ensure directory exists
        os.makedirs(self.persist_directory, exist_ok=True)

        # Initialize ChromaDB with persistent storage
        self.client = chromadb.PersistentClient(path=self.persist_directory)

        # Get or create the resources collection
        self.collection = self.client.get_or_create_collection(
            name=RESOURCES_COLLECTION,
            metadata={"description": "Learning resources for topic recommendations"},
        )

        logger.info(f"VectorStore initialized with {self.collection.count()} resources")

    def add_resource(
        self, resource_id: str, embedding: List[float], metadata: Dict[str, Any]
    ) -> None:
        """
        Add a resource embedding to the collection.

        Args:
            resource_id: Unique identifier (Firestore document ID)
            embedding: Vector embedding of the resource
            metadata: Resource metadata (title, type, tags, url, summary)
        """
        # ChromaDB requires metadata values to be str, int, float, or bool
        # Convert tags list to comma-separated string
        processed_metadata = {
            "title": metadata.get("title", ""),
            "type": metadata.get("type", ""),
            "url": metadata.get("url", ""),
            "summary": metadata.get("summary", "") or "",
            "tags": ",".join(metadata.get("tags", [])) if metadata.get("tags") else "",
        }

        # Use upsert to handle both insert and update
        self.collection.upsert(
            ids=[resource_id], embeddings=[embedding], metadatas=[processed_metadata]
        )

        logger.info(f"Added/updated resource in vector store: {resource_id}")

    def search(
        self,
        query_embedding: List[float],
        n_results: int = 5,
        filter_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar resources using query embedding.

        Args:
            query_embedding: Vector embedding of the query
            n_results: Maximum number of results to return
            filter_type: Optional filter by resource type

        Returns:
            List of matching resources with metadata and distances
        """
        where_filter = None
        if filter_type:
            where_filter = {"type": filter_type}

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_filter,
            include=["metadatas", "distances"],
        )

        # Format results
        resources = []
        if results and results["ids"] and results["ids"][0]:
            for i, resource_id in enumerate(results["ids"][0]):
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                distance = results["distances"][0][i] if results["distances"] else 0

                # Convert tags back to list
                tags = metadata.get("tags", "")
                if isinstance(tags, str) and tags:
                    metadata["tags"] = [t.strip() for t in tags.split(",")]
                else:
                    metadata["tags"] = []

                resources.append(
                    {
                        "id": resource_id,
                        "metadata": metadata,
                        "distance": distance,
                        # Convert L2 distance to Cosine Similarity
                        # L2^2 = 2(1 - cos_sim) -> cos_sim = 1 - (L2^2 / 2)
                        "similarity": 1 - ((distance**2) / 2),
                    }
                )

        logger.info(f"Search returned {len(resources)} results")
        return resources

    def delete_resource(self, resource_id: str) -> bool:
        """
        Remove a resource from the collection.

        Args:
            resource_id: ID of the resource to remove

        Returns:
            True if deletion was attempted (ChromaDB doesn't confirm if ID existed)
        """
        try:
            self.collection.delete(ids=[resource_id])
            logger.info(f"Deleted resource from vector store: {resource_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting resource {resource_id}: {e}")
            return False

    def get_resource(self, resource_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific resource by ID.

        Args:
            resource_id: ID of the resource to retrieve

        Returns:
            Resource metadata or None if not found
        """
        results = self.collection.get(
            ids=[resource_id], include=["metadatas", "embeddings"]
        )

        if results and results["ids"]:
            metadata = results["metadatas"][0] if results["metadatas"] else {}

            # Convert tags back to list
            tags = metadata.get("tags", "")
            if isinstance(tags, str) and tags:
                metadata["tags"] = [t.strip() for t in tags.split(",")]
            else:
                metadata["tags"] = []

            return {
                "id": resource_id,
                "metadata": metadata,
                "embedding": (
                    results["embeddings"][0]
                    if results["embeddings"] is not None
                    and len(results["embeddings"]) > 0
                    else None
                ),
            }

        return None

    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the collection.

        Returns:
            Dictionary with collection name and count
        """
        return {
            "collection_name": RESOURCES_COLLECTION,
            "total_resources": self.collection.count(),
            "persist_directory": self.persist_directory,
        }

    def clear_collection(self) -> None:
        """
        Clear all resources from the collection.
        Use with caution - this deletes all data!
        """
        # Delete and recreate the collection
        self.client.delete_collection(RESOURCES_COLLECTION)
        self.collection = self.client.get_or_create_collection(
            name=RESOURCES_COLLECTION,
            metadata={"description": "Learning resources for topic recommendations"},
        )
        logger.warning("Cleared all resources from vector store")


# Singleton instance for easy access
_vector_store_instance: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """
    Get or create the global VectorStore instance.
    """
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = VectorStore()
    return _vector_store_instance
