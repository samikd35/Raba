#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Audit Security Monitoring.

This module provides security monitoring capabilities for audit logs,
including threat detection, alerting, and security analysis.
"""

import logging
import socket
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from .models import (
    AuditLogAction, SecurityAlert, AdminActivitySummary,
    SENSITIVE_ACTIONS, DEFAULT_MAX_FAILED_ACTIONS,
    DEFAULT_MONITORING_WINDOW_MINUTES, DEFAULT_ALERT_THRESHOLD_ACTIONS
)

# Configure logging
logger = logging.getLogger(__name__)


class SecurityMonitor:
    """Security monitoring for audit logs."""
    
    def __init__(self):
        self.recent_actions = {}  # Track recent actions for security monitoring
        self.hostname = socket.gethostname()
        self.max_failed_actions = DEFAULT_MAX_FAILED_ACTIONS
        self.monitoring_window_minutes = DEFAULT_MONITORING_WINDOW_MINUTES
        self.alert_threshold_actions = DEFAULT_ALERT_THRESHOLD_ACTIONS
    
    async def track_action_for_security(
        self, 
        admin_user_id: str, 
        action: AuditLogAction, 
        ip_address: Optional[str],
        success: bool
    ) -> List[SecurityAlert]:
        """
        Track actions for security monitoring purposes.
        
        This method implements security monitoring to detect potential security
        issues such as:
        - Multiple failed actions from the same user/IP
        - Unusual patterns of sensitive actions
        - Rapid sequences of administrative actions
        
        Args:
            admin_user_id: ID of the admin performing the action
            action: Type of action being performed
            ip_address: IP address of the admin
            success: Whether the action was successful
            
        Returns:
            List of security alerts generated
        """
        current_time = datetime.utcnow()
        alerts = []
        
        # Track by user ID
        if admin_user_id not in self.recent_actions:
            self.recent_actions[admin_user_id] = []
        
        # Add current action
        self.recent_actions[admin_user_id].append({
            "time": current_time,
            "action": action,
            "ip_address": ip_address,
            "success": success
        })
        
        # Remove old actions outside monitoring window
        window_start = current_time - timedelta(minutes=self.monitoring_window_minutes)
        self.recent_actions[admin_user_id] = [
            a for a in self.recent_actions[admin_user_id] 
            if a["time"] >= window_start
        ]
        
        # Get recent actions in monitoring window
        recent_actions = self.recent_actions[admin_user_id]
        
        # Check for security issues
        
        # 1. Multiple failed actions
        failed_actions = [a for a in recent_actions if not a["success"]]
        if len(failed_actions) >= self.max_failed_actions:
            alert = SecurityAlert(
                id=f"failed_actions_{admin_user_id}_{current_time.timestamp()}",
                alert_type="multiple_failed_actions",
                severity="high",
                description=f"{len(failed_actions)} failed admin actions by {admin_user_id} "
                           f"in the last {self.monitoring_window_minutes} minutes",
                admin_user_id=admin_user_id,
                ip_address=ip_address,
                timestamp=current_time,
                details={
                    "failed_count": len(failed_actions),
                    "monitoring_window": self.monitoring_window_minutes,
                    "actions": [a["action"].value for a in failed_actions]
                }
            )
            alerts.append(alert)
            logger.warning(f"Security alert: {alert.description}")
        
        # 2. High volume of sensitive actions
        sensitive_actions = [a for a in recent_actions if a["action"] in SENSITIVE_ACTIONS]
        if len(sensitive_actions) >= self.alert_threshold_actions:
            alert = SecurityAlert(
                id=f"sensitive_actions_{admin_user_id}_{current_time.timestamp()}",
                alert_type="high_volume_sensitive_actions",
                severity="critical",
                description=f"{len(sensitive_actions)} sensitive admin actions by {admin_user_id} "
                           f"in the last {self.monitoring_window_minutes} minutes",
                admin_user_id=admin_user_id,
                ip_address=ip_address,
                timestamp=current_time,
                details={
                    "sensitive_count": len(sensitive_actions),
                    "monitoring_window": self.monitoring_window_minutes,
                    "actions": [a["action"].value for a in sensitive_actions]
                }
            )
            alerts.append(alert)
            logger.warning(f"Security alert: {alert.description}")
        
        # 3. Multiple actions from different IPs
        ip_addresses = {a["ip_address"] for a in recent_actions if a["ip_address"]}
        if len(ip_addresses) > 1:
            alert = SecurityAlert(
                id=f"multiple_ips_{admin_user_id}_{current_time.timestamp()}",
                alert_type="multiple_ip_addresses",
                severity="medium",
                description=f"Admin {admin_user_id} performed actions from multiple IPs: "
                           f"{', '.join(ip_addresses)}",
                admin_user_id=admin_user_id,
                ip_address=ip_address,
                timestamp=current_time,
                details={
                    "ip_count": len(ip_addresses),
                    "ip_addresses": list(ip_addresses),
                    "monitoring_window": self.monitoring_window_minutes
                }
            )
            alerts.append(alert)
            logger.warning(f"Security alert: {alert.description}")
        
        # 4. Unusual activity pattern (rapid succession of actions)
        if len(recent_actions) >= 10:  # Threshold for rapid actions
            time_span = (recent_actions[-1]["time"] - recent_actions[0]["time"]).total_seconds()
            if time_span < 300:  # Less than 5 minutes for 10+ actions
                alert = SecurityAlert(
                    id=f"rapid_actions_{admin_user_id}_{current_time.timestamp()}",
                    alert_type="unusual_activity_pattern",
                    severity="medium",
                    description=f"Admin {admin_user_id} performed {len(recent_actions)} actions "
                               f"in {time_span:.0f} seconds",
                    admin_user_id=admin_user_id,
                    ip_address=ip_address,
                    timestamp=current_time,
                    details={
                        "action_count": len(recent_actions),
                        "time_span_seconds": time_span,
                        "actions_per_minute": len(recent_actions) / (time_span / 60)
                    }
                )
                alerts.append(alert)
                logger.warning(f"Security alert: {alert.description}")
        
        return alerts
    
    def get_security_summary(self, admin_user_id: str) -> Dict[str, Any]:
        """
        Get security summary for a specific admin user.
        
        Args:
            admin_user_id: ID of the admin user
            
        Returns:
            Security summary dictionary
        """
        if admin_user_id not in self.recent_actions:
            return {
                "total_actions": 0,
                "failed_actions": 0,
                "sensitive_actions": 0,
                "unique_ips": 0,
                "risk_level": "low"
            }
        
        recent_actions = self.recent_actions[admin_user_id]
        current_time = datetime.utcnow()
        window_start = current_time - timedelta(minutes=self.monitoring_window_minutes)
        
        # Filter actions within monitoring window
        window_actions = [a for a in recent_actions if a["time"] >= window_start]
        
        failed_actions = [a for a in window_actions if not a["success"]]
        sensitive_actions = [a for a in window_actions if a["action"] in SENSITIVE_ACTIONS]
        unique_ips = len({a["ip_address"] for a in window_actions if a["ip_address"]})
        
        # Calculate risk level
        risk_level = "low"
        if len(failed_actions) >= self.max_failed_actions:
            risk_level = "high"
        elif len(sensitive_actions) >= self.alert_threshold_actions:
            risk_level = "critical"
        elif unique_ips > 1:
            risk_level = "medium"
        elif len(window_actions) >= 10:
            risk_level = "medium"
        
        return {
            "total_actions": len(window_actions),
            "failed_actions": len(failed_actions),
            "sensitive_actions": len(sensitive_actions),
            "unique_ips": unique_ips,
            "risk_level": risk_level,
            "monitoring_window_minutes": self.monitoring_window_minutes
        }
    
    def clear_user_history(self, admin_user_id: str) -> None:
        """
        Clear security monitoring history for a specific user.
        
        Args:
            admin_user_id: ID of the admin user
        """
        if admin_user_id in self.recent_actions:
            del self.recent_actions[admin_user_id]
            logger.info(f"Cleared security monitoring history for admin {admin_user_id}")
    
    def clear_all_history(self) -> None:
        """Clear all security monitoring history."""
        self.recent_actions.clear()
        logger.info("Cleared all security monitoring history")
    
    def update_config(
        self,
        max_failed_actions: Optional[int] = None,
        monitoring_window_minutes: Optional[int] = None,
        alert_threshold_actions: Optional[int] = None
    ) -> None:
        """
        Update security monitoring configuration.
        
        Args:
            max_failed_actions: Maximum failed actions before alert
            monitoring_window_minutes: Monitoring window in minutes
            alert_threshold_actions: Alert threshold for sensitive actions
        """
        if max_failed_actions is not None:
            self.max_failed_actions = max_failed_actions
        if monitoring_window_minutes is not None:
            self.monitoring_window_minutes = monitoring_window_minutes
        if alert_threshold_actions is not None:
            self.alert_threshold_actions = alert_threshold_actions
        
        logger.info(f"Updated security monitoring config: "
                   f"max_failed={self.max_failed_actions}, "
                   f"window={self.monitoring_window_minutes}min, "
                   f"threshold={self.alert_threshold_actions}")


# Global security monitor instance
security_monitor = SecurityMonitor()


