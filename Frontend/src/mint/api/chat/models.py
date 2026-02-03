#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Chat Models and Data Structures.

This module contains Pydantic models and data structures for chat functionality,
including chat messages, sessions, responses, and validation.
"""

from enum import Enum
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class ChatMessageType(str, Enum):
    """Types of chat messages."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    ERROR = "error"


class ChatSessionStatus(str, Enum):
    """Chat session status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    DELETED = "deleted"


class ChatErrorCode(str, Enum):
    """Chat error codes."""
    AUTHENTICATION_FAILED = "authentication_failed"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    REPORT_NOT_FOUND = "report_not_found"
    ACCESS_DENIED = "access_denied"
    NO_CHUNKS_FOUND = "no_chunks_found"
    PROCESSING_IN_PROGRESS = "processing_in_progress"
    VALIDATION_ERROR = "validation_error"
    CHAT_SERVICE_ERROR = "chat_service_error"
    WEB_SEARCH_ERROR = "web_search_error"
    QUERY_PROCESSING_ERROR = "query_processing_error"


class WebSearchStatus(str, Enum):
    """Web search status."""
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"


class ChatMessage(BaseModel):
    """Chat message model."""
    id: str
    content: str
    message_type: ChatMessageType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user_id: Optional[str] = None
    report_id: Optional[str] = None
    chat_session_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChatMessageRequest(BaseModel):
    """Request model for sending a chat message."""
    report_id: str = Field(..., description="ID of the report to chat with")
    content: str = Field(..., description="Content of the message")
    web_search_enabled: bool = Field(False, description="Whether to enable web search")
    chat_session_id: Optional[str] = Field(None, description="Optional chat session ID for conversation memory")
    conversation_history: Optional[List[Dict[str, str]]] = Field(
        default=None,
        description="Previous conversation messages for context. Each message should have 'role' and 'content' keys."
    )


class ChatMessageResponse(BaseModel):
    """Response model for a chat message."""
    id: str = Field(..., description="ID of the message")
    content: str = Field(..., description="Content of the message")
    success: bool = Field(..., description="Whether the message was processed successfully")
    error: Optional[str] = Field(None, description="Error message if any")
    chat_session_id: Optional[str] = Field(None, description="Chat session ID for conversation memory")
    conversation_history: Optional[List[Dict[str, str]]] = Field(
        default=None,
        description="Updated conversation history including the current exchange"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChatHistoryResponse(BaseModel):
    """Response model for chat history."""
    messages: List[Dict[str, Any]] = Field(..., description="List of chat messages")
    pagination: Dict[str, Any] = Field(..., description="Pagination metadata")


class WebSearchToggleRequest(BaseModel):
    """Request model for toggling web search."""
    enabled: bool = Field(..., description="Whether to enable web search")


class WebSearchToggleResponse(BaseModel):
    """Response model for web search toggle."""
    enabled: bool = Field(..., description="Whether web search is enabled")


class ChatSession(BaseModel):
    """Chat session model."""
    id: str
    user_id: str
    report_id: str
    status: ChatSessionStatus = ChatSessionStatus.ACTIVE
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_message_at: Optional[datetime] = None
    message_count: int = 0
    web_search_enabled: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChatQuery(BaseModel):
    """Chat query model."""
    id: str
    user_id: str
    report_id: str
    query: str
    web_search_enabled: bool = False
    chat_session_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    processed_at: Optional[datetime] = None
    response_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    """Chat response model."""
    id: str
    query_id: str
    content: str
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    web_search_results: List[Dict[str, Any]] = Field(default_factory=list)
    processing_time: float = 0.0
    token_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChatValidationResult(BaseModel):
    """Chat validation result."""
    success: bool
    report_id: Optional[str] = None
    error_code: Optional[ChatErrorCode] = None
    error_message: Optional[str] = None
    user_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChatRateLimitInfo(BaseModel):
    """Chat rate limit information."""
    is_limited: bool
    remaining_requests: int
    window_size: int
    reset_time: datetime
    user_id: str
    client_ip: str


class ChatPerformanceMetrics(BaseModel):
    """Chat performance metrics."""
    query_id: str
    processing_time: float
    validation_time: float
    search_time: float
    generation_time: float
    total_tokens: int
    chunks_retrieved: int
    web_search_enabled: bool
    success: bool
    error_code: Optional[ChatErrorCode] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ChatSearchResult(BaseModel):
    """Chat search result."""
    chunk_id: str
    content: str
    similarity: float
    metadata: Dict[str, Any] = Field(default_factory=dict)
    source: str = "report"


class ChatWebSearchResult(BaseModel):
    """Chat web search result."""
    title: str
    url: str
    snippet: str
    relevance_score: float
    source: str = "web"


class ChatContext(BaseModel):
    """Chat context for conversation."""
    report_id: str
    user_id: str
    chat_session_id: Optional[str] = None
    conversation_history: List[ChatMessage] = Field(default_factory=list)
    web_search_enabled: bool = False
    max_history_length: int = 10
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChatConfig(BaseModel):
    """Chat configuration."""
    max_query_length: int = 1000
    max_response_length: int = 2000
    similarity_threshold: float = 0.2
    max_chunks: int = 5
    web_search_enabled: bool = False
    rate_limit_window: int = 60
    rate_limit_max_requests: int = 20
    session_timeout: int = 3600  # 1 hour
    max_conversation_history: int = 50


class ChatError(BaseModel):
    """Chat error model."""
    error_code: ChatErrorCode
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user_id: Optional[str] = None
    report_id: Optional[str] = None


class ChatAnalytics(BaseModel):
    """Chat analytics data."""
    user_id: str
    report_id: str
    session_id: Optional[str] = None
    query_count: int = 0
    total_processing_time: float = 0.0
    average_response_time: float = 0.0
    web_search_usage: int = 0
    error_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ChatPagination(BaseModel):
    """Chat pagination model."""
    page: int = 1
    per_page: int = 20
    total: int = 0
    pages: int = 0
    has_next: bool = False
    has_prev: bool = False


class ChatFilter(BaseModel):
    """Chat filter model."""
    user_id: Optional[str] = None
    report_id: Optional[str] = None
    session_id: Optional[str] = None
    message_type: Optional[ChatMessageType] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    search_query: Optional[str] = None


class ChatExportRequest(BaseModel):
    """Chat export request model."""
    user_id: str
    report_id: Optional[str] = None
    session_id: Optional[str] = None
    format: str = "json"  # json, csv, txt
    include_metadata: bool = False
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class ChatExportResponse(BaseModel):
    """Chat export response model."""
    export_id: str
    download_url: str
    format: str
    record_count: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime


# Constants for chat functionality
DEFAULT_SIMILARITY_THRESHOLD = 0.2
DEFAULT_MAX_CHUNKS = 5
DEFAULT_MAX_QUERY_LENGTH = 1000
DEFAULT_MAX_RESPONSE_LENGTH = 2000
DEFAULT_RATE_LIMIT_WINDOW = 60
DEFAULT_RATE_LIMIT_MAX_REQUESTS = 20
DEFAULT_SESSION_TIMEOUT = 3600
DEFAULT_MAX_CONVERSATION_HISTORY = 50

# Chat error messages
CHAT_ERROR_MESSAGES = {
    ChatErrorCode.AUTHENTICATION_FAILED: "Authentication failed or rate limit exceeded",
    ChatErrorCode.RATE_LIMIT_EXCEEDED: "Too many chat messages. Please try again later.",
    ChatErrorCode.REPORT_NOT_FOUND: "The report you're trying to chat with could not be found. It may have been deleted or you may not have access to it.",
    ChatErrorCode.ACCESS_DENIED: "You don't have permission to chat with this report.",
    ChatErrorCode.NO_CHUNKS_FOUND: "This report is still being processed and isn't ready for chat yet. The system is currently analyzing and indexing the content. Please try again in a few moments.",
    ChatErrorCode.PROCESSING_IN_PROGRESS: "The report is still being processed. Please try again in a few moments.",
    ChatErrorCode.VALIDATION_ERROR: "An error occurred while validating the report.",
    ChatErrorCode.CHAT_SERVICE_ERROR: "An error occurred while processing your chat message.",
    ChatErrorCode.WEB_SEARCH_ERROR: "Web search is temporarily unavailable.",
    ChatErrorCode.QUERY_PROCESSING_ERROR: "An error occurred while processing your query."
}

# Chat validation rules
CHAT_VALIDATION_RULES = {
    "max_query_length": DEFAULT_MAX_QUERY_LENGTH,
    "min_query_length": 1,
    "max_response_length": DEFAULT_MAX_RESPONSE_LENGTH,
    "similarity_threshold": DEFAULT_SIMILARITY_THRESHOLD,
    "max_chunks": DEFAULT_MAX_CHUNKS,
    "rate_limit_window": DEFAULT_RATE_LIMIT_WINDOW,
    "rate_limit_max_requests": DEFAULT_RATE_LIMIT_MAX_REQUESTS
}

# Chat message templates
CHAT_MESSAGE_TEMPLATES = {
    "welcome": "Hello! I'm here to help you understand this report. What would you like to know?",
    "error_generic": "I'm sorry, I encountered an error while processing your request. Please try again.",
    "no_results": "I couldn't find relevant information in the report to answer your question. You might want to try rephrasing your question or asking about a different topic.",
    "processing": "I'm processing your request. This may take a moment...",
    "rate_limited": "You've reached the rate limit for chat messages. Please wait a moment before trying again."
}


