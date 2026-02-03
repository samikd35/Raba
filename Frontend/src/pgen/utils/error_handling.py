"""
Error Handling Utilities for Problem Generator API

This module provides standardized error handling functions and classes
for the Problem Generator API endpoints.
"""

import logging
import traceback
from typing import Dict, Any, Optional, Type, List, Union
from fastapi import HTTPException, status
from pydantic import BaseModel, Field

# Configure logger
logger = logging.getLogger("pgen.errors")

class ErrorDetail(BaseModel):
    """Detailed error information model."""
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    field: Optional[str] = Field(None, description="Field that caused the error (if applicable)")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class ErrorResponse(BaseModel):
    """Standardized error response model."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[List[ErrorDetail]] = Field(None, description="Detailed error information")
    request_id: Optional[str] = Field(None, description="Request ID for tracking")


# Define standard error types
class APIError(Exception):
    """Base class for API errors."""
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "internal_server_error"
    error_message: str = "An unexpected error occurred"
    
    def __init__(
        self, 
        message: Optional[str] = None, 
        details: Optional[List[Dict[str, Any]]] = None,
        log_exception: bool = True
    ):
        self.message = message or self.error_message
        self.details = details
        
        if log_exception:
            self._log_error()
            
        super().__init__(self.message)
    
    def _log_error(self) -> None:
        """Log the error with appropriate context."""
        logger.error(
            f"API Error ({self.error_code}): {self.message}",
            extra={
                "error_code": self.error_code,
                "status_code": self.status_code,
                "details": self.details
            }
        )
    
    def to_http_exception(self) -> HTTPException:
        """Convert to FastAPI HTTPException."""
        error_details = None
        
        if self.details:
            error_details = [
                ErrorDetail(
                    code=detail.get("code", self.error_code),
                    message=detail.get("message", ""),
                    field=detail.get("field"),
                    details=detail.get("details")
                )
                for detail in self.details
            ]
        
        return HTTPException(
            status_code=self.status_code,
            detail=ErrorResponse(
                error=self.error_code,
                message=self.message,
                details=error_details,
                request_id=None  # Will be filled by middleware
            ).dict(exclude_none=True)
        )


class ValidationError(APIError):
    """Validation error for invalid input data."""
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "validation_error"
    error_message = "Invalid input data"


class AuthenticationError(APIError):
    """Authentication error for invalid credentials."""
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "authentication_error"
    error_message = "Authentication failed"


class AuthorizationError(APIError):
    """Authorization error for insufficient permissions."""
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "authorization_error"
    error_message = "Insufficient permissions"


class NotFoundError(APIError):
    """Resource not found error."""
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "not_found"
    error_message = "Resource not found"


class ConflictError(APIError):
    """Conflict error for resource conflicts."""
    status_code = status.HTTP_409_CONFLICT
    error_code = "conflict"
    error_message = "Resource conflict"


class RateLimitError(APIError):
    """Rate limit exceeded error."""
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    error_code = "rate_limit_exceeded"
    error_message = "Rate limit exceeded"


class ServiceUnavailableError(APIError):
    """Service unavailable error."""
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    error_code = "service_unavailable"
    error_message = "Service temporarily unavailable"


# Error handler functions
def handle_api_error(error: Union[APIError, Exception]) -> HTTPException:
    """
    Convert any exception to an appropriate HTTPException.
    
    Args:
        error: The exception to handle
        
    Returns:
        HTTPException with standardized format
    """
    if isinstance(error, APIError):
        return error.to_http_exception()
    
    # Log unexpected errors
    logger.error(
        f"Unhandled exception: {str(error)}",
        exc_info=True,
        extra={
            "error_type": type(error).__name__,
            "traceback": traceback.format_exc()
        }
    )
    
    # Convert to internal server error
    internal_error = APIError(
        message=f"An unexpected error occurred: {str(error)}",
        log_exception=False  # Already logged above
    )
    return internal_error.to_http_exception()


def validation_error(
    message: str = "Invalid input data", 
    field: Optional[str] = None,
    code: str = "invalid_input",
    details: Optional[Dict[str, Any]] = None
) -> ValidationError:
    """
    Create a validation error.
    
    Args:
        message: Error message
        field: Field that caused the error
        code: Error code
        details: Additional error details
        
    Returns:
        ValidationError exception
    """
    error_details = [{
        "code": code,
        "message": message,
        "field": field,
        "details": details
    }]
    
    return ValidationError(
        message=message,
        details=error_details
    )


def not_found_error(
    resource_type: str,
    resource_id: str,
    message: Optional[str] = None
) -> NotFoundError:
    """
    Create a not found error.
    
    Args:
        resource_type: Type of resource not found
        resource_id: ID of resource not found
        message: Optional custom message
        
    Returns:
        NotFoundError exception
    """
    error_message = message or f"{resource_type} with ID '{resource_id}' not found"
    error_details = [{
        "code": "resource_not_found",
        "message": error_message,
        "details": {
            "resource_type": resource_type,
            "resource_id": resource_id
        }
    }]
    
    return NotFoundError(
        message=error_message,
        details=error_details
    )


# Error handler decorator
def error_handler(func):
    """
    Decorator to handle exceptions in API endpoints.
    
    Args:
        func: The endpoint function to wrap
        
    Returns:
        Wrapped function that handles exceptions
    """
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as exc:
            raise handle_api_error(exc)
    
    return wrapper
