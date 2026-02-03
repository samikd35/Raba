"""
Module Features Models (Admin).
Pydantic schemas for CRUD on public.module_features.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

ALLOWED_FEATURE_TYPES = {"generator", "analyzer", "validator", "reporter"}


class ModuleFeatureBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    display_name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    feature_type: str = Field(
        ..., description="One of: generator, analyzer, validator, reporter"
    )
    credit_cost: int = Field(1, gt=0)
    is_active: Optional[bool] = True
    settings: Optional[Dict[str, Any]] = Field(default_factory=dict)

    def validate_feature_type(self) -> None:
        if self.feature_type not in ALLOWED_FEATURE_TYPES:
            raise ValueError(
                f"feature_type must be one of {sorted(ALLOWED_FEATURE_TYPES)}"
            )


class ModuleFeatureCreate(ModuleFeatureBase):
    pass


class ModuleFeatureUpdate(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    feature_type: Optional[str] = None
    credit_cost: Optional[int] = Field(None, gt=0)
    is_active: Optional[bool] = None
    settings: Optional[Dict[str, Any]] = None

    def validate_feature_type(self) -> None:
        if (
            self.feature_type is not None
            and self.feature_type not in ALLOWED_FEATURE_TYPES
        ):
            raise ValueError(
                f"feature_type must be one of {sorted(ALLOWED_FEATURE_TYPES)}"
            )


class ModuleFeatureOut(ModuleFeatureBase):
    id: UUID
    created_at: datetime

    # matches your other models’ config style
    model_config = ConfigDict(from_attributes=True)


ALLOWED_PLAN_TYPES = {"individual", "team", "organization"}


class FeatureCreditCostBase(BaseModel):
    feature_id: UUID
    plan_type: str = Field(..., description="One of: individual, team, organization")
    credit_cost: int = Field(..., ge=0)  # Changed from gt=0 to ge=0 to allow free (0 cost)
    is_active: Optional[bool] = True
    effective_from: Optional[datetime] = None
    effective_until: Optional[datetime] = None

    def validate_plan_type(self) -> None:
        if self.plan_type not in ALLOWED_PLAN_TYPES:
            raise ValueError(f"plan_type must be one of {sorted(ALLOWED_PLAN_TYPES)}")


class FeatureCreditCostCreate(FeatureCreditCostBase):
    pass


class FeatureCreditCostUpdate(BaseModel):
    plan_type: Optional[str] = None
    credit_cost: Optional[int] = Field(None, ge=0)  # Changed from gt=0 to ge=0 to allow free (0 cost)
    is_active: Optional[bool] = None
    effective_from: Optional[datetime] = None
    effective_until: Optional[datetime] = None

    def validate_plan_type(self) -> None:
        if self.plan_type is not None and self.plan_type not in ALLOWED_PLAN_TYPES:
            raise ValueError(f"plan_type must be one of {sorted(ALLOWED_PLAN_TYPES)}")


class FeatureCreditCostOut(FeatureCreditCostBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ResolvedFeatureCostOut(BaseModel):
    feature_id: UUID
    plan_type: str
    credit_cost: int
    source: str  # "feature_credit_costs" | "module_features"
    effective_from: Optional[datetime] = None
    effective_until: Optional[datetime] = None
