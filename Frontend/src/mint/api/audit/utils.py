#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Audit Utility Functions.

This module provides utility functions for audit operations, including
data processing, formatting, and validation.
"""

import json
import csv
import io
import logging
from typing import Dict, Any, List, Union, Optional
from datetime import datetime, timedelta

from .models import (
    AuditLog, AuditLogQuery, AuditLogResponse, AuditLogStats,
    SUPPORTED_EXPORT_FORMATS, AUDIT_LOG_FIELDS
)

# Configure logging
logger = logging.getLogger(__name__)


def create_sample_audit_logs(limit: int = 10) -> List[AuditLog]:
    """
    Create sample audit logs for demonstration when real data is unavailable.
    
    Args:
        limit: Number of sample logs to create
        
    Returns:
        List of sample audit logs
    """
    from .models import AuditLogAction, AuditLogTargetType
    
    sample_logs = []
    base_time = datetime.now()
    
    actions = [
        AuditLogAction.USER_SUSPEND,
        AuditLogAction.USER_ACTIVATE,
        AuditLogAction.SESSION_TERMINATE,
        AuditLogAction.CONFIG_UPDATE,
        AuditLogAction.SYSTEM_MAINTENANCE
    ]
    
    target_types = [
        AuditLogTargetType.USER,
        AuditLogTargetType.SYSTEM,
        AuditLogTargetType.SESSION,
        AuditLogTargetType.CONFIG
    ]
    
    for i in range(min(limit, 10)):  # Cap at 10 sample logs
        log = AuditLog(
            id=f"sample-{i+1}",
            timestamp=base_time - timedelta(hours=i),
            admin_user_id="admin-sample",
            action=actions[i % len(actions)],
            target_type=target_types[i % len(target_types)],
            target_id=f"target-{i+1}",
            details={
                "sample": True,
                "description": f"Sample audit log entry {i+1}",
                "reason": "Demonstration data"
            },
            ip_address="127.0.0.1",
            user_agent="Sample User Agent",
            success=i % 3 != 0,  # Mix of success and failure
            error_message="Sample error" if i % 3 == 0 else None,
            created_at=base_time - timedelta(hours=i)
        )
        sample_logs.append(log)
    
    return sample_logs


def export_audit_logs(
    logs: List[AuditLog],
    format: str = "json"
) -> Union[str, bytes]:
    """
    Export audit logs in various formats.
    
    Args:
        logs: List of audit logs to export
        format: Export format ("json", "csv", "pdf", or "xlsx")
        
    Returns:
        Exported audit logs in the requested format
    """
    if format.lower() not in SUPPORTED_EXPORT_FORMATS:
        raise ValueError(f"Unsupported export format: {format}. "
                        f"Supported formats: {SUPPORTED_EXPORT_FORMATS}")
    
    if format.lower() == "json":
        # Convert to JSON
        logs_dict = [log.dict() for log in logs]
        return json.dumps(logs_dict, default=str, indent=2)
        
    elif format.lower() == "csv":
        # Convert to CSV
        output = io.StringIO()
        if logs:
            writer = csv.DictWriter(
                output,
                fieldnames=logs[0].dict().keys()
            )
            writer.writeheader()
            for log in logs:
                # Convert datetime to string and handle nested dicts
                log_dict = log.dict()
                for key, value in log_dict.items():
                    if isinstance(value, datetime):
                        log_dict[key] = value.isoformat()
                    elif isinstance(value, dict):
                        log_dict[key] = json.dumps(value)
                writer.writerow(log_dict)
        
        return output.getvalue()
        
    elif format.lower() == "pdf":
        # For PDF export, you would typically use a library like reportlab
        # This is a placeholder implementation
        logger.warning("PDF export not implemented, falling back to JSON")
        return export_audit_logs(logs, "json")
        
    elif format.lower() == "xlsx":
        # For Excel export, you would typically use openpyxl or xlsxwriter
        # This is a placeholder implementation
        logger.warning("Excel export not implemented, falling back to CSV")
        return export_audit_logs(logs, "csv")
    
    else:
        raise ValueError(f"Unsupported export format: {format}")


def validate_audit_log_query(query: AuditLogQuery) -> bool:
    """
    Validate an audit log query.
    
    Args:
        query: Audit log query to validate
        
    Returns:
        True if query is valid
    """
    if query.limit <= 0:
        logger.error("Query limit must be positive")
        return False
    
    if query.offset < 0:
        logger.error("Query offset must be non-negative")
        return False
    
    if query.limit > 1000:
        logger.warning("Query limit is very large, consider pagination")
    
    if query.start_date and query.end_date:
        if query.start_date >= query.end_date:
            logger.error("Start date must be before end date")
            return False
    
    return True


def format_audit_log_for_display(log: AuditLog) -> Dict[str, Any]:
    """
    Format an audit log for display purposes.
    
    Args:
        log: Audit log to format
        
    Returns:
        Formatted audit log dictionary
    """
    return {
        "id": log.id,
        "timestamp": log.timestamp.isoformat(),
        "admin_user_id": log.admin_user_id,
        "action": log.action.value,
        "target_type": log.target_type.value,
        "target_id": log.target_id,
        "details": json.dumps(log.details) if log.details else "",
        "ip_address": log.ip_address,
        "user_agent": log.user_agent,
        "success": "✓" if log.success else "✗",
        "error_message": log.error_message or "",
        "created_at": log.created_at.isoformat()
    }


def calculate_audit_log_metrics(logs: List[AuditLog]) -> Dict[str, Any]:
    """
    Calculate metrics from a list of audit logs.
    
    Args:
        logs: List of audit logs
        
    Returns:
        Calculated metrics
    """
    if not logs:
        return {
            "total_logs": 0,
            "success_rate": 0.0,
            "failure_rate": 0.0,
            "unique_admins": 0,
            "unique_actions": 0,
            "time_span_hours": 0.0
        }
    
    total_logs = len(logs)
    successful_logs = sum(1 for log in logs if log.success)
    failed_logs = total_logs - successful_logs
    
    success_rate = (successful_logs / total_logs) * 100 if total_logs > 0 else 0
    failure_rate = (failed_logs / total_logs) * 100 if total_logs > 0 else 0
    
    unique_admins = len(set(log.admin_user_id for log in logs))
    unique_actions = len(set(log.action for log in logs))
    
    # Calculate time span
    timestamps = [log.timestamp for log in logs]
    if timestamps:
        time_span = max(timestamps) - min(timestamps)
        time_span_hours = time_span.total_seconds() / 3600
    else:
        time_span_hours = 0.0
    
    return {
        "total_logs": total_logs,
        "success_rate": round(success_rate, 2),
        "failure_rate": round(failure_rate, 2),
        "unique_admins": unique_admins,
        "unique_actions": unique_actions,
        "time_span_hours": round(time_span_hours, 2)
    }


def filter_audit_logs(
    logs: List[AuditLog],
    admin_user_id: Optional[str] = None,
    action: Optional[str] = None,
    target_type: Optional[str] = None,
    success_only: Optional[bool] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> List[AuditLog]:
    """
    Filter audit logs based on criteria.
    
    Args:
        logs: List of audit logs to filter
        admin_user_id: Filter by admin user ID
        action: Filter by action
        target_type: Filter by target type
        success_only: Filter by success status
        start_date: Filter by start date
        end_date: Filter by end date
        
    Returns:
        Filtered list of audit logs
    """
    filtered_logs = logs
    
    if admin_user_id:
        filtered_logs = [log for log in filtered_logs if log.admin_user_id == admin_user_id]
    
    if action:
        filtered_logs = [log for log in filtered_logs if log.action.value == action]
    
    if target_type:
        filtered_logs = [log for log in filtered_logs if log.target_type.value == target_type]
    
    if success_only is not None:
        filtered_logs = [log for log in filtered_logs if log.success == success_only]
    
    if start_date:
        filtered_logs = [log for log in filtered_logs if log.timestamp >= start_date]
    
    if end_date:
        filtered_logs = [log for log in filtered_logs if log.timestamp <= end_date]
    
    return filtered_logs


def search_audit_logs(
    logs: List[AuditLog],
    query: str,
    search_fields: List[str] = ["admin_user_id", "action", "target_type", "details"],
    case_sensitive: bool = False
) -> List[AuditLog]:
    """
    Search audit logs based on text query.
    
    Args:
        logs: List of audit logs to search
        query: Search query
        search_fields: Fields to search in
        case_sensitive: Whether search is case sensitive
        
    Returns:
        List of matching audit logs
    """
    if not query:
        return logs
    
    if not case_sensitive:
        query = query.lower()
    
    matching_logs = []
    
    for log in logs:
        for field in search_fields:
            if field == "admin_user_id" and log.admin_user_id:
                value = log.admin_user_id if case_sensitive else log.admin_user_id.lower()
                if query in value:
                    matching_logs.append(log)
                    break
            elif field == "action" and log.action:
                value = log.action.value if case_sensitive else log.action.value.lower()
                if query in value:
                    matching_logs.append(log)
                    break
            elif field == "target_type" and log.target_type:
                value = log.target_type.value if case_sensitive else log.target_type.value.lower()
                if query in value:
                    matching_logs.append(log)
                    break
            elif field == "details" and log.details:
                details_str = json.dumps(log.details) if case_sensitive else json.dumps(log.details).lower()
                if query in details_str:
                    matching_logs.append(log)
                    break
    
    return matching_logs


def get_audit_log_summary(logs: List[AuditLog]) -> Dict[str, Any]:
    """
    Get a summary of audit logs.
    
    Args:
        logs: List of audit logs
        
    Returns:
        Summary dictionary
    """
    if not logs:
        return {
            "total_logs": 0,
            "date_range": None,
            "top_actions": [],
            "top_admins": [],
            "success_rate": 0.0
        }
    
    # Calculate basic metrics
    total_logs = len(logs)
    successful_logs = sum(1 for log in logs if log.success)
    success_rate = (successful_logs / total_logs) * 100 if total_logs > 0 else 0
    
    # Get date range
    timestamps = [log.timestamp for log in logs]
    date_range = {
        "start": min(timestamps).isoformat(),
        "end": max(timestamps).isoformat()
    }
    
    # Get top actions
    action_counts = {}
    for log in logs:
        action = log.action.value
        action_counts[action] = action_counts.get(action, 0) + 1
    
    top_actions = sorted(action_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # Get top admins
    admin_counts = {}
    for log in logs:
        admin = log.admin_user_id
        admin_counts[admin] = admin_counts.get(admin, 0) + 1
    
    top_admins = sorted(admin_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    
    return {
        "total_logs": total_logs,
        "date_range": date_range,
        "top_actions": top_actions,
        "top_admins": top_admins,
        "success_rate": round(success_rate, 2)
    }


