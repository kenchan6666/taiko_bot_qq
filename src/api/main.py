"""
FastAPI application main module.

This module sets up the FastAPI application with structured JSON logging
configuration and lifecycle management.

Per NFR-010: Structured JSON logging with structured fields.
"""

import logging
import sys
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.config import settings
from src.services.database import close_database, init_database
from src.services.llm import close_llm_service
from src.services.song_query import initialize_song_cache


def setup_structured_logging() -> None:
    """
    Configure structured JSON logging.

    Per NFR-010: Structured JSON logging with structured fields:
    - user_id (hashed), request_id, timestamp, operation_type,
    - log_level, message, contextual metadata

    Uses structlog for structured logging with JSON output.
    """
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,  # Filter by log level
            structlog.stdlib.add_logger_name,  # Add logger name
            structlog.stdlib.add_log_level,  # Add log level
            structlog.stdlib.PositionalArgumentsFormatter(),  # Format positional args
            structlog.processors.TimeStamper(fmt="iso"),  # ISO timestamp
            structlog.processors.StackInfoRenderer(),  # Stack traces
            structlog.processors.format_exc_info,  # Exception formatting
            structlog.processors.UnicodeDecoder(),  # Unicode decoding
            structlog.processors.JSONRenderer(),  # JSON output
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper()),
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown events:
    - Startup: Initialize database, validate configuration
    - Shutdown: Close database and LLM service connections
    """
    # Startup
    logger = structlog.get_logger()
    logger.info("application_startup", event_type="initializing")

    # Initialize database
    try:
        await init_database()
        logger.info("database_initialized", event_type="startup_success")
    except Exception as e:
        logger.error("database_init_failed", error=str(e), event_type="startup_error")
        raise

    # Initialize song cache
    # Per FR-002: Cache songs at startup for fast queries
    try:
        await initialize_song_cache()
        logger.info("song_cache_initialized", event_type="startup_success")
    except Exception as e:
        logger.warning("song_cache_init_failed", error=str(e), event_type="startup_warning")
        # Don't fail startup if song cache fails - can refresh later

    # Validate OpenRouter API key (if needed)
    # Note: LLM service will be created lazily on first use

    logger.info("application_ready", event_type="startup_complete")

    yield

    # Shutdown
    logger.info("application_shutdown", event_type="shutting_down")

    # Close database connection
    try:
        await close_database()
        logger.info("database_closed", event_type="shutdown_success")
    except Exception as e:
        logger.error("database_close_failed", error=str(e), event_type="shutdown_error")

    # Close LLM service
    try:
        await close_llm_service()
        logger.info("llm_service_closed", event_type="shutdown_success")
    except Exception as e:
        logger.error("llm_service_close_failed", error=str(e), event_type="shutdown_error")

    logger.info("application_stopped", event_type="shutdown_complete")


# Create FastAPI application
app = FastAPI(
    title="Mika Taiko Chatbot API",
    description="FastAPI backend for Mika Taiko no Tatsujin QQ chatbot",
    version="1.0.0",
    lifespan=lifespan,
)

# Setup structured logging
setup_structured_logging()

# Add metrics middleware (must be before routes)
from src.api.middleware.metrics import MetricsMiddleware  # noqa: E402
app.add_middleware(MetricsMiddleware)

# Import routes (must be after app creation)
from src.api.routes import langbot  # noqa: E402
from src.api.routes import health  # noqa: E402
from src.api.routes import metrics  # noqa: E402

# Register routes
app.include_router(langbot.router, prefix="/webhook", tags=["webhooks"])
app.include_router(health.router, prefix="/health", tags=["monitoring"])
app.include_router(metrics.router, prefix="/metrics", tags=["monitoring"])


# Add exception handler for validation errors to provide better error messages
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handle request validation errors with detailed logging.
    
    This helps debug 422 errors by logging the exact validation issues.
    """
    logger = structlog.get_logger()
    
    # Try to get request body for logging
    body_preview = "N/A"
    try:
        body_bytes = await request.body()
        body_preview = body_bytes.decode('utf-8', errors='ignore')[:500]
    except Exception:
        pass
    
    logger.error(
        "request_validation_failed",
        path=request.url.path,
        method=request.method,
        errors=exc.errors(),
        body_preview=body_preview,
    )
    
    return JSONResponse(
        status_code=422,
        content={
            "detail": exc.errors(),
            "body_preview": body_preview,
        },
    )
