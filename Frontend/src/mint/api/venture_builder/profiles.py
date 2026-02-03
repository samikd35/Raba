"""
Venture Builder Profiles API

Handles VB profile management including:
- Profile creation, update, deletion
- Public browsing and search
- Admin approval and pricing management
"""

import json
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status

from .exceptions import VBAccessDeniedError, VBBaseException, VBNotFoundError, VBValidationError
from .models import (
    VBApprovalRequest,
    VBListFilters,
    VBListingItem,
    VBListResponse,
    VBPendingListResponse,
    VBPricingUpdate,
    VBProfileCreate,
    VBProfileResponse,
    VBProfileUpdate,
    VBPublishRequest,
    VBRoleMismatchItem,
    VBRoleMismatchResponse,
    VBRoleRevertResponse,
    VBRoleUpdateRequest,
    VBRoleUpdateResponse,
)
from .service import get_vb_service
from .utils import handle_vb_exception
from src.mint.api.auth_v2.utils import (
    get_admin_user,
    get_current_user,
    get_vb_or_admin_user,
    get_vb_or_super_admin_user,
)

router = APIRouter(prefix="/venture-builder", tags=["Venture Builder: Profiles"])

# Singleton service instance
vb_service = get_vb_service()


@router.post("/profile/create", status_code=status.HTTP_201_CREATED)
async def create_vb_profile(
    data: str = Form(..., description="JSON string containing profile data"),
    invitation_token: str = Query(..., description="VB invitation token from email"),
    profile_picture: Optional[UploadFile] = File(None, description="Optional profile picture file"),
    current_user: dict = Depends(get_current_user),
):
    """
    Create a VB profile after accepting invitation.

    Requires:
    - Valid invitation token (48-hour expiration)
    - User must be authenticated
    - Email in token must match current user's email
    - data: JSON string containing profile data
    - profile_picture: Optional profile picture file (jpg, jpeg, png, gif, webp, bmp, max 5MB)
    """
    try:
        # Parse JSON data
        try:
            data_dict = json.loads(data)
            profile_data = VBProfileCreate(**data_dict)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON data: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid profile data: {str(e)}")

        # Validate invitation token first
        validation = vb_service.validate_invitation_token(invitation_token)
        if not validation["valid"]:
            raise VBValidationError(validation.get("error", "Invalid invitation token"))

        # Ensure email matches
        if validation["email"] != current_user["email"]:
            raise VBAccessDeniedError("Invitation email does not match your account")

        # Create profile with file upload
        profile = await vb_service.create_vb_profile(
            user_id=current_user["user_id"],
            name=profile_data.name,
            contact_email=profile_data.contact_email,
            main_expertise=profile_data.main_expertise,
            short_intro=profile_data.short_intro,
            work_experience=[item.dict() for item in profile_data.work_experience],
            biography=profile_data.biography,
            linkedin_url=str(profile_data.linkedin_url) if profile_data.linkedin_url else None,
            expertise_ids=[str(id) for id in profile_data.expertise_ids],
            other_expertise=profile_data.other_expertise,
            profile_picture=profile_picture,
        )

        # Mark invitation as accepted
        vb_service.mark_invitation_accepted(invitation_token, current_user["user_id"])

        return {
            "success": True,
            "data": VBProfileResponse(**profile).dict(),
            "error": None
        }
    except VBBaseException as e:
        handle_vb_exception(e)


@router.patch("/profile")
async def update_vb_profile(
    data: Optional[str] = Form(None, description="Optional JSON string containing profile data"),
    profile_picture: Optional[UploadFile] = File(None, description="Optional new profile picture file"),
    current_user: dict = Depends(get_vb_or_admin_user),
):
    """
    VB or Admin: Update own VB profile (partial update).

    Args:
        data: Optional JSON string containing profile data fields to update
        profile_picture: Optional new profile picture file (jpg, jpeg, png, gif, webp, bmp, max 5MB)
    """
    try:
        # Get VB profile for current user
        vb_profile = vb_service.get_vb_by_user_id(current_user["user_id"])
        if not vb_profile:
            raise VBNotFoundError("VB profile not found for current user")

        # Parse JSON data if provided
        profile_data = None
        if data:
            try:
                data_dict = json.loads(data)
                profile_data = VBProfileUpdate(**data_dict)
            except json.JSONDecodeError as e:
                raise HTTPException(status_code=400, detail=f"Invalid JSON data: {str(e)}")
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid profile data: {str(e)}")

        # Prepare update arguments
        update_kwargs = {
            "vb_id": vb_profile["id"],
            "user_id": current_user["user_id"],
        }

        # Only add profile_picture if it's provided
        if profile_picture:
            update_kwargs["profile_picture"] = profile_picture

        if profile_data:
            if profile_data.contact_email is not None:
                update_kwargs["contact_email"] = profile_data.contact_email
            if profile_data.name is not None:
                update_kwargs["name"] = profile_data.name
            if profile_data.main_expertise is not None:
                update_kwargs["main_expertise"] = profile_data.main_expertise
            if profile_data.short_intro is not None:
                update_kwargs["short_intro"] = profile_data.short_intro
            if profile_data.biography is not None:
                update_kwargs["biography"] = profile_data.biography
            if profile_data.linkedin_url is not None:
                update_kwargs["linkedin_url"] = str(profile_data.linkedin_url)
            if profile_data.work_experience is not None:
                update_kwargs["work_experience"] = [item.dict() for item in profile_data.work_experience]
            if profile_data.expertise_ids is not None:
                update_kwargs["expertise_ids"] = [str(id) for id in profile_data.expertise_ids]
            if profile_data.other_expertise is not None:
                update_kwargs["other_expertise"] = profile_data.other_expertise

        profile = await vb_service.update_vb_profile(**update_kwargs)
        return {
            "success": True,
            "data": VBProfileResponse(**profile).dict(),
            "error": None
        }
    except VBBaseException as e:
        handle_vb_exception(e)


