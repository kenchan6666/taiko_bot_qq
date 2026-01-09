"""
LangBot webhook route.

This module handles the /webhook/langbot POST endpoint for receiving
messages from LangBot when "Mika" is mentioned in QQ groups.

Per FR-001: Only respond to messages that explicitly mention bot's name.
Per T050: Update to start Temporal workflow instead of direct step calls.
"""

from datetime import datetime, timedelta
from typing import Any, Optional

import httpx
import structlog
from fastapi import APIRouter, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ValidationError
from temporalio.client import Client, WorkflowFailureError
from temporalio.exceptions import TimeoutError as TemporalTimeoutError

from src.api.middleware.rate_limit import check_rate_limit_middleware
from src.config import settings
from src.steps.step1 import parse_input
from src.workflows.message_workflow import ProcessMessageWorkflow

logger = structlog.get_logger()

router = APIRouter()


class LangBotWebhookRequest(BaseModel):
    """
    LangBot webhook request payload (simplified format).

    Matches the structure defined in contracts/api.yaml.
    Used for direct API calls or simplified webhook format.
    """

    group_id: str
    user_id: str
    message: str
    images: Optional[list[str]] = None
    timestamp: Optional[str] = None  # ISO format datetime string


class LangBotEventRequest(BaseModel):
    """
    LangBot event-based webhook request payload.

    Matches the actual format sent by LangBot:
    {
      "uuid": "...",
      "event_type": "bot.person_message" | "bot.group_message",
      "data": {
        "bot_uuid": "...",
        "adapter_name": "AiocqhttpAdapter",
        "sender": {"id": "...", "name": "..."},
        "message": [{"type": "Plain", "text": "..."}, ...],
        "timestamp": 1234567890.0,
        "group_id": "..." (for group messages)
      }
    }
    """

    uuid: str
    event_type: str
    data: dict[str, Any]


class LangBotWebhookResponse(BaseModel):
    """
    LangBot webhook response payload.
    
    LangBot expects response in format:
    {
      "status": "ok",
      "skip_pipeline": false,
      "message": [{"type": "Plain", "text": "回复内容"}]  # Optional, for returning message
    }
    
    For compatibility, we also support:
    {
      "response": "回复内容",
      "success": true
    }
    """

    # Primary response format (LangBot standard)
    status: str = "ok"
    skip_pipeline: bool = False
    message: Optional[list[dict[str, Any]]] = None
    
    # Legacy/compatibility fields
    response: Optional[str] = None
    success: bool = True


# Global Temporal client (initialized on startup)
_temporal_client: Optional[Client] = None

# Global HTTP client for LangBot API (initialized on first use)
_langbot_http_client: Optional[httpx.AsyncClient] = None


async def get_langbot_http_client() -> httpx.AsyncClient:
    """
    Get or create HTTP client for LangBot API.

    Returns:
        HTTP client instance.
    """
    global _langbot_http_client
    if _langbot_http_client is None:
        _langbot_http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0),  # 10 second timeout
        )
    return _langbot_http_client


async def _send_langbot_message(
    bot_uuid: Optional[str],
    event_type: str,
    target_id: str,
    message: str,
) -> None:
    """
    Send message via LangBot API.

    Args:
        bot_uuid: Bot UUID from webhook event.
        event_type: Event type ("bot.person_message" or "bot.group_message").
        target_id: Target ID (user_id for private, group_id for group).
        message: Message text to send.

    Raises:
        ValueError: If bot_uuid is missing or API key is not configured.
        httpx.HTTPError: If API request fails.
    """
    if not settings.langbot_api_key:
        raise ValueError("LangBot API key not configured")
    
    if not bot_uuid:
        raise ValueError("Bot UUID not available in webhook event")
    
    # Determine target type based on event type
    if event_type == "bot.person_message":
        target_type = "person"
    elif event_type == "bot.group_message":
        target_type = "group"
    else:
        raise ValueError(f"Unknown event type: {event_type}")
    
    # Build API URL
    api_url = f"{settings.langbot_api_base_url}/api/v1/platform/bots/{bot_uuid}/send_message"
    
    # Build request payload
    payload = {
        "target_type": target_type,
        "target_id": target_id,
        "message_chain": [
            {
                "type": "Plain",
                "text": message,
            }
        ],
    }
    
    # Get HTTP client
    client = await get_langbot_http_client()
    
    # Make API request
    try:
        logger.info(
            "langbot_api_send_starting",
            bot_uuid=bot_uuid[:8] + "..." if bot_uuid else "unknown",
            target_type=target_type,
            target_id=target_id[:8] + "..." if target_id else "unknown",
            message_length=len(message),
        )
        
        response = await client.post(
            api_url,
            json=payload,
            headers={
                "X-API-Key": settings.langbot_api_key,
                "Content-Type": "application/json",
            },
        )
        
        response.raise_for_status()
        
        logger.info(
            "langbot_api_send_success",
            bot_uuid=bot_uuid[:8] + "..." if bot_uuid else "unknown",
            target_type=target_type,
            status_code=response.status_code,
        )
    except httpx.HTTPStatusError as e:
        logger.error(
            "langbot_api_send_http_error",
            status_code=e.response.status_code,
            error_detail=e.response.text[:200] if e.response.text else None,
            bot_uuid=bot_uuid[:8] + "..." if bot_uuid else "unknown",
        )
        raise
    except httpx.HTTPError as e:
        logger.error(
            "langbot_api_send_network_error",
            error=str(e),
            bot_uuid=bot_uuid[:8] + "..." if bot_uuid else "unknown",
        )
        raise


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


