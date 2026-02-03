#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Authentication Module for MINT.

This module provides comprehensive authentication functionality for the MINT system,
including user authentication, authorization, security monitoring, and consistency auditing.

Module Structure:
- models: Pydantic models and data structures
- core: Core authentication functionality
- handler: Unified authentication handler
- dependencies: Enhanced authentication dependencies
- consistency: Authentication consistency auditing
- production: Production-ready authentication
- utils: Utility functions and helpers
"""

from .models import (
    # Enums
    AuthPatternType, AuthProvider, UserRole, AuthStatus, TokenType,
    
    # Core Models
    EndpointInfo, UserContext, AuthToken, AuthRequest, AuthResponse,
    AuthConsistencyReport, SecurityAlert, AuthConfig, AuthMetrics,
    AuthAuditLog, AuthDependency, AuthError, AuthSession,
    AuthProviderConfig, AuthValidationResult, AuthConsistencyIssue,
    
    # Constants
    DEFAULT_ROLES, AUTH_PATTERNS, SECURITY_ALERT_TYPES, SEVERITY_LEVELS,
    AUTH_ERROR_CODES
)
from .utils import (
    # Token and Password Functions
    generate_secure_token, hash_password, verify_password, validate_email,
    validate_password_strength, generate_jwt_token, decode_jwt_token,
    
    # Permission and Role Functions
    check_permissions, check_role_access, sanitize_user_input,
    
    # Security Functions
    extract_ip_address, is_suspicious_activity, generate_password_reset_token,
    validate_password_reset_token, create_auth_error,
    
    # Utility Functions
    format_auth_metrics, calculate_auth_score, get_auth_status_message,
    validate_auth_config
)
from .consistency import AuthConsistencyAuditor
from .production import ProductionAuthSystem, ProductionAuth
from .core import auth_router

__all__ = [
    # Enums
    "AuthPatternType",
    "AuthProvider",
    "UserRole",
    "AuthStatus",
    "TokenType",
    
    # Core Models
    "EndpointInfo",
    "UserContext",
    "AuthToken",
    "AuthRequest",
    "AuthResponse",
    "AuthConsistencyReport",
    "SecurityAlert",
    "AuthConfig",
    "AuthMetrics",
    "AuthAuditLog",
    "AuthDependency",
    "AuthError",
    "AuthSession",
    "AuthProviderConfig",
    "AuthValidationResult",
    "AuthConsistencyIssue",
    
    # Constants
    "DEFAULT_ROLES",
    "AUTH_PATTERNS",
    "SECURITY_ALERT_TYPES",
    "SEVERITY_LEVELS",
    "AUTH_ERROR_CODES",
    
    # Token and Password Functions
    "generate_secure_token",
    "hash_password",
    "verify_password",
    "validate_email",
    "validate_password_strength",
    "generate_jwt_token",
    "decode_jwt_token",
    
    # Permission and Role Functions
    "check_permissions",
    "check_role_access",
    "sanitize_user_input",
    
    # Security Functions
    "extract_ip_address",
    "is_suspicious_activity",
    "generate_password_reset_token",
    "validate_password_reset_token",
    "create_auth_error",
    
    # Utility Functions
    "format_auth_metrics",
    "calculate_auth_score",
    "get_auth_status_message",
    "validate_auth_config",
    
    # Consistency Auditing
    "AuthConsistencyAuditor",
    
    # Production
    "ProductionAuthSystem",
    "ProductionAuth",
    # Routers
    "auth_router"
]


