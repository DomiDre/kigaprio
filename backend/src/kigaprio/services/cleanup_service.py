"""Background service for cleaning up old priority records"""

import logging
import time
from datetime import datetime

from dateutil.relativedelta import relativedelta

import httpx

from kigaprio.config import settings
from kigaprio.middleware.metrics import track_cleanup_run
from kigaprio.services.pocketbase_service import POCKETBASE_URL
from kigaprio.services.service_account import authenticate_service_account

logger = logging.getLogger(__name__)


async def cleanup_old_priorities():
    """
    Delete priority records older than the configured retention period.

    This function authenticates as admin to PocketBase, queries for all priority
    records with a month field older than the configured retention months
    (default: 2 months) from the current date, and deletes them.
    """
    start_time = time.time()
    total_deleted = 0
    total_failed = 0
    success = False

    try:
        # Calculate cutoff date using configured retention period
        now = datetime.now()
        cutoff_date = now - relativedelta(months=settings.PRIORITY_RETENTION_MONTHS)
        cutoff_month = cutoff_date.strftime("%Y-%m")

        logger.info(
            f"Starting cleanup of priorities older than {cutoff_month} "
            f"(retention: {settings.PRIORITY_RETENTION_MONTHS} months)"
        )

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Authenticate as service account to access all records
            service_token = await authenticate_service_account(client)

            if not service_token:
                logger.error(
                    "Cannot proceed with cleanup without service account authentication"
                )
                return

            headers = {"Authorization": f"Bearer {service_token}"}

            # Query for old priority records
            # We'll paginate through all old records
            page = 1

            while True:
                response = await client.get(
                    f"{POCKETBASE_URL}/api/collections/priorities/records",
                    headers=headers,
                    params={
                        "filter": f'month < "{cutoff_month}"',
                        "perPage": 100,  # Process in batches of 100
                        "page": page,
                    },
                )

                if response.status_code != 200:
                    logger.error(
                        f"Failed to fetch old priorities (page {page}): "
                        f"{response.status_code} - {response.text}"
                    )
                    break

                data = response.json()
                items = data.get("items", [])

                if not items:
                    # No more records to process
                    break

                logger.info(
                    f"Processing page {page}: found {len(items)} priority records to delete"
                )

                # Delete each old record
                for item in items:
                    record_id = item["id"]
                    month = item.get("month", "unknown")
                    user_id = item.get("userId", "unknown")

                    try:
                        delete_response = await client.delete(
                            f"{POCKETBASE_URL}/api/collections/priorities/records/{record_id}",
                            headers=headers,
                        )

                        if delete_response.status_code in [200, 204]:
                            total_deleted += 1
                            logger.debug(
                                f"Deleted priority record {record_id} "
                                f"(month: {month}, user: {user_id})"
                            )
                        else:
                            total_failed += 1
                            logger.warning(
                                f"Failed to delete priority {record_id}: "
                                f"{delete_response.status_code} - {delete_response.text}"
                            )
                    except Exception as e:
                        total_failed += 1
                        logger.error(f"Error deleting priority {record_id}: {e}")

                # Check if there are more pages
                if len(items) < 100:
                    # Last page
                    break

                page += 1

            if total_deleted == 0 and total_failed == 0:
                logger.info("No old priorities to clean up")
            else:
                logger.info(
                    f"Cleanup complete: {total_deleted} deleted, {total_failed} failed"
                )

            # Mark as successful if we completed without exceptions
            success = True

    except httpx.RequestError as e:
        logger.error(f"Network error during cleanup: {e}")
    except Exception as e:
        logger.error(f"Unexpected error during cleanup: {e}")
    finally:
        # Track metrics regardless of success/failure
        duration = time.time() - start_time
        track_cleanup_run(success, total_deleted, total_failed, duration)