def convert_langbot_event_to_webhook_request(
    event: LangBotEventRequest,
) -> LangBotWebhookRequest:
    """
    Convert LangBot event format to simplified webhook request format.

    Args:
        event: LangBot event request.

    Returns:
        Converted webhook request.

    Raises:
        ValueError: If event format is invalid or missing required fields.
    """
    data = event.data
    sender = data.get("sender", {})
    user_id = sender.get("id", "")
    
    if not user_id:
        raise ValueError("Missing sender.id in LangBot event data")

    # Extract message text from message array
    # LangBot sends messages as: [{"type": "Source", ...}, {"type": "Plain", "text": "..."}, ...]
    message_parts = []
    images = []
    
    for msg_item in data.get("message", []):
        msg_type = msg_item.get("type", "")
        if msg_type == "Plain":
            text = msg_item.get("text", "")
            if text:
                message_parts.append(text)
        elif msg_type == "Image":
            # Extract image URL or base64 data
            image_url = msg_item.get("url", "") or msg_item.get("data", "")
            if image_url:
                images.append(image_url)
        # Log other message types for debugging
        elif msg_type not in ("Source", "At", "Face"):  # Common non-text types
            logger.debug(
                "langbot_unknown_message_type",
                msg_type=msg_type,
                msg_item_preview=str(msg_item)[:100],
            )
    
    message_text = "".join(message_parts)
    
    # Log if message extraction resulted in empty text
    if not message_text and data.get("message"):
        logger.warning(
            "langbot_empty_message_extracted",
            message_array_length=len(data.get("message", [])),
            message_array_preview=str(data.get("message", []))[:200],
        )
    
    # Extract group_id (for group messages) or use empty string for private messages
    # Determine message type: private (person_message) or group (group_message)
    is_private_message = event.event_type == "bot.person_message"
    is_group_message = event.event_type == "bot.group_message"
    
    # Try multiple possible locations for group_id
    # LangBot may send it as "group_id" or as "group" object with "id" field
    group_id = ""
    if is_group_message:
        # Try direct group_id field first
        group_id = data.get("group_id", "")
        
        # If not found, try "group" object
        if not group_id:
            group_obj = data.get("group")
            if isinstance(group_obj, dict):
                group_id = group_obj.get("id", "")
            elif isinstance(group_obj, str):
                # Sometimes group might be just the ID string
                group_id = group_obj
        
        if not group_id:
            logger.warning(
                "langbot_group_message_missing_group_id",
                event_type=event.event_type,
                data_keys=list(data.keys()),
                group_obj_type=type(data.get("group")).__name__ if data.get("group") else None,
                group_obj_preview=str(data.get("group"))[:100] if data.get("group") else None,
            )
        else:
            logger.debug(
                "langbot_group_message_detected",
                group_id=group_id[:8] + "..." if group_id else "unknown",
            )
    elif is_private_message:
        # Private message - no group_id
        group_id = ""
        logger.debug(
            "langbot_private_message_detected",
            user_id=user_id[:8] + "..." if user_id else "unknown",
        )
    else:
        logger.warning(
            "langbot_unknown_event_type",
            event_type=event.event_type,
        )
    
    # Extract timestamp
    timestamp = data.get("timestamp")
    timestamp_str = None
    if timestamp:
        from datetime import datetime
        if isinstance(timestamp, (int, float)):
            timestamp_str = datetime.fromtimestamp(timestamp).isoformat()
        else:
            timestamp_str = str(timestamp)
    
    return LangBotWebhookRequest(
        group_id=group_id,
        user_id=user_id,
        message=message_text,
        images=images if images else None,
        timestamp=timestamp_str,
    )


