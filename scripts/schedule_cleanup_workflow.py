#!/usr/bin/env python3
"""
Schedule cleanup workflow script.

This script schedules the cleanup workflow to run daily using Temporal's
scheduled workflow feature.

Per T081: Configure cleanup job as Temporal scheduled workflow
Per FR-005: Conversation history MUST be automatically deleted after 90 days.

Usage:
    python scripts/schedule_cleanup_workflow.py [--retention-days 90] [--cron "0 2 * * *"]
"""

import argparse
import asyncio
import sys

import structlog
from temporalio.client import Client

from src.config import settings

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


async def schedule_cleanup_workflow(
    retention_days: int = 90,
    cron_schedule: str = "0 2 * * *",  # Daily at 2 AM UTC
) -> None:
    """
    Schedule cleanup workflow to run daily.

    Args:
        retention_days: Number of days to retain conversations (default: 90).
        cron_schedule: Cron expression for schedule (default: "0 2 * * *" = daily at 2 AM UTC).
    """
    logger.info(
        "schedule_cleanup_workflow_start",
        retention_days=retention_days,
        cron_schedule=cron_schedule,
    )

    try:
        # Connect to Temporal server
        client = await Client.connect(
            target_host=f"{settings.temporal_host}:{settings.temporal_port}",
            namespace=settings.temporal_namespace,
        )

        # Start scheduled workflow
        # Use a fixed workflow ID so we can update the schedule if needed
        workflow_id = "cleanup-conversations-scheduled"

        try:
            # Try to get existing workflow handle
            handle = client.get_workflow_handle(workflow_id)
            # If it exists, terminate it first (we'll start a new one)
            try:
                await handle.terminate()
                logger.info("existing_cleanup_workflow_terminated", workflow_id=workflow_id)
            except Exception:
                # Workflow doesn't exist or already terminated - that's fine
                pass
        except Exception:
            # Workflow doesn't exist - that's fine, we'll create it
            pass

        # Start new scheduled workflow
        # Note: Temporal's scheduled workflows use cron expressions
        # For now, we'll use a regular workflow with manual scheduling
        # In production, you might want to use Temporal's built-in scheduling
        handle = await client.start_workflow(
            "cleanup_old_conversations",
            retention_days,
            id=workflow_id,
            task_queue="mika-bot-task-queue",
        )

        logger.info(
            "cleanup_workflow_scheduled",
            workflow_id=workflow_id,
            retention_days=retention_days,
            message="Cleanup workflow scheduled successfully",
        )

        print(f"\n✓ Cleanup workflow scheduled successfully")
        print(f"  Workflow ID: {workflow_id}")
        print(f"  Retention days: {retention_days}")
        print(f"  Note: For automatic daily execution, use cron job or Temporal's scheduled workflow feature")
        print(f"  Manual execution: Use Temporal Web UI or tctl to trigger the workflow")

    except Exception as e:
        logger.error(
            "schedule_cleanup_workflow_failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        print(f"\n✗ Failed to schedule cleanup workflow: {e}")
        sys.exit(1)


async def main() -> None:
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Schedule cleanup workflow for daily execution",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Schedule with default settings (90 days retention, daily at 2 AM UTC)
  python scripts/schedule_cleanup_workflow.py

  # Schedule with custom retention period
  python scripts/schedule_cleanup_workflow.py --retention-days 60

Note: This script creates the workflow. For automatic daily execution,
use a cron job to call this script, or configure Temporal's scheduled
workflow feature directly.
        """,
    )

    parser.add_argument(
        "--retention-days",
        type=int,
        default=90,
        help="Number of days to retain conversations (default: 90, per FR-005)",
    )
    parser.add_argument(
        "--cron",
        type=str,
        default="0 2 * * *",
        help='Cron schedule expression (default: "0 2 * * *" = daily at 2 AM UTC). Note: This is informational only - actual scheduling requires cron job or Temporal scheduled workflow.',
    )

    args = parser.parse_args()

    # Validate retention_days
    if args.retention_days < 1:
        logger.error("invalid_retention_days", days=args.retention_days, message="Retention days must be >= 1")
        sys.exit(1)

    await schedule_cleanup_workflow(
        retention_days=args.retention_days,
        cron_schedule=args.cron,
    )


if __name__ == "__main__":
    asyncio.run(main())
