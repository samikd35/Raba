from typing import List, Optional, Dict, Any
from ..system.core.supabase_client import get_supabase_client


class EnumSuggestionsService:
    """Service for managing enum suggestions from 'Other' field submissions"""

    def __init__(self, use_service_role: bool = True):
        self.supabase = get_supabase_client(use_service_role=use_service_role).client

    def list_suggestions(
        self,
        enum_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        order_by: str = "times_suggested",
        order_desc: bool = True
    ) -> Dict[str, Any]:
        """
        List enum suggestions with optional filters

        Args:
            enum_type: Filter by enum type (industries, responsibilities, etc.)
            status: Filter by status (pending, approved, rejected)
            limit: Maximum number of results
            offset: Number of results to skip
            order_by: Field to order by (times_suggested, created_at, updated_at)
            order_desc: Whether to order descending

        Returns:
            Dict with 'total' count and 'items' list
        """
        query = self.supabase.table("profile_enum_suggestions").select("*", count="exact")

        if enum_type:
            query = query.eq("enum_type", enum_type)
        if status:
            query = query.eq("status", status)

        # Get total count
        count_result = query.execute()
        total = count_result.count or 0

        # Get paginated results
        query = query.order(order_by, desc=order_desc).range(offset, offset + limit - 1)
        result = query.execute()

        return {
            "total": total,
            "items": result.data or []
        }

    def get_suggestion(self, suggestion_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific suggestion by ID"""
        result = (
            self.supabase.table("profile_enum_suggestions")
            .select("*")
            .eq("id", suggestion_id)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    def record_suggestion(
        self,
        enum_type: str,
        suggested_value: str,
        suggested_by: str,
        profile_version_id: str,
        field_context: Optional[str] = None
    ) -> str:
        """
        Record a new suggestion or increment existing one

        Args:
            enum_type: Type of enum (industries, responsibilities, etc.)
            suggested_value: The custom value submitted by user
            suggested_by: User ID who suggested it
            profile_version_id: Profile version ID where this was submitted
            field_context: Optional context (e.g., 'expected' vs 'preferred' for commitments)

        Returns:
            Suggestion ID (UUID)
        """
        result = self.supabase.rpc(
            "record_enum_suggestion",
            {
                "p_enum_type": enum_type,
                "p_suggested_value": suggested_value,
                "p_suggested_by": suggested_by,
                "p_profile_version_id": profile_version_id,
                "p_field_context": field_context
            }
        ).execute()

        return result.data if result.data else None

    def approve_and_create_enum(
        self,
        suggestion_id: str,
        enum_name: str,
        reviewed_by: str,
        enum_description: Optional[str] = None,
        admin_notes: Optional[str] = None
    ) -> str:
        """
        Approve a suggestion and create the official enum entry

        This will:
        1. Create a new entry in the appropriate enum table (profile_industries, etc.)
        2. Update the suggestion status to 'approved'
        3. Update all profile_versions that used this "other" value

        Args:
            suggestion_id: ID of the suggestion to approve
            enum_name: Display name for the new enum option
            reviewed_by: Admin user ID who approved it
            enum_description: Optional description for the new enum
            admin_notes: Optional admin notes about the approval

        Returns:
            ID of the created enum entry
        """
        result = self.supabase.rpc(
            "approve_and_create_enum",
            {
                "p_suggestion_id": suggestion_id,
                "p_enum_name": enum_name,
                "p_enum_description": enum_description,
                "p_reviewed_by": reviewed_by,
                "p_admin_notes": admin_notes
            }
        ).execute()

        return result.data if result.data else None

    def reject_suggestion(
        self,
        suggestion_id: str,
        reviewed_by: str,
        admin_notes: str
    ) -> bool:
        """
        Reject a suggestion

        Args:
            suggestion_id: ID of the suggestion to reject
            reviewed_by: Admin user ID who rejected it
            admin_notes: Reason for rejection

        Returns:
            True if successful
        """
        result = self.supabase.rpc(
            "reject_enum_suggestion",
            {
                "p_suggestion_id": suggestion_id,
                "p_reviewed_by": reviewed_by,
                "p_admin_notes": admin_notes
            }
        ).execute()

        return result.data if result.data else False

    def get_suggestion_stats(self) -> List[Dict[str, Any]]:
        """
        Get statistics about suggestions by type and status

        Returns:
            List of dicts with enum_type, status, count, and total_suggestions
        """
        result = self.supabase.rpc("get_enum_suggestion_stats").execute()
        return result.data or []

    def get_top_suggestions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the most frequently suggested values that are still pending

        Args:
            limit: Maximum number of suggestions to return

        Returns:
            List of pending suggestions ordered by times_suggested (descending)
        """
        result = (
            self.supabase.table("profile_enum_suggestions")
            .select("*")
            .eq("status", "pending")
            .order("times_suggested", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []

    def get_suggestions_by_type(
        self,
        enum_type: str,
        status: str = "pending",
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get suggestions filtered by enum type

        Args:
            enum_type: Type of enum (industries, responsibilities, etc.)
            status: Status filter (pending, approved, rejected)
            limit: Maximum number of results

        Returns:
            List of suggestions
        """
        result = (
            self.supabase.table("profile_enum_suggestions")
            .select("*")
            .eq("enum_type", enum_type)
            .eq("status", status)
            .order("times_suggested", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []
