"""
Report Error Handler Service

This service provides comprehensive error handling for report operations,
including graceful handling of missing, corrupted, or inaccessible historical reports.
It ensures proper error messages without exposing sensitive system information.

Requirements addressed:
- 5.2: Proper rollback mechanisms for failed database operations
- 5.3: Graceful error handling for missing, corrupted, or inaccessible historical reports
- 5.5: Proper error messages without exposing sensitive system information
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Union, List
from enum import Enum
from dataclasses import dataclass
from uuid import UUID

from fastapi import HTTPException
from ...utils.circuit_breaker import CircuitBreakerError

logger = logging.getLogger(__name__)


class ReportErrorType(Enum):
    """Enumeration of report error types for consistent error handling."""
    
    NOT_FOUND = "not_found"
    ACCESS_DENIED = "access_denied"
    CORRUPTED_DATA = "corrupted_data"
    INVALID_FORMAT = "invalid_format"
    DATABASE_ERROR = "database_error"
    AUTHENTICATION_ERROR = "authentication_error"
    VALIDATION_ERROR = "validation_error"
    SYSTEM_ERROR = "system_error"
    MIGRATION_ERROR = "migration_error"
    CIRCUIT_BREAKER_OPEN = "circuit_breaker_open"


@dataclass
class ReportError:
    """Structured error information for report operations."""
    
    error_type: ReportErrorType
    message: str
    user_message: str
    report_id: Optional[str] = None
    user_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class ReportErrorHandler:
    """
    Centralized error handling service for report operations.
    
    This service provides consistent error handling across all report-related
    operations, ensuring proper error messages without exposing sensitive
    system information while maintaining detailed logging for debugging.
    """
    
    def __init__(self):
        """Initialize the error handler."""
        self.logger = logging.getLogger(__name__)
    
    def handle_report_access_error(
        self,
        error: Exception,
        report_id: str,
        user_id: str,
        operation: str = "access"
    ) -> ReportError:
        """
        Handle errors during report access operations.
        
        Args:
            error: The original exception
            report_id: ID of the report being accessed
            user_id: ID of the user attempting access
            operation: Type of operation being performed
            
        Returns:
            ReportError with appropriate user-safe message
        """
        error_context = {
            "report_id": report_id,
            "user_id": user_id,
            "operation": operation,
            "error_type": type(error).__name__
        }
        
        # Handle specific error types
        if isinstance(error, ValueError):
            if "not found" in str(error).lower() or "access denied" in str(error).lower():
                self.logger.warning(f"Report access denied or not found: {error_context}")
                return ReportError(
                    error_type=ReportErrorType.NOT_FOUND,
                    message=f"Report {report_id} not found or access denied for user {user_id}",
                    user_message="The requested report could not be found or you don't have permission to access it.",
                    report_id=report_id,
                    user_id=user_id,
                    details=error_context
                )
            elif "invalid" in str(error).lower():
                self.logger.error(f"Invalid report data: {error_context}")
                return ReportError(
                    error_type=ReportErrorType.VALIDATION_ERROR,
                    message=f"Invalid data for report {report_id}: {str(error)}",
                    user_message="The report data is invalid. Please try refreshing the page.",
                    report_id=report_id,
                    user_id=user_id,
                    details=error_context
                )
        
        elif isinstance(error, CircuitBreakerError):
            self.logger.warning(f"Circuit breaker open for report access: {error_context}")
            return ReportError(
                error_type=ReportErrorType.CIRCUIT_BREAKER_OPEN,
                message=f"Circuit breaker open for report {report_id}",
                user_message="The service is temporarily unavailable. Please try again in a few moments.",
                report_id=report_id,
                user_id=user_id,
                details=error_context
            )
        
        elif isinstance(error, json.JSONDecodeError):
            self.logger.error(f"Corrupted report data: {error_context}")
            return ReportError(
                error_type=ReportErrorType.CORRUPTED_DATA,
                message=f"Corrupted JSON data in report {report_id}: {str(error)}",
                user_message="The report data appears to be corrupted. Please contact support if this issue persists.",
                report_id=report_id,
                user_id=user_id,
                details=error_context
            )
        
        elif "permission" in str(error).lower() or "unauthorized" in str(error).lower():
            self.logger.warning(f"Permission denied for report access: {error_context}")
            return ReportError(
                error_type=ReportErrorType.ACCESS_DENIED,
                message=f"Access denied to report {report_id} for user {user_id}",
                user_message="You don't have permission to access this report.",
                report_id=report_id,
                user_id=user_id,
                details=error_context
            )
        
        elif "database" in str(error).lower() or "connection" in str(error).lower():
            self.logger.error(f"Database error during report access: {error_context}")
            return ReportError(
                error_type=ReportErrorType.DATABASE_ERROR,
                message=f"Database error accessing report {report_id}: {str(error)}",
                user_message="A database error occurred. Please try again later.",
                report_id=report_id,
                user_id=user_id,
                details=error_context
            )
        
        else:
            # Generic system error
            self.logger.error(f"Unexpected error during report access: {error_context}, error: {str(error)}")
            return ReportError(
                error_type=ReportErrorType.SYSTEM_ERROR,
                message=f"System error accessing report {report_id}: {str(error)}",
                user_message="An unexpected error occurred. Please try again later or contact support if the issue persists.",
                report_id=report_id,
                user_id=user_id,
                details=error_context
            )
    
    def handle_data_corruption_error(
        self,
        report_id: str,
        user_id: str,
        corruption_details: Dict[str, Any]
    ) -> ReportError:
        """
        Handle data corruption errors with detailed logging.
        
        Args:
            report_id: ID of the corrupted report
            user_id: ID of the user
            corruption_details: Details about the corruption
            
        Returns:
            ReportError with appropriate handling
        """
        error_context = {
            "report_id": report_id,
            "user_id": user_id,
            "corruption_type": corruption_details.get("type", "unknown"),
            "corruption_details": corruption_details
        }
        
        self.logger.error(f"Data corruption detected: {error_context}")
        
        return ReportError(
            error_type=ReportErrorType.CORRUPTED_DATA,
            message=f"Data corruption in report {report_id}: {corruption_details}",
            user_message="The report data appears to be corrupted. Our team has been notified and will investigate.",
            report_id=report_id,
            user_id=user_id,
            details=error_context
        )
    
    def handle_migration_error(
        self,
        report_id: str,
        migration_step: str,
        error: Exception,
        rollback_info: Optional[Dict[str, Any]] = None
    ) -> ReportError:
        """
        Handle errors during data migration operations.
        
        Args:
            report_id: ID of the report being migrated
            migration_step: Current migration step
            error: The migration error
            rollback_info: Information about rollback status
            
        Returns:
            ReportError with migration-specific handling
        """
        error_context = {
            "report_id": report_id,
            "migration_step": migration_step,
            "error_type": type(error).__name__,
            "rollback_info": rollback_info
        }
        
        self.logger.error(f"Migration error: {error_context}, error: {str(error)}")
        
        return ReportError(
            error_type=ReportErrorType.MIGRATION_ERROR,
            message=f"Migration error for report {report_id} at step {migration_step}: {str(error)}",
            user_message="A data migration error occurred. The system will attempt to recover automatically.",
            report_id=report_id,
            details=error_context
        )
    
    def create_http_exception(self, report_error: ReportError) -> HTTPException:
        """
        Convert a ReportError to an HTTPException for API responses.
        
        Args:
            report_error: The ReportError to convert
            
        Returns:
            HTTPException with appropriate status code and user-safe message
        """
        # Map error types to HTTP status codes
        status_code_map = {
            ReportErrorType.NOT_FOUND: 404,
            ReportErrorType.ACCESS_DENIED: 403,
            ReportErrorType.AUTHENTICATION_ERROR: 401,
            ReportErrorType.VALIDATION_ERROR: 400,
            ReportErrorType.CORRUPTED_DATA: 422,
            ReportErrorType.INVALID_FORMAT: 400,
            ReportErrorType.CIRCUIT_BREAKER_OPEN: 503,
            ReportErrorType.DATABASE_ERROR: 500,
            ReportErrorType.MIGRATION_ERROR: 500,
            ReportErrorType.SYSTEM_ERROR: 500
        }
        
        status_code = status_code_map.get(report_error.error_type, 500)
        
        # Create user-safe response
        detail = {
            "error": report_error.error_type.value,
            "message": report_error.user_message,
            "timestamp": report_error.timestamp.isoformat(),
            "code": f"REPORT_{report_error.error_type.value.upper()}"
        }
        
        # Add report_id to response if available (safe to expose)
        if report_error.report_id:
            detail["report_id"] = report_error.report_id
        
        return HTTPException(status_code=status_code, detail=detail)
    
    def log_error_for_monitoring(self, report_error: ReportError) -> None:
        """
        Log error information for monitoring and alerting systems.
        
        Args:
            report_error: The error to log
        """
        log_data = {
            "error_type": report_error.error_type.value,
            "report_id": report_error.report_id,
            "user_id": report_error.user_id,
            "timestamp": report_error.timestamp.isoformat(),
            "error_message": report_error.message,  # Changed from 'message' to avoid LogRecord conflict
            "details": report_error.details
        }
        
        # Use structured logging for monitoring systems
        if report_error.error_type in [
            ReportErrorType.CORRUPTED_DATA,
            ReportErrorType.DATABASE_ERROR,
            ReportErrorType.MIGRATION_ERROR,
            ReportErrorType.SYSTEM_ERROR
        ]:
            self.logger.error("REPORT_ERROR_ALERT", extra=log_data)
        else:
            self.logger.warning("REPORT_ERROR_WARNING", extra=log_data)
    
    def validate_report_data_integrity(
        self,
        report_data: Dict[str, Any],
        report_id: str
    ) -> Optional[ReportError]:
        """
        Validate report data integrity and detect corruption.
        
        Args:
            report_data: The report data to validate
            report_id: ID of the report
            
        Returns:
            ReportError if corruption is detected, None if data is valid
        """
        try:
            # Check for required fields
            required_fields = ["id", "content"]
            missing_fields = [field for field in required_fields if field not in report_data]
            
            if missing_fields:
                return self.handle_data_corruption_error(
                    report_id=report_id,
                    user_id=report_data.get("user_id", "unknown"),
                    corruption_details={
                        "type": "missing_fields",
                        "missing_fields": missing_fields
                    }
                )
            
            # Validate content structure
            content = report_data.get("content")
            if content is not None:
                if isinstance(content, str):
                    try:
                        json.loads(content)
                    except json.JSONDecodeError as e:
                        return self.handle_data_corruption_error(
                            report_id=report_id,
                            user_id=report_data.get("user_id", "unknown"),
                            corruption_details={
                                "type": "invalid_json",
                                "json_error": str(e)
                            }
                        )
                elif not isinstance(content, dict):
                    return self.handle_data_corruption_error(
                        report_id=report_id,
                        user_id=report_data.get("user_id", "unknown"),
                        corruption_details={
                            "type": "invalid_content_type",
                            "actual_type": type(content).__name__
                        }
                    )
            
            # Validate UUID fields
            uuid_fields = ["id", "user_id"]
            for field in uuid_fields:
                if field in report_data and report_data[field] is not None:
                    try:
                        UUID(str(report_data[field]))
                    except (ValueError, TypeError):
                        return self.handle_data_corruption_error(
                            report_id=report_id,
                            user_id=report_data.get("user_id", "unknown"),
                            corruption_details={
                                "type": "invalid_uuid",
                                "field": field,
                                "value": str(report_data[field])
                            }
                        )
            
            return None  # Data is valid
            
        except Exception as e:
            return self.handle_data_corruption_error(
                report_id=report_id,
                user_id=report_data.get("user_id", "unknown"),
                corruption_details={
                    "type": "validation_error",
                    "error": str(e)
                }
            )
    
    def create_fallback_report_data(
        self,
        report_id: str,
        user_id: str,
        error_type: ReportErrorType
    ) -> Dict[str, Any]:
        """
        Create fallback report data when original data is corrupted or inaccessible.
        
        Args:
            report_id: ID of the report
            user_id: ID of the user
            error_type: Type of error that occurred
            
        Returns:
            Fallback report data structure
        """
        fallback_messages = {
            ReportErrorType.CORRUPTED_DATA: "This report's data appears to be corrupted and cannot be displayed properly.",
            ReportErrorType.NOT_FOUND: "This report could not be found in the system.",
            ReportErrorType.ACCESS_DENIED: "You don't have permission to access this report.",
            ReportErrorType.DATABASE_ERROR: "A database error prevented loading this report.",
            ReportErrorType.SYSTEM_ERROR: "A system error prevented loading this report."
        }
        
        message = fallback_messages.get(
            error_type,
            "This report could not be loaded due to an unexpected error."
        )
        
        return {
            "id": report_id,
            "title": "Report Loading Error",
            "summary": "An error occurred while loading this report",
            "report_type": "error",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "content": {
                "error": True,
                "error_type": error_type.value,
                "message": message,
                "instructions": [
                    "Try refreshing the page",
                    "Check your internet connection",
                    "Contact support if the issue persists"
                ],
                "support_info": {
                    "report_id": report_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        }


# Global error handler instance
_error_handler = None


def get_report_error_handler() -> ReportErrorHandler:
    """
    Get the global ReportErrorHandler instance.
    
    Returns:
        ReportErrorHandler instance
    """
    global _error_handler
    if _error_handler is None:
        _error_handler = ReportErrorHandler()
    return _error_handler