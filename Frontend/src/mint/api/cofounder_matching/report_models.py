from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class ReportReason(str, Enum):
    """Reasons for reporting a profile or message."""
    SPAM_OR_SCAM = "SPAM_OR_SCAM"
    HARASSMENT_OR_HATE = "HARASSMENT_OR_HATE"
    MISREPRESENTATION = "MISREPRESENTATION"
    OFF_PLATFORM_SOLICITATION = "OFF_PLATFORM_SOLICITATION"
    ADULT_CONTENT = "ADULT_CONTENT"
    DUPLICATE_ACCOUNT = "DUPLICATE_ACCOUNT"
    UNDERAGE_OR_NOT_FOUNDER = "UNDERAGE_OR_NOT_FOUNDER"
    OTHER = "OTHER"


class ReportStatus(str, Enum):
    """Status of a report."""
    PENDING = "PENDING"
    REVIEWED = "REVIEWED"
    ACTIONED = "ACTIONED"
    NO_ACTION = "NO_ACTION"


class ReportType(str, Enum):
    """Type of entity being reported."""
    PROFILE = "PROFILE"
    MESSAGE = "MESSAGE"


# ============================================================
# Request Models
# ============================================================


class CreateProfileReportRequest(BaseModel):
    """Request to report a profile."""
    reported_profile_id: str = Field(..., description="ID of the profile being reported")
    reason: ReportReason = Field(..., description="Reason for reporting")
    description: Optional[str] = Field(None, description="Optional additional context (required if reason is OTHER)")

    class Config:
        use_enum_values = True


class CreateMessageReportRequest(BaseModel):
    """Request to report a message."""
    message_id: str = Field(..., description="ID of the message being reported")
    reason: ReportReason = Field(..., description="Reason for reporting")
    description: Optional[str] = Field(None, description="Optional additional context (required if reason is OTHER)")

    class Config:
        use_enum_values = True


class ResolveReportRequest(BaseModel):
    """Request to resolve a report (admin only)."""
    status: ReportStatus = Field(..., description="New status for the report")
    admin_notes: Optional[str] = Field(None, description="Admin notes on resolution")
    action_taken: Optional[str] = Field(None, description="Description of action taken (if any)")

    class Config:
        use_enum_values = True


# ============================================================
# Response Models
# ============================================================


class ReportResponse(BaseModel):
    """Response for a single report."""
    id: str
    report_type: ReportType
    reporter_user_id: str
    reported_profile_id: Optional[str] = None
    reported_message_id: Optional[str] = None
    reason: ReportReason
    description: Optional[str] = None
    status: ReportStatus
    admin_notes: Optional[str] = None
    action_taken: Optional[str] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        use_enum_values = True


class CreateReportResponse(BaseModel):
    """Response after creating a report."""
    success: bool
    message: str
    data: ReportResponse


class ListReportsResponse(BaseModel):
    """Response for listing reports."""
    success: bool
    message: str
    data: List[ReportResponse]
    total: int
    page: int
    page_size: int


class ResolveReportResponse(BaseModel):
    """Response after resolving a report."""
    success: bool
    message: str
    data: ReportResponse


class ReportStatsResponse(BaseModel):
    """Statistics about reports."""
    total_reports: int
    pending_reports: int
    reviewed_reports: int
    actioned_reports: int
    no_action_reports: int
    reports_by_reason: dict
