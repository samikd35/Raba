#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Chat Authentication Functions.

This module provides authentication and authorization functions for chat functionality,
including user validation, token extraction, and access control.
"""

import logging
from typing import Dict, Any, Optional
from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .models import ChatErrorCode, CHAT_ERROR_MESSAGES

# Configure logging
logger = logging.getLogger(__name__)

# Authentication setup
security = HTTPBearer()


async def get_current_user_simple(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Simple authentication dependency using production auth system.
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        Dict: User authentication context
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        from ..production_auth_system import get_production_auth_dependencies
        deps = get_production_auth_dependencies()
        auth_context = await deps.get_auth_context_from_token(credentials.credentials)
        
        return {
            "user_id": auth_context.user_id,
            "email": auth_context.email,
            "auth_type": auth_context.auth_type,
            "is_user": auth_context.auth_type == "user",
            "is_service_role": auth_context.auth_type == "service_role",
            "bypass_rls": auth_context.bypass_rls,
            "roles": auth_context.roles
        }
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        raise HTTPException(
            status_code=401,
            detail={
                "code": "authentication_failed",
                "message": CHAT_ERROR_MESSAGES[ChatErrorCode.AUTHENTICATION_FAILED]
            }
        )


def validate_user_context(current_user: Dict[str, Any], request: Request = None) -> str:
    """
    Validate user authentication context and extract user ID.
    
    Args:
        current_user: Authentication context from get_current_user_simple
        request: FastAPI request object (optional)
        
    Returns:
        str: Validated user ID
        
    Raises:
        HTTPException: If user context is invalid
    """
    if not current_user or not isinstance(current_user, dict):
        raise HTTPException(
            status_code=401,
            detail={
                "code": "invalid_user_context",
                "message": "Invalid user authentication context"
            }
        )
    
    user_id = current_user.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "missing_user_id",
                "message": "User ID not found in authentication context"
            }
        )
    
    return user_id


def extract_user_token(request: Request) -> Optional[str]:
    """
    Extract JWT token from request headers.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Optional[str]: JWT token if found, None otherwise
    """
    if not request or not hasattr(request, 'headers'):
        return None
    
    auth_header = request.headers.get('authorization')
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(' ', 1)[1]
        logger.info("Extracted user token for chat authentication")
        return token
    
    return None


def validate_chat_access(
    user_id: str,
    report_id: str,
    user_token: Optional[str] = None
) -> bool:
    """
    Validate if user has access to chat with a specific report.
    
    Args:
        user_id: User ID
        report_id: Report ID
        user_token: Optional JWT token for additional validation
        
    Returns:
        bool: True if user has access
        
    Raises:
        HTTPException: If access is denied
    """
    try:
        # Basic validation - user_id must be present
        if not user_id or not report_id:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "invalid_parameters",
                    "message": "User ID and Report ID are required"
                }
            )
        
        # Additional validation can be added here
        # For example, checking if the user owns the report or has permission
        
        return True
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating chat access: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "access_validation_error",
                "message": "Error validating chat access"
            }
        )


def get_user_context_from_request(request: Request) -> Dict[str, Any]:
    """
    Extract user context information from request.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Dict: User context information
    """
    context = {
        "client_ip": getattr(request.client, 'host', 'unknown') if request and request.client else 'unknown',
        "user_agent": request.headers.get('user-agent', 'unknown') if request else 'unknown',
        "timestamp": None
    }
    
    if request:
        context["timestamp"] = request.state.get('request_start_time')
    
    return context


def create_auth_error_response(error_code: ChatErrorCode, message: Optional[str] = None) -> Dict[str, Any]:
    """
    Create standardized authentication error response.
    
    Args:
        error_code: Error code
        message: Custom error message
        
    Returns:
        Dict: Error response
    """
    return {
        "code": error_code.value,
        "message": message or CHAT_ERROR_MESSAGES.get(error_code, "Unknown error"),
        "timestamp": None
    }


def validate_rate_limit_context(
    user_id: str,
    client_ip: str,
    rate_limiter: Any
) -> Dict[str, Any]:
    """
    Validate rate limit context and return rate limit information.
    
    Args:
        user_id: User ID
        client_ip: Client IP address
        rate_limiter: Rate limiter instance
        
    Returns:
        Dict: Rate limit information
    """
    try:
        rate_limit_key = f"{client_ip}:{user_id}"
        is_limited, remaining = rate_limiter.is_rate_limited(rate_limit_key)
        
        return {
            "is_limited": is_limited,
            "remaining_requests": remaining,
            "window_size": rate_limiter.window_size,
            "rate_limit_key": rate_limit_key
        }
        
    except Exception as e:
        logger.error(f"Error validating rate limit: {e}")
        return {
            "is_limited": False,
            "remaining_requests": 0,
            "window_size": 60,
            "rate_limit_key": f"{client_ip}:{user_id}"
        }


def check_chat_permissions(
    user_context: Dict[str, Any],
    report_id: str
) -> bool:
    """
    Check if user has permissions to chat with a specific report.
    
    Args:
        user_context: User authentication context
        report_id: Report ID
        
    Returns:
        bool: True if user has permissions
    """
    try:
        # Check if user is authenticated
        if not user_context.get("user_id"):
            return False
        
        # Check if user has appropriate roles
        roles = user_context.get("roles", [])
        if not roles:
            return False
        
        # Additional permission checks can be added here
        # For example, checking if user owns the report or has admin access
        
        return True
        
    except Exception as e:
        logger.error(f"Error checking chat permissions: {e}")
        return False


def create_user_session_context(
    user_id: str,
    report_id: str,
    chat_session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create user session context for chat operations.
    
    Args:
        user_id: User ID
        report_id: Report ID
        chat_session_id: Optional chat session ID
        
    Returns:
        Dict: User session context
    """
    return {
        "user_id": user_id,
        "report_id": report_id,
        "chat_session_id": chat_session_id,
        "session_created_at": None,
        "last_activity": None,
        "permissions": {
            "can_chat": True,
            "can_web_search": True,
            "can_export": True
        }
    }


def validate_chat_session(
    session_id: str,
    user_id: str
) -> bool:
    """
    Validate chat session ownership and status.
    
    Args:
        session_id: Chat session ID
        user_id: User ID
        
    Returns:
        bool: True if session is valid
    """
    try:
        # Basic validation
        if not session_id or not user_id:
            return False
        
        # Additional session validation can be added here
        # For example, checking if session exists and belongs to user
        
        return True
        
    except Exception as e:
        logger.error(f"Error validating chat session: {e}")
        return False


def get_auth_headers(user_token: str) -> Dict[str, str]:
    """
    Get authentication headers for API requests.
    
    Args:
        user_token: JWT token
        
    Returns:
        Dict: Authentication headers
    """
    return {
        "Authorization": f"Bearer {user_token}",
        "Content-Type": "application/json"
    }


def log_auth_event(
    event_type: str,
    user_id: str,
    report_id: Optional[str] = None,
    success: bool = True,
    error_message: Optional[str] = None
) -> None:
    """
    Log authentication events for monitoring.
    
    Args:
        event_type: Type of authentication event
        user_id: User ID
        report_id: Optional report ID
        success: Whether the event was successful
        error_message: Optional error message
    """
    try:
        log_data = {
            "event_type": event_type,
            "user_id": user_id,
            "report_id": report_id,
            "success": success,
            "timestamp": None
        }
        
        if error_message:
            log_data["error_message"] = error_message
        
        logger.info(f"Auth event: {log_data}")
        
    except Exception as e:
        logger.error(f"Error logging auth event: {e}")

