"""File upload endpoints."""

from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List
import aiofiles
from pathlib import Path
import uuid
import os

from kigaprio.config import settings
from kigaprio.utils import validate_file
from kigaprio.models.schemas import UploadResponse, FileInfo, ErrorResponse

router = APIRouter()


@router.post(
    "/upload",
    response_model=UploadResponse,
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Invalid file or missing filename",
        },
        413: {"model": ErrorResponse, "description": "File too large"},
        415: {"model": ErrorResponse, "description": "Unsupported file type"},
    },
    summary="Upload Files",
    description="""
    Upload multiple files for analysis.
    
    **Supported file types:**
    - Images: JPG, JPEG, PNG, GIF, BMP, TIFF
    - Documents: PDF
    
    **Limitations:**
    - Maximum file size: 50MB per file
    - Multiple files can be uploaded simultaneously
    """,
)
async def upload_files(
    files: List[UploadFile] = File(..., description="Files to upload for analysis"),
) -> UploadResponse:
    """Upload multiple files for analysis."""

    # Validate files
    validated_files = await validate_file(files)
    uploaded_files = []

    # Ensure upload directory exists
    upload_path = Path(settings.UPLOAD_DIR)
    upload_path.mkdir(exist_ok=True)

    for file in validated_files:
        # Check if filename exists
        if not file.filename:
            raise HTTPException(status_code=400, detail="File must have a filename")

        # Generate safe filename to avoid conflicts and security issues
        safe_filename = _generate_safe_filename(file.filename)
        file_path = upload_path / safe_filename

        # Save file
        async with aiofiles.open(file_path, "wb") as f:
            content = await file.read()
            await f.write(content)

        uploaded_files.append(
            FileInfo(
                filename=safe_filename,  # Use the safe filename
                size=len(content),
                content_type=file.content_type or "application/octet-stream",
                path=str(file_path),
            )
        )

    return UploadResponse(
        message=f"Successfully uploaded {len(uploaded_files)} files",
        files=uploaded_files,
    )


def _generate_safe_filename(original_filename: str) -> str:
    """Generate a safe, unique filename."""
    # Remove any directory path components for security
    filename = os.path.basename(original_filename)

    # Split name and extension
    name, ext = os.path.splitext(filename)

    # Clean the filename (remove special characters, keep only alphanumeric, dots, dashes, underscores)
    import re

    clean_name = re.sub(r"[^\w\-_\.]", "_", name)

    # Add timestamp/uuid to make it unique
    unique_id = str(uuid.uuid4())[:8]

    # Combine everything
    safe_filename = f"{clean_name}_{unique_id}{ext}"

    return safe_filename
