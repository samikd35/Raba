#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Messaging Models and Data Structures.

This module contains Pydantic models and data structures for user-to-user messaging functionality,
including messages, threads, blocks, and rate limiting.
"""

from enum import Enum
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field


class MessageStatus(str, Enum):
    """Status of a message."""
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


class ThreadStatus(str, Enum):
    """Status of a message thread."""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class UserRelationship(str, Enum):
    """Relationship status between users."""
    NONE = "none"
    MATCHED = "matched"  # Users matched profiles
    CONTACTED = "contacted"  # Has initiated contact


class Message(BaseModel):
    """Message model for user-to-user messaging."""
    id: str = Field(..., description="Unique message ID")
    thread_id: str = Field(..., description="Thread this message belongs to")
    sender_id: str = Field(..., description="User ID of sender")
    recipient_id: str = Field(..., description="User ID of recipient")
    content_encrypted: str = Field(..., description="Server-side encrypted message content")
    status: MessageStatus = Field(default=MessageStatus.SENT, description="Message status")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MessageThread(BaseModel):
    """Thread model for conversation between two users."""
    id: str = Field(..., description="Unique thread ID")
    user1_id: str = Field(..., description="First user ID (lexicographically smaller)")
    user2_id: str = Field(..., description="Second user ID (lexicographically larger)")
    status: ThreadStatus = Field(default=ThreadStatus.ACTIVE)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_message_at: Optional[datetime] = None
    last_message_preview: Optional[str] = None
    unread_count_user1: int = Field(default=0, description="Unread count for user1")
    unread_count_user2: int = Field(default=0, description="Unread count for user2")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BlockedUser(BaseModel):
    """Model for blocked/muted users."""
    id: str = Field(..., description="Unique block record ID")
    blocker_id: str = Field(..., description="User who blocked/muted")
    blocked_id: str = Field(..., description="User who was blocked/muted")
    is_muted: bool = Field(default=False, description="If true, muted (can receive but notifications off); if false, fully blocked")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ContactRateLimit(BaseModel):
    """Rate limit model for new contact initiation."""
    id: str = Field(..., description="Unique rate limit record ID")
    user_id: str = Field(..., description="User ID")
    contacted_user_id: str = Field(..., description="User ID that was contacted")
    contacted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = Field(..., description="When this rate limit expires (48 hours)")

    @staticmethod
    def create_expiry() -> datetime:
        """Create expiry timestamp 48 hours from now."""
        return datetime.now(timezone.utc) + timedelta(hours=48)


class UserRelationshipRecord(BaseModel):
    """Record of relationship between two users."""
    id: str = Field(..., description="Unique relationship record ID")
    user1_id: str = Field(..., description="First user ID (lexicographically smaller)")
    user2_id: str = Field(..., description="Second user ID (lexicographically larger)")
    relationship: UserRelationship = Field(default=UserRelationship.NONE)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)


# Request/Response Models

class SendMessageRequest(BaseModel):
    """Request model for sending a message."""
    recipient_id: str = Field(..., description="User ID of the recipient")
    content: str = Field(..., min_length=1, max_length=5000, description="Message content (will be encrypted)")

    class Config:
        json_schema_extra = {
            "example": {
                "recipient_id": "user-123",
                "content": "Hello! I saw your profile and would love to connect."
            }
        }


class SendMessageResponse(BaseModel):
    """Response model for sending a message."""
    success: bool = Field(..., description="Whether the message was sent successfully")
    message_id: Optional[str] = Field(None, description="ID of the sent message")
    thread_id: Optional[str] = Field(None, description="ID of the message thread")
    error: Optional[str] = Field(None, description="Error message if any")
    rate_limit_info: Optional[Dict[str, Any]] = Field(None, description="Rate limit information if applicable")


class GetThreadsResponse(BaseModel):
    """Response model for getting message threads."""
    threads: List[Dict[str, Any]] = Field(..., description="List of message threads")
    total: int = Field(..., description="Total number of threads")
    page: int = Field(default=1, description="Current page number")
    per_page: int = Field(default=20, description="Items per page")


class GetMessagesRequest(BaseModel):
    """Request model for getting messages in a thread."""
    thread_id: str = Field(..., description="Thread ID to get messages from")
    page: int = Field(default=1, ge=1, description="Page number")
    per_page: int = Field(default=50, ge=1, le=100, description="Messages per page")
    mark_as_read: bool = Field(default=True, description="Mark messages as read")


class GetMessagesResponse(BaseModel):
    """Response model for getting messages."""
    messages: List[Dict[str, Any]] = Field(..., description="List of messages (with decrypted content)")
    total: int = Field(..., description="Total number of messages in thread")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Messages per page")
    thread_info: Dict[str, Any] = Field(..., description="Thread information")


class BlockUserRequest(BaseModel):
    """Request model for blocking a user."""
    user_id: str = Field(..., description="User ID to block")
    mute_only: bool = Field(default=False, description="If true, mute instead of block")


class BlockUserResponse(BaseModel):
    """Response model for blocking a user."""
    success: bool = Field(..., description="Whether the block was successful")
    blocked_user_id: str = Field(..., description="ID of the blocked/muted user")
    is_muted: bool = Field(..., description="Whether user was muted (vs fully blocked)")
    message: str = Field(..., description="Success message")


class UnblockUserRequest(BaseModel):
    """Request model for unblocking a user."""
    user_id: str = Field(..., description="User ID to unblock")


class UnblockUserResponse(BaseModel):
    """Response model for unblocking a user."""
    success: bool = Field(..., description="Whether the unblock was successful")
    unblocked_user_id: str = Field(..., description="ID of the unblocked user")
    message: str = Field(..., description="Success message")


class RateLimitCheckResponse(BaseModel):
    """Response model for rate limit check."""
    can_contact: bool = Field(..., description="Whether user can contact the recipient")
    reason: Optional[str] = Field(None, description="Reason if cannot contact")
    rate_limit_expires_at: Optional[datetime] = Field(None, description="When rate limit expires")
    is_matched: bool = Field(default=False, description="Whether users have matched profiles")


# Constants

RATE_LIMIT_HOURS = 48
"""Time in hours before a user can contact another new user again."""

MAX_MESSAGE_LENGTH = 5000
"""Maximum length of a message in characters."""

MAX_THREADS_PER_PAGE = 100
"""Maximum number of threads that can be fetched per page."""

MAX_MESSAGES_PER_PAGE = 100
"""Maximum number of messages that can be fetched per page."""

ERROR_MESSAGES = {
    "user_blocked": "You cannot send messages to this user because you have been blocked.",
    "user_blocked_by_you": "You have blocked this user. Unblock them to send messages.",
    "rate_limit_exceeded": "You can only initiate conversations with 1 new user every 48 hours. You can message users you've matched with at any time.",
    "self_message": "You cannot send messages to yourself.",
    "user_not_found": "The recipient user was not found.",
    "thread_not_found": "The message thread was not found.",
    "unauthorized": "You are not authorized to access this thread.",
    "encryption_failed": "Failed to encrypt the message.",
    "decryption_failed": "Failed to decrypt the message.",
}
