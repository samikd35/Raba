import logging
from datetime import datetime, timedelta
from datetime import timezone as tz
from decimal import Decimal

from ..credit.service import CreditService
from ..system.core.supabase_client import get_supabase_client
from ..tenant.models import TenantCreate
from ..tenant.service import TenantService
from .utils import hash_password
from .waitlist_service import WaitlistService

logger = logging.getLogger(__name__)
SAFE_USER_FIELDS = "id, email, full_name, avatar_url, timezone, preferences, bio, website, location, role, created_at"

credit_service = CreditService()


class AuthService:
    """Service for tenant management operations"""

    def __init__(self, use_service_role: bool = True):
        """Initialize tenant service with Supabase client"""
        self.supabase = get_supabase_client(use_service_role=use_service_role).client
        self.use_service_role = use_service_role
        self.tenant_service = TenantService()

    async def create_user_profile(
        self,
        email: str,
        password: str,
        full_name: str = None,
        avatar_url: str = None,
        timezone: str = "UTC",
        preferences: dict = None,
        bio: str = None,
        website: str = None,
        location: str = None,
    ):
        """Insert a new user profile into Supabase"""
        try:
            password_hash = hash_password(password)

            response = (
                self.supabase.table("user_profiles")
                .insert(
                    {
                        "email": email,
                        "password": password_hash,
                        "full_name": full_name,
                        "avatar_url": avatar_url,
                        "timezone": timezone,
                        "preferences": preferences or {},
                        "bio": bio,
                        "website": website,
                        "location": location,
                        "role": "user",  # default role
                    }
                )
                .execute()
            )

            if not response.data:
                raise Exception("User creation failed")

            user = response.data[0]
            user_id = user["id"]

            # === Create Tenant ===
            tenant_data = TenantCreate(
                name=f"{(full_name or 'user').split()[0].lower()}-{str(user_id).split('-')[0]}-ind",
                tenant_type="individual",
                description=f"Personal tenant for {full_name or email}",
                settings={},
            )

            tenant_resp = await self.tenant_service.create_tenant(
                tenant_data, owner_user_id=user_id
            )

            # --- ADD: allocate signup trial credits (40 credits for 2 weeks) ---
            tenant_id = (
                tenant_resp.data.id
                if tenant_resp and tenant_resp.success and tenant_resp.data
                else None
            )

            if tenant_id:
                now_utc = datetime.now(tz.utc)
                trial_start = now_utc.isoformat()
                trial_end = (now_utc + timedelta(days=14)).isoformat()

                # Free trial: 40 credits active immediately, lasts 2 weeks
                credit_service.create_credit_lot(
                    tenant_id=str(tenant_id),
                    original_tenant_id=str(tenant_id),
                    source="trial",
                    credit_amount=Decimal("40"),
                    valid_from=trial_start,
                    expires_at=trial_end,
                    metadata={"reason": "signup_bonus"},
                )

                # Check waitlist and apply bonus credits if applicable
                try:
                    waitlist_svc = WaitlistService()
                    waitlist_bonus = waitlist_svc.check_and_apply_waitlist_bonus(
                        email=email,
                        tenant_id=str(tenant_id),
                        user_id=str(user_id),
                    )
                    if waitlist_bonus:
                        logger.info(f"Applied waitlist bonus for {email}: {waitlist_bonus}")
                except Exception as e:
                    # Don't fail signup if waitlist check fails
                    logger.error(f"Failed to check/apply waitlist bonus: {e}")

            return {k: v for k, v in user.items() if k != "password"}
        except Exception:
            logger.exception("Failed to create user profile")
            raise

    def get_user_by_email(self, email: str):
        """Fetch a user profile by email from Supabase"""
        try:
            response = (
                self.supabase.table("user_profiles")
                .select("*")
                .eq("email", email)
                .execute()
            )
            return response.data[0] if response.data else None
        except Exception:
            logger.exception("Failed to fetch user profile")
            raise

    async def create_user_with_role(
        self,
        email: str,
        password: str,
        role: str = "user",
        full_name: str = None,
        avatar_url: str = None,
        timezone: str = "UTC",
        preferences: dict = None,
        bio: str = None,
        website: str = None,
        location: str = None,
    ):
        """Super admin creates a new user with a specific role"""
        try:
            # Check if user exists
            existing = self.get_user_by_email(email)
            if existing:
                raise Exception("Email is already registered")

            password_hash = hash_password(password)

            response = (
                self.supabase.table("user_profiles")
                .insert(
                    {
                        "email": email,
                        "password": password_hash,
                        "full_name": full_name,
                        "avatar_url": avatar_url,
                        "timezone": timezone,
                        "preferences": preferences or {},
                        "bio": bio,
                        "website": website,
                        "location": location,
                        "role": role,
                    }
                )
                .execute()
            )

            if not response.data:
                raise Exception("Failed to create user")

            user = response.data[0]
            user_id = user["id"]

            # === Create Tenant ===
            tenant_data = TenantCreate(
                name=f"{(full_name or 'user').split()[0].lower()}-{str(user_id).split('-')[0]}-ind",
                tenant_type="individual",
                description=f"Personal tenant for {full_name or email}",
                settings={},
            )

            await self.tenant_service.create_tenant(tenant_data, owner_user_id=user_id)

            return {k: v for k, v in user.items() if k != "password"}
        except Exception:
            logger.exception("Failed to create user with role")
            raise

    async def get_or_create_google_user(
        self,
        email: str,
        password: str,
        full_name: str = None,
        avatar_url: str = None,
    ):
        """
        Check if user exists, if not create them with role 'user'.
        """
        try:
            user = self.get_user_by_email(email)
            if user:
                tenant_id = await self.get_individual_tenant_for_user(user["id"])
                tenant = self.get_tenant_details(tenant_id) if tenant_id else None
                tenant_type = tenant.get("tenant_type") if tenant else None
                return user, tenant_id, tenant_type

            # Create new user without password
            response = (
                self.supabase.table("user_profiles")
                .insert(
                    {
                        "email": email,
                        "password": hash_password(password),
                        "full_name": full_name,
                        "avatar_url": avatar_url,
                        "timezone": "UTC",
                        "preferences": {},
                        "role": "user",
                    }
                )
                .execute()
            )

            if not response.data:
                raise Exception("Failed to create Google user")

            user = response.data[0]
            user_id = user["id"]

            # === Create Tenant ===
            tenant_data = TenantCreate(
                name=f"{(full_name or 'user').split()[0].lower()}-{str(user_id).split('-')[0]}-ind",
                tenant_type="individual",
                description=f"Personal tenant for {full_name or email}",
                settings={},
            )

            tenant_response = await self.tenant_service.create_tenant(
                tenant_data, owner_user_id=user_id
            )
            tenant_id = (
                tenant_response.data.id
                if tenant_response and tenant_response.success and tenant_response.data
                else None
            )
            tenant_type = tenant_data.tenant_type if tenant_id else None

            if tenant_id:
                now_utc = datetime.now(tz.utc)
                trial_start = now_utc.isoformat()
                trial_end = (now_utc + timedelta(days=7)).isoformat()

                # Free trial: 30 credits active immediately, lasts 1 week
                credit_service.create_credit_lot(
                    tenant_id=tenant_id,
                    original_tenant_id=tenant_id,
                    source="trial",
                    credit_amount=Decimal("30"),
                    valid_from=trial_start,
                    expires_at=trial_end,
                    metadata={"reason": "signup_bonus"},
                )

                # Check waitlist and apply bonus credits if applicable
                try:
                    waitlist_svc = WaitlistService()
                    waitlist_bonus = waitlist_svc.check_and_apply_waitlist_bonus(
                        email=email,
                        tenant_id=str(tenant_id),
                        user_id=str(user["id"]),
                    )
                    if waitlist_bonus:
                        logger.info(f"Applied waitlist bonus for {email}: {waitlist_bonus}")
                except Exception as e:
                    # Don't fail signup if waitlist check fails
                    logger.error(f"Failed to check/apply waitlist bonus: {e}")

            return user, tenant_id, tenant_type
        except Exception:
            logger.exception("Failed to get or create Google user")
            raise

    def update_user_profile(self, user_id: str, updates: dict):
        """Update user profile by ID"""
        try:
            response = (
                self.supabase.table("user_profiles")
                .update(updates)
                .eq("id", user_id)
                .execute()
            )
            return (
                {k: v for k, v in response.data[0].items() if k != "password"}
                if response.data
                else None
            )
        except Exception:
            logger.exception("Failed to update user profile")
            raise

    def delete_user_profile(self, user_id: str):
        """Delete user profile by ID"""
        try:
            response = (
                self.supabase.table("user_profiles")
                .delete()
                .eq("id", user_id)
                .execute()
            )
            return True if response.data else False
        except Exception:
            logger.exception("Failed to delete user profile")
            raise

    def get_user_by_id(self, user_id: str):
        """Fetch a user profile by ID"""
        try:
            response = (
                self.supabase.table("user_profiles")
                .select(SAFE_USER_FIELDS)
                .eq("id", user_id)
                .execute()
            )

            return response.data[0] if response.data else None
        except Exception:
            logger.exception("Failed to fetch user by id")
            raise

    def get_all_users(self):
        """Fetch all user profiles"""
        try:
            response = (
                self.supabase.table("user_profiles").select(SAFE_USER_FIELDS).execute()
            )

            return response.data or []
        except Exception:
            logger.exception("Failed to fetch all users")
            raise

    def update_user_password(self, user_id: str, new_password: str):
        """Update user password (hash before saving, exclude from return)"""
        try:
            password_hash = hash_password(new_password)

            response = (
                self.supabase.table("user_profiles")
                .update({"password": password_hash})
                .eq("id", user_id)
                .execute()
            )

            return (
                {k: v for k, v in response.data[0].items() if k != "password"}
                if response.data
                else None
            )
        except Exception:
            logger.exception("Failed to update user password")
            raise

    def get_tenant_membership(self, tenant_id: str, user_id: str):
        """
        Fetch tenant membership for a given tenant_id and user_id.
        """
        try:
            response = (
                self.supabase.table("tenant_memberships")
                .select("id, tenant_id, user_id, role, is_active")
                .eq("tenant_id", tenant_id)
                .eq("user_id", user_id)
                .execute()
            )

            # Log for debugging
            logger.info(
                f"🔍 Checking membership for user {user_id} in tenant {tenant_id}"
            )
            logger.info(f"📋 Found {len(response.data)} memberships: {response.data}")

            # Return first active membership, or None if no active membership found
            if response.data:
                membership = response.data[0]
                if not membership.get("is_active", True):
                    logger.warning(
                        f"⚠️ Membership exists but is_active=False for user {user_id} in tenant {tenant_id}"
                    )
                    return None
                return membership

            logger.warning(
                f"❌ No membership found for user {user_id} in tenant {tenant_id}"
            )
            return None
        except Exception:
            logger.exception("Failed to fetch tenant membership")
            raise

    async def get_individual_tenant_for_user(
        self, user_id: str, full_name: str = "user", email: str = ""
    ):
        """
        Fetch the user's oldest active individual tenant (owned by the user).
        If none exists, create one automatically.
        """
        try:
            tenant_id = None

            # Step 1: Find all active owned memberships (oldest first)
            membership_response = (
                self.supabase.table("tenant_memberships")
                .select("tenant_id, created_at")
                .eq("user_id", user_id)
                .eq("role", "owner")
                .eq("is_active", True)
                .order("created_at", desc=False)
                .execute()
            )

            if membership_response.data:
                for membership in membership_response.data:
                    # Step 2: Check tenant type and activity
                    t_response = (
                        self.supabase.table("tenants")
                        .select("id, tenant_type, is_active, created_at")
                        .eq("id", membership["tenant_id"])
                        .eq("tenant_type", "individual")
                        .eq("is_active", True)
                        .execute()
                    )

                    if t_response.data:
                        tenant_id = t_response.data[0]["id"]
                        break  # stop at the oldest valid one

            # =====================================
            # CASE: No active individual tenant found
            # =====================================
            if not tenant_id:
                logger.info(
                    f"No active individual tenant found for user {user_id}, creating one..."
                )

                # Create a new individual tenant
                tenant_data = TenantCreate(
                    name=f"{(full_name or 'user').split()[0].lower()}-{str(user_id).split('-')[0]}-ind",
                    tenant_type="individual",
                    description=f"Personal tenant for {full_name or email}",
                    settings={},
                )

                tenant_response = await self.tenant_service.create_tenant(
                    tenant_data, owner_user_id=user_id
                )

                tenant_id = (
                    tenant_response.data.id
                    if tenant_response
                    and tenant_response.success
                    and tenant_response.data
                    else None
                )

                logger.info(
                    f"Created new individual tenant {tenant_id} for user {user_id}"
                )

            return tenant_id

        except Exception:
            logger.exception("Failed to fetch or create individual tenant for user")
            raise

    def get_tenant_details(self, tenant_id: str):
        """Fetch tenant details by tenant ID from the tenants table."""
        try:
            response = (
                self.supabase.table("tenants").select("*").eq("id", tenant_id).execute()
            )
            return response.data[0] if response.data else None
        except Exception:
            logger.exception("Failed to fetch tenant details")
            raise

    def get_can_skip_module(
        self, tenant_id: str, user_id: str, tenant_type: str
    ) -> bool | None:
        """
        Fetch can_skip_modules for a tenant if it belongs to an organization.

        - For team tenants: check org_teams where team_id = tenant_id
        - For individual tenants: check org_individuals where individual_tenant_id = tenant_id
        - For organization tenants or tenants not in an org: return None
        """
        try:
            if tenant_type == "organization":
                # Organization owners don't have this restriction
                return None

            if tenant_type == "team":
                # Check org_teams for this team
                response = (
                    self.supabase.table("org_teams")
                    .select("can_skip_modules")
                    .eq("team_id", tenant_id)
                    .execute()
                )
                if response.data:
                    return response.data[0].get("can_skip_modules")
                return None

            if tenant_type == "individual":
                # Check org_individuals for this individual tenant and user
                response = (
                    self.supabase.table("org_individuals")
                    .select("can_skip_modules")
                    .eq("individual_tenant_id", tenant_id)
                    .eq("user_id", user_id)
                    .execute()
                )
                if response.data:
                    return response.data[0].get("can_skip_modules")
                return None

            return None
        except Exception:
            logger.exception("Failed to fetch can_skip_module")
            return None
