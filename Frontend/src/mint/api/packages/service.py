from typing import List
from uuid import UUID

from fastapi import HTTPException, status

from ..system.core.supabase_client import get_supabase_client
from .models import CreditPackageCreate, CreditPackageUpdate, TenantType, _dump

TABLE = "credit_packages"


class PackageService:
    def __init__(self, use_service_role: bool = True):
        self.client = get_supabase_client(use_service_role=use_service_role).client

    # ---- Reads ----
    async def list_packages(
        self, *, active_only: bool, limit: int, offset: int
    ) -> List[dict]:
        q = (
            self.client.table(TABLE)
            .select("*")
            .order("credits_per_user", desc=False)
            .range(offset, offset + limit - 1)
        )
        if active_only:
            q = q.eq("is_active", True)
        res = q.execute()
        return res.data or []

    async def list_by_tenant_type(
        self, tenant_type: TenantType, *, active_only: bool, limit: int, offset: int
    ) -> List[dict]:
        q = (
            self.client.table(TABLE)
            .select("*")
            .eq("tenant_type", tenant_type)
            .order("credits_per_user", desc=False)
            .range(offset, offset + limit - 1)
        )
        if active_only:
            q = q.eq("is_active", True)
        res = q.execute()
        return res.data or []

    async def get_package(self, package_id: UUID) -> dict:
        res = (
            self.client.table(TABLE)
            .select("*")
            .eq("id", str(package_id))
            .single()
            .execute()
        )
        if not res.data:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Package not found")
        return res.data

    # ---- Mutations ----
    async def create_package(self, payload: CreditPackageCreate) -> dict:
        try:
            res = (
                self.client.table(TABLE)
                .insert(_dump(payload))
                .select("*")
                .single()
                .execute()
            )
            return res.data
        except Exception as e:
            msg = str(e)
            if "duplicate key value" in msg or "409" in msg or "unique" in msg:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    "A package with this (tenant_type, credits_per_user) already exists.",
                )
            raise HTTPException(status.HTTP_400_BAD_REQUEST, msg)

    async def update_package(
        self, package_id: UUID, payload: CreditPackageUpdate
    ) -> dict:
        data = _dump(payload)
        if not data:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY, "No fields to update."
            )
        try:
            res = (
                self.client.table(TABLE)
                .update(data)
                .eq("id", str(package_id))
                .select("*")
                .single()
                .execute()
            )
            if not res.data:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Package not found")
            return res.data
        except Exception as e:
            msg = str(e)
            if "duplicate key value" in msg or "409" in msg or "unique" in msg:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    "A package with this (tenant_type, credits_per_user) already exists.",
                )
            raise HTTPException(status.HTTP_400_BAD_REQUEST, msg)

    async def delete_package(self, package_id: UUID) -> dict:
        res = (
            self.client.table(TABLE)
            .delete()
            .eq("id", str(package_id))
            .select("*")
            .single()
            .execute()
        )
        if not res.data:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Package not found")
        return res.data

    async def deactivate_package(self, package_id: UUID) -> dict:
        res = (
            self.client.table(TABLE)
            .update({"is_active": False})
            .eq("id", str(package_id))
            .select("*")
            .single()
            .execute()
        )
        if not res.data:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Package not found")
        return res.data
