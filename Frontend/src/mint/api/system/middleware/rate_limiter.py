"""
Rate limiting middleware for admin endpoints.

This module provides rate limiting functionality to protect admin endpoints
from brute force attacks and abuse.
"""

import time
import logging
from typing import Dict, List, Tuple, Optional, Any
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

# Configure logging
logger = logging.getLogger(__name__)

class RateLimiter:
    """In-memory rate limiter implementation."""
    
    def __init__(self, window_size: int = 60, max_requests: int = 100):
        """
        Initialize the rate limiter.
        
        Args:
            window_size: Time window in seconds
            max_requests: Maximum number of requests allowed in the window
        """
        self.window_size = window_size
        self.max_requests = max_requests
        self.requests: Dict[str, List[float]] = {}
    
    def is_rate_limited(self, key: str) -> Tuple[bool, int]:
        """
        Check if a key is rate limited.
        
        Args:
            key: The key to check (usually IP address or user ID)
            
        Returns:
            Tuple of (is_limited, remaining_requests)
        """
        current_time = time.time()
        
        # Initialize if key doesn't exist
        if key not in self.requests:
            self.requests[key] = []
        
        # Remove timestamps outside the window
        self.requests[key] = [ts for ts in self.requests[key] if current_time - ts <= self.window_size]
        
        # Check if rate limited
        is_limited = len(self.requests[key]) >= self.max_requests
        remaining = max(0, self.max_requests - len(self.requests[key]))
        
        # Add current request timestamp if not limited
        if not is_limited:
            self.requests[key].append(current_time)
        
        return is_limited, remaining
    
    def cleanup(self):
        """Remove expired entries to prevent memory leaks."""
        current_time = time.time()
        for key in list(self.requests.keys()):
            self.requests[key] = [ts for ts in self.requests[key] if current_time - ts <= self.window_size]
            if not self.requests[key]:
                del self.requests[key]


class AdminRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware for rate limiting admin endpoints.
    
    This middleware applies stricter rate limits to admin endpoints to prevent
    brute force attacks and unauthorized access attempts.
    """
    
    def __init__(
        self, 
        app, 
        admin_window_size: int = 60,
        admin_max_requests: int = 30,
        login_window_size: int = 300,
        login_max_requests: int = 5,
        exclude_paths: List[str] = None
    ):
        """
        Initialize the admin rate limit middleware.
        
        Args:
            app: The FastAPI application
            admin_window_size: Time window in seconds for admin endpoints
            admin_max_requests: Maximum requests allowed in the window for admin endpoints
            login_window_size: Time window in seconds for login endpoints
            login_max_requests: Maximum requests allowed in the window for login endpoints
            exclude_paths: List of paths to exclude from rate limiting
        """
        super().__init__(app)
        self.admin_limiter = RateLimiter(admin_window_size, admin_max_requests)
        self.login_limiter = RateLimiter(login_window_size, login_max_requests)
        self.exclude_paths = exclude_paths or ["/docs", "/openapi.json", "/health"]
        
        # Schedule periodic cleanup
        self.last_cleanup = time.time()
        self.cleanup_interval = 300  # 5 minutes
    
    async def dispatch(self, request: Request, call_next: Any) -> Any:
        """
        Process the request, applying rate limiting for admin endpoints.
        
        Args:
            request: The incoming request
            call_next: The next middleware or route handler
            
        Returns:
            Any: The response from the next handler
        """
        path = request.url.path
        
        # Skip rate limiting for excluded paths
        if any(path.startswith(excluded) for excluded in self.exclude_paths):
            return await call_next(request)
        
        # Get client IP address
        client_ip = request.client.host if request.client else "unknown"
        
        # Run cleanup periodically
        current_time = time.time()
        if current_time - self.last_cleanup > self.cleanup_interval:
            self.admin_limiter.cleanup()
            self.login_limiter.cleanup()
            self.last_cleanup = current_time
        
        # Apply stricter rate limiting for login attempts
        if (path.endswith("/login") or path.endswith("/token") or 
            path.endswith("/auth/callback") or path.endswith("/auth/signin")):
            is_limited, remaining = self.login_limiter.is_rate_limited(client_ip)
            if is_limited:
                logger.warning(f"Rate limit exceeded for login attempt from IP: {client_ip}")
                raise HTTPException(
                    status_code=429,
                    detail={
                        "code": "rate_limit_exceeded",
                        "message": "Too many login attempts. Please try again later.",
                        "retry_after": self.login_limiter.window_size
                    }
                )
        
        # Apply rate limiting for admin endpoints
        if path.startswith("/api/admin/"):
            is_limited, remaining = self.admin_limiter.is_rate_limited(client_ip)
            if is_limited:
                logger.warning(f"Rate limit exceeded for admin endpoint from IP: {client_ip}")
                raise HTTPException(
                    status_code=429,
                    detail={
                        "code": "rate_limit_exceeded",
                        "message": "Rate limit exceeded for admin endpoints. Please try again later.",
                        "retry_after": self.admin_limiter.window_size
                    }
                )
        
        # Continue processing the request
        response = await call_next(request)
        
        # Add rate limit headers to response
        if path.startswith("/api/admin/"):
            _, remaining = self.admin_limiter.is_rate_limited(client_ip)
            response.headers["X-RateLimit-Limit"] = str(self.admin_limiter.max_requests)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(int(time.time() + self.admin_limiter.window_size))
        
        return response