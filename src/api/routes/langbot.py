"""
LangBot webhook route.

This module handles the /webhook/langbot POST endpoint for receiving
messages from LangBot when "Mika" is mentioned in QQ groups.

Per FR-001: Only respond to messages that explicitly mention bot's name.
Per T050: Update to start Temporal workflow instead of direct step calls.
"""

from typing import Optional

import structlog
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from temporalio.client import Client

from src.api.middleware.rate_limit import check_rate_limit_middleware
from src.config import settings
from src.steps.step1 import parse_input
from src.workflows.message_workflow import ProcessMessageWorkflow

logger = structlog.get_logger()

router = APIRouter()


class LangBotWebhookRequest(BaseModel):
    """
    LangBot webhook request payload.

    Matches the structure defined in contracts/api.yaml.
    """

    group_id: str
    user_id: str
    message: str
    images: Optional[list[str]] = None
    timestamp: Optional[str] = None  # ISO format datetime string


class LangBotWebhookResponse(BaseModel):
    """
    LangBot webhook response payload.
    """

    response: str
    success: bool = True


# Global Temporal client (initialized on startup)
_temporal_client: Optional[Client] = None


async def get_temporal_client() -> Client:
    """
    Get or create Temporal client instance.

    Returns:
        Connected Temporal client.

    Raises:
        RuntimeError: If Temporal client cannot be created.
    """
    global _temporal_client

    if _temporal_client is None:
        try:
            _temporal_client = await Client.connect(
                target_host=f"{settings.temporal_host}:{settings.temporal_port}",
                namespace=settings.temporal_namespace,
            )
            logger.info(
                "temporal_client_initialized",
                host=settings.temporal_host,
                port=settings.temporal_port,
            )
        except Exception as e:
            logger.error("temporal_client_init_failed", error=str(e))
            raise RuntimeError(f"Failed to initialize Temporal client: {e}") from e

    return _temporal_client


@router.post("/langbot", response_model=LangBotWebhookResponse)
async def langbot_webhook(
    request: LangBotWebhookRequest,
    http_request: Request,
) -> LangBotWebhookResponse:
    """
    Handle LangBot webhook POST request.

    Processes incoming messages from LangBot when "Mika" is mentioned.
    Uses Temporal workflow to orchestrate the 5-step processing chain:
    1. Parse input and validate (name detection, content filtering)
    2. Retrieve user context from MongoDB
    3. Query song information (if applicable)
    4. Invoke LLM to generate response
    5. Update impression and save conversation

    Per FR-001: Only respond to messages mentioning "Mika".
    Per FR-012: Rate limiting applied via middleware.
    Per T050: Start Temporal workflow instead of direct step calls.
    Per FR-009: Temporal provides retry logic and fault tolerance.

    Args:
        request: LangBot webhook request payload.
        http_request: FastAPI request object (for rate limiting).

    Returns:
        LangBotWebhookResponse with generated response.

    Raises:
        HTTPException: If rate limit exceeded or processing fails.
    """
    # Log incoming request
    logger.info(
        "webhook_received",
        group_id=request.group_id,
        user_id=request.user_id[:8] + "...",  # Partial user ID for logging
        message_length=len(request.message),
        has_images=bool(request.images),
    )

    # Quick pre-check: Parse input to check if message mentions "Mika"
    # This allows early return without starting a workflow
    # Per FR-001: Only respond to messages mentioning bot's name
    parsed_input = parse_input(
        user_id=request.user_id,
        group_id=request.group_id,
        message=request.message,
        images=request.images,
    )

    # If message doesn't mention "Mika" or is filtered, return early
    if parsed_input is None:
        logger.info(
            "message_filtered",
            group_id=request.group_id,
            reason="no_mika_mention_or_filtered",
        )
        # Return empty response (bot doesn't respond)
        return LangBotWebhookResponse(response="", success=False)

    # Check rate limits (per FR-012)
    # Must check after parsing to get hashed_user_id
    try:
        check_rate_limit_middleware(parsed_input.hashed_user_id, request.group_id)
    except HTTPException:
        # Rate limit exceeded - re-raise HTTPException
        raise

    # Start Temporal workflow to process message
    # Per T050: Use Temporal workflow instead of direct step calls
    # Per FR-009: Temporal provides retry logic and fault tolerance
    try:
        # Get Temporal client
        client = await get_temporal_client()

        # Start workflow execution
        # Workflow ID includes user_id and timestamp for uniqueness
        workflow_id = f"process_message_{request.user_id}_{request.group_id}"

        # Execute workflow
        result = await client.execute_workflow(
            ProcessMessageWorkflow.run,
            request.user_id,
            request.group_id,
            request.message,
            request.images,
            id=workflow_id,
            task_queue="mika-bot-task-queue",
        )

        # Extract response from workflow result
        response = result.get("response", "")
        success = result.get("success", False)

        # Log workflow completion
        if success:
            logger.info(
                "workflow_completed",
                workflow_id=workflow_id,
                hashed_user_id=parsed_input.hashed_user_id[:8] + "...",
                has_song_info=bool(result.get("song_info")),
            )
        else:
            logger.info(
                "workflow_filtered",
                workflow_id=workflow_id,
                reason="message_filtered_in_workflow",
            )

        return LangBotWebhookResponse(response=response, success=success)

    except Exception as e:
        logger.error(
            "workflow_execution_failed",
            error=str(e),
            hashed_user_id=parsed_input.hashed_user_id[:8] + "...",
        )
        # Per FR-009: Graceful degradation
        # Return fallback response if workflow fails
        return LangBotWebhookResponse(
            response="Don! Mika暂时无法回应，但我会尽快回来的！🥁",
            success=False,
        )
