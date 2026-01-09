"""
Metrics endpoint for monitoring.

This module provides Prometheus-format metrics endpoint for monitoring
system performance, including request rate, error rate, response time,
and system resource usage.

Per T093: Create src/api/routes/metrics.py with /metrics endpoint
Per NFR-011: Basic monitoring metrics (request rate, error rate, response time
p50/p95/p99, system resources) via /metrics endpoint.
"""

import time
from collections import deque
from typing import Any

import structlog
from fastapi import APIRouter
from pydantic import BaseModel

# Try to import psutil, but make it optional
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None  # type: ignore

logger = structlog.get_logger()

router = APIRouter()

# In-memory metrics storage (simple implementation)
# For production, consider using Prometheus client library
_metrics_store: dict[str, Any] = {
    "request_count": 0,
    "error_count": 0,
    "response_times": deque(maxlen=1000),  # Keep last 1000 response times
    "start_time": time.time(),
}


def record_request(response_time: float, is_error: bool = False) -> None:
    """
    Record a request metric.

    Args:
        response_time: Request response time in seconds.
        is_error: Whether the request resulted in an error.
    """
    _metrics_store["request_count"] += 1
    if is_error:
        _metrics_store["error_count"] += 1
    _metrics_store["response_times"].append(response_time)


def _calculate_percentile(values: list[float], percentile: float) -> float:
    """
    Calculate percentile value from a list of numbers.

    Args:
        values: List of numeric values.
        percentile: Percentile to calculate (0.0-1.0).

    Returns:
        Percentile value.
    """
    if not values:
        return 0.0
    
    sorted_values = sorted(values)
    index = int(len(sorted_values) * percentile)
    if index >= len(sorted_values):
        index = len(sorted_values) - 1
    return sorted_values[index]


class MetricsResponse(BaseModel):
    """Metrics response model."""

    # Request metrics
    request_count: int
    error_count: int
    error_rate: float  # Error rate as percentage
    
    # Response time metrics (in seconds)
    response_time_p50: float  # 50th percentile (median)
    response_time_p95: float  # 95th percentile
    response_time_p99: float  # 99th percentile
    response_time_avg: float  # Average response time
    
    # System resource metrics
    cpu_percent: float  # CPU usage percentage
    memory_percent: float  # Memory usage percentage
    memory_used_mb: float  # Memory used in MB
    memory_available_mb: float  # Memory available in MB
    
    # Uptime
    uptime_seconds: float  # System uptime in seconds


@router.get("", response_model=MetricsResponse)
async def get_metrics() -> MetricsResponse:
    """
    Get system metrics in Prometheus-compatible format.

    Returns metrics including:
    - Request rate and error rate
    - Response time percentiles (p50, p95, p99)
    - System resource usage (CPU, memory)

    Returns:
        MetricsResponse with all metrics.

    Example:
        >>> GET /metrics
        {
          "request_count": 1000,
          "error_count": 5,
          "error_rate": 0.5,
          "response_time_p50": 1.2,
          "response_time_p95": 2.5,
          "response_time_p99": 3.0,
          "response_time_avg": 1.3,
          "cpu_percent": 25.5,
          "memory_percent": 45.2,
          ...
        }
    """
    logger.debug("metrics_requested")

    # Get request metrics
    request_count = _metrics_store["request_count"]
    error_count = _metrics_store["error_count"]
    error_rate = (error_count / request_count * 100) if request_count > 0 else 0.0

    # Calculate response time percentiles
    response_times = list(_metrics_store["response_times"])
    if response_times:
        response_time_p50 = _calculate_percentile(response_times, 0.50)
        response_time_p95 = _calculate_percentile(response_times, 0.95)
        response_time_p99 = _calculate_percentile(response_times, 0.99)
        response_time_avg = sum(response_times) / len(response_times)
    else:
        response_time_p50 = 0.0
        response_time_p95 = 0.0
        response_time_p99 = 0.0
        response_time_avg = 0.0

    # Get system resource metrics
    if PSUTIL_AVAILABLE and psutil:
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_mb = memory.used / (1024 * 1024)  # Convert to MB
            memory_available_mb = memory.available / (1024 * 1024)  # Convert to MB
        except Exception as e:
            logger.warning("system_metrics_collection_failed", error=str(e))
            cpu_percent = 0.0
            memory_percent = 0.0
            memory_used_mb = 0.0
            memory_available_mb = 0.0
    else:
        # psutil not available - return zero values
        logger.debug("psutil_not_available", message="System metrics unavailable (psutil not installed)")
        cpu_percent = 0.0
        memory_percent = 0.0
        memory_used_mb = 0.0
        memory_available_mb = 0.0

    # Calculate uptime
    uptime_seconds = time.time() - _metrics_store["start_time"]

    metrics = MetricsResponse(
        request_count=request_count,
        error_count=error_count,
        error_rate=error_rate,
        response_time_p50=response_time_p50,
        response_time_p95=response_time_p95,
        response_time_p99=response_time_p99,
        response_time_avg=response_time_avg,
        cpu_percent=cpu_percent,
        memory_percent=memory_percent,
        memory_used_mb=memory_used_mb,
        memory_available_mb=memory_available_mb,
        uptime_seconds=uptime_seconds,
    )

    logger.debug(
        "metrics_retrieved",
        request_count=request_count,
        error_rate=error_rate,
        response_time_p95=response_time_p95,
    )

    return metrics


