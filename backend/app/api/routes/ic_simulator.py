"""
IC Meeting Simulator API endpoints.

Provides routes for:
- Syncing IC meeting notes from Confluence
- Uploading IC meeting notes manually
- Listing synced meetings
- Generating anticipated IC questions for new project materials
- Running cognitive extraction pipeline (Layer 1)
- Managing cognitive profiles
- Incremental profile updates
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

# Thread pool for background work (sync, extraction)
_worker_pool = ThreadPoolExecutor(max_workers=2)

# In-memory sync status tracker
_sync_status = {
    "is_syncing": False,
    "progress": 0,
    "total_pages": 0,
    "pages_processed": 0,
    "last_sync": None,
    "error": None,
    "auto_extraction_triggered": False,
    "new_pages_synced": 0,
}

# In-memory extraction status tracker
_extraction_status = {
    "is_running": False,
    "stage": "",          # "pass1_pass2", "pass3", "pass4"
    "current": 0,
    "total": 0,
    "detail": "",
    "error": None,
    "started_at": None,
    "completed_at": None,
}


# ─── Request / Response models ───────────────────────────────────────────────

class GenerateQuestionsRequest(BaseModel):
    project_description: str = ""


class SyncConfluenceRequest(BaseModel):
    limit: int = 200
    date_from: str = ""   # e.g. "2024-01-01"
    date_to: str = ""     # e.g. "2025-12-31"


class RunExtractionRequest(BaseModel):
    """Request to run the cognitive extraction pipeline."""
    date_from: str = ""        # e.g. "2024-01-01"
    date_to: str = ""          # e.g. "2025-12-31"
    source: str = "confluence"  # "confluence" or "indexed" (from already-synced data)
    limit: int = 200


class IncrementalUpdateRequest(BaseModel):
    """Request to incrementally update cognitive profile with new meetings."""
    date_from: str = ""
    date_to: str = ""
    source: str = "confluence"
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
        "auto_extraction_triggered": False,
        "new_pages_synced": 0,
    }

    # Run sync in background thread
    _worker_pool.submit(
        _run_confluence_sync,
        body.limit,
        body.date_from or None,
        body.date_to or None,
    )

    return {
        "status": "started",
        "message": "Confluence sync started in background.",
    }


def _run_confluence_sync(limit: int, date_from: str = None, date_to: str = None):
    """Background worker to sync Confluence pages."""
    global _sync_status
    try:
        from backend.app.services.confluence import get_confluence_client, parse_meeting_qna
        from backend.app.core.ic_meeting_store import get_ic_meeting_store

        client = get_confluence_client()
        store = get_ic_meeting_store()

        # 1. Get list of meeting pages (optionally filtered by date range)
        pages = client.get_meeting_pages(
            limit=limit,
            date_from=date_from,
            date_to=date_to,
        )
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
        _sync_status["new_pages_synced"] = new_pages

        logger.info(
            f"Confluence sync complete: {new_pages} new pages, "
            f"{total_segments} segments indexed"
        )

        # Auto-trigger incremental extraction if new meetings were added
        if new_pages > 0 and not _extraction_status["is_running"]:
            logger.info(
                f"Auto-triggering incremental extraction for {new_pages} new meetings"
            )
            _sync_status["auto_extraction_triggered"] = True

            _extraction_status.update({
                "is_running": True,
                "stage": "starting",
                "current": 0,
                "total": 0,
                "detail": f"Auto-triggered: extracting {new_pages} new meetings...",
                "error": None,
                "started_at": datetime.utcnow().isoformat(),
                "completed_at": None,
            })

            _worker_pool.submit(
                _run_extraction_worker,
                "indexed",   # source: use already-synced meetings
                None,        # date_from
                None,        # date_to
                0,           # limit (0 = no limit)
                True,        # incremental
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
        documents = processor.process_file(temp_path, file.filename)

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
    date_from: str = Form(""),
    date_to: str = Form(""),
    current_user: User = Depends(get_current_user),
):
    """
    Generate anticipated IC questions for new project materials.

    Automatically uses cognitive simulation (Mode 2) when a cognitive profile
    exists, or falls back to legacy RAG mode (Mode 1).

    Accepts:
    - project_description: Text description of the project (form field)
    - files: Optional uploaded project documents (multipart files)
    - date_from: Only use IC meetings on or after this date (e.g. "2024-01-01")
    - date_to: Only use IC meetings on or before this date (e.g. "2025-12-31")

    Returns anticipated IC questions based on cognitive simulation or historical patterns.
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

                documents = processor.process_file(temp_path, upload_file.filename)
                full_text = "\n\n".join(doc.page_content for doc in documents)
                uploaded_doc_texts.append(full_text)
            except Exception as e:
                logger.error(f"Error processing file {upload_file.filename}: {e}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to process file '{upload_file.filename}': {e}",
                )
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
        date_from=date_from if date_from else None,
        date_to=date_to if date_to else None,
    )

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# Cognitive Extraction Pipeline Endpoints (Layer 1)
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/extraction/run")
@limiter.limit("2/minute")
async def run_extraction(
    request: Request,
    body: RunExtractionRequest = RunExtractionRequest(),
    current_user: User = Depends(get_current_user),
):
    """
    Run the full cognitive extraction pipeline (Pass 1-4) on IC meeting notes.

    This is the heavy-lift operation that builds the IC cognitive profile.
    Runs in background — poll /extraction/status for progress.

    Args (JSON body):
    - date_from: Only process meetings from this date (YYYY-MM-DD)
    - date_to: Only process meetings up to this date (YYYY-MM-DD)
    - source: "confluence" to fetch from Confluence, "indexed" to use already-synced data
    - limit: Max number of meetings to process (default 200)
    """
    global _extraction_status

    if _extraction_status["is_running"]:
        return {
            "status": "already_running",
            "message": "An extraction is already in progress.",
            "progress": _extraction_status,
        }

    _extraction_status = {
        "is_running": True,
        "stage": "starting",
        "current": 0,
        "total": 0,
        "detail": "Initializing extraction pipeline...",
        "error": None,
        "started_at": datetime.utcnow().isoformat(),
        "completed_at": None,
    }

    _worker_pool.submit(
        _run_extraction_worker,
        body.source,
        body.date_from or None,
        body.date_to or None,
        body.limit,
        False,  # not incremental
    )

    return {
        "status": "started",
        "message": "Cognitive extraction pipeline started in background.",
    }


