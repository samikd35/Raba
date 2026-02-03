"""
Pydantic models for admin credit granting and organization credit allocation.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, validator


class AdminCreditGrantRequest(BaseModel):
    """Request model for admins/super admins to grant credits to an organization."""
    organization_id: str = Field(..., description="Organization tenant ID to grant credits to")
    credit_amount: int = Field(..., gt=0, description="Number of credits to grant (must be > 0)")

    @validator('credit_amount')
    def validate_credit_amount(cls, v):
        if v < 1:
            raise ValueError('Credit amount must be at least 1')
        return v


class AdminCreditGrantResponse(BaseModel):
    """Response model for credit grant operation."""
    success: bool = True
    message: str
    organization_id: str
    organization_name: str
    credit_amount: int
    expires_at: datetime
    granted_by: str
    granted_at: datetime
    lot_id: Optional[str] = None
    email_sent: bool = False
    email_recipient: Optional[str] = None


class OrganizationCreditAllocationRequest(BaseModel):
    """Request model for organizations to allocate credits to tenants."""
    tenant_id: str = Field(..., description="Tenant ID (individual or team) to allocate credits to")
    tenant_type: str = Field(..., description="Type of tenant: 'individual' or 'team'")
    credit_amount: int = Field(..., gt=0, description="Number of credits to allocate (must be > 0)")

    @validator('tenant_type')
    def validate_tenant_type(cls, v):
        if v not in ['individual', 'team']:
            raise ValueError("tenant_type must be either 'individual' or 'team'")
        return v

    @validator('credit_amount')
    def validate_credit_amount(cls, v):
        if v < 1:
            raise ValueError('Credit amount must be at least 1')
        return v


class OrganizationCreditAllocationResponse(BaseModel):
    """Response model for credit allocation operation."""
    success: bool = True
    message: str
    organization_id: str
    organization_name: Optional[str] = None
    tenant_id: str
    tenant_name: Optional[str] = None
    tenant_type: str
    credit_amount: int
    expires_at: datetime
    allocated_by: str
    allocated_at: datetime
    remaining_org_credits: float
    email_sent: bool = False
    email_recipient: Optional[str] = None


class CreditBalance(BaseModel):
    """Model for credit balance information."""
    tenant_id: str
    tenant_name: str
    tenant_type: str
    total_credits: float
    active_lots: int
    details: List[dict] = []


class OrganizationCreditsOverview(BaseModel):
    """Overview of organization's credit status."""
    organization_id: str
    organization_name: str
    total_available_credits: float
    total_lots: int
    total_allocated_to_individuals: float
    total_allocated_to_teams: float
    lot_details: List[dict] = []


class BulkAllocationItem(BaseModel):
    """Single allocation in a bulk allocation request."""
    tenant_id: str = Field(..., description="Tenant ID (individual or team) to allocate credits to")
    tenant_type: str = Field(..., description="Type of tenant: 'individual' or 'team'")
    credit_amount: int = Field(..., gt=0, description="Number of credits to allocate (must be > 0)")

    @validator('tenant_type')
    def validate_tenant_type(cls, v):
        if v not in ['individual', 'team']:
            raise ValueError("tenant_type must be either 'individual' or 'team'")
        return v

    @validator('credit_amount')
    def validate_credit_amount(cls, v):
        if v < 1:
            raise ValueError('Credit amount must be at least 1')
        return v


class BulkAllocationRequest(BaseModel):
    """Request model for bulk credit allocation to multiple tenants."""
    allocations: List[BulkAllocationItem] = Field(..., min_items=1, max_items=100, description="List of allocations to perform")

    @validator('allocations')
    def validate_allocations(cls, v):
        if not v:
            raise ValueError('At least one allocation is required')
        if len(v) > 100:
            raise ValueError('Maximum 100 allocations per request')
        return v


class BulkAllocationResult(BaseModel):
    """Result of a single allocation in bulk operation."""
    tenant_id: str
    tenant_name: Optional[str] = None
    tenant_type: str
    credit_amount: int
    success: bool
    error: Optional[str] = None


class BulkAllocationResponse(BaseModel):
    """Response model for bulk credit allocation operation."""
    success: bool
    message: str
    organization_id: str
    organization_name: Optional[str] = None
    total_requested: int
    successful_count: int
    failed_count: int
    results: List[BulkAllocationResult]
    remaining_org_credits: float
    allocated_by: str
    allocated_at: datetime


class ToggleOrganizationCreditsRequest(BaseModel):
    """Request model for toggling organization's distributed credits suspension."""
    is_active: bool = Field(..., description="True to activate credits, False to suspend them")


class ToggleOrganizationCreditsResponse(BaseModel):
    """Response model for toggling organization's distributed credits suspension."""
    success: bool
    message: str
    organization_id: str
    organization_name: str
    affected_lot_count: int
    new_state: str  # "active" or "suspended"
    toggled_by: str
    toggled_at: datetime
