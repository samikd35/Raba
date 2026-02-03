from fastapi import APIRouter, Depends, Query

from ..auth_v2.utils import get_current_user
from ..system.core.supabase_client import get_supabase_client
from .matching_service import MatchingService

router = APIRouter(prefix="/profiles/me", tags=["profiles.matches"])

supabase = get_supabase_client(use_service_role=True).client
matching_service = MatchingService(use_service_role=True)


@router.get("/matches")
def get_matches(
    k: int = Query(20, ge=1, le=100), current_user: dict = Depends(get_current_user)
):
    # map current user -> profiles.id
    prof = (
        supabase.table("profiles")
        .select("id")
        .eq("user_id", current_user["user_id"])
        .maybe_single()
        .execute()
        .data
    )
    if not prof:
        return {"matches": []}
    res = supabase.rpc("get_matches", {"p_profile_id": prof["id"], "p_k": k}).execute()
    matches = res.data or []

    # Enrich matches with user_ids
    if matches:
        profile_ids = [m["candidate_profile_id"] for m in matches]
        profiles = (
            supabase.table("profiles")
            .select("id, user_id")
            .in_("id", profile_ids)
            .execute()
            .data or []
        )
        # Create lookup map
        profile_to_user = {p["id"]: p["user_id"] for p in profiles}
        # Add user_id to each match
        for match in matches:
            match["user_id"] = profile_to_user.get(match["candidate_profile_id"])

    return {"matches": matches}


@router.get("/matches/by-threshold")
def get_matches_by_threshold(
    threshold: float = Query(70.0, ge=0, le=100),
    current_user: dict = Depends(get_current_user),
):
    # map current user -> profiles.id
    prof = (
        supabase.table("profiles")
        .select("id")
        .eq("user_id", current_user["user_id"])
        .maybe_single()
        .execute()
        .data
    )
    if not prof:
        return {"matches": []}
    res = supabase.rpc(
        "get_matches_by_threshold",
        {"p_profile_id": prof["id"], "p_threshold": threshold},
    ).execute()
    matches = res.data or []

    # Enrich matches with user_ids
    if matches:
        profile_ids = [m["candidate_profile_id"] for m in matches]
        profiles = (
            supabase.table("profiles")
            .select("id, user_id")
            .in_("id", profile_ids)
            .execute()
            .data or []
        )
        # Create lookup map
        profile_to_user = {p["id"]: p["user_id"] for p in profiles}
        # Add user_id to each match
        for match in matches:
            match["user_id"] = profile_to_user.get(match["candidate_profile_id"])

    return {"matches": matches}


@router.get("/confirmed-matches")
def get_confirmed_matches(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    """
    Get user's confirmed matches from user_relationships table.
    These are matches that have been created by the matching algorithm
    and stored in the user_relationships table.
    Only accessible to users with approved profiles.
    """
    # Check if user has an approved profile
    profile = (
        supabase.table("profiles")
        .select("id, status")
        .eq("user_id", current_user["user_id"])
        .limit(1)
        .execute()
        .data
    )

    if not profile or profile[0].get("status") != "approved":
        return {
            "error": "Only users with approved profiles can access confirmed matches",
            "total": 0,
            "matches": [],
            "page": page,
            "page_size": page_size,
            "total_pages": 0
        }

    # Calculate offset from page
    offset = (page - 1) * page_size

    # Get matches
    result = matching_service.get_user_matches(
        user_id=current_user["user_id"],
        limit=page_size,
        offset=offset
    )

    # Calculate total pages
    total = result.get("total", 0)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return {
        "matches": result.get("matches", []),
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }
