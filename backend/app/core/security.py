"""Security utilities - path traversal fix from Phase 1."""

from __future__ import annotations

import os
from pathlib import Path

from app.core.config import settings


class PathTraversalError(Exception):
    pass


def sanitize_filename(filename: str) -> str:
    return os.path.basename(filename)


def validate_upload_path(filename: str) -> Path:
    upload_dir = Path(settings.UPLOAD_DIR).resolve()
    safe_name = sanitize_filename(filename)
    if not safe_name:
        raise PathTraversalError("Empty filename")
    full_path = (upload_dir / safe_name).resolve()
    if not str(full_path).startswith(str(upload_dir)):
        raise PathTraversalError(f"Path traversal detected: {filename!r}")
    if not full_path.exists():
        raise FileNotFoundError(f"Upload not found: {safe_name}")
    return full_path
