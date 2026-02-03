"""
IP whitelisting middleware for super admin access.

This module provides IP-based access control for super admin endpoints,
restricting access to specific trusted IP addresses.
"""

import os
import logging
from typing import List, Optional, Any
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from ...audit.service import audit_service, AuditLogAction, AuditLogTargetType

# Configure logging
logger = logging.getLogger(__name__)

class IPWhitelistMiddleware(BaseHTTPMiddleware):
    """
    Middleware for IP whitelisting super admin access.
    
    This middleware restricts access to super admin endpoints to a list of
    trusted IP addresses, providing an additional layer of security.
    """
    
    def __init__(
        self, 
        app, 
        whitelist: List[str] = None,
        super_admin_paths: List[str] = None,
        exclude_paths: List[str] = None
    ):
        """
        Initialize the IP whitelist middleware.
        
        Args:
            app: The FastAPI application
            whitelist: List of trusted IP addresses
            super_admin_paths: List of paths that require super admin access
            exclude_paths: List of paths to exclude from IP whitelisting
        """
        super().__init__(app)
        
        # Load whitelist from environment if not provided
        if whitelist is None:
            env_whitelist = os.getenv("SUPER_ADMIN_IP_WHITELIST", "")
            whitelist = [ip.strip() for ip in env_whitelist.split(",") if ip.strip()]
        
        self.whitelist = whitelist
        
        # Default super admin paths if not provided
        self.super_admin_paths = super_admin_paths or [
            "/api/admin/infrastructure/",
            "/api/admin/settings/",
            "/api/admin/auth/roles",
            "/api/admin/system/maintenance"
        ]
        
        self.exclude_paths = exclude_paths or ["/docs", "/openapi.json", "/health"]
        
        logger.info(f"IP whitelist configured with {len(self.whitelist)} trusted IPs")
    
    async def dispatch(self, request: Request, call_next: Any) -> Any:
        """
        Process the request, applying IP whitelisting for super admin endpoints.
        
        Args:
            request: The incoming request
            call_next: The next middleware or route handler
            
        Returns:
            Any: The response from the next handler
        """
        path = request.url.path
        
        # Skip IP whitelisting for excluded paths
        if any(path.startswith(excluded) for excluded in self.exclude_paths):
            return await call_next(request)
        
        # Check if path requires super admin access
        requires_super_admin = any(path.startswith(admin_path) for admin_path in self.super_admin_paths)
        
        if requires_super_admin:
            # Get client IP address
            client_ip = request.client.host if request.client else "unknown"
            
            # Check if IP is in whitelist
            if not self.whitelist or client_ip not in self.whitelist:
                # Log the unauthorized access attempt
                logger.warning(f"Unauthorized super admin access attempt from IP: {client_ip}, path: {path}")
                
                # Get user ID if available
                user_id = getattr(request.state, "user_id", "unknown")
                
                # Log to audit service
                try:
                    await audit_service.log_action(
                        admin_user_id=user_id,
                        action=AuditLogAction.USER_ROLE_ADD,  # Using this as a proxy for access attempt
                        target_type=AuditLogTargetType.SYSTEM,
                        details={
                            "message": "Unauthorized super admin access attempt",
                            "path": path,
                            "ip_address": client_ip
                        },
                        ip_address=client_ip,
                        user_agent=request.headers.get("user-agent"),
                        success=False,
                        error_message="IP address not in whitelist"
                    )
                except Exception as e:
                    logger.error(f"Failed to log audit event: {str(e)}")
                
                # Return 403 Forbidden
                raise HTTPException(
                    status_code=403,
                    detail={
                        "code": "ip_not_whitelisted",
                        "message": "Access to super admin functionality is restricted to whitelisted IP addresses."
                    }
                )
            
            # Log successful access
            logger.info(f"Super admin access granted from whitelisted IP: {client_ip}, path: {path}")
        
        # Continue processing the request
        return await call_next(request)


def get_trusted_ips() -> List[str]:
    """
    Get the list of trusted IP addresses from environment variables.
    
    Returns:
        List[str]: List of trusted IP addresses
    """
    env_whitelist = os.getenv("SUPER_ADMIN_IP_WHITELIST", "")
    return [ip.strip() for ip in env_whitelist.split(",") if ip.strip()]