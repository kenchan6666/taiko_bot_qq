#!/usr/bin/env python3
"""
Cleanup script for old conversations.

This script deletes conversations older than 90 days to comply with
privacy requirements and storage cost control.

Per T080: Create scripts/cleanup_old_conversations.py for 90-day conversation deletion
Per FR-005: Conversation history MUST be automatically deleted after 90 days.

Usage:
    python scripts/cleanup_old_conversations.py [--dry-run] [--days 90]

Example:
    # Dry run (show what would be deleted)
    python scripts/cleanup_old_conversations.py --dry-run

    # Actually delete old conversations
    python scripts/cleanup_old_conversations.py

    # Delete conversations older than 60 days
    python scripts/cleanup_old_conversations.py --days 60
"""

import argparse
import asyncio
import sys
from datetime import datetime, timedelta

import structlog

from src.config import settings
from src.models.conversation import Conversation
from src.services.database import init_database

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO level
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=False,
)

logger = structlog.get_logger()


async def cleanup_old_conversations(
    days: int = 90, dry_run: bool = False
) -> int:
    """
    Delete conversations older than specified days.

    Args:
        days: Number of days to retain (default: 90, per FR-005).
        dry_run: If True, only count conversations without deleting.

    Returns:
        Number of conversations deleted (or would be deleted in dry-run mode).
    """
    logger.info(
        "cleanup_started",
        days=days,
        dry_run=dry_run,
        event_type="cleanup_start",
    )

    # Calculate cutoff date
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    # Find expired conversations
    # Use expires_at index for efficient query
    expired_conversations = await Conversation.find(
        Conversation.expires_at < cutoff_date
    ).to_list()

    count = len(expired_conversations)

    if dry_run:
        logger.info(
            "cleanup_dry_run",
            conversations_found=count,
            cutoff_date=cutoff_date.isoformat(),
            message=f"Would delete {count} conversations older than {days} days",
        )
        return count

    # Delete expired conversations
    if count > 0:
        # Delete in batches for efficiency
        batch_size = 100
        deleted_count = 0

        for i in range(0, count, batch_size):
            batch = expired_conversations[i : i + batch_size]
            # Delete batch
            for conv in batch:
                await conv.delete()
            deleted_count += len(batch)

            logger.debug(
                "cleanup_batch_deleted",
                batch_size=len(batch),
                total_deleted=deleted_count,
                total_remaining=count - deleted_count,
            )

        logger.info(
            "cleanup_completed",
            conversations_deleted=deleted_count,
            cutoff_date=cutoff_date.isoformat(),
            event_type="cleanup_success",
        )
    else:
        logger.info(
            "cleanup_no_conversations",
            cutoff_date=cutoff_date.isoformat(),
            message="No expired conversations found",
        )

    return count


async def main() -> None:
    """Main cleanup function."""
    parser = argparse.ArgumentParser(
        description="Cleanup old conversations (90-day retention)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run (show what would be deleted)
  python scripts/cleanup_old_conversations.py --dry-run

  # Delete conversations older than 90 days (default)
  python scripts/cleanup_old_conversations.py

  # Delete conversations older than 60 days
  python scripts/cleanup_old_conversations.py --days 60
        """,
    )

    parser.add_argument(
        "--days",
        type=int,
        default=90,
        help="Number of days to retain conversations (default: 90, per FR-005)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting",
    )

    args = parser.parse_args()

    # Validate days
    if args.days < 1:
        logger.error("invalid_days", days=args.days, message="Days must be >= 1")
        sys.exit(1)

    try:
        # Initialize database connection
        await init_database()
        logger.info("database_connected", event_type="initialization")

        # Run cleanup
        deleted_count = await cleanup_old_conversations(
            days=args.days, dry_run=args.dry_run
        )

        if args.dry_run:
            print(f"\n✓ Dry run complete: {deleted_count} conversations would be deleted")
            print(f"  (Conversations older than {args.days} days)")
        else:
            print(f"\n✓ Cleanup complete: {deleted_count} conversations deleted")
            print(f"  (Conversations older than {args.days} days)")

        sys.exit(0)

    except Exception as e:
        logger.error(
            "cleanup_failed",
            error=str(e),
            error_type=type(e).__name__,
            event_type="cleanup_error",
        )
        print(f"\n✗ Cleanup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
