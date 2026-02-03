#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Messaging Module for MINT.

This module provides user-to-user messaging functionality with server-side encryption,
rate limiting, and blocking/muting capabilities.

Features:
- Server-side encrypted messaging (AES-GCM with TLS in transit, SSE at rest)
- One thread per user pair
- Rate limiting: 1 new conversation per 48 hours (unless matched)
- No limit for matched users
- Block and mute functionality

Module Structure:
- models: Pydantic models and data structures
- service: Messaging service implementation with encryption
- endpoints: FastAPI messaging endpoints
"""

from .models import (
    # Enums
    MessageStatus, ThreadStatus, UserRelationship,

    # Core Models
    Message, MessageThread, BlockedUser, ContactRateLimit, UserRelationshipRecord,

    # Request/Response Models
    SendMessageRequest, SendMessageResponse,
    GetThreadsResponse, GetMessagesRequest, GetMessagesResponse,
    BlockUserRequest, BlockUserResponse,
    UnblockUserRequest, UnblockUserResponse,
    RateLimitCheckResponse,

    # Constants
    RATE_LIMIT_HOURS, MAX_MESSAGE_LENGTH,
    MAX_THREADS_PER_PAGE, MAX_MESSAGES_PER_PAGE,
    ERROR_MESSAGES
)

from .service import (
    MessagingService, EncryptionService, get_messaging_service
)

from .endpoints import router as messaging_router

from .websocket import ConnectionManager, get_connection_manager
from .websocket_endpoints import websocket_router as messaging_websocket_router

__all__ = [
    # Enums
    "MessageStatus",
    "ThreadStatus",
    "UserRelationship",

    # Core Models
    "Message",
    "MessageThread",
    "BlockedUser",
    "ContactRateLimit",
    "UserRelationshipRecord",

    # Request/Response Models
    "SendMessageRequest",
    "SendMessageResponse",
    "GetThreadsResponse",
    "GetMessagesRequest",
    "GetMessagesResponse",
    "BlockUserRequest",
    "BlockUserResponse",
    "UnblockUserRequest",
    "UnblockUserResponse",
    "RateLimitCheckResponse",

    # Constants
    "RATE_LIMIT_HOURS",
    "MAX_MESSAGE_LENGTH",
    "MAX_THREADS_PER_PAGE",
    "MAX_MESSAGES_PER_PAGE",
    "ERROR_MESSAGES",

    # Services
    "MessagingService",
    "EncryptionService",
    "get_messaging_service",

    # WebSocket
    "ConnectionManager",
    "get_connection_manager",

    # Routers
    "messaging_router",
    "messaging_websocket_router",
]
