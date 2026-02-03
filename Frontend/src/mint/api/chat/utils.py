#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Chat Utility Functions.

This module provides utility functions for chat operations, including
message processing, validation, formatting, and performance monitoring.
"""

import logging
import time
import uuid
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone, timedelta
import json

from .models import (
    ChatMessage, ChatMessageType, ChatErrorCode, ChatPerformanceMetrics,
    ChatSearchResult, ChatWebSearchResult, ChatContext, ChatConfig,
    CHAT_ERROR_MESSAGES, CHAT_VALIDATION_RULES, CHAT_MESSAGE_TEMPLATES
)

# Configure logging
logger = logging.getLogger(__name__)


def generate_message_id() -> str:
    """
    Generate a unique message ID.
    
    Returns:
        str: Unique message ID
    """
    return str(uuid.uuid4())


def generate_session_id() -> str:
    """
    Generate a unique chat session ID.
    
    Returns:
        str: Unique session ID
    """
    return str(uuid.uuid4())


def validate_message_content(content: str) -> Tuple[bool, Optional[str]]:
    """
    Validate chat message content.
    
    Args:
        content: Message content to validate
        
    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    if not content or not isinstance(content, str):
        return False, "Message content is required"
    
    content = content.strip()
    
    if len(content) == 0:
        return False, "Message content cannot be empty"
    
    if len(content) > CHAT_VALIDATION_RULES["max_query_length"]:
        return False, f"Message content exceeds maximum length of {CHAT_VALIDATION_RULES['max_query_length']} characters"
    
    if len(content) < CHAT_VALIDATION_RULES["min_query_length"]:
        return False, f"Message content must be at least {CHAT_VALIDATION_RULES['min_query_length']} character"
    
    return True, None


