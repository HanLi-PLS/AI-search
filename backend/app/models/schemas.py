"""
Pydantic models for request/response validation
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class DocumentMetadata(BaseModel):
    """Document metadata"""
    source: str
    file_type: str
    upload_date: datetime
    file_size: int
    page_count: Optional[int] = None
    chunk_id: Optional[str] = None


class DocumentChunk(BaseModel):
    """Document chunk model"""
    id: str
    content: str
    metadata: DocumentMetadata
    score: Optional[float] = None


class UploadResponse(BaseModel):
    """File upload response"""
    success: bool
    message: str
    file_name: str
    file_id: Optional[str] = None
    job_id: Optional[str] = None  # Job ID for background processing
    chunks_created: Optional[int] = None
    processing_time: Optional[float] = None
    status: Optional[str] = None  # Job status: processing, completed, failed


class JobStatusResponse(BaseModel):
    """Job status response"""
    job_id: str
    file_name: str
    conversation_id: Optional[str] = None
    status: str  # pending, processing, completed, failed
    created_at: str
    updated_at: str
    total_files: int = 0
    processed_files: int = 0
    failed_files: int = 0
    total_chunks: int = 0
    error_message: Optional[str] = None
    file_results: List[Dict[str, Any]] = []


class ConversationTurn(BaseModel):
    """Single turn in conversation history"""
    query: str = Field(..., description="User's query")
    answer: str = Field(..., description="AI's answer")


class SearchRequest(BaseModel):
    """Search request model"""
    query: str = Field(..., min_length=1, description="Search query")
    top_k: int = Field(default=5, ge=1, le=200, description="Number of results to return from each method (max 200)")
    search_mode: str = Field(default="files_only", description="Search mode: auto, files_only, online_only, both, or sequential_analysis")
    reasoning_mode: str = Field(default="non_reasoning", description="Reasoning mode: non_reasoning (gpt-5.2), reasoning (gpt-5.2), reasoning_gpt5 (gpt-5-pro), or deep_research (o3-deep-research)")
    priority_order: Optional[List[str]] = Field(default=["online_search", "files"], description="Priority order for 'both' mode")
    conversation_history: Optional[List[ConversationTurn]] = Field(default=None, description="Previous conversation turns for context")
    conversation_id: Optional[str] = Field(default=None, description="Conversation ID to filter files")
    file_types: Optional[List[str]] = Field(default=None, description="Filter by file types")
    date_from: Optional[datetime] = Field(default=None, description="Filter documents from this date")
    date_to: Optional[datetime] = Field(default=None, description="Filter documents to this date")
    hybrid_alpha: float = Field(default=0.5, ge=0, le=1, description="Hybrid search weight (0=keyword, 1=semantic)")


class SearchResult(BaseModel):
    """Single search result"""
    content: str
    score: float
    metadata: Dict[str, Any]
    retrieval_method: Optional[str] = Field(default="Dense", description="Retrieval method: Dense, BM25, or Both")
    highlights: Optional[List[str]] = None


class SearchResponse(BaseModel):
    """Search response model"""
    success: bool
    query: str
    answer: Optional[str] = Field(default=None, description="GPT-generated answer based on search results")
    online_search_response: Optional[str] = Field(default=None, description="Raw online search response")
    extracted_info: Optional[str] = Field(default=None, description="Information extracted from files (sequential mode)")
    selected_mode: Optional[str] = Field(default=None, description="Auto-selected search mode (when using 'auto' mode)")
    mode_reasoning: Optional[str] = Field(default=None, description="Explanation of why this mode was selected")
    results: List[SearchResult]
    total_results: int
    processing_time: float


class DocumentInfo(BaseModel):
    """Document information"""
    file_id: str
    file_name: str
    file_type: str
    file_size: int
    upload_date: datetime
    chunk_count: int


class DocumentListResponse(BaseModel):
    """List of documents response"""
    success: bool
    documents: List[DocumentInfo]
    total_count: int


class DeleteResponse(BaseModel):
    """Delete response"""
    success: bool
    message: str
    deleted_count: Optional[int] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    qdrant_connected: bool
    documents_count: int
    version: str = "1.0.0"


class ErrorResponse(BaseModel):
    """Error response"""
    success: bool = False
    error: str
    details: Optional[str] = None
