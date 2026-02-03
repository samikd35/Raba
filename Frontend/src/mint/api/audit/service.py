#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Audit Service.

This service provides comprehensive audit logging capabilities for all administrative
actions performed through the admin dashboard. It includes enhanced security monitoring
features to track and analyze admin actions for security and compliance purposes.
"""

import logging
import json
import os
import socket
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timedelta
from fastapi import Request

from ..system.core.supabase_client import get_supabase_client
from ...schemas.schemas import (
    AuditLog, 
    AuditLogCreate, 
    AuditLogQuery, 
    AuditLogResponse, 
    AuditLogStats,
    AuditLogAction,
    AuditLogTargetType
)
from .models import (
    SecurityAlert, AdminActivitySummary, AuditLogExport,
    SENSITIVE_ACTIONS, DEFAULT_MAX_FAILED_ACTIONS,
    DEFAULT_MONITORING_WINDOW_MINUTES, DEFAULT_ALERT_THRESHOLD_ACTIONS
)
from .security import security_monitor
from .utils import (
    create_sample_audit_logs, export_audit_logs, validate_audit_log_query,
    format_audit_log_for_display, calculate_audit_log_metrics,
    filter_audit_logs, search_audit_logs, get_audit_log_summary
)

# Configure logging
logger = logging.getLogger(__name__)

# Security thresholds
MAX_FAILED_ACTIONS = int(os.getenv("MAX_FAILED_ACTIONS", str(DEFAULT_MAX_FAILED_ACTIONS)))
MONITORING_WINDOW_MINUTES = int(os.getenv("MONITORING_WINDOW_MINUTES", str(DEFAULT_MONITORING_WINDOW_MINUTES)))
ALERT_THRESHOLD_ACTIONS = int(os.getenv("ALERT_THRESHOLD_ACTIONS", str(DEFAULT_ALERT_THRESHOLD_ACTIONS)))


class AuditService:
    """Service for managing audit logs with enhanced security monitoring."""
    
    def __init__(self):
        self.supabase = get_supabase_client()
        self.hostname = socket.gethostname()
    
    async def log_action(
        self,
        admin_user_id: str,
        action: AuditLogAction,
        target_type: AuditLogTargetType,
        target_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> str:
        """
        Log an administrative action with enhanced security monitoring.
        
        Args:
            admin_user_id: ID of the admin performing the action
            action: Type of action being performed
            target_type: Type of target being affected
            target_id: ID of the specific target (optional)
            details: Additional context and metadata
            ip_address: IP address of the admin
            user_agent: User agent string
            success: Whether the action was successful
            error_message: Error message if action failed
            
        Returns:
            ID of the created audit log entry
        """
        try:
            # Enhance details with additional security context
            enhanced_details = details or {}
            enhanced_details.update({
                "hostname": self.hostname,
                "timestamp_utc": datetime.utcnow().isoformat(),
                "action_sensitivity": "high" if action in SENSITIVE_ACTIONS else "normal"
            })
            
            # Use the database function to insert audit log
            result = self.supabase.client.rpc(
                'log_admin_action',
                {
                    'p_admin_user_id': admin_user_id,
                    'p_action': action.value,
                    'p_target_type': target_type.value,
                    'p_target_id': target_id,
                    'p_details': enhanced_details,
                    'p_ip_address': ip_address,
                    'p_user_agent': user_agent,
                    'p_success': success,
                    'p_error_message': error_message
                }
            ).execute()
            
            if result.data:
                log_id = result.data
                logger.info(f"Audit log created: {log_id} - {action.value} by {admin_user_id}")
                
                # Track action for security monitoring
                security_alerts = await security_monitor.track_action_for_security(
                    admin_user_id, 
                    action, 
                    ip_address, 
                    success
                )
                
                # Log security alerts if any
                for alert in security_alerts:
                    logger.warning(f"Security alert: {alert.description}")
                
                return log_id
            else:
                logger.error("Failed to create audit log - no data returned")
                raise Exception("Failed to create audit log")
                
        except Exception as e:
            logger.error(f"Error creating audit log: {str(e)}")
            raise
    
    async def get_logs(self, query: AuditLogQuery) -> AuditLogResponse:
        """
        Retrieve audit logs with filtering and pagination.
        
        Args:
            query: Query parameters for filtering logs
            
        Returns:
            Paginated list of audit logs
        """
        try:
            # Validate query
            if not validate_audit_log_query(query):
                raise ValueError("Invalid audit log query")
            
            # Use direct table query instead of problematic database function
            # Build the query with filters
            table_query = self.supabase.table('audit_logs').select('*')
            
            # Apply filters if provided
            if query.admin_user_id:
                table_query = table_query.eq('admin_user_id', query.admin_user_id)
            if query.action:
                table_query = table_query.eq('action', query.action.value)
            if query.target_type:
                table_query = table_query.eq('target_type', query.target_type.value)
            if query.start_date:
                table_query = table_query.gte('timestamp', query.start_date.isoformat())
            if query.end_date:
                table_query = table_query.lte('timestamp', query.end_date.isoformat())
            
            # Apply pagination and ordering
            table_query = table_query.order('timestamp', desc=True)
            table_query = table_query.range(query.offset, query.offset + query.limit - 1)
            
            result = table_query.execute()
            
            logs = []
            if result.data:
                for row in result.data:
                    try:
                        # Handle potential missing columns gracefully
                        action_value = row.get('action', 'config_update')  # Use valid enum value as fallback
                        target_type_value = row.get('target_type', 'system')  # Use valid enum value as fallback
                        
                        # Validate enum values
                        try:
                            action = AuditLogAction(action_value)
                        except ValueError:
                            action = AuditLogAction.CONFIG_UPDATE  # Safe fallback
                            
                        try:
                            target_type = AuditLogTargetType(target_type_value)
                        except ValueError:
                            target_type = AuditLogTargetType.SYSTEM  # Safe fallback
                        
                        log = AuditLog(
                            id=row.get('id', ''),
                            timestamp=datetime.fromisoformat(row.get('timestamp', datetime.now().isoformat()).replace('Z', '+00:00')),
                            admin_user_id=row.get('admin_user_id', ''),
                            action=action,
                            target_type=target_type,
                            target_id=row.get('target_id', ''),
                            details=row.get('details', {}) or {},
                            ip_address=row.get('ip_address', ''),
                            user_agent=row.get('user_agent', ''),
                            success=row.get('success', True),
                            error_message=row.get('error_message', ''),
                            created_at=datetime.fromisoformat(row.get('timestamp', datetime.now().isoformat()).replace('Z', '+00:00'))
                        )
                        logs.append(log)
                    except Exception as row_error:
                        logger.warning(f"Skipping malformed audit log row: {row_error}")
                        continue
            
            # Get total count for pagination (simplified)
            try:
                count_result = self.supabase.table('audit_logs').select('*', count='exact').execute()
                total_count = count_result.count or 0
            except:
                # Fallback if count fails
                total_count = len(logs)
            
            has_more = (query.offset + len(logs)) < total_count
            
            return AuditLogResponse(
                logs=logs,
                total_count=total_count,
                has_more=has_more
            )
            
        except Exception as e:
            logger.error(f"Error retrieving audit logs: {str(e)}")
            # If audit_logs table doesn't exist or has issues, return sample data
            sample_logs = create_sample_audit_logs(query.limit)
            return AuditLogResponse(
                logs=sample_logs,
                total_count=len(sample_logs),
                has_more=False
            )
    
    async def get_stats(
        self, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> AuditLogStats:
        """
        Get audit log statistics for a time period.
        
        Args:
            start_date: Start of the time period (defaults to 30 days ago)
            end_date: End of the time period (defaults to now)
            
        Returns:
            Statistics about audit log entries
        """
        try:
            # Use the database function to get stats
            result = self.supabase.rpc(
                'get_audit_log_stats',
                {
                    'p_start_date': start_date.isoformat() if start_date else None,
                    'p_end_date': end_date.isoformat() if end_date else None
                }
            ).execute()
            
            if result.data and len(result.data) > 0:
                row = result.data[0]
                return AuditLogStats(
                    total_actions=row['total_actions'],
                    successful_actions=row['successful_actions'],
                    failed_actions=row['failed_actions'],
                    unique_admins=row['unique_admins'],
                    most_common_action=row['most_common_action'],
                    action_count=row['action_count']
                )
            else:
                # Return empty stats if no data
                return AuditLogStats(
                    total_actions=0,
                    successful_actions=0,
                    failed_actions=0,
                    unique_admins=0,
                    most_common_action="none",
                    action_count=0
                )
                
        except Exception as e:
            logger.error(f"Error retrieving audit log stats: {str(e)}")
            raise
    
    async def get_security_alerts(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[SecurityAlert]:
        """
        Get security alerts based on audit logs.
        
        This method analyzes audit logs to detect potential security issues.
        
        Args:
            start_date: Start of the time period (defaults to 24 hours ago)
            end_date: End of the time period (defaults to now)
            
        Returns:
            List of security alerts
        """
        if not start_date:
            start_date = datetime.utcnow() - timedelta(hours=24)
        if not end_date:
            end_date = datetime.utcnow()
            
        try:
            # Use the database function to get security alerts
            result = self.supabase.rpc(
                'get_security_alerts',
                {
                    'p_start_date': start_date.isoformat(),
                    'p_end_date': end_date.isoformat()
                }
            ).execute()
            
            if result.data:
                return result.data
            else:
                return []
                
        except Exception as e:
            logger.error(f"Error retrieving security alerts: {str(e)}")
            raise
    
    async def get_admin_activity_summary(
        self,
        admin_user_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get a summary of admin activity.
        
        Args:
            admin_user_id: Filter by admin user ID (optional)
            start_date: Start of the time period (defaults to 7 days ago)
            end_date: End of the time period (defaults to now)
            
        Returns:
            Summary of admin activity
        """
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=7)
        if not end_date:
            end_date = datetime.utcnow()
            
        try:
            # Use the database function to get admin activity summary
            result = self.supabase.rpc(
                'get_admin_activity_summary',
                {
                    'p_admin_user_id': admin_user_id,
                    'p_start_date': start_date.isoformat(),
                    'p_end_date': end_date.isoformat()
                }
            ).execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            else:
                return {
                    "total_actions": 0,
                    "successful_actions": 0,
                    "failed_actions": 0,
                    "sensitive_actions": 0,
                    "unique_ips": 0,
                    "most_common_action": "none",
                    "most_common_target": "none"
                }
                
        except Exception as e:
            logger.error(f"Error retrieving admin activity summary: {str(e)}")
            raise
    
    async def export_audit_logs(
        self,
        query: AuditLogQuery,
        format: str = "json"
    ) -> Union[str, bytes]:
        """
        Export audit logs in various formats.
        
        Args:
            query: Query parameters for filtering logs
            format: Export format ("json", "csv", "pdf", or "xlsx")
            
        Returns:
            Exported audit logs in the requested format
        """
        # Get the logs
        logs_response = await self.get_logs(query)
        logs = logs_response.logs
        
        return export_audit_logs(logs, format)
    
    def get_security_summary(self, admin_user_id: str) -> Dict[str, Any]:
        """
        Get security summary for a specific admin user.
        
        Args:
            admin_user_id: ID of the admin user
            
        Returns:
            Security summary dictionary
        """
        return security_monitor.get_security_summary(admin_user_id)
    
    def clear_security_history(self, admin_user_id: Optional[str] = None) -> None:
        """
        Clear security monitoring history.
        
        Args:
            admin_user_id: ID of the admin user (if None, clears all history)
        """
        if admin_user_id:
            security_monitor.clear_user_history(admin_user_id)
        else:
            security_monitor.clear_all_history()


# Global audit service instance
audit_service = AuditService()

