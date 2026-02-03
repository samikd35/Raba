#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Chat Module for MINT.

This module provides comprehensive chat functionality for the MINT system,
including chat endpoints, services, authentication, and utilities.

Module Structure:
- models: Pydantic models and data structures
- endpoints: FastAPI chat endpoints
- service: Chat service implementation
- auth: Chat authentication functions
- utils: Utility functions and helpers
"""

from .models import (
    # Enums
    ChatMessageType, ChatSessionStatus, ChatErrorCode, WebSearchStatus,
    
    # Core Models
    ChatMessage, ChatMessageRequest, ChatMessageResponse, ChatHistoryResponse,
    WebSearchToggleRequest, WebSearchToggleResponse, ChatSession, ChatQuery,
    ChatResponse, ChatValidationResult, ChatRateLimitInfo, ChatPerformanceMetrics,
    ChatSearchResult, ChatWebSearchResult, ChatContext, ChatConfig, ChatError,
    ChatAnalytics, ChatPagination, ChatFilter, ChatExportRequest, ChatExportResponse,
    
    # Constants
    DEFAULT_SIMILARITY_THRESHOLD, DEFAULT_MAX_CHUNKS, DEFAULT_MAX_QUERY_LENGTH,
    DEFAULT_MAX_RESPONSE_LENGTH, DEFAULT_RATE_LIMIT_WINDOW, DEFAULT_RATE_LIMIT_MAX_REQUESTS,
    DEFAULT_SESSION_TIMEOUT, DEFAULT_MAX_CONVERSATION_HISTORY,
    CHAT_ERROR_MESSAGES, CHAT_VALIDATION_RULES, CHAT_MESSAGE_TEMPLATES
)
from .endpoints import router as chat_router
from .service import get_report_chat_service, ChatMessage
from .auth import (
    get_current_user_simple, validate_user_context, extract_user_token,
    validate_chat_access, get_user_context_from_request, create_auth_error_response,
    validate_rate_limit_context, check_chat_permissions, create_user_session_context,
    validate_chat_session, get_auth_headers, log_auth_event
)
from .utils import (
    # ID Generation
    generate_message_id, generate_session_id,
    
    # Validation
    validate_message_content, validate_report_id, validate_chat_config,
    
    # Message Formatting
    format_chat_message, create_error_message, create_success_message,
    format_chat_response, format_error_response, create_success_response,
    
    # Search Results
    format_search_results, format_web_search_results,
    
    # Performance
    calculate_processing_time, create_performance_metrics,
    
    # Context and Configuration
    format_chat_context, extract_message_metadata,
    
    # Logging and Monitoring
    log_chat_operation, format_timestamp, calculate_message_age,
    is_message_recent, get_message_template, format_conversation_summary
)

# Convenience imports
from .endpoints import router

__all__ = [
    # Enums
    "ChatMessageType",
    "ChatSessionStatus",
    "ChatErrorCode",
    "WebSearchStatus",
    
    # Core Models
    "ChatMessage",
    "ChatMessageRequest",
    "ChatMessageResponse",
    "ChatHistoryResponse",
    "WebSearchToggleRequest",
    "WebSearchToggleResponse",
    "ChatSession",
    "ChatQuery",
    "ChatResponse",
    "ChatValidationResult",
    "ChatRateLimitInfo",
    "ChatPerformanceMetrics",
    "ChatSearchResult",
    "ChatWebSearchResult",
    "ChatContext",
    "ChatConfig",
    "ChatError",
    "ChatAnalytics",
    "ChatPagination",
    "ChatFilter",
    "ChatExportRequest",
    "ChatExportResponse",
    
    # Constants
    "DEFAULT_SIMILARITY_THRESHOLD",
    "DEFAULT_MAX_CHUNKS",
    "DEFAULT_MAX_QUERY_LENGTH",
    "DEFAULT_MAX_RESPONSE_LENGTH",
    "DEFAULT_RATE_LIMIT_WINDOW",
    "DEFAULT_RATE_LIMIT_MAX_REQUESTS",
    "DEFAULT_SESSION_TIMEOUT",
    "DEFAULT_MAX_CONVERSATION_HISTORY",
    "CHAT_ERROR_MESSAGES",
    "CHAT_VALIDATION_RULES",
    "CHAT_MESSAGE_TEMPLATES",
    
    # Main Components
    "chat_router",
    "get_report_chat_service",
    
    # ID Generation
    "generate_message_id",
    "generate_session_id",
    
    # Validation
    "validate_message_content",
    "validate_report_id",
    "validate_chat_config",
    
    # Message Formatting
    "format_chat_message",
    "create_error_message",
    "create_success_message",
    "format_chat_response",
    "format_error_response",
    "create_success_response",
    
    # Search Results
    "format_search_results",
    "format_web_search_results",
    
    # Performance
    "calculate_processing_time",
    "create_performance_metrics",
    
    # Context and Configuration
    "format_chat_context",
    "extract_message_metadata",
    
    # Logging and Monitoring
    "log_chat_operation",
    "format_timestamp",
    "calculate_message_age",
    "is_message_recent",
    "get_message_template",
    "format_conversation_summary",
    
    # Authentication
    "get_current_user_simple",
    "validate_user_context",
    "extract_user_token",
    "validate_chat_access",
    "get_user_context_from_request",
    "create_auth_error_response",
    "validate_rate_limit_context",
    "check_chat_permissions",
    "create_user_session_context",
    "validate_chat_session",
    "get_auth_headers",
    "log_auth_event",
    
    # Router
    "router"
]


