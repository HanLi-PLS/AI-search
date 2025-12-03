"""
Dedicated worker process for processing pending upload jobs
Polls the SQLite database for pending jobs and processes them
"""
import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.app.core.job_tracker import get_job_tracker, JobStatus
from backend.app.core.file_processor import process_file_background

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
shutdown_event = asyncio.Event()


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_event.set()


async def process_pending_jobs():
    """
    Main worker loop - polls for pending jobs and processes them
    """
    job_tracker = get_job_tracker()
    logger.info("Job worker started - polling for pending jobs...")

    # Track currently processing job to avoid double-processing
    current_job_id: Optional[str] = None

    while not shutdown_event.is_set():
        try:
            # If we have a current job, check if it's still processing
            if current_job_id:
                current_job = job_tracker.get_job(current_job_id)
                if not current_job or current_job.status != JobStatus.PROCESSING:
                    # Job completed, failed, or was cancelled
                    logger.info(f"Job {current_job_id} finished with status: {current_job.status if current_job else 'not found'}")
                    current_job_id = None

            # Only look for new jobs if we're not currently processing one
            if not current_job_id:
                # Get all jobs and find first pending one
                all_jobs = job_tracker.get_all_jobs()
                pending_job = next(
                    (job for job in all_jobs if job['status'] == JobStatus.PENDING.value),
                    None
                )

                if pending_job:
                    job_id = pending_job['job_id']
                    file_name = pending_job['file_name']
                    conversation_id = pending_job['conversation_id']

                    logger.info(f"Found pending job {job_id} for file: {file_name}")

                    # Reconstruct file path from job info
                    # The temp file should be in upload directory with pattern: {file_id}_{filename}
                    # We need to find it by scanning the directory
                    from backend.app.config import settings
                    upload_dir = Path(settings.UPLOAD_DIR)

                    # Find temp file matching this job
                    # Sanitize filename for pattern matching (same as upload.py does)
                    safe_filename = file_name.replace('/', '_').replace('\\', '_')
                    temp_file = None
                    for f in upload_dir.glob(f"*_{safe_filename}"):
                        temp_file = f
                        break

                    if not temp_file or not temp_file.exists():
                        # File not found - mark job as failed
                        logger.error(f"Temp file not found for job {job_id}: {file_name}")
                        job_tracker.update_job_status(
                            job_id,
                            JobStatus.FAILED,
                            "Temporary file not found - may have been deleted"
                        )
                        continue

                    # Get file extension
                    file_ext = temp_file.suffix.lower()

                    # Mark as current job
                    current_job_id = job_id

                    # Process the file
                    try:
                        await process_file_background(
                            temp_file,
                            file_name,
                            file_ext,
                            conversation_id,
                            job_id,
                            None
                        )
                    except Exception as e:
                        logger.error(f"Error processing job {job_id}: {str(e)}")
                        job_tracker.update_job_status(job_id, JobStatus.FAILED, str(e))
                        current_job_id = None

            # Poll interval - check for new jobs every 2 seconds
            await asyncio.sleep(2)

        except Exception as e:
            logger.error(f"Error in worker loop: {str(e)}")
            # Continue running even if there's an error
            await asyncio.sleep(5)

    logger.info("Job worker shutting down gracefully...")


async def main():
    """
    Main entry point for the worker
    """
    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        await process_pending_jobs()
    except Exception as e:
        logger.error(f"Fatal error in worker: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    # Run the async worker
    asyncio.run(main())
