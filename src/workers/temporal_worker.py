"""
Temporal Worker for processing workflows and activities.

This worker registers all workflows and activities, enabling Temporal
to execute message processing workflows with retry logic and fault tolerance.

Per T049: Create src/workers/temporal_worker.py to register workflows and activities.
"""

import asyncio
from typing import Optional

import structlog
from temporalio.client import Client
from temporalio.worker import Worker
from temporalio.worker.workflow_sandbox import SandboxedWorkflowRunner, SandboxRestrictions

from src.activities.step1_activity import step1_parse_input_activity
from src.activities.step2_activity import step2_retrieve_context_activity
from src.activities.step3_activity import step3_query_song_activity
from src.activities.step4_activity import step4_invoke_llm_activity
from src.activities.step5_activity import step5_update_impression_activity
from src.activities.cleanup_activity import cleanup_old_conversations_activity
from src.config import settings
from src.workflows.message_workflow import ProcessMessageWorkflow
from src.workflows.cleanup_workflow import CleanupConversationsWorkflow

logger = structlog.get_logger()


async def create_temporal_client() -> Client:
    """
    Create and connect to Temporal server.

    Returns:
        Connected Temporal client instance.

    Raises:
        RuntimeError: If connection to Temporal server fails.
    """
    try:
        # Connect to Temporal server
        # Per plan.md: Temporal host and port from config
        client = await Client.connect(
            target_host=f"{settings.temporal_host}:{settings.temporal_port}",
            namespace=settings.temporal_namespace,
        )
        logger.info(
            "temporal_client_connected",
            host=settings.temporal_host,
            port=settings.temporal_port,
            namespace=settings.temporal_namespace,
        )
        return client
    except Exception as e:
        logger.error("temporal_connection_failed", error=str(e))
        raise RuntimeError(f"Failed to connect to Temporal server: {e}") from e


async def run_worker(task_queue: str = "mika-bot-task-queue") -> None:
    """
    Run Temporal worker to process workflows and activities.

    This function:
    1. Connects to Temporal server
    2. Registers all workflows and activities
    3. Starts worker to process tasks from task queue

    Args:
        task_queue: Task queue name (default: "mika-bot-task-queue").

    Example:
        >>> await run_worker()
        # Worker runs until interrupted
    """
    # Create Temporal client
    client = await create_temporal_client()

    # Configure sandbox restrictions to allow httpx and related modules
    # These modules are only used in activities, not in workflows
    # Per Temporal docs: Pass through modules that are side-effect-free and deterministic
    restrictions = SandboxRestrictions.default.with_passthrough_modules(
        "httpx",
        "httpx._api",
        "httpx._client",
        "httpx._auth",
        "httpx._models",
        "httpx._content",
        "httpx._multipart",
        "httpx._utils",
        "sniffio",
        "sniffio._impl",
        "src.services.song_query",  # Service module that uses httpx
        "src.prompts",  # Prompts module (initialized at import time, only used in activities)
    )

    # Create worker with all workflows and activities
    worker = Worker(
        client,
        task_queue=task_queue,
        workflows=[ProcessMessageWorkflow, CleanupConversationsWorkflow],
        activities=[
            step1_parse_input_activity,
            step2_retrieve_context_activity,
            step3_query_song_activity,
            step4_invoke_llm_activity,
            step5_update_impression_activity,
            cleanup_old_conversations_activity,
        ],
        workflow_runner=SandboxedWorkflowRunner(restrictions=restrictions),
    )

    logger.info(
        "temporal_worker_started",
        task_queue=task_queue,
        workflows=["ProcessMessageWorkflow", "CleanupConversationsWorkflow"],
        activities_count=6,
    )

    # Run worker (blocks until interrupted)
    try:
        await worker.run()
    except KeyboardInterrupt:
        logger.info("temporal_worker_stopped", reason="keyboard_interrupt")
    except Exception as e:
        logger.error("temporal_worker_error", error=str(e))
        raise


def main() -> None:
    """
    Main entry point for Temporal worker.

    Runs the worker in an async event loop.
    """
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        print("\nWorker stopped by user")
    except Exception as e:
        print(f"Worker error: {e}")
        raise


if __name__ == "__main__":
    main()
