#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Admin Module Features Routes.
CRUD endpoints for public.module_features, restricted to admin/super_admin.
"""

import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..auth_v2.utils import get_admin_user
from .models import (FeatureCreditCostCreate, FeatureCreditCostOut,
                     FeatureCreditCostUpdate, ModuleFeatureCreate,
                     ModuleFeatureOut, ModuleFeatureUpdate,
                     ResolvedFeatureCostOut)
from .service import FeatureCreditCostService, ModuleFeatureService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/features", tags=["features"])
service = ModuleFeatureService()
cost_service = FeatureCreditCostService()


@router.get("/", response_model=List[ModuleFeatureOut])
async def list_features(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(
        None, description="Filter by name/display_name (ILIKE)"
    ),
    feature_type: Optional[str] = Query(
        None, description="generator|analyzer|validator|reporter"
    ),
    is_active: Optional[bool] = Query(None),
    admin_user=Depends(get_admin_user),
):
    items, _total = service.list(
        limit=limit,
        offset=offset,
        search=search,
        feature_type=feature_type,
        is_active=is_active,
    )
    return items


@router.get("/credit-costs", response_model=List[FeatureCreditCostOut])
async def list_feature_credit_costs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    feature_id: Optional[UUID] = Query(None),
    plan_type: Optional[str] = Query(None, description="individual|team|organization"),
    is_active: Optional[bool] = Query(None),
    current_only: bool = Query(False, description="Only rows effective as of `as_of`"),
    as_of: Optional[datetime] = Query(None, description="Defaults to now() if omitted"),
    admin_user=Depends(get_admin_user),
):
    items, _ = cost_service.list(
        limit=limit,
        offset=offset,
        feature_id=str(feature_id) if feature_id else None,
        plan_type=plan_type,
        is_active=is_active,
        current_only=current_only,
        as_of=as_of,
    )
    return items


@router.get("/credit-costs/{cost_id}", response_model=FeatureCreditCostOut)
async def get_feature_credit_cost(cost_id: UUID, admin_user=Depends(get_admin_user)):
    item = cost_service.get(str(cost_id))
    if not item:
        raise HTTPException(status_code=404, detail="Credit cost row not found")
    return item


@router.post(
    "/credit-costs",
    response_model=FeatureCreditCostOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_feature_credit_cost(
    body: FeatureCreditCostCreate,
    admin_user=Depends(get_admin_user),
):
    try:
        return cost_service.create(body)
    except Exception as e:
        logger.exception("Failed to create feature credit cost")
        raise HTTPException(
            status_code=400, detail={"code": "create_failed", "message": str(e)}
        )


@router.put("/credit-costs/{cost_id}", response_model=FeatureCreditCostOut)
async def update_feature_credit_cost(
    cost_id: UUID,
    body: FeatureCreditCostUpdate,
    admin_user=Depends(get_admin_user),
):
    item = cost_service.update(str(cost_id), body)
    if not item:
        raise HTTPException(status_code=404, detail="Credit cost row not found")
    return item


@router.delete("/credit-costs/{cost_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_feature_credit_cost(
    cost_id: UUID,
    admin_user=Depends(get_admin_user),
):
    existing = cost_service.get(str(cost_id))
    if not existing:
        raise HTTPException(status_code=404, detail="Credit cost row not found")
    cost_service.delete(str(cost_id))
    return None


@router.post("/credit-costs/{cost_id}/toggle", response_model=FeatureCreditCostOut)
async def toggle_feature_credit_cost_active(
    cost_id: UUID,
    is_active: bool = Query(...),
    admin_user=Depends(get_admin_user),
):
    item = cost_service.toggle_active(str(cost_id), is_active)
    if not item:
        raise HTTPException(status_code=404, detail="Credit cost row not found")
    return item


@router.get("/{feature_id}/resolve-cost", response_model=ResolvedFeatureCostOut)
async def resolve_feature_credit_cost(
    feature_id: UUID,
    plan_type: str = Query(..., description="individual|team|organization"),
    as_of: Optional[datetime] = Query(None),
    admin_user=Depends(get_admin_user),
):
    result = cost_service.resolve_cost(str(feature_id), plan_type, as_of)
    if not result:
        raise HTTPException(status_code=404, detail="Feature not found")
    return result


# =============================================
# FEATURE ENDPOINTS (moved after credit-costs to fix route precedence)
# =============================================

@router.get("/{feature_id}", response_model=ModuleFeatureOut)
async def get_feature(
    feature_id: UUID,
    admin_user=Depends(get_admin_user),
):
    item = service.get(feature_id)
    if not item:
        raise HTTPException(status_code=404, detail="Feature not found")
    return item


@router.post("/", response_model=ModuleFeatureOut, status_code=status.HTTP_201_CREATED)
async def create_feature(
    body: ModuleFeatureCreate,
    admin_user=Depends(get_admin_user),
):
    try:
        return service.create(body)
    except Exception as e:
        logger.exception("Failed to create feature")
        raise HTTPException(
            status_code=400, detail={"code": "create_failed", "message": str(e)}
        )


@router.put("/{feature_id}", response_model=ModuleFeatureOut)
async def update_feature(
    feature_id: UUID,
    body: ModuleFeatureUpdate,
    admin_user=Depends(get_admin_user),
):
    item = service.update(feature_id, body)
    if not item:
        raise HTTPException(status_code=404, detail="Feature not found")
    return item


@router.delete("/{feature_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_feature(
    feature_id: UUID,
    admin_user=Depends(get_admin_user),
):
    existing = service.get(feature_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Feature not found")
    service.delete(feature_id)
    return None


@router.post("/{feature_id}/toggle", response_model=ModuleFeatureOut)
async def toggle_feature_active(
    feature_id: UUID,
    is_active: bool = Query(...),
    admin_user=Depends(get_admin_user),
):
    item = service.toggle_active(feature_id, is_active)
    if not item:
        raise HTTPException(status_code=404, detail="Feature not found")
    return item
