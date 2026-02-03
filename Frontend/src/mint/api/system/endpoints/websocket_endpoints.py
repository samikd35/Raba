"""
WebSocket endpoints for real-time notifications and updates.
"""
import logging
import os
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
import json

router = APIRouter()
from ...auth.production.system import get_current_user, get_auth_context, get_production_auth_system
from ...services.communication.notification_service import notification_manager
from ..core.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

@router.websocket("/ws/notifications")
async def notifications_websocket(websocket: WebSocket):
    """WebSocket endpoint for user notifications."""
    await websocket.accept()
    
    user_id = None  # Initialize user_id to avoid UnboundLocalError
    is_admin = False
    
    try:
        # First message should be authentication token
        auth_message = await websocket.receive_text()
        auth_data = json.loads(auth_message)
        
        if "token" not in auth_data:
            await websocket.send_text(json.dumps({"error": "Authentication required"}))
            await websocket.close(code=1008)  # Policy violation
            return
            
        # Verify token and get user
        try:
            # Use ProductionAuthSystem to verify token
            auth_system = get_production_auth_system()
            token_payload = await auth_system._verify_jwt_secure(auth_data["token"])
            user_id = token_payload.get("sub")
            
            if not user_id:
                raise Exception("Invalid token payload")
            
            # Get user roles from database
            supabase = get_supabase_client()
            profile_response = supabase.table("user_profiles").select("roles").eq("id", user_id).execute()
            
            roles = []
            if profile_response.data and len(profile_response.data) > 0:
                roles = profile_response.data[0].get("roles", [])
            
            is_admin = any(role in ["super_admin", "support_admin", "business_analyst"] for role in roles)
            
            # Register connection with notification manager
            await notification_manager.register_connection(websocket, user_id, is_admin)
            
            # Send confirmation
            await websocket.send_text(json.dumps({"status": "connected", "user_id": user_id, "is_admin": is_admin}))
            
            # Keep connection alive and handle incoming messages
            while True:
                message = await websocket.receive_text()
                data = json.loads(message)
                
                # Handle message types
                if data.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                elif data.get("type") == "mark_read":
                    # Mark notification as read in database
                    notification_id = data.get("notification_id")
                    if notification_id:
                        supabase = get_supabase_client()
                        supabase.table("notifications").update({"read": True}).eq("id", notification_id).eq("user_id", user_id).execute()
                        await websocket.send_text(json.dumps({"type": "marked_read", "notification_id": notification_id}))
                elif data.get("type") == "acknowledge_alert":
                    # Acknowledge engagement alert
                    alert_id = data.get("alert_id")
                    if alert_id and is_admin:
                        supabase = get_supabase_client()
                        supabase.table("engagement_alerts").update({
                            "acknowledged": True,
                            "acknowledged_by": user_id,
                            "acknowledged_at": "now()"
                        }).eq("id", alert_id).execute()
                        await websocket.send_text(json.dumps({"type": "alert_acknowledged", "alert_id": alert_id}))
                
        except Exception as e:
            logger.error(f"Authentication error in WebSocket: {str(e)}")
            await websocket.send_text(json.dumps({"error": "Authentication failed"}))
            await websocket.close(code=1008)  # Policy violation
            return
            
    except WebSocketDisconnect:
        # Clean up connection
        notification_manager.disconnect(websocket, user_id, is_admin)
        logger.info(f"WebSocket disconnected for user {user_id}")
    except Exception as e:
        logger.error(f"Error in notifications WebSocket: {str(e)}")
        try:
            await websocket.close(code=1011)  # Internal error
        except:
            pass

@router.websocket("/ws/admin/dashboard")
async def admin_dashboard_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time admin dashboard updates."""
    await websocket.accept()
    
    user_id = None  # Initialize user_id to avoid UnboundLocalError
    
    try:
        # First message should be authentication token
        auth_message = await websocket.receive_text()
        auth_data = json.loads(auth_message)
        
        if "token" not in auth_data:
            await websocket.send_text(json.dumps({"error": "Authentication required"}))
            await websocket.close(code=1008)  # Policy violation
            return
            
        # Verify token and check admin permissions
        try:
            # Use ProductionAuthSystem to verify token
            auth_system = get_production_auth_system()
            token_payload = await auth_system._verify_jwt_secure(auth_data["token"])
            user_id = token_payload.get("sub")
            
            if not user_id:
                raise Exception("Invalid token payload")
            
            # Get user roles from database
            supabase = get_supabase_client()
            profile_response = supabase.table("user_profiles").select("roles").eq("id", user_id).execute()
            
            roles = []
            if profile_response.data and len(profile_response.data) > 0:
                roles = profile_response.data[0].get("roles", [])
            
            is_admin = any(role in ["super_admin", "support_admin", "business_analyst"] for role in roles)
            
            if not is_admin:
                await websocket.send_text(json.dumps({"error": "Admin access required"}))
                await websocket.close(code=1008)  # Policy violation
                return
            
            # Register admin connection
            admin_connections.add(websocket)
            
            # Send confirmation
            await websocket.send_text(json.dumps({"status": "connected", "user_id": user_id}))
            
            # Keep connection alive and handle incoming messages
            while True:
                message = await websocket.receive_text()
                data = json.loads(message)
                
                # Handle message types
                if data.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                elif data.get("type") == "subscribe":
                    # Handle subscription to specific dashboard metrics
                    metrics = data.get("metrics", [])
                    # Store subscription preferences
                    admin_subscriptions[user_id] = metrics
                    await websocket.send_text(json.dumps({"type": "subscribed", "metrics": metrics}))
                
        except Exception as e:
            logger.error(f"Authentication error in admin WebSocket: {str(e)}")
            await websocket.send_text(json.dumps({"error": "Authentication failed"}))
            await websocket.close(code=1008)  # Policy violation
            return
            
    except WebSocketDisconnect:
        # Clean up connection
        if websocket in admin_connections:
            admin_connections.remove(websocket)
        if user_id in admin_subscriptions:
            del admin_subscriptions[user_id]
        logger.info(f"Admin WebSocket disconnected for user {user_id}")
    except Exception as e:
        logger.error(f"Error in admin dashboard WebSocket: {str(e)}")
        try:
            await websocket.close(code=1011)  # Internal error
        except:
            pass

# Global variables for admin dashboard connections
admin_connections = set()
admin_subscriptions = {}