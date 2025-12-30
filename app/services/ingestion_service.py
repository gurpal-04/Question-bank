from google.cloud import firestore
from typing import List, Dict, Any, Optional
import logging
import asyncio

from app.services.resource_service import ResourceService
from app.services.vector_store import VectorStore, get_vector_store
from app.models.resource import ResourceResponse
from app.services.embedding_service import get_embedding_service

logger = logging.getLogger(__name__)

# LLM model for summary generation
SUMMARY_MODEL = "gemini-2.0-flash"


# Guardrail constants
SIMILARITY_THRESHOLD = 0.65
ALIAS_MAP = {
    "js": "javascript",
    "py": "python",
    "cpp": "c++",
}


class IngestionService:
    """
    Service for ingesting resources into the vector database.

    Workflow:
    1. Read unembedded resources from Firestore
    2. Generate summary using Gemini LLM (if not already present)
    3. Create embedding using local BGE model
    4. Insert into ChromaDB
    5. Mark as embedded in Firestore
    """

    def __init__(self, db: firestore.Client):
        self.db = db
        self.resource_service = ResourceService(db)
        self.vector_store = get_vector_store()
        self.embedding_service = get_embedding_service()

    def _tokenize_topic(self, topic: str) -> List[str]:
        """
        Tokenize the normalized topic string.
        Example: "java multithreading" -> ["java", "multithreading"]
        """
        if not topic:
            return []
        return [t.strip().lower() for t in topic.split() if t.strip()]

    def _normalize_tags(self, tags: List[str]) -> List[str]:
        """
        Normalize resource tags (lowercase, trimmed).
        """
        if not tags:
            return []
        return [t.strip().lower() for t in tags if t.strip()]

    def _has_topic_overlap(
        self, topic_tokens: List[str], resource_tags: List[str]
    ) -> bool:
        """
        Check if at least one topic token (or its alias) exists in the resource's tags.
        """
        normalized_tags = set(self._normalize_tags(resource_tags))

        for token in topic_tokens:
            # Check direct match
            if token in normalized_tags:
                return True

            # Check alias match
            if token in ALIAS_MAP and ALIAS_MAP[token] in normalized_tags:
                return True

        return False

    async def generate_embedding(
        self, text: str, is_query: bool = False
    ) -> List[float]:
        """
        Generate embedding for text using local BGE model.

        Args:
            text: Text to embed
            is_query: True if embedding a search query

        Returns:
            Embedding vector as list of floats
        """
        try:
            # Run CPU-bound embedding generation in a thread to avoid blocking event loop
            embedding = await asyncio.to_thread(
                self.embedding_service.generate_embedding, text, is_query
            )
            logger.debug(f"Generated embedding with dimension {len(embedding)}")
            return embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise

    async def ingest_resource(self, resource: ResourceResponse) -> bool:
        """
        Ingest a single resource into the vector database.

        Args:
            resource: The resource to ingest

        Returns:
            True if successful, False otherwise
        """
        try:
            # Step 1: Use existing summary (created at resource creation time)
            summary = resource.summary

            # Fallback for legacy resources without a stored summary
            if not summary:
                logger.warning(
                    f"Resource {resource.id} has no stored summary; using fallback from title and tags."
                )
                summary = (
                    f"{resource.title}. Topics covered: {', '.join(resource.tags)}."
                    if resource.tags
                    else resource.title
                )

            # Step 2: Create text for embedding (combine title, summary, and tags)
            embedding_text = (
                f"{resource.title}. {summary}. Topics: {', '.join(resource.tags)}"
            )

            # Step 3: Generate embedding (is_query=False for documents)
            embedding = await self.generate_embedding(embedding_text, is_query=False)

            # Step 4: Add to vector store
            metadata = {
                "title": resource.title,
                "type": (
                    resource.type.value
                    if hasattr(resource.type, "value")
                    else resource.type
                ),
                "url": resource.url,
                "summary": summary,
                "tags": resource.tags,
            }
            self.vector_store.add_resource(resource.id, embedding, metadata)

            # Step 5: Mark as embedded in Firestore
            await self.resource_service.mark_as_embedded(resource.id)

            logger.info(f"Successfully ingested resource: {resource.id}")
            return True

        except Exception as e:
            logger.error(f"Error ingesting resource {resource.id}: {e}", exc_info=True)
            return False

    async def ingest_unembedded_resources(self, limit: int = 50) -> Dict[str, Any]:
        """
        Ingest all unembedded resources from Firestore.

        Args:
            limit: Maximum number of resources to process

        Returns:
            Summary of ingestion results
        """
        # Get unembedded resources
        resources = await self.resource_service.get_unembedded_resources(limit=limit)

        if not resources:
            logger.info("No unembedded resources found")
            return {
                "processed": 0,
                "success": 0,
                "failed": 0,
                "message": "No unembedded resources to process",
            }

        logger.info(f"Found {len(resources)} unembedded resources to process")

        success_count = 0
        failed_count = 0
        failed_ids = []

        for resource in resources:
            success = await self.ingest_resource(resource)
            if success:
                success_count += 1
            else:
                failed_count += 1
                failed_ids.append(resource.id)

        result = {
            "processed": len(resources),
            "success": success_count,
            "failed": failed_count,
            "failed_ids": failed_ids if failed_ids else None,
            "message": f"Processed {len(resources)} resources: {success_count} succeeded, {failed_count} failed",
        }

        logger.info(result["message"])
        return result

    async def search_resources(
        self, query: str, n_results: int = 5, filter_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for resources similar to the query with guardrails.

        Guardrails:
        1. Similarity Threshold: Discard results below SIMILARITY_THRESHOLD.
        2. Topic/Tag Overlap: Ensure at least one query token matches resource tags.

        Args:
            query: Search query text
            n_results: Number of results to return
            filter_type: Optional filter by resource type

        Returns:
            List of matching resources with similarity scores
        """
        # Generate embedding for query (is_query=True)
        query_embedding = await self.generate_embedding(query, is_query=True)

        # Search vector store (fetch more results initially to allow for filtering)
        # We fetch 2x requested results to increase chance of finding valid ones after filtering
        initial_results = self.vector_store.search(
            query_embedding=query_embedding,
            n_results=n_results * 2,
            filter_type=filter_type,
        )

        if not initial_results:
            return []

        # Tokenize query for overlap check
        topic_tokens = self._tokenize_topic(query)

        filtered_results = []

        for res in initial_results:
            # Guardrail 1: Similarity Threshold
            similarity = res.get("similarity", 0)
            if similarity < SIMILARITY_THRESHOLD:
                logger.debug(
                    f"Resource {res.get('id')} filtered out: similarity {similarity:.3f} < {SIMILARITY_THRESHOLD}"
                )
                continue

            # Guardrail 2: Topic/Tag Overlap Check
            metadata = res.get("metadata", {})
            tags = metadata.get("tags", [])

            if not self._has_topic_overlap(topic_tokens, tags):
                logger.debug(
                    f"Resource {res.get('id')} filtered out: no topic overlap. Query: {topic_tokens}, Tags: {tags}"
                )
                continue

            filtered_results.append(res)

        # Return top n_results from filtered list
        return filtered_results[:n_results]

    def get_stats(self) -> Dict[str, Any]:
        """Get ingestion statistics"""
        vector_stats = self.vector_store.get_collection_stats()
        return {
            "vector_store": vector_stats,
            "embedding_model": "BAAI/bge-base-en-v1.5",
            "summary_model": SUMMARY_MODEL,
        }
