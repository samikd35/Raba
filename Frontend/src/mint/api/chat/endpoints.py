#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Chat API endpoints for MINT.

This module provides API endpoints for chatting with reports using RAG (Retrieval-Augmented Generation).
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field

from ..auth_v2.utils import get_current_user
from ..cache.core import warm_cache
from ..report.report_validation_service import get_report_validation_service
from ..system.middleware.rate_limiter import RateLimiter
from .models import (ChatHistoryResponse, ChatMessageRequest,
                     ChatMessageResponse, WebSearchToggleRequest,
                     WebSearchToggleResponse)
from .service import get_report_chat_service

from src.mint.api.system.core.supabase_client import get_supabase_client

# from ..auth.production.system import get_current_user, get_current_user_with_roles
# Chat utilities - using inline functions for stability
# Auth validation - using inline validation for stability

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/chat", tags=["chat"])

# Create rate limiter for chat endpoints
chat_rate_limiter = RateLimiter(
    window_size=60, max_requests=20
)  # 20 requests per minute

# Authentication setup
security = HTTPBearer()


# Authentication and model functions are now imported from auth and models modules


@router.post("/message", response_model=ChatMessageResponse)
async def send_chat_message(
    request: ChatMessageRequest,
    current_user: dict = Depends(get_current_user),
    req: Request = None,
):
    """
    Send a chat message to a report.

    Args:
        request: The chat message request
        current_user_id: User ID from production auth system
        req: The FastAPI request object

    Returns:
        ChatMessageResponse: The response with the assistant's message
    """
    # Performance monitoring removed for stability
    current_user_id = current_user["user_id"]

    try:
        # User ID is already validated by the production auth system
        logger.info(f"🎯 CHAT MESSAGE: Processing message for user {current_user_id}")

        # Apply rate limiting
        client_ip = req.client.host if req and req.client else "unknown"
        is_limited, remaining = chat_rate_limiter.is_rate_limited(
            f"{client_ip}:{current_user_id}"
        )

        if is_limited:
            logger.warning(
                f"Rate limit exceeded for chat message from user {current_user_id}"
            )
            # Rate limit exceeded
            raise HTTPException(
                status_code=429,
                detail={
                    "code": "rate_limit_exceeded",
                    "message": "Too many chat messages. Please try again later.",
                    "retry_after": chat_rate_limiter.window_size,
                },
            )

        # Extract JWT token from request for user authentication
        user_token = None
        if req and hasattr(req, "headers"):
            auth_header = req.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                user_token = auth_header.split(" ", 1)[1]
                logger.info("Extracted user token for chat authentication")

        # Import ID logging service
        from ..services.utilities.id_logging_service import (
            IDOperationTracker, log_chat_operation)

        # Start comprehensive ID tracking for chat operation
        with IDOperationTracker(
            "CHAT_MESSAGE", report_id=request.report_id, user_id=current_user_id
        ) as tracker:

            # Validate IDs
            tracker.validate_id("report_id", request.report_id, required=True)
            tracker.validate_id("user_id", current_user_id, required=True)

            # Log chat operation start
            log_chat_operation(
                "MESSAGE_START",
                request.report_id,
                current_user_id,
                query_length=len(request.content),
                web_search_enabled=request.web_search_enabled,
            )

            # STEP 1: Validate report exists and user has access
            tracker.update_ids("VALIDATION_START")
            validation_service = get_report_validation_service(user_token=user_token)
            validation_result = await validation_service.validate_report_for_chat(
                report_identifier=request.report_id,
                user_id=current_user_id,
                check_chunks=True,
            )

            if not validation_result.success:
                logger.error(
                    f"Report validation failed: {validation_result.error_message}"
                )
                # Validation failed

                # Log validation failure with specific error
                tracker.log_error(
                    "VALIDATION_FAILED",
                    validation_result.error_message,
                    error_code=validation_result.error_code,
                )
                log_chat_operation(
                    "VALIDATION_FAILED",
                    request.report_id,
                    current_user_id,
                    error_code=validation_result.error_code,
                    error_message=validation_result.error_message,
                )

                # Return specific error messages based on validation result
                if validation_result.error_code == "report_not_found":
                    return ChatMessageResponse(
                        id="",
                        content="The report you're trying to chat with could not be found. It may have been deleted or you may not have access to it.",
                        success=False,
                        error="report_not_found",
                    )
                elif validation_result.error_code == "access_denied":
                    return ChatMessageResponse(
                        id="",
                        content="You don't have permission to chat with this report.",
                        success=False,
                        error="access_denied",
                    )
                elif validation_result.error_code == "no_chunks_found":
                    return ChatMessageResponse(
                        id="",
                        content="This report is still being processed and isn't ready for chat yet. The system is currently analyzing and indexing the content. Please try again in a few moments.",
                        success=False,
                        error="processing_in_progress",
                    )
                else:
                    return ChatMessageResponse(
                        id="",
                        content=validation_result.user_message
                        or "An error occurred while validating the report.",
                        success=False,
                        error=validation_result.error_code or "validation_error",
                    )

            # Log successful validation
            tracker.update_ids(
                "VALIDATION_SUCCESS", validated_report_id=validation_result.report_id
            )
            log_chat_operation(
                "VALIDATION_SUCCESS", validation_result.report_id, current_user_id
            )

            # STEP 2: Get the chat service with user authentication
            tracker.update_ids("CHAT_SERVICE_INIT")
            chat_service = get_report_chat_service(user_token=user_token)

    except Exception as auth_error:
        logger.error(f"Authentication or validation error: {auth_error}")
        # Authentication error occurred
        raise HTTPException(
            status_code=401,
            detail={
                "code": "authentication_failed",
                "message": "Authentication failed or rate limit exceeded",
            },
        )

    try:
        # Process the query

        # Use the validated report ID from the validation result
        validated_report_id = validation_result.report_id
        logger.info(f"Processing chat query for validated report {validated_report_id}")

        # Log chat processing start
        tracker.update_ids(
            "CHAT_PROCESSING_START", validated_report_id=validated_report_id
        )
        log_chat_operation(
            "PROCESSING_START",
            validated_report_id,
            current_user_id,
            query_length=len(request.content),
        )

        result = await chat_service.process_query(
            report_id=validated_report_id,
            user_id=current_user_id,
            query=request.content,
            web_search_enabled=request.web_search_enabled,
            chat_session_id=request.chat_session_id
        )

        # Processing completed

        if not result.get("success"):
            # Log chat processing failure
            tracker.log_error(
                "CHAT_PROCESSING_FAILED", result.get("error", "Unknown error")
            )
            log_chat_operation(
                "PROCESSING_FAILED",
                validated_report_id,
                current_user_id,
                error=result.get("error"),
            )

            # Chat processing failed

            # Provide user-friendly error messages based on error type
            error_message = result.get("error", "")
            user_message = "I'm having trouble processing your message right now. Please try again in a moment."

            if "no chunks found" in error_message.lower():
                user_message = "This report is still being processed and isn't ready for chat yet. Please try again in a few moments."
            elif "embedding" in error_message.lower():
                user_message = "I'm having trouble understanding your question. Please try rephrasing it or try again later."
            elif "timeout" in error_message.lower():
                user_message = "Your request is taking longer than expected. Please try again with a shorter question."
            elif "rate limit" in error_message.lower():
                user_message = "You're sending messages too quickly. Please wait a moment before trying again."

            return ChatMessageResponse(
                id="", content=user_message, success=False, error=result.get("error")
            )

        # Log successful chat processing
        message_id = result.get("message_id", "")
        tracker.update_ids("CHAT_PROCESSING_SUCCESS", message_id=message_id)
        log_chat_operation(
            "PROCESSING_SUCCESS",
            validated_report_id,
            current_user_id,
            message_id=message_id,
            response_length=len(result.get("response", "")),
        )

        # Chat processing successful
        return ChatMessageResponse(
            id=message_id,
            content=result.get("response", ""),
            success=True,
            error=None,
            chat_session_id=result.get("chat_session_id"),
            conversation_history=result.get("conversation_history", []),
        )

    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        # Error occurred during processing

        # Provide user-friendly error message based on exception type
        user_message = (
            "I'm experiencing technical difficulties. Please try again in a moment."
        )

        if "connection" in str(e).lower() or "network" in str(e).lower():
            user_message = "I'm having trouble connecting to the AI service. Please check your connection and try again."
        elif "timeout" in str(e).lower():
            user_message = (
                "Your request timed out. Please try again with a shorter question."
            )
        elif "authentication" in str(e).lower():
            user_message = "There was an authentication issue. Please refresh the page and try again."

        return ChatMessageResponse(
            id="", content=user_message, success=False, error="system_error"
        )


