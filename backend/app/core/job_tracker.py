"""
Simple in-memory job tracking for background upload processing
"""
from typing import Dict, Optional, List
from datetime import datetime
from enum import Enum
import logging

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
    """In-memory job tracking"""

    def __init__(self, max_jobs: int = 1000):
        """
        Initialize job tracker

        Args:
            max_jobs: Maximum number of jobs to keep in memory (FIFO)
        """
        self.jobs: Dict[str, JobInfo] = {}
        self.max_jobs = max_jobs

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
        # Clean up old jobs if at max capacity
        if len(self.jobs) >= self.max_jobs:
            oldest_job_id = min(self.jobs.keys(), key=lambda k: self.jobs[k].created_at)
            del self.jobs[oldest_job_id]
            logger.info(f"Removed oldest job {oldest_job_id} to make space")

        job = JobInfo(job_id, file_name, conversation_id)
        self.jobs[job_id] = job
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
        return self.jobs.get(job_id)

    def update_job_status(self, job_id: str, status: JobStatus, error_message: Optional[str] = None):
        """
        Update job status

        Args:
            job_id: Job identifier
            status: New status
            error_message: Optional error message
        """
        job = self.jobs.get(job_id)
        if job:
            job.update_status(status, error_message)

    def add_file_result(self, job_id: str, result: Dict):
        """
        Add file processing result to job

        Args:
            job_id: Job identifier
            result: File processing result dictionary
        """
        job = self.jobs.get(job_id)
        if job:
            job.add_file_result(result)

    def get_all_jobs(self, conversation_id: Optional[str] = None) -> List[Dict]:
        """
        Get all jobs, optionally filtered by conversation

        Args:
            conversation_id: Optional conversation filter

        Returns:
            List of job dictionaries
        """
        jobs = self.jobs.values()
        if conversation_id:
            jobs = [j for j in jobs if j.conversation_id == conversation_id]

        # Sort by creation time, newest first
        sorted_jobs = sorted(jobs, key=lambda j: j.created_at, reverse=True)
        return [j.to_dict() for j in sorted_jobs]


# Global job tracker instance
_job_tracker = None


def get_job_tracker() -> JobTracker:
    """Get or create global job tracker instance"""
    global _job_tracker
    if _job_tracker is None:
        _job_tracker = JobTracker()
    return _job_tracker
