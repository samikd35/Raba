from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class PaymentInviteItem(BaseModel):
    email: EmailStr
    is_admin: bool = False
    is_team_leader: bool = False
    credit_allocated: int = Field(..., gt=0)
    can_skip_modules: bool = False


class PaymentInviteRequest(BaseModel):
    invites: List[PaymentInviteItem]
    currency: Optional[str] = None
