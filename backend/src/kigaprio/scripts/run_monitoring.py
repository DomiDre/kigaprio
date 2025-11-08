#!/usr/bin/env python3
"""
Standalone script to update monitoring metrics.

This script runs periodically to update Redis and PocketBase health metrics.
"""

import asyncio
import logging
import sys

import httpx

from kigaprio.middleware.metrics import update_health_status
from kigaprio.services.pocketbase_service import POCKETBASE_URL
from kigaprio.services.redis_service import redis_health_check, update_redis_metrics

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


async def main():
    """Update monitoring metrics."""
    try:
        # Update Redis metrics
        redis_healthy = redis_health_check()
        update_health_status("redis", redis_healthy)

        if redis_healthy:
            update_redis_metrics()

        # Check PocketBase health
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{POCKETBASE_URL}/api/health")
                pocketbase_healthy = response.status_code == 200
        except Exception as e:
            logger.warning(f"PocketBase health check failed: {e}")
            pocketbase_healthy = False

        update_health_status("pocketbase", pocketbase_healthy)

        return 0

    except Exception as e:
        logger.error(f"Error during monitoring update: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
