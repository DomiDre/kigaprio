from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Job status enumeration."""

    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisRequest(BaseModel):
    """Request model for starting analysis."""

    file_paths: list[str] = Field(
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
    color_count: int | str = Field(..., description="Number of colors or 'N/A'")


class PDFAnalysis(BaseModel):
    """PDF analysis results."""

    page_count: int = Field(..., description="Number of pages in the PDF")
    text_preview: str = Field(..., description="Preview of extracted text")
    character_count: int = Field(..., description="Total character count")
    metadata: dict[str, Any] | None = Field(None, description="PDF metadata")


class FileAnalysisResult(BaseModel):
    """Single file analysis result."""

    filename: str = Field(..., description="Name of the analyzed file")
    file_type: str = Field(..., description="File extension")
    file_size: int = Field(..., description="File size in bytes")
    analysis: ImageAnalysis | PDFAnalysis | dict[str, str] = Field(
        ..., description="Analysis results (varies by file type)"
    )
