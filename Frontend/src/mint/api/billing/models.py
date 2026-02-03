"""
Pydantic models for billing and cohort API endpoints.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator


# ============================================================================
# Pricing Configuration Models
# ============================================================================

class PricingConfigResponse(BaseModel):
    """Response model for pricing configuration"""
    id: str
    admin_seat_price_credits: int
    estimated_credits_per_user: int
    is_active: bool
    effective_from: datetime
    effective_until: Optional[datetime] = None
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class UpdatePricingConfigRequest(BaseModel):
    """Request model for updating pricing configuration"""
    admin_seat_price_credits: int = Field(..., ge=0, description="Price per admin seat in credits")
    estimated_credits_per_user: int = Field(..., ge=0, description="Estimated credits per user for bulk purchase")

    @validator('admin_seat_price_credits', 'estimated_credits_per_user')
    def validate_non_negative(cls, v):
        if v < 0:
            raise ValueError('Value must be non-negative')
        return v


# ============================================================================
# Invoice Models
# ============================================================================

class InvoiceLineItemResponse(BaseModel):
    """Response model for invoice line item"""
    id: str
    invoice_id: str
    item_type: str
    description: str
    quantity: int
    unit_price_credits: int
    total_price_credits: int
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime


class InvoiceResponse(BaseModel):
    """Response model for invoice"""
    id: str
    invoice_number: str
    tenant_id: str
    period_start: datetime
    period_end: datetime
    credits_allocated: int
    admin_seat_charges: int
    total_amount_credits: int
    admin_seats_count: int
    members_count: int
    status: str
    issued_at: datetime
    due_date: datetime
    paid_at: Optional[datetime] = None
    payment_method: Optional[str] = None
    payment_reference: Optional[str] = None
    stripe_invoice_id: Optional[str] = None
    stripe_hosted_invoice_url: Optional[str] = None
    stripe_invoice_pdf: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


class InvoiceWithLineItemsResponse(BaseModel):
    """Response model for invoice with line items"""
    invoice: InvoiceResponse
    line_items: List[InvoiceLineItemResponse]


class MarkInvoicePaidRequest(BaseModel):
    """Request model for manually marking invoice as paid"""
    payment_method: str = Field(..., description="Payment method (manual, bank_transfer, check, other)")
    payment_reference: Optional[str] = Field(None, description="Payment reference or transaction ID")
    payment_notes: Optional[str] = Field(None, description="Additional notes about the payment")


# ============================================================================
# Bulk Purchase Models
# ============================================================================

class BulkPurchaseRequest(BaseModel):
    """Request model for bulk credit purchase"""
    member_count: int = Field(..., ge=0, description="Number of members to allocate credits for")
    credits_per_member: Optional[int] = Field(None, ge=0, description="Credits per member (uses default if not provided)")
    currency: str = Field(default="USD", description="Currency code (e.g., USD, NGN, EUR)")

    @validator('member_count')
    def validate_member_count(cls, v):
        if v < 0:
            raise ValueError('Member count must be non-negative')
        return v

    @validator('currency')
    def validate_currency(cls, v):
        return v.upper()


class BulkPurchaseResponse(BaseModel):
    """Response model for bulk credit purchase calculation"""
    tenant_id: str
    member_count: int
    credits_per_member: int
    member_credits_total: int
    admin_seats_count: int
    admin_seat_price_credits: int
    admin_seats_total: int
    total_credits: int
    total_amount: float
    currency: str
    tx_ref: str
    checkout_url: Optional[str] = None  # Only for prepay_org (Stripe payment required)
    session_id: Optional[str] = None  # Only for prepay_org (Stripe session ID)


class BulkPurchaseVerifyResponse(BaseModel):
    """Response model for bulk purchase payment verification"""
    ok: bool
    message: str
    tx_ref: str
    credits_allocated: Optional[int] = None
    session_id: Optional[str] = None
    payment_intent: Optional[str] = None


# ============================================================================
# Direct Allocation Bulk Purchase Models
# ============================================================================

class TenantAllocation(BaseModel):
    """Model for individual tenant credit allocation"""
    tenant_id: str = Field(..., description="Tenant ID (member/team individual tenant)")
    credit_amount: float = Field(..., ge=1, description="Credits to allocate to this tenant (supports decimals)")


class BulkPurchaseDirectRequest(BaseModel):
    """Request model for direct allocation bulk purchase"""
    allocations: List[TenantAllocation] = Field(..., min_items=1, description="List of tenant allocations")
    currency: str = Field(default="USD", description="Currency code (e.g., USD, NGN, EUR)")

    @validator('allocations')
    def validate_allocations(cls, v):
        if not v:
            raise ValueError('At least one allocation is required')
        # Check for duplicate tenant_ids
        tenant_ids = [a.tenant_id for a in v]
        if len(tenant_ids) != len(set(tenant_ids)):
            raise ValueError('Duplicate tenant_ids in allocations')
        return v

    @validator('currency')
    def validate_currency(cls, v):
        return v.upper()


class BulkPurchaseDirectResponse(BaseModel):
    """Response model for direct allocation bulk purchase"""
    tenant_id: str  # Organization tenant ID
    allocations: List[TenantAllocation]
    total_credits: int
    total_amount: float
    currency: str
    tx_ref: str
    checkout_url: Optional[str] = None  # Only for prepay_org
    session_id: Optional[str] = None  # Only for prepay_org


class BulkPurchaseDirectVerifyResponse(BaseModel):
    """Response model for direct allocation bulk purchase verification"""
    ok: bool
    message: str
    tx_ref: str
    allocations_completed: Optional[int] = None
    session_id: Optional[str] = None
    payment_intent: Optional[str] = None


# ============================================================================
# Admin Seat Billing History Models
# ============================================================================

class AdminSeatBillingHistoryResponse(BaseModel):
    """Response model for admin seat billing history"""
    id: str
    tenant_id: str
    billing_period_start: datetime
    billing_period_end: datetime
    admin_seats_count: int
    seat_price_credits: int
    total_charged_credits: int
    consumption_id: Optional[str] = None
    deducted_at: Optional[datetime] = None
    invoice_id: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime


# ============================================================================
# Cohort Models
# ============================================================================

class CohortMemberProjectSummary(BaseModel):
    """Summary information for a single project in cohort member response."""

    id: str = Field(..., description="Project unique identifier")
    name: str = Field(..., description="Project name")
    description: Optional[str] = Field(None, description="Project description")
    current_step: str = Field(..., description="Current project step/stage")
    progress_percentage: Optional[int] = Field(None, description="Project completion percentage")
    created_at: datetime = Field(..., description="Project creation timestamp")
    updated_at: datetime = Field(..., description="Project last update timestamp")

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class CreateCohortRequest(BaseModel):
    """Request model for creating a cohort"""
    name: str = Field(..., min_length=1, max_length=255, description="Cohort name")
    description: Optional[str] = Field(None, description="Cohort description")
    color: Optional[str] = Field(None, max_length=50, description="Color code for UI display")
    settings: Optional[Dict[str, Any]] = Field(None, description="Additional cohort settings")


class UpdateCohortRequest(BaseModel):
    """Request model for updating a cohort"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="New cohort name")
    description: Optional[str] = Field(None, description="New description")
    color: Optional[str] = Field(None, max_length=50, description="New color code")
    settings: Optional[Dict[str, Any]] = Field(None, description="New settings")


