#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Authentication Models and Data Structures.

This module contains Pydantic models and data structures for authentication functionality,
including user authentication, authorization, and security monitoring.
"""

from enum import Enum
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from pydantic import BaseModel, Field


class AuthPatternType(str, Enum):
    """Types of authentication patterns found in endpoints."""
    NO_AUTH = "no_auth"
    API_KEY = "api_key"
    USER_TOKEN = "user_token"
    ADMIN_TOKEN = "admin_token"
    SERVICE_ROLE = "service_role"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class AuthProvider(str, Enum):
    """Authentication providers."""
    SUPABASE = "supabase"
    GOOGLE = "google"
    MICROSOFT = "microsoft"
    GITHUB = "github"
    CUSTOM = "custom"


class UserRole(str, Enum):
    """User roles in the system."""
    SUPER_ADMIN = "super_admin"
    SUPPORT_ADMIN = "support_admin"
    BUSINESS_ANALYST = "business_analyst"
    USER = "user"
    GUEST = "guest"


class AuthStatus(str, Enum):
    """Authentication status."""
    AUTHENTICATED = "authenticated"
    UNAUTHENTICATED = "unauthenticated"
    EXPIRED = "expired"
    REVOKED = "revoked"
    PENDING = "pending"


class TokenType(str, Enum):
    """Token types."""
    ACCESS = "access"
    REFRESH = "refresh"
    API_KEY = "api_key"
    SERVICE_ROLE = "service_role"


class EndpointInfo(BaseModel):
    """Information about an API endpoint."""
    file_path: str
    function_name: str
    route_path: str
    http_method: str
    auth_pattern: AuthPatternType
    auth_dependencies: List[str] = Field(default_factory=list)
    error_handling: List[str] = Field(default_factory=list)
    logging_patterns: List[str] = Field(default_factory=list)
    issues: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class UserContext(BaseModel):
    """User context for authentication."""
    user_id: str
    email: str
    roles: List[UserRole] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)
    is_active: bool = True
    last_login: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AuthToken(BaseModel):
    """Authentication token model."""
    token: str
    token_type: TokenType
    expires_at: datetime
    user_id: str
    provider: AuthProvider
    scopes: List[str] = Field(default_factory=list)
    is_revoked: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AuthRequest(BaseModel):
    """Authentication request model."""
    email: str
    password: Optional[str] = None
    provider: AuthProvider = AuthProvider.SUPABASE
    remember_me: bool = False
    redirect_url: Optional[str] = None


class AuthResponse(BaseModel):
    """Authentication response model."""
    success: bool
    user: Optional[UserContext] = None
    token: Optional[AuthToken] = None
    message: str
    error_code: Optional[str] = None
    redirect_url: Optional[str] = None


class AuthConsistencyReport(BaseModel):
    """Authentication consistency audit report."""
    summary: Dict[str, Any]
    detailed_findings: List[EndpointInfo]
    recommendations: List[str]
    audit_metadata: Dict[str, Any]


class SecurityAlert(BaseModel):
    """Security alert model."""
    alert_id: str
    alert_type: str
    severity: str
    description: str
    user_id: Optional[str] = None
    ip_address: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: Dict[str, Any] = Field(default_factory=dict)
    resolved: bool = False
    resolved_at: Optional[datetime] = None


class AuthConfig(BaseModel):
    """Authentication configuration."""
    jwt_secret: str
    jwt_expiry_hours: int = 24
    refresh_token_expiry_days: int = 30
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 15
    require_email_verification: bool = True
    require_mfa: bool = False
    allowed_origins: List[str] = Field(default_factory=list)
    session_timeout_minutes: int = 60


class AuthMetrics(BaseModel):
    """Authentication metrics."""
    total_users: int
    active_users: int
    failed_logins: int
    successful_logins: int
    locked_accounts: int
    password_resets: int
    mfa_enabled_users: int
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class AuthAuditLog(BaseModel):
    """Authentication audit log entry."""
    log_id: str
    user_id: Optional[str] = None
    action: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    success: bool
    error_message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: Dict[str, Any] = Field(default_factory=dict)


class AuthDependency(BaseModel):
    """Authentication dependency model."""
    name: str
    description: str
    required_roles: List[UserRole] = Field(default_factory=list)
    required_permissions: List[str] = Field(default_factory=list)
    is_deprecated: bool = False
    replacement: Optional[str] = None


class AuthError(BaseModel):
    """Authentication error model."""
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: Optional[str] = None


class AuthSession(BaseModel):
    """Authentication session model."""
    session_id: str
    user_id: str
    token: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    is_active: bool = True
    last_activity: datetime = Field(default_factory=datetime.utcnow)


class AuthProviderConfig(BaseModel):
    """Authentication provider configuration."""
    provider: AuthProvider
    client_id: str
    client_secret: str
    redirect_uri: str
    scopes: List[str] = Field(default_factory=list)
    enabled: bool = True
    config: Dict[str, Any] = Field(default_factory=dict)


class AuthValidationResult(BaseModel):
    """Authentication validation result."""
    is_valid: bool
    user: Optional[UserContext] = None
    error: Optional[AuthError] = None
    warnings: List[str] = Field(default_factory=list)


class AuthConsistencyIssue(BaseModel):
    """Authentication consistency issue."""
    issue_type: str
    severity: str
    description: str
    file_path: str
    function_name: str
    recommendation: str
    auto_fixable: bool = False


# Constants for authentication
DEFAULT_ROLES = {
    UserRole.SUPER_ADMIN: ["all"],
    UserRole.SUPPORT_ADMIN: ["user_management", "system_monitoring", "audit_logs"],
    UserRole.BUSINESS_ANALYST: ["analytics", "reports", "data_export"],
    UserRole.USER: ["profile", "reports", "basic_features"],
    UserRole.GUEST: ["public_content"]
}

AUTH_PATTERNS = {
    AuthPatternType.NO_AUTH: "No authentication required",
    AuthPatternType.API_KEY: "API key authentication",
    AuthPatternType.USER_TOKEN: "User token authentication",
    AuthPatternType.ADMIN_TOKEN: "Admin token authentication",
    AuthPatternType.SERVICE_ROLE: "Service role authentication",
    AuthPatternType.MIXED: "Mixed authentication patterns",
    AuthPatternType.UNKNOWN: "Unknown authentication pattern"
}

SECURITY_ALERT_TYPES = [
    "multiple_failed_logins",
    "suspicious_activity",
    "privilege_escalation",
    "unusual_location",
    "account_takeover_attempt",
    "brute_force_attack"
]

SEVERITY_LEVELS = ["low", "medium", "high", "critical"]

# Authentication error codes
AUTH_ERROR_CODES = {
    "INVALID_CREDENTIALS": "Invalid email or password",
    "ACCOUNT_LOCKED": "Account is temporarily locked",
    "ACCOUNT_DISABLED": "Account is disabled",
    "TOKEN_EXPIRED": "Authentication token has expired",
    "TOKEN_INVALID": "Invalid authentication token",
    "INSUFFICIENT_PERMISSIONS": "Insufficient permissions for this action",
    "MFA_REQUIRED": "Multi-factor authentication required",
    "EMAIL_NOT_VERIFIED": "Email address not verified",
    "RATE_LIMIT_EXCEEDED": "Too many requests, please try again later",
    "SESSION_EXPIRED": "Session has expired"
}

