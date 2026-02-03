"""
Venture Builder Pydantic models for API requests and responses.
"""

from datetime import datetime, time, timezone
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, HttpUrl, root_validator, validator


# =====================================================
# STANDARD API RESPONSES
# =====================================================

class StandardSuccessResponse(BaseModel):
    """Standard success response wrapper"""
    success: bool = True
    data: Optional[Dict] = None
    error: Optional[str] = None


class StandardErrorResponse(BaseModel):
    """Standard error response wrapper"""
    success: bool = False
    data: Optional[Dict] = None
    error: str


# =====================================================
# ENUMS
# =====================================================

class VBStatus(str, Enum):
    """Venture Builder status"""
    PENDING_PROFILE = "pending_profile"
    PENDING_ADMIN_REVIEW = "pending_admin_review"
    ACTIVE = "active"
    INACTIVE = "inactive"


class SessionStatus(str, Enum):
    """Session booking status"""
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    SETTLED = "settled"  # Payment reconciled/settled
    CANCELED = "canceled"


class DisputeReason(str, Enum):
    """Dispute reason"""
    MISSED_SESSION = "missed_session"  # VB no-show
    TIME_THEFT = "time_theft"          # VB arrived late or ended early
    OTHER = "other"                     # Custom reason


class DisputeStatus(str, Enum):
    """Dispute status lifecycle"""
    SUBMITTED = "submitted"             # Initial state when user creates dispute
    UNDER_REVIEW = "under_review"       # Admin is reviewing the dispute
    RESOLVED = "resolved"               # Dispute has been resolved


# =====================================================
# WORK EXPERIENCE
# =====================================================

class WorkExperienceItem(BaseModel):
    """Work experience entry"""
    position: str = Field(..., min_length=1, max_length=200)
    organization: str = Field(..., min_length=1, max_length=200)
    years: str = Field(..., description="e.g., '2020-2023' or '2 years'")
    description: Optional[str] = Field(None, max_length=1000)


# =====================================================
# AREAS OF EXPERTISE
# =====================================================

class ExpertiseAreaBase(BaseModel):
    """Base expertise area model"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    display_order: int = Field(default=0, ge=0)


class ExpertiseAreaCreate(ExpertiseAreaBase):
    """Create expertise area (Admin only)"""
    pass


class ExpertiseAreaUpdate(BaseModel):
    """Update expertise area (Admin only)"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    display_order: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class ExpertiseAreaResponse(ExpertiseAreaBase):
    """Expertise area response"""
    id: UUID
    is_active: bool = True
    is_custom: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# =====================================================
# VENTURE BUILDER PROFILE
# =====================================================

class VBProfileBase(BaseModel):
    """Base VB profile fields"""
    name: str = Field(..., min_length=1, max_length=200)
    contact_email: EmailStr
    main_expertise: str = Field(..., min_length=1, max_length=300)
    short_intro: str = Field(..., min_length=1, max_length=500)
    profile_picture_url: Optional[str] = None
    biography: str = Field(..., min_length=50, max_length=2000)
    linkedin_url: Optional[HttpUrl] = None


class VBProfileCreate(VBProfileBase):
    """Create/Update VB profile"""
    work_experience: List[WorkExperienceItem] = Field(..., min_items=1)
    expertise_ids: List[UUID] = Field(default=[], description="IDs of predefined expertise areas")
    other_expertise: Optional[List[str]] = Field(None, description="List of custom expertise names to create")

    @validator('work_experience')
    def validate_work_experience(cls, v):
        if len(v) > 10:
            raise ValueError('Maximum 10 work experience entries allowed')
        return v

    @validator('expertise_ids')
    def validate_expertise_ids(cls, v):
        if len(v) > 5:
            raise ValueError('Maximum 5 predefined expertise areas allowed')
        return v

    @validator('other_expertise')
    def validate_other_expertise(cls, v):
        if v is not None and len(v) > 5:
            raise ValueError('Maximum 5 custom expertise entries allowed')
        return v


