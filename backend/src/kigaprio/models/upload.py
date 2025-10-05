"""Pydantic models for API request/response schemas to upload files"""

from pydantic import BaseModel, Field


class FileInfo(BaseModel):
    """File information model."""

    filename: str = Field(..., description="Name of the uploaded file")
    size: int = Field(..., description="File size in bytes")
    content_type: str = Field(..., description="MIME type of the file")
    path: str = Field(..., description="Server path to the uploaded file")


class UploadResponse(BaseModel):
    """Response model for file upload."""

    message: str = Field(..., description="Success message")
    files: list[FileInfo] = Field(..., description="List of uploaded files")
