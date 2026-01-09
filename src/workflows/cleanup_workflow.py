"""
Temporal Scheduled Workflow for cleaning up old conversations.

This workflow is scheduled to run daily and deletes conversations
older than 90 days to comply with privacy requirements.

Per T081: Configure cleanup job as Temporal scheduled workflow
Per FR-005: Conversation history MUST be automatically deleted after 90 days.
"""

from datetime import timedelta

from temporalio import workflow

from src.activities.cleanup_activity import cleanup_old_conversations_activity


@workflow.defn(name="cleanup_old_conversations")
class CleanupConversationsWorkflow:
    """
    Scheduled workflow for cleaning up old conversations.

    This workflow runs daily (via cron schedule) and deletes
    conversations older than 90 days.
    """

    @workflow.run
    async def run(self, retention_days: int = 90) -> int:
        """
        Execute cleanup of old conversations.

        Args:
            retention_days: Number of days to retain conversations (default: 90).

        Returns:
            Number of conversations deleted.
        """
        # Execute cleanup activity
        # Use reasonable timeout (5 minutes should be enough for cleanup)
        deleted_count = await workflow.execute_activity(
            cleanup_old_conversations_activity,
            retention_days,
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=workflow.RetryPolicy(
                initial_interval=timedelta(seconds=30),
                backoff_coefficient=2.0,
                maximum_interval=timedelta(minutes=2),
                maximum_attempts=3,
            ),
        )

        return deleted_count
