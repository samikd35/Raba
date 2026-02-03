#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Messaging API Endpoints.

This module provides API endpoints for user-to-user messaging functionality.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from ..auth_v2.utils import get_current_user
from .models import (ERROR_MESSAGES, BlockUserRequest, BlockUserResponse,
                     GetMessagesRequest, GetMessagesResponse,
                     GetThreadsResponse, RateLimitCheckResponse,
                     SendMessageRequest, SendMessageResponse,
                     UnblockUserRequest, UnblockUserResponse)
from .service import get_messaging_service
from .websocket import get_connection_manager

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/messaging", tags=["messaging"])


@router.post("/send", response_model=SendMessageResponse)
async def send_message(
    request: SendMessageRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Send a message to another user.

    Rate limiting:
    - Users who have matched profiles: No limit
    - New contacts: 1 per 48 hours

    Args:
        request: Message send request
        current_user: Current authenticated user

    Returns:
        SendMessageResponse with message and thread details

    Raises:
        HTTPException: If validation fails or rate limit exceeded
    """
    sender_id = current_user["user_id"]

    try:
        messaging_service = get_messaging_service()

        # Send message
        message, thread = messaging_service.send_message(
            sender_id=sender_id,
            recipient_id=request.recipient_id,
            content=request.content,
        )

        logger.info(f"✉️ Message sent from {sender_id} to {request.recipient_id}")

        # Broadcast message via WebSocket for real-time delivery
        connection_manager = get_connection_manager()
        realtime_delivered = False
        try:
            # Decrypt message for WebSocket broadcast
            decrypted_content = messaging_service.encryption_service.decrypt(message["content_encrypted"])

            message_data = {
                "id": message["id"],
                "thread_id": message["thread_id"],
                "sender_id": message["sender_id"],
                "recipient_id": message["recipient_id"],
                "content": decrypted_content,
                "status": message["status"],
                "created_at": message["created_at"]
            }

            await connection_manager.broadcast_message(
                message_data=message_data,
                sender_id=sender_id,
                recipient_id=request.recipient_id
            )
            realtime_delivered = connection_manager.is_user_online(request.recipient_id)
        except Exception as ws_error:
            # WebSocket broadcast failure shouldn't fail the message send
            logger.warning(f"Failed to broadcast message via WebSocket: {ws_error}")

        return SendMessageResponse(
            success=True,
            message_id=message["id"],
            thread_id=thread["id"],
            error=None,
            rate_limit_info={"realtime_delivered": realtime_delivered}
        )

    except ValueError as e:
        error_message = str(e)
        logger.warning(f"Failed to send message from {sender_id}: {error_message}")

        # Check if it's a rate limit error
        if "48 hours" in error_message or "rate limit" in error_message.lower():
            raise HTTPException(
                status_code=429,
                detail={
                    "success": False,
                    "error": error_message,
                    "code": "rate_limit_exceeded",
                },
            )

        # Check if it's a blocking error
        if "blocked" in error_message.lower():
            raise HTTPException(
                status_code=403,
                detail={
                    "success": False,
                    "error": error_message,
                    "code": "user_blocked",
                },
            )

        # Generic error
        raise HTTPException(
            status_code=400, detail={"success": False, "error": error_message}
        )

    except Exception as e:
        logger.error(f"Unexpected error sending message: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": "An unexpected error occurred while sending the message",
            },
        )


@router.get("/threads", response_model=GetThreadsResponse)
async def get_threads(
    current_user: dict = Depends(get_current_user),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
):
    """
    Get all message threads for the current user.

    Args:
        current_user: Current authenticated user
        page: Page number (1-indexed)
        per_page: Items per page (max 100)

    Returns:
        GetThreadsResponse with threads and pagination info
    """
    user_id = current_user["user_id"]

    try:
        messaging_service = get_messaging_service()

        threads, total = messaging_service.get_threads(
            user_id=user_id, page=page, per_page=per_page
        )

        # Format threads for response
        formatted_threads = []
        for thread in threads:
            # Determine the other user in the thread
            other_user_id = (
                thread["user2_id"]
                if thread["user1_id"] == user_id
                else thread["user1_id"]
            )

            # Determine unread count for current user
            unread_count = (
                thread.get("unread_count_user1", 0)
                if thread["user1_id"] == user_id
                else thread.get("unread_count_user2", 0)
            )

            formatted_thread = {
                "id": thread["id"],
                "other_user_id": other_user_id,
                "last_message_preview": thread.get("last_message_preview"),
                "last_message_at": thread.get("last_message_at"),
                "unread_count": unread_count,
                "created_at": thread["created_at"],
                "updated_at": thread["updated_at"],
            }
            formatted_threads.append(formatted_thread)

        logger.info(f"Retrieved {len(threads)} threads for user {user_id}")

        return GetThreadsResponse(
            threads=formatted_threads, total=total, page=page, per_page=per_page
        )

    except Exception as e:
        logger.error(f"Error retrieving threads for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="An error occurred while retrieving message threads"
        )


@router.post("/messages", response_model=GetMessagesResponse)
async def get_messages(
    request: GetMessagesRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Get messages in a specific thread.

    By default, messages will be marked as read.

    Args:
        request: Get messages request
        current_user: Current authenticated user

    Returns:
        GetMessagesResponse with messages and thread info

    Raises:
        HTTPException: If thread not found or user unauthorized
    """
    user_id = current_user["user_id"]

    try:
        messaging_service = get_messaging_service()

        messages, total, thread = messaging_service.get_messages(
            user_id=user_id,
            thread_id=request.thread_id,
            page=request.page,
            per_page=request.per_page,
            mark_as_read=request.mark_as_read,
        )

        # Determine the other user in the thread
        other_user_id = (
            thread["user2_id"] if thread["user1_id"] == user_id else thread["user1_id"]
        )

        thread_info = {
            "id": thread["id"],
            "other_user_id": other_user_id,
            "created_at": thread["created_at"],
            "updated_at": thread["updated_at"],
        }

        logger.info(
            f"Retrieved {len(messages)} messages from thread {request.thread_id} for user {user_id}"
        )

        return GetMessagesResponse(
            messages=messages,
            total=total,
            page=request.page,
            per_page=request.per_page,
            thread_info=thread_info,
        )

    except ValueError as e:
        error_message = str(e)
        logger.warning(
            f"Failed to retrieve messages for user {user_id}: {error_message}"
        )

        if "not found" in error_message.lower():
            raise HTTPException(status_code=404, detail=error_message)

        if "unauthorized" in error_message.lower():
            raise HTTPException(status_code=403, detail=error_message)

        raise HTTPException(status_code=400, detail=error_message)

    except Exception as e:
        logger.error(
            f"Error retrieving messages for user {user_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=500, detail="An error occurred while retrieving messages"
        )


@router.post("/block", response_model=BlockUserResponse)
async def block_user(
    request: BlockUserRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Block or mute a user.

    - Block: User cannot send you messages
    - Mute: User can send messages, but notifications are disabled

    Args:
        request: Block user request
        current_user: Current authenticated user

    Returns:
        BlockUserResponse with success status
    """
    user_id = current_user["user_id"]

    try:
        messaging_service = get_messaging_service()

        block_record = messaging_service.block_user(
            user_id=user_id,
            blocked_user_id=request.user_id,
            mute_only=request.mute_only,
        )

        action = "muted" if request.mute_only else "blocked"
        logger.info(f"User {user_id} {action} user {request.user_id}")

        return BlockUserResponse(
            success=True,
            blocked_user_id=request.user_id,
            is_muted=request.mute_only,
            message=f"User successfully {action}",
        )

    except ValueError as e:
        error_message = str(e)
        logger.warning(f"Failed to block user for {user_id}: {error_message}")
        raise HTTPException(status_code=400, detail=error_message)

    except Exception as e:
        logger.error(f"Error blocking user for {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="An error occurred while blocking the user"
        )


@router.post("/unblock", response_model=UnblockUserResponse)
async def unblock_user(
    request: UnblockUserRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Unblock a user.

    Args:
        request: Unblock user request
        current_user: Current authenticated user

    Returns:
        UnblockUserResponse with success status
    """
    user_id = current_user["user_id"]

    try:
        messaging_service = get_messaging_service()

        messaging_service.unblock_user(user_id=user_id, blocked_user_id=request.user_id)

        logger.info(f"User {user_id} unblocked user {request.user_id}")

        return UnblockUserResponse(
            success=True,
            unblocked_user_id=request.user_id,
            message="User successfully unblocked",
        )

    except Exception as e:
        logger.error(f"Error unblocking user for {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="An error occurred while unblocking the user"
        )


@router.get("/can-contact/{recipient_id}", response_model=RateLimitCheckResponse)
async def check_can_contact(
    recipient_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Check if current user can contact a recipient.

    This endpoint is useful for UI to show whether a user can initiate
    a conversation before they try to send a message.

    Args:
        recipient_id: ID of the user to check
        current_user: Current authenticated user

    Returns:
        RateLimitCheckResponse with contact eligibility info
    """
    user_id = current_user["user_id"]

    try:
        messaging_service = get_messaging_service()

        # Check if users have matched
        is_matched = messaging_service._check_if_matched(user_id, recipient_id)

        # Check rate limit
        can_contact, reason, expires_at = messaging_service._check_rate_limit(
            user_id, recipient_id
        )

        # Check if blocked
        is_blocked_by_recipient, has_blocked_recipient = (
            messaging_service._check_if_blocked(user_id, recipient_id)
        )

        if is_blocked_by_recipient:
            can_contact = False
            reason = ERROR_MESSAGES["user_blocked"]
        elif has_blocked_recipient:
            can_contact = False
            reason = ERROR_MESSAGES["user_blocked_by_you"]

        logger.debug(f"Contact check: {user_id} -> {recipient_id}: {can_contact}")

        return RateLimitCheckResponse(
            can_contact=can_contact,
            reason=reason,
            rate_limit_expires_at=expires_at,
            is_matched=is_matched,
        )

    except Exception as e:
        logger.error(f"Error checking contact eligibility: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An error occurred while checking contact eligibility",
        )


@router.get("/blocked-users")
async def get_blocked_users(
    current_user: dict = Depends(get_current_user),
):
    """
    Get list of users blocked/muted by current user.

    Args:
        current_user: Current authenticated user

    Returns:
        List of blocked/muted users
    """
    user_id = current_user["user_id"]

    try:
        messaging_service = get_messaging_service()

        result = (
            messaging_service.supabase.table("blocked_users")
            .select("*")
            .eq("blocker_id", user_id)
            .execute()
        )

        blocked_users = result.data or []

        logger.info(f"Retrieved {len(blocked_users)} blocked users for {user_id}")

        return {"blocked_users": blocked_users, "total": len(blocked_users)}

    except Exception as e:
        logger.error(f"Error retrieving blocked users: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="An error occurred while retrieving blocked users"
        )
