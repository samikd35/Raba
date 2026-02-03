"""
Compatibility shim for production auth imports.

Maintains backward-compatible import path `src.mint.api.production_auth_system`
by re-exporting symbols from the new implementation.

Role system removed - require_roles and require_admin no longer available.
Auth admin router removed - not essential for core functionality.
"""

from .auth.production.system import (
    ProductionAuthSystem,
    ProductionAuthMiddleware,
    ProductionAuthDependencies,
    AuthContext,
    AuthErrorCode,
    get_production_auth_system,
    get_production_auth_dependencies,
    get_current_user,
    get_auth_context,
    # auth_admin_router,  # Removed - not essential
)

__all__ = [
    "ProductionAuthSystem",
    "ProductionAuthMiddleware",
    "ProductionAuthDependencies",
    "AuthContext",
    "AuthErrorCode",
    "get_production_auth_system",
    "get_production_auth_dependencies",
    "get_current_user",
    "get_auth_context",
    "auth_admin_router",
]


