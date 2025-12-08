"""
Search API endpoints
"""
from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
import time
from typing import List
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
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize limiter for this module
limiter = Limiter(key_func=get_remote_address)

# Modes that require background processing (long-running)
ASYNC_SEARCH_MODES = ["reasoning_gpt5", "reasoning_gemini", "deep_research"]


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
        job_tracker.save_results(
            job_id=job_id,
            answer=answer,
            results=search_results,
            total_results=len(search_results),
            processing_time=processing_time,
            extracted_info=extracted_info,
            online_search_response=online_search_response
        )

        logger.info(f"[JOB {job_id}] Search job completed successfully in {processing_time:.1f}s")

    except Exception as e:
        logger.error(f"[JOB {job_id}] Error processing search job: {str(e)}", exc_info=True)
        job_tracker.update_status(job_id, SearchJobStatus.FAILED, str(e))


@router.post("/search")
@limiter.limit(settings.RATE_LIMIT_SEARCH)
async def search_documents(request: Request, search_request: SearchRequest, background_tasks: BackgroundTasks):
    """
    Search documents using semantic similarity and/or online search, then generate answer

    For long-running reasoning modes (reasoning_gpt5, deep_research), creates a background job
    and returns immediately with job_id. For other modes, processes synchronously.

    Args:
        request: FastAPI Request object (required for rate limiting)
        search_request: Search request with query, search_mode, and filters
        background_tasks: FastAPI BackgroundTasks for async processing

    Returns:
        Search results with GPT-generated answer (sync mode) or job_id (async mode)
    """
    # Check if this is a long-running search that should be processed in background
    is_async_mode = search_request.reasoning_mode in ASYNC_SEARCH_MODES

    if is_async_mode:
        # Create background job for long-running search
        job_id = f"search_{uuid.uuid4().hex}"
        job_tracker = get_search_job_tracker()

        logger.info(f"Creating background job {job_id} for {search_request.reasoning_mode} mode")

        # Create job in database
        job_tracker.create_job(
            job_id=job_id,
            query=search_request.query,
            search_mode=search_request.search_mode,
            reasoning_mode=search_request.reasoning_mode,
            conversation_id=search_request.conversation_id
        )

        # Convert SearchRequest to dict for background processing
        search_request_dict = search_request.dict()

        # Add background task
        background_tasks.add_task(process_search_job, job_id, search_request_dict)

        # Return immediately with job_id
        estimated_time = "5-10 minutes" if search_request.reasoning_mode == "reasoning_gpt5" else "15-30 minutes"
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

    Args:
        file_id: File identifier

    Returns:
        Delete confirmation
    """
    try:
        vector_store = get_vector_store()
        deleted_count = vector_store.delete_by_file_id(file_id)

        if deleted_count == 0:
            raise HTTPException(status_code=404, detail="Document not found")

        return DeleteResponse(
            success=True,
            message=f"Document deleted successfully",
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
