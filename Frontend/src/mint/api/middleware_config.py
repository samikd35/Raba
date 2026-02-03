#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MINT API Middleware Configuration

Centralized middleware configuration for the MINT API.
"""

import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)


def configure_cors_middleware(app: FastAPI) -> None:
    """Configure CORS middleware for the FastAPI application."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info("CORS middleware configured")


def configure_security_middleware(app: FastAPI) -> None:
    """Configure security middleware for the FastAPI application."""
    # Import WebSocket endpoints and notification services
    from .system.endpoints.websocket_endpoints import router as websocket_router
    from .services.communication.notification_service import notification_manager
    from .chat.endpoints import router as chat_router

    # PRODUCTION SECURITY: Replace all legacy auth middleware with unified secure system
    from .system.middleware.rate_limiter import AdminRateLimitMiddleware
    from .system.middleware.ip_whitelist import IPWhitelistMiddleware

    # Initialize production auth system
    logger.info("Initializing Production Authentication System to replace legacy auth handlers")

    # Common exclude paths for middleware
    exclude_paths = [
        "/docs", 
        "/openapi.json", 
        "/health", 
        "/api/workflow", 
        "/api/status", 
        "/api/answers", 
        "/api/report", 
        "/ws/notifications", 
        "/ws/admin/dashboard",
        "/api/chat/message",
        "/api/chat/history",
        "/api/chat/web-search",
        "/api/idea-refinement"
    ]

    # Add rate limiting middleware (first in chain)
    app.add_middleware(
        AdminRateLimitMiddleware,
        admin_window_size=60,  # 1 minute window
        admin_max_requests=200,  # 200 requests per minute for admin endpoints (dashboard needs many calls)
        login_window_size=300,  # 5 minute window
        login_max_requests=5,   # 5 login attempts per 5 minutes
        exclude_paths=exclude_paths
    )

    # Add IP whitelisting middleware for super admin endpoints
    app.add_middleware(
        IPWhitelistMiddleware,
        whitelist=None,  # Will load from environment variable
        super_admin_paths=[
            "/api/admin/infrastructure/",
            "/api/admin/settings/",
            "/api/admin/auth/roles",
            "/api/admin/system/maintenance"
        ]
    )

    logger.info("Security middleware configured")


def configure_all_middleware(app: FastAPI) -> None:
    """Configure all middleware for the FastAPI application."""
    configure_cors_middleware(app)
    configure_security_middleware(app)
