"""
Search API endpoints
"""
from fastapi import APIRouter, HTTPException, Request, BackgroundTasks, Depends
import time
from typing import List, Optional
import uuid
import asyncio

from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.app.models.schemas import (
    SearchRequest, SearchResponse, SearchResult,
    DocumentListResponse, DocumentInfo, DeleteResponse,
    HealthResponse
)
from backend.app.core.vector_store import get_vector_store
from backend.app.core.answer_generator import get_answer_generator
from backend.app.core.search_job_tracker import get_search_job_tracker, SearchJobStatus
from backend.app.config import settings
from backend.app.models.user import User
from backend.app.api.routes.auth import get_current_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize limiter for this module
limiter = Limiter(key_func=get_remote_address)

# Modes that require background processing (long-running)
ASYNC_SEARCH_MODES = ["reasoning_gpt5", "reasoning_gemini", "deep_research"]

# Search modes that are always async (long-running regardless of reasoning mode)
ASYNC_ONLY_SEARCH_MODES = ["sectional_analysis"]


def process_search_job(job_id: str, search_request_dict: dict):
    """
    Background worker to process long-running search jobs

    Args:
        job_id: Job identifier
        search_request_dict: Dictionary representation of SearchRequest
    """
    job_tracker = get_search_job_tracker()

    try:
        # Update status to processing
        job_tracker.update_status(job_id, SearchJobStatus.PROCESSING)
        job_tracker.update_progress(job_id, 10, "Starting search...")

        start_time = time.time()

        # Reconstruct SearchRequest from dict
        search_request = SearchRequest(**search_request_dict)

        results = []
        search_results = []
        selected_mode = None
        mode_reasoning = None

        # Handle auto mode - classify the query first
        actual_search_mode = search_request.search_mode
        if search_request.search_mode == "auto":
            logger.info(f"[JOB {job_id}] Auto mode detected, classifying query...")
            job_tracker.update_progress(job_id, 15, "Classifying query...")
            answer_generator = get_answer_generator()
            selected_mode, mode_reasoning = answer_generator.classify_query(search_request.query)
            actual_search_mode = selected_mode
            logger.info(f"[JOB {job_id}] Auto mode selected: {selected_mode}")

        # Check if job was cancelled
        if job_tracker.is_job_cancelled(job_id):
            logger.info(f"[JOB {job_id}] Job was cancelled, stopping")
            return

        # Only search files if mode is not online_only
        if actual_search_mode != "online_only":
            logger.info(f"[JOB {job_id}] Searching documents...")
            job_tracker.update_progress(job_id, 20, "Searching documents...")

            vector_store = get_vector_store()
            results = vector_store.search(
                query=search_request.query,
                top_k=search_request.top_k,
                file_types=search_request.file_types,
                date_from=search_request.date_from,
                date_to=search_request.date_to,
                conversation_id=search_request.conversation_id
            )

            search_results = [
                {
                    "content": result["content"],
                    "score": result["score"],
                    "metadata": result["metadata"],
                    "retrieval_method": result.get("retrieval_method", "Dense")
                }
                for result in results
            ]

        # Check if job was cancelled
        if job_tracker.is_job_cancelled(job_id):
            logger.info(f"[JOB {job_id}] Job was cancelled, stopping")
            return

        # Generate final answer using GPT with search mode support
        logger.info(f"[JOB {job_id}] Generating answer with {actual_search_mode} mode...")
        job_tracker.update_progress(job_id, 25, f"Generating answer ({actual_search_mode})...")

        answer_generator = get_answer_generator()

        # Convert conversation history to dict format if provided
        conversation_history_dict = None
        if search_request.conversation_history:
            conversation_history_dict = [turn.dict() for turn in search_request.conversation_history]

        # Handle sectional_analysis mode specially
        if actual_search_mode == "sectional_analysis":
            logger.info(f"[JOB {job_id}] Using sectional analysis (divide and conquer) mode...")

            # Define progress callback for sectional processing
            def progress_callback(progress: int, total: int, step_name: str):
                # Scale progress: 25-95% for sectional processing
                scaled_progress = 25 + int((progress / total) * 70)
                job_tracker.update_progress(job_id, scaled_progress, step_name)

            answer, online_search_response, extracted_info = answer_generator.generate_sectional_answer(
                query=search_request.query,
                search_results=results,
                reasoning_mode=search_request.reasoning_mode,
                conversation_history=conversation_history_dict,
                progress_callback=progress_callback
            )
        else:
            answer, online_search_response, extracted_info = answer_generator.generate_answer(
                query=search_request.query,
                search_results=results,
                search_mode=actual_search_mode,
                reasoning_mode=search_request.reasoning_mode,
                priority_order=search_request.priority_order,
                conversation_history=conversation_history_dict
            )

        # Update progress to near completion
        job_tracker.update_progress(job_id, 95, "Finalizing results...")

        # Check if job was cancelled
        if job_tracker.is_job_cancelled(job_id):
            logger.info(f"[JOB {job_id}] Job was cancelled after answer generation")
            return

        processing_time = time.time() - start_time

        # Save results
        logger.info(f"[JOB {job_id}] Saving results...")

        # Serialize complex objects to JSON strings for database storage
        import json as json_module
        extracted_info_str = json_module.dumps(extracted_info, ensure_ascii=False) if extracted_info else None
        online_search_response_str = json_module.dumps(online_search_response, ensure_ascii=False) if online_search_response else None

        job_tracker.save_results(
            job_id=job_id,
            answer=answer,
            results=search_results,
            total_results=len(search_results),
            processing_time=processing_time,
            extracted_info=extracted_info_str,
            online_search_response=online_search_response_str
        )

        logger.info(f"[JOB {job_id}] Search job completed successfully in {processing_time:.1f}s")

    except Exception as e:
        logger.error(f"[JOB {job_id}] Error processing search job: {str(e)}", exc_info=True)
        job_tracker.update_status(job_id, SearchJobStatus.FAILED, str(e))


