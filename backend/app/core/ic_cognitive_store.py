"""
IC Cognitive Profile Store — persists extracted IC intelligence as versioned JSON.

Stores:
- Committee-level cognitive profile
- Per-member profiles (when attribution data is available)
- Calibration set (annotated meeting examples)
- Per-meeting structured extracts (Pass 1-2 outputs)

Profiles are stored in data/ic_profiles/ as JSON files, version-controlled
and human-reviewable. No vector database needed — the distilled intelligence
fits in a single LLM context window.
"""
import fcntl
import json
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.app.config import settings

logger = logging.getLogger(__name__)

# Base directory for all IC cognitive artifacts
PROFILES_DIR = settings.DATA_DIR / "ic_profiles"
EXTRACTS_DIR = PROFILES_DIR / "meeting_extracts"
VERSIONS_DIR = PROFILES_DIR / "versions"


def _ensure_dirs():
    """Create profile directories if they don't exist."""
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    EXTRACTS_DIR.mkdir(parents=True, exist_ok=True)
    VERSIONS_DIR.mkdir(parents=True, exist_ok=True)


def _save_json(path: Path, data: Any):
    """Write JSON with pretty-printing for human readability (exclusive lock)."""
    with open(path, "w", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def _load_json(path: Path) -> Any:
    """Load a JSON file, return None if missing (shared lock)."""
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_SH)
        try:
            return json.load(f)
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


# ── Per-meeting extracts (Pass 1 & 2 outputs) ──────────────────────────────

def save_meeting_extract(page_id: str, extract: Dict[str, Any]):
    """
    Save the structured extract for a single meeting (Pass 1 + Pass 2 output).

    Args:
        page_id: Confluence page ID or upload file ID
        extract: Dict containing structural + reasoning extraction results
    """
    _ensure_dirs()
    extract["extracted_at"] = datetime.now(timezone.utc).isoformat()
    path = EXTRACTS_DIR / f"{page_id}.json"
    _save_json(path, extract)
    logger.info(f"Saved meeting extract: {path.name}")


def load_meeting_extract(page_id: str) -> Optional[Dict[str, Any]]:
    """Load the structured extract for a single meeting."""
    path = EXTRACTS_DIR / f"{page_id}.json"
    return _load_json(path)


def list_meeting_extracts() -> List[Dict[str, Any]]:
    """List all available meeting extracts with metadata."""
    _ensure_dirs()
    extracts = []
    for path in sorted(EXTRACTS_DIR.glob("*.json")):
        data = _load_json(path)
        if data:
            extracts.append({
                "page_id": path.stem,
                "meeting_title": data.get("meeting_title", ""),
                "meeting_date": data.get("meeting_date", ""),
                "extracted_at": data.get("extracted_at", ""),
                "num_qa_items": len(data.get("qa_items", [])),
            })
    return extracts


