from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


# ---------- Schemas ----------
class CreditLotOut(BaseModel):
    id: str
    credit_amount: float
    valid_from: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class CreditsSummaryResponse(BaseModel):
    tenant_id: str
    lots: List[CreditLotOut]
    tenant_total_active_credits: float
    user_total_consumed_in_tenant: int


class ConsumptionAllocationOut(BaseModel):
    lot_id: str
    amount_used: int


class ConsumptionOut(BaseModel):
    id: str
    created_at: datetime
    tenant_id: str
    user_id: str
    feature_id: Optional[str] = None
    request_id: Optional[str] = None
    cost: int
    reason: Optional[str] = None
    project_id: Optional[str] = None
    workflow_id: Optional[str] = None
    metadata: Dict[str, Any] = {}
    allocations: Optional[List[ConsumptionAllocationOut]] = None


class ConsumptionsResponse(BaseModel):
    items: List[ConsumptionOut]
