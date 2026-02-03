"""
Venture Builder Sessions API

Handles session booking and management including:
- Project selection for booking
- Credit checking before booking
- Creating bookings
- Viewing sessions for VBs and users
- Completing and canceling sessions
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from .exceptions import VBAccessDeniedError, VBBaseException, VBNotFoundError
from .models import (
    CreditCheckResponse,
    ProjectSelectionItem,
    SessionFilters,
    VBBookingCreate,
    VBBookingResponse,
    VBSessionDetail,
    VBSessionCancelRequest,
)
from .service import get_vb_service
from .utils import handle_vb_exception
from src.mint.api.auth_v2.utils import get_current_user, get_vb_or_admin_user

router = APIRouter(prefix="/venture-builder", tags=["Venture Builder: Sessions"])

# Singleton service instance
vb_service = get_vb_service()


@router.get("/booking/projects")
async def get_tenant_projects(
    current_user: dict = Depends(get_current_user),
):
    """
    Get projects for booking (scoped to user's tenant).
    """
    try:
        tenant_id = current_user["tenant_id"]
        projects = vb_service.get_tenant_projects(tenant_id)
        return {
            "success": True,
            "data": [ProjectSelectionItem(**proj).dict() for proj in projects],
            "error": None
        }
    except VBBaseException as e:
        handle_vb_exception(e)


@router.get("/booking/credits/{vb_id}")
async def check_booking_credits(
    vb_id: UUID,
    current_user: dict = Depends(get_current_user),
):
    """
    Check if user has sufficient credits to book a session with a VB.
    """
    try:
        tenant_id = current_user["tenant_id"]
        result = vb_service.check_credits(
            tenant_id=tenant_id,
            user_id=current_user["user_id"],
            venture_builder_id=str(vb_id),
        )
        return {
            "success": True,
            "data": CreditCheckResponse(**result).dict(),
            "error": None
        }
    except VBBaseException as e:
        handle_vb_exception(e)


@router.post("/booking", status_code=status.HTTP_201_CREATED)
async def create_booking(
    data: VBBookingCreate,
    current_user: dict = Depends(get_current_user),
):
    """
    Create a VB session booking.

    Automatically:
    - Validates credits (FIFO lot-based)
    - Deducts credits
    - Records terms acceptance
    - Creates booking record
    """
    try:
        # Validate tenant_id matches current user's tenant
        tenant_id = current_user["tenant_id"]
        if str(data.tenant_id) != tenant_id:
            raise VBAccessDeniedError("Tenant ID mismatch")

        booking = vb_service.create_booking(
            user_id=current_user["user_id"],
            tenant_id=tenant_id,
            venture_builder_id=str(data.venture_builder_id),
            project_id=str(data.project_id),
            session_datetime=data.session_datetime,
            accepted_terms_version=data.accepted_terms_version,
            agenda=data.agenda,
        )
        return {
            "success": True,
            "data": VBBookingResponse(**booking).dict(),
            "error": None
        }
    except VBBaseException as e:
        handle_vb_exception(e)


@router.get("/sessions/vb")
async def get_my_vb_sessions(
    status_filter: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_vb_or_admin_user),
):
    """
    VB or Admin: Get all sessions for the current VB.
    """
    try:
        # Get VB profile
        vb_profile = vb_service.get_vb_by_user_id(current_user["user_id"])
        if not vb_profile:
            raise VBNotFoundError("VB profile not found")

        filters = SessionFilters(
            status=status_filter,
            start_date=start_date,
            end_date=end_date,
            page=page,
            page_size=page_size,
        )

        sessions = vb_service.get_vb_sessions(
            venture_builder_id=vb_profile["id"],
            status=filters.status,
            start_date=filters.start_date,
            end_date=filters.end_date,
            page=filters.page,
            page_size=filters.page_size,
        )

        return {
            "success": True,
            "data": [VBSessionDetail(**session).dict() for session in sessions],
            "error": None
        }
    except VBBaseException as e:
        handle_vb_exception(e)


@router.get("/sessions/user")
async def get_my_user_sessions(
    status_filter: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    """
    Get all sessions booked by the current user.
    """
    try:
        filters = SessionFilters(
            status=status_filter,
            start_date=start_date,
            end_date=end_date,
            page=page,
            page_size=page_size,
        )

        sessions = vb_service.get_user_sessions(
            user_id=current_user["user_id"],
            status=filters.status,
            start_date=filters.start_date,
            end_date=filters.end_date,
            page=filters.page,
            page_size=filters.page_size,
        )

        return {
            "success": True,
            "data": [VBSessionDetail(**session).dict() for session in sessions],
            "error": None
        }
    except VBBaseException as e:
        handle_vb_exception(e)


@router.post("/sessions/{session_id}/complete")
async def complete_session(
    session_id: UUID,
    current_user: dict = Depends(get_vb_or_admin_user),
):
    """
    VB or Admin: Mark a session as completed.

    Can only be done after the session has ended (or within 10 minutes of ending).
    Only the VB who owns the session or an admin can complete it.
    """
    try:
        user_role = current_user.get("roles", [])[0] if current_user.get("roles") else None
        is_admin = user_role in ["admin", "super_admin"]

        result = vb_service.complete_session(
            session_id=str(session_id),
            completed_by_user_id=current_user["user_id"],
            is_admin=is_admin,
        )
        return {
            "success": True,
            "data": result,
            "error": None
        }
    except VBBaseException as e:
        handle_vb_exception(e)


@router.post("/sessions/{session_id}/cancel")
async def cancel_session(
    session_id: UUID,
    data: VBSessionCancelRequest,
    current_user: dict = Depends(get_vb_or_admin_user),
):
    """
    VB or Admin only: Cancel a booked session.

    Can only be cancelled before the session start time.
    Deletes the associated Google Calendar event if one exists.
    Refunds credits to the tenant by restoring them to original credit lots.
    Sends email notification to the user with cancellation reason and rebooking link.
    """
    try:
        user_role = current_user.get("roles", [])[0] if current_user.get("roles") else None
        is_admin = user_role in ["admin", "super_admin"]

        result = vb_service.cancel_session(
            session_id=str(session_id),
            requesting_user_id=current_user["user_id"],
            cancellation_reason=data.cancellation_reason,
            is_admin=is_admin,
        )
        return {
            "success": True,
            "data": result,
            "error": None
        }
    except VBBaseException as e:
        handle_vb_exception(e)
