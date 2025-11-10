"""Health check endpoints."""

from fastapi import APIRouter

router = APIRouter()


@router.get(
    "/health",
    status_code=200,
    summary="Health Check",
    description="Check if the API is running and healthy",
)
async def health_check():
    """Health check endpoint."""
    return