@router.post("/extraction/incremental")
@limiter.limit("5/minute")
async def run_incremental_update(
    request: Request,
    body: IncrementalUpdateRequest = IncrementalUpdateRequest(),
    current_user: User = Depends(get_current_user),
):
    """
    Incrementally update the cognitive profile with new meetings.

    Only processes meetings that haven't been extracted yet. Updates the
    existing cognitive profile rather than rebuilding from scratch.

    Use this after syncing new meetings from Confluence to incorporate
    them into the IC intelligence model.
    """
    global _extraction_status

    if _extraction_status["is_running"]:
        return {
            "status": "already_running",
            "message": "An extraction is already in progress.",
            "progress": _extraction_status,
        }

    _extraction_status = {
        "is_running": True,
        "stage": "starting",
        "current": 0,
        "total": 0,
        "detail": "Initializing incremental update...",
        "error": None,
        "started_at": datetime.utcnow().isoformat(),
        "completed_at": None,
    }

    _worker_pool.submit(
        _run_extraction_worker,
        body.source,
        body.date_from or None,
        body.date_to or None,
        body.limit,
        True,  # incremental
    )

    return {
        "status": "started",
        "message": "Incremental cognitive update started in background.",
    }


def _run_extraction_worker(
    source: str,
    date_from: Optional[str],
    date_to: Optional[str],
    limit: int,
    incremental: bool,
):
    """Background worker for cognitive extraction pipeline."""
    global _extraction_status

    def progress_callback(stage, current, total, detail):
        _extraction_status["stage"] = stage
        _extraction_status["current"] = current
        _extraction_status["total"] = total
        _extraction_status["detail"] = detail

    try:
        meetings = _fetch_meetings_for_extraction(source, date_from, date_to, limit)

        if not meetings:
            _extraction_status["is_running"] = False
            _extraction_status["error"] = "No meetings found for extraction."
            return

        _extraction_status["total"] = len(meetings)

        if incremental:
            from backend.app.core.ic_cognitive_extractor import run_incremental_update
            result = run_incremental_update(
                new_meetings=meetings,
                progress_callback=progress_callback,
            )
        else:
            from backend.app.core.ic_cognitive_extractor import run_full_extraction
            result = run_full_extraction(
                meetings=meetings,
                date_from=date_from,
                date_to=date_to,
                progress_callback=progress_callback,
            )

        _extraction_status["is_running"] = False
        _extraction_status["completed_at"] = datetime.utcnow().isoformat()
        _extraction_status["detail"] = (
            f"Extraction complete. "
            f"Result: {json.dumps(_summarize_result(result), default=str)}"
        )

        logger.info(f"Extraction pipeline complete: {_summarize_result(result)}")

    except Exception as e:
        logger.error(f"Extraction pipeline failed: {e}", exc_info=True)
        _extraction_status["is_running"] = False
        _extraction_status["error"] = str(e)