@router.post("/search")
@limiter.limit(settings.RATE_LIMIT_SEARCH)
async def search_documents(
    request: Request,
    search_request: SearchRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """
    Search documents using semantic similarity and/or online search, then generate answer

    For long-running reasoning modes (reasoning_gpt5, deep_research), creates a background job
    and returns immediately with job_id. For other modes, processes synchronously.

    Args:
        request: FastAPI Request object (required for rate limiting)
        search_request: Search request with query, search_mode, and filters
        background_tasks: FastAPI BackgroundTasks for async processing
        current_user: Authenticated user (from JWT token)

    Returns:
        Search results with GPT-generated answer (sync mode) or job_id (async mode)
    """
    # Check if this is a long-running search that should be processed in background
    # Async modes: certain reasoning modes OR sectional_analysis search mode
    is_async_mode = (
        search_request.reasoning_mode in ASYNC_SEARCH_MODES or
        search_request.search_mode in ASYNC_ONLY_SEARCH_MODES
    )

    if is_async_mode:
        # Create background job for long-running search
        job_id = f"search_{uuid.uuid4().hex}"
        job_tracker = get_search_job_tracker()

        logger.info(f"Creating background job {job_id} for {search_request.reasoning_mode} mode")

        # Serialize priority_order (it's a list, but DB expects string)
        import json as json_module
        priority_order_str = json_module.dumps(search_request.priority_order) if search_request.priority_order else None

        # Create job in database
        job_tracker.create_job(
            job_id=job_id,
            query=search_request.query,
            search_mode=search_request.search_mode,
            reasoning_mode=search_request.reasoning_mode,
            conversation_id=search_request.conversation_id,
            user_id=current_user.id,
            top_k=search_request.top_k,
            priority_order=priority_order_str
        )

        # Convert SearchRequest to dict for background processing
        search_request_dict = search_request.dict()

        # Add background task
        background_tasks.add_task(process_search_job, job_id, search_request_dict)

        # Return immediately with job_id
        # Estimate time based on mode
        if search_request.search_mode == "sectional_analysis":
            estimated_time = "10-20 minutes (multi-section processing)"
        elif search_request.reasoning_mode == "reasoning_gpt5":
            estimated_time = "5-10 minutes"
        else:
            estimated_time = "15-30 minutes"
        return {
            "success": True,
            "job_id": job_id,
            "message": f"Search is processing in background. Poll /api/search-jobs/{job_id} for status.",
            "estimated_time": estimated_time,
            "is_async": True
        }

    # Synchronous processing for fast modes (non_reasoning, reasoning)
    start_time = time.time()

    try:
        results = []
        search_results = []
        selected_mode = None
        mode_reasoning = None

        # Handle auto mode - classify the query first
        actual_search_mode = search_request.search_mode
        if search_request.search_mode == "auto":
            logger.info(f"Auto mode detected, classifying query: {search_request.query[:50]}...")
            answer_generator = get_answer_generator()
            selected_mode, mode_reasoning = answer_generator.classify_query(search_request.query)
            actual_search_mode = selected_mode
            logger.info(f"Auto mode selected: {selected_mode}")
            logger.info(f"Reasoning: {mode_reasoning}")

            # If auto mode selected sectional_analysis, we need to process async
            # because sectional analysis is a long-running operation
            if actual_search_mode == "sectional_analysis":
                logger.info(f"Auto mode detected sectional query, switching to async processing...")
                job_id = f"search_{uuid.uuid4().hex}"
                job_tracker = get_search_job_tracker()

                import json as json_module
                priority_order_str = json_module.dumps(search_request.priority_order) if search_request.priority_order else None

                job_tracker.create_job(
                    job_id=job_id,
                    query=search_request.query,
                    search_mode="sectional_analysis",  # Use the classified mode
                    reasoning_mode=search_request.reasoning_mode,
                    conversation_id=search_request.conversation_id,
                    user_id=current_user.id,
                    top_k=search_request.top_k,
                    priority_order=priority_order_str
                )

                # Update the search request to use sectional_analysis mode
                search_request_dict = search_request.dict()
                search_request_dict["search_mode"] = "sectional_analysis"

                background_tasks.add_task(process_search_job, job_id, search_request_dict)

                return {
                    "success": True,
                    "job_id": job_id,
                    "message": f"Query detected as multi-section document request. Processing in background.",
                    "estimated_time": "10-20 minutes (multi-section processing)",
                    "is_async": True,
                    "selected_mode": "sectional_analysis",
                    "mode_reasoning": mode_reasoning
                }

        # Only search files if mode is not online_only
        if actual_search_mode != "online_only":
            vector_store = get_vector_store()

            # Perform search with conversation filtering
            results = vector_store.search(
                query=search_request.query,
                top_k=search_request.top_k,
                file_types=search_request.file_types,
                date_from=search_request.date_from,
                date_to=search_request.date_to,
                conversation_id=search_request.conversation_id
            )

            # Format results
            search_results = [
                SearchResult(
                    content=result["content"],
                    score=result["score"],
                    metadata=result["metadata"],
                    retrieval_method=result.get("retrieval_method", "Dense")
                )
                for result in results
            ]

        # Generate final answer using GPT with search mode support
        answer = None
        online_search_response = None
        extracted_info = None
        try:
            answer_generator = get_answer_generator()

            # Convert conversation history to dict format if provided
            conversation_history_dict = None
            if search_request.conversation_history:
                conversation_history_dict = [turn.dict() for turn in search_request.conversation_history]

            answer, online_search_response, extracted_info = answer_generator.generate_answer(
                query=search_request.query,
                search_results=results,
                search_mode=actual_search_mode,
                reasoning_mode=search_request.reasoning_mode,
                priority_order=search_request.priority_order,
                conversation_history=conversation_history_dict
            )
            logger.info(f"Generated answer for query: {search_request.query[:50]}... using mode: {actual_search_mode}")
        except Exception as e:
            logger.error(f"Error generating answer: {str(e)}")
            # Continue without answer if generation fails
            answer = f"Error generating answer: {str(e)}"

        processing_time = time.time() - start_time

        # Save synchronous search to database for conversation history
        # Create job_id for tracking in conversation history
        job_id = f"search_{uuid.uuid4().hex}"
        job_tracker = get_search_job_tracker()

        try:
            import json as json_module

            # Serialize priority_order (it's a list, but DB expects string)
            priority_order_str = json_module.dumps(search_request.priority_order, ensure_ascii=False) if search_request.priority_order else None

            # Create job record
            job_tracker.create_job(
                job_id=job_id,
                query=search_request.query,
                search_mode=search_request.search_mode,
                reasoning_mode=search_request.reasoning_mode,
                conversation_id=search_request.conversation_id,
                user_id=current_user.id,
                top_k=search_request.top_k,
                priority_order=priority_order_str
            )

            # Update to completed and save results
            job_tracker.update_status(job_id, SearchJobStatus.COMPLETED)

            # Serialize complex objects to JSON strings for database storage
            extracted_info_str = json_module.dumps(extracted_info, ensure_ascii=False) if extracted_info else None
            online_search_response_str = json_module.dumps(online_search_response, ensure_ascii=False) if online_search_response else None

            job_tracker.save_results(
                job_id=job_id,
                answer=answer,
                results=[result.dict() for result in search_results],
                total_results=len(search_results),
                processing_time=processing_time,
                extracted_info=extracted_info_str,
                online_search_response=online_search_response_str
            )
            logger.info(f"[JOB {job_id}] Synchronous search saved to database")
        except Exception as e:
            logger.error(f"[JOB {job_id}] Error saving synchronous search to database: {str(e)}")
            # Don't fail the request if database save fails

        return SearchResponse(
            success=True,
            query=search_request.query,
            answer=answer,
            online_search_response=online_search_response,
            extracted_info=extracted_info,
            selected_mode=selected_mode,
            mode_reasoning=mode_reasoning,
            results=search_results,
            total_results=len(search_results),
            processing_time=round(processing_time, 3)
        )

    except Exception as e:
        logger.error(f"Error during search: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(conversation_id: str = None):
    """
    List all uploaded documents, optionally filtered by conversation

    Args:
        conversation_id: Optional conversation ID to filter documents

    Returns:
        List of documents with metadata
    """
    try:
        logger.info(f"Listing documents with conversation_id: {conversation_id}")
        vector_store = get_vector_store()
        files = vector_store.list_files(conversation_id=conversation_id)
        logger.info(f"Found {len(files)} files for conversation_id: {conversation_id}")

        documents = [
            DocumentInfo(
                file_id=file["file_id"],
                file_name=file["file_name"],
                file_type=file["file_type"],
                file_size=file["file_size"],
                upload_date=file["upload_date"],
                chunk_count=file["chunk_count"]
            )
            for file in files
        ]

        return DocumentListResponse(
            success=True,
            documents=documents,
            total_count=len(documents)
        )

    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listing documents: {str(e)}")


@router.delete("/documents/{file_id}", response_model=DeleteResponse)
async def delete_document(file_id: str):
    """
    Delete a document and all its chunks
    Backs up the file to S3 before deleting from EC2

    Args:
        file_id: File identifier

    Returns:
        Delete confirmation
    """
    try:
        from pathlib import Path
        import os
        from backend.app.utils.s3_storage import S3Storage
        from datetime import datetime

        vector_store = get_vector_store()
        deleted_count, file_metadata = vector_store.delete_by_file_id(file_id)

        if deleted_count == 0:
            raise HTTPException(status_code=404, detail="Document not found")

        # Backup file to S3 before deleting from EC2
        if file_metadata and file_metadata.get("file_name"):
            file_name = file_metadata["file_name"]

            # Find the file in uploads directory (format: {file_id}_{filename})
            upload_dir = Path(settings.UPLOAD_DIR)
            file_pattern = f"{file_id}_*"
            matching_files = list(upload_dir.glob(file_pattern))

            if matching_files:
                local_file = matching_files[0]
                logger.info(f"Found file to backup: {local_file}")

                try:
                    # Initialize S3 client (using same bucket as stock data)
                    s3_storage = S3Storage(
                        bucket_name="plfs-han-ai-search",
                        region_name="us-west-2"
                    )

                    # Create S3 key with timestamp for archival
                    upload_date = file_metadata.get("upload_date", datetime.now().isoformat())
                    s3_key = f"deleted-documents/{upload_date[:10]}/{file_id}_{file_name}"

                    # Backup to S3
                    success = s3_storage.upload_file(local_file, s3_key)

                    if success:
                        logger.info(f"File backed up to S3: s3://{s3_storage.bucket_name}/{s3_key}")

                        # Delete from EC2 after successful S3 backup
                        os.remove(local_file)
                        logger.info(f"File deleted from EC2: {local_file}")
                    else:
                        logger.warning(f"Failed to backup file to S3, keeping on EC2: {local_file}")

                except Exception as s3_error:
                    logger.error(f"Error backing up to S3: {str(s3_error)}, keeping file on EC2")
            else:
                logger.warning(f"File not found in uploads directory: {file_pattern}")

        return DeleteResponse(
            success=True,
            message=f"Document deleted successfully and backed up to S3",
            deleted_count=deleted_count
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting document: {str(e)}")


@router.get("/search-jobs/{job_id}")
async def get_search_job_status(job_id: str):
    """
    Get status and results of a background search job

    Args:
        job_id: Job identifier

    Returns:
        Job status, progress, and results (if completed)
    """
    try:
        job_tracker = get_search_job_tracker()
        job = job_tracker.get_job(job_id)

        if not job:
            raise HTTPException(status_code=404, detail="Search job not found")

        response = job.to_dict()

        # For completed jobs, format results as SearchResult objects
        if job.status == SearchJobStatus.COMPLETED and job.results:
            response["results"] = [
                SearchResult(**result).dict() for result in job.results
            ]

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting search job status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting job status: {str(e)}")


@router.post("/search-jobs/{job_id}/cancel")
async def cancel_search_job(job_id: str):
    """
    Cancel a running search job

    Args:
        job_id: Job identifier

    Returns:
        Cancellation confirmation
    """
    try:
        job_tracker = get_search_job_tracker()
        success = job_tracker.cancel_job(job_id)

        if not success:
            # Check if job exists
            job = job_tracker.get_job(job_id)
            if not job:
                raise HTTPException(status_code=404, detail="Search job not found")
            else:
                raise HTTPException(status_code=400, detail=f"Cannot cancel job in status: {job.status.value}")

        return {
            "success": True,
            "message": "Search job cancelled successfully",
            "job_id": job_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling search job: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error cancelling job: {str(e)}")


@router.get("/conversations")
async def get_conversations(
    current_user: User = Depends(get_current_user),
    limit: int = 100
):
    """
    Get all conversations for the current user

    Args:
        current_user: Authenticated user (from JWT token)
        limit: Maximum number of conversations to return

    Returns:
        List of conversations for this user
    """
    try:
        job_tracker = get_search_job_tracker()
        conversations = job_tracker.get_conversations(user_id=current_user.id, limit=limit)

        return {
            "success": True,
            "user_id": current_user.id,
            "conversations": conversations,
            "total_count": len(conversations)
        }

    except Exception as e:
        logger.error(f"Error fetching conversations: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching conversations: {str(e)}")


@router.get("/conversations/{conversation_id}")
async def get_conversation_history(
    conversation_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get full history for a specific conversation (user must own it)

    Args:
        conversation_id: Conversation identifier
        current_user: Authenticated user (from JWT token)

    Returns:
        Conversation history with all searches
    """
    try:
        job_tracker = get_search_job_tracker()
        history = job_tracker.get_conversation_history(conversation_id, user_id=current_user.id)

        if not history:
            raise HTTPException(status_code=404, detail="Conversation not found or has no completed searches")

        return {
            "success": True,
            "conversation_id": conversation_id,
            "history": history,
            "search_count": len(history)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching conversation history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching conversation history: {str(e)}")


@router.put("/conversations/{conversation_id}")
async def update_conversation_title(
    conversation_id: str,
    title: str,
    current_user: User = Depends(get_current_user)
):
    """
    Update the title of a conversation (user must own it)

    Args:
        conversation_id: Conversation identifier
        title: New title for the conversation
        current_user: Authenticated user (from JWT token)

    Returns:
        Success status and updated conversation info
    """
    try:
        # Validate title
        if not title or not title.strip():
            raise HTTPException(status_code=400, detail="Title cannot be empty")

        if len(title) > 200:
            raise HTTPException(status_code=400, detail="Title too long (max 200 characters)")

        job_tracker = get_search_job_tracker()
        success = job_tracker.update_conversation_title(conversation_id, title.strip(), user_id=current_user.id)

        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")

        return {
            "success": True,
            "conversation_id": conversation_id,
            "title": title.strip()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating conversation title: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating conversation title: {str(e)}")


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Delete a conversation and all its associated search jobs (user must own it)

    Args:
        conversation_id: Conversation identifier
        current_user: Authenticated user (from JWT token)

    Returns:
        Success status
    """
    try:
        job_tracker = get_search_job_tracker()
        success = job_tracker.delete_conversation(conversation_id, user_id=current_user.id)

        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")

        return {
            "success": True,
            "conversation_id": conversation_id,
            "message": "Conversation deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting conversation: {str(e)}")


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint

    Returns:
        System health status
    """
    try:
        vector_store = get_vector_store()
        qdrant_connected = vector_store.health_check()
        documents_count = vector_store.get_documents_count()

        return HealthResponse(
            status="healthy" if qdrant_connected else "degraded",
            qdrant_connected=qdrant_connected,
            documents_count=documents_count
        )

    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return HealthResponse(
            status="unhealthy",
            qdrant_connected=False,
            documents_count=0
        )
