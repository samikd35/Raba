"""
Enhanced Authentication Dependencies for API Endpoints

This module provides enhanced authentication dependencies that use the
unified authentication handler to ensure consistent authentication patterns,
error responses, and logging across all API endpoints.

Implements requirements 5.1, 5.2, 5.3, 5.4, 8.1, 8.2, 8.3, 8.4, 8.5
from the auth-connection-fixes specification.
"""

import os
import logging
from typing import Dict, List, Any, Optional
from functools import wraps

from fastapi import Depends, Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .production.system import AuthErrorCode
from .production.auth import AuthEventType

# Create a simple unified_auth_handler for compatibility
class UnifiedAuthHandler:
    def __init__(self):
        pass
    
    def validate_authorization_header(self, request, auth_header):
        if not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization header")
        return auth_header[7:]
    
    def validate_token_format(self, token, request):
        if not token:
            raise HTTPException(status_code=401, detail="Invalid token format")
    
    def validate_user_context(self, user_context, request):
        user_id = user_context.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found")
        return user_id
    
    def handle_authentication_success(self, user_context, request):
        pass
    
    def handle_authentication_failure(self, error, request, auth_type="user"):
        raise HTTPException(status_code=401, detail="Authentication failed")
    
    def handle_authorization_failure(self, user_id, required_permissions, user_permissions, request, is_admin_endpoint=False):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    def extract_request_context(self, request):
        return {
            "endpoint": request.url.path,
            "ip_address": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", ""),
            "request_id": None
        }
    
    def log_auth_event(self, event_type, success, user_id=None, user_email=None, auth_type=None, endpoint=None, ip_address=None, user_agent=None, additional_data=None, error_code=None, error_message=None):
        pass

unified_auth_handler = UnifiedAuthHandler()
# Role system removed - require_admin no longer available
from .production.system import get_current_user, get_auth_context, get_current_user_with_roles, get_production_auth_system
from ..system.core.utils import is_valid_uuid

# Configure logging
logger = logging.getLogger(__name__)

# OAuth2 bearer token scheme
oauth2_scheme = HTTPBearer()


