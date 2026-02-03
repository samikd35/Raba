#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
WebSocket Implementation for Real-time Messaging.

This module provides WebSocket endpoints for real-time message delivery,
typing indicators, and online status.
"""

import json
import logging
from typing import Dict, Set
from datetime import datetime, timezone

from fastapi import WebSocket, WebSocketDisconnect, Depends, Query
from starlette.websockets import WebSocketState

from .service import get_messaging_service
from .models import MAX_MESSAGE_LENGTH

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time messaging."""

    def __init__(self):
        # Map of user_id -> Set of WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Map of user_id -> last activity timestamp
        self.user_activity: Dict[str, datetime] = {}
        # Rate limiting: Map of user_id -> list of message timestamps
        self.message_timestamps: Dict[str, list] = {}
        # Rate limit config
        self.rate_limit_messages = 30  # Max messages per window
        self.rate_limit_window = 60  # Window in seconds

    async def connect(self, websocket: WebSocket, user_id: str, already_accepted: bool = False):
        """
        Connect a user's WebSocket.

        Args:
            websocket: WebSocket connection
            user_id: User ID
            already_accepted: If True, skip calling accept() (already done)
        """
        if not already_accepted:
            await websocket.accept()

        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()

        self.active_connections[user_id].add(websocket)
        self.user_activity[user_id] = datetime.now(timezone.utc)

        logger.info(f"User {user_id} connected via WebSocket. Total connections: {len(self.active_connections[user_id])}")

    def disconnect(self, websocket: WebSocket, user_id: str):
        """
        Disconnect a user's WebSocket.

        Args:
            websocket: WebSocket connection
            user_id: User ID
        """
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)

            # Remove user from active connections if no more connections
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
                if user_id in self.user_activity:
                    del self.user_activity[user_id]

        logger.info(f"User {user_id} disconnected from WebSocket")

    async def send_personal_message(self, message: dict, user_id: str):
        """
        Send a message to a specific user across all their connections.

        Args:
            message: Message data to send
            user_id: Target user ID
        """
        if user_id not in self.active_connections:
            logger.debug(f"User {user_id} not connected, message not sent")
            return

        # Send to all connections for this user
        disconnected_sockets = []
        for connection in self.active_connections[user_id]:
            try:
                if connection.client_state == WebSocketState.CONNECTED:
                    await connection.send_json(message)
                else:
                    disconnected_sockets.append(connection)
            except Exception as e:
                logger.error(f"Error sending message to {user_id}: {e}")
                disconnected_sockets.append(connection)

        # Clean up disconnected sockets
        for socket in disconnected_sockets:
            self.disconnect(socket, user_id)

    async def broadcast_typing_indicator(self, sender_id: str, recipient_id: str, is_typing: bool):
        """
        Send typing indicator to recipient.

        Args:
            sender_id: User who is typing
            recipient_id: User who should see the indicator
            is_typing: Whether user is currently typing
        """
        message = {
            "type": "typing_indicator",
            "sender_id": sender_id,
            "is_typing": is_typing,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await self.send_personal_message(message, recipient_id)

    async def broadcast_message(self, message_data: dict, sender_id: str, recipient_id: str):
        """
        Broadcast a new message to the recipient in real-time.

        Args:
            message_data: Message data
            sender_id: Sender user ID
            recipient_id: Recipient user ID
        """
        notification = {
            "type": "new_message",
            "message": message_data,
            "sender_id": sender_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await self.send_personal_message(notification, recipient_id)

    async def broadcast_message_read(self, message_id: str, thread_id: str, reader_id: str, sender_id: str):
        """
        Notify sender that their message was read.

        Args:
            message_id: ID of message that was read
            thread_id: Thread ID
            reader_id: User who read the message
            sender_id: Original sender to notify
        """
        notification = {
            "type": "message_read",
            "message_id": message_id,
            "thread_id": thread_id,
            "reader_id": reader_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await self.send_personal_message(notification, sender_id)

    def is_user_online(self, user_id: str) -> bool:
        """
        Check if a user is currently online.

        Args:
            user_id: User ID to check

        Returns:
            True if user has active connections
        """
        return user_id in self.active_connections and len(self.active_connections[user_id]) > 0

    async def broadcast_online_status(self, user_id: str, is_online: bool, to_user_id: str):
        """
        Broadcast online/offline status to a specific user.

        Args:
            user_id: User whose status changed
            is_online: Online status
            to_user_id: User to notify
        """
        notification = {
            "type": "online_status",
            "user_id": user_id,
            "is_online": is_online,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await self.send_personal_message(notification, to_user_id)

    def check_rate_limit(self, user_id: str) -> bool:
        """
        Check if user has exceeded WebSocket message rate limit.

        Args:
            user_id: User ID to check

        Returns:
            True if within rate limit, False if exceeded
        """
        now = datetime.now(timezone.utc)

        # Initialize if not exists
        if user_id not in self.message_timestamps:
            self.message_timestamps[user_id] = []

        # Remove timestamps outside the window
        cutoff_time = now.timestamp() - self.rate_limit_window
        self.message_timestamps[user_id] = [
            ts for ts in self.message_timestamps[user_id]
            if ts > cutoff_time
        ]

        # Check if exceeded
        if len(self.message_timestamps[user_id]) >= self.rate_limit_messages:
            logger.warning(f"User {user_id} exceeded WebSocket rate limit")
            return False

        # Add current timestamp
        self.message_timestamps[user_id].append(now.timestamp())
        return True


# Global connection manager instance
manager = ConnectionManager()


async def handle_websocket_message(websocket: WebSocket, user_id: str, data: dict):
    """
    Handle incoming WebSocket messages.

    Args:
        websocket: WebSocket connection
        user_id: User ID
        data: Message data
    """
    message_type = data.get("type")

    try:
        # Check rate limit for message-sending operations
        if message_type in ["send_message", "typing_indicator"]:
            if not manager.check_rate_limit(user_id):
                await websocket.send_json({
                    "type": "error",
                    "error": "Rate limit exceeded. Please slow down.",
                    "code": "rate_limit_exceeded"
                })
                return

        if message_type == "send_message":
            # Send a message via WebSocket
            recipient_id = data.get("recipient_id")
            content = data.get("content")

            if not recipient_id or not content:
                await websocket.send_json({
                    "type": "error",
                    "error": "recipient_id and content are required"
                })
                return

            # Validate content length
            if len(content) > MAX_MESSAGE_LENGTH:
                await websocket.send_json({
                    "type": "error",
                    "error": f"Message content exceeds maximum length of {MAX_MESSAGE_LENGTH} characters",
                    "code": "content_too_long"
                })
                return

            # Send message using the messaging service
            messaging_service = get_messaging_service()

            try:
                message, thread = messaging_service.send_message(
                    sender_id=user_id,
                    recipient_id=recipient_id,
                    content=content
                )

                # Decrypt for WebSocket broadcast
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

                # Send confirmation to sender
                await websocket.send_json({
                    "type": "message_sent",
                    "message": message_data,
                    "success": True
                })

                # Broadcast to recipient
                await manager.broadcast_message(
                    message_data=message_data,
                    sender_id=user_id,
                    recipient_id=recipient_id
                )

            except ValueError as e:
                # Handle rate limits, blocks, etc.
                await websocket.send_json({
                    "type": "error",
                    "error": str(e),
                    "code": "send_failed"
                })

        elif message_type == "typing_indicator":
            # Broadcast typing indicator to recipient
            recipient_id = data.get("recipient_id")
            is_typing = data.get("is_typing", False)

            if recipient_id:
                await manager.broadcast_typing_indicator(user_id, recipient_id, is_typing)

        elif message_type == "message_read":
            # Mark message as read and notify sender
            message_id = data.get("message_id")
            thread_id = data.get("thread_id")
            sender_id = data.get("sender_id")

            if message_id and sender_id:
                # Use service layer to mark message as read
                messaging_service = get_messaging_service()

                try:
                    success = messaging_service.mark_message_as_read(message_id, user_id)

                    if success:
                        # Notify sender
                        await manager.broadcast_message_read(message_id, thread_id, user_id, sender_id)
                    else:
                        await websocket.send_json({
                            "type": "error",
                            "error": "Message not found",
                            "code": "message_not_found"
                        })
                except ValueError as e:
                    await websocket.send_json({
                        "type": "error",
                        "error": str(e),
                        "code": "unauthorized"
                    })

        elif message_type == "ping":
            # Heartbeat - update user activity
            manager.user_activity[user_id] = datetime.now(timezone.utc)
            await websocket.send_json({
                "type": "pong",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

        elif message_type == "get_online_status":
            # Check if specific users are online
            user_ids = data.get("user_ids", [])
            online_status = {
                uid: manager.is_user_online(uid)
                for uid in user_ids
            }
            await websocket.send_json({
                "type": "online_status_response",
                "statuses": online_status,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

        else:
            logger.warning(f"Unknown WebSocket message type: {message_type}")
            await websocket.send_json({
                "type": "error",
                "error": f"Unknown message type: {message_type}"
            })

    except Exception as e:
        logger.error(f"Error handling WebSocket message: {e}", exc_info=True)
        await websocket.send_json({
            "type": "error",
            "error": str(e)
        })


def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager instance."""
    return manager
