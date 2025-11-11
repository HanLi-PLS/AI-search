"""
File upload API endpoints
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
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

from backend.app.models.schemas import UploadResponse, ErrorResponse
from backend.app.core.document_processor import DocumentProcessor
from backend.app.core.vector_store import get_vector_store
from backend.app.utils.s3_storage import get_s3_storage
from backend.app.config import settings
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

                # Extract file
                extracted_path = extract_dir / Path(filename).name
                with zip_ref.open(file_info) as source:
                    with open(extracted_path, 'wb') as target:
                        target.write(source.read())

                temp_files.append((extracted_path, Path(filename).name))

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


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    conversation_id: str = Form(None)
):
    """
    Upload and process a document (or zip file containing multiple documents)

    Args:
        file: Uploaded file
        conversation_id: Optional conversation ID to associate file with

    Returns:
        Upload response with processing details
    """
    start_time = time.time()

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

        # Handle zip files differently - extract and process in parallel
        if file_ext == '.zip':
            logger.info(f"Processing zip file: {file.filename}")

            results = await extract_and_process_zip(
                zip_content=content,
                zip_filename=file.filename,
                conversation_id=conversation_id
            )

            # Calculate totals
            total_chunks = sum(r.get('chunks_created', 0) for r in results if r.get('success'))
            successful = sum(1 for r in results if r.get('success'))
            failed = sum(1 for r in results if not r.get('success'))

            processing_time = time.time() - start_time

            logger.info(
                f"Zip file processed: {file.filename}, "
                f"{successful} files successful, {failed} failed, "
                f"{total_chunks} total chunks"
            )

            message = f"Zip file processed: {successful} files successful"
            if failed > 0:
                message += f", {failed} files failed"

            return UploadResponse(
                success=True,
                message=message,
                file_name=file.filename,
                file_id=str(uuid.uuid4()),
                chunks_created=total_chunks,
                processing_time=round(processing_time, 2)
            )

        # Generate unique file ID
        file_id = str(uuid.uuid4())
        upload_date = datetime.now()

        logger.info(f"File uploaded: {file.filename} for conversation: {conversation_id or 'global'} (type: {type(conversation_id)})")

        # Save file temporarily for processing
        temp_file_path = settings.UPLOAD_DIR / f"{file_id}_{file.filename}"
        async with aiofiles.open(temp_file_path, 'wb') as f:
            await f.write(content)

        logger.info(f"File uploaded: {file.filename} ({file_size} bytes)")

        # Upload to S3 if enabled
        s3_key = None
        if settings.USE_S3_STORAGE and settings.AWS_S3_BUCKET:
            s3_storage = get_s3_storage(
                bucket_name=settings.AWS_S3_BUCKET,
                region_name=settings.AWS_REGION
            )
            if s3_storage:
                s3_key = get_s3_key(file_id, file.filename)
                upload_success = s3_storage.upload_file(temp_file_path, s3_key)
                if upload_success:
                    logger.info(f"File uploaded to S3: s3://{settings.AWS_S3_BUCKET}/{s3_key}")
                else:
                    logger.warning(f"Failed to upload file to S3: {file.filename}")

        # Process document
        processor = DocumentProcessor()
        documents = processor.process_file(temp_file_path, file.filename)

        # Add to vector store with conversation association
        vector_store = get_vector_store()
        chunks_created = vector_store.add_documents(
            documents=documents,
            file_id=file_id,
            file_name=file.filename,
            file_size=file_size,
            upload_date=upload_date,
            conversation_id=conversation_id
        )

        # Clean up: remove local file if using S3, otherwise keep it
        if settings.USE_S3_STORAGE and s3_key and temp_file_path.exists():
            os.remove(temp_file_path)
            logger.info(f"Removed local file (using S3): {temp_file_path}")

        processing_time = time.time() - start_time

        logger.info(f"File processed successfully: {file.filename}, {chunks_created} chunks created")

        storage_info = f"stored in S3: s3://{settings.AWS_S3_BUCKET}/{s3_key}" if s3_key else "stored locally"

        return UploadResponse(
            success=True,
            message=f"File uploaded and processed successfully ({storage_info})",
            file_name=file.filename,
            file_id=file_id,
            chunks_created=chunks_created,
            processing_time=round(processing_time, 2)
        )

    except HTTPException:
        # Clean up temp file if exists
        if 'temp_file_path' in locals() and temp_file_path.exists():
            os.remove(temp_file_path)
        raise

    except Exception as e:
        # Clean up temp file if exists
        if 'temp_file_path' in locals() and temp_file_path.exists():
            os.remove(temp_file_path)

        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


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
