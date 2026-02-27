"""
IC Meeting Simulator API endpoints.

Provides routes for:
- Syncing IC meeting notes from Confluence
- Uploading IC meeting notes manually
- Listing synced meetings
- Generating anticipated IC questions for new project materials
"""
import os
import uuid
import logging
from typing import Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Request, Depends
from pydantic import BaseModel

from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.app.config import settings
from backend.app.models.user import User
from backend.app.api.routes.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

# Thread pool for background sync work
_sync_pool = ThreadPoolExecutor(max_workers=2)

# In-memory sync status tracker
_sync_status = {
    "is_syncing": False,
    "progress": 0,
    "total_pages": 0,
    "pages_processed": 0,
    "last_sync": None,
    "error": None,
}


# ─── Request / Response models ───────────────────────────────────────────────

class GenerateQuestionsRequest(BaseModel):
    project_description: str = ""
    # uploaded files are handled via multipart form, not JSON


class SyncConfluenceRequest(BaseModel):
    limit: int = 200


# ─── Confluence sync endpoints ───────────────────────────────────────────────

@router.post("/sync-confluence")
@limiter.limit("5/minute")
async def sync_confluence(
    request: Request,
    body: SyncConfluenceRequest = SyncConfluenceRequest(),
    current_user: User = Depends(get_current_user),
):
    """
    Trigger a sync of IC meeting notes from Confluence.
    Fetches pages, parses Q&A segments, and indexes them in the vector store.
    """
    global _sync_status

    if _sync_status["is_syncing"]:
        return {
            "status": "already_syncing",
            "message": "A sync is already in progress.",
            "progress": _sync_status,
        }

    # Reset status
    _sync_status = {
        "is_syncing": True,
        "progress": 0,
        "total_pages": 0,
        "pages_processed": 0,
        "last_sync": None,
        "error": None,
    }

    # Run sync in background thread
    _sync_pool.submit(_run_confluence_sync, body.limit)

    return {
        "status": "started",
        "message": "Confluence sync started in background.",
    }


def _run_confluence_sync(limit: int):
    """Background worker to sync Confluence pages."""
    global _sync_status
    try:
        from backend.app.services.confluence import get_confluence_client, parse_meeting_qna
        from backend.app.core.ic_meeting_store import get_ic_meeting_store

        client = get_confluence_client()
        store = get_ic_meeting_store()

        # 1. Get list of meeting pages
        pages = client.get_meeting_pages(limit=limit)
        _sync_status["total_pages"] = len(pages)

        if not pages:
            _sync_status["is_syncing"] = False
            _sync_status["error"] = "No pages found in Confluence."
            return

        # 2. Get already-indexed page IDs to skip
        existing_meetings = store.list_meetings()
        existing_page_ids = {m["page_id"] for m in existing_meetings}

        total_segments = 0
        new_pages = 0

        for i, page_meta in enumerate(pages):
            page_id = page_meta["page_id"]

            # Skip already indexed pages
            if page_id in existing_page_ids:
                _sync_status["pages_processed"] = i + 1
                _sync_status["progress"] = int((i + 1) / len(pages) * 100)
                continue

            try:
                # Fetch full content
                page_content = client.get_page_content(page_id)

                # Parse Q&A segments
                segments = parse_meeting_qna(
                    page_content["body_text"],
                    title=page_content["title"],
                )

                # Determine meeting date from page metadata
                meeting_date = page_content.get("created", "")

                # Index segments
                count = store.add_meeting_segments(
                    segments=segments,
                    page_id=page_id,
                    title=page_content["title"],
                    meeting_date=meeting_date,
                    source="confluence",
                )
                total_segments += count
                new_pages += 1

            except Exception as e:
                logger.error(f"Error processing page {page_id}: {e}")

            _sync_status["pages_processed"] = i + 1
            _sync_status["progress"] = int((i + 1) / len(pages) * 100)

        _sync_status["is_syncing"] = False
        _sync_status["last_sync"] = datetime.utcnow().isoformat()
        _sync_status["progress"] = 100

        logger.info(
            f"Confluence sync complete: {new_pages} new pages, "
            f"{total_segments} segments indexed"
        )

    except Exception as e:
        logger.error(f"Confluence sync failed: {e}", exc_info=True)
        _sync_status["is_syncing"] = False
        _sync_status["error"] = str(e)


