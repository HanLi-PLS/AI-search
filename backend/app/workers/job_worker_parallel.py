"""
Parallel job worker - processes multiple jobs concurrently
"""
import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import Optional, Set
import concurrent.futures

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.app.core.job_tracker import get_job_tracker, JobStatus
from backend.app.core.file_processor import process_file_background
from backend.app.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
shutdown_event = asyncio.Event()

# Maximum concurrent jobs (adjust based on server resources)
MAX_CONCURRENT_JOBS = 3


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_event.set()


async def process_single_job(job_id: str, file_name: str, conversation_id: str) -> bool:
    """
    Process a single job

    Returns:
        True if successful, False otherwise
    """
    job_tracker = get_job_tracker()

    try:
        # Find temp file
        upload_dir = Path(settings.UPLOAD_DIR)
        safe_filename = file_name.replace('/', '_').replace('\\', '_')
        temp_file = None

        for f in upload_dir.glob(f"*_{safe_filename}"):
            temp_file = f
            break

        if not temp_file or not temp_file.exists():
            logger.error(f"Temp file not found for job {job_id}: {file_name}")
            job_tracker.update_job_status(
                job_id,
                JobStatus.FAILED,
                "Temporary file not found - may have been deleted"
            )
            return False

        file_ext = temp_file.suffix.lower()

        # Process the file
        await process_file_background(
            temp_file,
            file_name,
            file_ext,
            conversation_id,
            job_id,
            None
        )
        return True

    except Exception as e:
        logger.error(f"Error processing job {job_id}: {str(e)}")
        job_tracker.update_job_status(job_id, JobStatus.FAILED, str(e))
        return False


async def process_pending_jobs():
    """
    Main worker loop - polls for pending jobs and processes them in parallel
    """
    job_tracker = get_job_tracker()
    logger.info(f"Parallel job worker started - processing up to {MAX_CONCURRENT_JOBS} jobs concurrently...")

    # Track currently processing jobs
    active_tasks: Set[asyncio.Task] = set()

    while not shutdown_event.is_set():
        try:
            # Clean up finished tasks
            finished_tasks = {task for task in active_tasks if task.done()}
            for task in finished_tasks:
                try:
                    result = task.result()
                    logger.info(f"Task completed with result: {result}")
                except Exception as e:
                    logger.error(f"Task failed with error: {str(e)}")
            active_tasks -= finished_tasks

            # Check if we can process more jobs
            if len(active_tasks) < MAX_CONCURRENT_JOBS:
                # Get all pending jobs
                all_jobs = job_tracker.get_all_jobs()
                pending_jobs = [
                    job for job in all_jobs
                    if job['status'] == JobStatus.PENDING.value
                ]

                # Process up to MAX_CONCURRENT_JOBS
                slots_available = MAX_CONCURRENT_JOBS - len(active_tasks)
                jobs_to_process = pending_jobs[:slots_available]

                for job in jobs_to_process:
                    job_id = job['job_id']
                    file_name = job['file_name']
                    conversation_id = job['conversation_id']

                    logger.info(f"Starting job {job_id} for file: {file_name} ({len(active_tasks)+1}/{MAX_CONCURRENT_JOBS} active)")

                    # Create task for this job
                    task = asyncio.create_task(
                        process_single_job(job_id, file_name, conversation_id)
                    )
                    active_tasks.add(task)

            # Poll interval
            await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Error in worker loop: {str(e)}")
            await asyncio.sleep(5)

    # Wait for active tasks to complete
    if active_tasks:
        logger.info(f"Waiting for {len(active_tasks)} active tasks to complete...")
        await asyncio.gather(*active_tasks, return_exceptions=True)

    logger.info("Parallel job worker shut down gracefully")


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
