"""RABA API Routes Package.

This package contains all API route handlers.
"""

from fastapi import APIRouter

from app.api.routes import generate, workflows

api_router = APIRouter()
api_router.include_router(generate.router, prefix="/generate", tags=["generate"])
api_router.include_router(workflows.router, prefix="/workflows", tags=["workflows"])
