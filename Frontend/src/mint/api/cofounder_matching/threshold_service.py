from datetime import datetime
from typing import List, Optional
from uuid import UUID

from ..system.core.supabase_client import get_supabase_client


class ThresholdService:

    def __init__(self, use_service_role: bool = True):
        """Initialize threshold service with Supabase client"""
        self.supabase = get_supabase_client(use_service_role=use_service_role).client
        self.use_service_role = use_service_role

    def create_threshold(
        self,
        name: str,
        threshold_score: float,
        description: Optional[str] = None,
        is_active: bool = False,
        created_by: Optional[str] = None,
    ):
        """Create a new matching threshold configuration"""
        data = {
            "name": name,
            "description": description,
            "threshold_score": threshold_score,
            "is_active": is_active,
            "created_by": created_by,
            "updated_by": created_by,
        }

        result = self.supabase.table("matching_thresholds").insert(data).execute()
        return result.data[0] if result.data else None

    def get_threshold(self, threshold_id: str):
        """Get a specific threshold by ID"""
        result = (
            self.supabase.table("matching_thresholds")
            .select("*")
            .eq("id", threshold_id)
            .single()
            .execute()
        )
        return result.data

    def get_active_threshold(self):
        """Get the currently active threshold"""
        result = (
            self.supabase.table("matching_thresholds")
            .select("*")
            .eq("is_active", True)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    def list_thresholds(self, limit: int = 50, offset: int = 0):
        """List all threshold configurations"""
        result = (
            self.supabase.table("matching_thresholds")
            .select("*", count="exact")
            .order("created_at", desc=True)
            .limit(limit)
            .offset(offset)
            .execute()
        )
        return {"data": result.data, "count": result.count}

    def update_threshold(
        self,
        threshold_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        threshold_score: Optional[float] = None,
        is_active: Optional[bool] = None,
        updated_by: Optional[str] = None,
    ):
        """Update an existing threshold configuration"""
        update_data = {"updated_by": updated_by}

        if name is not None:
            update_data["name"] = name
        if description is not None:
            update_data["description"] = description
        if threshold_score is not None:
            update_data["threshold_score"] = threshold_score
        if is_active is not None:
            update_data["is_active"] = is_active

        result = (
            self.supabase.table("matching_thresholds")
            .update(update_data)
            .eq("id", threshold_id)
            .execute()
        )
        return result.data[0] if result.data else None

    def delete_threshold(self, threshold_id: str):
        """Delete a threshold configuration"""
        result = (
            self.supabase.table("matching_thresholds")
            .delete()
            .eq("id", threshold_id)
            .execute()
        )
        return {"ok": True, "deleted_count": len(result.data)}

    def activate_threshold(self, threshold_id: str, updated_by: Optional[str] = None):
        """Activate a specific threshold (deactivates all others automatically via trigger)"""
        return self.update_threshold(
            threshold_id=threshold_id, is_active=True, updated_by=updated_by
        )

    def deactivate_threshold(self, threshold_id: str, updated_by: Optional[str] = None):
        """Deactivate a specific threshold"""
        return self.update_threshold(
            threshold_id=threshold_id, is_active=False, updated_by=updated_by
        )
