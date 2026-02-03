import re
from typing import Optional

from ..system.core.supabase_client import get_supabase_client
from .models import (EnumItem, EnumItemCreate, EnumItemListResponse,
                     EnumItemResponse, EnumItemUpdate)


def slugify(value: str) -> str:
    """Simple slugify: lowercase, strip punctuation, collapse spaces to dashes."""
    v = value.lower()
    v = re.sub(r"[^\w\s-]", "", v)
    v = re.sub(r"[\s_-]+", "-", v).strip("-")
    return v


class BaseEnumService:
    """
    Generic service for CRUD on enumeration tables.
    Instantiate with the concrete table name.
    """

    def __init__(self, table_name: str):
        self.table = table_name
        self.supabase = get_supabase_client(use_service_role=True).client

    # ---------- Create ----------
    async def create(
        self, payload: EnumItemCreate, user_id: Optional[str] = None
    ) -> EnumItemResponse:
        data = payload.dict()
        data["slug"] = slugify(data["name"])
        if user_id:
            data["created_by"] = user_id
            data["updated_by"] = user_id

        result = self.supabase.table(self.table).insert([data]).execute()
        rows = result.data or []
        return EnumItemResponse(
            success=len(rows) == 1,
            message="Created successfully" if rows else "Create failed",
            data=EnumItem(**rows[0]) if rows else None,
        )

    # ---------- Read ----------
    async def get(self, item_id: str) -> EnumItemResponse:
        result = (
            self.supabase.table(self.table)
            .select("*")
            .eq("id", item_id)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        return EnumItemResponse(
            success=len(rows) == 1,
            message="Retrieved successfully" if rows else "Not found",
            data=EnumItem(**rows[0]) if rows else None,
        )

    # ---------- List ----------
    async def list(
        self,
        search: Optional[str] = None,
        is_active: Optional[bool] = True,
        page: int = 1,
        page_size: int = 100,
    ) -> EnumItemListResponse:
        query = self.supabase.table(self.table).select("*", count="exact")

        if is_active is not None:
            query = query.eq("is_active", is_active)

        if search:
            like = f"%{search}%"
            # Note: Removed .or_() as Supabase Python client doesn't support it
            # Using ilike on name only - description filtering can be done in Python if needed
            query = query.ilike("name", like)

        # Stable ordering by name (sort_order removed by request)
        query = query.order("name", desc=False)

        offset = (page - 1) * page_size
        query = query.range(offset, offset + page_size - 1)

        result = query.execute()
        total = result.count or 0
        items = [EnumItem(**row) for row in (result.data or [])]

        return EnumItemListResponse(
            success=True,
            message="List retrieved successfully",
            data=items,
            total=total,
            page=page,
            page_size=page_size,
        )

    # ---------- Update ----------
    async def update(
        self, item_id: str, payload: EnumItemUpdate, user_id: Optional[str] = None
    ) -> EnumItemResponse:
        data = {k: v for k, v in payload.dict().items() if v is not None}
        if "name" in data:
            data["slug"] = slugify(data["name"])
        if user_id:
            data["updated_by"] = user_id

        result = (
            self.supabase.table(self.table).update(data).eq("id", item_id).execute()
        )
        rows = result.data or []
        return EnumItemResponse(
            success=len(rows) == 1,
            message="Updated successfully" if rows else "Update failed",
            data=EnumItem(**rows[0]) if rows else None,
        )

    # ---------- Activate/Deactivate ----------
    async def set_active(
        self, item_id: str, active: bool, user_id: Optional[str] = None
    ) -> EnumItemResponse:
        data = {"is_active": active}
        if user_id:
            data["updated_by"] = user_id

        result = (
            self.supabase.table(self.table).update(data).eq("id", item_id).execute()
        )
        rows = result.data or []
        msg = "Activated successfully" if active else "Deactivated successfully"
        return EnumItemResponse(
            success=len(rows) == 1,
            message=msg if rows else "State change failed",
            data=EnumItem(**rows[0]) if rows else None,
        )

    # ---------- Delete (hard delete) ----------
    async def delete(self, item_id: str) -> EnumItemResponse:
        result = self.supabase.table(self.table).delete().eq("id", item_id).execute()
        existed = result.data or []

        return EnumItemResponse(
            success=len(existed) == 1,
            message="Deleted successfully" if existed else "Not found",
            data=EnumItem(**existed[0]) if existed else None,
        )


# ---------- Typed services ----------
class IndustriesService(BaseEnumService):
    def __init__(self):
        super().__init__("profile_industries")


class ResponsibilitiesService(BaseEnumService):
    def __init__(self):
        super().__init__("profile_responsibilities")


class CommitmentsService(BaseEnumService):
    def __init__(self):
        super().__init__("profile_commitments")


class VentureStagesService(BaseEnumService):
    def __init__(self):
        super().__init__("profile_venture_stages")


class LanguagesService(BaseEnumService):
    def __init__(self):
        super().__init__("profile_languages")
