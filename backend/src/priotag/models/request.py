"""General pydantic models used in various routes"""

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(..., description="Error message")
    detail: str | None = Field(None, description="Detailed error information")


class SuccessResponse(BaseModel):
    """Success response model."""

    message: str = Field(..., description="Success message")
    detail: str | None = Field(default=None, description="Additional details")


class DataResponse(BaseModel):
    """Response with data."""

    data: dict | list = Field(..., description="Response data")
    message: str | None = Field(default=None, description="Optional message")
