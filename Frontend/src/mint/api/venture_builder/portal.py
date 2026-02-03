"""
Venture Builder Portal API

Handles VB portal access including:
- Read-only access to projects where VB has active sessions
"""

from typing import List

from fastapi import APIRouter, Depends

from .exceptions import VBBaseException, VBNotFoundError
from .service import get_vb_service
from .utils import handle_vb_exception
from src.mint.api.auth_v2.utils import get_vb_or_admin_user

router = APIRouter(prefix="/venture-builder", tags=["Venture Builder: Portal"])

# Singleton service instance
vb_service = get_vb_service()


@router.get("/portal/projects")
async def get_vb_portal_projects(
    current_user: dict = Depends(get_vb_or_admin_user),
):
    """
    VB or Admin: Get read-only access to projects where VB has active sessions.
    """
    try:
        # Get VB profile
        vb_profile = vb_service.get_vb_by_user_id(current_user["user_id"])
        if not vb_profile:
            raise VBNotFoundError("VB profile not found")

        projects = vb_service.get_vb_accessible_projects(vb_profile["id"])
        return {"success": True, "data": projects, "error": None}
    except VBBaseException as e:
        handle_vb_exception(e)
