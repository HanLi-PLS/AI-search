"""
File upload API endpoints
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request
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

from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.app.models.schemas import UploadResponse, ErrorResponse, JobStatusResponse
from backend.app.core.document_processor import DocumentProcessor
from backend.app.core.vector_store import get_vector_store
from backend.app.utils.s3_storage import get_s3_storage
from backend.app.config import settings
from backend.app.core.job_tracker import get_job_tracker, JobStatus
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize limiter for this module
limiter = Limiter(key_func=get_remote_address)

# Thread pool for parallel file processing
# Use more workers to handle multiple concurrent users
# Each user's uploads will share these workers
_thread_pool = ThreadPoolExecutor(max_workers=16)


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
    Check if file should be skipped during extraction or upload

    Args:
        filename: File path to check

    Returns:
        True if file should be skipped
    """
    # Get just the filename without path
    base_filename = Path(filename).name

    # Skip directories
    if filename.endswith('/'):
        return True

    # Skip system/hidden files
    if base_filename.startswith('.'):  # Hidden files (.DS_Store, .git, etc.)
        return True

    # Skip Microsoft Office temporary files
    if base_filename.startswith('~$'):  # Excel/Word temporary files
        return True

    # Skip __MACOSX folder (macOS zip metadata)
    if '__MACOSX' in filename:
        return True

    return False


def _process_single_file_sync(
    file_path: Path,
    filename: str,
    file_id: str,
    conversation_id: str
) -> dict:
    """
    Synchronous file processing function (runs in thread pool)

    Args:
        file_path: Path to file
        filename: Original filename
        file_id: Unique file ID
        conversation_id: Conversation ID

    Returns:
        Processing result dictionary
    """
    try:
        # Check if file exists and is readable
        if not file_path.exists():
            error_msg = "File not found or inaccessible"
            logger.error(f"Error processing {filename}: {error_msg}")
            return {
                'success': False,
                'filename': filename,
                'error': error_msg,
                'error_type': 'file_not_found'
            }

        file_size = file_path.stat().st_size

        # Check if file is empty
        if file_size == 0:
            error_msg = "File is empty (0 bytes)"
            logger.warning(f"Skipping empty file: {filename}")
            return {
                'success': False,
                'filename': filename,
                'error': error_msg,
                'error_type': 'empty_file'
            }

        upload_date = datetime.now()

        # Process document (CPU-bound operation)
        processor = DocumentProcessor()
        documents = processor.process_file(file_path, filename)

        # Check if any content was extracted
        if not documents or len(documents) == 0:
            error_msg = "No content could be extracted from file"
            logger.warning(f"No content extracted from: {filename}")
            return {
                'success': False,
                'filename': filename,
                'error': error_msg,
                'error_type': 'no_content'
            }

        # Add to vector store (I/O-bound operation)
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
    except FileNotFoundError as e:
        error_msg = "File not found"
        logger.error(f"File not found: {filename}")
        return {
            'success': False,
            'filename': filename,
            'error': error_msg,
            'error_type': 'file_not_found'
        }
    except PermissionError as e:
        error_msg = "Permission denied reading file"
        logger.error(f"Permission denied: {filename}")
        return {
            'success': False,
            'filename': filename,
            'error': error_msg,
            'error_type': 'permission_denied'
        }
    except UnicodeDecodeError as e:
        error_msg = "File encoding error - file may be corrupted or in unsupported encoding"
        logger.error(f"Encoding error in {filename}: {str(e)}")
        return {
            'success': False,
            'filename': filename,
            'error': error_msg,
            'error_type': 'encoding_error'
        }
    except Exception as e:
        # Categorize error based on error message
        error_str = str(e).lower()
        if 'corrupt' in error_str or 'damaged' in error_str or 'invalid' in error_str:
            error_type = 'corrupted_file'
            error_msg = f"File appears to be corrupted or damaged: {str(e)}"
        elif 'unsupported' in error_str or 'not supported' in error_str:
            error_type = 'unsupported_format'
            error_msg = f"Unsupported file format or feature: {str(e)}"
        elif 'password' in error_str or 'encrypted' in error_str:
            error_type = 'encrypted_file'
            error_msg = "File is password-protected or encrypted"
        else:
            error_type = 'processing_error'
            error_msg = f"Error processing file: {str(e)}"

        logger.error(f"Error processing file {filename}: {error_msg}")
        return {
            'success': False,
            'filename': filename,
            'error': error_msg,
            'error_type': error_type
        }


async def process_single_file(
    file_path: Path,
    filename: str,
    file_id: str,
    conversation_id: str
) -> dict:
    """
    Process a single file and add to vector store (async wrapper for thread pool)

    Args:
        file_path: Path to file
        filename: Original filename
        file_id: Unique file ID
        conversation_id: Conversation ID

    Returns:
        Processing result dictionary
    """
    # Run the synchronous processing in thread pool for true parallelism
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        _thread_pool,
        _process_single_file_sync,
        file_path,
        filename,
        file_id,
        conversation_id
    )