@router.get("/profile")
async def get_my_vb_profile(
    current_user: dict = Depends(get_vb_or_admin_user),
):
    """
    VB or Admin: Get own VB profile.
    """
    try:
        profile = vb_service.get_vb_by_user_id(current_user["user_id"])
        if not profile:
            raise VBNotFoundError("VB profile not found")

        # Check if profile is incomplete (pending_profile status)
        if profile.get("status") == "pending_profile":
            raise VBProfileIncompleteError(
                "Profile incomplete. Please complete your profile before accessing this information."
            )

        return {
            "success": True,
            "data": VBProfileResponse(**profile).dict(),
            "error": None
        }
    except VBBaseException as e:
        handle_vb_exception(e)


@router.delete("/profile", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_vb_profile(
    current_user: dict = Depends(get_vb_or_super_admin_user),
):
    """
    VB or Super Admin: Delete own VB profile.
    """
    try:
        user_role = current_user["roles"][0] if current_user.get("roles") else None

        vb_profile = vb_service.get_vb_by_user_id(current_user["user_id"])
        if not vb_profile:
            raise VBNotFoundError("VB profile not found")

        vb_service.delete_vb_profile(vb_profile["id"], user_role=user_role)
    except VBBaseException as e:
        handle_vb_exception(e)


@router.get("/browse")
async def browse_venture_builders(
    expertise_ids: Optional[List[UUID]] = Query(None),
    search_query: Optional[str] = Query(None, max_length=200),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    """
    Public: Browse active Venture Builders with filtering and pagination.
    """
    try:
        filters = VBListFilters(
            expertise_ids=expertise_ids,
            search_query=search_query,
            page=page,
            page_size=page_size,
        )

        user_role = current_user.get("roles", [])[0] if current_user.get("roles") else None
        exclude_vb_id = None
        if user_role == "venture_builder":
            vb_profile = vb_service.get_vb_by_user_id(current_user["user_id"])
            if vb_profile and vb_profile.get("id"):
                exclude_vb_id = str(vb_profile.get("id"))

        result = vb_service.browse_vbs(
            expertise_ids=[str(id) for id in filters.expertise_ids] if filters.expertise_ids else None,
            search_query=filters.search_query,
            page=filters.page,
            page_size=filters.page_size,
            exclude_vb_id=exclude_vb_id,
        )

        list_response = VBListResponse(
            total=result["total"],
            items=result["items"],
            page=result["page"],
            page_size=result["page_size"],
        )

        return {
            "success": True,
            "data": list_response.dict(),
            "error": None
        }
    except VBBaseException as e:
        handle_vb_exception(e)


@router.get("/browse/{vb_id}")
async def get_vb_details(vb_id: UUID):
    """
    Public: Get detailed VB profile for viewing.
    """
    try:
        profile = vb_service.get_vb_profile(str(vb_id))

        # Check if profile is incomplete (missing required fields)
        if not profile.get("name") or not profile.get("main_expertise") or not profile.get("short_intro"):
            raise VBNotFoundError("VB profile not found or incomplete")

        return {
            "success": True,
            "data": VBProfileResponse(**profile).dict(),
            "error": None
        }
    except VBBaseException as e:
        handle_vb_exception(e)


@router.post("/admin/vb/{vb_id}/approve")
async def approve_vb(
    vb_id: UUID,
    data: VBApprovalRequest,
    current_user: dict = Depends(get_admin_user),
):
    """
    Admin only: Approve a VB profile and set pricing.

    Transitions VB from 'pending_admin_review' to 'active'.
    """
    try:
        profile = vb_service.approve_vb(
            vb_id=str(vb_id),
            credit_price_per_hour=data.credit_price_per_hour,
            calendar_booking_url=data.calendar_booking_url,
        )
        return {
            "success": True,
            "data": VBProfileResponse(**profile).dict(),
            "error": None
        }
    except VBBaseException as e:
        handle_vb_exception(e)


@router.get("/admin/vb/role-mismatches", response_model=VBRoleMismatchResponse)
async def list_vb_role_mismatches(
    current_user: dict = Depends(get_admin_user),
):
    """
    Admin only: List active VB profiles whose user role is not venture_builder.
    """
    try:
        rows = vb_service.list_active_vb_role_mismatches()
        items = [
            VBRoleMismatchItem(
                vb_id=row.get("id"),
                user_id=row.get("user_id"),
                vb_name=row.get("name"),
                contact_email=row.get("contact_email"),
                vb_status=row.get("status"),
                user_role=(row.get("user_profiles") or {}).get("role"),
                user_email=(row.get("user_profiles") or {}).get("email"),
            )
            for row in rows
        ]
        return {"items": items, "total": len(items)}
    except VBBaseException as e:
        handle_vb_exception(e)


@router.get("/admin/vb/pending-approval-role-mismatches", response_model=VBRoleMismatchResponse)
async def list_pending_vb_role_mismatches(
    current_user: dict = Depends(get_admin_user),
):
    """
    Admin only: List pending VBs whose user role is venture_builder.
    """
    try:
        rows = vb_service.list_pending_vb_role_mismatches()
        items = [
            VBRoleMismatchItem(
                vb_id=row.get("id"),
                user_id=row.get("user_id"),
                vb_name=row.get("name"),
                contact_email=row.get("contact_email"),
                vb_status=row.get("status"),
                user_role=(row.get("user_profiles") or {}).get("role"),
                user_email=(row.get("user_profiles") or {}).get("email"),
            )
            for row in rows
        ]
        return {"items": items, "total": len(items)}
    except VBBaseException as e:
        handle_vb_exception(e)


@router.post("/admin/vb/assign-roles", response_model=VBRoleUpdateResponse)
async def assign_vb_roles(
    data: VBRoleUpdateRequest,
    current_user: dict = Depends(get_admin_user),
):
    """
    Admin only: Assign venture_builder role to provided user IDs.
    """
    try:
        result = vb_service.assign_vb_roles(data.user_ids)
        return result
    except VBBaseException as e:
        handle_vb_exception(e)


@router.post("/admin/vb/revert-roles", response_model=VBRoleRevertResponse)
async def revert_vb_roles(
    data: VBRoleUpdateRequest,
    current_user: dict = Depends(get_admin_user),
):
    """
    Admin only: Revert venture_builder role to user for provided user IDs.
    """
    try:
        result = vb_service.revert_vb_roles(data.user_ids)
        return result
    except VBBaseException as e:
        handle_vb_exception(e)


@router.patch("/admin/vb/{vb_id}/pricing")
async def update_vb_pricing(
    vb_id: UUID,
    data: VBPricingUpdate,
    current_user: dict = Depends(get_admin_user),
):
    """
    Admin only: Update VB's credit pricing.
    """
    try:
        profile = vb_service.update_vb_pricing(
            vb_id=str(vb_id),
            credit_price_per_hour=data.credit_price_per_hour,
        )
        return {
            "success": True,
            "data": VBProfileResponse(**profile).dict(),
            "error": None
        }
    except VBBaseException as e:
        handle_vb_exception(e)


@router.patch("/admin/vb/{vb_id}/publish")
async def publish_unpublish_vb(
    vb_id: UUID,
    data: VBPublishRequest,
    current_user: dict = Depends(get_admin_user),
):
    """
    Admin only: Publish or unpublish a VB.

    Toggles between 'active' and 'inactive' status.
    """
    try:
        user_role = current_user["roles"][0] if current_user.get("roles") else None

        if data.is_active:
            profile = vb_service.activate_vb(str(vb_id), user_role=user_role)
        else:
            profile = vb_service.deactivate_vb(str(vb_id), user_role=user_role)
        return {
            "success": True,
            "data": VBProfileResponse(**profile).dict(),
            "error": None
        }
    except VBBaseException as e:
        handle_vb_exception(e)


@router.get("/admin/vb/pending", response_model=VBPendingListResponse)
async def list_pending_vbs(
    current_user: dict = Depends(get_admin_user),
):
    """
    Admin only: List all VB profiles pending admin review.

    Returns VBs with status 'pending_admin_review' who have submitted their profiles
    and are waiting for admin approval.

    Success response:
        {
            "success": true,
            "data": [...],
            "error": null
        }

    Error response:
        {
            "success": false,
            "data": null,
            "error": "Error message"
        }
    """
    pending_vbs = vb_service.list_pending_vbs()

    # Filter out VBs with incomplete profiles (missing required fields)
    # Only include VBs that have completed their profile submission
    complete_profiles = []
    for vb in pending_vbs:
        if vb.get("name") and vb.get("main_expertise") and vb.get("short_intro"):
            complete_profiles.append(VBProfileResponse(**vb))

    return VBPendingListResponse(
        success=True,
        data=complete_profiles,
        error=None
    )
