"""
Health check endpoint.

This module provides health check endpoints for monitoring system status,
including MongoDB, Temporal, and OpenRouter API connectivity.

Per T092: Create src/api/routes/health.py with /health endpoint
Per NFR-011: Basic monitoring metrics via /health endpoint.
"""

from typing import Any

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.config import settings
from src.services.database import get_database_client, ensure_database_initialized
from src.services.llm import get_llm_service

# Try to import Temporal client (may not be available in all environments)
try:
    from temporalio.client import Client
    TEMPORAL_AVAILABLE = True
except ImportError:
    TEMPORAL_AVAILABLE = False
    Client = None  # type: ignore

logger = structlog.get_logger()

router = APIRouter()


class HealthStatus(BaseModel):
    """Health status response model."""

    status: str  # "healthy" or "degraded"
    services: dict[str, str]  # Service status: "connected", "disconnected", "error"


async def check_mongodb_health() -> str:
    """
    Check MongoDB connection health.

    Returns:
        "connected" if healthy, "disconnected" or "error" otherwise.
    """
    try:
        # Ensure database is initialized
        await ensure_database_initialized()
        
        # Get database client
        client = get_database_client()
        if client is None:
            return "disconnected"
        
        # Ping MongoDB to check connection
        await client.admin.command("ping")
        return "connected"
    except Exception as e:
        logger.warning("mongodb_health_check_failed", error=str(e))
        return "disconnected"


async def check_temporal_health() -> str:
    """
    Check Temporal server connection health.

    Returns:
        "connected" if healthy, "disconnected" or "error" otherwise.
    """
    if not TEMPORAL_AVAILABLE or Client is None:
        return "unavailable"
    
    try:
        # Try to connect to Temporal server
        client = await Client.connect(
            target_host=f"{settings.temporal_host}:{settings.temporal_port}",
            namespace=settings.temporal_namespace,
        )
        # Close connection immediately (we just need to verify connectivity)
        await client.close()
        return "connected"
    except Exception as e:
        logger.warning("temporal_health_check_failed", error=str(e))
        return "disconnected"


async def check_openrouter_health() -> str:
    """
    Check OpenRouter API availability.

    Returns:
        "available" if API key is configured, "unavailable" otherwise.
    """
    try:
        # Check if API key is configured
        if not settings.openrouter_api_key:
            return "unavailable"
        
        # Try to get LLM service (lazy initialization)
        # This doesn't make an actual API call, just checks configuration
        llm_service = get_llm_service()
        if llm_service is None:
            return "unavailable"
        
        return "available"
    except Exception as e:
        logger.warning("openrouter_health_check_failed", error=str(e))
        return "unavailable"


@router.get("", response_model=HealthStatus)
async def health_check() -> HealthStatus:
    """
    Health check endpoint.

    Checks the health status of all critical services:
    - MongoDB: Database connectivity
    - Temporal: Workflow engine connectivity
    - OpenRouter: API key configuration

    Returns:
        HealthStatus with overall status and individual service statuses.

    Example:
        >>> GET /health
        {
          "status": "healthy",
          "services": {
            "mongodb": "connected",
            "temporal": "connected",
            "openrouter": "available"
          }
        }
    """
    logger.debug("health_check_requested")

    # Check all services
    mongodb_status = await check_mongodb_health()
    temporal_status = await check_temporal_health()
    openrouter_status = await check_openrouter_health()

    # Determine overall status
    # "healthy" if all critical services are available
    # "degraded" if some services are unavailable but system can still function
    critical_services = [mongodb_status, temporal_status]
    if all(status == "connected" for status in critical_services):
        overall_status = "healthy"
    else:
        overall_status = "degraded"

    services = {
        "mongodb": mongodb_status,
        "temporal": temporal_status,
        "openrouter": openrouter_status,
    }

    logger.info(
        "health_check_completed",
        status=overall_status,
        services=services,
    )

    return HealthStatus(
        status=overall_status,
        services=services,
    )
