"""
Qdrant vector store for IC meeting notes.

Stores parsed Q&A segments from IC meeting notes in a dedicated Qdrant collection,
enabling semantic retrieval of historically relevant IC questions and discussions.
"""
import uuid
import time
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams, Distance, PointStruct, Filter,
    FieldCondition, MatchValue, Range, TextIndexParams,
    TextIndexType, TokenizerType, PointIdsList,
)

from backend.app.config import settings
from backend.app.core.embeddings import get_embedding_generator

logger = logging.getLogger(__name__)


class ICMeetingStore:
    """Qdrant vector store dedicated to IC meeting Q&A segments."""

    def __init__(self):
        self.client = QdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT,
        )
        self.collection_name = settings.IC_MEETINGS_COLLECTION_NAME
        self.embedding_generator = get_embedding_generator()
        self.embedding_dim = self.embedding_generator.get_embedding_dimension()
        self._init_collection()

    def _init_collection(self):
        """Create the ic_meetings collection if it doesn't exist."""
        try:
            collections = self.client.get_collections().collections
            existing = [c.name for c in collections]

            if self.collection_name not in existing:
                logger.info(f"Creating IC meetings collection: {self.collection_name}")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.embedding_dim,
                        distance=Distance.COSINE,
                    ),
                )
                # Create text index for hybrid search
                try:
                    self.client.create_payload_index(
                        collection_name=self.collection_name,
                        field_name="content",
                        field_schema=TextIndexParams(
                            type=TextIndexType.TEXT,
                            tokenizer=TokenizerType.WORD,
                            min_token_len=2,
                            max_token_len=20,
                            lowercase=True,
                        ),
                    )
                except Exception as e:
                    logger.warning(f"Could not create text index: {e}")
            else:
                logger.info(f"IC meetings collection already exists: {self.collection_name}")
        except Exception as e:
            logger.error(f"Error initializing IC meetings collection: {e}")
            raise

    def add_meeting_segments(
        self,
        segments: List[Dict[str, Any]],
        page_id: str,
        title: str,
        meeting_date: str,
        source: str = "confluence",
    ) -> int:
        """
        Add parsed meeting Q&A segments to the vector store.

        Args:
            segments: List of dicts with keys: question, answer, topic, raw_text
            page_id: Confluence page ID or upload file ID
            title: Meeting note title
            meeting_date: ISO date string of the meeting
            source: "confluence" or "upload"

        Returns:
            Number of segments added
        """
        if not segments:
            return 0

        start = time.time()

        # Build text for embedding — combine question + answer + raw_text
        texts = []
        for seg in segments:
            parts = []
            if seg.get("question"):
                parts.append(f"Question: {seg['question']}")
            if seg.get("answer"):
                parts.append(f"Answer: {seg['answer']}")
            if not parts and seg.get("raw_text"):
                parts.append(seg["raw_text"])
            texts.append("\n".join(parts))

        # Generate embeddings
        embeddings = self.embedding_generator.embed_batch(texts)

        # Build Qdrant points
        points = []
        for idx, (seg, embedding, text) in enumerate(zip(segments, embeddings, texts)):
            point_id = str(uuid.uuid4())
            payload = {
                "content": text,
                "question": seg.get("question", ""),
                "answer": seg.get("answer", ""),
                "topic": seg.get("topic", ""),
                "raw_text": seg.get("raw_text", ""),
                "page_id": page_id,
                "meeting_title": title,
                "meeting_date": meeting_date,
                "source": source,
                "indexed_at": datetime.utcnow().isoformat(),
                "chunk_index": idx,
            }
            points.append(PointStruct(id=point_id, vector=embedding, payload=payload))

        # Upload in batches
        batch_size = 100
        for i in range(0, len(points), batch_size):
            self.client.upsert(
                collection_name=self.collection_name,
                points=points[i : i + batch_size],
            )

        elapsed = time.time() - start
        logger.info(
            f"Added {len(points)} segments from '{title}' in {elapsed:.2f}s"
        )
        return len(points)

    def search(
        self,
        query: str,
        top_k: int = 15,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Semantic search over IC meeting segments.

        Args:
            query: Search query text
            top_k: Number of results to return
            date_from: Only include meetings on or after this date (ISO format, e.g. "2024-01-01")
            date_to: Only include meetings on or before this date (ISO format, e.g. "2025-12-31")

        Returns the most relevant historical Q&A segments for the given query.
        """
        query_embedding = self.embedding_generator.embed_text(query)

        # Build date range filter
        search_filter = self._build_date_filter(date_from, date_to)

        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=top_k,
            query_filter=search_filter,
        )

        formatted = []
        for hit in results:
            formatted.append({
                "content": hit.payload.get("content", ""),
                "question": hit.payload.get("question", ""),
                "answer": hit.payload.get("answer", ""),
                "topic": hit.payload.get("topic", ""),
                "meeting_title": hit.payload.get("meeting_title", ""),
                "meeting_date": hit.payload.get("meeting_date", ""),
                "score": hit.score,
            })

        return formatted

    def _build_date_filter(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Optional[Filter]:
        """Build a Qdrant filter for meeting_date range."""
        if not date_from and not date_to:
            return None

        conditions = []
        if date_from:
            conditions.append(
                FieldCondition(
                    key="meeting_date",
                    range=Range(gte=date_from),
                )
            )
        if date_to:
            # Append "T23:59:59" so that the end date is inclusive of the whole day
            date_to_inclusive = date_to if "T" in date_to else date_to + "T23:59:59"
            conditions.append(
                FieldCondition(
                    key="meeting_date",
                    range=Range(lte=date_to_inclusive),
                )
            )

        return Filter(must=conditions)

    def delete_by_page_id(self, page_id: str) -> int:
        """Delete all segments for a given page/document."""
        all_points = []
        offset = None

        while True:
            scroll_result = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[FieldCondition(key="page_id", match=MatchValue(value=page_id))]
                ),
                limit=100,
                offset=offset,
                with_payload=False,
                with_vectors=False,
            )
            points, next_offset = scroll_result
            if not points:
                break
            all_points.extend(points)
            if next_offset is None:
                break
            offset = next_offset

        if all_points:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=PointIdsList(points=[p.id for p in all_points]),
            )
            logger.info(f"Deleted {len(all_points)} segments for page_id={page_id}")

        return len(all_points)

    def list_meetings(self) -> List[Dict[str, Any]]:
        """List all unique meetings currently indexed."""
        all_points, _ = self.client.scroll(
            collection_name=self.collection_name,
            limit=10000,
            with_payload=True,
            with_vectors=False,
        )

        meetings = {}
        for point in all_points:
            page_id = point.payload.get("page_id", "")
            if page_id and page_id not in meetings:
                meetings[page_id] = {
                    "page_id": page_id,
                    "title": point.payload.get("meeting_title", ""),
                    "meeting_date": point.payload.get("meeting_date", ""),
                    "source": point.payload.get("source", ""),
                    "segment_count": 0,
                }
            if page_id:
                meetings[page_id]["segment_count"] += 1

        return sorted(
            meetings.values(),
            key=lambda m: m.get("meeting_date", ""),
            reverse=True,
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get collection statistics."""
        try:
            info = self.client.get_collection(self.collection_name)
            meetings = self.list_meetings()
            return {
                "total_segments": info.points_count,
                "total_meetings": len(meetings),
                "collection_name": self.collection_name,
            }
        except Exception as e:
            logger.error(f"Error getting IC meeting stats: {e}")
            return {"total_segments": 0, "total_meetings": 0, "error": str(e)}


# Singleton
_ic_meeting_store = None


def get_ic_meeting_store() -> ICMeetingStore:
    """Get or create the global IC meeting store instance."""
    global _ic_meeting_store
    if _ic_meeting_store is None:
        _ic_meeting_store = ICMeetingStore()
    return _ic_meeting_store
