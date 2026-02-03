from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, condecimal, validator

# ---- Base & IO models ----


class CreditRateBase(BaseModel):
    currency: str = Field(
        ..., min_length=3, max_length=3, description="3-letter ISO 4217 code"
    )
    credits_per_unit: condecimal(max_digits=18, decimal_places=6) = Field(..., ge=0)
    is_active: bool = True

    @validator("currency")
    def normalize_currency(cls, v: str) -> str:
        v = (v or "").strip().upper()
        if len(v) != 3:
            raise ValueError("currency must be a 3-letter ISO 4217 code")
        return v

    class Config:
        json_encoders = {Decimal: lambda v: str(v)}


class CreditRateCreate(CreditRateBase):
    """Payload for creating a new exchange rate row."""

    pass


class CreditRateUpdate(BaseModel):
    """Partial update; at least one field must be present."""

    credits_per_unit: Optional[condecimal(max_digits=18, decimal_places=6)] = Field(
        None, ge=0
    )
    is_active: Optional[bool] = None

    class Config:
        json_encoders = {Decimal: lambda v: str(v)}


class CreditRateOut(CreditRateBase):
    created_at: datetime
    updated_at: datetime
