"""
Metrics middleware for request tracking.

This middleware records request metrics including response time and error status
for the /metrics endpoint.

Per T093: Record metrics for monitoring (request rate, error rate, response time).
"""

import time
from typing import Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.api.routes.metrics import record_request

logger = structlog.get_logger()


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to record request metrics.

    Records response time and error status for all requests,
    excluding health and metrics endpoints to avoid recursion.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and record metrics.

        Args:
            request: FastAPI request object.
            call_next: Next middleware/handler in chain.

        Returns:
            Response from next handler.
        """
        # Skip metrics recording for health and metrics endpoints
        # to avoid recursion and self-measurement
        if request.url.path in ("/health", "/metrics", "/metrics/prometheus"):
            return await call_next(request)

        # Record start time
        start_time = time.time()

        # Process request
        try:
            response = await call_next(request)
            is_error = response.status_code >= 400
        except Exception as e:
            # Record error
            logger.error(
                "request_error",
                path=request.url.path,
                method=request.method,
                error=str(e),
                error_type=type(e).__name__,
            )
            is_error = True
            raise
        finally:
            # Calculate response time
            response_time = time.time() - start_time

            # Record metric
            record_request(response_time, is_error=is_error)

            logger.debug(
                "request_metric_recorded",
                path=request.url.path,
                method=request.method,
                response_time=response_time,
                is_error=is_error,
            )

        return response
