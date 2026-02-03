from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Query, UploadFile
from typing import Optional
import json

from ..auth_v2.utils import get_current_user
from .models import DraftProfileIn
from .profiles_service import ProfileService

router = APIRouter(prefix="/profiles/me", tags=["profiles.me"])
profile_service = ProfileService()


@router.get("/")
def get_me_profile(current_user: dict = Depends(get_current_user)):
    return profile_service.get_my_profile(current_user["user_id"])


@router.post("/save-draft")
async def save_draft(
    data: str = Form(...),
    profile_picture: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user),
):
    """
    Save a draft profile.

    Args:
        data: JSON string containing profile data
        profile_picture: Optional profile picture file
        current_user: Authenticated user

    Returns:
        The saved draft profile version
    """
    try:
        # Parse the JSON data
        payload_dict = json.loads(data)

        # Validate the data using Pydantic model
        payload = DraftProfileIn(**payload_dict)

        # Save the draft with optional file upload
        return await profile_service.save_draft(
            current_user["user_id"],
            payload.dict(),
            profile_picture
        )
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON data: {str(e)}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/submit")
def submit_profile(current_user: dict = Depends(get_current_user)):
    try:
        return profile_service.submit_latest(current_user["user_id"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/versions")
def list_versions(
    status: str = Query("all", description="draft|submitted|approved|all"),
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
):
    """List versions for the caller (optionally filter by status)."""
    return {
        "items": profile_service.list_versions(
            current_user["user_id"], status=status, limit=limit
        )
    }


@router.get("/versions/latest")
def latest_version(
    status: str = Query("all", description="draft|submitted|approved|all"),
    current_user: dict = Depends(get_current_user),
):
    """Get the latest version (optionally filter by status)."""
    v = profile_service.get_latest_version(current_user["user_id"], status=status)
    if not v:
        raise HTTPException(status_code=404, detail="No version found")
    return v


@router.get("/drafts")
def list_drafts(
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
):
    """List draft versions only."""
    return {"items": profile_service.list_drafts(current_user["user_id"], limit=limit)}


@router.get("/versions/{version_id}")
def get_version(
    version_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get a specific version that belongs to the caller."""
    v = profile_service.get_version(current_user["user_id"], version_id)
    if not v:
        raise HTTPException(status_code=404, detail="Version not found")
    return v


@router.post("/me/versions/{version_id}/submit")
def submit_version(
    version_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Submit a specific draft version for admin review."""
    try:
        return profile_service.submit_version(current_user["user_id"], version_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/me/approved")
def my_current_approved(
    current_user: dict = Depends(get_current_user),
):
    """Return the caller's current approved version (used for matching)."""
    v = profile_service.get_current_approved(current_user["user_id"])
    if not v:
        raise HTTPException(status_code=404, detail="No approved version")
    return v


@router.get("/{profile_id}")
def public_profile(profile_id: str):
    out = profile_service.get_public_profile(profile_id)
    if not out:
        raise HTTPException(status_code=404, detail="Profile not available")
    return out
