from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

# ---------- Models ----------
TenantType = Literal["individual", "team"]


def _dump(model: BaseModel) -> dict:
    # Works with both Pydantic v1 and v2
    return (
        model.model_dump(exclude_unset=True)
        if hasattr(model, "model_dump")
        else model.dict(exclude_unset=True)
    )


class CreditPackageBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    tenant_type: TenantType
    credits_per_user: int = Field(..., gt=0)
    is_active: Optional[bool] = True


class CreditPackageCreate(CreditPackageBase):
    pass


class CreditPackageUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=120)
    tenant_type: Optional[TenantType] = None
    credits_per_user: Optional[int] = Field(None, gt=0)
    is_active: Optional[bool] = None


class CreditPackage(CreditPackageBase):
    id: UUID
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
