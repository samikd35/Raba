"""
Payment Data Models

This module defines Pydantic models for payment operations including:
1. Payment requests and responses
2. Credit packages and pricing
3. Payment status tracking
4. Payment history
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
from decimal import Decimal

from pydantic import BaseModel, Field, validator
from uuid import UUID


class PaymentStatus(str, Enum):
    """Payment status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentMethod(str, Enum):
    """Payment method enumeration."""
    STRIPE_CARD = "stripe_card"
    STRIPE_BANK = "stripe_bank"
    PAYPAL = "paypal"
    APPLE_PAY = "apple_pay"
    GOOGLE_PAY = "google_pay"


class CreditType(str, Enum):
    """Credit type enumeration."""
    GENERAL = "general"
    PROBLEM_GENERATOR = "problem_generator"
    MARKET_VALIDATION = "market_validation"


class CreditPackage(BaseModel):
    """Credit package definition."""
    id: str = Field(..., description="Package identifier")
    name: str = Field(..., description="Package display name")
    credits: int = Field(..., ge=1, description="Number of credits in package")
    price: Decimal = Field(..., ge=0, description="Price in USD")
    credit_type: CreditType = Field(default=CreditType.GENERAL, description="Type of credits")
    popular: bool = Field(default=False, description="Whether this is a popular package")
    bonus_credits: int = Field(default=0, ge=0, description="Bonus credits included")
    description: Optional[str] = Field(None, description="Package description")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }


class PaymentRequest(BaseModel):
    """Payment request model."""
    package_id: str = Field(..., description="Credit package identifier")
    payment_method: PaymentMethod = Field(..., description="Payment method")
    return_url: Optional[str] = Field(None, description="URL to redirect after payment")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "package_id": "credits_50",
                "payment_method": "stripe_card",
                "return_url": "https://yourapp.com/payment/success",
                "metadata": {"source": "dashboard"}
            }
        }


class PaymentResponse(BaseModel):
    """Payment response model."""
    payment_id: str = Field(..., description="Payment identifier")
    status: PaymentStatus = Field(..., description="Payment status")
    package: CreditPackage = Field(..., description="Credit package details")
    amount: Decimal = Field(..., description="Payment amount")
    currency: str = Field(default="USD", description="Payment currency")
    payment_url: Optional[str] = Field(None, description="URL for payment completion")
    client_secret: Optional[str] = Field(None, description="Stripe client secret")
    expires_at: Optional[datetime] = Field(None, description="Payment expiration time")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat()
        }


class PaymentHistory(BaseModel):
    """Payment history record."""
    payment_id: str = Field(..., description="Payment identifier")
    user_id: str = Field(..., description="User identifier")
    package: CreditPackage = Field(..., description="Credit package purchased")
    amount: Decimal = Field(..., description="Payment amount")
    currency: str = Field(default="USD", description="Payment currency")
    status: PaymentStatus = Field(..., description="Payment status")
    payment_method: PaymentMethod = Field(..., description="Payment method used")
    credits_granted: int = Field(..., description="Credits granted to user")
    transaction_id: Optional[str] = Field(None, description="External transaction ID")
    created_at: datetime = Field(..., description="Payment creation time")
    completed_at: Optional[datetime] = Field(None, description="Payment completion time")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat()
        }


class PaymentListResponse(BaseModel):
    """Payment list response model."""
    payments: List[PaymentHistory] = Field(..., description="List of payments")
    total_count: int = Field(..., description="Total number of payments")
    page: int = Field(default=1, description="Current page number")
    per_page: int = Field(default=20, description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")
    
    @validator('total_pages', pre=False, always=True)
    def calculate_total_pages(cls, v, values):
        total_count = values.get('total_count', 0)
        per_page = values.get('per_page', 20)
        return max(1, (total_count + per_page - 1) // per_page)


class CreditPackageListResponse(BaseModel):
    """Credit packages list response."""
    packages: List[CreditPackage] = Field(..., description="Available credit packages")
    currency: str = Field(default="USD", description="Pricing currency")


class PaymentWebhookEvent(BaseModel):
    """Payment webhook event model."""
    event_type: str = Field(..., description="Webhook event type")
    payment_id: str = Field(..., description="Payment identifier")
    status: PaymentStatus = Field(..., description="New payment status")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Event metadata")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
