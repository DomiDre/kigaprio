#!/usr/bin/env python3
"""
Standalone script to run cleanup tasks.

This script is designed to be run periodically by a scheduler (cron, systemd timer, etc.)
and performs both priority cleanup and user cleanup operations.
"""

import asyncio
import logging
import sys

from kigaprio.services.cleanup_service import cleanup_old_priorities
from kigaprio.services.user_cleanup_service import cleanup_inactive_users

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


async def main():
    """Run all cleanup tasks sequentially."""
    logger.info("Starting scheduled cleanup tasks")

    try:
        # Run priority cleanup
        logger.info("Running priority cleanup...")
        await cleanup_old_priorities()

        # Run user cleanup
        logger.info("Running user cleanup...")
        await cleanup_inactive_users()

        logger.info("All cleanup tasks completed successfully")
        return 0

    except Exception as e:
        logger.error(f"Error during cleanup tasks: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
