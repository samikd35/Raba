from datetime import datetime
from typing import Optional
from fastapi import UploadFile
import logging

from ..system.core.supabase_client import get_supabase_client
from .supabase_storage import SupabaseStorageService
from .enum_suggestions_service import EnumSuggestionsService

logger = logging.getLogger(__name__)


class ProfileService:
    def __init__(self, use_service_role: bool = True):
        """Initialize service with Supabase client."""
        self.supabase = get_supabase_client(use_service_role=use_service_role).client
        self.suggestions_service = EnumSuggestionsService(use_service_role=use_service_role)
        self.use_service_role = use_service_role
        try:
            self.storage = SupabaseStorageService()
        except Exception as e:
            # Storage not configured - will skip file uploads
            logger.warning(f"Storage service not available: {str(e)}")
            self.storage = None

    # ---------- internal helpers ----------

    def _resp_data(self, resp, default=None):
        """
        Unwrap supabase .execute() responses across client versions:
          - v2: object with `.data`
          - v1: dict with ['data']
          - None: return default
        """
        if resp is None:
            return default
        if isinstance(resp, dict):
            return resp.get("data", default)
        return getattr(resp, "data", default)

    def _first_row(self, resp):
        data = self._resp_data(resp, default=[]) or []
        if isinstance(data, list):
            return data[0] if data else None
        # if the client returns a single object instead of a list
        return data

    def _enrich_languages(self, preferred_languages):
        """
        Enrich language preferences with language details using the PostgreSQL function.
        Returns enriched languages as a list.
        """
        if not preferred_languages:
            return []

        try:
            result = self.supabase.rpc(
                "enrich_language_preferences",
                {"prefs": preferred_languages}
            ).execute()
            return result.data if result.data else []
        except Exception as e:
            logger.warning(f"Failed to enrich languages: {str(e)}")
            return preferred_languages  # Return raw data as fallback

    # ---------- core ops ----------

    def ensure_profile_row(self, user_id: str):
        """Return the user's profiles row; create if missing."""
        existing = (
            self.supabase.table("profiles")
            .select("*")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        prof = self._first_row(existing)
        if prof:
            return prof

        # insert (no select() on modify ops)
        created = (
            self.supabase.table("profiles")
            .insert({"user_id": user_id, "status": "draft"})
            .execute()
        )
        prof = self._first_row(created)
        if prof:
            return prof

        # fallback read (handles race where another request created it)
        reread = (
            self.supabase.table("profiles")
            .select("*")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        return self._first_row(reread)

    async def save_draft(
        self, user_id: str, payload: dict, profile_picture: Optional[UploadFile] = None
    ):
        """
        Create a new draft version (immutable).

        Args:
            user_id: The user ID
            payload: Profile data
            profile_picture: Optional profile picture file to upload

        Returns:
            The created draft version
        """
        prof = self.ensure_profile_row(user_id)

        # Handle profile picture upload
        if profile_picture and self.storage:
            try:
                # Validate file type
                allowed_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
                import os

                file_ext = os.path.splitext(profile_picture.filename)[1].lower()
                if file_ext not in allowed_extensions:
                    raise ValueError(
                        f"Invalid file type. Allowed types: {', '.join(allowed_extensions)}"
                    )

                # Validate file size (max 5MB)
                max_size = 5 * 1024 * 1024  # 5MB
                contents = await profile_picture.read()
                if len(contents) > max_size:
                    raise ValueError("File size exceeds 5MB limit")

                # Upload to Supabase Storage
                picture_url = self.storage.upload_profile_picture(
                    contents, profile_picture.filename, user_id
                )

                # If there's an old profile picture, delete it
                old_picture_url = payload.get("profile_picture_url")
                if old_picture_url:
                    self.storage.delete_file(old_picture_url)

                # Update payload with new URL
                payload["profile_picture_url"] = picture_url

            except ValueError as e:
                # Re-raise validation errors
                raise
            except Exception as e:
                logger.error(f"Failed to upload profile picture: {str(e)}")
                raise RuntimeError(f"Failed to upload profile picture: {str(e)}")

        # Set default empty string for profile_picture_url if not provided (database requires NOT NULL)
        if "profile_picture_url" not in payload or payload["profile_picture_url"] is None:
            payload["profile_picture_url"] = ""

        version = {"profile_id": prof["id"], "status": "draft", **payload}
        out = self.supabase.table("profile_versions").insert(version).execute()
        created_version = self._first_row(out)

        # Record "other" value suggestions if any were provided
        if created_version:
            self._record_other_suggestions(
                user_id=user_id,
                version_id=created_version["id"],
                payload=payload
            )

        return created_version

    def submit_latest(self, user_id: str):
        """Submit the latest draft for review."""
        prof = self.ensure_profile_row(user_id)
        drafts = (
            self.supabase.table("profile_versions")
            .select("*")
            .eq("profile_id", prof["id"])
            .eq("status", "draft")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        draft = self._first_row(drafts)
        if not draft:
            raise ValueError("No draft to submit")

        self.supabase.table("profile_versions").update(
            {"status": "submitted", "submitted_at": datetime.utcnow().isoformat()}
        ).eq("id", draft["id"]).execute()

        self.supabase.table("profiles").update(
            {"status": "submitted", "updated_at": datetime.utcnow().isoformat()}
        ).eq("id", prof["id"]).execute()

        return {"ok": True, "version_id": draft["id"]}

    def get_my_profile(self, user_id: str):
        """Return profile row + last approved version + latest version (any status)."""
        prof_q = (
            self.supabase.table("profiles")
            .select("*")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        prof = self._first_row(prof_q)
        if not prof:
            return {"profile": None, "last_approved": None, "latest_version": None}

        last_approved = None
        last_id = prof.get("last_approved_version_id")
        if last_id:
            la_q = (
                self.supabase.table("profile_versions")
                .select("*")
                .eq("id", last_id)
                .limit(1)
                .execute()
            )
            last_approved = self._first_row(la_q)
            # Enrich languages for last_approved
            if last_approved and last_approved.get("preferred_languages"):
                last_approved["preferred_languages"] = self._enrich_languages(
                    last_approved["preferred_languages"]
                )

        latest_q = (
            self.supabase.table("profile_versions")
            .select("*")
            .eq("profile_id", prof["id"])
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        latest_version = self._first_row(latest_q)
        # Enrich languages for latest_version
        if latest_version and latest_version.get("preferred_languages"):
            latest_version["preferred_languages"] = self._enrich_languages(
                latest_version["preferred_languages"]
            )

        return {
            "profile": prof,
            "last_approved": last_approved,
            "latest_version": latest_version,
        }

    def get_public_profile(self, profile_id: str):
        """Public approved snapshot by profile id."""
        prof_q = (
            self.supabase.table("profiles")
            .select("*")
            .eq("id", profile_id)
            .limit(1)
            .execute()
        )
        prof = self._first_row(prof_q)
        if not prof:
            return None
        if prof.get("status") != "approved" or not prof.get("last_approved_version_id"):
            return None

        pv_q = (
            self.supabase.table("profile_versions")
            .select("*")
            .eq("id", prof["last_approved_version_id"])
            .limit(1)
            .execute()
        )
        version = self._first_row(pv_q)
        # Enrich languages
        if version and version.get("preferred_languages"):
            version["preferred_languages"] = self._enrich_languages(
                version["preferred_languages"]
            )
        return version

    def list_versions(
        self, user_id: str, status: Optional[str] = None, limit: int = 50
    ):
        """
        List profile versions for the caller (optionally filter by status).
        Status: draft | submitted | approved | rejected | all/None
        """
        prof = self.ensure_profile_row(user_id)
        q = (
            self.supabase.table("profile_versions")
            .select("*")
            .eq("profile_id", prof["id"])
            .order("created_at", desc=True)
            .limit(limit)
        )
        if status and status.lower() != "all":
            q = q.eq("status", status)
        resp = q.execute()
        versions = self._resp_data(resp, default=[]) or []
        # Enrich languages for each version
        for version in versions:
            if version.get("preferred_languages"):
                version["preferred_languages"] = self._enrich_languages(
                    version["preferred_languages"]
                )
        return versions

    def get_latest_version(self, user_id: str, status: Optional[str] = None):
        """Return the latest version for the caller (optionally filter by status)."""
        prof = self.ensure_profile_row(user_id)
        q = (
            self.supabase.table("profile_versions")
            .select("*")
            .eq("profile_id", prof["id"])
            .order("created_at", desc=True)
            .limit(1)
        )
        if status and status.lower() != "all":
            q = q.eq("status", status)
        resp = q.execute()
        version = self._first_row(resp)
        # Enrich languages
        if version and version.get("preferred_languages"):
            version["preferred_languages"] = self._enrich_languages(
                version["preferred_languages"]
            )
        return version

    def list_drafts(self, user_id: str, limit: int = 50):
        """Convenience: list draft versions only."""
        return self.list_versions(user_id, status="draft", limit=limit)

    def get_version(self, user_id: str, version_id: str):
        """Get a specific version that belongs to the caller."""
        prof = self.ensure_profile_row(user_id)
        resp = (
            self.supabase.table("profile_versions")
            .select("*")
            .eq("id", version_id)
            .eq("profile_id", prof["id"])
            .limit(1)
            .execute()
        )
        version = self._first_row(resp)
        # Enrich languages
        if version and version.get("preferred_languages"):
            version["preferred_languages"] = self._enrich_languages(
                version["preferred_languages"]
            )
        return version

    def submit_version(self, user_id: str, version_id: str):
        """
        Submit a draft version for admin review.
        Sets profile_versions.status = 'submitted' and profiles.status = 'submitted'.
        """
        prof = self.ensure_profile_row(user_id)
        pv_q = (
            self.supabase.table("profile_versions")
            .select("*")
            .eq("id", version_id)
            .eq("profile_id", prof["id"])
            .limit(1)
            .execute()
        )
        pv = self._first_row(pv_q)
        if not pv or pv.get("status") != "draft":
            raise ValueError("Draft not found or already submitted")

        self.supabase.table("profile_versions").update(
            {"status": "submitted", "submitted_at": datetime.utcnow().isoformat()}
        ).eq("id", version_id).execute()

        self.supabase.table("profiles").update(
            {"status": "submitted", "updated_at": datetime.utcnow().isoformat()}
        ).eq("id", prof["id"]).execute()

        return {"ok": True, "version_id": version_id}

    def get_current_approved(self, user_id: str):
        """
        Return the currently approved profile version for the caller
        (the version used for matching).
        """
        prof_q = (
            self.supabase.table("profiles")
            .select("*")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        prof = self._first_row(prof_q)
        if not prof or not prof.get("last_approved_version_id"):
            return None

        pv_q = (
            self.supabase.table("profile_versions")
            .select("*")
            .eq("id", prof["last_approved_version_id"])
            .limit(1)
            .execute()
        )
        version = self._first_row(pv_q)
        # Enrich languages
        if version and version.get("preferred_languages"):
            version["preferred_languages"] = self._enrich_languages(
                version["preferred_languages"]
            )
        return version

    def _record_other_suggestions(self, user_id: str, version_id: str, payload: dict):
        """
        Record suggestions for any "other" values submitted by the user.
        This is called after saving a draft to track custom enum values.
        """
        try:
            # Map of field names to enum types and field contexts
            other_field_mappings = [
                ("other_industries", "industries", None),
                ("other_responsibilities", "responsibilities", None),
                ("other_venture_stages", "venture_stages", "venture_stage"),
                ("other_preferred_venture_stages", "venture_stages", "preferred_venture_stage"),
                ("other_languages", "languages", None),
            ]

            # Record array-based "other" fields
            for field_name, enum_type, field_context in other_field_mappings:
                other_values = payload.get(field_name, [])
                if other_values and isinstance(other_values, list):
                    for value in other_values:
                        if value and isinstance(value, str) and value.strip():
                            try:
                                self.suggestions_service.record_suggestion(
                                    enum_type=enum_type,
                                    suggested_value=value.strip(),
                                    suggested_by=user_id,
                                    profile_version_id=version_id,
                                    field_context=field_context
                                )
                            except Exception as e:
                                logger.warning(f"Failed to record suggestion for {field_name}: {str(e)}")

            # Record single-value "other" fields for commitments
            commitment_mappings = [
                ("other_expected_commitment", "commitments", "expected"),
                ("other_preferred_commitment", "commitments", "preferred"),
            ]

            for field_name, enum_type, field_context in commitment_mappings:
                other_value = payload.get(field_name)
                if other_value and isinstance(other_value, str) and other_value.strip():
                    try:
                        self.suggestions_service.record_suggestion(
                            enum_type=enum_type,
                            suggested_value=other_value.strip(),
                            suggested_by=user_id,
                            profile_version_id=version_id,
                            field_context=field_context
                        )
                    except Exception as e:
                        logger.warning(f"Failed to record suggestion for {field_name}: {str(e)}")

        except Exception as e:
            # Don't fail the draft save if suggestion recording fails
            logger.error(f"Error recording other suggestions: {str(e)}")
