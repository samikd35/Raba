"""
Venture Builder Expertise Areas API

Handles expertise area management including:
- Admin CRUD operations for expertise areas
- Public listing of active expertise areas
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from .exceptions import VBBaseException
from .models import ExpertiseAreaCreate, ExpertiseAreaResponse, ExpertiseAreaUpdate
from .service import get_vb_service
from .utils import handle_vb_exception
from src.mint.api.auth_v2.utils import get_admin_user, get_super_admin_user

router = APIRouter(prefix="/venture-builder", tags=["Venture Builder: Expertise"])

# Singleton service instance
vb_service = get_vb_service()


@router.get("/admin/expertise")
async def list_all_expertise_areas(
    include_inactive: bool = Query(False),
    current_user: dict = Depends(get_admin_user),
):
    """
    Admin only: List all expertise areas (active and optionally inactive).
    """
    try:
        areas = vb_service.list_expertise_areas(active_only=not include_inactive)
        return {"success": True, "data": [ExpertiseAreaResponse(**area).dict() for area in areas], "error": None}
    except VBBaseException as e:
        handle_vb_exception(e)


@router.post(
    "/admin/expertise", status_code=status.HTTP_201_CREATED
)
async def create_expertise_area(
    data: ExpertiseAreaCreate,
    current_user: dict = Depends(get_admin_user),
):
    """
    Admin only: Create a new expertise area.
    """
    try:
        area = vb_service.create_expertise_area(
            name=data.name,
            description=data.description,
            display_order=data.display_order,
        )
        return {"success": True, "data": ExpertiseAreaResponse(**area).dict(), "error": None}
    except VBBaseException as e:
        handle_vb_exception(e)


@router.patch("/admin/expertise/{expertise_id}")
async def update_expertise_area(
    expertise_id: UUID,
    data: ExpertiseAreaUpdate,
    current_user: dict = Depends(get_admin_user),
):
    """
    Admin only: Update an expertise area (partial update).
    """
    try:
        area = vb_service.update_expertise_area(
            expertise_id=str(expertise_id),
            name=data.name,
            description=data.description,
            display_order=data.display_order,
            is_active=data.is_active,
        )
        return {"success": True, "data": ExpertiseAreaResponse(**area).dict(), "error": None}
    except VBBaseException as e:
        handle_vb_exception(e)


@router.delete("/admin/expertise/{expertise_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expertise_area(
    expertise_id: UUID,
    current_user: dict = Depends(get_super_admin_user),
):
    """
    Super Admin only: Hard delete an expertise area.
    """
    try:
        vb_service.delete_expertise_area(str(expertise_id))
        return {"success": True, "data": None, "error": None}
    except VBBaseException as e:
        handle_vb_exception(e)


@router.get("/expertise")
async def list_active_expertise_areas():
    """
    Public: List all active expertise areas for filtering/browsing.
    """
    try:
        areas = vb_service.list_expertise_areas(active_only=True)
        return {"success": True, "data": [ExpertiseAreaResponse(**area).dict() for area in areas], "error": None}
    except VBBaseException as e:
        handle_vb_exception(e)