def validate_report_id(report_id: str) -> Tuple[bool, Optional[str]]:
    """
    Validate report ID format.
    
    Args:
        report_id: Report ID to validate
        
    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    if not report_id or not isinstance(report_id, str):
        return False, "Report ID is required"
    
    report_id = report_id.strip()
    
    if len(report_id) == 0:
        return False, "Report ID cannot be empty"
    
    # Basic UUID format validation
    try:
        uuid.UUID(report_id)
        return True, None
    except ValueError:
        # If not a UUID, it might be a session_id, which is also valid
        if len(report_id) > 0:
            return True, None
        return False, "Invalid report ID format"


def format_chat_message(
    content: str,
    message_type: ChatMessageType,
    user_id: Optional[str] = None,
    report_id: Optional[str] = None,
    chat_session_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> ChatMessage:
    """
    Format a chat message with proper structure.
    
    Args:
        content: Message content
        message_type: Type of message
        user_id: User ID
        report_id: Report ID
        chat_session_id: Chat session ID
        metadata: Additional metadata
        
    Returns:
        ChatMessage: Formatted chat message
    """
    return ChatMessage(
        id=generate_message_id(),
        content=content,
        message_type=message_type,
        user_id=user_id,
        report_id=report_id,
        chat_session_id=chat_session_id,
        metadata=metadata or {}
    )


def create_error_message(
    error_code: ChatErrorCode,
    custom_message: Optional[str] = None,
    user_id: Optional[str] = None,
    report_id: Optional[str] = None
) -> ChatMessage:
    """
    Create an error message.
    
    Args:
        error_code: Error code
        custom_message: Custom error message
        user_id: User ID
        report_id: Report ID
        
    Returns:
        ChatMessage: Error message
    """
    message = custom_message or CHAT_ERROR_MESSAGES.get(error_code, "Unknown error")
    
    return ChatMessage(
        id=generate_message_id(),
        content=message,
        message_type=ChatMessageType.ERROR,
        user_id=user_id,
        report_id=report_id,
        metadata={
            "error_code": error_code.value,
            "is_error": True
        }
    )


def create_success_message(
    content: str,
    user_id: Optional[str] = None,
    report_id: Optional[str] = None,
    chat_session_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> ChatMessage:
    """
    Create a success message.
    
    Args:
        content: Message content
        user_id: User ID
        report_id: Report ID
        chat_session_id: Chat session ID
        metadata: Additional metadata
        
    Returns:
        ChatMessage: Success message
    """
    return ChatMessage(
        id=generate_message_id(),
        content=content,
        message_type=ChatMessageType.ASSISTANT,
        user_id=user_id,
        report_id=report_id,
        chat_session_id=chat_session_id,
        metadata=metadata or {}
    )


def format_search_results(
    chunks: List[Dict[str, Any]],
    similarity_threshold: float = 0.2
) -> List[ChatSearchResult]:
    """
    Format search results for chat.
    
    Args:
        chunks: List of chunk data
        similarity_threshold: Minimum similarity threshold
        
    Returns:
        List[ChatSearchResult]: Formatted search results
    """
    results = []
    
    for chunk in chunks:
        if chunk.get("similarity", 0.0) >= similarity_threshold:
            results.append(ChatSearchResult(
                chunk_id=chunk.get("id", ""),
                content=chunk.get("content", ""),
                similarity=chunk.get("similarity", 0.0),
                metadata=chunk.get("metadata", {}),
                source="report"
            ))
    
    return results


def format_web_search_results(
    web_results: List[Dict[str, Any]]
) -> List[ChatWebSearchResult]:
    """
    Format web search results for chat.
    
    Args:
        web_results: List of web search data
        
    Returns:
        List[ChatWebSearchResult]: Formatted web search results
    """
    results = []
    
    for result in web_results:
        results.append(ChatWebSearchResult(
            title=result.get("title", ""),
            url=result.get("url", ""),
            snippet=result.get("snippet", ""),
            relevance_score=result.get("relevance_score", 0.0),
            source="web"
        ))
    
    return results


def calculate_processing_time(start_time: float, end_time: Optional[float] = None) -> float:
    """
    Calculate processing time in seconds.
    
    Args:
        start_time: Start time timestamp
        end_time: End time timestamp (uses current time if None)
        
    Returns:
        float: Processing time in seconds
    """
    if end_time is None:
        end_time = time.time()
    
    return end_time - start_time


def create_performance_metrics(
    query_id: str,
    processing_time: float,
    validation_time: float = 0.0,
    search_time: float = 0.0,
    generation_time: float = 0.0,
    total_tokens: int = 0,
    chunks_retrieved: int = 0,
    web_search_enabled: bool = False,
    success: bool = True,
    error_code: Optional[ChatErrorCode] = None
) -> ChatPerformanceMetrics:
    """
    Create performance metrics for a chat operation.
    
    Args:
        query_id: Query ID
        processing_time: Total processing time
        validation_time: Validation time
        search_time: Search time
        generation_time: Generation time
        total_tokens: Total tokens used
        chunks_retrieved: Number of chunks retrieved
        web_search_enabled: Whether web search was enabled
        success: Whether operation was successful
        error_code: Error code if failed
        
    Returns:
        ChatPerformanceMetrics: Performance metrics
    """
    return ChatPerformanceMetrics(
        query_id=query_id,
        processing_time=processing_time,
        validation_time=validation_time,
        search_time=search_time,
        generation_time=generation_time,
        total_tokens=total_tokens,
        chunks_retrieved=chunks_retrieved,
        web_search_enabled=web_search_enabled,
        success=success,
        error_code=error_code
    )


def format_chat_context(
    report_id: str,
    user_id: str,
    conversation_history: List[ChatMessage],
    web_search_enabled: bool = False,
    max_history_length: int = 10
) -> ChatContext:
    """
    Format chat context for conversation.
    
    Args:
        report_id: Report ID
        user_id: User ID
        conversation_history: List of conversation messages
        web_search_enabled: Whether web search is enabled
        max_history_length: Maximum history length
        
    Returns:
        ChatContext: Formatted chat context
    """
    # Limit conversation history
    if len(conversation_history) > max_history_length:
        conversation_history = conversation_history[-max_history_length:]
    
    return ChatContext(
        report_id=report_id,
        user_id=user_id,
        conversation_history=conversation_history,
        web_search_enabled=web_search_enabled,
        max_history_length=max_history_length
    )


def extract_message_metadata(
    message: ChatMessage,
    include_timing: bool = True
) -> Dict[str, Any]:
    """
    Extract metadata from a chat message.
    
    Args:
        message: Chat message
        include_timing: Whether to include timing information
        
    Returns:
        Dict: Message metadata
    """
    metadata = {
        "message_id": message.id,
        "message_type": message.message_type.value,
        "user_id": message.user_id,
        "report_id": message.report_id,
        "chat_session_id": message.chat_session_id,
        "content_length": len(message.content),
        "timestamp": message.timestamp.isoformat()
    }
    
    if include_timing:
        metadata.update({
            "created_at": message.timestamp.isoformat(),
            "time_since_epoch": message.timestamp.timestamp()
        })
    
    # Add custom metadata
    if message.metadata:
        metadata.update(message.metadata)
    
    return metadata


def format_chat_response(
    message: ChatMessage,
    success: bool = True,
    error: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Format chat response for API.
    
    Args:
        message: Chat message
        success: Whether operation was successful
        error: Error message if any
        metadata: Additional metadata
        
    Returns:
        Dict: Formatted response
    """
    response = {
        "id": message.id,
        "content": message.content,
        "success": success,
        "chat_session_id": message.chat_session_id,
        "metadata": metadata or {}
    }
    
    if error:
        response["error"] = error
    
    return response


