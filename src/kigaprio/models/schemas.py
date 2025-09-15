"""Pydantic models for API request/response schemas."""

from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
from enum import Enum


class JobStatus(str, Enum):
    """Job status enumeration."""

    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class FileInfo(BaseModel):
    """File information model."""

    filename: str = Field(..., description="Name of the uploaded file")
    size: int = Field(..., description="File size in bytes")
    content_type: str = Field(..., description="MIME type of the file")
    path: str = Field(..., description="Server path to the uploaded file")


class UploadResponse(BaseModel):
    """Response model for file upload."""

    message: str = Field(..., description="Success message")
    files: List[FileInfo] = Field(..., description="List of uploaded files")


class AnalysisRequest(BaseModel):
    """Request model for starting analysis."""

    file_paths: List[str] = Field(
        ...,
        description="List of file paths to analyze",
        examples=["/app/uploads/image1.jpg", "/app/uploads/document.pdf"],
    )


class AnalysisResponse(BaseModel):
    """Response model for starting analysis."""

    job_id: str = Field(..., description="Unique job identifier")
    status: JobStatus = Field(..., description="Current job status")
    message: str = Field(..., description="Status message")


class ImageAnalysis(BaseModel):
    """Image analysis results."""

    width: int = Field(..., description="Image width in pixels")
    height: int = Field(..., description="Image height in pixels")
    format: str = Field(..., description="Image format (e.g., JPEG, PNG)")
    mode: str = Field(..., description="Color mode (e.g., RGB, RGBA)")
    has_transparency: bool = Field(..., description="Whether image has transparency")
    color_count: Union[int, str] = Field(..., description="Number of colors or 'N/A'")


class PDFAnalysis(BaseModel):
    """PDF analysis results."""

    page_count: int = Field(..., description="Number of pages in the PDF")
    text_preview: str = Field(..., description="Preview of extracted text")
    character_count: int = Field(..., description="Total character count")
    metadata: Optional[Dict[str, Any]] = Field(None, description="PDF metadata")


class FileAnalysisResult(BaseModel):
    """Single file analysis result."""

    filename: str = Field(..., description="Name of the analyzed file")
    file_type: str = Field(..., description="File extension")
    file_size: int = Field(..., description="File size in bytes")
    analysis: Union[ImageAnalysis, PDFAnalysis, Dict[str, str]] = Field(
        ..., description="Analysis results (varies by file type)"
    )


class JobStatusResponse(BaseModel):
    """Job status response model."""

    status: JobStatus = Field(..., description="Current job status")
    files: List[str] = Field(..., description="List of files being processed")
    progress: int = Field(..., description="Progress percentage (0-100)")
    results: Optional[str] = Field(None, description="Path to results file")
    error: Optional[str] = Field(None, description="Error message if failed")


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
