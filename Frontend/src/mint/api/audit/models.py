#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Audit Models and Data Structures.

This module contains Pydantic models and data structures for audit functionality,
including audit logs, security monitoring, and administrative actions.
"""

from enum import Enum
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from pydantic import BaseModel, Field


class AuditLogAction(str, Enum):
    """Enum for audit log actions."""
    USER_SUSPEND = "user_suspend"
    USER_ACTIVATE = "user_activate"
    USER_PASSWORD_RESET = "user_password_reset"
    USER_ROLE_ADD = "user_role_add"
    USER_ROLE_REMOVE = "user_role_remove"
    SESSION_TERMINATE = "session_terminate"
    CONFIG_UPDATE = "config_update"
    SYSTEM_MAINTENANCE = "system_maintenance"
    DATA_EXPORT = "data_export"
    CACHE_CLEAR = "cache_clear"
    FEATURE_FLAG_UPDATE = "feature_flag_update"
    SECURITY_ALERT = "security_alert"


class AuditLogTargetType(str, Enum):
    """Enum for audit log target types."""
    USER = "user"
    SYSTEM = "system"
    SESSION = "session"
    CONFIG = "config"
    CACHE = "cache"
    FEATURE_FLAG = "feature_flag"
    DATA = "data"


class AuditLog(BaseModel):
    """Audit log entry model."""
    id: str
    timestamp: datetime
    admin_user_id: str
    action: AuditLogAction
    target_type: AuditLogTargetType
    target_id: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None
    created_at: datetime


class AuditLogCreate(BaseModel):
    """Model for creating audit log entries."""
    admin_user_id: str
    action: AuditLogAction
    target_type: AuditLogTargetType
    target_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None


class AuditLogQuery(BaseModel):
    """Model for querying audit logs."""
    admin_user_id: Optional[str] = None
    action: Optional[AuditLogAction] = None
    target_type: Optional[AuditLogTargetType] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    offset: int = 0
    limit: int = 50


class AuditLogResponse(BaseModel):
    """Response model for audit log queries."""
    logs: List[AuditLog]
    total_count: int
    has_more: bool


class AuditLogStats(BaseModel):
    """Statistics model for audit logs."""
    total_actions: int
    successful_actions: int
    failed_actions: int
    unique_admins: int
    most_common_action: str
    action_count: int


class SecurityAlert(BaseModel):
    """Security alert model."""
    id: str
    alert_type: str
    severity: str
    description: str
    admin_user_id: Optional[str] = None
    ip_address: Optional[str] = None
    timestamp: datetime
    details: Dict[str, Any] = Field(default_factory=dict)
    resolved: bool = False
    resolved_at: Optional[datetime] = None


class AdminActivitySummary(BaseModel):
    """Admin activity summary model."""
    total_actions: int
    successful_actions: int
    failed_actions: int
    sensitive_actions: int
    unique_ips: int
    most_common_action: str
    most_common_target: str
    time_period: str


class AuditLogExport(BaseModel):
    """Audit log export model."""
    format: str = "json"
    query: AuditLogQuery
    exported_at: datetime
    total_records: int
    file_size: Optional[int] = None


class SecurityMonitoringConfig(BaseModel):
    """Security monitoring configuration."""
    max_failed_actions: int = 5
    monitoring_window_minutes: int = 15
    alert_threshold_actions: int = 10
    enable_ip_monitoring: bool = True
    enable_sensitive_action_monitoring: bool = True


class AuditLogFilter(BaseModel):
    """Advanced audit log filtering."""
    admin_user_ids: Optional[List[str]] = None
    actions: Optional[List[AuditLogAction]] = None
    target_types: Optional[List[AuditLogTargetType]] = None
    success_only: Optional[bool] = None
    has_error: Optional[bool] = None
    ip_addresses: Optional[List[str]] = None
    date_range: Optional[Dict[str, datetime]] = None


class AuditLogMetrics(BaseModel):
    """Audit log metrics for analytics."""
    period: str
    total_logs: int
    success_rate: float
    failure_rate: float
    top_actions: List[Dict[str, Any]]
    top_admins: List[Dict[str, Any]]
    top_targets: List[Dict[str, Any]]
    error_summary: List[Dict[str, Any]]


class AuditLogSearch(BaseModel):
    """Audit log search parameters."""
    query: str
    search_fields: List[str] = ["admin_user_id", "action", "target_type", "details"]
    case_sensitive: bool = False
    exact_match: bool = False


# Constants for security monitoring
SENSITIVE_ACTIONS = [
    AuditLogAction.USER_SUSPEND,
    AuditLogAction.USER_PASSWORD_RESET,
    AuditLogAction.USER_ROLE_ADD,
    AuditLogAction.USER_ROLE_REMOVE,
    AuditLogAction.CONFIG_UPDATE,
    AuditLogAction.SYSTEM_MAINTENANCE
]

# Security thresholds
DEFAULT_MAX_FAILED_ACTIONS = 5
DEFAULT_MONITORING_WINDOW_MINUTES = 15
DEFAULT_ALERT_THRESHOLD_ACTIONS = 10

# Audit log field mappings
AUDIT_LOG_FIELDS = {
    "id": "id",
    "timestamp": "timestamp",
    "admin_user_id": "admin_user_id",
    "action": "action",
    "target_type": "target_type",
    "target_id": "target_id",
    "details": "details",
    "ip_address": "ip_address",
    "user_agent": "user_agent",
    "success": "success",
    "error_message": "error_message",
    "created_at": "created_at"
}

# Export formats
SUPPORTED_EXPORT_FORMATS = ["json", "csv", "pdf", "xlsx"]

# Security alert types
SECURITY_ALERT_TYPES = [
    "multiple_failed_actions",
    "high_volume_sensitive_actions",
    "multiple_ip_addresses",
    "unusual_activity_pattern",
    "privilege_escalation_attempt",
    "suspicious_admin_behavior"
]

# Audit log severity levels
SEVERITY_LEVELS = ["low", "medium", "high", "critical"]


