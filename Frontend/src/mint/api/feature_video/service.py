"""
Service layer for Feature Video Seen tracking.
"""

import logging
from typing import List, Optional, Tuple

from ..system.core.supabase_client import get_service_role_client

logger = logging.getLogger(__name__)

TABLE_NAME = "user_feature_video_seen"


class FeatureVideoSeenService:
    """Service for managing user feature video seen status."""

    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = get_service_role_client().client
        return self._client

    async def get_seen_features(self, user_id: str) -> List[str]:
        """
        Get all feature IDs that a user has seen.
        
        Args:
            user_id: The authenticated user's ID
            
        Returns:
            List of feature_id strings
        """
        try:
            response = (
                self.client.table(TABLE_NAME)
                .select("feature_id")
                .eq("user_id", user_id)
                .execute()
            )
            
            return [row["feature_id"] for row in response.data]
            
        except Exception as e:
            logger.error(f"Failed to get seen features for user {user_id}: {e}")
            raise

    async def mark_feature_seen(
        self,
        user_id: str,
        feature_id: str,
        source: Optional[str] = None
    ) -> Tuple[bool, bool]:
        """
        Mark a feature video as seen for a user.
        Uses UPSERT to handle idempotent inserts.
        
        Args:
            user_id: The authenticated user's ID
            feature_id: The feature identifier
            source: How the video was triggered ('autoplay' or 'icon_click')
            
        Returns:
            Tuple of (success: bool, created: bool)
            - success: True if operation completed
            - created: True if this was a new record, False if already existed
        """
        try:
            # First check if record exists
            existing = (
                self.client.table(TABLE_NAME)
                .select("id")
                .eq("user_id", user_id)
                .eq("feature_id", feature_id)
                .execute()
            )
            
            if existing.data:
                # Record already exists
                logger.info(f"Feature {feature_id} already seen by user {user_id}")
                return (True, False)
            
            # Insert new record
            insert_data = {
                "user_id": user_id,
                "feature_id": feature_id,
            }
            if source:
                insert_data["source"] = source
                
            self.client.table(TABLE_NAME).insert(insert_data).execute()
            
            logger.info(f"Marked feature {feature_id} as seen for user {user_id}")
            return (True, True)
            
        except Exception as e:
            # Handle unique constraint violation (race condition)
            if "duplicate key" in str(e).lower() or "unique constraint" in str(e).lower():
                logger.info(f"Feature {feature_id} already seen (concurrent insert)")
                return (True, False)
            
            logger.error(f"Failed to mark feature {feature_id} seen for user {user_id}: {e}")
            raise


# Singleton instance
_service_instance: Optional[FeatureVideoSeenService] = None


def get_feature_video_service() -> FeatureVideoSeenService:
    """Get or create the singleton service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = FeatureVideoSeenService()
    return _service_instance
