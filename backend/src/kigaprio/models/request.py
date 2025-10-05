"""General pydantic models used in various routes"""

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(..., description="Error message")
    detail: str | None = Field(None, description="Detailed error information")