def validate_chat_config(config: ChatConfig) -> List[str]:
    """
    Validate chat configuration.
    
    Args:
        config: Chat configuration
        
    Returns:
        List[str]: List of validation errors
    """
    errors = []
    
    if config.max_query_length <= 0:
        errors.append("max_query_length must be positive")
    
    if config.max_response_length <= 0:
        errors.append("max_response_length must be positive")
    
    if config.similarity_threshold < 0 or config.similarity_threshold > 1:
        errors.append("similarity_threshold must be between 0 and 1")
    
    if config.max_chunks <= 0:
        errors.append("max_chunks must be positive")
    
    if config.rate_limit_window <= 0:
        errors.append("rate_limit_window must be positive")
    
    if config.rate_limit_max_requests <= 0:
        errors.append("rate_limit_max_requests must be positive")
    
    if config.session_timeout <= 0:
        errors.append("session_timeout must be positive")
    
    if config.max_conversation_history <= 0:
        errors.append("max_conversation_history must be positive")
    
    return errors


def format_error_response(
    error_code: ChatErrorCode,
    custom_message: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Format error response for API.
    
    Args:
        error_code: Error code
        custom_message: Custom error message
        details: Additional error details
        
    Returns:
        Dict: Formatted error response
    """
    response = {
        "id": generate_message_id(),
        "content": custom_message or CHAT_ERROR_MESSAGES.get(error_code, "Unknown error"),
        "success": False,
        "error": error_code.value,
        "metadata": details or {}
    }
    
    return response


def create_success_response(
    content: str,
    chat_session_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create success response for API.
    
    Args:
        content: Response content
        chat_session_id: Chat session ID
        metadata: Additional metadata
        
    Returns:
        Dict: Formatted success response
    """
    return {
        "id": generate_message_id(),
        "content": content,
        "success": True,
        "chat_session_id": chat_session_id,
        "metadata": metadata or {}
    }


def log_chat_operation(
    operation: str,
    user_id: str,
    report_id: str,
    success: bool = True,
    error_code: Optional[ChatErrorCode] = None,
    processing_time: Optional[float] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log chat operation for monitoring.
    
    Args:
        operation: Operation type
        user_id: User ID
        report_id: Report ID
        success: Whether operation was successful
        error_code: Error code if failed
        processing_time: Processing time in seconds
        metadata: Additional metadata
    """
    try:
        log_data = {
            "operation": operation,
            "user_id": user_id,
            "report_id": report_id,
            "success": success,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        if error_code:
            log_data["error_code"] = error_code.value
        
        if processing_time is not None:
            log_data["processing_time"] = processing_time
        
        if metadata:
            log_data.update(metadata)
        
        logger.info(f"Chat operation: {json.dumps(log_data)}")
        
    except Exception as e:
        logger.error(f"Error logging chat operation: {e}")


def format_timestamp(timestamp: datetime) -> str:
    """
    Format timestamp for display.
    
    Args:
        timestamp: Timestamp to format
        
    Returns:
        str: Formatted timestamp
    """
    return timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")


def calculate_message_age(message: ChatMessage) -> float:
    """
    Calculate age of a message in seconds.
    
    Args:
        message: Chat message
        
    Returns:
        float: Message age in seconds
    """
    now = datetime.now(timezone.utc)
    return (now - message.timestamp).total_seconds()


def is_message_recent(message: ChatMessage, max_age_seconds: int = 3600) -> bool:
    """
    Check if a message is recent.
    
    Args:
        message: Chat message
        max_age_seconds: Maximum age in seconds
        
    Returns:
        bool: True if message is recent
    """
    return calculate_message_age(message) <= max_age_seconds


def get_message_template(template_key: str) -> str:
    """
    Get message template by key.
    
    Args:
        template_key: Template key
        
    Returns:
        str: Message template
    """
    return CHAT_MESSAGE_TEMPLATES.get(template_key, "Hello! How can I help you?")


def format_conversation_summary(
    messages: List[ChatMessage],
    max_messages: int = 10
) -> str:
    """
    Format conversation summary.
    
    Args:
        messages: List of messages
        max_messages: Maximum number of messages to include
        
    Returns:
        str: Conversation summary
    """
    if not messages:
        return "No messages in conversation"
    
    # Take the last N messages
    recent_messages = messages[-max_messages:] if len(messages) > max_messages else messages
    
    summary_parts = []
    for message in recent_messages:
        role = "User" if message.message_type == ChatMessageType.USER else "Assistant"
        summary_parts.append(f"{role}: {message.content[:100]}...")
    
    return "\n".join(summary_parts)