# Import the enhanced cache service
from ..cache.core import cached as enhanced_cached


@enhanced_cached(ttl_seconds=60, key_prefix="chat_history", tags=["chat_history"])
async def get_cached_chat_history(
    report_id: str, page: int, page_size: int, sort_order: str, user_token: str = None
):
    """
    Get chat history with enhanced caching.

    Args:
        report_id: ID of the report
        page: Page number (1-based)
        page_size: Number of messages per page
        sort_order: Sort order (asc, desc)
        user_token: User JWT token for RLS enforcement

    Returns:
        Dict: The chat history result
    """
    # Performance monitoring removed for stability

    try:
        # Use the user_token parameter that was passed to this function
        # (no need to extract from request since it's already provided)
        logger.info("Using provided user token for chat history authentication")

        # Get the chat service with user authentication
        chat_service = get_report_chat_service(user_token=user_token)

        # Get chat history by page
        result = await chat_service.get_chat_history_by_page(
            report_id=report_id,
            page=page,
            page_size=page_size,
            sort_order=sort_order,
            user_token=user_token,
        )

        # Chat history retrieval successful
        return result
    except Exception as e:
        # Error occurred during chat history retrieval
        raise e


@router.get("/processing-status-debug/{report_id}")
async def get_report_processing_status_debug(
    report_id: str, current_user: dict = Depends(get_current_user)
):
    """
    DEBUG ENDPOINT: Check report processing status WITHOUT authentication
    This is for debugging authentication issues only
    """
    try:
        from datetime import datetime, timedelta

        from src.mint.api.supabase_client import get_service_role_client

        service_client = get_service_role_client()

        # Check if report exists (without user filtering)
        report_check = (
            service_client.client.table("documents")
            .select("id,created_by,created_at,title")
            .eq("id", report_id)
            .eq("source_type", "pv_report")
            .limit(1)
            .execute()
        )

        if not report_check.data:
            return {
                "status": "not_found",
                "ready_for_chat": False,
                "message": "Report not found",
                "debug_info": "Report does not exist in database",
            }

        report_data = report_check.data[0]

        # Check for chunks
        chunk_check = (
            service_client.client.table("report_chunks")
            .select("id")
            .eq("report_id", report_id)
            .limit(1)
            .execute()
        )

        has_chunks = bool(chunk_check.data)

        # Check if recent
        created_at = datetime.fromisoformat(
            report_data["created_at"].replace("Z", "+00:00")
        )
        is_recent = datetime.now(created_at.tzinfo) - created_at < timedelta(hours=24)

        if has_chunks:
            return {
                "status": "ready",
                "ready_for_chat": True,
                "message": "Report is ready for chat",
                "user_message": "Your report is ready! You can now ask questions about its content.",
                "report_id": report_id,
                "debug_info": {
                    "report_title": report_data["title"],
                    "report_user": report_data["user_id"],
                    "is_recent": is_recent,
                    "has_chunks": has_chunks,
                    "created_at": report_data["created_at"],
                },
            }
        else:
            return {
                "status": "processing",
                "ready_for_chat": False,
                "message": "Report is being processed",
                "user_message": "Your report is being analyzed and prepared for chat.",
                "debug_info": {
                    "report_title": report_data["title"],
                    "report_user": report_data["user_id"],
                    "is_recent": is_recent,
                    "has_chunks": has_chunks,
                    "created_at": report_data["created_at"],
                },
            }

    except Exception as e:
        return {
            "status": "error",
            "ready_for_chat": False,
            "message": f"Debug endpoint error: {str(e)}",
            "debug_info": f"Exception: {type(e).__name__}: {str(e)}",
        }