def get_meeting_extracts_by_date(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Load all meeting extracts, optionally filtered by date range.

    Args:
        date_from: Include meetings on or after this date (YYYY-MM-DD)
        date_to: Include meetings on or before this date (YYYY-MM-DD)

    Returns:
        List of full extract dicts, sorted by meeting_date
    """
    _ensure_dirs()
    extracts = []
    for path in EXTRACTS_DIR.glob("*.json"):
        data = _load_json(path)
        if not data:
            continue
        meeting_date = data.get("meeting_date", "")
        if date_from and meeting_date < date_from:
            continue
        if date_to and meeting_date > date_to:
            continue
        extracts.append(data)

    extracts.sort(key=lambda x: x.get("meeting_date", ""))
    return extracts


def delete_meeting_extract(page_id: str) -> bool:
    """Delete a single meeting extract."""
    path = EXTRACTS_DIR / f"{page_id}.json"
    if path.exists():
        path.unlink()
        logger.info(f"Deleted meeting extract: {page_id}")
        return True
    return False


# ── Cognitive Profile (Pass 3 output) ──────────────────────────────────────

def save_cognitive_profile(profile: Dict[str, Any]):
    """
    Save the committee-level cognitive profile (Pass 3 output).
    Automatically versions the previous profile before overwriting.
    """
    _ensure_dirs()
    current_path = PROFILES_DIR / "cognitive_profile.json"

    # Version the existing profile before overwriting
    existing = _load_json(current_path) if current_path.exists() else None
    if existing:
        version_ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        version_path = VERSIONS_DIR / f"cognitive_profile_{version_ts}.json"
        shutil.copy2(current_path, version_path)
        logger.info(f"Versioned previous profile: {version_path.name}")

    # Compute next version from what we already loaded (avoids redundant read)
    next_version = (existing["version"] + 1) if existing and "version" in existing else 1

    profile["updated_at"] = datetime.now(timezone.utc).isoformat()
    profile["version"] = next_version
    _save_json(current_path, profile)
    logger.info(f"Saved cognitive profile v{profile['version']}")


def load_cognitive_profile() -> Optional[Dict[str, Any]]:
    """Load the current committee-level cognitive profile."""
    path = PROFILES_DIR / "cognitive_profile.json"
    return _load_json(path)


def list_profile_versions() -> List[Dict[str, str]]:
    """List all versioned cognitive profiles."""
    _ensure_dirs()
    versions = []
    for path in sorted(VERSIONS_DIR.glob("cognitive_profile_*.json"), reverse=True):
        data = _load_json(path)
        versions.append({
            "filename": path.name,
            "version": data.get("version", "?") if data else "?",
            "updated_at": data.get("updated_at", "") if data else "",
            "date_range": data.get("date_range", {}) if data else {},
        })
    return versions


# ── Calibration Set (Pass 4 output) ───────────────────────────────────────

def save_calibration_set(calibration: Dict[str, Any]):
    """Save the calibration set (annotated exemplar meetings)."""
    _ensure_dirs()
    current_path = PROFILES_DIR / "calibration_set.json"

    # Version existing
    if current_path.exists():
        version_ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        version_path = VERSIONS_DIR / f"calibration_set_{version_ts}.json"
        shutil.copy2(current_path, version_path)

    calibration["updated_at"] = datetime.now(timezone.utc).isoformat()
    _save_json(current_path, calibration)
    logger.info(f"Saved calibration set ({len(calibration.get('examples', []))} examples)")


def load_calibration_set() -> Optional[Dict[str, Any]]:
    """Load the current calibration set."""
    path = PROFILES_DIR / "calibration_set.json"
    return _load_json(path)


# ── Incremental Update Tracking ───────────────────────────────────────────

def save_extraction_state(state: Dict[str, Any]):
    """
    Save the extraction pipeline state for incremental updates.
    Tracks which meetings have been processed and when the last
    synthesis was run.
    """
    _ensure_dirs()
    state["saved_at"] = datetime.now(timezone.utc).isoformat()
    _save_json(PROFILES_DIR / "extraction_state.json", state)


def load_extraction_state() -> Optional[Dict[str, Any]]:
    """Load the extraction pipeline state."""
    return _load_json(PROFILES_DIR / "extraction_state.json")


# ── Helpers ────────────────────────────────────────────────────────────────

def get_profile_summary() -> Dict[str, Any]:
    """
    Get a summary of the current IC cognitive intelligence state.
    Useful for API responses and dashboard display.
    """
    profile = load_cognitive_profile()
    calibration = load_calibration_set()
    state = load_extraction_state()
    extracts = list_meeting_extracts()

    return {
        "has_cognitive_profile": profile is not None,
        "profile_version": profile.get("version") if profile else None,
        "profile_updated_at": profile.get("updated_at") if profile else None,
        "profile_date_range": profile.get("date_range", {}) if profile else {},
        "num_meeting_extracts": len(extracts),
        "has_calibration_set": calibration is not None,
        "num_calibration_examples": len(calibration.get("examples", [])) if calibration else 0,
        "last_extraction": state.get("saved_at") if state else None,
        "processed_page_ids": state.get("processed_page_ids", []) if state else [],
    }
