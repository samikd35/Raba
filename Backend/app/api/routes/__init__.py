"""RABA API Routes Package.

This package contains all API route handlers.
"""

from fastapi import APIRouter

from app.api.routes import generate, hitl, monitoring, tools, workflows

api_router = APIRouter()
api_router.include_router(generate.router, prefix="/generate", tags=["video-generation"])
api_router.include_router(workflows.router, prefix="/workflows", tags=["video-generation"])
api_router.include_router(tools.router, prefix="/tools", tags=["tools"])
api_router.include_router(hitl.router, tags=["video-generation"])  # HITL routes under /workflows
api_router.include_router(monitoring.router, prefix="/monitoring", tags=["monitoring"])
