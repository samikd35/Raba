"""
Async Auth service for high-performance API operations.

This is an optimized async version of AuthService that uses:
- Async Supabase client for non-blocking database operations

NOTE: User creation methods (create_user_profile, create_user_with_role,
get_or_create_google_user) are NOT included here because they depend on
TenantService and WaitlistService. Use sync AuthService for those until
AsyncTenantService is available.
"""

import logging
from typing import Any, Dict, List, Optional

from ..system.core.async_supabase_client import get_async_supabase_client
from .utils import hash_password

logger = logging.getLogger(__name__)

SAFE_USER_FIELDS = "id, email, full_name, avatar_url, timezone, preferences, bio, website, location, role, created_at"


class AsyncAuthService:
    """Async service for authentication and user management operations."""

    # =========================================================================
    # User Profile - Read Operations
    # =========================================================================

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a user profile by ID."""
        client = await get_async_supabase_client()

        try:
            result = await (
                client.table("user_profiles")
                .select(SAFE_USER_FIELDS)
                .eq("id", user_id)
                .limit(1)
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception:
            logger.exception(f"Failed to fetch user by id: {user_id}")
            raise

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Fetch a user profile by email."""
        client = await get_async_supabase_client()

        try:
            result = await (
                client.table("user_profiles")
                .select("*")
                .eq("email", email.lower().strip())
                .limit(1)
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception:
            logger.exception(f"Failed to fetch user by email: {email}")
            raise

    async def get_all_users(self) -> List[Dict[str, Any]]:
        """Fetch all user profiles."""
        client = await get_async_supabase_client()

        try:
            result = await (
                client.table("user_profiles")
                .select(SAFE_USER_FIELDS)
                .execute()
            )
            return result.data or []
        except Exception:
            logger.exception("Failed to fetch all users")
            raise

    async def get_users_by_ids(self, user_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Fetch multiple user profiles by IDs in a single query.
        OPTIMIZED: Batch fetch instead of N+1 queries.
        """
        if not user_ids:
            return []

        client = await get_async_supabase_client()

        try:
            result = await (
                client.table("user_profiles")
                .select(SAFE_USER_FIELDS)
                .in_("id", user_ids)
                .execute()
            )
            return result.data or []
        except Exception:
            logger.exception(f"Failed to fetch users by ids")
            raise

    # =========================================================================
    # User Profile - Write Operations
    # =========================================================================

    async def update_user_profile(
        self,
        user_id: str,
        updates: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Update user profile by ID."""
        client = await get_async_supabase_client()

        try:
            result = await (
                client.table("user_profiles")
                .update(updates)
                .eq("id", user_id)
                .select(SAFE_USER_FIELDS)
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception:
            logger.exception(f"Failed to update user profile: {user_id}")
            raise

    async def update_user_password(
        self,
        user_id: str,
        new_password: str,
    ) -> Optional[Dict[str, Any]]:
        """Update user password (hashed before saving)."""
        client = await get_async_supabase_client()

        try:
            password_hash = hash_password(new_password)
            result = await (
                client.table("user_profiles")
                .update({"password": password_hash})
                .eq("id", user_id)
                .select(SAFE_USER_FIELDS)
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception:
            logger.exception(f"Failed to update password for user: {user_id}")
            raise

    async def delete_user_profile(self, user_id: str) -> bool:
        """Delete user profile by ID."""
        client = await get_async_supabase_client()

        try:
            result = await (
                client.table("user_profiles")
                .delete()
                .eq("id", user_id)
                .execute()
            )
            return bool(result.data)
        except Exception:
            logger.exception(f"Failed to delete user profile: {user_id}")
            raise

    # =========================================================================
    # Tenant Operations
    # =========================================================================

    async def get_tenant_membership(
        self,
        tenant_id: str,
        user_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Fetch tenant membership for a given tenant_id and user_id."""
        client = await get_async_supabase_client()

        try:
            result = await (
                client.table("tenant_memberships")
                .select("id, tenant_id, user_id, role, is_active")
                .eq("tenant_id", tenant_id)
                .eq("user_id", user_id)
                .eq("is_active", True)
                .limit(1)
                .execute()
            )

            if result.data:
                return result.data[0]

            logger.debug(f"No active membership found for user {user_id} in tenant {tenant_id}")
            return None
        except Exception:
            logger.exception("Failed to fetch tenant membership")
            raise

    async def get_tenant_details(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Fetch tenant details by tenant ID."""
        client = await get_async_supabase_client()

        try:
            result = await (
                client.table("tenants")
                .select("*")
                .eq("id", tenant_id)
                .limit(1)
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception:
            logger.exception(f"Failed to fetch tenant details: {tenant_id}")
            raise

    async def get_user_tenants(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all tenants a user is a member of.
        Returns tenant details with membership role.
        """
        client = await get_async_supabase_client()

        try:
            result = await (
                client.table("tenant_memberships")
                .select("tenant_id, role, is_active, tenants!tenant_memberships_tenant_id_fkey(*)")
                .eq("user_id", user_id)
                .eq("is_active", True)
                .execute()
            )
            return result.data or []
        except Exception:
            logger.exception(f"Failed to fetch tenants for user: {user_id}")
            raise

    async def get_individual_tenant_for_user(
        self,
        user_id: str,
    ) -> Optional[str]:
        """
        Fetch the user's oldest active individual tenant (owned by the user).

        NOTE: This method does NOT auto-create a tenant if none exists.
        For auto-creation, use the sync AuthService which has TenantService dependency.
        """
        client = await get_async_supabase_client()

        try:
            # Find all active owned memberships (oldest first)
            membership_result = await (
                client.table("tenant_memberships")
                .select("tenant_id, created_at")
                .eq("user_id", user_id)
                .eq("role", "owner")
                .eq("is_active", True)
                .order("created_at", desc=False)
                .execute()
            )

            if not membership_result.data:
                return None

            # Check each membership for individual tenant type
            for membership in membership_result.data:
                tenant_result = await (
                    client.table("tenants")
                    .select("id")
                    .eq("id", membership["tenant_id"])
                    .eq("tenant_type", "individual")
                    .eq("is_active", True)
                    .limit(1)
                    .execute()
                )

                if tenant_result.data:
                    return tenant_result.data[0]["id"]

            return None
        except Exception:
            logger.exception(f"Failed to fetch individual tenant for user: {user_id}")
            raise

# Singleton instance
_async_auth_service: Optional[AsyncAuthService] = None


def get_async_auth_service() -> AsyncAuthService:
    """Get singleton async auth service instance."""
    global _async_auth_service
    if _async_auth_service is None:
        _async_auth_service = AsyncAuthService()
    return _async_auth_service
