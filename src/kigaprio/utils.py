from fastapi import HTTPException, UploadFile
from typing import List
from pathlib import Path

from kigaprio.config import settings


async def validate_file(files: List[UploadFile]) -> List[UploadFile]:
    """Validate uploaded files."""

    for file in files:
        if file.size is None:
            raise HTTPException(status_code=400, detail="File size is zero")
        if file.filename is None:
            raise HTTPException(status_code=400, detail="Received file without name")
        # Check file size
        if file.size > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File {file.filename} is too large. Max size: {settings.MAX_FILE_SIZE} bytes",
            )

        # Check file extension
        file_ext = Path(file.filename).suffix.lower()

        if file_ext not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=415,
                detail=f"File type {file_ext} not supported. Allowed: {settings.ALLOWED_EXTENSIONS}",
            )

    return files
