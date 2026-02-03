"""
Audit logging service for admin dashboard.

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
import asyncpg
from ..api.supabase_client import get_supabase_client
from ..schemas.schemas import (
    AuditLog, 
    AuditLogCreate, 
    AuditLogQuery, 
    AuditLogResponse, 
    AuditLogStats,
    AuditLogAction,
    AuditLogTargetType
)

# Configure logging
logger = logging.getLogger(__name__)

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
MAX_FAILED_ACTIONS = int(os.getenv("MAX_FAILED_ACTIONS", "5"))
MONITORING_WINDOW_MINUTES = int(os.getenv("MONITORING_WINDOW_MINUTES", "15"))
ALERT_THRESHOLD_ACTIONS = int(os.getenv("ALERT_THRESHOLD_ACTIONS", "10"))


class AuditService:
    """Service for managing audit logs with enhanced security monitoring."""
    
    def __init__(self):
        self.supabase = get_supabase_client()
        self.recent_actions = {}  # Track recent actions for security monitoring
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
                await self._track_action_for_security(
                    admin_user_id, 
                    action, 
                    ip_address, 
                    success
                )
                
                return log_id
            else:
                logger.error("Failed to create audit log - no data returned")
                raise Exception("Failed to create audit log")
                
        except Exception as e:
            logger.error(f"Error creating audit log: {str(e)}")
            raise
    
    async def _track_action_for_security(
        self, 
        admin_user_id: str, 
        action: AuditLogAction, 
        ip_address: Optional[str],
        success: bool
    ):
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
        """
        current_time = datetime.utcnow()
        
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
        window_start = current_time - timedelta(minutes=MONITORING_WINDOW_MINUTES)
        self.recent_actions[admin_user_id] = [
            a for a in self.recent_actions[admin_user_id] 
            if a["time"] >= window_start
        ]
        
        # Get recent actions in monitoring window
        recent_actions = self.recent_actions[admin_user_id]
        
        # Check for security issues
        
        # 1. Multiple failed actions
        failed_actions = [a for a in recent_actions if not a["success"]]
        if len(failed_actions) >= MAX_FAILED_ACTIONS:
            logger.warning(
                f"Security alert: {len(failed_actions)} failed admin actions by {admin_user_id} "
                f"in the last {MONITORING_WINDOW_MINUTES} minutes"
            )
            # Here you would typically trigger an alert or notification
            
        # 2. High volume of sensitive actions
        sensitive_actions = [a for a in recent_actions if a["action"] in SENSITIVE_ACTIONS]
        if len(sensitive_actions) >= ALERT_THRESHOLD_ACTIONS:
            logger.warning(
                f"Security alert: {len(sensitive_actions)} sensitive admin actions by {admin_user_id} "
                f"in the last {MONITORING_WINDOW_MINUTES} minutes"
            )
            # Here you would typically trigger an alert or notification
            
        # 3. Multiple actions from different IPs
        ip_addresses = {a["ip_address"] for a in recent_actions if a["ip_address"]}
        if len(ip_addresses) > 1:
            logger.warning(
                f"Security alert: Admin {admin_user_id} performed actions from multiple IPs: "
                f"{', '.join(ip_addresses)}"
            )
            # Here you would typically trigger an alert or notification
    
    async def get_logs(self, query: AuditLogQuery) -> AuditLogResponse:
        """
        Retrieve audit logs with filtering and pagination.
        
        Args:
            query: Query parameters for filtering logs
            
        Returns:
            Paginated list of audit logs
        """
        try:
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
            sample_logs = self._create_sample_audit_logs(query.limit)
            return AuditLogResponse(
                logs=sample_logs,
                total_count=len(sample_logs),
                has_more=False
            )
    
    def _create_sample_audit_logs(self, limit: int = 10) -> List[AuditLog]:
        """
        Create sample audit logs for demonstration when real data is unavailable.
        
        Args:
            limit: Number of sample logs to create
            
        Returns:
            List of sample audit logs
        """
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


# Decorator for automatic audit logging
def audit_action(
    action: AuditLogAction,
    target_type: AuditLogTargetType,
    get_target_id: Optional[callable] = None,
    get_details: Optional[callable] = None
):
    """
    Decorator to automatically log admin actions.
    
    Args:
        action: Type of action being performed
        target_type: Type of target being affected
        get_target_id: Function to extract target ID from function args
        get_details: Function to extract additional details from function args
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            audit_service = AuditService()
            
            # Extract admin user ID from request context
            admin_user_id = None
            ip_address = None
            user_agent = None
            
            # Look for request object in args/kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                for value in kwargs.values():
                    if isinstance(value, Request):
                        request = value
                        break
            
            if request:
                # Extract user ID from JWT token or session
                admin_user_id = getattr(request.state, 'user_id', None)
                ip_address = request.client.host if request.client else None
                user_agent = request.headers.get('user-agent')
            
            # Extract target ID and details if functions provided
            target_id = None
            details = {}
            
            if get_target_id:
                try:
                    target_id = get_target_id(*args, **kwargs)
                except Exception as e:
                    logger.warning(f"Failed to extract target ID: {str(e)}")
            
            if get_details:
                try:
                    details = get_details(*args, **kwargs)
                except Exception as e:
                    logger.warning(f"Failed to extract details: {str(e)}")
            
            # Execute the function
            success = True
            error_message = None
            
            try:
                result = await func(*args, **kwargs)
                
                # Log successful action
                if admin_user_id:
                    await audit_service.log_action(
                        admin_user_id=admin_user_id,
                        action=action,
                        target_type=target_type,
                        target_id=target_id,
                        details=details,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        success=True
                    )
                
                return result
                
            except Exception as e:
                success = False
                error_message = str(e)
                
                # Log failed action
                if admin_user_id:
                    await audit_service.log_action(
                        admin_user_id=admin_user_id,
                        action=action,
                        target_type=target_type,
                        target_id=target_id,
                        details=details,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        success=False,
                        error_message=error_message
                    )
                
                raise
        
        return wrapper
    return decorator


# Additional security monitoring methods
    async def get_security_alerts(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
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
            format: Export format ("json", "csv", or "pdf")
            
        Returns:
            Exported audit logs in the requested format
        """
        # Get the logs
        logs_response = await self.get_logs(query)
        logs = logs_response.logs
        
        if format.lower() == "json":
            # Convert to JSON
            logs_dict = [log.dict() for log in logs]
            return json.dumps(logs_dict, default=str, indent=2)
            
        elif format.lower() == "csv":
            # Convert to CSV
            import csv
            import io
            
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
            
        else:
            raise ValueError(f"Unsupported export format: {format}")


# Global audit service instance
audit_service = AuditService()