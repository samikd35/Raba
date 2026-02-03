from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field, constr

ISO4217 = constr(pattern=r"^[A-Z]{3}$")


class CreatePaymentBody(BaseModel):
    amount: Decimal = Field(gt=0)
    currency: ISO4217 = "USD"
    email: EmailStr | None = None
    name: constr(strip_whitespace=True, min_length=1, max_length=120) | None = None


class CreatePaymentResp(BaseModel):
    checkout_link: str
    tx_ref: str


class VerifyResp(BaseModel):
    ok: bool
    message: str
    tx_id: int | None = None
    tx_ref: str | None = None
    raw: dict | None = None
