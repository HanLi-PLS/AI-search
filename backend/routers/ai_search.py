"""
AI Search API endpoints
Handles document upload, indexing, search, and Q&A
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
import os

from ..services.document_service import DocumentService
from ..services.search_service import SearchService


router = APIRouter(prefix="/api/ai-search", tags=["AI Search"])

# Initialize services (in production, use dependency injection)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
doc_service = DocumentService(openai_api_key=OPENAI_API_KEY)
search_service = SearchService(openai_api_key=OPENAI_API_KEY)

# Load existing vector DB and BM25 retriever if available
try:
    search_service.load_vector_db()
    search_service.load_bm25_retriever()
except Exception as e:
    print(f"No existing index found: {e}")


class SearchQuery(BaseModel):
    """Search query model"""
    question: str
    k_bm: int = 50
    k_jd: int = 50
    search_model: str = "gpt-4.1"
    priority_order: List[str] = ['jarvis_docs', 'online_search']


class SearchResponse(BaseModel):
    """Search response model"""
    answer: str
    online_search_response: Optional[str] = None


class IndexRequest(BaseModel):
    """Index documents request"""
    s3_bucket: str
    s3_folder: str
    ignored_files: List[str] = []
    collection_name: str = "jarvis_docs"
    persist_directory: str = "./chroma_db_jarvis_docs"


class IndexResponse(BaseModel):
    """Index response model"""
    status: str
    message: str
    document_count: int


@router.post("/search", response_model=SearchResponse)
async def search(query: SearchQuery):
    """
    Search documents and get AI-generated answer

    Args:
        query: Search query with parameters

    Returns:
        AI-generated answer with sources
    """
    try:
        answer, online_response = search_service.answer_with_search_ensemble(
            question=query.question,
            k_bm=query.k_bm,
            k_jd=query.k_jd,
            search_model=query.search_model,
            priority_order=query.priority_order
        )

        return SearchResponse(
            answer=answer,
            online_search_response=online_response if online_response else None
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.post("/index", response_model=IndexResponse)
async def index_documents(request: IndexRequest, background_tasks: BackgroundTasks):
    """
    Index documents from S3 into vector database

    Args:
        request: S3 bucket and folder information
        background_tasks: FastAPI background tasks

    Returns:
        Status of indexing operation
    """
    try:
        # Load and process documents
        texts = doc_service.process_documents_from_s3(
            s3_bucket=request.s3_bucket,
            s3_folder=request.s3_folder,
            ignored_files=request.ignored_files
        )

        if not texts:
            raise HTTPException(status_code=400, detail="No documents found to index")

        # Create vector DB
        search_service.create_vector_db(
            texts=texts,
            collection_name=request.collection_name,
            persist_directory=request.persist_directory
        )

        # Create BM25 retriever
        search_service.create_bm25_retriever(
            collection_name=request.collection_name,
            persist_directory=request.persist_directory
        )

        return IndexResponse(
            status="success",
            message=f"Successfully indexed documents from s3://{request.s3_bucket}/{request.s3_folder}",
            document_count=len(texts)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Indexing failed: {str(e)}")


@router.get("/status")
async def get_index_status():
    """
    Get status of the search index

    Returns:
        Status information about vector DB and BM25 retriever
    """
    try:
        has_vector_db = search_service.db_jd is not None
        has_bm25 = search_service.bm25_retriever is not None

        return {
            "status": "ready" if (has_vector_db and has_bm25) else "not_ready",
            "vector_db_loaded": has_vector_db,
            "bm25_loaded": has_bm25,
            "embeddings_model": search_service.embeddings_model_name,
            "device": search_service.device
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")


@router.post("/company-info")
async def extract_company_info(company_name: str, k_bm: int = 100, k_jd: int = 100):
    """
    Extract structured company information including drug pipelines

    Args:
        company_name: Name of the biotech company
        k_bm: Number of BM25 results
        k_jd: Number of vector search results

    Returns:
        Structured JSON with company information
    """
    try:
        question = f"""
        Extract structured facts about the drug pipelines of company {company_name}.
        Return ONLY a JSON object with company-level information and its key assets.
        Include only assets with a known asset name.
        If no assets are found, return an empty assets list.

        JSON structure:
        {{
          "company name": "{company_name}",
          "has platform": true | false | null,
          "platform name": "<name, else null>",
          "platform is core asset": true | false | null,
          "assets": [
            {{
              "asset name": "<name, else null>",
              "modality": "<name, else null>",
              "targets": ["..."],
              "targeted therapeutic areas": ["..."],
              "targeted indications": ["..."],
              "current development stage": "<name, else null>",
              "brief trial result": "<brief description, else null>",
              "companies with competing asset":["..."],
            }}
          ]
        }}
        """

        answer, _ = search_service.answer_with_search_ensemble(
            question=question,
            k_bm=k_bm,
            k_jd=k_jd,
            search_model="o4-mini",
            priority_order=["jarvis_docs"]
        )

        return {"company_name": company_name, "info": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Company info extraction failed: {str(e)}")
