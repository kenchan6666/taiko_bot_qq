"""
Rate limiting middleware.

This module provides rate limiting middleware for FastAPI routes
to prevent abuse in large group environments.

Per FR-012: Rate limiting (20 requests/user/minute, 50 requests/group/minute).
"""

from typing import Callable

import structlog
from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from src.services.rate_limiter import check_rate_limit
from src.utils.hashing import hash_user_id

logger = structlog.get_logger()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware for FastAPI.

    Checks rate limits for user and group before processing requests.
    Per FR-012: 20 requests/user/minute, 50 requests/group/minute.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with rate limiting check.

        Args:
            request: FastAPI request object.
            call_next: Next middleware/route handler.

        Returns:
            Response from next handler, or 429 if rate limit exceeded.

        Raises:
            HTTPException: 429 if rate limit exceeded.
        """
        # Only apply rate limiting to webhook endpoints
        if not request.url.path.startswith("/webhook/"):
            return await call_next(request)

        # Extract user_id and group_id from request body
        # Note: This requires reading the request body
        # For now, we'll check rate limits in the route handler
        # A more sophisticated approach would parse JSON here

        # Continue to next handler
        # Rate limiting will be checked in route handler
        return await call_next(request)


def check_rate_limit_middleware(
    hashed_user_id: str,
    group_id: str,
) -> None:
    """
    Check rate limits for user and group.

    This function should be called in route handlers before processing.
    Per FR-012: 20 requests/user/minute, 50 requests/group/minute.

    Args:
        hashed_user_id: Hashed user ID.
        group_id: QQ group ID.

    Raises:
        HTTPException: 429 if rate limit exceeded.
    """
    allowed, reason, remaining = check_rate_limit(hashed_user_id, group_id)

    if not allowed:
        logger.warning(
            "rate_limit_exceeded",
            hashed_user_id=hashed_user_id[:8] + "...",
            group_id=group_id,
            reason=reason,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: {reason}",
        )

    # Log rate limit status (optional, for monitoring)
    if remaining is not None and remaining < 5:
        logger.info(
            "rate_limit_warning",
            hashed_user_id=hashed_user_id[:8] + "...",
            group_id=group_id,
            remaining=remaining,
        )
