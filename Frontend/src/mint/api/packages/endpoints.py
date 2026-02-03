from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from ..auth_v2.utils import get_admin_user
from .models import (CreditPackage, CreditPackageCreate, CreditPackageUpdate,
                     TenantType)
from .service import PackageService

router = APIRouter(prefix="/api/packages", tags=["packages"])

# Initialize the service at import time using your factory
package_service = PackageService()


# ---------- Endpoints ----------
@router.get("", response_model=List[CreditPackage])
async def list_available_packages(
    current_user: dict = Depends(get_admin_user),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Get all *available* (is_active=true) packages across all tenant types."""
    return await package_service.list_packages(
        active_only=True, limit=limit, offset=offset
    )


@router.get("/all", response_model=List[CreditPackage])
async def list_all_packages(
    current_user: dict = Depends(get_admin_user),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Get all packages (active + inactive)."""
    return await package_service.list_packages(
        active_only=False, limit=limit, offset=offset
    )


@router.get("/{tenant_type}", response_model=List[CreditPackage])
async def list_by_tenant_type_endpoint(
    tenant_type: TenantType,
    current_user: dict = Depends(get_admin_user),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Get available packages for a specific tenant type."""
    return await package_service.list_by_tenant_type(
        tenant_type=tenant_type, active_only=True, limit=limit, offset=offset
    )


@router.get("/{package_id}", response_model=CreditPackage)
async def get_package_endpoint(
    package_id: UUID, current_user: dict = Depends(get_admin_user)
):
    """Get a single package by ID."""
    return await package_service.get_package(package_id)


@router.post("", response_model=CreditPackage, status_code=status.HTTP_201_CREATED)
async def create_package_endpoint(
    body: CreditPackageCreate, current_user: dict = Depends(get_admin_user)
):
    """Create a new credit package."""
    return await package_service.create_package(body)


@router.put("/{package_id}", response_model=CreditPackage)
async def update_package_endpoint(
    package_id: UUID,
    body: CreditPackageUpdate,
    current_user: dict = Depends(get_admin_user),
):
    """Edit an existing credit package."""
    return await package_service.update_package(package_id, body)


@router.delete("/{package_id}", response_model=CreditPackage)
async def delete_package_endpoint(
    package_id: UUID, current_user: dict = Depends(get_admin_user)
):
    """Delete a package (hard delete)."""
    return await package_service.delete_package(package_id)


@router.post("/{package_id}/deactivate", response_model=CreditPackage)
async def deactivate_package_endpoint(
    package_id: UUID, current_user: dict = Depends(get_admin_user)
):
    """Deactivate a package (sets is_active=false)."""
    return await package_service.deactivate_package(package_id)
