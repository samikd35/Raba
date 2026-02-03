from fastapi import APIRouter, Body, Depends, Query

from ..auth_v2.utils import get_admin_user, get_super_admin_user
from .admin_service import AdminService
from .threshold_service import ThresholdService
from .models import MatchingThresholdCreate, MatchingThresholdUpdate, ProfileRejectionRequest

router = APIRouter(prefix="/profiles/admin", tags=["profiles.admin"])

admin_service = AdminService()
threshold_service = ThresholdService()


@router.get("/profile-versions")
def list_versions(
    status: str = Query("submitted"),
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_admin_user),
):
    return {"items": admin_service.list_submissions(status=status, limit=limit)}


@router.post("/profile-versions/{version_id}/approve")
def approve(version_id: str, current_user: dict = Depends(get_admin_user)):
    return admin_service.approve(version_id)


@router.post("/profile-versions/{version_id}/reject")
def reject(
    version_id: str,
    rejection: ProfileRejectionRequest,
    current_user: dict = Depends(get_admin_user),
):
    return admin_service.reject(version_id, rejection.reason)


# ==========================================
# Matching Threshold Management Endpoints
# ==========================================


@router.post("/matching-thresholds")
def create_threshold(
    threshold: MatchingThresholdCreate,
    current_user: dict = Depends(get_admin_user),
):
    """Create a new matching threshold configuration"""
    return threshold_service.create_threshold(
        name=threshold.name,
        description=threshold.description,
        threshold_score=threshold.threshold_score,
        is_active=threshold.is_active,
        created_by=current_user.get("id"),
    )


@router.get("/matching-thresholds")
def list_thresholds(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_admin_user),
):
    """List all matching threshold configurations"""
    return threshold_service.list_thresholds(limit=limit, offset=offset)


@router.get("/matching-thresholds/active")
def get_active_threshold(current_user: dict = Depends(get_admin_user)):
    """Get the currently active threshold configuration"""
    return threshold_service.get_active_threshold()


@router.get("/matching-thresholds/{threshold_id}")
def get_threshold(
    threshold_id: str,
    current_user: dict = Depends(get_admin_user),
):
    """Get a specific threshold configuration by ID"""
    return threshold_service.get_threshold(threshold_id)


@router.patch("/matching-thresholds/{threshold_id}")
def update_threshold(
    threshold_id: str,
    threshold: MatchingThresholdUpdate,
    current_user: dict = Depends(get_admin_user),
):
    """Update a matching threshold configuration"""
    return threshold_service.update_threshold(
        threshold_id=threshold_id,
        name=threshold.name,
        description=threshold.description,
        threshold_score=threshold.threshold_score,
        is_active=threshold.is_active,
        updated_by=current_user.get("id"),
    )


@router.delete("/matching-thresholds/{threshold_id}")
def delete_threshold(
    threshold_id: str,
    current_user: dict = Depends(get_super_admin_user),
):
    """Delete a matching threshold configuration (super admin only)"""
    return threshold_service.delete_threshold(threshold_id)


@router.post("/matching-thresholds/{threshold_id}/activate")
def activate_threshold(
    threshold_id: str,
    current_user: dict = Depends(get_admin_user),
):
    """Activate a specific threshold (deactivates all others)"""
    return threshold_service.activate_threshold(
        threshold_id=threshold_id,
        updated_by=current_user.get("id"),
    )


@router.post("/matching-thresholds/{threshold_id}/deactivate")
def deactivate_threshold(
    threshold_id: str,
    current_user: dict = Depends(get_admin_user),
):
    """Deactivate a specific threshold"""
    return threshold_service.deactivate_threshold(
        threshold_id=threshold_id,
        updated_by=current_user.get("id"),
    )
