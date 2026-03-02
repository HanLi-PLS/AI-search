"""
Shared status store for background tasks across multiple uvicorn workers.

Uses a JSON file with file locking so that all worker processes can
read/write the same status atomically.  Each "namespace" (e.g.
"extraction", "sync") is stored as a top-level key in the JSON file.
"""

import json
import fcntl
import logging
from pathlib import Path
from typing import Any, Dict

from backend.app.config import settings

logger = logging.getLogger(__name__)

_STATUS_FILE: Path = settings.DATA_DIR / "worker_status.json"


def _ensure_file():
    """Create the status file if it doesn't exist."""
    if not _STATUS_FILE.exists():
        _STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
        _STATUS_FILE.write_text("{}")


def read_status(namespace: str) -> Dict[str, Any]:
    """Read the status dict for *namespace*, returning {} if absent."""
    _ensure_file()
    try:
        with open(_STATUS_FILE, "r") as f:
            fcntl.flock(f, fcntl.LOCK_SH)
            try:
                data = json.load(f)
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
        return data.get(namespace, {})
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("shared_status read error: %s", exc)
        return {}


def write_status(namespace: str, status: Dict[str, Any]) -> None:
    """Atomically overwrite the status dict for *namespace*."""
    _ensure_file()
    try:
        with open(_STATUS_FILE, "r+") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    data = {}
                data[namespace] = status
                f.seek(0)
                f.truncate()
                json.dump(data, f, default=str)
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
    except OSError as exc:
        logger.error("shared_status write error: %s", exc)


def update_status(namespace: str, **fields) -> None:
    """Merge *fields* into the existing status dict for *namespace*."""
    _ensure_file()
    try:
        with open(_STATUS_FILE, "r+") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    data = {}
                ns = data.get(namespace, {})
                ns.update(fields)
                data[namespace] = ns
                f.seek(0)
                f.truncate()
                json.dump(data, f, default=str)
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
    except OSError as exc:
        logger.error("shared_status update error: %s", exc)
