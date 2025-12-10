"""
Embedding generation using sentence-transformers with multiprocessing support
"""
from typing import List
from sentence_transformers import SentenceTransformer
from backend.app.config import settings
import logging
import torch

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Generate embeddings for text using sentence-transformers with optimizations"""

    def __init__(self, model_name: str = None):
        """
        Initialize the embedding generator with performance optimizations

        Args:
            model_name: Name of the sentence-transformer model to use
        """
        self.model_name = model_name or settings.EMBEDDING_MODEL
        logger.info(f"Loading embedding model: {self.model_name}")

        # Determine device
        if torch.cuda.is_available():
            device = "cuda"
            logger.info("Using GPU for embeddings")
        else:
            device = "cpu"
            logger.info("Using CPU for embeddings")

        # Load model with device specification
        self.model = SentenceTransformer(
            self.model_name,
            trust_remote_code=True,
            device=device
        )

        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        logger.info(f"Embedding dimension: {self.embedding_dim}")

    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text

        Args:
            text: Input text

        Returns:
            List of floats representing the embedding
        """
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def embed_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Generate embeddings for a batch of texts with optimizations

        Args:
            texts: List of input texts
            batch_size: Batch size for processing (reduced to 32 to prevent memory overload)

        Returns:
            List of embeddings
        """
        # Conservative batch size to prevent memory crashes
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            convert_to_numpy=True,
            show_progress_bar=len(texts) > 100,
            normalize_embeddings=False,
            convert_to_tensor=False
        )
        return embeddings.tolist()

    def get_embedding_dimension(self) -> int:
        """Get the dimension of the embeddings"""
        return self.embedding_dim


# Global embedding generator instance
_embedding_generator = None


def get_embedding_generator() -> EmbeddingGenerator:
    """Get or create the global embedding generator instance"""
    global _embedding_generator
    if _embedding_generator is None:
        _embedding_generator = EmbeddingGenerator()
    return _embedding_generator
