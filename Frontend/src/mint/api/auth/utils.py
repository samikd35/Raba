#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Authentication Utility Functions.

This module provides utility functions for authentication operations, including
token validation, password handling, and security checks.
"""

import hashlib
import secrets
import string
import logging
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
import jwt
import re

from .models import (
    UserRole, AuthStatus, TokenType, AuthProvider, UserContext,
    AuthToken, AuthError, AUTH_ERROR_CODES, DEFAULT_ROLES
)

# Configure logging
logger = logging.getLogger(__name__)


def generate_secure_token(length: int = 32) -> str:
    """
    Generate a secure random token.
    
    Args:
        length: Length of the token
        
    Returns:
        str: Secure random token
    """
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def hash_password(password: str) -> str:
    """
    Hash a password using SHA-256.
    
    Args:
        password: Plain text password
        
    Returns:
        str: Hashed password
    """
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        password: Plain text password
        hashed_password: Hashed password
        
    Returns:
        bool: True if password matches
    """
    return hash_password(password) == hashed_password


def validate_email(email: str) -> bool:
    """
    Validate email address format.
    
    Args:
        email: Email address to validate
        
    Returns:
        bool: True if email is valid
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_password_strength(password: str) -> Dict[str, Any]:
    """
    Validate password strength.
    
    Args:
        password: Password to validate
        
    Returns:
        Dict: Validation result with score and feedback
    """
    result = {
        "is_valid": True,
        "score": 0,
        "feedback": [],
        "requirements": {
            "min_length": len(password) >= 8,
            "has_uppercase": any(c.isupper() for c in password),
            "has_lowercase": any(c.islower() for c in password),
            "has_digit": any(c.isdigit() for c in password),
            "has_special": any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
        }
    }
    
    # Calculate score
    score = 0
    for requirement, met in result["requirements"].items():
        if met:
            score += 1
        else:
            result["feedback"].append(f"Missing {requirement.replace('_', ' ')}")
    
    result["score"] = score
    
    # Determine if valid
    if len(password) < 8:
        result["is_valid"] = False
        result["feedback"].append("Password must be at least 8 characters long")
    
    if score < 3:
        result["is_valid"] = False
        result["feedback"].append("Password is too weak")
    
    return result


def generate_jwt_token(
    user_id: str,
    email: str,
    roles: List[UserRole],
    secret_key: str,
    expires_hours: int = 24
) -> str:
    """
    Generate a JWT token for a user.
    
    Args:
        user_id: User ID
        email: User email
        roles: User roles
        secret_key: JWT secret key
        expires_hours: Token expiry in hours
        
    Returns:
        str: JWT token
    """
    payload = {
        "user_id": user_id,
        "email": email,
        "roles": [role.value for role in roles],
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=expires_hours)
    }
    
    return jwt.encode(payload, secret_key, algorithm="HS256")


def decode_jwt_token(token: str, secret_key: str) -> Dict[str, Any]:
    """
    Decode a JWT token.
    
    Args:
        token: JWT token to decode
        secret_key: JWT secret key
        
    Returns:
        Dict: Decoded token payload
    """
    try:
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthError(
            error_code="TOKEN_EXPIRED",
            message="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise AuthError(
            error_code="TOKEN_INVALID",
            message="Invalid token"
        )


def check_permissions(user_roles: List[UserRole], required_permissions: List[str]) -> bool:
    """
    Check if user has required permissions.
    
    Args:
        user_roles: User's roles
        required_permissions: Required permissions
        
    Returns:
        bool: True if user has all required permissions
    """
    user_permissions = set()
    
    for role in user_roles:
        if role in DEFAULT_ROLES:
            user_permissions.update(DEFAULT_ROLES[role])
    
    return all(perm in user_permissions for perm in required_permissions)


def check_role_access(user_roles: List[UserRole], required_roles: List[UserRole]) -> bool:
    """
    Check if user has required roles.
    
    Args:
        user_roles: User's roles
        required_roles: Required roles
        
    Returns:
        bool: True if user has at least one required role
    """
    return any(role in user_roles for role in required_roles)


def sanitize_user_input(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize user input data.
    
    Args:
        input_data: Input data to sanitize
        
    Returns:
        Dict: Sanitized data
    """
    sanitized = {}
    
    for key, value in input_data.items():
        if isinstance(value, str):
            # Remove potentially dangerous characters
            sanitized[key] = re.sub(r'[<>"\']', '', value).strip()
        elif isinstance(value, dict):
            sanitized[key] = sanitize_user_input(value)
        else:
            sanitized[key] = value
    
    return sanitized


def extract_ip_address(request_headers: Dict[str, str]) -> Optional[str]:
    """
    Extract IP address from request headers.
    
    Args:
        request_headers: Request headers
        
    Returns:
        str: IP address or None
    """
    # Check various headers for IP address
    ip_headers = [
        'X-Forwarded-For',
        'X-Real-IP',
        'X-Client-IP',
        'CF-Connecting-IP'
    ]
    
    for header in ip_headers:
        if header in request_headers:
            ip = request_headers[header].split(',')[0].strip()
            if ip and ip != 'unknown':
                return ip
    
    return None


