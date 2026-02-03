"""
Venture Builder Disputes API

Handles dispute management including:
- Checking dispute eligibility
- Creating disputes for completed sessions
- Viewing user disputes
- Admin dispute management and resolution
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from .exceptions import VBBaseException
from .models import (
    CanOpenDisputeResponse,
    DisputeCreateRequest,
    DisputeResponse,
    DisputeUpdateRequest,
    DisputeWithDetailsResponse,
)
from .service import get_vb_service
from .utils import handle_vb_exception
from src.mint.api.auth_v2.utils import get_admin_user, get_current_user

router = APIRouter(prefix="/venture-builder", tags=["Venture Builder: Disputes"])

# Singleton service instance
vb_service = get_vb_service()


@router.get("/sessions/{session_id}/can-dispute")
async def check_can_open_dispute(
    session_id: UUID,
    current_user: dict = Depends(get_current_user),
):
    """
    User: Check if they can open a dispute for a specific session.

    Returns can_open_dispute flag and reason if not eligible.
    Used by frontend to show/hide "Report a problem" button.
    """
    try:
        result = vb_service.check_can_open_dispute(
            str(session_id),
            current_user["user_id"]
        )
        return {"success": True, "data": CanOpenDisputeResponse(**result).dict(), "error": None}
    except VBBaseException as e:
        handle_vb_exception(e)


@router.post("/sessions/{session_id}/disputes", status_code=status.HTTP_201_CREATED)
async def create_dispute(
    session_id: UUID,
    data: DisputeCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    User: Create a dispute for a completed session.

    Requirements:
    - Session must be completed
    - User must be the one who booked the session
    - No existing dispute for this session
    - If reason is 'other', custom_reason must be provided
    """
    try:
        dispute = vb_service.create_dispute(
            session_id=str(session_id),
            user_id=current_user["user_id"],
            tenant_id=current_user["tenant_id"],
            reason=data.reason.value,
            custom_reason=data.custom_reason,
            description=data.description,
        )
        return {"success": True, "data": DisputeResponse(**dispute).dict(), "error": None}
    except VBBaseException as e:
        handle_vb_exception(e)


@router.get("/disputes")
async def get_my_disputes(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    """
    User: Get all disputes they have created with pagination.

    Returns list of disputes with metadata (total_count, page, total_pages).
    """
    try:
        result = vb_service.get_user_disputes(
            user_id=current_user["user_id"],
            tenant_id=current_user["tenant_id"],
            page=page,
            page_size=page_size,
        )
        # Convert disputes to response models
        result["disputes"] = [DisputeResponse(**d).dict() for d in result["disputes"]]
        return {"success": True, "data": result, "error": None}
    except VBBaseException as e:
        handle_vb_exception(e)


@router.get("/disputes/{dispute_id}")
async def get_dispute_detail(
    dispute_id: UUID,
    current_user: dict = Depends(get_current_user),
):
    """
    User: Get details of a specific dispute.

    User must be the creator of the dispute.
    """
    try:
        dispute = vb_service.get_dispute_by_id(
            str(dispute_id),
            current_user["user_id"]
        )
        return {"success": True, "data": DisputeResponse(**dispute).dict(), "error": None}
    except VBBaseException as e:
        handle_vb_exception(e)


@router.get("/admin/disputes")
async def get_all_disputes(
    status: Optional[str] = Query(None),
    vb_id: Optional[UUID] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(get_admin_user),
):
    """
    Admin: Get all disputes with filters and pagination.

    Filters:
    - status: Filter by dispute status (submitted, under_review, resolved)
    - vb_id: Filter by venture builder
    - start_date: Filter disputes created after this date
    - end_date: Filter disputes created before this date

    Returns disputes with full session and user details.
    """
    try:
        result = vb_service.get_admin_disputes(
            status=status,
            vb_id=str(vb_id) if vb_id else None,
            start_date=start_date,
            end_date=end_date,
            page=page,
            page_size=page_size,
        )
        # Convert disputes to response models
        result["disputes"] = [DisputeWithDetailsResponse(**d).dict() for d in result["disputes"]]
        return {"success": True, "data": result, "error": None}
    except VBBaseException as e:
        handle_vb_exception(e)


@router.patch("/admin/disputes/{dispute_id}")
async def update_dispute(
    dispute_id: UUID,
    data: DisputeUpdateRequest,
    current_user: dict = Depends(get_admin_user),
):
    """
    Admin: Update dispute status and add admin notes.

    Can update:
    - status: Change dispute status (submitted → under_review → resolved)
    - admin_notes: Add admin's notes about the resolution

    When status is changed to 'resolved', resolved_by and resolved_at are automatically set.
    """
    try:
        dispute = vb_service.update_dispute_status(
            dispute_id=str(dispute_id),
            admin_user_id=current_user["user_id"],
            status=data.status.value if data.status else None,
            admin_notes=data.admin_notes,
        )
        return {"success": True, "data": DisputeResponse(**dispute).dict(), "error": None}
    except VBBaseException as e:
        handle_vb_exception(e)