@router.post("", response_model=LangBotWebhookResponse)
async def langbot_webhook_root(
    http_request: Request,
) -> LangBotWebhookResponse:
    """
    Root webhook endpoint (redirects to /langbot for backward compatibility).

    This endpoint accepts requests at /webhook and forwards them to /webhook/langbot.
    Supports both simplified format and LangBot event format.
    """
    logger.warning(
        "webhook_root_deprecated",
        path=http_request.url.path,
        message="Using deprecated /webhook endpoint, should use /webhook/langbot",
    )
    
    # Parse request body manually to handle both formats
    try:
        body = await http_request.json()
    except Exception as e:
        logger.error(
            "webhook_parse_failed",
            error=str(e),
            path=http_request.url.path,
        )
        raise HTTPException(
            status_code=422,
            detail=f"Invalid request body: {str(e)}",
        )
    
    # Try to parse as LangBot event format first
    event: Optional[LangBotEventRequest] = None
    try:
        event = LangBotEventRequest(**body)
        request = convert_langbot_event_to_webhook_request(event)
        logger.info(
            "webhook_event_format_detected",
            event_type=event.event_type,
            has_group_id=bool(request.group_id),
            extracted_message_preview=request.message[:50] if request.message else "(empty)",
            extracted_message_length=len(request.message),
        )
    except (ValidationError, ValueError) as e:
        # Fall back to simplified format
        event = None  # Simplified format doesn't have event structure
        try:
            request = LangBotWebhookRequest(**body)
            logger.info(
                "webhook_simplified_format_detected",
                message_preview=request.message[:50] if request.message else "(empty)",
            )
        except ValidationError as e2:
            logger.error(
                "webhook_validation_failed",
                error=str(e2),
                body_preview=str(body)[:200],
            )
            raise HTTPException(
                status_code=422,
                detail=f"Invalid request format: {str(e2)}",
            )
    
    # Process the request directly (already parsed)
    # Pass event if available (for bot_uuid extraction)
    return await _process_webhook_request(request, http_request, event=event)


