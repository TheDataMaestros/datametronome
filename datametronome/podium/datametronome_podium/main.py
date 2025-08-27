"""
Main application module for DataMetronome Podium.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .core.config import settings
from .core.database import init_db, close_db
from .core.scheduler import init_scheduler, shutdown_scheduler
from .api.v1.api import api_router

# Configure logging
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


def create_cors_middleware() -> CORSMiddleware:
    """Create CORS middleware with configuration.
    
    Returns:
        Configured CORS middleware.
    """
    return CORSMiddleware(
        app=None,  # Will be set when added to the app
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


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
            "redoc": "/redoc"
        }
    
    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logging.info("Starting DataMetronome Podium...")
    
    # Initialize database
    await init_db()
    logging.info("Database initialized")
    
    # Initialize scheduler
    await init_scheduler()
    logging.info("Scheduler initialized")
    
    yield
    
    # Shutdown
    logging.info("Shutting down DataMetronome Podium...")
    await shutdown_scheduler()
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
    
    # Add CORS middleware
    app.add_middleware(CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API router
    app.include_router(api_router, prefix="/api/v1")
    
    # Add root endpoints
    create_root_endpoints(app)
    
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