async def extract_and_process_zip(
    zip_content: bytes,
    zip_filename: str,
    conversation_id: str,
    job_id: str = None
) -> List[dict]:
    """
    Extract zip file and process all files in parallel

    Args:
        zip_content: Zip file content as bytes
        zip_filename: Original zip filename
        conversation_id: Conversation ID
        job_id: Optional job ID for cancellation checks

    Returns:
        List of processing results
    """
    results = []
    temp_files = []
    job_tracker = get_job_tracker() if job_id else None

    try:
        # Check if cancelled before starting
        if job_tracker and job_tracker.is_job_cancelled(job_id):
            logger.info(f"[Job {job_id}] Zip extraction cancelled before starting")
            return []

        # Extract zip file
        buffer = io.BytesIO(zip_content)

        with zipfile.ZipFile(buffer, 'r') as zip_ref:
            # Create temporary extraction directory
            extract_dir = settings.UPLOAD_DIR / f"zip_{uuid.uuid4()}"
            extract_dir.mkdir(parents=True, exist_ok=True)

            # Extract all valid files
            for file_info in zip_ref.infolist():
                try:
                    # Decode filename properly
                    filename = decode_zip_filename(file_info)

                    # Skip directories
                    if file_info.is_dir():
                        continue

                    # Skip system/unwanted files with notification
                    if should_skip_file(filename):
                        logger.info(f"Skipping system file in zip: {filename}")
                        results.append({
                            'success': False,
                            'filename': filename,
                            'error': 'System file (skipped)',
                            'error_type': 'skipped_system_file'
                        })
                        continue

                    # Check file extension
                    file_ext = Path(filename).suffix.lower()
                    if file_ext not in settings.SUPPORTED_EXTENSIONS:
                        logger.info(f"Skipping unsupported file type in zip: {filename}")
                        results.append({
                            'success': False,
                            'filename': filename,
                            'error': f'Unsupported file type: {file_ext or "no extension"}',
                            'error_type': 'unsupported_file_type'
                        })
                        continue

                    if file_ext == '.zip':
                        logger.info(f"Skipping nested zip file: {filename}")
                        results.append({
                            'success': False,
                            'filename': filename,
                            'error': 'Nested zip files are not supported',
                            'error_type': 'nested_zip'
                        })
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

                except Exception as e:
                    # Log extraction error but continue with other files
                    logger.error(f"Failed to extract {filename} from zip: {str(e)}")
                    # Add to results as failed extraction
                    results.append({
                        'success': False,
                        'filename': filename,
                        'error': f"Failed to extract from zip: {str(e)}",
                        'error_type': 'extraction_error'
                    })

            logger.info(f"Extracted {len(temp_files)} files from {zip_filename}")

            # Check if cancelled after extraction
            if job_tracker and job_tracker.is_job_cancelled(job_id):
                logger.info(f"[Job {job_id}] Zip processing cancelled after extraction")
                return results

            # Process ALL files in parallel for maximum speed (like original fast implementation)
            logger.info(f"[Job {job_id}] Processing {len(temp_files)} files in parallel...")
            tasks = [
                process_single_file(
                    file_path=file_path,
                    filename=filename,
                    file_id=str(uuid.uuid4()),
                    conversation_id=conversation_id
                )
                for file_path, filename in temp_files
            ]

            # Process all files concurrently (asyncio.gather for max speed)
            processing_results = await asyncio.gather(*tasks)
            results.extend(processing_results)
            logger.info(f"[Job {job_id}] Completed processing {len(temp_files)} files in parallel")

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
    job_id: str,
    relative_path: str = None
):
    """
    Background task to process uploaded file

    Args:
        file_path: Path to uploaded file
        filename: Original filename
        file_ext: File extension
        conversation_id: Conversation ID
        job_id: Job tracking ID
        relative_path: Relative path from folder upload (e.g., 'folder/subfolder/file.txt')
    """
    job_tracker = get_job_tracker()

    # Check if cancelled before starting
    if job_tracker.is_job_cancelled(job_id):
        logger.info(f"[Job {job_id}] Job cancelled before processing started")
        # Clean up temp file
        try:
            if file_path.exists():
                os.remove(file_path)
        except Exception as e:
            logger.error(f"Error cleaning up cancelled job file: {str(e)}")
        return

    job_tracker.update_job_status(job_id, JobStatus.PROCESSING)

    try:
        # Read file content
        with open(file_path, 'rb') as f:
            content = f.read()

        # Check for cancellation after reading file
        if job_tracker.is_job_cancelled(job_id):
            logger.info(f"[Job {job_id}] Job cancelled after reading file")
            return

        # Handle zip files
        if file_ext == '.zip':
            logger.info(f"[Job {job_id}] Processing zip file: {filename}")
            # Extract and count files first
            buffer = io.BytesIO(content)
            with zipfile.ZipFile(buffer, 'r') as zip_ref:
                valid_files = sum(
                    1 for file_info in zip_ref.infolist()
                    if not should_skip_file(decode_zip_filename(file_info))
                    and not file_info.is_dir()
                    and Path(decode_zip_filename(file_info)).suffix.lower() in settings.SUPPORTED_EXTENSIONS
                )
            job_tracker.update_total_files(job_id, valid_files)

            # Process zip with cancellation support
            results = await extract_and_process_zip(content, filename, conversation_id, job_id)

            # Update job with results
            for result in results:
                job_tracker.add_file_result(job_id, result)

            successful = sum(1 for r in results if r.get('success'))
            failed = sum(1 for r in results if not r.get('success'))
            cancelled = sum(1 for r in results if r.get('error_type') == 'cancelled')

            # Check final status
            if job_tracker.is_job_cancelled(job_id):
                logger.info(f"[Job {job_id}] Zip processing cancelled: {successful} successful, {failed} failed, {cancelled} cancelled")
                # Status already set to CANCELLED by cancel_job
            else:
                logger.info(f"[Job {job_id}] Zip processed: {successful} successful, {failed} failed")
                job_tracker.update_job_status(job_id, JobStatus.COMPLETED)

        else:
            # Handle single file
            # Use relative_path as display name if provided (from folder upload)
            display_name = relative_path if relative_path else filename
            logger.info(f"[Job {job_id}] Processing single file: {display_name}")
            job_tracker.update_total_files(job_id, 1)

            # Check for cancellation before processing
            if job_tracker.is_job_cancelled(job_id):
                logger.info(f"[Job {job_id}] Job cancelled before document processing")
                return

            file_id = str(uuid.uuid4())

            # Process file using thread pool to avoid blocking event loop
            # This allows multiple users to upload/search simultaneously
            result = await process_single_file(
                file_path=file_path,
                filename=display_name,
                file_id=file_id,
                conversation_id=conversation_id
            )

            # Check for cancellation after processing
            if job_tracker.is_job_cancelled(job_id):
                logger.info(f"[Job {job_id}] Job cancelled after document processing")
                return

            job_tracker.add_file_result(job_id, result)

            if result.get('success'):
                job_tracker.update_job_status(job_id, JobStatus.COMPLETED)
                logger.info(f"[Job {job_id}] File processed: {result.get('chunks_created', 0)} chunks created")
            else:
                job_tracker.update_job_status(job_id, JobStatus.FAILED, result.get('error', 'Unknown error'))
                logger.error(f"[Job {job_id}] File processing failed: {result.get('error', 'Unknown error')}")

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
@limiter.limit(settings.RATE_LIMIT_UPLOAD)
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    conversation_id: str = Form(None),
    relative_path: str = Form(None)
):
    """
    Upload and process a document (or zip file containing multiple documents)
    Processing happens in background using asyncio - fast parallel processing

    Args:
        file: Uploaded file
        conversation_id: Optional conversation ID to associate file with
        relative_path: Optional relative path from folder upload (e.g., 'folder/subfolder/file.txt')

    Returns:
        Upload response with job_id for tracking
    """
    try:
        # Skip temporary/system files
        if should_skip_file(file.filename):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot upload system or temporary files: {file.filename}"
            )

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
        # Sanitize filename for temp storage - replace path separators with underscores
        safe_filename = file.filename.replace('/', '_').replace('\\', '_')
        temp_file_path = settings.UPLOAD_DIR / f"{file_id}_{safe_filename}"
        async with aiofiles.open(temp_file_path, 'wb') as f:
            await f.write(content)

        # Use relative_path for display name if provided, otherwise just the filename
        display_name = relative_path if relative_path else file.filename

        logger.info(f"File uploaded: {display_name} ({file_size} bytes), job_id: {job_id}")

        # Create job tracker entry (status: PENDING)
        job_tracker = get_job_tracker()
        job_tracker.create_job(job_id, display_name, conversation_id)

        # Process file directly in background (fast parallel processing with asyncio)
        # This is MUCH faster than queuing for a worker
        asyncio.create_task(
            process_file_background(
                temp_file_path,
                file.filename,
                file_ext,
                conversation_id,
                job_id,
                relative_path
            )
        )

        logger.info(f"Job {job_id} started with async background processing")

        return UploadResponse(
            success=True,
            message="File upload successful. Processing in background.",
            file_name=display_name,
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


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    """
    Cancel a running or pending job

    Args:
        job_id: Job identifier

    Returns:
        Success response
    """
    job_tracker = get_job_tracker()
    success = job_tracker.cancel_job(job_id)

    if not success:
        raise HTTPException(
            status_code=400,
            detail="Cannot cancel job. Job may not exist or is already completed/failed/cancelled."
        )

    return {"success": True, "message": f"Job {job_id} has been cancelled"}
