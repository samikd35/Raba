"""RABA Backend Main Application.

FastAPI application entry point.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import api_router
from app.config import settings
from app.utils.logging import get_logger, setup_logging

setup_logging(settings.log_level)
logger = get_logger(__name__)


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
    description="AI-Powered Multi-Agent YouTube Shorts Generator",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

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
    description="Check if the API is running.",
)
async def health_check():
    """Health check endpoint."""
    logger.debug("Health check requested")
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "healthy",
            "environment": settings.environment,
            "version": "0.1.0",
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
