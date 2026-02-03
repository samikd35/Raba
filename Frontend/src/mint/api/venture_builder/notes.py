"""
Venture Builder Session Notes API

Handles session notes management including:
- Creating and updating notes by VBs
- Viewing notes for specific sessions
- Viewing all notes for a tenant
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, status

from .exceptions import VBBaseException, VBNotFoundError
from .models import VBSessionNoteCreate, VBSessionNoteResponse, VBSessionNoteUpdate
from .service import get_vb_service
from .utils import handle_vb_exception
from src.mint.api.auth_v2.utils import get_current_user, get_vb_or_admin_user

router = APIRouter(prefix="/venture-builder", tags=["Venture Builder: Notes"])

# Singleton service instance
vb_service = get_vb_service()


@router.post("/notes", status_code=status.HTTP_201_CREATED)
async def create_session_note(
    data: VBSessionNoteCreate,
    current_user: dict = Depends(get_vb_or_admin_user),
):
    """
    VB or Admin: Create session notes after a coaching session.
    """
    try:
        # Get VB profile
        vb_profile = vb_service.get_vb_by_user_id(current_user["user_id"])
        if not vb_profile:
            raise VBNotFoundError("VB profile not found")

        note = vb_service.create_session_note(
            vb_session_id=str(data.vb_session_id),
            venture_builder_id=vb_profile["id"],
            created_by_user_id=current_user["user_id"],
            main_outcomes=data.main_outcomes,
            key_takeaways=data.key_takeaways,
            next_steps=data.next_steps,
            visible_to_user=data.visible_to_user,
        )
        return {"success": True, "data": VBSessionNoteResponse(**note).dict(), "error": None}
    except VBBaseException as e:
        handle_vb_exception(e)


@router.patch("/notes/{note_id}")
async def update_session_note(
    note_id: UUID,
    data: VBSessionNoteUpdate,
    current_user: dict = Depends(get_vb_or_admin_user),
):
    """
    VB or Admin: Update session notes.
    """
    try:
        # Get VB profile
        vb_profile = vb_service.get_vb_by_user_id(current_user["user_id"])
        if not vb_profile:
            raise VBNotFoundError("VB profile not found")

        update_data = {}
        if data.main_outcomes is not None:
            update_data["main_outcomes"] = data.main_outcomes
        if data.key_takeaways is not None:
            update_data["key_takeaways"] = data.key_takeaways
        if data.next_steps is not None:
            update_data["next_steps"] = data.next_steps
        if data.visible_to_user is not None:
            update_data["visible_to_user"] = data.visible_to_user

        note = vb_service.update_session_note(
            str(note_id),
            vb_profile["id"],
            **update_data
        )
        return {"success": True, "data": VBSessionNoteResponse(**note).dict(), "error": None}
    except VBBaseException as e:
        handle_vb_exception(e)


@router.get("/notes/session/{session_id}/user")
async def get_session_note_for_user(
    session_id: UUID,
    current_user: dict = Depends(get_current_user),
):
    """
    Regular users: Get notes for a specific session (only visible notes).
    """
    try:
        note = vb_service.get_session_note_for_user(str(session_id), current_user["user_id"])
        if not note:
            raise VBNotFoundError("Session note not found or not visible")
        return {"success": True, "data": VBSessionNoteResponse(**note).dict(), "error": None}
    except VBBaseException as e:
        handle_vb_exception(e)


@router.get("/notes/session/{session_id}/vb")
async def get_session_note_for_vb(
    session_id: UUID,
    current_user: dict = Depends(get_vb_or_admin_user),
):
    """
    VB or Admin: Get all notes for a specific session.
    """
    try:
        note = vb_service.get_session_note(str(session_id))
        if not note:
            raise VBNotFoundError("Session note not found")
        return {"success": True, "data": VBSessionNoteResponse(**note).dict(), "error": None}
    except VBBaseException as e:
        handle_vb_exception(e)


@router.get("/notes/tenant/user")
async def get_tenant_notes_for_user(
    current_user: dict = Depends(get_current_user),
):
    """
    Regular users: Get all coaching notes for user's tenant (only visible notes).
    """
    try:
        tenant_id = current_user["tenant_id"]
        notes = vb_service.get_user_coaching_notes(tenant_id, current_user["user_id"])
        return {"success": True, "data": [VBSessionNoteResponse(**note).dict() for note in notes], "error": None}
    except VBBaseException as e:
        handle_vb_exception(e)


@router.get("/notes/tenant/vb")
async def get_tenant_notes_for_vb(
    current_user: dict = Depends(get_vb_or_admin_user),
):
    """
    VB or Admin: Get all coaching notes for tenant.
    """
    try:
        tenant_id = current_user["tenant_id"]
        notes = vb_service.get_tenant_coaching_notes(tenant_id)
        return {"success": True, "data": [VBSessionNoteResponse(**note).dict() for note in notes], "error": None}
    except VBBaseException as e:
        handle_vb_exception(e)
