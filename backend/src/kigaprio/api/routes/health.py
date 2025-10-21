"""Health check endpoints."""

from datetime import datetime

import httpx
from fastapi import APIRouter

from kigaprio.middleware.metrics import update_health_status
from kigaprio.services.pocketbase_service import POCKETBASE_URL
from kigaprio.services.redis_service import redis_health_check

router = APIRouter()


@router.get(
    "/health",
    status_code=200,
    summary="Health Check",
    description="Check if the API is running and healthy",
)
async def health_check():
    """Health check endpoint."""
    update_health_status("backend", True)

    # check redis
    redis_healthy = redis_health_check()
    update_health_status("redis", redis_healthy)

    # check pocketbase
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{POCKETBASE_URL}/api/health", timeout=5.0)
            pocketbase_healthy = response.status_code == 200
    except Exception:
        pocketbase_healthy = False

    update_health_status("pocketbase", pocketbase_healthy)

    overall_healthy = redis_healthy and pocketbase_healthy
    return {
        "status": "healthy" if overall_healthy else "degraded",
        "components": {
            "backend": True,
            "redis": redis_healthy,
            "pocketbase": pocketbase_healthy,
        },
        "timestamp": datetime.now().isoformat(),
    }
