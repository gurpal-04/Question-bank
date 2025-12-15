from sentence_transformers import SentenceTransformer
from typing import List
import logging

logger = logging.getLogger(__name__)

# Model configuration
MODEL_NAME = "BAAI/bge-base-en-v1.5"


class EmbeddingService:
    """
    Service for generating text embeddings using local BGE model.
    Singleton pattern to ensure model is loaded only once.
    """

    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EmbeddingService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        # Initialize model only if it hasn't been initialized yet
        if self._model is None:
            logger.info(f"Loading embedding model: {MODEL_NAME}...")
            try:
                # Load model on CPU
                self._model = SentenceTransformer(MODEL_NAME, device="cpu")
                logger.info("Embedding model loaded successfully.")
            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}")
                raise

    def generate_embedding(self, text: str, is_query: bool = False) -> List[float]:
        """
        Generate embedding for the given text.

        Args:
            text: The text to embed.
            is_query: True if embedding a search query, False for documents.

        Returns:
            List of floats representing the embedding vector.
        """
        if not text:
            return []

        # Add appropriate prefix based on usage
        # BGE models require "query: " for queries and "passage: " for documents
        prefix = "query: " if is_query else "passage: "
        text_with_prefix = f"{prefix}{text}"

        try:
            # Generate embedding
            # normalize_embeddings=True is recommended for BGE models for dot product/cosine similarity
            embedding = self._model.encode(
                text_with_prefix, normalize_embeddings=True, convert_to_tensor=False
            )

            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise


# Global instance
_embedding_service = None


def get_embedding_service() -> EmbeddingService:
    """Get or create the global EmbeddingService instance."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
