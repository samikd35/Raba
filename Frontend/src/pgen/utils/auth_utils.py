"""
Authentication utilities for Problem Generator module.

This module provides standardized authentication handling and user validation
to ensure consistent behavior across all pgen endpoints.
"""

import uuid
import logging
from typing import Optional, Dict, Any
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Custom exception for authentication errors."""
    pass


class UserValidationError(Exception):
    """Custom exception for user validation errors."""
    pass


def validate_and_extract_user_id(current_user: Any) -> str:
    """
    Standardized function to extract and validate user ID from get_current_user dependency.
    
    Args:
        current_user: The return value from get_current_user dependency
        
    Returns:
        str: Validated user ID
        
    Raises:
        HTTPException: If user ID is invalid or missing
    """
    try:
        # The production auth system returns a string (user ID)
        if isinstance(current_user, str):
            user_id = current_user.strip()
            if not user_id:
                raise UserValidationError("User ID is empty")
                
        # Legacy compatibility - handle dict format (should not happen in production)
        elif isinstance(current_user, dict):
            user_id = current_user.get('id')
            if not user_id:
                raise UserValidationError("User ID not found in auth context")
            user_id = str(user_id).strip()
            
        else:
            raise UserValidationError(f"Invalid current_user type: {type(current_user)}")
        
        # Validate UUID format
        try:
            uuid.UUID(user_id)
        except ValueError:
            raise UserValidationError(f"Invalid user ID format: {user_id}")
            
        logger.debug(f"Successfully validated user ID: {user_id}")
        return user_id
        
    except UserValidationError as e:
        logger.error(f"User validation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "invalid_user_id",
                "message": f"User validation failed: {str(e)}"
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error during user validation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "auth_system_error",
                "message": "Internal authentication error"
            }
        )


def validate_user_access_to_resource(user_id: str, resource_user_id: str, resource_type: str = "resource") -> None:
    """
    Validate that a user has access to a specific resource.
    
    Args:
        user_id: The authenticated user's ID
        resource_user_id: The user ID associated with the resource
        resource_type: Type of resource for error messages
        
    Raises:
        HTTPException: If user doesn't have access to the resource
    """
    if user_id != resource_user_id:
        logger.warning(f"User {user_id} attempted to access {resource_type} belonging to {resource_user_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "access_denied",
                "message": f"Access denied: You don't have permission to access this {resource_type}"
            }
        )


def create_auth_error_response(error_code: str, message: str, status_code: int = 401) -> HTTPException:
    """
    Create a standardized authentication error response.
    
    Args:
        error_code: Standardized error code
        message: Human-readable error message
        status_code: HTTP status code
        
    Returns:
        HTTPException: Formatted error response
    """
    return HTTPException(
        status_code=status_code,
        detail={
            "code": error_code,
            "message": message
        }
    )


def log_auth_event(user_id: str, action: str, resource_type: Optional[str] = None, 
                  resource_id: Optional[str] = None, success: bool = True, 
                  error_message: Optional[str] = None) -> None:
    """
    Log authentication and authorization events for audit purposes.
    
    Args:
        user_id: User ID performing the action
        action: Action being performed
        resource_type: Type of resource being accessed
        resource_id: ID of the resource being accessed
        success: Whether the action was successful
        error_message: Error message if action failed
    """
    log_data = {
        "user_id": user_id,
        "action": action,
        "success": success,
        "timestamp": logging.Formatter().formatTime(logging.LogRecord(
            name="auth", level=logging.INFO, pathname="", lineno=0,
            msg="", args=(), exc_info=None
        ))
    }
    
    if resource_type:
        log_data["resource_type"] = resource_type
    if resource_id:
        log_data["resource_id"] = resource_id
    if error_message:
        log_data["error"] = error_message
    
    if success:
        logger.info(f"Auth event: {log_data}")
    else:
        logger.warning(f"Auth failure: {log_data}")


class AuthenticatedUser:
    """
    Wrapper class for authenticated user information.
    Provides a clean interface for user data access.
    """
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self._uuid = uuid.UUID(user_id)  # Validate UUID format
    
    @property
    def uuid(self) -> uuid.UUID:
        """Get user ID as UUID object."""
        return self._uuid
    
    def __str__(self) -> str:
        return self.user_id
    
    def __repr__(self) -> str:
        return f"AuthenticatedUser(user_id='{self.user_id}')"
