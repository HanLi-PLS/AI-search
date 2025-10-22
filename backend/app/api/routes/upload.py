"""
File upload API endpoints
"""
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List
import uuid
import time
from pathlib import Path
from datetime import datetime
import aiofiles
import os

from backend.app.models.schemas import UploadResponse, ErrorResponse
from backend.app.core.document_processor import DocumentProcessor
from backend.app.core.vector_store import get_vector_store
from backend.app.utils.s3_storage import get_s3_storage
from backend.app.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


def get_s3_key(file_id: str, filename: str) -> str:
    """Generate S3 key for uploaded file"""
    return f"{settings.S3_UPLOAD_PREFIX}{file_id}_{filename}"


@router.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """
    Upload and process a document

    Args:
        file: Uploaded file

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

        # Generate unique file ID
        file_id = str(uuid.uuid4())
        upload_date = datetime.now()

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

        # Add to vector store
        vector_store = get_vector_store()
        chunks_created = vector_store.add_documents(
            documents=documents,
            file_id=file_id,
            file_name=file.filename,
            file_size=file_size,
            upload_date=upload_date
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