import json


def _fetch_meetings_for_extraction(
    source: str,
    date_from: Optional[str],
    date_to: Optional[str],
    limit: int,
) -> list:
    """
    Fetch meeting texts for the extraction pipeline.

    Two modes:
    - "confluence": Fetch directly from Confluence API
    - "indexed": Use meetings already synced to the Qdrant store,
                 re-fetching full text from Confluence by page_id
    """
    if source == "confluence":
        from backend.app.services.confluence import get_confluence_client
        client = get_confluence_client()

        pages = client.get_meeting_pages(
            limit=limit, date_from=date_from, date_to=date_to
        )

        meetings = []
        for page_meta in pages:
            try:
                page_content = client.get_page_content(page_meta["page_id"])
                meetings.append({
                    "page_id": page_meta["page_id"],
                    "title": page_content["title"],
                    "meeting_date": page_content.get("created", ""),
                    "body_text": page_content["body_text"],
                })
            except Exception as e:
                logger.error(
                    f"Error fetching page {page_meta['page_id']}: {e}"
                )

        return meetings

    elif source == "indexed":
        # Use already-indexed meetings, re-fetch full text from Confluence
        from backend.app.core.ic_meeting_store import get_ic_meeting_store
        from backend.app.services.confluence import get_confluence_client

        store = get_ic_meeting_store()
        indexed_meetings = store.list_meetings()
        client = get_confluence_client()

        # Apply date filtering
        if date_from:
            indexed_meetings = [
                m for m in indexed_meetings
                if m.get("meeting_date", "") >= date_from
            ]
        if date_to:
            indexed_meetings = [
                m for m in indexed_meetings
                if m.get("meeting_date", "") <= date_to
            ]

        meetings = []
        for m in indexed_meetings[:limit]:
            page_id = m["page_id"]
            try:
                # For Confluence-sourced meetings, re-fetch full text
                if m.get("source") == "confluence":
                    page_content = client.get_page_content(page_id)
                    meetings.append({
                        "page_id": page_id,
                        "title": page_content["title"],
                        "meeting_date": page_content.get("created", ""),
                        "body_text": page_content["body_text"],
                    })
                else:
                    # For uploaded meetings, we'd need to re-read from stored data
                    # For now, reconstruct from indexed segments
                    logger.warning(
                        f"Uploaded meeting {page_id}: reconstructing from segments"
                    )
                    _reconstruct_from_segments(store, page_id, m, meetings)
            except Exception as e:
                logger.error(f"Error fetching page {page_id}: {e}")

        return meetings

    else:
        raise ValueError(f"Unknown source: {source}. Use 'confluence' or 'indexed'.")


def _reconstruct_from_segments(store, page_id, meeting_meta, meetings_list):
    """Reconstruct meeting text from stored Qdrant segments (fallback for uploads)."""
    from qdrant_client.models import Filter, FieldCondition, MatchValue

    all_points, _ = store.client.scroll(
        collection_name=store.collection_name,
        scroll_filter=Filter(
            must=[FieldCondition(key="page_id", match=MatchValue(value=page_id))]
        ),
        limit=1000,
        with_payload=True,
        with_vectors=False,
    )
    if all_points:
        sorted_points = sorted(
            all_points,
            key=lambda p: p.payload.get("chunk_index", 0),
        )
        full_text = "\n\n".join(
            p.payload.get("raw_text", p.payload.get("content", ""))
            for p in sorted_points
        )
        meetings_list.append({
            "page_id": page_id,
            "title": meeting_meta.get("title", ""),
            "meeting_date": meeting_meta.get("meeting_date", ""),
            "body_text": full_text,
        })


