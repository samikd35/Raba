#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Messaging Service.

This module provides business logic for user-to-user messaging functionality,
including encryption, rate limiting, thread management, and blocking/muting.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Tuple
import base64
import hashlib
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from fastapi import HTTPException

from ..system.core.supabase_client import get_supabase_client
from .models import (
    Message, MessageThread, BlockedUser, ContactRateLimit,
    UserRelationshipRecord, UserRelationship, MessageStatus,
    ThreadStatus, RATE_LIMIT_HOURS, ERROR_MESSAGES
)

logger = logging.getLogger(__name__)


class EncryptionService:
    """Server-side encryption service for messages."""

    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize encryption service.

        Args:
            encryption_key: Base64-encoded encryption key. If not provided,
                          will try to get from environment variable MESSAGING_ENCRYPTION_KEY

        Raises:
            RuntimeError: If encryption key is not provided
        """
        if encryption_key is None:
            encryption_key = os.getenv("MESSAGING_ENCRYPTION_KEY")
            if not encryption_key:
                raise RuntimeError(
                    "MESSAGING_ENCRYPTION_KEY environment variable is required. "
                    "Generate a key using: python -c 'import base64, os; print(base64.b64encode(os.urandom(32)).decode())' "
                    "Then add it to your .env file: MESSAGING_ENCRYPTION_KEY=<generated_key>"
                )

        try:
            self.key = base64.b64decode(encryption_key)
            if len(self.key) != 32:
                raise ValueError(f"Key must be 32 bytes (256 bits), got {len(self.key)} bytes")
        except Exception as e:
            raise ValueError(
                f"Invalid MESSAGING_ENCRYPTION_KEY format: {e}. "
                "Expected base64-encoded 32-byte key. Generate using: "
                "python -c 'import base64, os; print(base64.b64encode(os.urandom(32)).decode())'"
            )

        self.aesgcm = AESGCM(self.key)
        logger.info("✅ Encryption service initialized successfully")

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a message using AES-GCM.

        Args:
            plaintext: The message to encrypt

        Returns:
            Base64-encoded encrypted data with nonce prepended
        """
        try:
            nonce = os.urandom(12)  # 96-bit nonce for GCM
            plaintext_bytes = plaintext.encode('utf-8')
            ciphertext = self.aesgcm.encrypt(nonce, plaintext_bytes, None)

            # Prepend nonce to ciphertext and base64 encode
            encrypted_data = nonce + ciphertext
            return base64.b64encode(encrypted_data).decode('utf-8')
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise ValueError("Encryption failed")

    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt a message using AES-GCM.

        Args:
            encrypted_data: Base64-encoded encrypted data with nonce prepended

        Returns:
            Decrypted plaintext message
        """
        try:
            encrypted_bytes = base64.b64decode(encrypted_data)

            # Extract nonce and ciphertext
            nonce = encrypted_bytes[:12]
            ciphertext = encrypted_bytes[12:]

            plaintext_bytes = self.aesgcm.decrypt(nonce, ciphertext, None)
            return plaintext_bytes.decode('utf-8')
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError("Decryption failed")


class MessagingService:
    """Service for user-to-user messaging functionality."""

    def __init__(self, use_service_role: bool = True):
        """
        Initialize messaging service.

        Args:
            use_service_role: Whether to use service role for database access
        """
        self.supabase = get_supabase_client(use_service_role=use_service_role).client
        self.encryption_service = EncryptionService()

    # ==================== Thread Management ====================

    def _get_or_create_thread(self, user1_id: str, user2_id: str) -> Dict[str, Any]:
        """
        Get or create a message thread between two users.

        Args:
            user1_id: First user ID
            user2_id: Second user ID

        Returns:
            Thread data
        """
        # Ensure users are in lexicographical order
        sorted_ids = sorted([user1_id, user2_id])

        # Try to get existing thread
        result = (
            self.supabase.table("message_threads")
            .select("*")
            .eq("user1_id", sorted_ids[0])
            .eq("user2_id", sorted_ids[1])
            .limit(1)
            .execute()
        )

        if result.data:
            return result.data[0]

        # Create new thread
        now = datetime.now(timezone.utc).isoformat()
        thread_data = {
            "user1_id": sorted_ids[0],
            "user2_id": sorted_ids[1],
            "status": ThreadStatus.ACTIVE.value,
            "created_at": now,
            "updated_at": now,
            "unread_count_user1": 0,
            "unread_count_user2": 0,
            "metadata": {}
        }

        result = self.supabase.table("message_threads").insert(thread_data).execute()
        return result.data[0] if result.data else thread_data

    def _update_thread_last_message(
        self, thread_id: str, message_preview: str, sender_id: str
    ) -> None:
        """
        Update thread with last message info and increment unread count.

        Args:
            thread_id: Thread ID
            message_preview: Preview of the last message
            sender_id: ID of the message sender
        """
        now = datetime.now(timezone.utc).isoformat()

        # Get thread to determine which user's unread count to increment
        thread = (
            self.supabase.table("message_threads")
            .select("*")
            .eq("id", thread_id)
            .limit(1)
            .execute()
        )

        if not thread.data:
            return

        thread_data = thread.data[0]

        # Increment unread count for the recipient
        if sender_id == thread_data["user1_id"]:
            # Sender is user1, increment user2's unread count
            new_unread_count = thread_data.get("unread_count_user2", 0) + 1
            update_data = {
                "updated_at": now,
                "last_message_at": now,
                "last_message_preview": message_preview[:100],
                "unread_count_user2": new_unread_count
            }
        else:
            # Sender is user2, increment user1's unread count
            new_unread_count = thread_data.get("unread_count_user1", 0) + 1
            update_data = {
                "updated_at": now,
                "last_message_at": now,
                "last_message_preview": message_preview[:100],
                "unread_count_user1": new_unread_count
            }

        self.supabase.table("message_threads").update(update_data).eq("id", thread_id).execute()

    # ==================== Rate Limiting ====================

    def _check_rate_limit(self, user_id: str, recipient_id: str) -> Tuple[bool, Optional[str], Optional[datetime]]:
        """
        Check if user can contact recipient based on rate limiting rules.

        Returns:
            Tuple of (can_contact, reason, expires_at)
        """
        # Check if users have matched profiles
        is_matched = self._check_if_matched(user_id, recipient_id)

        if is_matched:
            # No rate limit for matched users
            return True, None, None

        # Check if user has already contacted this recipient
        existing_contact = self._check_existing_contact(user_id, recipient_id)

        if existing_contact:
            # Already contacted, no rate limit
            return True, None, None

        # Check if user has contacted another new user in the last 48 hours
        now = datetime.now(timezone.utc)
        rate_limit_result = (
            self.supabase.table("contact_rate_limits")
            .select("*")
            .eq("user_id", user_id)
            .gte("expires_at", now.isoformat())
            .execute()
        )

        if rate_limit_result.data:
            # User has active rate limit
            expires_at = datetime.fromisoformat(rate_limit_result.data[0]["expires_at"].replace('Z', '+00:00'))
            return False, ERROR_MESSAGES["rate_limit_exceeded"], expires_at

        return True, None, None

    def _check_if_matched(self, user1_id: str, user2_id: str) -> bool:
        """
        Check if two users have matched profiles.

        Args:
            user1_id: First user ID
            user2_id: Second user ID

        Returns:
            True if users have matched, False otherwise
        """
        sorted_ids = sorted([user1_id, user2_id])

        result = (
            self.supabase.table("user_relationships")
            .select("relationship")
            .eq("user1_id", sorted_ids[0])
            .eq("user2_id", sorted_ids[1])
            .limit(1)
            .execute()
        )

        if result.data:
            return result.data[0]["relationship"] == UserRelationship.MATCHED.value

        return False

    def _check_existing_contact(self, user_id: str, recipient_id: str) -> bool:
        """
        Check if user has already contacted recipient.

        Args:
            user_id: User ID
            recipient_id: Recipient ID

        Returns:
            True if contact exists, False otherwise
        """
        sorted_ids = sorted([user_id, recipient_id])

        result = (
            self.supabase.table("user_relationships")
            .select("relationship")
            .eq("user1_id", sorted_ids[0])
            .eq("user2_id", sorted_ids[1])
            .limit(1)
            .execute()
        )

        if result.data:
            relationship = result.data[0]["relationship"]
            return relationship in [UserRelationship.CONTACTED.value, UserRelationship.MATCHED.value]

        return False

    def check_can_message_bulk(self, user_id: str, recipient_ids: List[str]) -> Dict[str, bool]:
        """
        Check if user can message multiple recipients efficiently.

        Args:
            user_id: The sender's user ID
            recipient_ids: List of recipient user IDs to check

        Returns:
            Dictionary mapping recipient_id -> can_message (bool)
        """
        if not recipient_ids:
            return {}

        result = {}

        # Fetch all relationships for this user with the recipients in one query
        # We need to check both directions since relationships are stored with sorted IDs
        # Note: Removed .or_() as Supabase Python client doesn't support it
        # Query user1_id first, then user2_id separately and combine
        relationships_result_1 = (
            self.supabase.table("user_relationships")
            .select("user1_id, user2_id, relationship")
            .eq("user1_id", user_id)
            .execute()
        )
        relationships_result_2 = (
            self.supabase.table("user_relationships")
            .select("user1_id, user2_id, relationship")
            .eq("user2_id", user_id)
            .execute()
        )
        # Combine results
        relationships_data = (relationships_result_1.data or []) + (relationships_result_2.data or [])

        # Build a map of recipient -> relationship status
        relationships_map = {}
        for row in relationships_data:
            other_user = row["user2_id"] if row["user1_id"] == user_id else row["user1_id"]
            if other_user in recipient_ids:
                relationships_map[other_user] = row["relationship"]

        # Check rate limit once for this user
        now = datetime.now(timezone.utc)
        rate_limit_result = (
            self.supabase.table("contact_rate_limits")
            .select("*")
            .eq("user_id", user_id)
            .gte("expires_at", now.isoformat())
            .execute()
        )

        has_active_rate_limit = bool(rate_limit_result.data)

        # Determine can_message for each recipient
        for recipient_id in recipient_ids:
            relationship = relationships_map.get(recipient_id)

            # If matched or already contacted, can always message
            if relationship in [UserRelationship.MATCHED.value, UserRelationship.CONTACTED.value]:
                result[recipient_id] = True
            # If has active rate limit and no existing relationship, cannot message
            elif has_active_rate_limit:
                result[recipient_id] = False
            # Otherwise, can message (will create rate limit on first contact)
            else:
                result[recipient_id] = True

        return result

    def _create_contact_record(self, user_id: str, recipient_id: str) -> None:
        """
        Create contact rate limit record and update user relationship.

        Args:
            user_id: User ID who initiated contact
            recipient_id: Recipient user ID
        """
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=RATE_LIMIT_HOURS)

        # Create rate limit record
        rate_limit_data = {
            "user_id": user_id,
            "contacted_user_id": recipient_id,
            "contacted_at": now.isoformat(),
            "expires_at": expires_at.isoformat()
        }

        self.supabase.table("contact_rate_limits").insert(rate_limit_data).execute()

        # Update or create user relationship
        sorted_ids = sorted([user_id, recipient_id])

        # Check if relationship exists
        existing = (
            self.supabase.table("user_relationships")
            .select("*")
            .eq("user1_id", sorted_ids[0])
            .eq("user2_id", sorted_ids[1])
            .limit(1)
            .execute()
        )

        if existing.data:
            # Update existing relationship
            if existing.data[0]["relationship"] == UserRelationship.NONE.value:
                self.supabase.table("user_relationships").update({
                    "relationship": UserRelationship.CONTACTED.value,
                    "updated_at": now.isoformat()
                }).eq("user1_id", sorted_ids[0]).eq("user2_id", sorted_ids[1]).execute()
        else:
            # Create new relationship
            relationship_data = {
                "user1_id": sorted_ids[0],
                "user2_id": sorted_ids[1],
                "relationship": UserRelationship.CONTACTED.value,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
                "metadata": {}
            }
            self.supabase.table("user_relationships").insert(relationship_data).execute()

    # ==================== Blocking/Muting ====================

    def _check_if_blocked(self, user_id: str, other_user_id: str) -> Tuple[bool, bool]:
        """
        Check if either user has blocked the other.

        Returns:
            Tuple of (is_blocked_by_other, has_blocked_other)
        """
        # Check if other user blocked this user
        blocked_by_other = (
            self.supabase.table("blocked_users")
            .select("is_muted")
            .eq("blocker_id", other_user_id)
            .eq("blocked_id", user_id)
            .eq("is_muted", False)  # Only full blocks prevent messaging
            .limit(1)
            .execute()
        )

        # Check if this user blocked other user
        has_blocked_other = (
            self.supabase.table("blocked_users")
            .select("is_muted")
            .eq("blocker_id", user_id)
            .eq("blocked_id", other_user_id)
            .limit(1)
            .execute()
        )

        return bool(blocked_by_other.data), bool(has_blocked_other.data)

    def block_user(self, user_id: str, blocked_user_id: str, mute_only: bool = False) -> Dict[str, Any]:
        """
        Block or mute a user.

        Args:
            user_id: User ID doing the blocking
            blocked_user_id: User ID to block
            mute_only: If True, mute instead of block

        Returns:
            Block record data
        """
        if user_id == blocked_user_id:
            raise ValueError(ERROR_MESSAGES["self_message"])

        # Check if already blocked
        existing = (
            self.supabase.table("blocked_users")
            .select("*")
            .eq("blocker_id", user_id)
            .eq("blocked_id", blocked_user_id)
            .limit(1)
            .execute()
        )

        now = datetime.now(timezone.utc).isoformat()

        if existing.data:
            # Update existing block
            result = (
                self.supabase.table("blocked_users")
                .update({"is_muted": mute_only})
                .eq("blocker_id", user_id)
                .eq("blocked_id", blocked_user_id)
                .execute()
            )
            return result.data[0] if result.data else existing.data[0]
        else:
            # Create new block
            block_data = {
                "blocker_id": user_id,
                "blocked_id": blocked_user_id,
                "is_muted": mute_only,
                "created_at": now,
                "metadata": {}
            }
            result = self.supabase.table("blocked_users").insert(block_data).execute()
            return result.data[0] if result.data else block_data

    def unblock_user(self, user_id: str, blocked_user_id: str) -> bool:
        """
        Unblock a user.

        Args:
            user_id: User ID doing the unblocking
            blocked_user_id: User ID to unblock

        Returns:
            True if successful
        """
        result = (
            self.supabase.table("blocked_users")
            .delete()
            .eq("blocker_id", user_id)
            .eq("blocked_id", blocked_user_id)
            .execute()
        )

        return True

    # ==================== Messaging ====================

    def send_message(
        self, sender_id: str, recipient_id: str, content: str
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Send a message from sender to recipient.

        Args:
            sender_id: Sender user ID
            recipient_id: Recipient user ID
            content: Message content (will be encrypted)

        Returns:
            Tuple of (message_data, thread_data)

        Raises:
            ValueError: If validation fails
        """
        # Validation
        if sender_id == recipient_id:
            raise ValueError(ERROR_MESSAGES["self_message"])

        # Check if blocked
        is_blocked_by_recipient, has_blocked_recipient = self._check_if_blocked(sender_id, recipient_id)

        if is_blocked_by_recipient:
            raise ValueError(ERROR_MESSAGES["user_blocked"])

        if has_blocked_recipient:
            raise ValueError(ERROR_MESSAGES["user_blocked_by_you"])

        # Check rate limit
        can_contact, reason, expires_at = self._check_rate_limit(sender_id, recipient_id)

        if not can_contact:
            error_data = {
                "reason": reason,
                "expires_at": expires_at.isoformat() if expires_at else None
            }
            raise ValueError(reason or ERROR_MESSAGES["rate_limit_exceeded"])

        # Get or create thread
        thread = self._get_or_create_thread(sender_id, recipient_id)

        # Encrypt message
        try:
            encrypted_content = self.encryption_service.encrypt(content)
        except Exception as e:
            logger.error(f"Failed to encrypt message: {e}")
            raise ValueError(ERROR_MESSAGES["encryption_failed"])

        # Create message
        now = datetime.now(timezone.utc).isoformat()
        message_data = {
            "thread_id": thread["id"],
            "sender_id": sender_id,
            "recipient_id": recipient_id,
            "content_encrypted": encrypted_content,
            "status": MessageStatus.SENT.value,
            "created_at": now,
            "metadata": {}
        }

        result = self.supabase.table("messages").insert(message_data).execute()
        saved_message = result.data[0] if result.data else message_data

        # Update thread
        self._update_thread_last_message(thread["id"], content, sender_id)

        # Create contact record if this is a new contact
        if not self._check_existing_contact(sender_id, recipient_id):
            self._create_contact_record(sender_id, recipient_id)

        return saved_message, thread

    def get_threads(
        self, user_id: str, page: int = 1, per_page: int = 20
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get message threads for a user.

        Args:
            user_id: User ID
            page: Page number (1-indexed)
            per_page: Items per page

        Returns:
            Tuple of (threads, total_count)
        """
        offset = (page - 1) * per_page

        # Get threads where user is participant
        # Note: Removed .or_() as Supabase Python client doesn't support it
        # Query user1_id first, then user2_id separately and combine
        result_1 = (
            self.supabase.table("message_threads")
            .select("*", count="exact")
            .eq("user1_id", user_id)
            .eq("status", ThreadStatus.ACTIVE.value)
            .order("last_message_at", desc=True)
            .execute()
        )
        result_2 = (
            self.supabase.table("message_threads")
            .select("*", count="exact")
            .eq("user2_id", user_id)
            .eq("status", ThreadStatus.ACTIVE.value)
            .order("last_message_at", desc=True)
            .execute()
        )
        
        # Combine and deduplicate results by thread id
        all_threads = {}
        for thread in (result_1.data or []) + (result_2.data or []):
            all_threads[thread["id"]] = thread
        
        # Sort by last_message_at descending
        threads_sorted = sorted(all_threads.values(), key=lambda x: x.get("last_message_at", ""), reverse=True)
        
        # Apply pagination manually
        total_count = len(threads_sorted)
        threads = threads_sorted[offset:offset + per_page]

        return threads, total_count

    def get_messages(
        self, user_id: str, thread_id: str, page: int = 1, per_page: int = 50, mark_as_read: bool = True
    ) -> Tuple[List[Dict[str, Any]], int, Dict[str, Any]]:
        """
        Get messages in a thread.

        Args:
            user_id: User ID requesting messages
            thread_id: Thread ID
            page: Page number (1-indexed)
            per_page: Messages per page
            mark_as_read: Whether to mark messages as read

        Returns:
            Tuple of (messages with decrypted content, total_count, thread_info)

        Raises:
            ValueError: If user is not part of the thread
        """
        # Verify user is part of thread
        thread_result = (
            self.supabase.table("message_threads")
            .select("*")
            .eq("id", thread_id)
            .limit(1)
            .execute()
        )

        if not thread_result.data:
            raise ValueError(ERROR_MESSAGES["thread_not_found"])

        thread = thread_result.data[0]

        if user_id not in [thread["user1_id"], thread["user2_id"]]:
            raise ValueError(ERROR_MESSAGES["unauthorized"])

        # Get messages
        offset = (page - 1) * per_page

        result = (
            self.supabase.table("messages")
            .select("*", count="exact")
            .eq("thread_id", thread_id)
            .order("created_at", desc=True)
            .range(offset, offset + per_page - 1)
            .execute()
        )

        messages = result.data or []
        total_count = result.count or 0

        # Decrypt messages
        decrypted_messages = []
        for message in messages:
            try:
                decrypted_content = self.encryption_service.decrypt(message["content_encrypted"])
                message_copy = message.copy()
                message_copy["content"] = decrypted_content
                del message_copy["content_encrypted"]  # Remove encrypted version from response
                decrypted_messages.append(message_copy)
            except Exception as e:
                logger.error(f"Failed to decrypt message {message['id']}: {e}")
                message_copy = message.copy()
                message_copy["content"] = "[Failed to decrypt message]"
                del message_copy["content_encrypted"]
                decrypted_messages.append(message_copy)

        # Mark messages as read if requested
        if mark_as_read and messages:
            now = datetime.now(timezone.utc).isoformat()
            message_ids = [m["id"] for m in messages if m["recipient_id"] == user_id and not m.get("read_at")]

            if message_ids:
                # Mark messages as read
                self.supabase.table("messages").update({
                    "status": MessageStatus.READ.value,
                    "read_at": now
                }).in_("id", message_ids).execute()

                # Decrement unread count by the number of messages marked as read (atomic operation)
                num_marked = len(message_ids)

                # Use PostgreSQL's decrement operation to avoid race conditions
                # Note: Supabase doesn't support direct increment/decrement, so we fetch and update
                # but at least we only decrement by the actual number marked, not reset to 0
                thread_refresh = (
                    self.supabase.table("message_threads")
                    .select("unread_count_user1, unread_count_user2")
                    .eq("id", thread_id)
                    .limit(1)
                    .execute()
                )

                if thread_refresh.data:
                    current_thread = thread_refresh.data[0]
                    if user_id == thread["user1_id"]:
                        current_count = current_thread.get("unread_count_user1", 0)
                        new_count = max(0, current_count - num_marked)
                        self.supabase.table("message_threads").update({
                            "unread_count_user1": new_count
                        }).eq("id", thread_id).execute()
                    else:
                        current_count = current_thread.get("unread_count_user2", 0)
                        new_count = max(0, current_count - num_marked)
                        self.supabase.table("message_threads").update({
                            "unread_count_user2": new_count
                        }).eq("id", thread_id).execute()

        return decrypted_messages, total_count, thread

    def mark_message_as_read(self, message_id: str, reader_id: str) -> bool:
        """
        Mark a specific message as read.

        Args:
            message_id: ID of the message to mark as read
            reader_id: User ID who is reading the message

        Returns:
            True if successful, False if message not found or reader is not recipient

        Raises:
            ValueError: If reader is not the recipient of the message
        """
        # Get the message to verify reader is the recipient
        message_result = (
            self.supabase.table("messages")
            .select("*")
            .eq("id", message_id)
            .limit(1)
            .execute()
        )

        if not message_result.data:
            logger.warning(f"Message {message_id} not found")
            return False

        message = message_result.data[0]

        # Verify reader is the recipient
        if message["recipient_id"] != reader_id:
            raise ValueError("You can only mark messages sent to you as read")

        # Skip if already read
        if message.get("read_at"):
            return True

        # Mark as read
        now = datetime.now(timezone.utc).isoformat()
        self.supabase.table("messages").update({
            "status": MessageStatus.READ.value,
            "read_at": now
        }).eq("id", message_id).execute()

        # Decrement unread count for the thread
        thread_id = message["thread_id"]
        thread_result = (
            self.supabase.table("message_threads")
            .select("*")
            .eq("id", thread_id)
            .limit(1)
            .execute()
        )

        if thread_result.data:
            thread = thread_result.data[0]
            # Determine which user's count to decrement
            if reader_id == thread["user1_id"]:
                current_count = thread.get("unread_count_user1", 0)
                if current_count > 0:
                    self.supabase.table("message_threads").update({
                        "unread_count_user1": current_count - 1
                    }).eq("id", thread_id).execute()
            elif reader_id == thread["user2_id"]:
                current_count = thread.get("unread_count_user2", 0)
                if current_count > 0:
                    self.supabase.table("message_threads").update({
                        "unread_count_user2": current_count - 1
                    }).eq("id", thread_id).execute()

        logger.info(f"Message {message_id} marked as read by {reader_id}")
        return True


def get_messaging_service(use_service_role: bool = True) -> MessagingService:
    """
    Get messaging service instance.

    Args:
        use_service_role: Whether to use service role for database access

    Returns:
        MessagingService instance
    """
    return MessagingService(use_service_role=use_service_role)
