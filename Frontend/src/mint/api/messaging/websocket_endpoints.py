#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
WebSocket Endpoints for Real-time Messaging.
"""

import logging
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException

from .websocket import manager, handle_websocket_message
from ..auth_v2.utils import decode_token

logger = logging.getLogger(__name__)

# Create router
websocket_router = APIRouter(prefix="/api/messaging/ws", tags=["messaging-websocket"])


@websocket_router.websocket("/connect")
async def websocket_endpoint(
    websocket: WebSocket,
):
    """
    WebSocket endpoint for real-time messaging.

    Connect using: ws://your-domain/api/messaging/ws/connect

    Authentication:
    First message MUST be: {"type": "auth", "token": "YOUR_JWT_TOKEN"}
    Server will respond with: {"type": "connected", "user_id": "...", "message": "..."}

    Supported message types:

    Client -> Server:
    - auth: {"type": "auth", "token": "YOUR_JWT_TOKEN"} (REQUIRED FIRST MESSAGE)
    - send_message: {"type": "send_message", "recipient_id": "user_id", "content": "message text"}
    - typing_indicator: {"type": "typing_indicator", "recipient_id": "user_id", "is_typing": true}
    - message_read: {"type": "message_read", "message_id": "msg_id", "thread_id": "thread_id", "sender_id": "user_id"}
    - ping: {"type": "ping"}
    - get_online_status: {"type": "get_online_status", "user_ids": ["user1", "user2"]}

    Server -> Client:
    - connected: {"type": "connected", "user_id": "...", "message": "WebSocket connection established"}
    - message_sent: {"type": "message_sent", "message": {...}, "success": true} (confirmation to sender)
    - new_message: {"type": "new_message", "message": {...}, "sender_id": "user_id", "timestamp": "..."} (to recipient)
    - typing_indicator: {"type": "typing_indicator", "sender_id": "user_id", "is_typing": true, "timestamp": "..."}
    - message_read: {"type": "message_read", "message_id": "msg_id", "thread_id": "thread_id", "reader_id": "user_id", "timestamp": "..."}
    - online_status: {"type": "online_status", "user_id": "user_id", "is_online": true, "timestamp": "..."}
    - online_status_response: {"type": "online_status_response", "statuses": {"user1": true, "user2": false}, "timestamp": "..."}
    - pong: {"type": "pong", "timestamp": "..."}
    - error: {"type": "error", "error": "error message", "code": "error_code"}

    Args:
        websocket: WebSocket connection
    """
    user_id = None
    await websocket.accept()

    try:
        # Wait for authentication message (with timeout)
        import asyncio

        try:
            auth_data = await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
            auth_message = json.loads(auth_data)
        except asyncio.TimeoutError:
            await websocket.send_json({
                "type": "error",
                "error": "Authentication timeout. Send auth message within 10 seconds.",
                "code": "auth_timeout"
            })
            await websocket.close(code=1008, reason="Authentication timeout")
            return
        except json.JSONDecodeError:
            await websocket.send_json({
                "type": "error",
                "error": "Invalid JSON in authentication message",
                "code": "invalid_json"
            })
            await websocket.close(code=1008, reason="Invalid JSON")
            return

        # Verify it's an auth message
        if auth_message.get("type") != "auth":
            await websocket.send_json({
                "type": "error",
                "error": "First message must be auth message: {\"type\": \"auth\", \"token\": \"YOUR_TOKEN\"}",
                "code": "auth_required"
            })
            await websocket.close(code=1008, reason="Authentication required")
            return

        # Extract and validate token
        token = auth_message.get("token")
        if not token:
            await websocket.send_json({
                "type": "error",
                "error": "Token is required in auth message",
                "code": "token_missing"
            })
            await websocket.close(code=1008, reason="Token missing")
            return

        # Authenticate user using decode_token from auth_v2.utils
        payload = decode_token(token)
        user_id = payload.get("uid")

        # Connect user (already accepted connection above)
        await manager.connect(websocket, user_id, already_accepted=True)

        # Send connection success
        await websocket.send_json(
            {
                "type": "connected",
                "message": "WebSocket connection established",
                "user_id": user_id,
            }
        )

        # Main message loop
        while True:
            try:
                # Receive message
                data = await websocket.receive_text()
                message_data = json.loads(data)

                # Handle message
                await handle_websocket_message(websocket, user_id, message_data)

            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for user {user_id}")
                break
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON from user {user_id}: {e}")
                await websocket.send_json(
                    {"type": "error", "error": "Invalid JSON format"}
                )
            except Exception as e:
                logger.error(
                    f"Error in WebSocket loop for user {user_id}: {e}", exc_info=True
                )
                await websocket.send_json(
                    {"type": "error", "error": "Internal server error"}
                )

    except Exception as e:
        logger.error(f"WebSocket connection error: {e}", exc_info=True)
        try:
            if websocket.client_state.name == "CONNECTED":
                await websocket.send_json({
                    "type": "error",
                    "error": "Authentication failed",
                    "code": "auth_failed"
                })
                await websocket.close(code=1008, reason="Authentication failed")
        except:
            # Connection already closed, ignore
            pass
    finally:
        # Disconnect user
        if user_id:
            manager.disconnect(websocket, user_id)


@websocket_router.get("/online-status/{user_id}")
async def check_online_status(user_id: str):
    """
    Check if a user is currently online (has active WebSocket connection).

    Args:
        user_id: User ID to check

    Returns:
        Online status
    """
    is_online = manager.is_user_online(user_id)

    return {"user_id": user_id, "is_online": is_online}
