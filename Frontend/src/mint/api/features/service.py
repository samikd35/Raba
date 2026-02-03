"""
Module Features Service (Admin).
Uses the Supabase service-role client wrapper to perform CRUD.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from ..system.core.supabase_client import get_service_role_client
from .models import ModuleFeatureCreate, ModuleFeatureUpdate

logger = logging.getLogger(__name__)

TABLE = "module_features"
TABLE_COSTS = "feature_credit_costs"


class ModuleFeatureService:
    def __init__(self) -> None:
        # follow existing pattern: service-role client (bypass RLS)
        self.db = get_service_role_client().client

    # -------- Feature Name Resolution --------
    def get_feature_id_by_name(self, feature_name: str) -> Optional[str]:
        """
        Resolve feature name to UUID for automatic endpoint routing.
        
        Args:
            feature_name: Human-readable feature name (e.g., 'problem-generator')
            
        Returns:
            Feature UUID if found, None otherwise
        """
        resp = (
            self.db.table(TABLE)
            .select("id")
            .eq("name", feature_name)
            .eq("is_active", True)
            .execute()
        )
        
        if resp.data:
            return resp.data[0]["id"]
        return None
    
    def resolve_feature_identifier(self, identifier: str) -> Optional[str]:
        """
        Resolve either feature name or UUID to UUID.
        
        Args:
            identifier: Either feature name or UUID
            
        Returns:
            Feature UUID if valid, None otherwise
        """
        import uuid as uuid_module
        
        # Check if it's a valid UUID format first
        try:
            uuid_module.UUID(identifier)
            # It's a valid UUID format, check if it exists in database
            resp = (
                self.db.table(TABLE)
                .select("id")
                .eq("id", identifier)
                .eq("is_active", True)
                .execute()
            )
            
            if resp.data:
                return identifier  # It's a valid UUID and exists
        except ValueError:
            # Not a valid UUID format, treat as feature name
            pass
        
        # Try to resolve as feature name
        return self.get_feature_id_by_name(identifier)

    # -------- Read --------
    def list(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        search: Optional[str] = None,
        feature_type: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        q = (
            self.db.table(TABLE)
            .select("*", count="exact")
            .order("created_at", desc=True)
        )
        if search:
            # Use individual filters instead of or_ for compatibility
            # Apply search to both name and display_name fields
            # Note: This will be an AND condition, but it's safer for now
            q = q.ilike("name", f"%{search}%")
        if feature_type:
            q = q.eq("feature_type", feature_type)
        if is_active is not None:
            q = q.eq("is_active", is_active)
        q = q.range(offset, offset + limit - 1)

        resp = q.execute()
        data = resp.data or []
        total = resp.count or len(data)
        return data, total

    def get(self, feature_id: str) -> Optional[Dict[str, Any]]:
        resp = (
            self.db.table(TABLE)
            .select("*")
            .eq("id", str(feature_id))
            .execute()
        )
        return resp.data[0] if resp.data else None

    # -------- Create --------
    def create(self, payload: ModuleFeatureCreate) -> Dict[str, Any]:
        payload.validate_feature_type()
        resp = (
            self.db.table(TABLE)
            .insert(payload.model_dump())
            .execute()
        )
        if resp.data:
            return resp.data[0]
        return {}

    # -------- Update --------
    def update(
        self, feature_id: str, payload: ModuleFeatureUpdate
    ) -> Optional[Dict[str, Any]]:
        payload.validate_feature_type()
        update_dict = payload.model_dump(exclude_unset=True)
        if not update_dict:
            # no-op -> return current row
            resp = (
                self.db.table(TABLE)
                .select("*")
                .eq("id", str(feature_id))
                .execute()
            )
            return resp.data[0] if resp.data else None
        
        # Update the record
        update_resp = (
            self.db.table(TABLE)
            .update(update_dict)
            .eq("id", str(feature_id))
            .execute()
        )
        
        # Fetch the updated record
        if update_resp.data:
            fetch_resp = (
                self.db.table(TABLE)
                .select("*")
                .eq("id", str(feature_id))
                .execute()
            )
            return fetch_resp.data[0] if fetch_resp.data else None
        return None

    # -------- Delete --------
    def delete(self, feature_id: str) -> None:
        self.db.table(TABLE).delete().eq("id", str(feature_id)).execute()

    # -------- Utility actions --------
    def toggle_active(
        self, feature_id: str, is_active: bool
    ) -> Optional[Dict[str, Any]]:
        # Update the record
        update_resp = (
            self.db.table(TABLE)
            .update({"is_active": is_active})
            .eq("id", str(feature_id))
            .execute()
        )
        
        # Fetch the updated record
        if update_resp.data:
            fetch_resp = (
                self.db.table(TABLE)
                .select("*")
                .eq("id", str(feature_id))
                .execute()
            )
            return fetch_resp.data[0] if fetch_resp.data else None
        return None


class FeatureCreditCostService:
    def __init__(self) -> None:
        self.db = get_service_role_client().client

    # -------- Read --------
    def list(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        feature_id: Optional[str] = None,
        plan_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        current_only: bool = False,
        as_of: Optional[datetime] = None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        # First, try to get overrides from feature_credit_costs table
        q = (
            self.db.table(TABLE_COSTS)
            .select("*", count="exact")
            .order("effective_from", desc=True)
        )
        if feature_id:
            q = q.eq("feature_id", str(feature_id))
        if plan_type:
            q = q.eq("plan_type", plan_type)
        if is_active is not None:
            q = q.eq("is_active", is_active)

        if current_only:
            ts = (as_of or datetime.now(timezone.utc)).isoformat()
            q = q.lte("effective_from", ts)
            # Note: Removed complex OR condition for compatibility
            # Will filter effective_until manually if needed

        q = q.range(offset, offset + limit - 1)
        
        logger.info(f"🔍 CREDIT_COSTS SERVICE: Executing query with feature_id={feature_id}")
        
        resp = q.execute()
        data = resp.data or []
        total = resp.count or len(data)
        
        logger.info(f"🔍 CREDIT_COSTS SERVICE: Query returned {len(data)} items from feature_credit_costs table")
        
        # If no overrides found and feature_id is specified, generate default entries from module_features
        if feature_id and not data:
            logger.info(f"🔍 CREDIT_COSTS SERVICE: No overrides found, generating default from module_features")
            
            # Get the base feature data
            feature_resp = (
                self.db.table(TABLE)
                .select("*")
                .eq("id", str(feature_id))
                .execute()
            )
            
            if feature_resp.data:
                feature = feature_resp.data[0]
                logger.info(f"🔍 CREDIT_COSTS SERVICE: Found feature: {feature['name']} with credit_cost: {feature['credit_cost']}")
                
                # Generate default cost entries for all plan types
                plan_types = ['individual', 'team', 'organization']
                if plan_type:
                    plan_types = [plan_type]  # Filter to specific plan type if requested
                
                generated_data = []
                for pt in plan_types:
                    # Generate a deterministic UUID based on feature_id and plan_type
                    # This ensures consistent IDs across requests for the same feature+plan combination
                    namespace = uuid.UUID(str(feature_id))
                    deterministic_uuid = str(uuid.uuid5(namespace, f"default-{pt}"))
                    
                    generated_entry = {
                        "id": deterministic_uuid,  # Valid UUID
                        "feature_id": str(feature_id),
                        "plan_type": pt,
                        "credit_cost": feature["credit_cost"],
                        "is_active": feature["is_active"],
                        "effective_from": feature["created_at"],
                        "effective_until": None,
                        "created_at": feature["created_at"],
                    }
                    generated_data.append(generated_entry)
                
                # Apply limit/offset to generated data
                start_idx = offset
                end_idx = offset + limit
                data = generated_data[start_idx:end_idx]
                total = len(generated_data)
                
                logger.info(f"🔍 CREDIT_COSTS SERVICE: Generated {len(data)} default entries from module_features")
            else:
                logger.warning(f"🔍 CREDIT_COSTS SERVICE: Feature {feature_id} not found in module_features table")
        
        return data, total

    def get(self, cost_id: str) -> Optional[Dict[str, Any]]:
        resp = (
            self.db.table(TABLE_COSTS)
            .select("*")
            .eq("id", str(cost_id))
            .execute()
        )
        return resp.data[0] if resp.data else None

    # -------- Create --------
    def create(self, payload) -> Dict[str, Any]:
        payload.validate_plan_type()
        
        # Convert to dict with proper serialization
        data = payload.model_dump()
        
        # Convert UUID to string for JSON serialization
        if "feature_id" in data and data["feature_id"]:
            data["feature_id"] = str(data["feature_id"])
        
        # Convert datetime objects to ISO format strings for JSON serialization
        if "effective_from" in data and data["effective_from"]:
            data["effective_from"] = data["effective_from"].isoformat()
        if "effective_until" in data and data["effective_until"]:
            data["effective_until"] = data["effective_until"].isoformat()
        
        resp = (
            self.db.table(TABLE_COSTS)
            .insert(data)
            .execute()
        )
        if resp.data:
            return resp.data[0]
        return {}

    # -------- Update --------
    def update(self, cost_id: str, payload) -> Optional[Dict[str, Any]]:
        payload.validate_plan_type()
        update_dict = payload.model_dump(exclude_unset=True)
        
        # Convert UUID to string for JSON serialization
        if "feature_id" in update_dict and update_dict["feature_id"]:
            update_dict["feature_id"] = str(update_dict["feature_id"])
        
        # Convert datetime objects to ISO format strings for JSON serialization
        if "effective_from" in update_dict and update_dict["effective_from"]:
            update_dict["effective_from"] = update_dict["effective_from"].isoformat()
        if "effective_until" in update_dict and update_dict["effective_until"]:
            update_dict["effective_until"] = update_dict["effective_until"].isoformat()
        
        if not update_dict:
            resp = (
                self.db.table(TABLE_COSTS)
                .select("*")
                .eq("id", str(cost_id))
                .execute()
            )
            return resp.data[0] if resp.data else None
        
        # Update the record
        update_resp = (
            self.db.table(TABLE_COSTS)
            .update(update_dict)
            .eq("id", str(cost_id))
            .execute()
        )
        
        # Fetch the updated record
        if update_resp.data:
            fetch_resp = (
                self.db.table(TABLE_COSTS)
                .select("*")
                .eq("id", str(cost_id))
                .execute()
            )
            return fetch_resp.data[0] if fetch_resp.data else None
        return None

    # -------- Delete --------
    def delete(self, cost_id: str) -> None:
        self.db.table(TABLE_COSTS).delete().eq("id", str(cost_id)).execute()

    # -------- Utility actions --------
    def toggle_active(self, cost_id: str, is_active: bool) -> Optional[Dict[str, Any]]:
        # Update the record
        update_resp = (
            self.db.table(TABLE_COSTS)
            .update({"is_active": is_active})
            .eq("id", str(cost_id))
            .execute()
        )
        
        # Fetch the updated record
        if update_resp.data:
            fetch_resp = (
                self.db.table(TABLE_COSTS)
                .select("*")
                .eq("id", str(cost_id))
                .execute()
            )
            return fetch_resp.data[0] if fetch_resp.data else None
        return None

    def resolve_cost(
        self,
        feature_id: str,
        plan_type: str,
        as_of: Optional[datetime] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        First try active feature_credit_costs effective at `as_of` (default now, UTC).
        Fallback to module_features.credit_cost.
        
        NOTE: feature_id can be either a UUID string or a feature name.
        This method will resolve feature names to UUIDs before querying.
        """
        now_ts = (as_of or datetime.now(timezone.utc)).isoformat()

        # Resolve feature_id: could be UUID or feature name
        # Check if it's a valid UUID format first
        resolved_feature_id = feature_id
        try:
            uuid.UUID(feature_id)
            # It's a valid UUID format, use as-is
        except ValueError:
            # Not a valid UUID, try to resolve as feature name
            logger.info(f"🔍 RESOLVE_COST: '{feature_id}' is not a UUID, resolving as feature name...")
            name_resp = (
                self.db.table(TABLE)
                .select("id")
                .eq("name", feature_id)
                .eq("is_active", True)
                .execute()
            )
            if name_resp.data:
                resolved_feature_id = name_resp.data[0]["id"]
                logger.info(f"✅ RESOLVE_COST: Resolved '{feature_id}' to UUID '{resolved_feature_id}'")
            else:
                logger.warning(f"⚠️ RESOLVE_COST: Feature name '{feature_id}' not found in module_features")
                return None

        # Look for an active, currently-effective override
        # Split the complex OR condition into separate queries for compatibility
        q = (
            self.db.table(TABLE_COSTS)
            .select("*")
            .eq("feature_id", str(resolved_feature_id))
            .eq("plan_type", plan_type)
            .eq("is_active", True)
            .lte("effective_from", now_ts)
            .order("effective_from", desc=True)
        )
        # Filter results manually for effective_until condition
        all_results = q.execute().data or []
        current_results = []
        for row in all_results:
            effective_until = row.get("effective_until")
            if effective_until is None or effective_until > now_ts:
                current_results.append(row)
        
        if current_results:
            # Sort by effective_from desc and take the first one
            current_results.sort(key=lambda x: x.get("effective_from", ""), reverse=True)
            row = current_results[0]
            return {
                "feature_id": str(resolved_feature_id),
                "plan_type": plan_type,
                "credit_cost": row["credit_cost"],
                "source": TABLE_COSTS,
                "effective_from": row.get("effective_from"),
                "effective_until": row.get("effective_until"),
            }

        # Fallback to base module_features.credit_cost
        base_resp = (
            self.db.table(TABLE)
            .select("credit_cost")
            .eq("id", str(feature_id))
            .execute()
        )
        if not base_resp.data:
            return None
        
        base = base_resp.data[0]
        return {
            "feature_id": str(feature_id),
            "plan_type": plan_type,
            "credit_cost": base["credit_cost"],
            "source": TABLE,
            "effective_from": None,
            "effective_until": None,
        }
