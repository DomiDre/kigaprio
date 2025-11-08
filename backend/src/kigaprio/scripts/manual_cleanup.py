#!/usr/bin/env python3
"""
Manual cleanup script for testing.

Usage:
  python -m kigaprio.scripts.manual_cleanup --priorities  # Clean old priorities
  python -m kigaprio.scripts.manual_cleanup --users       # Clean inactive users
  python -m kigaprio.scripts.manual_cleanup --all         # Run both cleanups
"""

import argparse
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
    """Run cleanup tasks based on command-line arguments."""
    parser = argparse.ArgumentParser(description="Manually run cleanup tasks")
    parser.add_argument(
        "--priorities",
        action="store_true",
        help="Clean old priority records",
    )
    parser.add_argument(
        "--users",
        action="store_true",
        help="Clean inactive user accounts",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all cleanup tasks",
    )

    args = parser.parse_args()

    # If no specific task selected, show help
    if not (args.priorities or args.users or args.all):
        parser.print_help()
        return 1

    try:
        if args.all or args.priorities:
            logger.info("=" * 60)
            logger.info("Running priority cleanup...")
            logger.info("=" * 60)
            await cleanup_old_priorities()

        if args.all or args.users:
            logger.info("=" * 60)
            logger.info("Running user cleanup...")
            logger.info("=" * 60)
            await cleanup_inactive_users()

        logger.info("=" * 60)
        logger.info("✓ Cleanup completed successfully")
        logger.info("=" * 60)
        return 0

    except Exception as e:
        logger.error(f"Error during cleanup: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
