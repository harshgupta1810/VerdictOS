"""File upload endpoint.

Accepts multipart PDF/DOCX files, persists them to UPLOAD_DIR,
and returns their absolute server-side paths for use in deal creation.
"""

import logging
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from src.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["upload"])

_ALLOWED_SUFFIXES = {".pdf", ".docx", ".doc"}


@router.post("/upload")
async def upload_documents(files: list[UploadFile]) -> JSONResponse:
    """Save uploaded documents and return their server-side absolute paths."""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")

    upload_dir = Path(settings.upload_dir).resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)

    saved_paths: list[str] = []

    for file in files:
        filename = file.filename or ""
        suffix = Path(filename).suffix.lower()
        if suffix not in _ALLOWED_SUFFIXES:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type '{suffix}'. Allowed: {_ALLOWED_SUFFIXES}",
            )

        # Prefix with UUID to avoid collisions on same-named files
        safe_name = f"{uuid.uuid4().hex}_{filename}"
        dest = upload_dir / safe_name

        content = await file.read()
        dest.write_bytes(content)
        saved_paths.append(str(dest))
        logger.info("Saved upload: %s (%d bytes)", dest, len(content))

    return JSONResponse({"paths": saved_paths})