@router.get("/sync-status")
async def get_sync_status(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Get the current Confluence sync status."""
    return _sync_status


@router.get("/confluence-test")
async def test_confluence_connection(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Test Confluence API connection."""
    try:
        from backend.app.services.confluence import get_confluence_client
        client = get_confluence_client()
        return client.test_connection()
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ─── Meeting management endpoints ───────────────────────────────────────────

@router.get("/meetings")
async def list_meetings(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """List all indexed IC meetings."""
    from backend.app.core.ic_meeting_store import get_ic_meeting_store
    store = get_ic_meeting_store()
    meetings = store.list_meetings()
    stats = store.get_stats()
    return {"meetings": meetings, "stats": stats}


@router.delete("/meetings/{page_id}")
async def delete_meeting(
    page_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Delete an indexed meeting by page ID."""
    from backend.app.core.ic_meeting_store import get_ic_meeting_store
    store = get_ic_meeting_store()
    deleted = store.delete_by_page_id(page_id)
    return {"deleted_segments": deleted, "page_id": page_id}


# ─── Manual upload of meeting notes ─────────────────────────────────────────

@router.post("/upload-meeting")
@limiter.limit("10/minute")
async def upload_meeting_note(
    request: Request,
    file: UploadFile = File(...),
    meeting_date: str = Form(""),
    current_user: User = Depends(get_current_user),
):
    """
    Upload an IC meeting note file (PDF, DOCX, TXT, etc.) for indexing.
    The file will be processed, Q&A segments extracted, and indexed.
    """
    from backend.app.core.document_processor import DocumentProcessor
    from backend.app.services.confluence import parse_meeting_qna
    from backend.app.core.ic_meeting_store import get_ic_meeting_store

    # Validate file extension
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in settings.SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_ext}",
        )

    # Save file temporarily
    upload_dir = settings.UPLOAD_DIR / "ic_meetings"
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_id = str(uuid.uuid4())
    temp_path = upload_dir / f"{file_id}{file_ext}"

    try:
        content = await file.read()
        with open(temp_path, "wb") as f:
            f.write(content)

        # Process file to extract text
        processor = DocumentProcessor()
        documents = processor.process_file(str(temp_path), file.filename)

        # Combine extracted text
        full_text = "\n\n".join(doc.page_content for doc in documents)

        # Parse into Q&A segments
        segments = parse_meeting_qna(full_text, title=file.filename)

        # Use provided date or fallback to today
        if not meeting_date:
            meeting_date = datetime.utcnow().isoformat()

        # Index segments
        store = get_ic_meeting_store()
        count = store.add_meeting_segments(
            segments=segments,
            page_id=file_id,
            title=file.filename,
            meeting_date=meeting_date,
            source="upload",
        )

        return {
            "status": "success",
            "file_name": file.filename,
            "file_id": file_id,
            "segments_indexed": count,
            "meeting_date": meeting_date,
        }

    except Exception as e:
        logger.error(f"Error processing uploaded meeting note: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Cleanup temp file
        if temp_path.exists():
            os.remove(temp_path)


# ─── Question generation endpoint ───────────────────────────────────────────

@router.post("/generate-questions")
@limiter.limit("10/minute")
async def generate_questions(
    request: Request,
    project_description: str = Form(""),
    files: list[UploadFile] = File(default=[]),
    current_user: User = Depends(get_current_user),
):
    """
    Generate anticipated IC questions for new project materials.

    Accepts:
    - project_description: Text description of the project (form field)
    - files: Optional uploaded project documents (multipart files)

    Returns anticipated IC questions based on historical Q&A patterns.
    """
    from backend.app.core.document_processor import DocumentProcessor
    from backend.app.core.ic_question_generator import generate_ic_questions

    uploaded_doc_texts = []

    # Process uploaded files
    if files:
        processor = DocumentProcessor()
        upload_dir = settings.UPLOAD_DIR / "ic_temp"
        upload_dir.mkdir(parents=True, exist_ok=True)

        for upload_file in files:
            if not upload_file.filename:
                continue

            file_ext = os.path.splitext(upload_file.filename)[1].lower()
            if file_ext not in settings.SUPPORTED_EXTENSIONS:
                continue

            temp_id = str(uuid.uuid4())
            temp_path = upload_dir / f"{temp_id}{file_ext}"

            try:
                content = await upload_file.read()
                with open(temp_path, "wb") as f:
                    f.write(content)

                documents = processor.process_file(str(temp_path), upload_file.filename)
                full_text = "\n\n".join(doc.page_content for doc in documents)
                uploaded_doc_texts.append(full_text)
            except Exception as e:
                logger.error(f"Error processing file {upload_file.filename}: {e}")
            finally:
                if temp_path.exists():
                    os.remove(temp_path)

    # Validate that we have some input
    if not project_description.strip() and not uploaded_doc_texts:
        raise HTTPException(
            status_code=400,
            detail="Please provide a project description or upload project documents.",
        )

    # Generate questions
    result = generate_ic_questions(
        project_description=project_description,
        uploaded_doc_texts=uploaded_doc_texts if uploaded_doc_texts else None,
    )

    return result
