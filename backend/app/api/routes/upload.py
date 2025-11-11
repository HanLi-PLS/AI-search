"""
File upload API endpoints
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from typing import List
import uuid
import time
from pathlib import Path
from datetime import datetime
import aiofiles
import os
import zipfile
import io
import asyncio
from concurrent.futures import ThreadPoolExecutor

from backend.app.models.schemas import UploadResponse, ErrorResponse, JobStatusResponse
from backend.app.core.document_processor import DocumentProcessor
from backend.app.core.vector_store import get_vector_store
from backend.app.utils.s3_storage import get_s3_storage
from backend.app.config import settings
from backend.app.core.job_tracker import get_job_tracker, JobStatus
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


def get_s3_key(file_id: str, filename: str) -> str:
    """Generate S3 key for uploaded file - uses folder per upload to preserve original filename"""
    return f"{settings.S3_UPLOAD_PREFIX}{file_id}/{filename}"


def decode_zip_filename(file_info: zipfile.ZipInfo) -> str:
    """
    Decode zip filename with proper encoding handling for Chinese characters

    Args:
        file_info: ZipInfo object from zipfile

    Returns:
        Properly decoded filename
    """
    filename = file_info.filename
    try:
        # Try to encode as CP437 and decode as UTF-8 (common for files zipped on Windows)
        filename = file_info.filename.encode('cp437').decode('utf-8')
    except (UnicodeDecodeError, UnicodeEncodeError):
        try:
            # Try GB2312/GBK encoding (common for Chinese Windows systems)
            filename = file_info.filename.encode('cp437').decode('gbk')
        except (UnicodeDecodeError, UnicodeEncodeError):
            # If all else fails, keep the original filename
            pass
    return filename


def should_skip_file(filename: str) -> bool:
    """
    Check if file should be skipped during extraction

    Args:
        filename: File path to check

    Returns:
        True if file should be skipped
    """
    # Skip .DS_Store files and __MACOSX folder
    return filename.endswith('.DS_Store') or filename.startswith('__MACOSX/') or filename.endswith('/')


async def process_single_file(
    file_path: Path,
    filename: str,
    file_id: str,
    conversation_id: str
) -> dict:
    """
    Process a single file and add to vector store

    Args:
        file_path: Path to file
        filename: Original filename
        file_id: Unique file ID
        conversation_id: Conversation ID

    Returns:
        Processing result dictionary
    """
    try:
        file_size = file_path.stat().st_size
        upload_date = datetime.now()

        # Process document
        processor = DocumentProcessor()
        documents = processor.process_file(file_path, filename)

        # Add to vector store
        vector_store = get_vector_store()
        chunks_created = vector_store.add_documents(
            documents=documents,
            file_id=file_id,
            file_name=filename,
            file_size=file_size,
            upload_date=upload_date,
            conversation_id=conversation_id
        )

        logger.info(f"Processed file: {filename}, {chunks_created} chunks created")

        return {
            'success': True,
            'filename': filename,
            'file_id': file_id,
            'chunks_created': chunks_created
        }
    except Exception as e:
        logger.error(f"Error processing file {filename}: {str(e)}")
        return {
            'success': False,
            'filename': filename,
            'error': str(e)
        }


async def extract_and_process_zip(
    zip_content: bytes,
    zip_filename: str,
    conversation_id: str
) -> List[dict]:
    """
    Extract zip file and process all files in parallel

    Args:
        zip_content: Zip file content as bytes
        zip_filename: Original zip filename
        conversation_id: Conversation ID

    Returns:
        List of processing results
    """
    results = []
    temp_files = []

    try:
        # Extract zip file
        buffer = io.BytesIO(zip_content)

        with zipfile.ZipFile(buffer, 'r') as zip_ref:
            # Create temporary extraction directory
            extract_dir = settings.UPLOAD_DIR / f"zip_{uuid.uuid4()}"
            extract_dir.mkdir(parents=True, exist_ok=True)

            # Extract all valid files
            for file_info in zip_ref.infolist():
                # Decode filename properly
                filename = decode_zip_filename(file_info)

                # Skip unwanted files
                if should_skip_file(filename) or file_info.is_dir():
                    continue

                # Check file extension
                file_ext = Path(filename).suffix.lower()
                if file_ext not in settings.SUPPORTED_EXTENSIONS or file_ext == '.zip':
                    logger.info(f"Skipping unsupported file in zip: {filename}")
                    continue

                # Preserve folder structure in filename to avoid collisions
                # Convert "folder1/subfolder/document.pdf" to "folder1_subfolder_document.pdf"
                safe_filename = filename.replace('/', '_').replace('\\', '_')

                # Extract file
                extracted_path = extract_dir / safe_filename
                with zip_ref.open(file_info) as source:
                    with open(extracted_path, 'wb') as target:
                        target.write(source.read())

                # Use safe_filename (with folder path) for tracking and metadata
                temp_files.append((extracted_path, safe_filename))

            logger.info(f"Extracted {len(temp_files)} files from {zip_filename}")

            # Process all files in parallel
            tasks = [
                process_single_file(
                    file_path=file_path,
                    filename=filename,
                    file_id=str(uuid.uuid4()),
                    conversation_id=conversation_id
                )
                for file_path, filename in temp_files
            ]

            results = await asyncio.gather(*tasks)

    finally:
        # Clean up temporary files
        for file_path, _ in temp_files:
            try:
                if file_path.exists():
                    os.remove(file_path)
            except Exception as e:
                logger.error(f"Error removing temp file {file_path}: {str(e)}")

        # Remove extraction directory
        if 'extract_dir' in locals() and extract_dir.exists():
            try:
                extract_dir.rmdir()
            except Exception as e:
                logger.error(f"Error removing extraction directory: {str(e)}")

    return results


async def process_file_background(
    file_path: Path,
    filename: str,
    file_ext: str,
    conversation_id: str,
    job_id: str
):
    """
    Background task to process uploaded file

    Args:
        file_path: Path to uploaded file
        filename: Original filename
        file_ext: File extension
        conversation_id: Conversation ID
        job_id: Job tracking ID
    """
    job_tracker = get_job_tracker()
    job_tracker.update_job_status(job_id, JobStatus.PROCESSING)

    try:
        # Read file content
        with open(file_path, 'rb') as f:
            content = f.read()

        # Handle zip files
        if file_ext == '.zip':
            logger.info(f"[Job {job_id}] Processing zip file: {filename}")
            job = job_tracker.get_job(job_id)
            if job:
                # Extract and count files first
                buffer = io.BytesIO(content)
                with zipfile.ZipFile(buffer, 'r') as zip_ref:
                    valid_files = sum(
                        1 for file_info in zip_ref.infolist()
                        if not should_skip_file(decode_zip_filename(file_info))
                        and not file_info.is_dir()
                        and Path(decode_zip_filename(file_info)).suffix.lower() in settings.SUPPORTED_EXTENSIONS
                    )
                job.total_files = valid_files

            # Process zip
            results = await extract_and_process_zip(content, filename, conversation_id)

            # Update job with results
            for result in results:
                job_tracker.add_file_result(job_id, result)

            successful = sum(1 for r in results if r.get('success'))
            failed = sum(1 for r in results if not r.get('success'))

            logger.info(f"[Job {job_id}] Zip processed: {successful} successful, {failed} failed")
            job_tracker.update_job_status(job_id, JobStatus.COMPLETED)

        else:
            # Handle single file
            logger.info(f"[Job {job_id}] Processing single file: {filename}")
            job = job_tracker.get_job(job_id)
            if job:
                job.total_files = 1

            file_id = str(uuid.uuid4())
            upload_date = datetime.now()
            file_size = len(content)

            # Process document
            processor = DocumentProcessor()
            documents = processor.process_file(file_path, filename)

            # Add to vector store
            vector_store = get_vector_store()
            chunks_created = vector_store.add_documents(
                documents=documents,
                file_id=file_id,
                file_name=filename,
                file_size=file_size,
                upload_date=upload_date,
                conversation_id=conversation_id
            )

            result = {
                'success': True,
                'filename': filename,
                'file_id': file_id,
                'chunks_created': chunks_created
            }

            job_tracker.add_file_result(job_id, result)
            job_tracker.update_job_status(job_id, JobStatus.COMPLETED)
            logger.info(f"[Job {job_id}] File processed: {chunks_created} chunks created")

    except Exception as e:
        error_msg = str(e)
        logger.error(f"[Job {job_id}] Error processing file: {error_msg}")
        job_tracker.update_job_status(job_id, JobStatus.FAILED, error_msg)

    finally:
        # Clean up temp file
        try:
            if file_path.exists():
                os.remove(file_path)
                logger.info(f"[Job {job_id}] Cleaned up temp file: {file_path}")
        except Exception as e:
            logger.error(f"[Job {job_id}] Error cleaning up temp file: {str(e)}")


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    conversation_id: str = Form(None)
):
    """
    Upload and process a document (or zip file containing multiple documents)
    Processing happens in the background - returns immediately with job_id

    Args:
        background_tasks: FastAPI background tasks
        file: Uploaded file
        conversation_id: Optional conversation ID to associate file with

    Returns:
        Upload response with job_id for tracking
    """
    try:
        # Validate file extension
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in settings.SUPPORTED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file_ext}. Supported types: {', '.join(settings.SUPPORTED_EXTENSIONS)}"
            )

        # Check file size
        content = await file.read()
        file_size = len(content)
        max_size_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024

        if file_size > max_size_bytes:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: {settings.MAX_FILE_SIZE_MB}MB"
            )

        # Generate job ID and file ID
        job_id = str(uuid.uuid4())
        file_id = str(uuid.uuid4())

        # Save file temporarily
        temp_file_path = settings.UPLOAD_DIR / f"{file_id}_{file.filename}"
        async with aiofiles.open(temp_file_path, 'wb') as f:
            await f.write(content)

        logger.info(f"File uploaded: {file.filename} ({file_size} bytes), job_id: {job_id}")

        # Create job tracker entry
        job_tracker = get_job_tracker()
        job_tracker.create_job(job_id, file.filename, conversation_id)

        # Add background task
        background_tasks.add_task(
            process_file_background,
            temp_file_path,
            file.filename,
            file_ext,
            conversation_id,
            job_id
        )

        return UploadResponse(
            success=True,
            message="File upload successful. Processing in background.",
            file_name=file.filename,
            file_id=file_id,
            job_id=job_id,
            status="processing"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")


@router.post("/upload-batch", response_model=List[UploadResponse])
async def upload_multiple_files(files: List[UploadFile] = File(...)):
    """
    Upload and process multiple documents

    Args:
        files: List of uploaded files

    Returns:
        List of upload responses
    """
    results = []

    for file in files:
        try:
            result = await upload_file(file)
            results.append(result)
        except Exception as e:
            logger.error(f"Error processing {file.filename}: {str(e)}")
            results.append(
                UploadResponse(
                    success=False,
                    message=f"Error: {str(e)}",
                    file_name=file.filename
                )
            )

    return results


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Get status of a background processing job

    Args:
        job_id: Job identifier

    Returns:
        Job status information
    """
    job_tracker = get_job_tracker()
    job = job_tracker.get_job(job_id)

    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job not found: {job_id}"
        )

    return JobStatusResponse(**job.to_dict())


@router.get("/jobs", response_model=List[JobStatusResponse])
async def list_jobs(conversation_id: str = None):
    """
    List all jobs, optionally filtered by conversation

    Args:
        conversation_id: Optional conversation ID to filter by

    Returns:
        List of job status information
    """
    from typing import Optional
    job_tracker = get_job_tracker()
    jobs = job_tracker.get_all_jobs(conversation_id)
    return [JobStatusResponse(**job) for job in jobs]
