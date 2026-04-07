"""
Main application module for DataMetronome Podium.
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
try:
    import logfire
except ImportError:
    logfire = None  # type: ignore
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .api.v1.api import api_router
from .core.config import settings
from .core.database import close_db, init_db
from .core.logging_config import get_logger, setup_logging
from .core.rate_limit import limiter

# Configure logging based on environment
log_format = os.getenv("LOG_FORMAT", "text")  # 'text' for dev, 'json' for prod
setup_logging(log_level=settings.log_level, log_format=log_format)
logger = get_logger(__name__)


def create_root_endpoints(app: FastAPI) -> None:
    """Add root-level endpoints to the application.

    Args:
        app: FastAPI application instance.
    """

    @app.get("/")
    async def root() -> dict[str, str]:
        """Root endpoint."""
        return {
            "message": "DataMetronome Podium API",
            "version": "0.1.0",
            "docs": "/docs",
            "redoc": "/redoc",
            "metrics": "/metrics",
        }

    @app.get("/health")
    async def health_check() -> dict[str, str | dict]:
        """
        Health check endpoint for load balancers and monitoring.

        Returns comprehensive system health status including:
        - Overall health status
        - Database connectivity
        - Version information
        - Timestamp
        """
        from datetime import datetime, timezone

        health_status: dict[str, Any] = {
            "status": "healthy",
            "version": "0.1.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": "datametronome-podium",
            "checks": {},
        }

        # Check database connectivity
        try:
            from .core.database import get_db_connection_status

            db_status = await get_db_connection_status()
            health_status["checks"]["database"] = {
                "status": "healthy" if db_status else "unhealthy",
                "message": "Database connection OK"
                if db_status
                else "Database connection failed",
            }
        except Exception as e:
            health_status["checks"]["database"] = {
                "status": "unhealthy",
                "message": f"Database check failed: {str(e)}",
            }
            health_status["status"] = "degraded"

        # Scheduling: Celery Beat + RedBeat + persisted jobs (see api/v1/endpoints/scheduler.py).
        sched_ok = settings.scheduler_enabled
        health_status["checks"]["scheduler"] = {
            "status": "healthy" if sched_ok else "degraded",
            "message": (
                f"Scheduler integration {'on' if sched_ok else 'off'} "
                f"(Celery Beat / persisted jobs); dispatch_mode={settings.dispatch_mode}"
            ),
        }
        if not sched_ok:
            health_status["status"] = "degraded"

        return health_status

    @app.get("/metrics")
    async def metrics():
        """
        Prometheus metrics endpoint.

        Returns application metrics in Prometheus format for monitoring:
        - HTTP request metrics (count, duration, in-progress)
        - Database metrics (queries, connections)
        - Check run metrics (success rate, duration, anomalies)
        - System health metrics
        - Business metrics (users, clefs, staves)
        """
        from fastapi import Response

        from .core.metrics import get_metrics_content, update_system_metrics

        # Update dynamic metrics before returning
        await update_system_metrics()

        # Get metrics in Prometheus format
        content, content_type = get_metrics_content()

        return Response(content=content, media_type=content_type)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logging.info("Starting DataMetronome Podium...")

    # Validate configuration (blocks startup on critical errors like default secret key)
    from .core.config import validate_and_report_config
    validate_and_report_config()

    # Initialize database
    await init_db()
    logging.info("Database initialized")

    logging.info(
        "Scheduler integration: Celery Beat + RedBeat (scheduler_enabled=%s, dispatch_mode=%s)",
        settings.scheduler_enabled,
        settings.dispatch_mode,
    )

    yield

    # Shutdown
    logging.info("Shutting down DataMetronome Podium...")
    await close_db()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application.
    """
    app = FastAPI(
        title="DataMetronome Podium",
        description="Core backend API server for DataMetronome data observability platform",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Add rate limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore

    # Add metrics middleware (first, to track all requests)
    from .core.middleware import MetricsMiddleware

    app.add_middleware(MetricsMiddleware)  # type: ignore

    # Add CORS middleware
    app.add_middleware(  # type: ignore
        CORSMiddleware,  # type: ignore
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )  # type: ignore

    # Include API router
    app.include_router(api_router, prefix="/api/v1")

    # Add root endpoints
    create_root_endpoints(app)

    # Logfire observability: tracing, spans, request/response timing (optional)
    # Sends to Logfire cloud only when LOGFIRE_TOKEN is set; otherwise console-only
    if logfire is not None:
        try:
            logfire.configure(send_to_logfire="if-token-present")
            logfire.instrument_fastapi(app)
            logfire.instrument_httpx()  # Traces ADK agent's internal API calls via httpx
        except Exception as e:  # e.g. missing opentelemetry-instrumentation-fastapi
            logger.warning("Logfire instrumentation skipped: %s", e)

    return app


def main() -> None:
    """Main entry point for the application."""
    uvicorn.run(
        "datametronome_podium.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )


# Create application instance
app = create_app()


if __name__ == "__main__":
    main()
