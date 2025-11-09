"""
Search API endpoints
"""
from fastapi import APIRouter, HTTPException
import time
from typing import List

from backend.app.models.schemas import (
    SearchRequest, SearchResponse, SearchResult,
    DocumentListResponse, DocumentInfo, DeleteResponse,
    HealthResponse
)
from backend.app.core.vector_store import get_vector_store
from backend.app.core.answer_generator import get_answer_generator
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def search_documents(request: SearchRequest):
    """
    Search documents using semantic similarity and/or online search, then generate answer

    Args:
        request: Search request with query, search_mode, and filters

    Returns:
        Search results with GPT-generated answer
    """
    start_time = time.time()

    try:
        results = []
        search_results = []
        selected_mode = None
        mode_reasoning = None

        # Handle auto mode - classify the query first
        actual_search_mode = request.search_mode
        if request.search_mode == "auto":
            logger.info(f"Auto mode detected, classifying query: {request.query[:50]}...")
            answer_generator = get_answer_generator()
            selected_mode, mode_reasoning = answer_generator.classify_query(request.query)
            actual_search_mode = selected_mode
            logger.info(f"Auto mode selected: {selected_mode}")
            logger.info(f"Reasoning: {mode_reasoning}")

        # Only search files if mode is not online_only
        if actual_search_mode != "online_only":
            vector_store = get_vector_store()

            # Perform search with conversation filtering
            results = vector_store.search(
                query=request.query,
                top_k=request.top_k,
                file_types=request.file_types,
                date_from=request.date_from,
                date_to=request.date_to,
                conversation_id=request.conversation_id
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
            if request.conversation_history:
                conversation_history_dict = [turn.dict() for turn in request.conversation_history]

            answer, online_search_response, extracted_info = answer_generator.generate_answer(
                query=request.query,
                search_results=results,
                search_mode=actual_search_mode,
                reasoning_mode=request.reasoning_mode,
                priority_order=request.priority_order,
                conversation_history=conversation_history_dict
            )
            logger.info(f"Generated answer for query: {request.query[:50]}... using mode: {actual_search_mode}")
        except Exception as e:
            logger.error(f"Error generating answer: {str(e)}")
            # Continue without answer if generation fails
            answer = f"Error generating answer: {str(e)}"

        processing_time = time.time() - start_time

        return SearchResponse(
            success=True,
            query=request.query,
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
