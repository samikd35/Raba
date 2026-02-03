from typing import List, Optional
from uuid import UUID

from ..system.core.supabase_client import get_supabase_client


class MatchingService:

    def __init__(self, use_service_role: bool = True):
        """Initialize matching service with Supabase client"""
        self.supabase = get_supabase_client(use_service_role=use_service_role).client
        self.use_service_role = use_service_role

    def create_matches_for_profile(self, profile_id: str):
        """
        Run matching algorithm for a newly approved profile and create user_relationships.
        Calls the PostgreSQL function create_matches_for_approved_profile.

        Returns list of matched profiles with their scores.
        """
        result = self.supabase.rpc(
            "create_matches_for_approved_profile",
            {"p_profile_id": profile_id}
        ).execute()

        return result.data

    def _enrich_languages(self, preferred_languages):
        """
        Enrich language preferences with language details using the PostgreSQL function.
        """
        if not preferred_languages:
            return []

        result = self.supabase.rpc(
            "enrich_language_preferences",
            {"prefs": preferred_languages}
        ).execute()

        return result.data

    def get_user_matches(self, user_id: str, limit: int = 50, offset: int = 0):
        """
        Get all matches for a user from user_relationships table.
        Returns matched users with their full profile information and match scores.
        """
        # First get the user's relationships where relationship = 'matched'
        # Note: Removed .or_() as Supabase Python client doesn't support it
        # Query both user1_id and user2_id separately and combine
        relationships_result_1 = (
            self.supabase.table("user_relationships")
            .select("id, user1_id, user2_id, relationship, metadata, created_at, updated_at")
            .eq("user1_id", user_id)
            .eq("relationship", "matched")
            .order("updated_at", desc=True)
            .execute()
        )
        relationships_result_2 = (
            self.supabase.table("user_relationships")
            .select("id, user1_id, user2_id, relationship, metadata, created_at, updated_at")
            .eq("user2_id", user_id)
            .eq("relationship", "matched")
            .order("updated_at", desc=True)
            .execute()
        )
        
        # Combine, deduplicate by id, sort by updated_at, and apply limit/offset
        all_relationships = {}
        for rel in (relationships_result_1.data or []) + (relationships_result_2.data or []):
            all_relationships[rel["id"]] = rel
        
        relationships_sorted = sorted(all_relationships.values(), key=lambda x: x.get("updated_at", ""), reverse=True)
        relationships = relationships_sorted[offset:offset + limit]
        if not relationships:
            return {"total": 0, "matches": []}

        # Extract matched user IDs and build response
        matches = []
        matched_user_ids = []

        for rel in relationships:
            # Determine which user is the matched user (not the requesting user)
            matched_user_id = (
                rel["user2_id"] if rel["user1_id"] == user_id else rel["user1_id"]
            )
            matched_user_ids.append(matched_user_id)

            # Extract match score from metadata
            match_score = None
            matched_at = None
            if rel.get("metadata"):
                match_score = rel["metadata"].get("match_score")
                matched_at = rel["metadata"].get("matched_at")

            matches.append({
                "match_id": rel["id"],
                "user_id": matched_user_id,
                "relationship": rel["relationship"],
                "match_score": match_score,
                "matched_at": matched_at,
            })

        # Get full profile information for matched users
        if matched_user_ids:
            profiles_result = (
                self.supabase.table("profiles")
                .select("user_id, last_approved_version_id")
                .in_("user_id", matched_user_ids)
                .eq("status", "approved")
                .execute()
            )

            # Get version IDs
            version_ids = [p["last_approved_version_id"] for p in profiles_result.data if p.get("last_approved_version_id")]

            if version_ids:
                # Get all profile_versions data
                versions_result = (
                    self.supabase.table("profile_versions")
                    .select("*")
                    .in_("id", version_ids)
                    .execute()
                )

                # Create a lookup dict mapping user_id to version data
                user_id_to_profile = {p["user_id"]: p["last_approved_version_id"] for p in profiles_result.data}
                version_lookup = {v["id"]: v for v in versions_result.data}

                # Enrich matches with full profile information
                for match in matches:
                    version_id = user_id_to_profile.get(match["user_id"])
                    if version_id and version_id in version_lookup:
                        version = version_lookup[version_id]

                        # Enrich languages
                        enriched_languages = self._enrich_languages(version.get("preferred_languages"))

                        # Add all profile version data to match
                        match["profile_data"] = {
                            **version,
                            "preferred_languages": enriched_languages,
                            "full_name": f"{version.get('first_name', '')} {version.get('last_name', '')}".strip()
                        }

        return {"total": len(matches), "matches": matches}