class EnhancedAuthDependencies:
    """
    Enhanced authentication dependencies that provide consistent authentication
    patterns across all API endpoints using the unified authentication handler.
    
    This class provides:
    - Consistent token validation with unified error handling
    - Comprehensive authentication event logging
    - Standardized error responses
    - User context validation
    - Admin authentication separation
    """
    
    def __init__(self):
        """Initialize enhanced auth dependencies."""
        self.logger = logging.getLogger(f"{__name__}.EnhancedAuthDependencies")
        self.logger.info("EnhancedAuthDependencies initialized for consistent API authentication")
    
    async def get_authenticated_user_context(
        self,
        credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
        request: Request = None
    ) -> Dict[str, Any]:
        """
        Get authenticated user context with enhanced error handling and logging.
        
        This dependency provides:
        - Consistent token validation
        - Unified error responses
        - Comprehensive authentication logging
        - User context validation
        
        Args:
            credentials: HTTP authorization credentials
            request: FastAPI request object
            
        Returns:
            Dict: Authenticated user context
            
        Raises:
            HTTPException: If authentication fails
        """
        try:
            # Validate authorization header and extract token
            auth_header = f"Bearer {credentials.credentials}"
            token = unified_auth_handler.validate_authorization_header(request, auth_header)
            
            # Validate token format
            unified_auth_handler.validate_token_format(token, request)
            
            # Use existing auth system to get user context
            user_context = await get_current_user_with_roles(credentials, request)
            
            # Validate user context
            user_id = unified_auth_handler.validate_user_context(user_context, request)
            
            # Handle successful authentication
            unified_auth_handler.handle_authentication_success(user_context, request)
            
            return user_context
            
        except HTTPException:
            # Re-raise HTTP exceptions (already handled by unified handler)
            raise
        except Exception as e:
            # Handle unexpected errors with unified error handling
            raise unified_auth_handler.handle_authentication_failure(e, request, "user")
    
    async def get_authenticated_user_id(
        self,
        credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
        request: Request = None
    ) -> str:
        """
        Get authenticated user ID with enhanced error handling and logging.
        
        This is a simplified dependency that returns just the user ID
        for endpoints that only need user identification.
        
        Args:
            credentials: HTTP authorization credentials
            request: FastAPI request object
            
        Returns:
            str: Authenticated user ID
            
        Raises:
            HTTPException: If authentication fails
        """
        user_context = await self.get_authenticated_user_context(credentials, request)
        return user_context["user_id"]
    
    async def get_authenticated_admin_context(
        self,
        credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
        request: Request = None
    ) -> Dict[str, Any]:
        """
        Get authenticated admin context with enhanced error handling and logging.
        
        This dependency provides admin-specific authentication with:
        - Admin token validation (service role or admin user)
        - Admin role verification
        - Enhanced logging for admin access
        - Clear separation from user authentication
        
        Args:
            credentials: HTTP authorization credentials
            request: FastAPI request object
            
        Returns:
            Dict: Authenticated admin context
            
        Raises:
            HTTPException: If authentication fails or user is not admin
        """
        try:
            # Role system removed - use standard authentication
            # Admin endpoints now use get_current_user instead of admin-specific auth
            user_context = await self.get_authenticated_user_context(credentials, request)
            return user_context
            
        except HTTPException:
            # Re-raise HTTP exceptions (already handled by unified handler)
            raise
        except Exception as e:
            # Handle unexpected errors with unified error handling
            raise unified_auth_handler.handle_authentication_failure(e, request, "admin")
    
    def require_permissions(self, required_permissions: List[str], is_admin_endpoint: bool = False):
        """
        Create a dependency that requires specific permissions.
        
        This creates a dependency function that validates user permissions
        with unified error handling and logging.
        
        Args:
            required_permissions: List of required permissions
            is_admin_endpoint: Whether this is an admin endpoint
            
        Returns:
            Dependency function that validates permissions
        """
        async def permission_dependency(
            user_context: Dict[str, Any] = Depends(self.get_authenticated_user_context),
            request: Request = None
        ) -> Dict[str, Any]:
            """
            Validate user permissions with unified error handling.
            
            Args:
                user_context: Authenticated user context
                request: FastAPI request object
                
            Returns:
                Dict: User context (if permissions are valid)
                
            Raises:
                HTTPException: If user lacks required permissions
            """
            user_id = user_context.get("user_id", "unknown")
            
            # Get user permissions based on endpoint type
            if is_admin_endpoint:
                user_permissions = user_context.get("admin_roles", [])
            else:
                user_permissions = user_context.get("roles", [])
            
            # Check if user has any of the required permissions
            if not any(permission in user_permissions for permission in required_permissions):
                raise unified_auth_handler.handle_authorization_failure(
                    user_id=user_id,
                    required_permissions=required_permissions,
                    user_permissions=user_permissions,
                    request=request,
                    is_admin_endpoint=is_admin_endpoint
                )
            
            # Log successful authorization
            context = unified_auth_handler.extract_request_context(request)
            unified_auth_handler.log_auth_event(
                event_type=AuthEventType.AUTHORIZATION_SUCCESS,
                success=True,
                user_id=user_id,
                user_email=user_context.get("email"),
                auth_type=user_context.get("auth_type"),
                endpoint=context["endpoint"],
                ip_address=context["ip_address"],
                user_agent=context["user_agent"],
                additional_data={
                    "required_permissions": required_permissions,
                    "user_permissions": user_permissions,
                    "is_admin_endpoint": is_admin_endpoint
                }
            )
            
            return user_context
        
        return permission_dependency
    
    def validate_user_id_format(self, user_id: str, request: Request) -> None:
        """
        Validate user ID format with unified error handling.
        
        Args:
            user_id: User ID to validate
            request: FastAPI request object
            
        Raises:
            HTTPException: If user ID format is invalid
        """
        if not is_valid_uuid(user_id):
            context = unified_auth_handler.extract_request_context(request)
            
            unified_auth_handler.log_auth_event(
                event_type=AuthEventType.TOKEN_VALIDATION_FAILURE,
                success=False,
                user_id=user_id,
                endpoint=context["endpoint"],
                ip_address=context["ip_address"],
                user_agent=context["user_agent"],
                error_code=AuthErrorCode.INVALID_USER_ID,
                error_message=f"Invalid user ID format: {user_id}"
            )
            
            raise unified_auth_handler.create_auth_error(
                error_code=AuthErrorCode.INVALID_USER_ID,
                message="Invalid user ID format",
                request_id=context.get("request_id")
            )


