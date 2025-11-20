"""
Database-backed job tracking for background upload processing
Uses SQLite for shared state across multiple uvicorn workers
"""
from typing import Dict, Optional, List
from datetime import datetime
from enum import Enum
import logging
import sqlite3
import json
import threading
from pathlib import Path

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Job status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobInfo:
    """Job information container"""

    def __init__(self, job_id: str, file_name: str, conversation_id: Optional[str] = None):
        self.job_id = job_id
        self.file_name = file_name
        self.conversation_id = conversation_id
        self.status = JobStatus.PENDING
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.total_files = 0
        self.processed_files = 0
        self.failed_files = 0
        self.total_chunks = 0
        self.error_message: Optional[str] = None
        self.file_results: List[Dict] = []

    def to_dict(self) -> Dict:
        """Convert to dictionary for API response"""
        return {
            "job_id": self.job_id,
            "file_name": self.file_name,
            "conversation_id": self.conversation_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "total_files": self.total_files,
            "processed_files": self.processed_files,
            "failed_files": self.failed_files,
            "total_chunks": self.total_chunks,
            "error_message": self.error_message,
            "file_results": self.file_results
        }

    def update_status(self, status: JobStatus, error_message: Optional[str] = None):
        """Update job status"""
        self.status = status
        self.updated_at = datetime.now()
        if error_message:
            self.error_message = error_message
        logger.info(f"Job {self.job_id} status updated to {status.value}")

    def add_file_result(self, result: Dict):
        """Add a file processing result"""
        self.file_results.append(result)
        self.processed_files += 1
        if result.get('success'):
            self.total_chunks += result.get('chunks_created', 0)
        else:
            self.failed_files += 1
        self.updated_at = datetime.now()


class JobTracker:
    """Database-backed job tracking with SQLite for multi-worker support"""

    def __init__(self, db_path: str = "data/db/jobs.db", max_jobs: int = 1000):
        """
        Initialize job tracker with SQLite database

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
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    file_name TEXT NOT NULL,
                    conversation_id TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    total_files INTEGER DEFAULT 0,
                    processed_files INTEGER DEFAULT 0,
                    failed_files INTEGER DEFAULT 0,
                    total_chunks INTEGER DEFAULT 0,
                    error_message TEXT,
                    file_results TEXT
                )
            """)
            conn.commit()

    def _job_from_row(self, row) -> JobInfo:
        """Convert database row to JobInfo object"""
        job = JobInfo.__new__(JobInfo)
        job.job_id = row[0]
        job.file_name = row[1]
        job.conversation_id = row[2]
        job.status = JobStatus(row[3])
        job.created_at = datetime.fromisoformat(row[4])
        job.updated_at = datetime.fromisoformat(row[5])
        job.total_files = row[6]
        job.processed_files = row[7]
        job.failed_files = row[8]
        job.total_chunks = row[9]
        job.error_message = row[10]
        job.file_results = json.loads(row[11]) if row[11] else []
        return job

    def create_job(self, job_id: str, file_name: str, conversation_id: Optional[str] = None) -> JobInfo:
        """
        Create a new job

        Args:
            job_id: Unique job identifier
            file_name: Name of file being processed
            conversation_id: Optional conversation ID

        Returns:
            Created JobInfo object
        """
        with self.lock:
            # Clean up old jobs if at max capacity
            with sqlite3.connect(str(self.db_path)) as conn:
                count = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
                if count >= self.max_jobs:
                    # Delete oldest job
                    conn.execute("""
                        DELETE FROM jobs
                        WHERE job_id = (SELECT job_id FROM jobs ORDER BY created_at ASC LIMIT 1)
                    """)
                    logger.info("Removed oldest job to make space")

                # Create new job
                job = JobInfo(job_id, file_name, conversation_id)
                conn.execute("""
                    INSERT INTO jobs (
                        job_id, file_name, conversation_id, status, created_at, updated_at,
                        total_files, processed_files, failed_files, total_chunks, error_message, file_results
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    job.job_id, job.file_name, job.conversation_id, job.status.value,
                    job.created_at.isoformat(), job.updated_at.isoformat(),
                    job.total_files, job.processed_files, job.failed_files, job.total_chunks,
                    job.error_message, json.dumps(job.file_results)
                ))
                conn.commit()
                logger.info(f"Created job {job_id} for file {file_name}")
                return job

    def get_job(self, job_id: str) -> Optional[JobInfo]:
        """
        Get job by ID

        Args:
            job_id: Job identifier

        Returns:
            JobInfo object or None if not found
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
            if row:
                return self._job_from_row(row)
            return None

    def update_job_status(self, job_id: str, status: JobStatus, error_message: Optional[str] = None):
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
                        UPDATE jobs
                        SET status = ?, updated_at = ?, error_message = ?
                        WHERE job_id = ?
                    """, (status.value, datetime.now().isoformat(), error_message, job_id))
                else:
                    conn.execute("""
                        UPDATE jobs
                        SET status = ?, updated_at = ?
                        WHERE job_id = ?
                    """, (status.value, datetime.now().isoformat(), job_id))
                conn.commit()
                logger.info(f"Job {job_id} status updated to {status.value}")

    def update_total_files(self, job_id: str, total_files: int):
        """
        Update total files count for a job

        Args:
            job_id: Job identifier
            total_files: Total number of files to process
        """
        with self.lock:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute("""
                    UPDATE jobs
                    SET total_files = ?, updated_at = ?
                    WHERE job_id = ?
                """, (total_files, datetime.now().isoformat(), job_id))
                conn.commit()

    def add_file_result(self, job_id: str, result: Dict):
        """
        Add file processing result to job

        Args:
            job_id: Job identifier
            result: File processing result dictionary
        """
        with self.lock:
            with sqlite3.connect(str(self.db_path)) as conn:
                # Get current job data
                row = conn.execute("SELECT file_results, processed_files, failed_files, total_chunks FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
                if row:
                    file_results = json.loads(row[0]) if row[0] else []
                    processed_files = row[1]
                    failed_files = row[2]
                    total_chunks = row[3]

                    # Update values
                    file_results.append(result)
                    processed_files += 1
                    if result.get('success'):
                        total_chunks += result.get('chunks_created', 0)
                    else:
                        failed_files += 1

                    # Save back to database
                    conn.execute("""
                        UPDATE jobs
                        SET file_results = ?, processed_files = ?, failed_files = ?, total_chunks = ?, updated_at = ?
                        WHERE job_id = ?
                    """, (json.dumps(file_results), processed_files, failed_files, total_chunks, datetime.now().isoformat(), job_id))
                    conn.commit()

    def get_all_jobs(self, conversation_id: Optional[str] = None) -> List[Dict]:
        """
        Get all jobs, optionally filtered by conversation

        Args:
            conversation_id: Optional conversation filter

        Returns:
            List of job dictionaries
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            if conversation_id:
                rows = conn.execute(
                    "SELECT * FROM jobs WHERE conversation_id = ? ORDER BY created_at DESC",
                    (conversation_id,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC").fetchall()

            return [self._job_from_row(row).to_dict() for row in rows]


# Global job tracker instance
_job_tracker = None


def get_job_tracker() -> JobTracker:
    """Get or create global job tracker instance"""
    global _job_tracker
    if _job_tracker is None:
        _job_tracker = JobTracker()
    return _job_tracker