async def _process_webhook_request(
    request: LangBotWebhookRequest,
    http_request: Request,
    event: Optional[LangBotEventRequest] = None,
) -> LangBotWebhookResponse:
    """
    Internal function to process webhook request.

    This function handles the actual processing logic and is called by
    both langbot_webhook_root and langbot_webhook endpoints.

    Args:
        request: Parsed webhook request.
        http_request: FastAPI request object (for rate limiting).

    Returns:
        LangBotWebhookResponse with generated response.

    Raises:
        HTTPException: If rate limit exceeded or processing fails.
    """
    # Determine message type for logging
    message_type = "private" if not request.group_id else "group"
    
    # Log incoming request with message preview
    logger.info(
        "webhook_received",
        message_type=message_type,  # "private" or "group"
        group_id=request.group_id if request.group_id else "(private)",
        user_id=request.user_id[:8] + "...",  # Partial user ID for logging
        message_length=len(request.message),
        message_preview=request.message[:50] if request.message else "(empty)",  # Log first 50 chars
        has_images=bool(request.images),
    )

    # Quick pre-check: Parse input to check if message mentions "Mika"
    # This allows early return without starting a workflow
    # Per FR-001: Only respond to messages mentioning bot's name
    # Per FR-013 Enhancement: Intent detection is now part of parsing
    parsed_input = await parse_input(
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
            user_id=request.user_id[:8] + "...",
            message_preview=request.message[:50] if request.message else "(empty)",
            reason="no_mika_mention_or_filtered",
            hint="Message must contain 'Mika', '米卡', or 'mika酱' to trigger response",
        )
        # Return empty response (bot doesn't respond)
        # Note: Set skip_pipeline=false to let LangBot handle filtered messages
        return LangBotWebhookResponse(
            status="ok",
            skip_pipeline=False,  # Let LangBot handle filtered messages
            message=None,
            response="",
            success=False,
        )

    # Validate group whitelist (per T068)
    # Private messages (no group_id) are always allowed
    # Group messages must be in whitelist if whitelist is configured
    if request.group_id:  # Only check for group messages
        allowed_groups = settings.get_langbot_allowed_groups_list()
        if allowed_groups:  # Whitelist is configured
            if request.group_id not in allowed_groups:
                logger.warning(
                    "group_not_in_whitelist",
                    group_id=request.group_id,
                    user_id=request.user_id[:8] + "...",
                    allowed_groups_count=len(allowed_groups),
                    message="Group ID not in whitelist, request rejected",
                )
                # Return empty response (bot doesn't respond to unauthorized groups)
                return LangBotWebhookResponse(
                    status="ok",
                    skip_pipeline=False,  # Let LangBot handle unauthorized groups
                    message=None,
                    response="",
                    success=False,
                )
            else:
                logger.debug(
                    "group_whitelist_passed",
                    group_id=request.group_id[:8] + "...",
                    message="Group ID is in whitelist",
                )
        else:
            # No whitelist configured - allow all groups
            logger.debug(
                "group_whitelist_not_configured",
                group_id=request.group_id[:8] + "...",
                message="No whitelist configured, allowing all groups",
            )

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
        # Workflow ID includes user_id, group_id, and timestamp for uniqueness
        # Use timestamp to ensure unique ID even for rapid consecutive messages
        timestamp_ms = int(datetime.utcnow().timestamp() * 1000)
        group_id_part = request.group_id if request.group_id else "private"
        workflow_id = f"process_message_{request.user_id}_{group_id_part}_{timestamp_ms}"

        # Execute workflow
        # Note: execute_workflow requires args as a list/sequence, not individual positional arguments
        # Set timeouts: execution_timeout (total), run_timeout (single run), task_timeout (single task)
        logger.info(
            "workflow_starting",
            workflow_id=workflow_id,
            user_id=request.user_id[:8] + "...",
            message_type="private" if not request.group_id else "group",
        )
        
        try:
            result = await client.execute_workflow(
                ProcessMessageWorkflow.run,
                args=[
                    request.user_id,
                    request.group_id,
                    request.message,
                    request.images,
                ],
                id=workflow_id,
                task_queue="mika-bot-task-queue",
                execution_timeout=timedelta(minutes=2),  # Total timeout: 2 minutes
                run_timeout=timedelta(minutes=1),  # Single run timeout: 1 minute
                task_timeout=timedelta(seconds=30),  # Single task timeout: 30 seconds
            )
            logger.info(
                "workflow_completed",
                workflow_id=workflow_id,
                success=result.get("success", False),
                response_length=len(result.get("response", "")),
            )
        except TemporalTimeoutError as timeout_error:
            # Workflow timed out - likely because Worker is not running
            logger.error(
                "workflow_timeout",
                workflow_id=workflow_id,
                error=str(timeout_error),
                hint="Worker may not be running. Start with: poetry run python -m src.workers.temporal_worker",
            )
            # Return fallback response instead of raising
            fallback_text = "Don! Mika暂时无法回应，工作流执行超时。请检查 Worker 是否在运行。🥁"
            return LangBotWebhookResponse(
                status="ok",
                skip_pipeline=True,
                message=[{"type": "Plain", "text": fallback_text}],
                response=fallback_text,
                success=False,
            )
        except WorkflowFailureError as workflow_failure:
            # Workflow failed during execution
            logger.error(
                "workflow_failure",
                workflow_id=workflow_id,
                error=str(workflow_failure),
                error_type=type(workflow_failure).__name__,
            )
            # Return fallback response
            fallback_text = "Don! Mika处理消息时出错了，但我会尽快恢复的！🥁"
            return LangBotWebhookResponse(
                status="ok",
                skip_pipeline=True,
                message=[{"type": "Plain", "text": fallback_text}],
                response=fallback_text,
                success=False,
            )
        except Exception as workflow_error:
            logger.error(
                "workflow_execution_error",
                workflow_id=workflow_id,
                error=str(workflow_error),
                error_type=type(workflow_error).__name__,
            )
            # Return fallback response for other errors
            fallback_text = "Don! Mika遇到了意外错误，但我会尽快回来的！🥁"
            return LangBotWebhookResponse(
                status="ok",
                skip_pipeline=True,
                message=[{"type": "Plain", "text": fallback_text}],
                response=fallback_text,
                success=False,
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

        # Format response for LangBot
        # LangBot expects message in format: [{"type": "Plain", "text": "..."}]
        message_array = None
        if response:
            message_array = [{"type": "Plain", "text": response}]

        # Log the response we're sending to LangBot
        logger.info(
            "langbot_response_prepared",
            skip_pipeline=True,
            has_message=bool(message_array),
            message_length=len(response) if response else 0,
            message_preview=response[:50] if response else None,
            has_event=bool(event),
            has_api_key=bool(settings.langbot_api_key),
        )

        # Send message via LangBot API if API key is configured and event is available
        if response and success:
            if not event:
                logger.warning(
                    "langbot_api_send_skipped",
                    reason="event_not_available",
                    hint="Webhook request may be in simplified format, not event format",
                    has_response=bool(response),
                    has_success=success,
                )
            elif not settings.langbot_api_key:
                logger.warning(
                    "langbot_api_send_skipped",
                    reason="api_key_not_configured",
                    hint="Set LANGBOT_API_KEY in .env file",
                    has_event=bool(event),
                    has_response=bool(response),
                )
            else:
                # All conditions met - send message
                logger.info(
                    "langbot_api_send_attempting",
                    bot_uuid=event.data.get("bot_uuid", "unknown")[:8] + "..." if event.data.get("bot_uuid") else "unknown",
                    event_type=event.event_type,
                    target_id=request.user_id[:8] + "..." if not request.group_id else request.group_id[:8] + "...",
                )
                try:
                    await _send_langbot_message(
                        bot_uuid=event.data.get("bot_uuid"),
                        event_type=event.event_type,
                        target_id=request.user_id if not request.group_id else request.group_id,
                        message=response,
                    )
                except Exception as send_error:
                    # Log error but don't fail the webhook response
                    logger.error(
                        "langbot_api_send_failed",
                        error=str(send_error),
                        error_type=type(send_error).__name__,
                        bot_uuid=event.data.get("bot_uuid", "unknown")[:8] + "..." if event.data.get("bot_uuid") else "unknown",
                    )
        else:
            logger.debug(
                "langbot_api_send_skipped",
                reason="no_response_or_not_success",
                has_response=bool(response),
                success=success,
            )

        return LangBotWebhookResponse(
            status="ok",
            skip_pipeline=True,  # Skip LangBot's pipeline to use our response
            message=message_array,
            response=response,  # Keep for compatibility
            success=success,
        )

    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        logger.error(
            "workflow_execution_failed",
            error=str(e),
            error_type=type(e).__name__,
            hashed_user_id=parsed_input.hashed_user_id[:8] + "...",
            traceback=error_traceback,
        )
        # Per FR-009: Graceful degradation
        # Return fallback response if workflow fails
        fallback_text = "Don! Mika暂时无法回应，但我会尽快回来的！🥁"
        
        # Try to send fallback message via LangBot API
        if event and settings.langbot_api_key:
            try:
                await _send_langbot_message(
                    bot_uuid=event.data.get("bot_uuid"),
                    event_type=event.event_type,
                    target_id=request.user_id if not request.group_id else request.group_id,
                    message=fallback_text,
                )
            except Exception as send_error:
                logger.error(
                    "langbot_api_send_fallback_failed",
                    error=str(send_error),
                    error_type=type(send_error).__name__,
                )
        
        return LangBotWebhookResponse(
            status="ok",
            skip_pipeline=True,
            message=[{"type": "Plain", "text": fallback_text}],
            response=fallback_text,
            success=False,
        )


@router.post("/langbot", response_model=LangBotWebhookResponse)
async def langbot_webhook(
    http_request: Request,
) -> LangBotWebhookResponse:
    """
    Handle LangBot webhook POST request.

    Processes incoming messages from LangBot when "Mika" is mentioned.
    Supports both simplified format and LangBot event format.
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
        http_request: FastAPI request object (for rate limiting and body parsing).

    Returns:
        LangBotWebhookResponse with generated response.

    Raises:
        HTTPException: If rate limit exceeded or processing fails.
    """
    # Parse request body manually to handle both formats
    try:
        body = await http_request.json()
    except Exception as e:
        logger.error(
            "webhook_parse_failed",
            error=str(e),
            path=http_request.url.path,
        )
        raise HTTPException(
            status_code=422,
            detail=f"Invalid request body: {str(e)}",
        )
    
    # Try to parse as LangBot event format first
    event: Optional[LangBotEventRequest] = None
    try:
        event = LangBotEventRequest(**body)
        request = convert_langbot_event_to_webhook_request(event)
        logger.info(
            "webhook_event_format_detected",
            event_type=event.event_type,
            has_group_id=bool(request.group_id),
            extracted_message_preview=request.message[:50] if request.message else "(empty)",
            extracted_message_length=len(request.message),
        )
    except (ValidationError, ValueError) as e:
        # Fall back to simplified format
        event = None  # Simplified format doesn't have event structure
        try:
            request = LangBotWebhookRequest(**body)
            logger.info(
                "webhook_simplified_format_detected",
                message_preview=request.message[:50] if request.message else "(empty)",
            )
        except ValidationError as e2:
            logger.error(
                "webhook_validation_failed",
                error=str(e2),
                body_preview=str(body)[:200],
            )
            raise HTTPException(
                status_code=422,
                detail=f"Invalid request format: {str(e2)}",
            )
    
    # Process the request
    # Pass event if available (for bot_uuid extraction)
    return await _process_webhook_request(request, http_request, event=event)