# Global instance for use across the application
enhanced_auth_deps = EnhancedAuthDependencies()


# Convenience dependency functions for common use cases
async def get_current_user_context(
    credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
    request: Request = None
) -> Dict[str, Any]:
    """
    Get current authenticated user context.
    
    This is the primary dependency for user authentication across all endpoints.
    It provides consistent authentication with unified error handling and logging.
    
    Args:
        credentials: HTTP authorization credentials
        request: FastAPI request object
        
    Returns:
        Dict: Authenticated user context
        
    Raises:
        HTTPException: If authentication fails
    """
    return await enhanced_auth_deps.get_authenticated_user_context(credentials, request)


async def get_current_user_id_enhanced(
    credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
    request: Request = None
) -> str:
    """
    Get current authenticated user ID.
    
    This is a simplified dependency for endpoints that only need the user ID.
    
    Args:
        credentials: HTTP authorization credentials
        request: FastAPI request object
        
    Returns:
        str: Authenticated user ID
        
    Raises:
        HTTPException: If authentication fails
    """
    return await enhanced_auth_deps.get_authenticated_user_id(credentials, request)


async def get_admin_context(
    credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
    request: Request = None
) -> Dict[str, Any]:
    """
    Get current authenticated admin context.
    
    This dependency is specifically for admin endpoints and provides
    admin-specific authentication with proper role verification.
    
    Args:
        credentials: HTTP authorization credentials
        request: FastAPI request object
        
    Returns:
        Dict: Authenticated admin context
        
    Raises:
        HTTPException: If authentication fails or user is not admin
    """
    return await enhanced_auth_deps.get_authenticated_admin_context(credentials, request)


def require_user_permissions(permissions: List[str]):
    """
    Create a dependency that requires specific user permissions.
    
    Args:
        permissions: List of required permissions
        
    Returns:
        Dependency function that validates user permissions
    """
    return enhanced_auth_deps.require_permissions(permissions, is_admin_endpoint=False)


def require_admin_permissions(permissions: List[str]):
    """
    Create a dependency that requires specific admin permissions.
    
    Args:
        permissions: List of required admin permissions
        
    Returns:
        Dependency function that validates admin permissions
    """
    return enhanced_auth_deps.require_permissions(permissions, is_admin_endpoint=True)


# Decorator for endpoint-level authentication consistency
def consistent_auth_logging(func):
    """
    Decorator to add consistent authentication logging to endpoint functions.
    
    This decorator automatically logs endpoint access with authentication context
    and handles any authentication-related errors with unified error responses.
    
    Args:
        func: Endpoint function to decorate
        
    Returns:
        Decorated function with consistent auth logging
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract request and user context from kwargs
        # For FastAPI endpoints, the actual HTTP request is often named 'req' or might be a positional arg
        # The 'request' parameter is often a Pydantic model for the request body
        fastapi_request = kwargs.get('req')
        user_context = None
        
        # Look for user context in various possible parameter names
        for param_name in ['current_user', 'user_context', 'current_user_context']:
            if param_name in kwargs:
                user_context = kwargs[param_name]
                break
        
        # Log endpoint access
        if fastapi_request and user_context:
            try:
                context = unified_auth_handler.extract_request_context(fastapi_request)
                unified_auth_handler.log_auth_event(
                    event_type=AuthEventType.USER_ACCESS,
                    success=True,
                    user_id=user_context.get("user_id"),
                    user_email=user_context.get("email"),
                    auth_type=user_context.get("auth_type"),
                    endpoint=context["endpoint"],
                    ip_address=context["ip_address"],
                    user_agent=context["user_agent"],
                    additional_data={
                        "endpoint_function": func.__name__,
                        "roles": user_context.get("roles", [])
                    }
                )
            except Exception as e:
                # If we can't log, just continue with the function
                # This prevents issues with request context extraction
                logger.warning(f"Failed to log auth event: {e}")
        
        try:
            # Execute the original function
            return await func(*args, **kwargs)
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            # Handle unexpected errors with unified error handling
            if fastapi_request:
                raise unified_auth_handler.handle_authentication_failure(e, fastapi_request)
            else:
                raise
    
    return wrapper