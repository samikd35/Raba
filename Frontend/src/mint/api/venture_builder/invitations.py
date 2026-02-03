"""
Venture Builder Invitations API

Handles VB invitation management including:
- Sending invitations to potential VBs
"""

from fastapi import APIRouter, Depends

from .exceptions import VBBaseException
from .models import VBInviteRequest, VBInviteResponse
from .service import get_vb_service
from .utils import handle_vb_exception
from src.mint.api.auth_v2.utils import get_admin_user

router = APIRouter(prefix="/venture-builder", tags=["Venture Builder: Invitations"])

# Singleton service instance
vb_service = get_vb_service()


@router.post("/admin/invite")
async def invite_venture_builder(
    request: VBInviteRequest,
    current_user: dict = Depends(get_admin_user),
):
    """
    Admin only: Send an invitation to a Venture Builder via email.

    Creates an invitation record, generates a secure token, and sends an email
    with a registration link. The invitation is valid for 48 hours.
    """
    try:
        result = vb_service.send_vb_invitation(
            email=request.email,
            invited_by_user_id=current_user["user_id"],
            invited_by_email=current_user["email"],
        )
        return {"success": True, "data": VBInviteResponse(**result).dict(), "error": None}
    except VBBaseException as e:
        handle_vb_exception(e)
