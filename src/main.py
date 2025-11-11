"""
FastAPI Main Application

Entry point for the HS Basketball Players Multi-Datasource API.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_settings
from .services.rate_limiter import get_rate_limiter
from .utils.logger import get_logger, get_metrics, setup_logging

# Initialize logging first
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown tasks.
    """
    # Startup
    logger.info("Application starting up...")
    settings = get_settings()

    # Initialize rate limiter
    rate_limiter = get_rate_limiter()
    logger.info("Rate limiter initialized")

    logger.info(
        "Application startup complete",
        environment=settings.environment,
        debug=settings.debug,
    )

    yield

    # Shutdown
    logger.info("Application shutting down...")
    logger.info("Application shutdown complete")


# Create FastAPI application
settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Multi-datasource basketball player statistics API with comprehensive rate limiting and validation",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health", tags=["system"])
async def health_check():
    """
    Health check endpoint.

    Returns application health status and basic metrics.
    """
    metrics = get_metrics()
    return JSONResponse(
        {
            "status": "healthy",
            "version": settings.app_version,
            "environment": settings.environment,
            "metrics": metrics.get_summary(),
        }
    )


# Root endpoint
@app.get("/", tags=["system"])
async def root():
    """
    Root endpoint with API information.
    """
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "description": "Multi-datasource basketball player statistics API",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "players": "/api/v1/players",
            "teams": "/api/v1/teams",
            "games": "/api/v1/games",
            "stats": "/api/v1/stats",
        },
    }


# Rate limit status endpoint
@app.get("/rate-limits", tags=["system"])
async def get_rate_limits():
    """
    Get rate limit status for all data sources.
    """
    rate_limiter = get_rate_limiter()
    statuses = rate_limiter.get_all_statuses()

    return {
        "rate_limits": {
            source: {
                "requests_made": status.requests_made,
                "requests_allowed": status.requests_allowed,
                "requests_remaining": status.requests_remaining,
                "usage_percentage": status.usage_percentage,
                "is_limited": status.is_limited,
                "window_reset_at": status.window_reset_at.isoformat(),
            }
            for source, status in statuses.items()
        }
    }


# Metrics endpoint
@app.get("/metrics", tags=["system"])
async def get_metrics_endpoint():
    """
    Get application metrics.
    """
    metrics = get_metrics()
    return metrics.get_summary()


# Import and include API routers
from .api.routes import router as api_router

app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
