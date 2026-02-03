"""
Venture Builder data access layer for database operations.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Tuple
from uuid import UUID

from src.mint.api.system.core.supabase_client import get_service_role_client

from .exceptions import VBNotFoundError
from .models import SessionStatus, VBStatus

logger = logging.getLogger(__name__)


class VBDataAccess:
    """Data access service for Venture Builder operations"""

    def __init__(self, use_service_role: bool = True):
        """
        Initialize data access with Supabase client

        Args:
            use_service_role: Whether to use service role (bypasses RLS for admin operations)
        """
        self.supabase = get_service_role_client().client
        self.use_service_role = use_service_role

    # =====================================================
    # EXPERTISE AREAS
    # =====================================================

    def get_all_expertise_areas(self, active_only: bool = True) -> List[dict]:
        """Get all expertise areas"""
        query = self.supabase.table("vb_areas_of_expertise").select("*")

        if active_only:
            query = query.eq("is_active", True)

        result = query.order("display_order").execute()
        return result.data or []

    def get_expertise_by_id(self, expertise_id: UUID) -> Optional[dict]:
        """Get expertise area by ID"""
        result = self.supabase.table("vb_areas_of_expertise")\
            .select("*")\
            .eq("id", str(expertise_id))\
            .limit(1)\
            .execute()

        return result.data[0] if result.data else None

    def create_expertise_area(self, name: str, description: Optional[str], display_order: int) -> dict:
        """Create new expertise area"""
        result = self.supabase.table("vb_areas_of_expertise").insert({
            "name": name,
            "description": description,
            "display_order": display_order,
            "is_active": True
        }).execute()

        if not result.data:
            raise Exception("Failed to create expertise area")

        return result.data[0]

    def update_expertise_area(self, expertise_id: UUID, data: dict) -> dict:
        """Update expertise area"""
        result = self.supabase.table("vb_areas_of_expertise")\
            .update(data)\
            .eq("id", str(expertise_id))\
            .execute()

        if not result.data:
            raise VBNotFoundError(f"Expertise area {expertise_id} not found")

        return result.data[0]

    def deactivate_expertise_area(self, expertise_id: UUID) -> dict:
        """Deactivate expertise area (soft delete)"""
        logger.info(f"Deactivating expertise area {expertise_id}")
        return self.update_expertise_area(expertise_id, {"is_active": False})

    def activate_expertise_area(self, expertise_id: UUID) -> dict:
        """Activate expertise area"""
        logger.info(f"Activating expertise area {expertise_id}")
        return self.update_expertise_area(expertise_id, {"is_active": True})

    def delete_expertise_area(self, expertise_id: UUID) -> None:
        """Hard delete expertise area (permanent removal)"""
        logger.warning(f"Permanently deleting expertise area {expertise_id}")
        result = self.supabase.table("vb_areas_of_expertise")\
            .delete()\
            .eq("id", str(expertise_id))\
            .execute()

        if not result.data:
            raise VBNotFoundError(f"Expertise area {expertise_id} not found")

    def create_custom_expertise(self, name: str) -> dict:
        """Create custom expertise area (created by VB). Case-insensitive check."""
        # Check if already exists (case-insensitive)
        result = self.supabase.table("vb_areas_of_expertise")\
            .select("*")\
            .ilike("name", name)\
            .limit(1)\
            .execute()

        if result.data:
            return result.data[0]

        # Get current max display_order for auto-increment
        max_order_result = self.supabase.table("vb_areas_of_expertise")\
            .select("display_order")\
            .order("display_order", desc=True)\
            .limit(1)\
            .execute()

        next_order = (max_order_result.data[0]["display_order"] + 1) if max_order_result.data else 1000

        # Create new custom expertise
        result = self.supabase.table("vb_areas_of_expertise").insert({
            "name": name,
            "description": None,
            "display_order": next_order,
            "is_active": True,
            "is_custom": True
        }).execute()

        if not result.data:
            raise Exception(f"Failed to create custom expertise: {name}")

        return result.data[0]

    def bulk_create_custom_expertise(self, names: List[str]) -> List[dict]:
        """
        Bulk create custom expertise areas efficiently using case-insensitive OR query.

        Args:
            names: List of custom expertise names to create

        Returns:
            List of expertise area dictionaries (both existing and newly created)
        """
        if not names:
            return []

        # Normalize and deduplicate (case-insensitive)
        normalized_map = {}  # {lowercase: original_cased_name}
        for name in names:
            if name and name.strip():
                cleaned = name.strip()
                normalized_map[cleaned.lower()] = cleaned

        if not normalized_map:
            return []

        unique_names = list(normalized_map.values())
        logger.info(f"Bulk processing {len(unique_names)} custom expertise areas")

        # Step 1: Query existing expertise with OR + ilike (single case-insensitive query)
        # Build OR filter: name.ilike.value1,name.ilike.value2,...
        or_conditions = ",".join([f"name.ilike.{name}" for name in unique_names])

        existing_result = self.supabase.table("vb_areas_of_expertise")\
            .select("*")\
            .or_(or_conditions)\
            .execute()

        existing_expertise = existing_result.data or []

        # Build set of existing names (case-insensitive)
        existing_lower = {exp["name"].lower() for exp in existing_expertise}

        # Step 2: Determine which names need to be created
        names_to_create = [
            name for name in unique_names
            if name.lower() not in existing_lower
        ]

        logger.info(f"Found {len(existing_expertise)} existing, creating {len(names_to_create)} new")

        if not names_to_create:
            return existing_expertise

        # Step 3: Get max display_order (single query)
        max_order_result = self.supabase.table("vb_areas_of_expertise")\
            .select("display_order")\
            .order("display_order", desc=True)\
            .limit(1)\
            .execute()

        next_order = (max_order_result.data[0]["display_order"] + 1) if max_order_result.data else 1000

        # Step 4: Bulk insert new expertise (single query)
        new_expertise_data = [
            {
                "name": name,
                "description": None,
                "display_order": next_order + i,
                "is_active": True,
                "is_custom": True
            }
            for i, name in enumerate(names_to_create)
        ]

        insert_result = self.supabase.table("vb_areas_of_expertise")\
            .insert(new_expertise_data)\
            .execute()

        if not insert_result.data:
            raise Exception("Failed to bulk create custom expertise areas")

        newly_created = insert_result.data
        logger.info(f"Successfully created {len(newly_created)} new custom expertise areas")

        return existing_expertise + newly_created

    # =====================================================
    # VENTURE BUILDERS
    # =====================================================

    def get_vb_by_id(self, vb_id: UUID) -> Optional[dict]:
        """Get VB by ID using the view"""
        result = self.supabase.from_("vb_with_expertise")\
            .select("*")\
            .eq("id", str(vb_id))\
            .limit(1)\
            .execute()

        return result.data[0] if result.data else None

    def get_vb_by_user_id(self, user_id: UUID) -> Optional[dict]:
        """Get VB by user_id using the view"""
        result = self.supabase.from_("vb_with_expertise")\
            .select("*")\
            .eq("user_id", str(user_id))\
            .limit(1)\
            .execute()

        return result.data[0] if result.data else None

    def create_vb_profile(self, user_id: UUID, profile_data: dict) -> dict:
        """Create VB profile"""
        result = self.supabase.table("venture_builders").insert({
            "user_id": str(user_id),
            "name": profile_data.get("name"),
            "contact_email": profile_data["contact_email"],
            "main_expertise": profile_data.get("main_expertise"),
            "short_intro": profile_data.get("short_intro"),
            "profile_picture_url": profile_data.get("profile_picture_url"),
            "work_experience": profile_data["work_experience"],
            "biography": profile_data["biography"],
            "linkedin_url": profile_data.get("linkedin_url"),
            "status": VBStatus.PENDING_PROFILE.value
        }).execute()

        if not result.data:
            raise Exception("Failed to create VB profile")

        return result.data[0]

    def update_vb_profile(self, vb_id: UUID, profile_data: dict) -> dict:
        """Update VB profile"""
        result = self.supabase.table("venture_builders")\
            .update(profile_data)\
            .eq("id", str(vb_id))\
            .execute()

        if not result.data:
            raise VBNotFoundError(f"Venture Builder {vb_id} not found")

        return result.data[0]

    def update_vb_status(self, vb_id: UUID, status: VBStatus) -> dict:
        """Update VB status"""
        return self.update_vb_profile(vb_id, {"status": status.value})

    def list_active_vbs(
        self,
        expertise_ids: Optional[List[UUID]] = None,
        search_query: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
        exclude_vb_id: Optional[str] = None,
    ) -> Tuple[List[dict], int]:
        """List active VBs with filters"""
        query = self.supabase.from_("vb_with_expertise")\
            .select("*", count="exact")\
            .eq("status", VBStatus.ACTIVE.value)

        if exclude_vb_id:
            query = query.neq("id", str(exclude_vb_id))

        # Apply search filter
        # Note: Removed .or_() as Supabase Python client doesn't support it
        # Using ilike on name only - other fields filtered in Python if needed
        if search_query:
            query = query.ilike("name", f"%{search_query}%")

        # Apply pagination
        query = query.range(offset, offset + limit - 1)

        result = query.execute()

        # Filter by expertise if specified (client-side filtering since it's a JSON field)
        items = result.data or []
        if expertise_ids:
            expertise_id_strs = [str(eid) for eid in expertise_ids]
            items = [
                vb for vb in items
                if any(
                    exp.get("id") in expertise_id_strs
                    for exp in vb.get("areas_of_expertise", [])
                )
            ]

        return items, result.count or 0

    def list_pending_vbs(self) -> List[dict]:
        """List VBs pending admin review"""
        result = self.supabase.from_("vb_with_expertise")\
            .select("*")\
            .eq("status", VBStatus.PENDING_ADMIN_REVIEW.value)\
            .execute()
        return result.data or []

    def delete_vb_profile(self, vb_id: str) -> None:
        """
        Delete VB profile.

        Database cascading deletes will automatically remove:
        - vb_expertise_mapping (ON DELETE CASCADE)
        - vb_sessions (ON DELETE CASCADE)
        - vb_session_notes (ON DELETE CASCADE)
        - vb_terms_acceptances (ON DELETE CASCADE)
        """
        self.supabase.table("venture_builders")\
            .delete()\
            .eq("id", str(vb_id))\
            .execute()

    # =====================================================
    # VB EXPERTISE MAPPING
    # =====================================================

    def add_vb_expertise(self, vb_id: UUID, expertise_ids: List[UUID]) -> None:
        """Add expertise areas to VB (upserts - ignores if already exists)"""
        if not expertise_ids:
            return

        mappings = [
            {
                "venture_builder_id": str(vb_id),
                "expertise_id": str(eid)
            }
            for eid in expertise_ids
        ]
        self.supabase.table("vb_expertise_mapping")\
            .upsert(mappings, on_conflict="venture_builder_id,expertise_id")\
            .execute()

    def remove_vb_expertise(self, vb_id: UUID, expertise_id: UUID) -> None:
        """Remove expertise area from VB"""
        self.supabase.table("vb_expertise_mapping")\
            .delete()\
            .eq("venture_builder_id", str(vb_id))\
            .eq("expertise_id", str(expertise_id))\
            .execute()

    # =====================================================
    # SESSIONS
    # =====================================================

    def create_session(self, session_data: dict) -> dict:
        """Create VB session booking"""
        result = self.supabase.table("vb_sessions").insert(session_data).execute()

        if not result.data:
            raise Exception("Failed to create session")

        return result.data[0]

    def get_session_by_id(self, session_id: UUID) -> Optional[dict]:
        """Get session by ID using the view"""
        result = self.supabase.from_("vb_session_details")\
            .select("*")\
            .eq("id", str(session_id))\
            .limit(1)\
            .execute()

        return result.data[0] if result.data else None

    def update_session(self, session_id: UUID, data: dict) -> dict:
        """Update session"""
        result = self.supabase.table("vb_sessions")\
            .update(data)\
            .eq("id", str(session_id))\
            .execute()

        if not result.data:
            raise VBNotFoundError(f"Session {session_id} not found")

        return result.data[0]

    def mark_sessions_as_settled(
        self,
        vb_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> int:
        """
        Mark completed sessions as settled (bulk update).
        Used during reconciliation to mark sessions as paid.

        Args:
            vb_id: Venture Builder ID
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Number of sessions updated
        """
        query = self.supabase.table("vb_sessions")\
            .update({"status": SessionStatus.SETTLED.value})\
            .eq("venture_builder_id", str(vb_id))\
            .eq("status", SessionStatus.COMPLETED.value)

        if start_date:
            query = query.gte("session_datetime", start_date.isoformat())

        if end_date:
            query = query.lte("session_datetime", end_date.isoformat())

        result = query.execute()
        return len(result.data) if result.data else 0

    def get_vb_sessions(
        self,
        vb_id: UUID,
        status: Optional[SessionStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[List[dict], int]:
        """Get sessions for a VB"""
        query = self.supabase.from_("vb_session_details")\
            .select("*", count="exact")\
            .eq("venture_builder_id", str(vb_id))

        if status:
            query = query.eq("status", status.value)

        if start_date:
            query = query.gte("session_datetime", start_date.isoformat())

        if end_date:
            query = query.lte("session_datetime", end_date.isoformat())

        result = query.order("session_datetime", desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()

        return result.data or [], result.count or 0

    def get_user_sessions(
        self,
        user_id: UUID,
        tenant_id: Optional[UUID] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[List[dict], int]:
        """Get sessions booked by a user"""
        query = self.supabase.from_("vb_session_details")\
            .select("*", count="exact")\
            .eq("booked_by_user_id", str(user_id))

        if tenant_id:
            query = query.eq("tenant_id", str(tenant_id))

        result = query.order("session_datetime", desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()

        return result.data or [], result.count or 0

    def get_completed_sessions_count(self, vb_id: UUID) -> int:
        """Get total completed or settled sessions count for a VB"""
        result = self.supabase.table("vb_sessions")\
            .select("id", count="exact")\
            .eq("venture_builder_id", str(vb_id))\
            .in_("status", [SessionStatus.COMPLETED.value, SessionStatus.SETTLED.value])\
            .execute()

        return result.count or 0

    def get_completed_sessions_for_earnings(
        self,
        vb_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        include_settled: bool = False,
    ) -> List[dict]:
        """Get completed sessions for earnings calculation"""
        statuses = [SessionStatus.COMPLETED.value]
        if include_settled:
            statuses.append(SessionStatus.SETTLED.value)

        query = self.supabase.table("vb_sessions")\
            .select("*")\
            .eq("venture_builder_id", str(vb_id))\
            .in_("status", statuses)

        if start_date:
            query = query.gte("session_datetime", start_date.isoformat())

        if end_date:
            query = query.lte("session_datetime", end_date.isoformat())

        result = query.execute()
        return result.data or []

    # =====================================================
    # SESSION NOTES
    # =====================================================

    def create_session_note(self, note_data: dict) -> dict:
        """Create session note"""
        result = self.supabase.table("vb_session_notes").insert(note_data).execute()

        if not result.data:
            raise Exception("Failed to create session note")

        return result.data[0]

    def get_note_by_id(self, note_id: UUID) -> Optional[dict]:
        """Get note by note ID"""
        result = self.supabase.table("vb_session_notes")\
            .select("*")\
            .eq("id", str(note_id))\
            .limit(1)\
            .execute()

        return result.data[0] if result.data else None

    def update_session_note(self, note_id: UUID, note_data: dict) -> dict:
        """Update session note"""
        result = self.supabase.table("vb_session_notes")\
            .update(note_data)\
            .eq("id", str(note_id))\
            .execute()

        if not result.data:
            raise VBNotFoundError(f"Session note {note_id} not found")

        return result.data[0]

    def get_note_by_session_id(self, session_id: UUID) -> Optional[dict]:
        """Get note by session ID"""
        result = self.supabase.table("vb_session_notes")\
            .select("*")\
            .eq("vb_session_id", str(session_id))\
            .limit(1)\
            .execute()

        return result.data[0] if result.data else None

    def get_user_coaching_notes(
        self,
        tenant_id: UUID,
        user_id: Optional[UUID] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[List[dict], int]:
        """Get coaching notes for a user's tenant"""
        query = self.supabase.table("vb_session_notes")\
            .select("*", count="exact")\
            .eq("tenant_id", str(tenant_id))\
            .eq("visible_to_user", True)

        result = query.order("created_at", desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()

        return result.data or [], result.count or 0

    # =====================================================
    # TERMS ACCEPTANCE
    # =====================================================

    def log_terms_acceptance(
        self,
        user_id: UUID,
        tenant_id: UUID,
        vb_id: UUID,
        version: str
    ) -> dict:
        """Log terms acceptance"""
        result = self.supabase.table("vb_terms_acceptances").insert({
            "user_id": str(user_id),
            "tenant_id": str(tenant_id),
            "venture_builder_id": str(vb_id),
            "accepted_terms_version": version
        }).execute()

        if not result.data:
            raise Exception("Failed to log terms acceptance")

        return result.data[0]

    # =====================================================
    # EARNINGS CONFIG
    # =====================================================

    def get_earnings_config(self) -> dict:
        """Get earnings configuration"""
        result = self.supabase.table("vb_earnings_config")\
            .select("*")\
            .limit(1)\
            .execute()

        if not result.data:
            # Return default if not found
            return {
                "credit_to_usd_rate": Decimal("1.0"),
                "commission_rate": Decimal("0.15")
            }

        return result.data[0]

    def update_earnings_config(self, config_data: dict, updated_by: UUID) -> dict:
        """Update earnings configuration"""
        # Get the single config row
        existing = self.supabase.table("vb_earnings_config")\
            .select("id")\
            .limit(1)\
            .execute()

        config_data["updated_by"] = str(updated_by)

        if existing.data:
            result = self.supabase.table("vb_earnings_config")\
                .update(config_data)\
                .eq("id", existing.data[0]["id"])\
                .execute()
        else:
            result = self.supabase.table("vb_earnings_config")\
                .insert(config_data)\
                .execute()

        if not result.data:
            raise Exception("Failed to update earnings config")

        return result.data[0]

    # =====================================================
    # PROJECT ACCESS
    # =====================================================

    def get_project_by_id(self, project_id: UUID) -> Optional[dict]:
        """Get project by ID (for view-only access)"""
        result = self.supabase.table("vmp_projects")\
            .select("*")\
            .eq("id", str(project_id))\
            .limit(1)\
            .execute()

        return result.data[0] if result.data else None

    def get_project_name(self, project_id: UUID) -> Optional[str]:
        """Get project name by ID"""
        result = self.supabase.table("vmp_projects")\
            .select("name")\
            .eq("id", str(project_id))\
            .limit(1)\
            .execute()

        return result.data[0]["name"] if result.data else None

    def get_tenant_projects(self, tenant_id: UUID) -> List[dict]:
        """Get projects for a tenant"""
        result = self.supabase.table("vmp_projects")\
            .select("id, name, tenant_id")\
            .eq("tenant_id", str(tenant_id))\
            .execute()
        return result.data or []

    def get_tenant_name(self, tenant_id: UUID) -> Optional[str]:
        """Get tenant name by ID"""
        result = self.supabase.table("tenants")\
            .select("name")\
            .eq("id", str(tenant_id))\
            .limit(1)\
            .execute()

        return result.data[0]["name"] if result.data else None

    # =====================================================
    # USER PROFILE ACCESS
    # =====================================================

    def get_user_profile(self, user_id: UUID) -> Optional[dict]:
        """Get user profile information"""
        result = self.supabase.table("user_profiles")\
            .select("id, full_name, email, role")\
            .eq("id", str(user_id))\
            .limit(1)\
            .execute()

        return result.data[0] if result.data else None

    # =====================================================
    # USER ROLE MANAGEMENT
    # =====================================================

    def update_user_role(self, user_id: UUID, role: str) -> dict:
        """
        Update user's role in user_profiles table

        Args:
            user_id: UUID of the user
            role: New role to assign (e.g., 'venture_builder', 'user')

        Returns:
            Updated user profile data
        """
        result = self.supabase.table("user_profiles")\
            .update({"role": role})\
            .eq("id", str(user_id))\
            .execute()

        if not result.data:
            raise Exception(f"Failed to update role for user {user_id}")

        return result.data[0]

    def get_user_roles(self, user_ids: List[UUID]) -> List[dict]:
        """Get user roles for a list of user IDs"""
        if not user_ids:
            return []

        result = self.supabase.table("user_profiles")\
            .select("id, role, email")\
            .in_("id", [str(user_id) for user_id in user_ids])\
            .execute()

        return result.data or []

    def update_user_roles(self, user_ids: List[UUID], role: str) -> List[dict]:
        """Bulk update user roles"""
        if not user_ids:
            return []

        result = self.supabase.table("user_profiles")\
            .update({"role": role})\
            .in_("id", [str(user_id) for user_id in user_ids])\
            .execute()

        return result.data or []

    def list_active_vbs_with_role_mismatch(self) -> List[dict]:
        """List active VBs whose user role is not venture_builder"""
        result = self.supabase.table("venture_builders")\
            .select(
                "id, user_id, status, name, contact_email, "
                "user_profiles!inner(id, email, role)"
            )\
            .eq("status", VBStatus.ACTIVE.value)\
            .eq("user_profiles.role", "user")\
            .execute()

        return result.data or []

    def list_pending_vbs_with_vb_role(self) -> List[dict]:
        """List pending admin review VBs whose user role is venture_builder"""
        result = self.supabase.table("venture_builders")\
            .select(
                "id, user_id, status, name, contact_email, "
                "user_profiles!inner(id, email, role)"
            )\
            .eq("status", VBStatus.PENDING_ADMIN_REVIEW.value)\
            .eq("user_profiles.role", "venture_builder")\
            .execute()

        return result.data or []

    # =====================================================
    # DISPUTES
    # =====================================================

    def get_dispute_by_session_id(self, session_id: UUID) -> Optional[dict]:
        """Check if a dispute already exists for a session"""
        result = self.supabase.table("vb_disputes")\
            .select("*")\
            .eq("session_id", str(session_id))\
            .limit(1)\
            .execute()

        return result.data[0] if result.data else None

    def create_dispute(self, dispute_data: dict) -> dict:
        """Create a new dispute"""
        result = self.supabase.table("vb_disputes")\
            .insert(dispute_data)\
            .execute()

        if not result.data:
            raise Exception("Failed to create dispute")

        return result.data[0]

    def get_dispute_by_id(self, dispute_id: UUID) -> Optional[dict]:
        """Get dispute by ID"""
        result = self.supabase.table("vb_disputes")\
            .select("*")\
            .eq("id", str(dispute_id))\
            .limit(1)\
            .execute()

        return result.data[0] if result.data else None

    def get_disputes_for_user(
        self,
        user_id: UUID,
        tenant_id: UUID,
        limit: int = 20,
        offset: int = 0
    ) -> tuple[List[dict], int]:
        """Get disputes created by a user with pagination"""
        # Get count
        count_result = self.supabase.table("vb_disputes")\
            .select("id", count="exact")\
            .eq("user_id", str(user_id))\
            .eq("tenant_id", str(tenant_id))\
            .execute()

        total_count = count_result.count or 0

        # Get disputes
        result = self.supabase.table("vb_disputes")\
            .select("*")\
            .eq("user_id", str(user_id))\
            .eq("tenant_id", str(tenant_id))\
            .order("created_at", desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()

        return result.data or [], total_count

    def get_disputes_for_admin(
        self,
        status: Optional[str] = None,
        vb_id: Optional[UUID] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> tuple[List[dict], int]:
        """Get disputes with filters (admin view) using the view with session details"""
        query = self.supabase.from_("vb_disputes_with_details").select("*", count="exact")

        if status:
            query = query.eq("status", status)
        if vb_id:
            query = query.eq("vb_id", str(vb_id))
        if start_date:
            query = query.gte("created_at", start_date)
        if end_date:
            query = query.lte("created_at", end_date)

        # Get count
        count_result = query.execute()
        total_count = count_result.count or 0

        # Get disputes
        result = query.order("created_at", desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()

        return result.data or [], total_count

    def update_dispute(self, dispute_id: UUID, update_data: dict) -> dict:
        """Update dispute"""
        result = self.supabase.table("vb_disputes")\
            .update(update_data)\
            .eq("id", str(dispute_id))\
            .execute()

        if not result.data:
            raise Exception(f"Failed to update dispute {dispute_id}")

        return result.data[0]

    # =====================================================
    # RECONCILIATION
    # =====================================================

    def get_vb_total_reconciled(self, vb_id: UUID) -> Decimal:
        """Get VB's total reconciled payments"""
        result = self.supabase.table("venture_builders")\
            .select("total_reconciled_payments")\
            .eq("id", str(vb_id))\
            .limit(1)\
            .execute()

        if not result.data:
            raise VBNotFoundError(f"Venture Builder {vb_id} not found")

        return Decimal(str(result.data[0].get("total_reconciled_payments", 0)))

    def create_reconciliation(
        self,
        vb_id: UUID,
        reconciled_by: UUID,
        amount_reconciled_usd: Decimal,
        pending_amount_before: Decimal,
        session_count: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        notes: Optional[str] = None,
    ) -> dict:
        """Create a new reconciliation record"""
        reconciliation_data = {
            "venture_builder_id": str(vb_id),
            "reconciled_by": str(reconciled_by),
            "amount_reconciled_usd": float(amount_reconciled_usd),
            "pending_amount_before": float(pending_amount_before),
            "session_count": session_count,
            "notes": notes,
        }

        if start_date:
            reconciliation_data["start_date"] = start_date.isoformat()
        if end_date:
            reconciliation_data["end_date"] = end_date.isoformat()

        result = self.supabase.table("vb_reconciliations").insert(reconciliation_data).execute()

        if not result.data:
            raise Exception("Failed to create reconciliation")

        return result.data[0]

    def update_vb_total_reconciled(self, vb_id: UUID, new_total: Decimal) -> dict:
        """Update VB's total reconciled payments"""
        result = self.supabase.table("venture_builders")\
            .update({"total_reconciled_payments": float(new_total)})\
            .eq("id", str(vb_id))\
            .execute()

        if not result.data:
            raise VBNotFoundError(f"Venture Builder {vb_id} not found")

        return result.data[0]

    def get_reconciliation_history(
        self,
        vb_id: UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[dict], int]:
        """Get reconciliation history for a VB with pagination"""
        # Get total count
        count_result = self.supabase.table("vb_reconciliations")\
            .select("*", count="exact")\
            .eq("venture_builder_id", str(vb_id))\
            .execute()

        total_count = count_result.count or 0

        # Get paginated data from the view
        offset = (page - 1) * page_size
        result = self.supabase.table("vb_reconciliation_history")\
            .select("*")\
            .eq("venture_builder_id", str(vb_id))\
            .order("created_at", desc=True)\
            .range(offset, offset + page_size - 1)\
            .execute()

        return result.data or [], total_count

    def get_all_reconciliations(
        self,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[dict], int]:
        """Get all reconciliations (Admin view) with pagination"""
        # Get total count
        count_result = self.supabase.table("vb_reconciliations")\
            .select("*", count="exact")\
            .execute()

        total_count = count_result.count or 0

        # Get paginated data from the view
        offset = (page - 1) * page_size
        result = self.supabase.table("vb_reconciliation_history")\
            .select("*")\
            .order("created_at", desc=True)\
            .range(offset, offset + page_size - 1)\
            .execute()

        return result.data or [], total_count

    # =====================================================
    # GOOGLE CALENDAR CONNECTIONS
    # =====================================================

    def get_google_connection(self, vb_id: UUID) -> Optional[dict]:
        """Get Google Calendar connection for a VB"""
        result = self.supabase.table("venture_builder_google_connections")\
            .select("*")\
            .eq("vb_id", str(vb_id))\
            .eq("is_valid", True)\
            .limit(1)\
            .execute()

        return result.data[0] if result.data else None

    def has_calendar_connection(self, vb_id: UUID) -> bool:
        """Check if VB has a valid Google Calendar connection"""
        result = self.supabase.table("venture_builder_google_connections")\
            .select("vb_id")\
            .eq("vb_id", str(vb_id))\
            .eq("is_valid", True)\
            .limit(1)\
            .execute()

        return bool(result.data)

    def get_vbs_with_calendar_connectivity(self) -> List[str]:
        """
        Get list of VB IDs that have either Google Calendar connection or legacy URL.
        Used for filtering browse results.
        """
        # Get VBs with Google Calendar connection
        google_result = self.supabase.table("venture_builder_google_connections")\
            .select("vb_id")\
            .eq("is_valid", True)\
            .execute()

        google_vb_ids = {row["vb_id"] for row in (google_result.data or [])}

        # Get VBs with calendar_booking_url set
        legacy_result = self.supabase.table("venture_builders")\
            .select("id")\
            .neq("calendar_booking_url", None)\
            .execute()

        legacy_vb_ids = {row["id"] for row in (legacy_result.data or [])}

        # Return union of both sets
        return list(google_vb_ids | legacy_vb_ids)

    # =====================================================
    # AVAILABILITY SLOTS
    # =====================================================

    def get_availability_slots(self, vb_id: UUID) -> List[dict]:
        """Get all availability slots for a VB"""
        result = self.supabase.table("venture_builder_availability_profiles")\
            .select("*")\
            .eq("vb_id", str(vb_id))\
            .order("day_of_week")\
            .order("session_start")\
            .execute()

        return result.data or []

    def create_availability_slots(self, vb_id: UUID, slots: List[dict]) -> List[dict]:
        """
        Create or replace availability slots for a VB (single bulk upsert).
        If a slot already exists for the same day_of_week + session_start, it's replaced.

        Args:
            vb_id: Venture Builder ID
            slots: List of slot data dicts with day_of_week and session_start

        Returns:
            List of created/updated slot records
        """
        if not slots:
            return []

        from datetime import datetime, timedelta

        slots_data = []
        for s in slots:
            session_start = s["session_start"]
            if isinstance(session_start, str):
                start_time = datetime.strptime(session_start, "%H:%M:%S").time()
            else:
                start_time = session_start

            # Compute end time (+1 hour)
            start_dt = datetime.combine(datetime.today(), start_time)
            end_dt = start_dt + timedelta(hours=1)
            session_end = end_dt.time()

            slots_data.append({
                "vb_id": str(vb_id),
                "day_of_week": s["day_of_week"],
                "session_start": start_time.strftime("%H:%M:%S"),
                "session_end": session_end.strftime("%H:%M:%S"),
            })

        # Upsert: replace if vb_id + day_of_week + session_start already exists
        result = self.supabase.table("venture_builder_availability_profiles")\
            .upsert(slots_data, on_conflict="vb_id,day_of_week,session_start")\
            .execute()

        return result.data or []

    def delete_availability_slots(self, vb_id: UUID, slots: List[dict]) -> int:
        """
        Delete specific availability slots for a VB (single bulk delete).

        Args:
            vb_id: Venture Builder ID
            slots: List of slot identifiers with day_of_week and session_start

        Returns:
            Number of deleted slots
        """
        if not slots:
            return 0

        # Build OR filter: (day=X AND start=Y) OR (day=A AND start=B)
        or_conditions = []
        for slot in slots:
            session_start = slot["session_start"]
            if not isinstance(session_start, str):
                session_start = session_start.strftime("%H:%M:%S")

            or_conditions.append(
                f"and(day_of_week.eq.{slot['day_of_week']},session_start.eq.{session_start})"
            )

        result = self.supabase.table("venture_builder_availability_profiles")\
            .delete()\
            .eq("vb_id", str(vb_id))\
            .or_(",".join(or_conditions))\
            .execute()

        return len(result.data) if result.data else 0

    # =====================================================
    # SESSIONS - ADDITIONAL HELPERS
    # =====================================================

    def get_sessions_in_range(
        self,
        vb_id: UUID,
        start: datetime,
        end: datetime,
        statuses: Optional[List[str]] = None
    ) -> List[dict]:
        """
        Get sessions for a VB within a date range.
        Used for availability computation.

        Args:
            vb_id: Venture Builder ID
            start: Start datetime
            end: End datetime
            statuses: Optional list of status values to filter

        Returns:
            List of session records
        """
        query = self.supabase.table("vb_sessions")\
            .select("session_datetime, session_duration_minutes, status")\
            .eq("venture_builder_id", str(vb_id))\
            .gte("session_datetime", start.isoformat())\
            .lte("session_datetime", end.isoformat())

        if statuses:
            query = query.in_("status", statuses)

        result = query.execute()
        return result.data or []

    def delete_session(self, session_id: UUID) -> Optional[dict]:
        """
        Delete a session by ID.
        Returns the deleted session data for calendar event cleanup.
        """
        # First get the session to return its data
        session = self.get_session_by_id(session_id)

        if session:
            self.supabase.table("vb_sessions")\
                .delete()\
                .eq("id", str(session_id))\
                .execute()

        return session

    # =====================================================
    # VB INTEREST SUBMISSIONS
    # =====================================================

    def create_interest_submission(self, data: dict) -> dict:
        """
        Create a new VB interest submission.
        
        Args:
            data: Submission data including all form fields
            
        Returns:
            Created submission record
            
        Raises:
            Exception if email already exists or insert fails
        """
        result = self.supabase.table("vb_interest_submissions")\
            .insert(data)\
            .execute()
        
        if not result.data:
            raise Exception("Failed to create interest submission")
        
        return result.data[0]

    def get_interest_submission_by_id(self, submission_id: str) -> Optional[dict]:
        """
        Get a submission by its ID.
        
        Args:
            submission_id: UUID of the submission
            
        Returns:
            Submission record or None if not found
        """
        result = self.supabase.table("vb_interest_submissions")\
            .select("*")\
            .eq("id", submission_id)\
            .execute()
        
        return result.data[0] if result.data else None

    def get_interest_submission_by_email(self, email: str) -> Optional[dict]:
        """
        Get a submission by email address.
        
        Args:
            email: Work email to search for
            
        Returns:
            Submission record or None if not found
        """
        result = self.supabase.table("vb_interest_submissions")\
            .select("*")\
            .eq("work_email", email.lower())\
            .execute()
        
        return result.data[0] if result.data else None

    def list_interest_submissions(
        self,
        status: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[dict], int]:
        """
        List interest submissions with optional filtering.
        
        Args:
            status: Filter by status (pending, approved, rejected, invited)
            search: Search by name or email
            limit: Max number of results
            offset: Offset for pagination
            
        Returns:
            Tuple of (list of submissions, total count)
        """
        # Build the base query for items
        query = self.supabase.table("vb_interest_submissions")\
            .select("*")
        
        # Apply status filter
        if status:
            query = query.eq("status", status)
        
        # Apply search filter (name or email)
        if search:
            search_term = f"%{search}%"
            query = query.or_(f"full_name.ilike.{search_term},work_email.ilike.{search_term}")
        
        # Get total count first (separate query)
        count_query = self.supabase.table("vb_interest_submissions")\
            .select("id", count="exact")
        
        if status:
            count_query = count_query.eq("status", status)
        
        if search:
            search_term = f"%{search}%"
            count_query = count_query.or_(f"full_name.ilike.{search_term},work_email.ilike.{search_term}")
        
        count_result = count_query.execute()
        total_count = count_result.count if count_result.count is not None else 0
        
        # Apply pagination and ordering
        query = query.order("created_at", desc=True)\
            .range(offset, offset + limit - 1)
        
        result = query.execute()
        
        return result.data or [], total_count

    def update_interest_submission(
        self,
        submission_id: str,
        update_data: dict,
    ) -> Optional[dict]:
        """
        Update a submission's fields.
        
        Args:
            submission_id: UUID of the submission
            update_data: Dict of fields to update
            
        Returns:
            Updated submission record or None if not found
        """
        result = self.supabase.table("vb_interest_submissions")\
            .update(update_data)\
            .eq("id", submission_id)\
            .execute()
        
        return result.data[0] if result.data else None

    def check_interest_email_exists(self, email: str) -> bool:
        """
        Check if an email already has a submission.
        
        Args:
            email: Email to check
            
        Returns:
            True if email exists, False otherwise
        """
        result = self.supabase.table("vb_interest_submissions")\
            .select("id")\
            .eq("work_email", email.lower())\
            .execute()
        
        return len(result.data) > 0 if result.data else False


# Singleton instance
_data_access_instance: Optional[VBDataAccess] = None


def get_vb_data_access() -> VBDataAccess:
    """Get VB data access singleton"""
    global _data_access_instance
    if _data_access_instance is None:
        _data_access_instance = VBDataAccess()
    return _data_access_instance