class CohortResponse(BaseModel):
    """Response model for cohort"""
    id: str
    tenant_id: str
    name: str
    description: Optional[str] = None
    color: Optional[str] = None
    is_active: bool
    settings: Optional[Dict[str, Any]] = None
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class AssignMemberToCohortRequest(BaseModel):
    """Request model for assigning member to cohort"""
    member_tenant_id: str = Field(..., description="Tenant ID (individual or team) to assign to cohort")


class MoveMemberToCohortRequest(BaseModel):
    """Request model for moving member between cohorts"""
    target_cohort_id: str = Field(..., description="Target cohort ID to move the user to")


# ============================================================================
# Bulk Cohort Membership Models
# ============================================================================

class BulkMemberResult(BaseModel):
    """Result for a single member in a bulk operation"""
    member_tenant_id: str
    success: bool
    error: Optional[str] = None


class BulkAssignMembersRequest(BaseModel):
    """Request model for bulk assigning members to cohort"""
    member_tenant_ids: List[str] = Field(..., min_items=1, description="List of tenant IDs to assign")

    @validator('member_tenant_ids')
    def validate_no_duplicates(cls, v):
        if len(v) != len(set(v)):
            raise ValueError('Duplicate member_tenant_ids not allowed')
        return v


class BulkAssignMembersResponse(BaseModel):
    """Response model for bulk assign members"""
    cohort_id: str
    total_requested: int
    successful: int
    failed: int
    results: List[BulkMemberResult]


