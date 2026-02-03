#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Audit Module for MINT.

This module provides comprehensive audit logging capabilities for all administrative
actions performed through the admin dashboard. It includes enhanced security monitoring
features to track and analyze admin actions for security and compliance purposes.

Module Structure:
- models: Pydantic models and data structures
- service: Main audit service implementation
- security: Security monitoring and threat detection
- decorators: Audit decorators for automatic logging
- utils: Utility functions and helpers
"""

from .service import AuditService, audit_service
from .security import SecurityMonitor, security_monitor
from .models import (
    # Enums
    AuditLogAction, AuditLogTargetType,
    
    # Core Models
    AuditLog, AuditLogCreate, AuditLogQuery, AuditLogResponse, AuditLogStats,
    SecurityAlert, AdminActivitySummary, AuditLogExport,
    SecurityMonitoringConfig, AuditLogFilter, AuditLogMetrics, AuditLogSearch,
    
    # Constants
    SENSITIVE_ACTIONS, DEFAULT_MAX_FAILED_ACTIONS, DEFAULT_MONITORING_WINDOW_MINUTES,
    DEFAULT_ALERT_THRESHOLD_ACTIONS, AUDIT_LOG_FIELDS, SUPPORTED_EXPORT_FORMATS,
    SECURITY_ALERT_TYPES, SEVERITY_LEVELS
)
from .decorators import (
    audit_action, audit_user_action, audit_system_action, audit_config_action,
    audit_session_action, audit_data_action, audit_feature_flag_action, audit_cache_action
)
from .utils import (
    create_sample_audit_logs, export_audit_logs, validate_audit_log_query,
    format_audit_log_for_display, calculate_audit_log_metrics,
    filter_audit_logs, search_audit_logs, get_audit_log_summary
)

__all__ = [
    # Main Service
    "AuditService",
    "audit_service",
    
    # Security Monitoring
    "SecurityMonitor",
    "security_monitor",
    
    # Enums
    "AuditLogAction",
    "AuditLogTargetType",
    
    # Core Models
    "AuditLog",
    "AuditLogCreate",
    "AuditLogQuery",
    "AuditLogResponse",
    "AuditLogStats",
    "SecurityAlert",
    "AdminActivitySummary",
    "AuditLogExport",
    "SecurityMonitoringConfig",
    "AuditLogFilter",
    "AuditLogMetrics",
    "AuditLogSearch",
    
    # Constants
    "SENSITIVE_ACTIONS",
    "DEFAULT_MAX_FAILED_ACTIONS",
    "DEFAULT_MONITORING_WINDOW_MINUTES",
    "DEFAULT_ALERT_THRESHOLD_ACTIONS",
    "AUDIT_LOG_FIELDS",
    "SUPPORTED_EXPORT_FORMATS",
    "SECURITY_ALERT_TYPES",
    "SEVERITY_LEVELS",
    
    # Decorators
    "audit_action",
    "audit_user_action",
    "audit_system_action",
    "audit_config_action",
    "audit_session_action",
    "audit_data_action",
    "audit_feature_flag_action",
    "audit_cache_action",
    
    # Utility Functions
    "create_sample_audit_logs",
    "export_audit_logs",
    "validate_audit_log_query",
    "format_audit_log_for_display",
    "calculate_audit_log_metrics",
    "filter_audit_logs",
    "search_audit_logs",
    "get_audit_log_summary"
]