def _summarize_result(result: dict) -> dict:
    """Create a compact summary of extraction results for status reporting."""
    if "status" in result:
        return result
    summary = result.get("summary", {})
    return {
        "meetings_processed": summary.get("meetings_processed", result.get("new_meetings_processed", 0)),
        "total_qa_items": summary.get("total_qa_items", result.get("new_qa_items", 0)),
        "profile_updated": result.get("profile_updated", result.get("pass3_profile") is not None),
        "calibration_updated": result.get("calibration_updated", result.get("pass4_calibration") is not None),
    }


@router.get("/extraction/status")
async def get_extraction_status(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Get the current cognitive extraction pipeline status."""
    return _extraction_status


# ─── Cognitive Profile Management ─────────────────────────────────────────────

@router.get("/cognitive/profile")
async def get_cognitive_profile(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """
    Get the current IC cognitive profile.

    Returns the committee-level cognitive profile including:
    - Core priorities and decision patterns
    - Member-level profiles (if attribution data available)
    - Collective patterns, kill criteria, blind spots
    """
    from backend.app.core.ic_cognitive_store import load_cognitive_profile, get_profile_summary

    profile = load_cognitive_profile()
    summary = get_profile_summary()

    if not profile:
        return {
            "status": "no_profile",
            "message": (
                "No cognitive profile exists yet. "
                "Run the extraction pipeline first: POST /ic-simulator/extraction/run"
            ),
            "summary": summary,
        }

    return {
        "status": "ok",
        "profile": profile,
        "summary": summary,
    }


@router.get("/cognitive/calibration")
async def get_calibration_set(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Get the current calibration set (annotated exemplar meetings)."""
    from backend.app.core.ic_cognitive_store import load_calibration_set

    calibration = load_calibration_set()
    if not calibration:
        return {
            "status": "no_calibration",
            "message": "No calibration set exists yet. Run the extraction pipeline first.",
        }

    return {
        "status": "ok",
        "calibration": calibration,
        "num_examples": len(calibration.get("examples", [])),
    }


@router.get("/cognitive/extracts")
async def list_extracts(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """List all per-meeting extracts (Pass 1+2 outputs)."""
    from backend.app.core.ic_cognitive_store import list_meeting_extracts

    extracts = list_meeting_extracts()
    return {
        "total": len(extracts),
        "extracts": extracts,
    }


@router.get("/cognitive/extracts/{page_id}")
async def get_extract(
    page_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Get the full structured extract for a specific meeting."""
    from backend.app.core.ic_cognitive_store import load_meeting_extract

    extract = load_meeting_extract(page_id)
    if not extract:
        raise HTTPException(status_code=404, detail=f"No extract found for page_id: {page_id}")

    return extract


@router.delete("/cognitive/extracts/{page_id}")
async def delete_extract(
    page_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Delete a specific meeting extract."""
    from backend.app.core.ic_cognitive_store import delete_meeting_extract

    deleted = delete_meeting_extract(page_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"No extract found for page_id: {page_id}")

    return {"status": "deleted", "page_id": page_id}


@router.get("/cognitive/versions")
async def list_profile_versions(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """List all historical versions of the cognitive profile."""
    from backend.app.core.ic_cognitive_store import list_profile_versions

    versions = list_profile_versions()
    return {"versions": versions, "total": len(versions)}


@router.get("/cognitive/summary")
async def get_intelligence_summary(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """
    Get a high-level summary of the IC cognitive intelligence state.

    Shows whether a profile exists, how many meetings were analyzed,
    calibration set status, and when the last extraction was run.
    """
    from backend.app.core.ic_cognitive_store import get_profile_summary

    return get_profile_summary()
