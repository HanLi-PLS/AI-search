"""
Background job tracking for long-running AI searches
Extends the existing job tracking system for searches with reasoning models
"""
from typing import Dict, Optional, Any
from datetime import datetime
from enum import Enum
import logging
import sqlite3
import json
import threading
from pathlib import Path

logger = logging.getLogger(__name__)


class SearchJobStatus(str, Enum):
    """Search job status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SearchJobInfo:
    """Search job information container"""

    def __init__(self, job_id: str, query: str, search_mode: str, reasoning_mode: str, conversation_id: Optional[str] = None, user_id: Optional[int] = None, top_k: int = 10, priority_order: Optional[str] = None):
        self.job_id = job_id
        self.query = query
        self.search_mode = search_mode
        self.reasoning_mode = reasoning_mode
        self.conversation_id = conversation_id
        self.user_id = user_id
        self.top_k = top_k
        self.priority_order = priority_order
        self.status = SearchJobStatus.PENDING
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.progress = 0  # 0-100 percentage
        self.current_step = ""  # Step 0, Step 1, Step 2, Step 3
        self.error_message: Optional[str] = None

        # Results (only populated when completed)
        self.answer: Optional[str] = None
        self.extracted_info: Optional[str] = None
        self.online_search_response: Optional[str] = None
        self.results: Optional[list] = None
        self.total_results: int = 0
        self.processing_time: float = 0.0

    def to_dict(self) -> Dict:
        """Convert to dictionary for API response"""
        return {
            "job_id": self.job_id,
            "query": self.query,
            "search_mode": self.search_mode,
            "reasoning_mode": self.reasoning_mode,
            "conversation_id": self.conversation_id,
            "top_k": self.top_k,
            "priority_order": self.priority_order,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "progress": self.progress,
            "current_step": self.current_step,
            "error_message": self.error_message,
            "answer": self.answer,
            "extracted_info": self.extracted_info,
            "online_search_response": self.online_search_response,
            "results": self.results,
            "total_results": self.total_results,
            "processing_time": self.processing_time
        }


class SearchJobTracker:
    """Database-backed search job tracking with SQLite"""

    def __init__(self, db_path: str = "data/db/search_jobs.db", max_jobs: int = 500):
        """
        Initialize search job tracker with SQLite database

        Args:
            db_path: Path to SQLite database file
            max_jobs: Maximum number of jobs to keep in database (FIFO)
        """
        self.db_path = Path(db_path)
        self.max_jobs = max_jobs
        self.lock = threading.Lock()

        # Create database directory if it doesn't exist
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._init_db()

    def _init_db(self):
        """Initialize database schema"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS search_jobs (
                    job_id TEXT PRIMARY KEY,
                    query TEXT NOT NULL,
                    search_mode TEXT NOT NULL,
                    reasoning_mode TEXT NOT NULL,
                    conversation_id TEXT,
                    user_id INTEGER,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    progress INTEGER DEFAULT 0,
                    current_step TEXT DEFAULT '',
                    error_message TEXT,
                    answer TEXT,
                    extracted_info TEXT,
                    online_search_response TEXT,
                    results TEXT,
                    total_results INTEGER DEFAULT 0,
                    processing_time REAL DEFAULT 0.0
                )
            """)

            # Add user_id column if it doesn't exist (migration for existing databases)
            try:
                conn.execute("ALTER TABLE search_jobs ADD COLUMN user_id INTEGER")
                conn.commit()
            except sqlite3.OperationalError:
                # Column already exists
                pass

            # Add top_k column if it doesn't exist (migration for existing databases)
            try:
                conn.execute("ALTER TABLE search_jobs ADD COLUMN top_k INTEGER DEFAULT 10")
                conn.commit()
            except sqlite3.OperationalError:
                # Column already exists
                pass

            # Add priority_order column if it doesn't exist (migration for existing databases)
            try:
                conn.execute("ALTER TABLE search_jobs ADD COLUMN priority_order TEXT")
                conn.commit()
            except sqlite3.OperationalError:
                # Column already exists
                pass

    def _job_from_row(self, row) -> SearchJobInfo:
        """Convert database row to SearchJobInfo object"""
        job = SearchJobInfo.__new__(SearchJobInfo)
        job.job_id = row[0]
        job.query = row[1]
        job.search_mode = row[2]
        job.reasoning_mode = row[3]
        job.conversation_id = row[4]
        job.user_id = row[5]
        job.status = SearchJobStatus(row[6])
        job.created_at = datetime.fromisoformat(row[7])
        job.updated_at = datetime.fromisoformat(row[8])
        job.progress = row[9]
        job.current_step = row[10]
        job.error_message = row[11]
        job.answer = row[12]
        job.extracted_info = row[13]
        job.online_search_response = row[14]
        job.results = json.loads(row[15]) if row[15] else None
        job.total_results = row[16]
        job.processing_time = row[17]
        job.top_k = row[18] if len(row) > 18 and row[18] is not None else 10
        job.priority_order = row[19] if len(row) > 19 else None
        return job

    def create_job(self, job_id: str, query: str, search_mode: str, reasoning_mode: str, conversation_id: Optional[str] = None, user_id: Optional[int] = None, top_k: int = 10, priority_order: Optional[str] = None) -> SearchJobInfo:
        """
        Create a new search job

        Args:
            job_id: Unique job identifier
            query: Search query
            search_mode: Search mode (files_only, online_only, both, sequential_analysis)
            reasoning_mode: Reasoning mode (non_reasoning, reasoning, reasoning_gpt5, deep_research)
            conversation_id: Optional conversation ID
            user_id: Optional user ID for filtering
            top_k: Number of results to return (default: 10)
            priority_order: Priority order for 'both' mode (online_first/files_first)

        Returns:
            Created SearchJobInfo object
        """
        with self.lock:
            # Clean up old jobs if at max capacity
            with sqlite3.connect(str(self.db_path)) as conn:
                count = conn.execute("SELECT COUNT(*) FROM search_jobs").fetchone()[0]
                if count >= self.max_jobs:
                    # Delete oldest job
                    conn.execute("""
                        DELETE FROM search_jobs
                        WHERE job_id = (SELECT job_id FROM search_jobs ORDER BY created_at ASC LIMIT 1)
                    """)
                    logger.info("Removed oldest search job to make space")

                # Create new job
                job = SearchJobInfo(job_id, query, search_mode, reasoning_mode, conversation_id, user_id, top_k, priority_order)
                conn.execute("""
                    INSERT INTO search_jobs (
                        job_id, query, search_mode, reasoning_mode, conversation_id, user_id, status, created_at, updated_at,
                        progress, current_step, error_message, answer, extracted_info, online_search_response,
                        results, total_results, processing_time, top_k, priority_order
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    job.job_id, job.query, job.search_mode, job.reasoning_mode, job.conversation_id, job.user_id, job.status.value,
                    job.created_at.isoformat(), job.updated_at.isoformat(),
                    job.progress, job.current_step, job.error_message, job.answer, job.extracted_info,
                    job.online_search_response, None, job.total_results, job.processing_time, job.top_k, job.priority_order
                ))
                conn.commit()
                logger.info(f"Created search job {job_id} for query: {query[:50]}...")
                return job

    def get_job(self, job_id: str) -> Optional[SearchJobInfo]:
        """
        Get job by ID

        Args:
            job_id: Job identifier

        Returns:
            SearchJobInfo object or None if not found
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            row = conn.execute("""
                SELECT job_id, query, search_mode, reasoning_mode, conversation_id, user_id,
                       status, created_at, updated_at, progress, current_step, error_message,
                       answer, extracted_info, online_search_response, results, total_results, processing_time,
                       top_k, priority_order
                FROM search_jobs WHERE job_id = ?
            """, (job_id,)).fetchone()
            if row:
                return self._job_from_row(row)
            return None

    def update_progress(self, job_id: str, progress: int, current_step: str):
        """
        Update job progress

        Args:
            job_id: Job identifier
            progress: Progress percentage (0-100)
            current_step: Current step description
        """
        with self.lock:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute("""
                    UPDATE search_jobs
                    SET progress = ?, current_step = ?, updated_at = ?
                    WHERE job_id = ?
                """, (progress, current_step, datetime.now().isoformat(), job_id))
                conn.commit()
                logger.info(f"Search job {job_id} progress: {progress}% - {current_step}")

    def update_status(self, job_id: str, status: SearchJobStatus, error_message: Optional[str] = None):
        """
        Update job status

        Args:
            job_id: Job identifier
            status: New status
            error_message: Optional error message
        """
        with self.lock:
            with sqlite3.connect(str(self.db_path)) as conn:
                if error_message:
                    conn.execute("""
                        UPDATE search_jobs
                        SET status = ?, updated_at = ?, error_message = ?
                        WHERE job_id = ?
                    """, (status.value, datetime.now().isoformat(), error_message, job_id))
                else:
                    conn.execute("""
                        UPDATE search_jobs
                        SET status = ?, updated_at = ?
                        WHERE job_id = ?
                    """, (status.value, datetime.now().isoformat(), job_id))
                conn.commit()
                logger.info(f"Search job {job_id} status updated to {status.value}")

    def save_results(self, job_id: str, answer: str, results: list, total_results: int, processing_time: float,
                     extracted_info: Optional[str] = None, online_search_response: Optional[str] = None):
        """
        Save search results to job

        Args:
            job_id: Job identifier
            answer: Final answer
            results: Search results list
            total_results: Total number of results
            processing_time: Processing time in seconds
            extracted_info: Optional extracted information (Step 1)
            online_search_response: Optional online search response (Step 2)
        """
        with self.lock:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute("""
                    UPDATE search_jobs
                    SET answer = ?, results = ?, total_results = ?, processing_time = ?,
                        extracted_info = ?, online_search_response = ?, status = ?, updated_at = ?, progress = 100
                    WHERE job_id = ?
                """, (
                    answer, json.dumps(results), total_results, processing_time,
                    extracted_info, online_search_response, SearchJobStatus.COMPLETED.value,
                    datetime.now().isoformat(), job_id
                ))
                conn.commit()
                logger.info(f"Search job {job_id} results saved successfully")

    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a search job

        Args:
            job_id: Job identifier

        Returns:
            True if job was cancelled, False if job not found or already completed
        """
        with self.lock:
            with sqlite3.connect(str(self.db_path)) as conn:
                # Check current status
                row = conn.execute("SELECT status FROM search_jobs WHERE job_id = ?", (job_id,)).fetchone()
                if not row:
                    logger.warning(f"Cannot cancel search job {job_id}: not found")
                    return False

                current_status = SearchJobStatus(row[0])

                # Only allow cancelling pending or processing jobs
                if current_status in [SearchJobStatus.COMPLETED, SearchJobStatus.FAILED, SearchJobStatus.CANCELLED]:
                    logger.warning(f"Cannot cancel search job {job_id}: already in status {current_status.value}")
                    return False

                # Update to cancelled status
                conn.execute("""
                    UPDATE search_jobs
                    SET status = ?, updated_at = ?, error_message = ?
                    WHERE job_id = ?
                """, (SearchJobStatus.CANCELLED.value, datetime.now().isoformat(), "Cancelled by user", job_id))
                conn.commit()
                logger.info(f"Search job {job_id} cancelled by user")
                return True

    def is_job_cancelled(self, job_id: str) -> bool:
        """
        Check if a job has been cancelled

        Args:
            job_id: Job identifier

        Returns:
            True if job is cancelled, False otherwise
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            row = conn.execute("SELECT status FROM search_jobs WHERE job_id = ?", (job_id,)).fetchone()
            if row:
                return SearchJobStatus(row[0]) == SearchJobStatus.CANCELLED
            return False

    def get_conversations(self, user_id: Optional[int] = None, limit: int = 100) -> list:
        """
        Get all conversations with their search history, optionally filtered by user

        Args:
            user_id: Optional user ID to filter conversations
            limit: Maximum number of conversations to return

        Returns:
            List of conversations with metadata and search count
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            # Get conversations grouped by conversation_id
            if user_id is not None:
                query = """
                    SELECT
                        conversation_id,
                        MIN(created_at) as first_search,
                        MAX(updated_at) as last_updated,
                        COUNT(*) as search_count,
                        MAX(CASE WHEN status = 'completed' THEN query ELSE NULL END) as last_query
                    FROM search_jobs
                    WHERE conversation_id IS NOT NULL AND user_id = ?
                    GROUP BY conversation_id
                    ORDER BY MAX(updated_at) DESC
                    LIMIT ?
                """
                rows = conn.execute(query, (user_id, limit)).fetchall()
            else:
                query = """
                    SELECT
                        conversation_id,
                        MIN(created_at) as first_search,
                        MAX(updated_at) as last_updated,
                        COUNT(*) as search_count,
                        MAX(CASE WHEN status = 'completed' THEN query ELSE NULL END) as last_query
                    FROM search_jobs
                    WHERE conversation_id IS NOT NULL
                    GROUP BY conversation_id
                    ORDER BY MAX(updated_at) DESC
                    LIMIT ?
                """
                rows = conn.execute(query, (limit,)).fetchall()

            conversations = []
            for row in rows:
                conversation_id, first_search, last_updated, search_count, last_query = row
                conversations.append({
                    'id': conversation_id,
                    'title': (last_query[:50] + '...') if last_query and len(last_query) > 50 else (last_query or 'Conversation'),
                    'createdAt': first_search,
                    'updatedAt': last_updated,
                    'searchCount': search_count
                })

            return conversations

    def get_conversation_history(self, conversation_id: str, user_id: Optional[int] = None) -> list:
        """
        Get all searches for a specific conversation, optionally filtered by user

        Args:
            conversation_id: Conversation identifier
            user_id: Optional user ID to verify ownership

        Returns:
            List of searches in chronological order
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            if user_id is not None:
                query = """
                    SELECT job_id, query, answer, created_at, status, reasoning_mode, search_mode, top_k, priority_order, extracted_info, online_search_response
                    FROM search_jobs
                    WHERE conversation_id = ? AND user_id = ?
                    ORDER BY created_at ASC
                """
                rows = conn.execute(query, (conversation_id, user_id)).fetchall()
            else:
                query = """
                    SELECT job_id, query, answer, created_at, status, reasoning_mode, search_mode, top_k, priority_order, extracted_info, online_search_response
                    FROM search_jobs
                    WHERE conversation_id = ?
                    ORDER BY created_at ASC
                """
                rows = conn.execute(query, (conversation_id,)).fetchall()

            history = []
            for row in rows:
                job_id, query, answer, created_at, status, reasoning_mode, search_mode = row[:7]
                top_k = row[7] if len(row) > 7 and row[7] is not None else 10
                priority_order = row[8] if len(row) > 8 else None
                extracted_info = row[9] if len(row) > 9 else None
                online_search_response = row[10] if len(row) > 10 else None

                # Deserialize JSON strings back to Python objects
                if extracted_info:
                    try:
                        import json
                        extracted_info = json.loads(extracted_info)
                    except:
                        pass  # Keep as string if JSON parsing fails

                if online_search_response:
                    try:
                        import json
                        online_search_response = json.loads(online_search_response)
                    except:
                        pass  # Keep as string if JSON parsing fails

                # Only include completed searches
                if status == 'completed' and query and answer:
                    history.append({
                        'query': query,
                        'answer': answer,
                        'timestamp': created_at,
                        'reasoning_mode': reasoning_mode,
                        'search_mode': search_mode,
                        'top_k': top_k,
                        'priority_order': priority_order,
                        'extracted_info': extracted_info,
                        'online_search_response': online_search_response
                    })

            return history


# Global search job tracker instance
_search_job_tracker = None


def get_search_job_tracker() -> SearchJobTracker:
    """Get or create global search job tracker instance"""
    global _search_job_tracker
    if _search_job_tracker is None:
        _search_job_tracker = SearchJobTracker()
    return _search_job_tracker