class BulkRemoveMembersRequest(BaseModel):
    """Request model for bulk removing members from cohort"""
    member_tenant_ids: List[str] = Field(..., min_items=1, description="List of tenant IDs to remove")

    @validator('member_tenant_ids')
    def validate_no_duplicates(cls, v):
        if len(v) != len(set(v)):
            raise ValueError('Duplicate member_tenant_ids not allowed')
        return v


class BulkRemoveMembersResponse(BaseModel):
    """Response model for bulk remove members"""
    cohort_id: str
    total_requested: int
    successful: int
    failed: int
    results: List[BulkMemberResult]


class BulkMoveMembersRequest(BaseModel):
    """Request model for bulk moving members between cohorts"""
    member_tenant_ids: List[str] = Field(..., min_items=1, description="List of tenant IDs to move")
    target_cohort_id: str = Field(..., description="Target cohort ID")

    @validator('member_tenant_ids')
    def validate_no_duplicates(cls, v):
        if len(v) != len(set(v)):
            raise ValueError('Duplicate member_tenant_ids not allowed')
        return v


class BulkMoveMembersResponse(BaseModel):
    """Response model for bulk move members"""
    source_cohort_id: str
    target_cohort_id: str
    total_requested: int
    successful: int
    failed: int
    results: List[BulkMemberResult]


class CohortMemberResponse(BaseModel):
    """Response model for cohort member"""
    id: str
    cohort_id: str
    member_tenant_id: str
    tenant_type: Optional[str] = None  # 'individual' or 'team'
    tenant_name: Optional[str] = None  # Tenant name for display
    # Consistency fields (populated for both individuals and teams)
    user_id: Optional[str] = None  # User ID (individuals) or Tenant ID (teams)
    user_email: Optional[str] = None  # User email (individuals) or first admin email (teams)
    user_name: Optional[str] = None  # User name (individuals) or team name (teams)
    user_role: Optional[str] = None  # Role in organization (for individuals)
    # Team-specific fields (only for teams)
    team_name: Optional[str] = None
    team_contact_email: Optional[str] = None
    team_admin_emails: Optional[List[str]] = None
    # Project fields
    project_count: int = Field(0, description="Total number of projects")
    pv_report_count: int = Field(0, description="Total number of PV reports generated")
    projects: List[CohortMemberProjectSummary] = Field(default_factory=list, description="List of recent projects")
    created_at: datetime


class CohortWithMembersResponse(BaseModel):
    """Response model for cohort with member details"""
    cohort: CohortResponse
    members: List[CohortMemberResponse]
    member_count: int


class CohortMembersListResponse(BaseModel):
    """Paginated response for listing cohort members"""
    members: List[CohortMemberResponse] = Field(..., description="List of cohort members")
    total_count: int = Field(..., description="Total number of members")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    has_next: bool = Field(..., description="Whether there are more pages")


class CohortProjectResponse(BaseModel):
    """Response model for a project within a cohort"""
    id: str = Field(..., description="Project unique identifier")
    name: str = Field(..., description="Project name")
    description: Optional[str] = Field(None, description="Project description")
    current_step: Optional[str] = Field(None, description="Current project step/stage")
    status: Optional[str] = Field(None, description="Project status")
    created_at: datetime = Field(..., description="Project creation timestamp")
    updated_at: datetime = Field(..., description="Project last update timestamp")
    # Owner information
    tenant_id: str = Field(..., description="Owner tenant ID")
    tenant_name: Optional[str] = Field(None, description="Owner tenant name")
    tenant_type: Optional[str] = Field(None, description="Owner tenant type (individual/team)")
    owner_email: Optional[str] = Field(None, description="Owner email (for individuals)")
    owner_name: Optional[str] = Field(None, description="Owner name (for individuals)")

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class CohortProjectsListResponse(BaseModel):
    """Paginated response for listing cohort projects"""
    projects: List[CohortProjectResponse] = Field(..., description="List of projects in the cohort")
    total_count: int = Field(..., description="Total number of projects")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    has_next: bool = Field(..., description="Whether there are more pages")
    cohort_id: str = Field(..., description="Cohort ID")
    cohort_name: str = Field(..., description="Cohort name")


# ============================================================================
# Common Response Models
# ============================================================================

class SuccessResponse(BaseModel):
    """Generic success response"""
    success: bool = True
    message: str


class ErrorResponse(BaseModel):
    """Generic error response"""
    success: bool = False
    error: str
    detail: Optional[str] = None
