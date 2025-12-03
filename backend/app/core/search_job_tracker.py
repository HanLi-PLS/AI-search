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

    def __init__(self, job_id: str, query: str, search_mode: str, reasoning_mode: str, conversation_id: Optional[str] = None):
        self.job_id = job_id
        self.query = query
        self.search_mode = search_mode
        self.reasoning_mode = reasoning_mode
        self.conversation_id = conversation_id
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
            conn.commit()

    def _job_from_row(self, row) -> SearchJobInfo:
        """Convert database row to SearchJobInfo object"""
        job = SearchJobInfo.__new__(SearchJobInfo)
        job.job_id = row[0]
        job.query = row[1]
        job.search_mode = row[2]
        job.reasoning_mode = row[3]
        job.conversation_id = row[4]
        job.status = SearchJobStatus(row[5])
        job.created_at = datetime.fromisoformat(row[6])
        job.updated_at = datetime.fromisoformat(row[7])
        job.progress = row[8]
        job.current_step = row[9]
        job.error_message = row[10]
        job.answer = row[11]
        job.extracted_info = row[12]
        job.online_search_response = row[13]
        job.results = json.loads(row[14]) if row[14] else None
        job.total_results = row[15]
        job.processing_time = row[16]
        return job

    def create_job(self, job_id: str, query: str, search_mode: str, reasoning_mode: str, conversation_id: Optional[str] = None) -> SearchJobInfo:
        """
        Create a new search job

        Args:
            job_id: Unique job identifier
            query: Search query
            search_mode: Search mode (files_only, online_only, both, sequential_analysis)
            reasoning_mode: Reasoning mode (non_reasoning, reasoning, reasoning_gpt5, deep_research)
            conversation_id: Optional conversation ID

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
                job = SearchJobInfo(job_id, query, search_mode, reasoning_mode, conversation_id)
                conn.execute("""
                    INSERT INTO search_jobs (
                        job_id, query, search_mode, reasoning_mode, conversation_id, status, created_at, updated_at,
                        progress, current_step, error_message, answer, extracted_info, online_search_response,
                        results, total_results, processing_time
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    job.job_id, job.query, job.search_mode, job.reasoning_mode, job.conversation_id, job.status.value,
                    job.created_at.isoformat(), job.updated_at.isoformat(),
                    job.progress, job.current_step, job.error_message, job.answer, job.extracted_info,
                    job.online_search_response, None, job.total_results, job.processing_time
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
            row = conn.execute("SELECT * FROM search_jobs WHERE job_id = ?", (job_id,)).fetchone()
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


# Global search job tracker instance
_search_job_tracker = None


def get_search_job_tracker() -> SearchJobTracker:
    """Get or create global search job tracker instance"""
    global _search_job_tracker
    if _search_job_tracker is None:
        _search_job_tracker = SearchJobTracker()
    return _search_job_tracker
