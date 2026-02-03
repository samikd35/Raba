"""
Venture Builder Availability API

Handles availability management including:
- Creating and viewing availability slots
- Deleting specific availability slots
- Getting available booking slots
"""

from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query

from .exceptions import VBAccessDeniedError, VBBaseException
from .models import (
    AvailabilitySlotResponse,
    AvailabilitySlotsBulkCreate,
    AvailabilitySlotsBulkDelete,
    AvailabilityResponse,
    TimeSlot,
)
from .service import get_vb_service
from .utils import handle_vb_exception
from src.mint.api.auth_v2.utils import get_current_user, get_vb_or_admin_user

router = APIRouter(prefix="/venture-builder", tags=["Venture Builder: Availability"])

# Singleton service instance
vb_service = get_vb_service()


@router.post("/{vb_id}/availability-slots")
async def create_availability_slots(
    vb_id: UUID,
    data: AvailabilitySlotsBulkCreate,
    current_user: dict = Depends(get_vb_or_admin_user),
):
    """
    VB only: Create availability slots (session start times).

    Adds new slots without removing existing ones.
    Each slot represents a 1-hour session starting at session_start time.
    session_end is computed automatically as session_start + 1 hour.
    """
    try:
        # Verify VB owns this profile or is admin
        vb_profile = vb_service.get_vb_by_user_id(current_user["user_id"])
        user_role = current_user.get("roles", [])[0] if current_user.get("roles") else None

        if not vb_profile or str(vb_profile["id"]) != str(vb_id):
            if user_role not in ["admin", "super_admin"]:
                raise VBAccessDeniedError("Can only modify your own availability")

        slots = vb_service.create_availability_slots(str(vb_id), data.slots)
        return {"success": True, "data": [AvailabilitySlotResponse(**s).dict() for s in slots], "error": None}
    except VBBaseException as e:
        handle_vb_exception(e)


@router.get("/{vb_id}/availability-slots")
async def get_availability_slots(vb_id: UUID):
    """
    Public: Get availability slots (session start/end times) for a VB.
    """
    try:
        slots = vb_service.get_availability_slots(str(vb_id))
        return {"success": True, "data": [AvailabilitySlotResponse(**s).dict() for s in slots], "error": None}
    except VBBaseException as e:
        handle_vb_exception(e)


@router.delete("/{vb_id}/availability-slots")
async def delete_availability_slots(
    vb_id: UUID,
    data: AvailabilitySlotsBulkDelete,
    current_user: dict = Depends(get_vb_or_admin_user),
):
    """
    VB only: Delete specific availability slots.

    Removes slots matching the provided day_of_week + session_start combinations.
    """
    try:
        vb_profile = vb_service.get_vb_by_user_id(current_user["user_id"])
        user_role = current_user.get("roles", [])[0] if current_user.get("roles") else None

        if not vb_profile or str(vb_profile["id"]) != str(vb_id):
            if user_role not in ["admin", "super_admin"]:
                raise VBAccessDeniedError("Can only modify your own availability")

        deleted_count = vb_service.delete_availability_slots(str(vb_id), data.slots)
        return {"success": True, "data": {"deleted_count": deleted_count}, "error": None}
    except VBBaseException as e:
        handle_vb_exception(e)


@router.get("/{vb_id}/availability")
async def get_available_slots(
    vb_id: UUID,
    start_date: str = Query(..., description="Start date (ISO format: YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (ISO format: YYYY-MM-DD)"),
    current_user: dict = Depends(get_current_user),
):
    """
    Public: Get available booking slots for a VB.

    Computes availability by combining:
    - VB's configured availability slots (1-hour sessions)
    - Existing Yuba bookings
    - Google Calendar busy times (if connected)

    Returns a list of available time slots within the date range.
    """
    try:
        # Parse date strings to datetime objects
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=ZoneInfo("UTC"))
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(
            hour=23, minute=59, second=59, tzinfo=ZoneInfo("UTC")
        )

        # Get VB's timezone from calendar connection
        calendar_status = vb_service.get_calendar_status(str(vb_id))
        vb_timezone = calendar_status.get("time_zone", "UTC")

        slots = vb_service.get_available_slots(
            vb_id=str(vb_id),
            start_date=start_dt,
            end_date=end_dt,
        )
        availability_data = AvailabilityResponse(
            vb_id=vb_id,
            time_zone=vb_timezone,
            slots=[TimeSlot(start=s["start"], end=s["end"], available=s["available"]) for s in slots],
            date_range={"start_date": start_date, "end_date": end_date},
        )
        return {"success": True, "data": availability_data.dict(), "error": None}
    except VBBaseException as e:
        handle_vb_exception(e)