# Prometheus format endpoint (optional, for Prometheus scraping)
@router.get("/prometheus")
async def get_metrics_prometheus() -> str:
    """
    Get metrics in Prometheus text format.

    Returns metrics in Prometheus-compatible text format for scraping.

    Returns:
        Prometheus-format metrics string.
    """
    logger.debug("prometheus_metrics_requested")

    # Get metrics
    metrics = await get_metrics()

    # Format as Prometheus text format
    lines = [
        "# HELP mika_bot_requests_total Total number of requests",
        "# TYPE mika_bot_requests_total counter",
        f"mika_bot_requests_total {metrics.request_count}",
        "",
        "# HELP mika_bot_errors_total Total number of errors",
        "# TYPE mika_bot_errors_total counter",
        f"mika_bot_errors_total {metrics.error_count}",
        "",
        "# HELP mika_bot_error_rate Error rate as percentage",
        "# TYPE mika_bot_error_rate gauge",
        f"mika_bot_error_rate {metrics.error_rate}",
        "",
        "# HELP mika_bot_response_time_seconds Response time in seconds",
        "# TYPE mika_bot_response_time_seconds histogram",
        f'mika_bot_response_time_seconds{{quantile="0.5"}} {metrics.response_time_p50}',
        f'mika_bot_response_time_seconds{{quantile="0.95"}} {metrics.response_time_p95}',
        f'mika_bot_response_time_seconds{{quantile="0.99"}} {metrics.response_time_p99}',
        f'mika_bot_response_time_seconds{{quantile="avg"}} {metrics.response_time_avg}',
        "",
        "# HELP mika_bot_cpu_percent CPU usage percentage",
        "# TYPE mika_bot_cpu_percent gauge",
        f"mika_bot_cpu_percent {metrics.cpu_percent}",
        "",
        "# HELP mika_bot_memory_percent Memory usage percentage",
        "# TYPE mika_bot_memory_percent gauge",
        f"mika_bot_memory_percent {metrics.memory_percent}",
        "",
        "# HELP mika_bot_memory_used_mb Memory used in MB",
        "# TYPE mika_bot_memory_used_mb gauge",
        f"mika_bot_memory_used_mb {metrics.memory_used_mb}",
        "",
        "# HELP mika_bot_uptime_seconds System uptime in seconds",
        "# TYPE mika_bot_uptime_seconds gauge",
        f"mika_bot_uptime_seconds {metrics.uptime_seconds}",
    ]

    return "\n".join(lines)
