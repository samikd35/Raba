"""
Notification service for real-time alerts and notifications.
Handles WebSocket connections, alert generation, and notification delivery.
"""
import json
import asyncio
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Any, Optional, Set
from fastapi import WebSocket, WebSocketDisconnect, Depends
from pydantic import BaseModel

from ...system.core.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

# Models for notifications
class NotificationLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class Notification(BaseModel):
    id: str
    timestamp: datetime
    level: NotificationLevel
    title: str
    message: str
    source: str
    data: Optional[Dict[str, Any]] = None
    read: bool = False
    
class EngagementAlert(BaseModel):
    id: str
    timestamp: datetime
    metric_name: str
    current_value: float
    threshold_value: float
    comparison: str  # "below", "above"
    percentage_change: Optional[float] = None
    is_anomaly: bool = False
    details: Optional[Dict[str, Any]] = None

# WebSocket connection manager
class NotificationManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.admin_connections: Dict[str, List[WebSocket]] = {}
        self.alert_thresholds: Dict[str, Dict[str, float]] = {
            "user_volume": {"warning": 0.1, "critical": 0.2},  # 10% and 20% decrease
            "report_generation": {"warning": 0.15, "critical": 0.25},
            "screen_time": {"warning": 0.12, "critical": 0.22},
            "click_through": {"warning": 0.15, "critical": 0.3},
        }
        
    async def connect(self, websocket: WebSocket, user_id: str, is_admin: bool = False):
        await websocket.accept()
        
        if is_admin:
            if user_id not in self.admin_connections:
                self.admin_connections[user_id] = []
            self.admin_connections[user_id].append(websocket)
            logger.info(f"Admin {user_id} connected to notifications")
        else:
            if user_id not in self.active_connections:
                self.active_connections[user_id] = []
            self.active_connections[user_id].append(websocket)
            logger.info(f"User {user_id} connected to notifications")
            
        # Send initial unread notifications
        await self.send_unread_notifications(user_id, websocket)
        
    async def register_connection(self, websocket: WebSocket, user_id: str, is_admin: bool = False):
        """Register a WebSocket connection that's already been accepted."""
        if is_admin:
            if user_id not in self.admin_connections:
                self.admin_connections[user_id] = []
            self.admin_connections[user_id].append(websocket)
            logger.info(f"Admin {user_id} connected to notifications")
        else:
            if user_id not in self.active_connections:
                self.active_connections[user_id] = []
            self.active_connections[user_id].append(websocket)
            logger.info(f"User {user_id} connected to notifications")
            
        # Send initial unread notifications
        await self.send_unread_notifications(user_id, websocket)
        
    def disconnect(self, websocket: WebSocket, user_id: str, is_admin: bool = False):
        if is_admin and user_id in self.admin_connections:
            self.admin_connections[user_id].remove(websocket)
            if not self.admin_connections[user_id]:
                del self.admin_connections[user_id]
            logger.info(f"Admin {user_id} disconnected from notifications")
        elif user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
            logger.info(f"User {user_id} disconnected from notifications")
    
    async def send_personal_notification(self, user_id: str, notification: Dict[str, Any]):
        """Send notification to a specific user"""
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                await connection.send_text(json.dumps(notification))
                
        # Store notification in database
        await self._store_notification(user_id, notification)
    
    async def broadcast_admin_notification(self, notification: Dict[str, Any]):
        """Broadcast notification to all connected admins"""
        for user_id, connections in self.admin_connections.items():
            for connection in connections:
                await connection.send_text(json.dumps(notification))
                
        # Store notification for all admins
        await self._store_admin_notification(notification)
    
    async def broadcast_system_update(self, update: Dict[str, Any]):
        """Broadcast system update to all connected clients"""
        # Send to regular users
        for user_id, connections in self.active_connections.items():
            for connection in connections:
                await connection.send_text(json.dumps(update))
                
        # Send to admins
        for user_id, connections in self.admin_connections.items():
            for connection in connections:
                await connection.send_text(json.dumps(update))
    
    async def send_engagement_alert(self, alert: EngagementAlert):
        """Send engagement alert to all admin connections"""
        alert_dict = alert.dict()
        alert_dict["type"] = "engagement_alert"
        
        for user_id, connections in self.admin_connections.items():
            for connection in connections:
                await connection.send_text(json.dumps(alert_dict))
                
        # Store alert in database
        await self._store_engagement_alert(alert)
    
    async def send_unread_notifications(self, user_id: str, websocket: WebSocket):
        """Send unread notifications to user on connect"""
        supabase = get_supabase_client()
        
        # Get unread notifications for user
        response = supabase.table("notifications").select("*").eq("user_id", user_id).eq("read", False).execute()
        
        if response.data:
            for notification in response.data:
                await websocket.send_text(json.dumps(notification))
    
    async def _store_notification(self, user_id: str, notification: Dict[str, Any]):
        """Store notification in database"""
        supabase = get_supabase_client()
        
        notification_data = {
            "user_id": user_id,
            "timestamp": notification.get("timestamp", datetime.now().isoformat()),
            "level": notification.get("level", "info"),
            "title": notification.get("title"),
            "message": notification.get("message"),
            "source": notification.get("source"),
            "data": notification.get("data"),
            "read": False
        }
        
        supabase.table("notifications").insert(notification_data).execute()
    
    async def _store_admin_notification(self, notification: Dict[str, Any]):
        """Store notification for all admin users"""
        supabase = get_supabase_client()
        
        # Get all admin user IDs
        response = supabase.table("user_profiles").select("user_id").in_("role", ["super_admin", "support_admin", "business_analyst"]).execute()
        
        if response.data:
            for admin in response.data:
                await self._store_notification(admin["user_id"], notification)
    
    async def _store_engagement_alert(self, alert: EngagementAlert):
        """Store engagement alert in database"""
        supabase = get_supabase_client()
        
        alert_data = alert.dict()
        alert_data["timestamp"] = alert_data["timestamp"].isoformat()
        
        supabase.table("engagement_alerts").insert(alert_data).execute()
    
    def check_engagement_threshold(self, metric_name: str, current_value: float, 
                                  previous_value: float) -> Optional[EngagementAlert]:
        """Check if engagement metric has crossed a threshold"""
        if previous_value == 0:
            return None  # Avoid division by zero
            
        percentage_change = (current_value - previous_value) / previous_value
        
        # Check if metric is decreasing (negative change)
        if percentage_change < 0:
            abs_change = abs(percentage_change)
            thresholds = self.alert_thresholds.get(metric_name, {})
            
            if abs_change >= thresholds.get("critical", 0.2):
                level = "critical"
            elif abs_change >= thresholds.get("warning", 0.1):
                level = "warning"
            else:
                return None  # No threshold crossed
                
            return EngagementAlert(
                id=f"{metric_name}-{datetime.now().isoformat()}",
                timestamp=datetime.now(),
                metric_name=metric_name,
                current_value=current_value,
                threshold_value=previous_value * (1 - thresholds.get(level, 0.1)),
                comparison="below",
                percentage_change=percentage_change,
                is_anomaly=False,
                details={
                    "previous_value": previous_value,
                    "level": level,
                    "threshold_name": f"{level}_threshold"
                }
            )
        
        return None
        
    async def detect_engagement_anomalies(self):
        """Detect anomalies in engagement metrics using simple statistical methods"""
        supabase = get_supabase_client()
        
        # Get historical engagement data (last 30 days)
        thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
        
        metrics = [
            "user_volume", 
            "report_generation", 
            "screen_time", 
            "click_through"
        ]
        
        for metric in metrics:
            # Get historical data for this metric
            response = supabase.table("user_engagement_metrics").select("date", metric).gte("date", thirty_days_ago).order("date").execute()
            
            if not response.data or len(response.data) < 7:
                continue  # Not enough data for anomaly detection
                
            # Calculate mean and standard deviation
            values = [item[metric] for item in response.data]
            mean = sum(values) / len(values)
            std_dev = (sum((x - mean) ** 2 for x in values) / len(values)) ** 0.5
            
            # Get latest value
            latest = values[-1]
            
            # Check if latest value is an anomaly (more than 2 standard deviations from mean)
            if abs(latest - mean) > 2 * std_dev:
                alert = EngagementAlert(
                    id=f"{metric}-anomaly-{datetime.now().isoformat()}",
                    timestamp=datetime.now(),
                    metric_name=metric,
                    current_value=latest,
                    threshold_value=mean,
                    comparison="below" if latest < mean else "above",
                    percentage_change=(latest - mean) / mean if mean != 0 else None,
                    is_anomaly=True,
                    details={
                        "mean": mean,
                        "std_dev": std_dev,
                        "z_score": (latest - mean) / std_dev if std_dev != 0 else None
                    }
                )
                
                await self.send_engagement_alert(alert)

# Create global notification manager
notification_manager = NotificationManager()