"""
Venture Builder Google Calendar Integration API

Handles Google Calendar OAuth and management including:
- Generating OAuth authorization URLs
- Handling OAuth callbacks
- Calendar connection status
- Listing available calendars
- Selecting calendars for bookings
- Disconnecting calendar integration
"""

import os

from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse

from .exceptions import VBBaseException, VBNotFoundError
from .models import CalendarSelectionRequest, GoogleCalendarAuthURL, GoogleCalendarListResponse, GoogleCalendarStatus
from .service import get_vb_service
from .utils import handle_vb_exception
from src.mint.api.auth_v2.utils import get_vb_or_admin_user

router = APIRouter(prefix="/venture-builder", tags=["Venture Builder: Calendar"])

# Singleton service instance
vb_service = get_vb_service()


@router.get("/calendar/auth-url")
async def get_calendar_auth_url(
    current_user: dict = Depends(get_vb_or_admin_user),
):
    """
    VB only: Generate Google OAuth authorization URL.

    Returns an authorization URL that the VB should redirect to.
    After authorization, Google redirects back to /calendar/callback.
    """
    try:
        # Get VB profile for current user
        vb_profile = vb_service.get_vb_by_user_id(current_user["user_id"])
        if not vb_profile:
            raise VBNotFoundError("VB profile not found for current user")

        result = vb_service.get_calendar_auth_url(vb_profile["id"])
        return {"success": True, "data": GoogleCalendarAuthURL(**result).dict(), "error": None}
    except VBBaseException as e:
        handle_vb_exception(e)


@router.get("/calendar/callback")
async def calendar_oauth_callback(
    code: str = Query(..., description="Authorization code from Google"),
    state: str = Query(..., description="CSRF state token"),
):
    """
    OAuth callback endpoint. Google redirects here after user authorizes.

    This is called by Google, not by the frontend directly.
    Redirects to frontend with success or error status.
    """
    try:
        result = vb_service.handle_calendar_oauth_callback(code, state)
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        return RedirectResponse(
            url=f"{frontend_url}/venture-builder/settings?calendar_connected=true"
        )
    except Exception as e:
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        return RedirectResponse(
            url=f"{frontend_url}/venture-builder/settings?calendar_error={str(e)}"
        )


@router.get("/calendar/status")
async def get_calendar_status(
    current_user: dict = Depends(get_vb_or_admin_user),
):
    """
    VB only: Get current Google Calendar connection status.

    Returns whether calendar is connected, which calendar is selected,
    and whether the connection is still valid.
    """
    try:
        vb_profile = vb_service.get_vb_by_user_id(current_user["user_id"])
        if not vb_profile:
            raise VBNotFoundError("VB profile not found for current user")

        result = vb_service.get_calendar_status(vb_profile["id"])
        return {"success": True, "data": GoogleCalendarStatus(**result).dict(), "error": None}
    except VBBaseException as e:
        handle_vb_exception(e)


@router.get("/calendar/list")
async def list_calendars(
    current_user: dict = Depends(get_vb_or_admin_user),
):
    """
    VB only: List all available Google Calendars.

    Returns a list of calendars that the VB can select for booking.
    Requires an existing calendar connection.
    """
    try:
        vb_profile = vb_service.get_vb_by_user_id(current_user["user_id"])
        if not vb_profile:
            raise VBNotFoundError("VB profile not found for current user")

        calendars = vb_service.list_calendars(vb_profile["id"])
        return {"success": True, "data": GoogleCalendarListResponse(calendars=calendars).dict(), "error": None}
    except VBBaseException as e:
        handle_vb_exception(e)


@router.post("/calendar/select")
async def select_calendar(
    data: CalendarSelectionRequest,
    current_user: dict = Depends(get_vb_or_admin_user),
):
    """
    VB only: Select which Google Calendar to use for Yuba bookings.

    Also sets the timezone for the VB's availability.
    """
    try:
        vb_profile = vb_service.get_vb_by_user_id(current_user["user_id"])
        if not vb_profile:
            raise VBNotFoundError("VB profile not found for current user")

        vb_service.select_calendar(
            vb_profile["id"], data.calendar_id, data.time_zone
        )
        return {"success": True, "data": {"message": "Calendar selected"}, "error": None}
    except VBBaseException as e:
        handle_vb_exception(e)


@router.delete("/calendar/disconnect")
async def disconnect_calendar(
    current_user: dict = Depends(get_vb_or_admin_user),
):
    """
    VB only: Disconnect Google Calendar integration.

    Removes the OAuth connection and all stored tokens.
    """
    try:
        vb_profile = vb_service.get_vb_by_user_id(current_user["user_id"])
        if not vb_profile:
            raise VBNotFoundError("VB profile not found for current user")

        vb_service.disconnect_calendar(vb_profile["id"])
        return {"success": True, "data": {"message": "Calendar disconnected"}, "error": None}
    except VBBaseException as e:
        handle_vb_exception(e)