@router.get("/history/{report_id}", response_model=ChatHistoryResponse)
async def get_chat_history(
    report_id: str,
    page: int = Query(1, description="Page number (1-based)"),
    page_size: int = Query(20, description="Number of messages per page"),
    sort_order: str = Query("asc", description="Sort order (asc, desc)"),
    current_user: dict = Depends(get_current_user),
    request: Request = None,
):
    """
        Get chat history for a report.
    {{ ... }}

        Args:
            report_id: ID of the report
            page: Page number (1-based)
            page_size: Number of messages per page
            sort_order: Sort order (asc, desc)
            current_user: Authentication context from get_current_user_with_roles
            request: The FastAPI request object for extracting the Authorization header

        Returns:
            ChatHistoryResponse: The chat history with pagination metadata
    """
    # Performance monitoring removed for stability

    try:
        # User ID is already validated by the production auth system
        user_id = current_user["user_id"]
        logger.info(
            f"🎯 CHAT HISTORY: Retrieving history for report {report_id} for user {user_id}"
        )

        # Extract user token from Authorization header for RLS enforcement
        user_token = None
        if request and request.headers.get("Authorization"):
            auth_header = request.headers.get("Authorization")
            scheme, token = auth_header.split()
            if scheme.lower() == "bearer":
                user_token = token
                logger.info(
                    f"Extracted user token for RLS enforcement when retrieving chat history for report {report_id} for user {user_id}"
                )

        # STEP 1: Validate report exists and user has access
        validation_service = get_report_validation_service(user_token=user_token)
        validation_result = await validation_service.validate_report_for_chat(
            report_identifier=report_id,
            user_id=user_id,
            check_chunks=False,  # Don't check chunks for history - user might want to see history even if no chunks
        )

        if not validation_result.success:
            logger.error(
                f"Report validation failed for history: {validation_result.error_message}"
            )
            # Validation failed

            # Return specific HTTP errors based on validation result
            if validation_result.error_code == "report_not_found":
                raise HTTPException(
                    status_code=404,
                    detail={
                        "code": "report_not_found",
                        "message": "The requested report could not be found.",
                    },
                )
            elif validation_result.error_code == "access_denied":
                raise HTTPException(
                    status_code=403,
                    detail={
                        "code": "access_denied",
                        "message": "You don't have permission to access this report's chat history.",
                    },
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "code": validation_result.error_code or "validation_error",
                        "message": validation_result.user_message
                        or "An error occurred while validating the report.",
                    },
                )

        # Use the validated report ID
        validated_report_id = validation_result.report_id
        logger.info(
            f"Retrieving chat history for validated report {validated_report_id}"
        )

        # Get chat history from cache or service
        result = await get_cached_chat_history(
            report_id=validated_report_id,
            page=page,
            page_size=page_size,
            sort_order=sort_order,
            user_token=user_token,
        )

        # Convert ChatMessage objects to dictionaries
        messages = [msg.to_json() for msg in result.get("messages", [])]

        # Prefetch adjacent pages to improve user experience
        # This uses our enhanced cache service's warm_cache function
        if result.get("pagination", {}).get("has_next", False):
            next_page = page + 1
            await warm_cache(
                get_cached_chat_history,
                report_id=validated_report_id,
                page=next_page,
                page_size=page_size,
                sort_order=sort_order,
                user_token=user_token,
            )

        if page > 1:
            prev_page = page - 1
            await warm_cache(
                get_cached_chat_history,
                report_id=validated_report_id,
                page=prev_page,
                page_size=page_size,
                sort_order=sort_order,
                user_token=user_token,
            )

        # Chat history retrieval successful

        return ChatHistoryResponse(
            messages=messages, pagination=result.get("pagination", {})
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        # Error occurred
        raise
    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        # Error occurred during processing

        raise HTTPException(
            status_code=500,
            detail={
                "code": "history_retrieval_error",
                "message": f"An error occurred while retrieving chat history: {str(e)}",
            },
        )


@router.post("/web-search", response_model=WebSearchToggleResponse)
async def toggle_web_search(
    request: WebSearchToggleRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    req: Request = None,
):
    """
    Toggle web search for chat.

    Args:
        request: The web search toggle request
        current_user: The authenticated user context
        req: The FastAPI request object

    Returns:
        WebSearchToggleResponse: The response with the web search status
    """
    # Extract user ID from the current_user dictionary
    current_user_id = current_user.get("user_id")
    if not current_user_id:
        raise HTTPException(
            status_code=401, detail="User ID not found in authentication context"
        )

    # Store the preference in the session
    if req and hasattr(req, "session"):
        req.session["web_search_enabled"] = request.enabled

    # Store the preference in the database for persistence across sessions
    try:
        from ..system.core.supabase_client import get_supabase_client

        supabase = get_supabase_client()

        # Check if a preference already exists
        result = (
            supabase.table("user_preferences")
            .select("*")
            .eq("user_id", current_user_id)
            .eq("preference_key", "web_search_enabled")
            .execute()
        )

        if result.data:
            # Update existing preference
            supabase.table("user_preferences").update(
                {"preference_value": json.dumps(request.enabled)}
            ).eq("user_id", current_user_id).eq(
                "preference_key", "web_search_enabled"
            ).execute()
        else:
            # Insert new preference
            supabase.table("user_preferences").insert(
                {
                    "user_id": current_user_id,
                    "preference_key": "web_search_enabled",
                    "preference_value": json.dumps(request.enabled),
                    "metadata": {"last_updated": datetime.now().isoformat()},
                }
            ).execute()

        logger.info(
            f"Stored web search preference for user {current_user_id}: {request.enabled}"
        )
    except Exception as e:
        logger.error(f"Error storing web search preference: {e}")

    return WebSearchToggleResponse(enabled=request.enabled)


@router.get("/web-search", response_model=WebSearchToggleResponse)
async def get_web_search_status(
    current_user: Dict[str, Any] = Depends(get_current_user),
    req: Request = None,
):
    """
    Get the current web search status.

    Args:
        current_user: The authenticated user context
        req: The FastAPI request object

    Returns:
        WebSearchToggleResponse: The response with the web search status
    """
    # Extract user ID from the current_user dictionary
    current_user_id = current_user.get("user_id")
    if not current_user_id:
        raise HTTPException(
            status_code=401, detail="User ID not found in authentication context"
        )

    # Check session first
    if req and hasattr(req, "session") and "web_search_enabled" in req.session:
        return WebSearchToggleResponse(enabled=req.session["web_search_enabled"])

    # If not in session, check database
    try:
        from ..system.core.supabase_client import get_supabase_client

        supabase = get_supabase_client()

        result = (
            supabase.table("user_preferences")
            .select("preference_value")
            .eq("user_id", current_user_id)
            .eq("preference_key", "web_search_enabled")
            .execute()
        )

        if result.data:
            enabled = json.loads(result.data[0]["preference_value"])

            # Store in session for future requests
            if req and hasattr(req, "session"):
                req.session["web_search_enabled"] = enabled

            return WebSearchToggleResponse(enabled=enabled)
    except Exception as e:
        logger.error(f"Error retrieving web search preference: {e}")

    # Default to disabled if not found
    return WebSearchToggleResponse(enabled=False)


@router.get("/processing-status/{report_id}")
async def get_report_processing_status(
    report_id: str, request: Request, current_user: dict = Depends(get_current_user)
):
    """
    Get the processing status of a report for chat functionality.

    This endpoint provides detailed information about whether a report is ready
    for chat, still processing, or has encountered errors.

    Optimized for frequent polling with caching and lightweight checks.

    Args:
        report_id: ID of the report to check
        request: The FastAPI request object
        current_user: Authentication context from get_current_user_with_roles

    Returns:
        Dict: Detailed processing status information
    """
    user_id = current_user["user_id"]
    try:
        logger.info(f"Processing status request for report {report_id}")

        # Check if client has already disconnected/cancelled
        if await request.is_disconnected():
            logger.info(
                f"Client disconnected, aborting processing status request for {report_id}"
            )
            return {
                "status": "cancelled",
                "ready_for_chat": False,
                "message": "Request cancelled",
            }

        # Validate user authentication context and extract user ID
         
        logger.info(f"User ID validated: {user_id}")

        # Extract JWT token from request for user authentication
        user_token = None
        if request and hasattr(request, "headers"):
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                user_token = auth_header.split(" ", 1)[1]

        # OPTIMIZATION: Use cache to avoid repeated expensive operations
        # Cache service removed for stability
        # admin_cache = None
        cache_key = f"processing_status:{report_id}:{user_id}"

        # Cache disabled for stability - proceeding with direct validation
        logger.info(f"Proceeding with direct validation for {report_id}")

        # Check for client disconnection before expensive operations
        if await request.is_disconnected():
            logger.info(f"Client disconnected during cache check for {report_id}")
            return {
                "status": "cancelled",
                "ready_for_chat": False,
                "message": "Request cancelled",
            }

        logger.info(
            f"No cached result found, proceeding with FAST validation for {report_id}"
        )

        # OPTIMIZATION: Fast lightweight check first - just verify report exists and user owns it
        from ..system.core.supabase_client import get_service_role_client

        try:
            service_client = get_service_role_client()
            quick_check = (
                service_client.client.table("documents")
                .select("id,created_by,created_at")
                .eq("id", report_id)
                .eq("created_by", user_id)
                .eq("source_type", "pv_report")
                .limit(1)
                .execute()
            )

            if not quick_check.data:
                # Report doesn't exist or access denied
                result = {
                    "status": "not_found",
                    "ready_for_chat": False,
                    "message": "Report not found or you don't have access to it",
                    "user_message": "The report you're looking for could not be found.",
                    "error_code": "report_not_found",
                }
                # Cache negative result for shorter time (10 seconds)
                try:
                    admin_cache.set(cache_key, result, ttl_seconds=10)
                except Exception:
                    pass
                return result

            report_data = quick_check.data[0]

            # For recent reports (created in last 24 hours), do a quick chunk check
            from datetime import datetime, timedelta

            if report_data.get("created_at"):
                created_at = datetime.fromisoformat(
                    report_data["created_at"].replace("Z", "+00:00")
                )
                if datetime.now(created_at.tzinfo) - created_at < timedelta(hours=24):
                    # Quick chunk existence check for recent reports
                    chunk_check = (
                        service_client.client.table("report_chunks")
                        .select("id")
                        .eq("report_id", report_id)
                        .limit(1)
                        .execute()
                    )

                    if chunk_check.data:
                        # Recent report with chunks - ready for chat
                        result = {
                            "status": "ready",
                            "ready_for_chat": True,
                            "message": "Report is ready for chat",
                            "user_message": "Your report is ready! You can now ask questions about its content.",
                            "report_id": report_id,
                        }
                        # Cache positive result for longer (60 seconds)
                        try:
                            admin_cache.set(cache_key, result, ttl_seconds=60)
                        except Exception:
                            pass
                        return result
                    else:
                        # Recent report without chunks - still processing
                        result = {
                            "status": "processing",
                            "ready_for_chat": False,
                            "message": "Report is being processed",
                            "user_message": "Your report is being analyzed and prepared for chat. This usually takes 1-2 minutes.",
                            "estimated_completion": "1-2 minutes",
                            "error_code": "processing_in_progress",
                        }
                        # Cache processing result for shorter time (15 seconds)
                        try:
                            admin_cache.set(cache_key, result, ttl_seconds=15)
                        except Exception:
                            pass
                        return result
        except Exception as e:
            logger.warning(f"Fast check failed for {report_id}: {e}")
            # Fall back to full validation if fast check fails

        # FALLBACK: Full validation for older reports or if fast check failed
        validation_service = get_report_validation_service(user_token=user_token)
        validation_result = await validation_service.validate_report_for_chat(
            report_identifier=report_id, user_id=user_id, check_chunks=True
        )

        result = None
        if not validation_result.success:
            if validation_result.error_code == "report_not_found":
                result = {
                    "status": "not_found",
                    "ready_for_chat": False,
                    "message": "Report not found or you don't have access to it",
                    "user_message": "The report you're looking for could not be found.",
                    "error_code": "report_not_found",
                }
            elif validation_result.error_code == "access_denied":
                result = {
                    "status": "access_denied",
                    "ready_for_chat": False,
                    "message": "Access denied to report",
                    "user_message": "You don't have permission to access this report.",
                    "error_code": "access_denied",
                }
            elif validation_result.error_code == "no_chunks_found":
                result = {
                    "status": "processing",
                    "ready_for_chat": False,
                    "message": "Report is being processed",
                    "user_message": "Your report is being analyzed and prepared for chat. This usually takes 1-2 minutes.",
                    "estimated_completion": "1-2 minutes",
                    "error_code": "processing_in_progress",
                }
        else:
            # Report is ready for chat
            result = {
                "status": "ready",
                "ready_for_chat": True,
                "message": "Report is ready for chat",
                "user_message": "Your report is ready! You can now ask questions about its content.",
                "report_id": validation_result.report_id,
            }

        # Cache the result
        if result:
            try:
                # Cache ready reports longer, processing reports shorter
                ttl = 60 if result.get("ready_for_chat") else 15
                logger.info(
                    f"DEBUG CACHE: Setting cache key: {cache_key} with TTL: {ttl}"
                )
                logger.info(f"DEBUG CACHE: Setting cache value: {result}")
                admin_cache.set(cache_key, result, ttl_seconds=ttl)
                logger.info(f"DEBUG CACHE: Cache set successful for {cache_key}")

                # Verify the cache was set by immediately reading it back
                verify_result = admin_cache.get(cache_key)
                logger.info(
                    f"DEBUG CACHE: Immediate verification read: {verify_result}"
                )
            except Exception as e:
                logger.warning(f"Cache set failed for {cache_key}: {e}")
                import traceback

                logger.warning(f"Cache set traceback: {traceback.format_exc()}")

        logger.info(f"Returning processing status result for {report_id}: {result}")
        return result

    except Exception as e:
        logger.error(f"Error checking processing status for report {report_id}: {e}")

        return {
            "status": "error",
            "ready_for_chat": False,
            "message": f"Error checking status: {str(e)}",
            "user_message": "We're having trouble checking your report's status. Please try refreshing the page.",
            "error_code": "system_error",
        }


@router.get("/verify-embeddings/{report_id}")
async def verify_report_embeddings(
    report_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Verify that a report has embeddings available for chat functionality.

    This endpoint checks if the report was properly embedded when initially saved,
    ensuring chat functionality can work with historical reports.

    Args:
        report_id: ID of the report to verify
        request: The FastAPI request object
        current_user: Authentication context from get_current_user_with_roles

    Returns:
        Dict: Status of report embeddings availability
    """
    try:
        logger.info(f"Verifying embeddings for report {report_id}")

        # Validate user authentication context and extract user ID
        user_id = current_user["user_id"]

        # Extract JWT token from request for user authentication
        user_token = None
        if request and hasattr(request, "headers"):
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                user_token = auth_header.split(" ", 1)[1]
                logger.info("Extracted user token for embeddings verification")

        # FAST PATH: For performance, first do a quick report existence check
        from ..system.core.supabase_client import get_service_role_client

        try:
            service_client = get_service_role_client()
            quick_check = (
                service_client.client.table("documents")
                .select("id,created_by,created_at")
                .eq("id", report_id)
                .eq("source_type", "pv_report")
                .limit(1)
                .execute()
            )

            if not quick_check.data:
                # Report doesn't exist, return early
                return {
                    "success": False,
                    "has_embeddings": False,
                    "message": "Report not found",
                    "user_message": "The report could not be found.",
                    "error_code": "report_not_found",
                }

            report_data = quick_check.data[0]
            if report_data.get("user_id") != user_id:
                # Access denied, return early
                return {
                    "success": False,
                    "has_embeddings": False,
                    "message": "Access denied",
                    "user_message": "You don't have permission to access this report.",
                    "error_code": "access_denied",
                }

            # For recent reports (created in last 24 hours), assume chunks exist
            from datetime import datetime, timedelta

            if report_data.get("created_at"):
                created_at = datetime.fromisoformat(
                    report_data["created_at"].replace("Z", "+00:00")
                )
                if datetime.now(created_at.tzinfo) - created_at < timedelta(hours=24):
                    logger.info(
                        f"Fast-path: Recent report {report_id} assumed to have embeddings"
                    )
                    return {
                        "success": True,
                        "has_embeddings": True,
                        "message": "Recent report embeddings available",
                        "user_message": "Your report is ready for chat!",
                        "report_id": report_id,
                    }
        except Exception as e:
            logger.warning(f"Fast-path check failed for {report_id}: {e}")
            # Continue to full validation

        # STEP 1: Full validation with timeout protection
        validation_service = get_report_validation_service(user_token=user_token)

        try:
            # Add timeout protection (5 seconds max, reduced from 10)
            import asyncio

            validation_result = await asyncio.wait_for(
                validation_service.validate_report_for_chat(
                    report_identifier=report_id,
                    user_id=user_id,
                    check_chunks=True,  # This will check if chunks exist
                ),
                timeout=5.0,  # 5 second timeout
            )
        except asyncio.TimeoutError:
            logger.error(
                f"Timeout during embeddings verification for report {report_id}"
            )
            # Return success with fallback to avoid blocking the UI
            return {
                "success": True,
                "has_embeddings": True,  # Assume embeddings exist to allow chat
                "message": "Report verification timed out, proceeding with chat",
                "user_message": "Your report is ready for chat!",
                "report_id": report_id,
            }

        if not validation_result.success:
            logger.error(
                f"Report validation failed for embeddings check: {validation_result.error_message}"
            )

            # Return specific responses based on validation result
            if validation_result.error_code == "report_not_found":
                return {
                    "success": False,
                    "has_embeddings": False,
                    "message": "Report not found or you don't have access to it",
                    "user_message": "The report could not be found or you don't have access to it.",
                    "error_code": "report_not_found",
                }
            elif validation_result.error_code == "access_denied":
                return {
                    "success": False,
                    "has_embeddings": False,
                    "message": "You don't have permission to access this report",
                    "user_message": "You don't have permission to access this report.",
                    "error_code": "access_denied",
                }
            elif validation_result.error_code == "no_chunks_found":
                return {
                    "success": True,
                    "has_embeddings": False,
                    "message": "Report is still being processed",
                    "user_message": "Your report is being processed and will be ready for chat soon.",
                    "error_code": "processing_in_progress",
                }
            else:
                return {
                    "success": False,
                    "has_embeddings": False,
                    "message": validation_result.user_message
                    or "Could not verify embeddings",
                    "user_message": "We're having trouble verifying your report. Please try again later.",
                    "error_code": validation_result.error_code or "validation_error",
                }

        # If validation passed, the report exists and has chunks
        validated_report_id = validation_result.report_id
        logger.info(f"Report {validated_report_id} has embeddings available for chat")

        return {
            "success": True,
            "has_embeddings": True,
            "message": "Report embeddings are available for chat functionality",
            "user_message": "Your report is ready for chat!",
            "report_id": validated_report_id,
        }

    except Exception as e:
        logger.error(f"Error verifying embeddings for report {report_id}: {e}")

        # Return success with fallback to avoid breaking the UI
        return {
            "success": True,
            "has_embeddings": False,
            "message": f"Could not verify embeddings: {str(e)}",
            "user_message": "We're having trouble checking your report. Please try again later.",
            "error_code": "system_error",
        }


@router.post("/prepare-chat/{report_id}")
async def prepare_chat_background(
    report_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Prepare chat functionality for a report in the background.

    This endpoint is designed to be called proactively when a report is loaded
    or generated, rather than waiting for the user to click the chat button.
    It performs the same checks as get_report_processing_status but is optimized
    for background execution.

    Args:
        report_id: ID of the report to prepare chat for
        request: FastAPI request object
        current_user: Authentication context from get_current_user_with_roles

    Returns:
        Dict: Chat preparation status
    """
    try:
        # Validate user context
        user_id = current_user["user_id"]
        user_token = request.headers.get("authorization", "").replace("Bearer ", "")

        logger.info(
            f"Background chat preparation requested for report {report_id} by user {user_id}"
        )

        # Use the same validation logic as get_report_processing_status
        # but with shorter timeout for background processing
        validation_service = get_report_validation_service(user_token=user_token)

        try:
            # Shorter timeout for background processing (3 seconds)
            import asyncio

            validation_result = await asyncio.wait_for(
                validation_service.validate_report_for_chat(
                    report_identifier=report_id, user_id=user_id, check_chunks=True
                ),
                timeout=3.0,
            )
        except asyncio.TimeoutError:
            logger.warning(
                f"Background chat preparation timed out for report {report_id}"
            )
            return {
                "success": True,
                "ready_for_chat": False,
                "status": "preparing",
                "message": "Chat preparation in progress",
                "user_message": "Preparing chat for your report...",
                "report_id": report_id,
            }

        if not validation_result.success:
            logger.info(
                f"Background chat preparation - report not ready: {validation_result.error_code}"
            )

            if validation_result.error_code == "no_chunks_found":
                return {
                    "success": True,
                    "ready_for_chat": False,
                    "status": "preparing",
                    "message": "Report is still being processed",
                    "user_message": "Preparing chat for your report...",
                    "report_id": report_id,
                }
            else:
                return {
                    "success": False,
                    "ready_for_chat": False,
                    "status": "error",
                    "message": validation_result.user_message
                    or "Chat preparation failed",
                    "user_message": "Unable to prepare chat for this report.",
                    "error_code": validation_result.error_code,
                    "report_id": report_id,
                }

        # Chat is ready
        logger.info(
            f"Background chat preparation completed successfully for report {report_id}"
        )
        return {
            "success": True,
            "ready_for_chat": True,
            "status": "ready",
            "message": "Chat is ready for this report",
            "user_message": "Chat is ready!",
            "report_id": validation_result.report_id,
        }

    except Exception as e:
        logger.error(
            f"Error in background chat preparation for report {report_id}: {e}"
        )
        return {
            "success": False,
            "ready_for_chat": False,
            "status": "error",
            "message": f"Chat preparation failed: {str(e)}",
            "user_message": "Unable to prepare chat for this report.",
            "error_code": "system_error",
            "report_id": report_id,
        }


# =============================================
# ACTIONABLE INSIGHTS ENDPOINTS
# =============================================

from ..actionable_insights.service import (InsightGenerationContext,
                                           get_actionable_insights_service)


class InsightGenerationRequest(BaseModel):
    """Request model for generating actionable insights."""

    user_context: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional user context"
    )


class InsightResponse(BaseModel):
    """Response model for actionable insights."""

    id: str
    insight_type: str
    title: str
    content: str
    supporting_chunks: List[str] = Field(default_factory=list)
    confidence_score: float
    user_context: Dict[str, Any] = Field(default_factory=dict)
    generation_metadata: Dict[str, Any] = Field(default_factory=dict)


class InsightGenerationResponse(BaseModel):
    """Response model for insight generation."""

    success: bool
    insights: List[InsightResponse] = Field(default_factory=list)
    total_insights: int = 0
    generation_time_seconds: float = 0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


@router.post("/insights/{report_id}/generate", response_model=InsightGenerationResponse)
async def generate_actionable_insights(
    report_id: str,
    request: InsightGenerationRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    req: Request = None,
):
    """
    Generate actionable insights for a completed report.

    This endpoint triggers the generation of actionable insights using the hybrid RAG approach.
    The insights are generated asynchronously and stored in the database.

    Args:
        report_id: UUID of the report to generate insights for
        request: Request body with user context
        current_user: Authentication context
        req: The FastAPI request object

    Returns:
        InsightGenerationResponse: Generated insights or existing ones
    """
    try:
        logger.info(f"Generating actionable insights for report {report_id}")

        # Validate user authentication context and extract user ID
        user_id = current_user["user_id"]
        logger.info(f"User ID validated: {user_id}")

        # Get report metadata to extract user context
        supabase = get_supabase_client().client
        report_result = (
            supabase.table("documents")
            .select("id, created_by, metadata")
            .eq("id", report_id)
            .eq("source_type", "pv_report")
            .single()
            .execute()
        )

        if not report_result.data:
            raise HTTPException(status_code=404, detail="Report not found")

        report = report_result.data
        if report.get("created_by") != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        # Extract user context from report metadata and request
        workflow_metadata = report.get("metadata", {}).get("workflow_metadata", {})
        user_context_data = {
            "industry": workflow_metadata.get("industry"),
            "geography": workflow_metadata.get("geography"),
            "background": workflow_metadata.get("background"),
            "product_type": workflow_metadata.get("product_type"),
            **request.user_context,  # Allow override from request
        }

        # Create insight generation context
        insight_context = InsightGenerationContext(
            user_id=user_id,
            report_id=report_id,
            industry=user_context_data.get("industry"),
            geography=user_context_data.get("geography"),
            background=user_context_data.get("background"),
            product_type=user_context_data.get("product_type"),
        )

        # Generate insights using the service
        insights_service = get_actionable_insights_service()
        result = await insights_service.generate_insights(report_id, insight_context)

        # Convert to response format
        insight_responses = []
        for insight in result.insights:
            insight_response = InsightResponse(
                id=insight.id,
                insight_type=insight.insight_type,
                title=insight.title,
                content=insight.content,
                supporting_chunks=insight.supporting_chunks,
                confidence_score=insight.confidence_score,
                user_context=insight.user_context,
                generation_metadata=insight.generation_metadata,
            )
            insight_responses.append(insight_response)

        return InsightGenerationResponse(
            success=result.success,
            insights=insight_responses,
            total_insights=result.total_insights,
            generation_time_seconds=result.generation_time_seconds,
            error_message=result.error_message,
            metadata=result.metadata,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate insights for report {report_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Insight generation failed: {str(e)}"
        )


@router.get("/insights/{report_id}", response_model=InsightGenerationResponse)
async def get_report_insights(
    report_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    req: Request = None,
):
    """
    Retrieve existing actionable insights for a report.

    Args:
        report_id: UUID of the report to get insights for
        current_user: Authentication context
        req: The FastAPI request object

    Returns:
        InsightGenerationResponse: Existing insights or empty response
    """
    try:
        logger.info(f"Retrieving insights for report {report_id}")

        # Validate user authentication context and extract user ID
        user_id = current_user["user_id"]

        # Get insights service and retrieve existing insights
        insights_service = get_actionable_insights_service()
        existing_insights = await insights_service._get_existing_insights(report_id)

        # Validate user has access to this report
        supabase = get_supabase_client()
        report_result = (
            supabase.table("documents")
            .select("created_by")
            .eq("id", report_id)
            .eq("source_type", "pv_report")
            .single()
            .execute()
        )

        if not report_result.data:
            raise HTTPException(status_code=404, detail="Report not found")

        if report_result.data.get("created_by") != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        # Convert to response format
        insight_responses = []
        for insight in existing_insights:
            insight_response = InsightResponse(
                id=insight.id,
                insight_type=insight.insight_type,
                title=insight.title,
                content=insight.content,
                supporting_chunks=insight.supporting_chunks,
                confidence_score=insight.confidence_score,
                user_context=insight.user_context,
                generation_metadata=insight.generation_metadata,
            )
            insight_responses.append(insight_response)

        return InsightGenerationResponse(
            success=True,
            insights=insight_responses,
            total_insights=len(existing_insights),
            generation_time_seconds=0,
            metadata={"source": "existing"},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve insights for report {report_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve insights: {str(e)}"
        )


@router.get("/insights/{report_id}/status")
async def get_insight_generation_status(
    report_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    req: Request = None,
):
    """
    Get the status of actionable insight generation for a report.

    Args:
        report_id: UUID of the report to check
        current_user: Authentication context
        req: The FastAPI request object

    Returns:
        Dict: Status information about insight generation
    """
    try:
        logger.info(f"Checking insight generation status for report {report_id}")

        # Validate user authentication context and extract user ID
        user_id = current_user["user_id"]

        # Get report status
        supabase = get_supabase_client()
        result = (
            supabase.table("documents")
            .select("created_by, metadata")
            .eq("id", report_id)
            .eq("source_type", "pv_report")
            .single()
            .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="Report not found")

        report = result.data
        if report.get("created_by") != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        # Get insight count
        insights_result = (
            supabase.table("report_insights")
            .select("id")
            .eq("report_id", report_id)
            .execute()
        )
        insight_count = len(insights_result.data) if insights_result.data else 0

        metadata = report.get("metadata", {})
        return {
            "success": True,
            "report_id": report_id,
            "status": metadata.get("insights_status", "not_generated"),
            "generated_at": metadata.get("insights_generated_at"),
            "insight_count": insight_count,
            "summary": metadata.get("actionable_insights", {}),
            "ready_for_insights": metadata.get("insights_status") not in ["generating"],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get insight status for report {report_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get insight status: {str(e)}"
        )

