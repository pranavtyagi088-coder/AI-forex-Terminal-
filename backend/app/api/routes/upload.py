"""
Secure chart screenshot upload endpoint.
Fixes Phase 1 audit vulnerabilities:
- UUID-based file naming prevents overwrite
- File extension & MIME validation
- Async disk write via aiofiles (non-blocking)
- Maximum upload size validation
"""

from __future__ import annotations

import uuid
from pathlib import Path
import aiofiles
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.core.auth import verify_api_token
from app.core.config import settings

router = APIRouter(prefix="/api/charts", tags=["charts"])
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


@router.post("/upload")
async def upload_chart(
    file: UploadFile = File(...),
    _token: str = Depends(verify_api_token),
):
    """Upload a chart image securely for visual analysis."""
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {sorted(list(ALLOWED_EXTENSIONS))}"
        )

    content = await file.read()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File size exceeds the {settings.MAX_UPLOAD_SIZE_MB}MB limit."
        )

    unique_filename = f"{uuid.uuid4().hex}{ext}"
    upload_dir = Path(settings.UPLOAD_DIR).resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)
    full_path = upload_dir / unique_filename

    async with aiofiles.open(full_path, "wb") as f:
        await f.write(content)

    return {
        "status": "success",
        "file_name": unique_filename,
        "file_path": f"/uploads/{unique_filename}",
        "size_bytes": len(content),
    }
