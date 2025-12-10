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

        # Enable FP16 for faster computation (2x speedup with minimal accuracy loss)
        if device == "cuda":
            self.model.half()  # Use FP16 on GPU
            logger.info("Enabled FP16 precision for faster GPU inference")

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

    def embed_batch(self, texts: List[str], batch_size: int = 64) -> List[List[float]]:
        """
        Generate embeddings for a batch of texts with optimizations

        Args:
            texts: List of input texts
            batch_size: Batch size for processing (balanced at 64 for performance vs memory)

        Returns:
            List of embeddings
        """
        # Balanced batch size: reduces overhead while maintaining memory safety
        # With 3 workers: 64 batch_size = ~6GB RAM usage (46% of 13GB total)

        # Determine optimal number of workers for data loading
        # Use 4 workers to parallelize tokenization/preprocessing
        num_workers = 4 if len(texts) > 100 else 0

        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            convert_to_numpy=True,
            show_progress_bar=len(texts) > 100,
            normalize_embeddings=False,
            convert_to_tensor=False,
            num_workers=num_workers  # Parallel data loading/tokenization
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
