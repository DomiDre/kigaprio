"""Background tasks for monitoring and maintenance"""

import asyncio
import logging

import httpx

from kigaprio.config import settings
from kigaprio.middleware.metrics import update_health_status
from kigaprio.services.cleanup_service import cleanup_old_priorities
from kigaprio.services.pocketbase_service import POCKETBASE_URL
from kigaprio.services.redis_service import redis_health_check, update_redis_metrics
from kigaprio.services.user_cleanup_service import cleanup_inactive_users

logger = logging.getLogger(__name__)


async def monitoring_loop():
    """Background task to collect metrics from Redis and PocketBase"""
    while True:
        try:
            # Update Redis metrics
            update_redis_metrics()

            # Check PocketBase health
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(
                        f"{POCKETBASE_URL}/api/health", timeout=5.0
                    )
                    pocketbase_healthy = response.status_code == 200
            except Exception:
                pocketbase_healthy = False
            update_health_status("pocketbase", pocketbase_healthy)

            # Check Redis health
            redis_healthy = redis_health_check()
            update_health_status("redis", redis_healthy)

            # Backend is healthy if we're running this task
            update_health_status("backend", True)

        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}")

        # Update every 15 seconds
        await asyncio.sleep(15)


async def cleanup_loop():
    """Background task to periodically clean up old priority records"""
    while True:
        try:
            # Run cleanup task
            await cleanup_old_priorities()
        except Exception as e:
            logger.error(f"Error in cleanup loop: {e}")

        # Wait for configured interval (default: 24 hours)
        interval_seconds = settings.CLEANUP_INTERVAL_HOURS * 3600
        logger.info(
            f"Next cleanup scheduled in {settings.CLEANUP_INTERVAL_HOURS} hours"
        )
        await asyncio.sleep(interval_seconds)


async def user_cleanup_loop():
    """Background task to periodically clean up inactive user accounts"""
    while True:
        try:
            # Run user cleanup task
            await cleanup_inactive_users()
        except Exception as e:
            logger.error(f"Error in user cleanup loop: {e}")

        # Wait for configured interval (default: 24 hours)
        # User cleanup runs on the same schedule as priority cleanup
        interval_seconds = settings.CLEANUP_INTERVAL_HOURS * 3600
        logger.info(
            f"Next user cleanup scheduled in {settings.CLEANUP_INTERVAL_HOURS} hours"
        )
        await asyncio.sleep(interval_seconds)
