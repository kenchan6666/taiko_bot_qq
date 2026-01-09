"""
Temporal Activity for cleaning up old conversations.

This activity deletes conversations older than the specified retention period.

Per T081: Create cleanup activity for Temporal scheduled workflow
Per FR-005: Conversation history MUST be automatically deleted after 90 days.
"""

from datetime import datetime, timedelta

import structlog
from temporalio import activity

from src.models.conversation import Conversation
from src.services.database import init_database

logger = structlog.get_logger()


@activity.defn(name="cleanup_old_conversations")
async def cleanup_old_conversations_activity(retention_days: int = 90) -> int:
    """
    Delete conversations older than specified retention period.

    This activity is called by the cleanup scheduled workflow to
    delete expired conversations from the database.

    Args:
        retention_days: Number of days to retain conversations (default: 90).

    Returns:
        Number of conversations deleted.

    Example:
        >>> deleted_count = await cleanup_old_conversations_activity(90)
        >>> print(f"Deleted {deleted_count} conversations")
    """
    logger.info(
        "cleanup_activity_started",
        retention_days=retention_days,
        event_type="cleanup_start",
    )

    # Ensure database is initialized
    await init_database()

    # Calculate cutoff date
    cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

    # Find expired conversations
    # Use expires_at index for efficient query
    expired_conversations = await Conversation.find(
        Conversation.expires_at < cutoff_date
    ).to_list()

    count = len(expired_conversations)

    if count == 0:
        logger.info(
            "cleanup_activity_no_conversations",
            cutoff_date=cutoff_date.isoformat(),
            message="No expired conversations found",
        )
        return 0

    # Delete expired conversations in batches
    batch_size = 100
    deleted_count = 0

    for i in range(0, count, batch_size):
        batch = expired_conversations[i : i + batch_size]
        # Delete batch
        for conv in batch:
            await conv.delete()
        deleted_count += len(batch)

        logger.debug(
            "cleanup_activity_batch_deleted",
            batch_size=len(batch),
            total_deleted=deleted_count,
            total_remaining=count - deleted_count,
        )

    logger.info(
        "cleanup_activity_completed",
        conversations_deleted=deleted_count,
        cutoff_date=cutoff_date.isoformat(),
        retention_days=retention_days,
        event_type="cleanup_success",
    )

    return deleted_count
