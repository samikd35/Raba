import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..auth_v2.utils import (get_admin_user, get_current_user,
                             get_super_admin_user)
from .models import (CommitmentCreate, CommitmentUpdate, EnumItemListResponse,
                     EnumItemResponse, IndustryCreate, IndustryUpdate,
                     LanguageCreate, LanguageUpdate,
                     ResponsibilityCreate, ResponsibilityUpdate,
                     VentureStageCreate, VentureStageUpdate)
from .service import (CommitmentsService, IndustriesService,
                      LanguagesService, ResponsibilitiesService,
                      VentureStagesService)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/profiles/enums", tags=["profiles.enums"])

# ============================================================
# Public READ endpoints (active items only)
# ============================================================


@router.get("/industries", response_model=EnumItemListResponse)
async def list_industries(
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    svc = IndustriesService()
    return await svc.list(search=search, is_active=True, page=page, page_size=page_size)


@router.get("/responsibilities", response_model=EnumItemListResponse)
async def list_responsibilities(
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    svc = ResponsibilitiesService()
    return await svc.list(search=search, is_active=True, page=page, page_size=page_size)


@router.get("/commitment", response_model=EnumItemListResponse)
async def list_commitments(
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    svc = CommitmentsService()
    return await svc.list(search=search, is_active=True, page=page, page_size=page_size)


@router.get("/venture_stages", response_model=EnumItemListResponse)
async def list_venture_stages(
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    svc = VentureStagesService()
    return await svc.list(search=search, is_active=True, page=page, page_size=page_size)


@router.get("/languages", response_model=EnumItemListResponse)
async def list_languages(
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    svc = LanguagesService()
    return await svc.list(search=search, is_active=True, page=page, page_size=page_size)


# ============================================================
# Admin: full CRUD + activate/deactivate
# Roles: admin and super_admin
# ============================================================


# ---- Industries ----
@router.post("/industries", response_model=EnumItemResponse)
async def create_industry(
    payload: IndustryCreate,
    admin_user: Dict[str, Any] = Depends(get_admin_user),
):
    svc = IndustriesService()
    return await svc.create(payload, user_id=admin_user.get("user_id"))


@router.get("/industries/{item_id}", response_model=EnumItemResponse)
async def get_industry(
    item_id: str, admin_user: Dict[str, Any] = Depends(get_admin_user)
):
    svc = IndustriesService()
    return await svc.get(item_id)


@router.put("/industries/{item_id}", response_model=EnumItemResponse)
async def update_industry(
    item_id: str,
    payload: IndustryUpdate,
    admin_user: Dict[str, Any] = Depends(get_admin_user),
):
    svc = IndustriesService()
    return await svc.update(item_id, payload, user_id=admin_user.get("user_id"))


@router.post("/industries/{item_id}/activate", response_model=EnumItemResponse)
async def activate_industry(
    item_id: str, admin_user: Dict[str, Any] = Depends(get_admin_user)
):
    svc = IndustriesService()
    return await svc.set_active(item_id, True, user_id=admin_user.get("user_id"))


@router.post("/industries/{item_id}/deactivate", response_model=EnumItemResponse)
async def deactivate_industry(
    item_id: str, admin_user: Dict[str, Any] = Depends(get_admin_user)
):
    svc = IndustriesService()
    return await svc.set_active(item_id, False, user_id=admin_user.get("user_id"))


@router.delete("/industries/{item_id}", response_model=EnumItemResponse)
async def delete_industry(
    item_id: str, admin_user: Dict[str, Any] = Depends(get_super_admin_user)
):
    svc = IndustriesService()
    return await svc.delete(item_id)


# ---- Responsibilities ----
@router.post("/responsibilities", response_model=EnumItemResponse)
async def create_responsibility(
    payload: ResponsibilityCreate,
    admin_user: Dict[str, Any] = Depends(get_admin_user),
):
    svc = ResponsibilitiesService()
    return await svc.create(payload, user_id=admin_user.get("user_id"))


@router.get("/responsibilities/{item_id}", response_model=EnumItemResponse)
async def get_responsibility(
    item_id: str, admin_user: Dict[str, Any] = Depends(get_admin_user)
):
    svc = ResponsibilitiesService()
    return await svc.get(item_id)


@router.put("/responsibilities/{item_id}", response_model=EnumItemResponse)
async def update_responsibility(
    item_id: str,
    payload: ResponsibilityUpdate,
    admin_user: Dict[str, Any] = Depends(get_admin_user),
):
    svc = ResponsibilitiesService()
    return await svc.update(item_id, payload, user_id=admin_user.get("user_id"))


@router.post("/responsibilities/{item_id}/activate", response_model=EnumItemResponse)
async def activate_responsibility(
    item_id: str, admin_user: Dict[str, Any] = Depends(get_admin_user)
):
    svc = ResponsibilitiesService()
    return await svc.set_active(item_id, True, user_id=admin_user.get("user_id"))


@router.post("/responsibilities/{item_id}/deactivate", response_model=EnumItemResponse)
async def deactivate_responsibility(
    item_id: str, admin_user: Dict[str, Any] = Depends(get_admin_user)
):
    svc = ResponsibilitiesService()
    return await svc.set_active(item_id, False, user_id=admin_user.get("user_id"))


@router.delete("/responsibilities/{item_id}", response_model=EnumItemResponse)
async def delete_responsibility(
    item_id: str, admin_user: Dict[str, Any] = Depends(get_super_admin_user)
):
    svc = ResponsibilitiesService()
    return await svc.delete(item_id)


# ---- Commitments ----
@router.post("/commitment", response_model=EnumItemResponse)
async def create_commitment(
    payload: CommitmentCreate,
    admin_user: Dict[str, Any] = Depends(get_admin_user),
):
    svc = CommitmentsService()
    return await svc.create(payload, user_id=admin_user.get("user_id"))


@router.get("/commitment/{item_id}", response_model=EnumItemResponse)
async def get_commitment(
    item_id: str, admin_user: Dict[str, Any] = Depends(get_admin_user)
):
    svc = CommitmentsService()
    return await svc.get(item_id)


@router.put("/commitment/{item_id}", response_model=EnumItemResponse)
async def update_commitment(
    item_id: str,
    payload: CommitmentUpdate,
    admin_user: Dict[str, Any] = Depends(get_admin_user),
):
    svc = CommitmentsService()
    return await svc.update(item_id, payload, user_id=admin_user.get("user_id"))


@router.post("/commitment/{item_id}/activate", response_model=EnumItemResponse)
async def activate_commitment(
    item_id: str, admin_user: Dict[str, Any] = Depends(get_admin_user)
):
    svc = CommitmentsService()
    return await svc.set_active(item_id, True, user_id=admin_user.get("user_id"))


@router.post("/commitment/{item_id}/deactivate", response_model=EnumItemResponse)
async def deactivate_commitment(
    item_id: str, admin_user: Dict[str, Any] = Depends(get_admin_user)
):
    svc = CommitmentsService()
    return await svc.set_active(item_id, False, user_id=admin_user.get("user_id"))


@router.delete("/commitment/{item_id}", response_model=EnumItemResponse)
async def delete_commitment(
    item_id: str, admin_user: Dict[str, Any] = Depends(get_super_admin_user)
):
    svc = CommitmentsService()
    return await svc.delete(item_id)


# ---- Venture Stages ----
@router.post("/venture_stages", response_model=EnumItemResponse)
async def create_venture_stage(
    payload: VentureStageCreate,
    admin_user: Dict[str, Any] = Depends(get_admin_user),
):
    svc = VentureStagesService()
    return await svc.create(payload, user_id=admin_user.get("user_id"))


@router.get("/venture_stages/{item_id}", response_model=EnumItemResponse)
async def get_venture_stage(
    item_id: str, admin_user: Dict[str, Any] = Depends(get_admin_user)
):
    svc = VentureStagesService()
    return await svc.get(item_id)


@router.put("/venture_stages/{item_id}", response_model=EnumItemResponse)
async def update_venture_stage(
    item_id: str,
    payload: VentureStageUpdate,
    admin_user: Dict[str, Any] = Depends(get_admin_user),
):
    svc = VentureStagesService()
    return await svc.update(item_id, payload, user_id=admin_user.get("user_id"))


@router.post("/venture_stages/{item_id}/activate", response_model=EnumItemResponse)
async def activate_venture_stage(
    item_id: str, admin_user: Dict[str, Any] = Depends(get_admin_user)
):
    svc = VentureStagesService()
    return await svc.set_active(item_id, True, user_id=admin_user.get("user_id"))


@router.post("/venture_stages/{item_id}/deactivate", response_model=EnumItemResponse)
async def deactivate_venture_stage(
    item_id: str, admin_user: Dict[str, Any] = Depends(get_admin_user)
):
    svc = VentureStagesService()
    return await svc.set_active(item_id, False, user_id=admin_user.get("user_id"))


@router.delete("/venture_stages/{item_id}", response_model=EnumItemResponse)
async def delete_venture_stage(
    item_id: str, admin_user: Dict[str, Any] = Depends(get_super_admin_user)
):
    svc = VentureStagesService()
    return await svc.delete(item_id)


# ---- Languages ----
@router.post("/languages", response_model=EnumItemResponse)
async def create_language(
    payload: LanguageCreate,
    admin_user: Dict[str, Any] = Depends(get_admin_user),
):
    svc = LanguagesService()
    return await svc.create(payload, user_id=admin_user.get("user_id"))


@router.get("/languages/{item_id}", response_model=EnumItemResponse)
async def get_language(
    item_id: str, admin_user: Dict[str, Any] = Depends(get_admin_user)
):
    svc = LanguagesService()
    return await svc.get(item_id)


@router.put("/languages/{item_id}", response_model=EnumItemResponse)
async def update_language(
    item_id: str,
    payload: LanguageUpdate,
    admin_user: Dict[str, Any] = Depends(get_admin_user),
):
    svc = LanguagesService()
    return await svc.update(item_id, payload, user_id=admin_user.get("user_id"))


@router.post("/languages/{item_id}/activate", response_model=EnumItemResponse)
async def activate_language(
    item_id: str, admin_user: Dict[str, Any] = Depends(get_admin_user)
):
    svc = LanguagesService()
    return await svc.set_active(item_id, True, user_id=admin_user.get("user_id"))


@router.post("/languages/{item_id}/deactivate", response_model=EnumItemResponse)
async def deactivate_language(
    item_id: str, admin_user: Dict[str, Any] = Depends(get_admin_user)
):
    svc = LanguagesService()
    return await svc.set_active(item_id, False, user_id=admin_user.get("user_id"))


@router.delete("/languages/{item_id}", response_model=EnumItemResponse)
async def delete_language(
    item_id: str, admin_user: Dict[str, Any] = Depends(get_super_admin_user)
):
    svc = LanguagesService()
    return await svc.delete(item_id)


# Optional: admin list (includes inactive)
@router.get("/admin/{resource}", response_model=EnumItemListResponse)
async def admin_list(
    resource: str,
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    admin_user: Dict[str, Any] = Depends(get_admin_user),
):
    svc_map = {
        "industries": IndustriesService,
        "responsibilities": ResponsibilitiesService,
        "commitment": CommitmentsService,
        "venture_stages": VentureStagesService,
        "languages": LanguagesService,
    }
    if resource not in svc_map:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Unknown resource"
        )

    svc = svc_map[resource]()
    return await svc.list(
        search=search, is_active=is_active, page=page, page_size=page_size
    )