def is_suspicious_activity(
    user_id: str,
    ip_address: str,
    user_agent: str,
    activity_log: List[Dict[str, Any]]
) -> bool:
    """
    Check for suspicious activity patterns.
    
    Args:
        user_id: User ID
        ip_address: Current IP address
        user_agent: Current user agent
        activity_log: Recent activity log
        
    Returns:
        bool: True if activity is suspicious
    """
    if not activity_log:
        return False
    
    # Check for multiple IP addresses
    unique_ips = set(entry.get('ip_address') for entry in activity_log[-10:])
    if len(unique_ips) > 3:
        return True
    
    # Check for rapid requests
    recent_requests = [entry for entry in activity_log[-10:] 
                      if entry.get('timestamp', datetime.min) > datetime.utcnow() - timedelta(minutes=5)]
    if len(recent_requests) > 20:
        return True
    
    # Check for unusual user agents
    user_agents = set(entry.get('user_agent') for entry in activity_log[-10:])
    if len(user_agents) > 2:
        return True
    
    return False


def generate_password_reset_token() -> str:
    """
    Generate a secure password reset token.
    
    Returns:
        str: Password reset token
    """
    return generate_secure_token(32)


def validate_password_reset_token(token: str, expiry_hours: int = 1) -> bool:
    """
    Validate a password reset token.
    
    Args:
        token: Token to validate
        expiry_hours: Token expiry in hours
        
    Returns:
        bool: True if token is valid
    """
    # This would typically check against a database
    # For now, just check token format
    return len(token) == 32 and token.isalnum()


def create_auth_error(error_code: str, message: Optional[str] = None) -> AuthError:
    """
    Create an authentication error.
    
    Args:
        error_code: Error code
        message: Custom error message
        
    Returns:
        AuthError: Authentication error
    """
    if message is None:
        message = AUTH_ERROR_CODES.get(error_code, "Unknown error")
    
    return AuthError(
        error_code=error_code,
        message=message
    )


def format_auth_metrics(metrics_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format authentication metrics for display.
    
    Args:
        metrics_data: Raw metrics data
        
    Returns:
        Dict: Formatted metrics
    """
    formatted = {}
    
    for key, value in metrics_data.items():
        if isinstance(value, datetime):
            formatted[key] = value.isoformat()
        elif isinstance(value, (int, float)):
            formatted[key] = f"{value:,}"
        else:
            formatted[key] = value
    
    return formatted


def calculate_auth_score(user_context: UserContext) -> int:
    """
    Calculate authentication security score for a user.
    
    Args:
        user_context: User context
        
    Returns:
        int: Security score (0-100)
    """
    score = 0
    
    # Base score
    score += 20
    
    # Email verification
    if user_context.email and validate_email(user_context.email):
        score += 10
    
    # Active status
    if user_context.is_active:
        score += 10
    
    # Recent login
    if user_context.last_login and user_context.last_login > datetime.utcnow() - timedelta(days=30):
        score += 20
    
    # Role-based scoring
    if UserRole.SUPER_ADMIN in user_context.roles:
        score += 30
    elif UserRole.SUPPORT_ADMIN in user_context.roles:
        score += 25
    elif UserRole.BUSINESS_ANALYST in user_context.roles:
        score += 20
    elif UserRole.USER in user_context.roles:
        score += 15
    else:
        score += 5
    
    return min(score, 100)


def get_auth_status_message(status: AuthStatus) -> str:
    """
    Get human-readable status message.
    
    Args:
        status: Authentication status
        
    Returns:
        str: Status message
    """
    status_messages = {
        AuthStatus.AUTHENTICATED: "Successfully authenticated",
        AuthStatus.UNAUTHENTICATED: "Authentication required",
        AuthStatus.EXPIRED: "Session expired, please log in again",
        AuthStatus.REVOKED: "Access has been revoked",
        AuthStatus.PENDING: "Authentication pending"
    }
    
    return status_messages.get(status, "Unknown status")


def validate_auth_config(config: Dict[str, Any]) -> List[str]:
    """
    Validate authentication configuration.
    
    Args:
        config: Configuration to validate
        
    Returns:
        List: Validation errors
    """
    errors = []
    
    required_fields = ["jwt_secret", "jwt_expiry_hours"]
    for field in required_fields:
        if field not in config:
            errors.append(f"Missing required field: {field}")
    
    if "jwt_secret" in config and len(config["jwt_secret"]) < 32:
        errors.append("JWT secret must be at least 32 characters long")
    
    if "jwt_expiry_hours" in config and config["jwt_expiry_hours"] <= 0:
        errors.append("JWT expiry hours must be positive")
    
    return errors


