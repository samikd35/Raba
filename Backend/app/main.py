"""RABA Backend Main Application.

FastAPI application entry point.
Includes rate limiting and API documentation.

Reference: NFR-405 - Rate limiting SHALL be implemented on API endpoints
Phase 4.5.3 & 4.5.4 Implementation
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.routes import api_router
from app.config import settings
from app.services.redis import check_redis_health
from app.utils.logging import get_logger, setup_logging

setup_logging(settings.log_level)
logger = get_logger(__name__)

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("=" * 60)
    logger.info("RABA Backend - Starting up")
    logger.info("=" * 60)
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"API prefix: {settings.api_v1_prefix}")
    logger.info("=" * 60)
    
    yield
    
    logger.info("=" * 60)
    logger.info("RABA Backend - Shutting down")
    logger.info("=" * 60)


app = FastAPI(
    title="RABA API",
    description="""
## AI-Powered Multi-Agent YouTube Shorts Generator

RABA automatically generates viral YouTube Shorts (8-25 seconds) using a multi-agent pipeline:

1. **Intent/Tool Selection** - Analyzes topic and selects visual style
2. **Deep Research** - Gathers facts with Google Search grounding
3. **Script Generation** - Creates viral-optimized scripts
4. **Image Generation** - Generates reference images (Nano Banana Pro)
5. **Video Generation** - Produces final video (Veo 3.1)

### Features
- **Auto/Manual modes** - End-to-end or with human approval gates
- **Reference image upload** - Guide visual style with your own images
- **Multiple categories** - Surreal Realism, High-Octane Anime, Stylized 3D

### Rate Limits
- Generate endpoint: 5 requests/minute
- Workflows endpoint: 60 requests/minute
- Tools endpoint: 60 requests/minute
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "video-generation", "description": "Video generation, workflow management, and HITL feedback"},
        {"name": "tools", "description": "Tool repository management"},
        {"name": "monitoring", "description": "Token usage and cost tracking"},
        {"name": "health", "description": "API health and status"},
    ],
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get(
    "/health",
    tags=["health"],
    summary="Health check",
    description="Check API health including Redis connection status.",
)
async def health_check():
    """Health check endpoint with service status."""
    logger.debug("Health check requested")
    
    # Check Redis health
    redis_health = check_redis_health()
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "healthy",
            "environment": settings.environment,
            "version": "1.0.0",
            "services": {
                "redis": redis_health,
            },
        },
    )


@app.get(
    "/",
    tags=["root"],
    summary="Root endpoint",
    description="API information.",
)
async def root():
    """Root endpoint with API information."""
    logger.debug("Root endpoint requested")
    return {
        "name": "RABA API",
        "description": "AI-Powered Multi-Agent YouTube Shorts Generator",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting RABA Backend with uvicorn...")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
