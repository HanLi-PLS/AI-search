"""
Qdrant vector store integration with hybrid search
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams, Distance, PointStruct,
    Filter, FieldCondition, MatchValue, Range,
    SearchRequest, QueryResponse
)
from langchain_core.documents import Document
from backend.app.config import settings
from backend.app.core.embeddings import get_embedding_generator
import logging

logger = logging.getLogger(__name__)


class VectorStore:
    """Qdrant vector store with hybrid search capabilities"""

    def __init__(self):
        """Initialize Qdrant client and create collection if needed"""
        self.client = QdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT
        )
        self.collection_name = settings.QDRANT_COLLECTION_NAME
        self.embedding_generator = get_embedding_generator()
        self.embedding_dim = self.embedding_generator.get_embedding_dimension()

        # Initialize collection
        self._init_collection()

    def _init_collection(self):
        """Create collection if it doesn't exist"""
        try:
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]

            if self.collection_name not in collection_names:
                logger.info(f"Creating collection: {self.collection_name}")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.embedding_dim,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Collection {self.collection_name} created successfully")
            else:
                logger.info(f"Collection {self.collection_name} already exists")

        except Exception as e:
            logger.error(f"Error initializing collection: {str(e)}")
            raise

    def add_documents(self, documents: List[Document], file_id: str, file_name: str,
                     file_size: int, upload_date: datetime) -> int:
        """
        Add documents to the vector store

        Args:
            documents: List of Document objects
            file_id: Unique file identifier
            file_name: Original file name
            file_size: File size in bytes
            upload_date: Upload timestamp

        Returns:
            Number of documents added
        """
        if not documents:
            return 0

        logger.info(f"Adding {len(documents)} documents to vector store")

        # Extract texts for embedding
        texts = [doc.page_content for doc in documents]

        # Generate embeddings
        embeddings = self.embedding_generator.embed_batch(texts)

        # Create points for Qdrant
        points = []
        for idx, (doc, embedding) in enumerate(zip(documents, embeddings)):
            point_id = str(uuid.uuid4())

            # Prepare metadata
            payload = {
                "content": doc.page_content,
                "file_id": file_id,
                "file_name": file_name,
                "file_type": doc.metadata.get("file_type", ""),
                "file_size": file_size,
                "upload_date": upload_date.isoformat(),
                "chunk_index": idx,
                "page": doc.metadata.get("page"),
                "has_images": doc.metadata.get("has_images", False),
                "has_tables": doc.metadata.get("has_tables", False),
            }

            # Add any additional metadata
            for key, value in doc.metadata.items():
                if key not in payload and value is not None:
                    payload[key] = value

            points.append(
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=payload
                )
            )

        # Upload to Qdrant in batches
        batch_size = 100
        for i in range(0, len(points), batch_size):
            batch = points[i:i + batch_size]
            self.client.upsert(
                collection_name=self.collection_name,
                points=batch
            )

        logger.info(f"Successfully added {len(points)} documents to vector store")
        return len(points)

    def search(
        self,
        query: str,
        top_k: int = 5,
        file_types: Optional[List[str]] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Semantic search using vector similarity

        Args:
            query: Search query
            top_k: Number of results to return
            file_types: Filter by file types
            date_from: Filter documents from this date
            date_to: Filter documents to this date

        Returns:
            List of search results
        """
        # Generate query embedding
        query_embedding = self.embedding_generator.embed_text(query)

        # Build filter
        search_filter = self._build_filter(file_types, date_from, date_to)

        # Search
        search_results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=top_k,
            query_filter=search_filter
        )

        # Format results
        results = []
        for hit in search_results:
            results.append({
                "content": hit.payload.get("content", ""),
                "score": hit.score,
                "metadata": {
                    "file_name": hit.payload.get("file_name", ""),
                    "file_type": hit.payload.get("file_type", ""),
                    "upload_date": hit.payload.get("upload_date", ""),
                    "page": hit.payload.get("page"),
                    "has_images": hit.payload.get("has_images", False),
                    "has_tables": hit.payload.get("has_tables", False),
                }
            })

        return results

    def delete_by_file_id(self, file_id: str) -> int:
        """
        Delete all documents associated with a file

        Args:
            file_id: File identifier

        Returns:
            Number of documents deleted
        """
        # Get all points with this file_id
        search_results = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="file_id",
                        match=MatchValue(value=file_id)
                    )
                ]
            )
        )

        points = search_results[0]
        point_ids = [point.id for point in points]

        if point_ids:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=point_ids
            )
            logger.info(f"Deleted {len(point_ids)} documents for file_id: {file_id}")

        return len(point_ids)

    def get_documents_count(self) -> int:
        """Get total number of documents in the collection"""
        try:
            collection_info = self.client.get_collection(self.collection_name)
            return collection_info.points_count
        except Exception as e:
            logger.error(f"Error getting documents count: {str(e)}")
            return 0

    def list_files(self) -> List[Dict[str, Any]]:
        """
        List all unique files in the collection

        Returns:
            List of file information
        """
        # Get all points (may need pagination for large collections)
        all_points, _ = self.client.scroll(
            collection_name=self.collection_name,
            limit=10000  # Adjust based on your needs
        )

        # Group by file_id
        files_dict = {}
        for point in all_points:
            file_id = point.payload.get("file_id")
            if file_id and file_id not in files_dict:
                files_dict[file_id] = {
                    "file_id": file_id,
                    "file_name": point.payload.get("file_name", ""),
                    "file_type": point.payload.get("file_type", ""),
                    "file_size": point.payload.get("file_size", 0),
                    "upload_date": point.payload.get("upload_date", ""),
                    "chunk_count": 0
                }
            if file_id:
                files_dict[file_id]["chunk_count"] += 1

        return list(files_dict.values())

    def _build_filter(
        self,
        file_types: Optional[List[str]] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Optional[Filter]:
        """Build Qdrant filter from search parameters"""
        conditions = []

        if file_types:
            conditions.append(
                FieldCondition(
                    key="file_type",
                    match=MatchValue(any=file_types)
                )
            )

        if date_from or date_to:
            range_params = {}
            if date_from:
                range_params["gte"] = date_from.isoformat()
            if date_to:
                range_params["lte"] = date_to.isoformat()

            conditions.append(
                FieldCondition(
                    key="upload_date",
                    range=Range(**range_params)
                )
            )

        if conditions:
            return Filter(must=conditions)

        return None

    def health_check(self) -> bool:
        """Check if Qdrant is accessible"""
        try:
            self.client.get_collections()
            return True
        except Exception as e:
            logger.error(f"Qdrant health check failed: {str(e)}")
            return False


# Global vector store instance
_vector_store = None


def get_vector_store() -> VectorStore:
    """Get or create the global vector store instance"""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
