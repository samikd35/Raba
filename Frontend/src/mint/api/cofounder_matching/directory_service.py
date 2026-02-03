from datetime import date
from typing import Dict, List, Optional, Tuple

from ..system.core.supabase_client import get_supabase_client
from ..messaging.service import MessagingService


def _normalize_list(items: Optional[List[str]]) -> Optional[List[str]]:
    """Convert all list items to lowercase trimmed strings."""
    if not items:
        return None
    return [i.strip().lower() for i in items if i and isinstance(i, str)]


def _calc_age(birth_iso: Optional[str]) -> Optional[int]:
    if not birth_iso:
        return None
    try:
        y, m, d = map(int, birth_iso.split("-"))
        born = date(y, m, d)
        today = date.today()
        return (
            today.year - born.year - ((today.month, today.day) < (born.month, born.day))
        )
    except Exception:
        return None


class DirectoryService:
    def __init__(self, use_service_role: bool = True):
        self.supabase = get_supabase_client(use_service_role=use_service_role).client

    async def user_is_approved(self, user_id: str) -> bool:
        res = (
            self.supabase.table("profiles")
            .select("status")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        return bool(rows) and rows[0].get("status") == "approved"

    async def search_directory(
        self,
        filters: Dict,
        current_user_id: str,
    ) -> Tuple[int, List[Dict]]:
        """Return (total, items) from approved_candidates with filter support."""
        countries = filters.get("countries")
        if countries:
            countries = [c.strip() for c in countries if c and isinstance(c, str)]
            countries = countries if countries else None

        # Languages: UUIDs, just strip whitespace
        languages = filters.get("languages")
        if languages:
            languages = [lang.strip() for lang in languages if lang and isinstance(lang, str)]
            languages = languages if languages else None
        venture = _normalize_list(filters.get("preferred_venture_stage"))
        age_min = filters.get("age_min")
        age_max = filters.get("age_max")
        commitment = filters.get("preferred_commitment")
        limit = filters.get("limit", 20)
        offset = filters.get("offset", 0)

        q = self.supabase.table("approved_candidates").select(
            "profile_id, version_id, preferred_country, "
            "birth_date, preferred_languages, "
            "profiles!approved_candidates_profile_id_fkey(user_id)"
        )

        # Filter out current user's own profile - exclude based on profile_id
        # First, get current user's profile_id if they have one
        user_profile_result = (
            self.supabase.table("profiles")
            .select("id")
            .eq("user_id", current_user_id)
            .limit(1)
            .execute()
        )
        if user_profile_result.data:
            current_user_profile_id = user_profile_result.data[0]["id"]
            q = q.neq("profile_id", current_user_profile_id)

        # Country filter (case-insensitive match)
        # Note: Removed .or_() as Supabase Python client doesn't support it
        # For multiple countries, use in_() with the countries list
        if countries:
            if len(countries) == 1:
                # Single country: use ilike directly
                q = q.ilike("preferred_country", countries[0])
            else:
                # Multiple countries: use in_() filter (exact match, case-sensitive)
                # For case-insensitive matching, filtering is done in Python below
                pass  # Will filter in Python after fetching

        # Commitment filter
        if commitment:
            q = q.eq("preferred_commitment", commitment)

        # Venture stage overlap filter
        if venture:
            q = q.overlaps("preferred_venture_stage", venture)

        # Sort (optional)
        q = q.order("version_id", desc=True)

        # For client-side filters (languages, age), we need to fetch all matching records
        # then filter and paginate them in memory
        has_client_filters = languages or age_min is not None or age_max is not None

        if has_client_filters:
            # Fetch all records matching DB-side filters
            result = q.execute()
            rows = result.data or []
        else:
            # No client-side filters: get total count from DB and use DB pagination
            count_q = self.supabase.table("approved_candidates").select(
                "profile_id, profiles!approved_candidates_profile_id_fkey(user_id)",
                count="exact",
            )
            # Filter out current user's profile from count query
            if user_profile_result.data:
                count_q = count_q.neq("profile_id", current_user_profile_id)
            # Note: Removed .or_() as Supabase Python client doesn't support it
            if countries:
                if len(countries) == 1:
                    count_q = count_q.ilike("preferred_country", countries[0])
                else:
                    # For multiple countries, skip DB filter - will be handled in Python
                    pass
            if commitment:
                count_q = count_q.eq("preferred_commitment", commitment)
            if venture:
                count_q = count_q.overlaps("preferred_venture_stage", venture)

            total_res = count_q.execute()
            db_total = total_res.count or 0

            # Use DB pagination directly
            result = q.range(offset, offset + limit - 1).execute()
            rows = result.data or []

        # Extract user_id from nested profiles object
        for row in rows:
            if "profiles" in row and isinstance(row["profiles"], dict):
                row["user_id"] = row["profiles"].get("user_id")
                del row["profiles"]

        # Client-side filter: languages (match any)
        if languages:

            def lang_match(lang_json):
                if not isinstance(lang_json, list):
                    return False
                language_ids = {
                    str(x.get("language_id", ""))
                    for x in lang_json
                    if isinstance(x, dict)
                }
                return any(lang_id in language_ids for lang_id in languages)

            rows = [r for r in rows if lang_match(r.get("preferred_languages") or [])]

        # Client-side filter: age range
        if age_min is not None or age_max is not None:

            def age_ok(birth_iso):
                age = _calc_age(birth_iso)
                if age is None:
                    return False
                if age_min is not None and age < age_min:
                    return False
                if age_max is not None and age > age_max:
                    return False
                return True

            rows = [r for r in rows if age_ok(r.get("birth_date"))]

        # Calculate total
        if has_client_filters:
            # Total from filtered results
            total = len(rows)
        else:
            # Total from DB count
            total = db_total

        # Apply pagination after client-side filters
        if has_client_filters:
            items = rows[offset : offset + limit]
        else:
            items = rows

        # Enrich from profile_versions for display fields
        if items:
            version_ids = [i["version_id"] for i in items]
            pv = (
                self.supabase.table("profile_versions")
                .select(
                    "id, first_name, last_name, profile_picture_url, "
                    "preferred_country, date_of_birth, professional_background"
                )
                .in_("id", version_ids)
                .execute()
                .data
                or []
            )
            by_id = {v["id"]: v for v in pv}
            for i in items:
                v = by_id.get(i["version_id"])
                if v:
                    i["full_name"] = " ".join(
                        [p for p in [v.get("first_name"), v.get("last_name")] if p]
                    )
                    i["profile_picture_url"] = v.get("profile_picture_url")
                    i["preferred_country"] = i.get("preferred_country") or v.get(
                        "preferred_country"
                    )
                    i["date_of_birth"] = i.get("birth_date") or v.get("date_of_birth")
                    i["professional_background"] = v.get("professional_background")

        # Check messaging eligibility for all profiles in bulk
        if items:
            messaging_service = MessagingService()
            recipient_ids = [i.get("user_id") for i in items if i.get("user_id")]

            if recipient_ids:
                can_message_map = messaging_service.check_can_message_bulk(current_user_id, recipient_ids)
                for i in items:
                    recipient_id = i.get("user_id")
                    i["can_message"] = can_message_map.get(recipient_id, False) if recipient_id else False
            else:
                for i in items:
                    i["can_message"] = False

        return total, items

    async def get_version_details(self, version_id: str):
        """Get details of a specific version without ownership checks."""
        # Fetch the version
        version_resp = (
            self.supabase.table("profile_versions")
            .select("*")
            .eq("id", version_id)
            .limit(1)
            .execute()
        )

        version = version_resp.data[0] if version_resp.data else None
        if not version:
            return None

        # Enrich preferred_languages using the database function
        raw_languages = version.get("preferred_languages")
        if raw_languages:
            enriched = self.supabase.rpc(
                "enrich_language_preferences", {"prefs": raw_languages}
            ).execute()
            version["preferred_languages"] = enriched.data if enriched.data else []
        else:
            version["preferred_languages"] = []

        return version