class VBProfileUpdate(BaseModel):
    """Update VB profile (partial update)"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    contact_email: Optional[EmailStr] = None
    main_expertise: Optional[str] = Field(None, min_length=1, max_length=300)
    short_intro: Optional[str] = Field(None, min_length=1, max_length=500)
    profile_picture_url: Optional[str] = None
    biography: Optional[str] = Field(None, min_length=50, max_length=2000)
    linkedin_url: Optional[HttpUrl] = None
    work_experience: Optional[List[WorkExperienceItem]] = None
    expertise_ids: Optional[List[UUID]] = None
    other_expertise: Optional[List[str]] = Field(None, description="List of custom expertise names to create")


class VBProfileResponse(VBProfileBase):
    """VB profile response"""
    id: UUID
    user_id: UUID
    work_experience: List[WorkExperienceItem]
    calendar_booking_url: Optional[str] = None
    credit_price_per_hour: int = 0
    status: VBStatus
    areas_of_expertise: List[ExpertiseAreaResponse]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class VBListingItem(BaseModel):
    """VB listing item for browse page"""
    id: UUID
    user_id: UUID
    name: str
    profile_picture_url: Optional[str]
    main_expertise: str
    short_intro: str
    biography: str
    linkedin_url: Optional[HttpUrl]
    credit_price_per_hour: int
    areas_of_expertise: List[ExpertiseAreaResponse]

    class Config:
        from_attributes = True


class VBListResponse(BaseModel):
    """VB listing response with pagination"""
    total: int
    items: List[VBListingItem]
    page: int
    page_size: int


class VBPendingListResponse(BaseModel):
    """Response for listing pending VBs (Admin)"""
    success: bool = True
    data: List[VBProfileResponse]
    error: Optional[str] = None


# =====================================================
# ADMIN VB MANAGEMENT
# =====================================================

class VBApprovalRequest(BaseModel):
    """Admin approval request"""
    credit_price_per_hour: int = Field(..., ge=1, description="Credits per hour")
    calendar_booking_url: Optional[str] = Field(None, description="Calendar booking URL (fallback if no Google Calendar)")


class VBPricingUpdate(BaseModel):
    """Update VB pricing"""
    credit_price_per_hour: int = Field(..., ge=1)


class VBPublishRequest(BaseModel):
    """Publish/unpublish VB"""
    is_active: bool


class VBRoleMismatchItem(BaseModel):
    """VB profile with mismatched user role"""
    vb_id: UUID
    user_id: UUID
    vb_name: Optional[str]
    contact_email: Optional[str]
    vb_status: str
    user_role: Optional[str]
    user_email: Optional[str]


class VBRoleMismatchResponse(BaseModel):
    """Response for role mismatch list"""
    items: List[VBRoleMismatchItem]
    total: int


class VBRoleUpdateRequest(BaseModel):
    """Bulk role update request"""
    user_ids: List[UUID]


class VBRoleUpdateResponse(BaseModel):
    """Bulk role update response"""
    updated_user_ids: List[UUID]
    skipped_admin_user_ids: List[UUID]
    missing_user_ids: List[UUID]


class VBRoleRevertResponse(BaseModel):
    """Bulk role revert response"""
    updated_user_ids: List[UUID]
    skipped_non_vb_user_ids: List[UUID]
    missing_user_ids: List[UUID]


# =====================================================
# BOOKING
# =====================================================

class CreditCheckRequest(BaseModel):
    """Check if user has enough credits"""
    venture_builder_id: UUID
    tenant_id: UUID


class CreditCheckResponse(BaseModel):
    """Credit check response"""
    has_sufficient_credits: bool
    current_balance: int
    required_credits: int
    vb_credit_price: int


class ProjectSelectionItem(BaseModel):
    """Project item for selection"""
    id: UUID
    name: str
    tenant_id: UUID


class TermsAcceptanceRequest(BaseModel):
    """Accept T&C request"""
    venture_builder_id: UUID
    tenant_id: UUID
    accepted_terms_version: str = "v1.0"


class VBBookingCreate(BaseModel):
    """Create booking request"""
    venture_builder_id: UUID
    project_id: UUID
    tenant_id: UUID
    session_datetime: datetime
    accepted_terms_version: str = "v1.0"
    agenda: Optional[str] = Field(None, min_length=10, max_length=2000, description="Meeting agenda (10-2000 chars)")

    @validator('session_datetime')
    def validate_future_datetime(cls, v):
        # Ensure timezone-aware comparison
        now = datetime.now(timezone.utc)
        # If v is naive, assume UTC
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        if v <= now:
            raise ValueError('Session datetime must be in the future')
        return v


class VBBookingResponse(BaseModel):
    """Booking response"""
    id: UUID
    tenant_id: UUID
    booked_by_user_id: UUID
    venture_builder_id: UUID
    project_id: UUID
    session_datetime: datetime
    session_duration_minutes: int
    credits_charged: int
    status: SessionStatus
    calendar_event_id: Optional[str] = None
    agenda: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class VBSessionDetail(VBBookingResponse):
    """Session detail with VB info"""
    vb_email: str
    vb_picture: Optional[str]
    has_notes: bool

    class Config:
        from_attributes = True


class VBSessionCancelRequest(BaseModel):
    """Cancel session request (VB only)"""
    cancellation_reason: str = Field(..., min_length=10, max_length=500, description="Reason for cancellation (10-500 chars)")


# =====================================================
# SESSION NOTES
# =====================================================

class VBSessionNoteCreate(BaseModel):
    """Create session note"""
    vb_session_id: UUID
    main_outcomes: str = Field(..., min_length=10, max_length=5000)
    key_takeaways: str = Field(..., min_length=10, max_length=5000)
    next_steps: Optional[str] = Field(None, max_length=2000)
    visible_to_user: bool = True


class VBSessionNoteUpdate(BaseModel):
    """Update session note"""
    main_outcomes: Optional[str] = Field(None, min_length=10, max_length=5000)
    key_takeaways: Optional[str] = Field(None, min_length=10, max_length=5000)
    next_steps: Optional[str] = Field(None, max_length=2000)
    visible_to_user: Optional[bool] = None


class VBSessionNoteResponse(BaseModel):
    """Session note response"""
    id: UUID
    vb_session_id: UUID
    venture_builder_id: UUID
    tenant_id: UUID
    project_id: UUID
    created_by_user_id: UUID
    main_outcomes: str
    key_takeaways: str
    next_steps: Optional[str]
    visible_to_user: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# =====================================================
# EARNINGS
# =====================================================

class SessionEarningsDetail(BaseModel):
    """Per-session earnings detail"""
    session_id: UUID
    session_datetime: datetime
    tenant_name: Optional[str]
    project_name: Optional[str]
    credits_charged: int
    gross_usd: Decimal
    commission_usd: Decimal
    net_usd: Decimal


class VBEarningsResponse(BaseModel):
    """Earnings dashboard response"""
    total_earned_credits: int
    total_earnings_usd: Decimal
    commission_amount_usd: Decimal
    net_earnings_usd: Decimal
    total_reconciled_payments: Decimal
    pending_amount_usd: Decimal
    completed_sessions_period: int
    total_sessions_all_time: int
    sessions: List[SessionEarningsDetail]
    date_range_start: Optional[datetime]
    date_range_end: Optional[datetime]


class EarningsConfigResponse(BaseModel):
    """Earnings config response"""
    credit_to_usd_rate: Decimal
    commission_rate: Decimal
    updated_at: datetime

    class Config:
        from_attributes = True


class EarningsConfigUpdate(BaseModel):
    """Update earnings config (Admin only)"""
    credit_to_usd_rate: Optional[Decimal] = Field(None, gt=0)
    commission_rate: Optional[Decimal] = Field(None, ge=0, le=1)


# =====================================================
# RECONCILIATION
# =====================================================

class VBReconciliationCreate(BaseModel):
    """Create a reconciliation for a VB (Admin only)"""
    start_date: Optional[datetime] = Field(None, description="Optional start date for sessions to reconcile")
    end_date: Optional[datetime] = Field(None, description="Optional end date for sessions to reconcile")
    notes: Optional[str] = Field(None, max_length=1000, description="Optional admin notes about the reconciliation")

    @validator('end_date')
    def validate_date_range(cls, v, values):
        """Ensure end_date is after start_date if both provided"""
        if v and values.get('start_date') and v < values['start_date']:
            raise ValueError('end_date must be after start_date')
        return v


class ReconciliationDetail(BaseModel):
    """Individual reconciliation record"""
    id: UUID
    venture_builder_id: UUID
    reconciled_by: UUID
    reconciled_by_name: Optional[str]
    reconciled_by_email: Optional[str]
    amount_reconciled_usd: Decimal
    pending_amount_before: Decimal
    session_count: int
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class VBReconciliationResponse(BaseModel):
    """Response after reconciliation"""
    reconciliation_id: UUID
    venture_builder_id: UUID
    amount_reconciled_usd: Decimal
    pending_amount_before: Decimal
    pending_amount_after: Decimal
    session_count: int
    sessions_marked_settled: int
    total_reconciled_lifetime: Decimal
    created_at: datetime


class VBReconciliationHistoryResponse(BaseModel):
    """List of reconciliations with pagination"""
    reconciliations: List[ReconciliationDetail]
    total_count: int
    page: int
    page_size: int


# =====================================================
# FILTERS
# =====================================================

class VBListFilters(BaseModel):
    """Filters for VB listing"""
    expertise_ids: Optional[List[UUID]] = None
    search_query: Optional[str] = Field(None, max_length=200)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class SessionFilters(BaseModel):
    """Filters for session listing"""
    status: Optional[SessionStatus] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


# =====================================================
# VB INVITATIONS
# =====================================================

class VBInviteRequest(BaseModel):
    """Request to invite a Venture Builder"""
    email: EmailStr


class VBInviteResponse(BaseModel):
    """Response after sending VB invitation"""
    success: bool
    message: str
    token: str


class VBInviteValidateRequest(BaseModel):
    """Request to validate VB invitation token"""
    token: str


class VBInviteValidateResponse(BaseModel):
    """Response for invitation validation"""
    valid: bool
    email: Optional[str] = None
    error: Optional[str] = None


# =====================================================
# DISPUTES
# =====================================================

class DisputeCreateRequest(BaseModel):
    """User request to create a dispute for a session"""
    reason: DisputeReason
    custom_reason: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)

    @validator('custom_reason')
    def validate_custom_reason(cls, v, values):
        """Require custom_reason when reason is OTHER"""
        if values.get('reason') == DisputeReason.OTHER and not v:
            raise ValueError('custom_reason is required when reason is "other"')
        return v


class DisputeResponse(BaseModel):
    """Dispute response"""
    id: UUID
    session_id: UUID
    user_id: UUID
    vb_id: UUID
    tenant_id: UUID
    reason: DisputeReason
    custom_reason: Optional[str]
    description: Optional[str]
    status: DisputeStatus
    admin_notes: Optional[str]
    resolved_by: Optional[UUID]
    resolved_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DisputeWithDetailsResponse(DisputeResponse):
    """Dispute with session and user details (for admin view)"""
    session_datetime: datetime
    credits_charged: int
    session_status: SessionStatus
    user_name: Optional[str]
    user_email: str
    vb_email: str
    project_name: Optional[str]

    class Config:
        from_attributes = True


class DisputeUpdateRequest(BaseModel):
    """Admin request to update dispute status"""
    status: Optional[DisputeStatus] = None
    admin_notes: Optional[str] = Field(None, max_length=2000)


class CanOpenDisputeResponse(BaseModel):
    """Response indicating whether a dispute can be opened for a session"""
    can_open_dispute: bool
    reason: Optional[str] = None  # Explanation if cannot open


class DisputeListFilters(BaseModel):
    """Filters for dispute listing (admin)"""
    status: Optional[DisputeStatus] = None
    vb_id: Optional[UUID] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


# =====================================================
# GOOGLE CALENDAR INTEGRATION
# =====================================================

class GoogleCalendarAuthURL(BaseModel):
    """OAuth authorization URL response"""
    auth_url: str
    state: str  # CSRF token for validation


class GoogleCalendarStatus(BaseModel):
    """Google Calendar connection status"""
    connected: bool
    calendar_id: Optional[str] = None
    calendar_name: Optional[str] = None
    time_zone: Optional[str] = None
    is_valid: Optional[bool] = None  # False if refresh token failed


class GoogleCalendarItem(BaseModel):
    """Calendar item from Google Calendar list"""
    id: str
    summary: str
    primary: bool = False


class GoogleCalendarListResponse(BaseModel):
    """List of available calendars"""
    calendars: List[GoogleCalendarItem]


class CalendarSelectionRequest(BaseModel):
    """Request to select a calendar for bookings"""
    calendar_id: str
    time_zone: str = "UTC"


# =====================================================
# AVAILABILITY SLOTS
# =====================================================

class AvailabilitySlotCreate(BaseModel):
    """Create an availability slot - a specific session start time for a day of week"""
    day_of_week: int = Field(..., ge=0, le=6, description="0=Sunday, 6=Saturday")
    session_start: time = Field(..., description="Session beginning time. End time is computed as +1 hour.")


class AvailabilitySlotsBulkCreate(BaseModel):
    """Create multiple availability slots at once"""
    slots: List[AvailabilitySlotCreate]

    @validator('slots')
    def unique_slots(cls, v):
        seen = set()
        for slot in v:
            key = (slot.day_of_week, slot.session_start)
            if key in seen:
                raise ValueError('Each day_of_week + session_start combination can only appear once')
            seen.add(key)
        return v


class AvailabilitySlotIdentifier(BaseModel):
    """Identify a specific slot by day and start time"""
    day_of_week: int = Field(..., ge=0, le=6, description="0=Sunday, 6=Saturday")
    session_start: time = Field(..., description="Session beginning time")


class AvailabilitySlotsBulkDelete(BaseModel):
    """Delete specific availability slots"""
    slots: List[AvailabilitySlotIdentifier]


class AvailabilitySlotResponse(BaseModel):
    """Availability slot from database"""
    id: UUID
    vb_id: UUID
    day_of_week: int
    session_start: time
    session_end: time
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TimeSlot(BaseModel):
    """A single bookable time slot"""
    start: datetime
    end: datetime
    available: bool = True


class AvailabilityResponse(BaseModel):
    """Available booking slots for a VB"""
    vb_id: UUID
    time_zone: str
    slots: List[TimeSlot]
    date_range: Dict[str, str]  # {start_date, end_date}
