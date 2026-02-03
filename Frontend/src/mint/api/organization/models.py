"""
Organization models for user signup and admin management.

This module defines Pydantic models for organization data validation
and API request/response handling.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, condecimal, validator


class OrganizationBase(BaseModel):
    """Base organization model with common fields."""

    name: str = Field(
        ..., min_length=1, max_length=200, description="Organization name"
    )
    description: Optional[str] = Field(
        None, max_length=500, description="Organization description"
    )
    is_active: bool = Field(
        True, description="Whether organization is available for selection"
    )

    @validator("name")
    def validate_name(cls, v):
        """Validate organization name."""
        if not v or not v.strip():
            raise ValueError("Organization name cannot be empty")
        return v.strip()


class OrganizationCreate(OrganizationBase):
    """Model for creating a new organization."""

    pass


class OrganizationUpdate(BaseModel):
    """Model for updating an existing organization."""

    name: Optional[str] = Field(
        None, min_length=1, max_length=200, description="Organization name"
    )
    description: Optional[str] = Field(
        None, max_length=500, description="Organization description"
    )
    is_active: Optional[bool] = Field(
        None, description="Whether organization is available for selection"
    )

    @validator("name")
    def validate_name(cls, v):
        """Validate organization name if provided."""
        if v is not None and (not v or not v.strip()):
            raise ValueError("Organization name cannot be empty")
        return v.strip() if v else v


class Organization(OrganizationBase):
    """Complete organization model with all fields."""

    id: uuid.UUID = Field(..., description="Organization unique identifier")
    created_at: datetime = Field(..., description="Organization creation timestamp")
    updated_at: datetime = Field(..., description="Organization last update timestamp")

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat(), uuid.UUID: lambda v: str(v)}


class OrganizationList(BaseModel):
    """Model for organization list responses."""

    organizations: List[Organization] = Field(..., description="List of organizations")
    total_count: int = Field(..., description="Total number of organizations")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    has_next: bool = Field(..., description="Whether there are more pages")


class OrganizationResponse(BaseModel):
    """Standard API response for organization operations."""

    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Response message")
    data: Optional[Organization] = Field(None, description="Organization data")
    error: Optional[str] = Field(None, description="Error message if operation failed")


class OrganizationListResponse(BaseModel):
    """Standard API response for organization list operations."""

    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Response message")
    data: Optional[OrganizationList] = Field(None, description="Organization list data")
    error: Optional[str] = Field(None, description="Error message if operation failed")


class ActiveOrganizationResponse(BaseModel):
    """Response model for active organizations (public endpoint)."""

    organizations: List[Organization] = Field(
        ..., description="List of active organizations"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat(), uuid.UUID: lambda v: str(v)}


class InviteUser(BaseModel):
    email: EmailStr
    is_admin: bool = Field(..., description="Whether the invite is for admin access")
    is_team_leader: bool = Field(
        False, description="Whether the invited user should be a team leader"
    )
    credit_allocated: int = Field(
        ..., description="amount of credits assigned to this tenant"
    )
    cohort_id: Optional[str] = Field(
        None, description="Optional cohort ID to assign user to upon joining"
    )
    can_skip_modules: bool = Field(
        False, description="Whether the invited user/team can skip modules"
    )

    @validator("cohort_id", pre=True)
    def validate_cohort_id(cls, v):
        """Validate cohort_id is a valid UUID or None."""
        if v is None or v == "":
            return None
        # Check if it's a valid UUID
        try:
            uuid.UUID(str(v))
            return str(v)
        except (ValueError, AttributeError):
            raise ValueError(
                f"Invalid cohort_id: '{v}'. Must be a valid UUID or null."
            )


class InviteUsersRequest(BaseModel):
    """Request body for inviting users to join an organization"""

    invites: List[InviteUser]


class JoinOrganizationRequest(BaseModel):
    """Request body for joining an organization"""

    invite_token: str = Field(..., description="invitation token")


class InvitationMetrics(BaseModel):
    sent: int
    accepted: int
    pending_individual: Optional[int] = None  # Pending individual member invitations
    pending_team_leader: Optional[int] = None  # Pending team leader invitations


class MembershipMetrics(BaseModel):
    total: int
    team_members: int
    individual_members: int


class CreditsSummary(BaseModel):
    total: Union[int, float]
    used: int
    remaining: Union[int, float]
    monthly_limit: Optional[int] = None


class OrgMetricsResponse(BaseModel):
    invitations: InvitationMetrics
    membership: MembershipMetrics
    credits: CreditsSummary


class OrganizationCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    country: str = Field(..., description="country of organization")
    city: str = Field(..., description="city of organization")
    contact_email: EmailStr = Field(..., description="email for the organization")
    phone_number: str = Field(..., description="phone number for the organization")
    description: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    size: Optional[str] = Field(
        None,
        description="Organization size",
        pattern="^(startup|small|medium|large|enterprise)$"
    )
    settings: Optional[Dict] = None
    invite_token: str = Field(..., description="invitation token")


class OrganizationCreateResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    website: Optional[str]
    industry: Optional[str]
    size: Optional[str]
    country: Optional[str]
    settings: Optional[Dict]
    created_by: str
    created_at: datetime


class OrganizationUpdateRequest(BaseModel):
    """Request body for updating organization details"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    size: Optional[str] = Field(
        None,
        description="Organization size",
        pattern="^(startup|small|medium|large|enterprise)$"
    )
    country: Optional[str] = None
    city: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    phone_number: Optional[str] = None


class AppInvitationCreateRequest(BaseModel):
    email: EmailStr
    credit: Optional[int] = None
    organization_type: Optional[str] = Field(
        default="grant_org",
        description="Organization type: 'grant_org', 'prepay_org', or 'postpay_org'",
        pattern="^(grant_org|prepay_org|postpay_org)$"
    )


class AppInvitationResponse(BaseModel):
    id: str
    email: EmailStr
    status: str
    type: str
    created_at: datetime
    invite_url: Optional[str] = None


class AllocateCreditsBody(BaseModel):
    user_tenant_id: UUID
    amount: condecimal(gt=0)  # Decimal
    source: str = Field(default="grant")
    valid_from: Optional[str] = None  # ISO timestamp; defaults to now()
    expires_at: Optional[str] = None  # ISO timestamp
    metadata: Optional[Dict[str, Any]] = None


# Super Admin Models
class SuperAdminOrganization(BaseModel):
    """Organization model with additional details for Super Admin dashboard."""
    
    id: str = Field(..., description="Organization unique identifier")
    name: str = Field(..., description="Organization name")
    description: Optional[str] = Field(None, description="Organization description")
    industry: Optional[str] = Field(None, description="Organization industry")
    country: Optional[str] = Field(None, description="Organization country")
    city: Optional[str] = Field(None, description="Organization city")
    contact_email: Optional[str] = Field(None, description="Organization contact email")
    phone_number: Optional[str] = Field(None, description="Organization phone number")
    website: Optional[str] = Field(None, description="Organization website")
    size: Optional[str] = Field(None, description="Organization size")
    is_active: bool = Field(..., description="Whether organization is active")
    created_at: datetime = Field(..., description="Organization creation timestamp")
    updated_at: datetime = Field(..., description="Organization last update timestamp")
    
    # Additional metrics for Super Admin
    total_members: int = Field(0, description="Total number of members")
    total_teams: int = Field(0, description="Total number of teams")
    total_credits: int = Field(0, description="Total available credits")
    used_credits: int = Field(0, description="Total used credits")
    last_activity: Optional[datetime] = Field(None, description="Last activity timestamp")
    
    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class SuperAdminOrganizationListResponse(BaseModel):
    """Response model for Super Admin organization listing."""
    
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Response message")
    data: List[SuperAdminOrganization] = Field(..., description="List of organizations")
    total: int = Field(..., description="Total number of organizations")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    has_next: bool = Field(..., description="Whether there are more pages")


class SuperAdminOrganizationSummary(BaseModel):
    """Summary statistics for Super Admin dashboard."""
    
    total_organizations: int = Field(..., description="Total number of organizations")
    active_organizations: int = Field(..., description="Number of active organizations")
    inactive_organizations: int = Field(..., description="Number of inactive organizations")
    total_members: int = Field(..., description="Total members across all organizations")
    total_teams: int = Field(..., description="Total teams across all organizations")
    total_credits_allocated: int = Field(..., description="Total credits allocated to organizations")
    total_credits_used: int = Field(..., description="Total credits used by organizations")
    organizations_by_industry: Dict[str, int] = Field(..., description="Organizations grouped by industry")
    organizations_by_size: Dict[str, int] = Field(..., description="Organizations grouped by size")
    organizations_by_country: Dict[str, int] = Field(..., description="Organizations grouped by country")


class SuperAdminOrganizationSummaryResponse(BaseModel):
    """Response model for Super Admin organization summary."""
    
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Response message")
    data: SuperAdminOrganizationSummary = Field(..., description="Organization summary data")


# ============================================================================
# Member Projects Access Models
# ============================================================================

class MemberProjectSummary(BaseModel):
    """Summary information for a single project."""
    
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


class TenantInfo(BaseModel):
    """Information about a tenant (individual or team)."""
    
    tenant_id: str = Field(..., description="Tenant unique identifier")
    tenant_type: str = Field(..., description="Tenant type: individual or team")
    tenant_name: str = Field(..., description="Tenant display name")
    
    # Consistency fields (populated for both individuals and teams)
    user_id: Optional[str] = Field(None, description="User ID (individuals) or Tenant ID (teams)")
    user_email: Optional[str] = Field(None, description="User email (individuals) or first admin email (teams)")
    user_name: Optional[str] = Field(None, description="User name (individuals) or team name (teams)")
    
    # Team-specific fields (only for teams, preserved for detailed team info)
    team_id: Optional[str] = Field(None, description="Team ID (for teams)")
    team_name: Optional[str] = Field(None, description="Team name (for teams)")
    team_contact_email: Optional[str] = Field(None, description="Team contact email (for teams)")
    team_admin_emails: Optional[List[str]] = Field(None, description="List of team admin emails (for teams)")
    
    class Config:
        from_attributes = True


class MemberWithProjects(BaseModel):
    """Member information with their project summaries."""
    
    # Consistency fields (populated for both individuals and teams)
    user_id: Optional[str] = Field(None, description="User ID (individuals) or Tenant ID (teams)")
    user_email: Optional[str] = Field(None, description="User email (individuals) or first admin email (teams)")
    user_name: Optional[str] = Field(None, description="User name (individuals) or team name (teams)")
    
    # Team-specific fields (only for teams, preserved for detailed team info)
    team_name: Optional[str] = Field(None, description="Team name (for teams)")
    team_contact_email: Optional[str] = Field(None, description="Team contact email (for teams)")
    team_admin_emails: Optional[List[str]] = Field(None, description="List of team admin emails (for teams)")
    
    # Common fields
    member_type: str = Field(..., description="Member type: individual or team")
    tenant_id: str = Field(..., description="Organization-specific tenant ID")
    project_count: int = Field(0, description="Total number of projects")
    pv_report_count: int = Field(0, description="Total number of PV reports generated")
    projects: List[MemberProjectSummary] = Field(default_factory=list, description="List of projects")
    
    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class MemberProjectsListResponse(BaseModel):
    """Response for listing all organization members with their projects."""
    
    members: List[MemberWithProjects] = Field(..., description="List of members with projects")
    total_count: int = Field(..., description="Total number of members")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    has_next: bool = Field(..., description="Whether there are more pages")


class TenantProjectsResponse(BaseModel):
    """Response for listing projects of a specific tenant."""
    
    member: TenantInfo = Field(..., description="Tenant information")
    projects: List[MemberProjectSummary] = Field(..., description="List of projects")
    total_count: int = Field(..., description="Total number of projects")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    has_next: bool = Field(..., description="Whether there are more pages")


class ProjectDataSnapshot(BaseModel):
    """Complete project data up to the current progress step."""
    
    personas: Optional[List[Dict[str, Any]]] = Field(None, description="Target personas")
    customer_profile: Optional[Dict[str, Any]] = Field(None, description="Customer Profile v1")
    hypothesis: Optional[Dict[str, Any]] = Field(None, description="Market hypothesis")
    assumptions: Optional[List[Dict[str, Any]]] = Field(None, description="Testable assumptions")
    questionnaires: Optional[List[Dict[str, Any]]] = Field(None, description="Field research questionnaires")
    research_documents: Optional[List[Dict[str, Any]]] = Field(None, description="Uploaded research documents")
    customer_profile_v2: Optional[Dict[str, Any]] = Field(None, description="Customer Profile v2 (refined)")
    value_map: Optional[Dict[str, Any]] = Field(None, description="Value Map")
    market_analysis_report: Optional[Dict[str, Any]] = Field(None, description="Market analysis report")
    vps_v1: Optional[Dict[str, Any]] = Field(None, description="Value Proposition Statement v1")
    bmc_v1: Optional[Dict[str, Any]] = Field(None, description="Business Model Canvas v1")
    solution_critique: Optional[Dict[str, Any]] = Field(None, description="Solution critique")
    vps_v2: Optional[Dict[str, Any]] = Field(None, description="Value Proposition Statement v2")
    bmc_v2: Optional[Dict[str, Any]] = Field(None, description="Business Model Canvas v2")
    
    class Config:
        from_attributes = True


class ProjectOwnerInfo(BaseModel):
    """Information about the project owner."""
    
    user_id: Optional[str] = Field(None, description="User ID (for individuals)")
    user_email: Optional[str] = Field(None, description="User email")
    user_name: Optional[str] = Field(None, description="User name")
    member_type: str = Field(..., description="Member type: individual or team")
    tenant_id: str = Field(..., description="Organization-specific tenant ID")


class PVReportInfo(BaseModel):
    """Basic PV Report information."""
    
    id: str = Field(..., description="PV Report ID")
    title: str = Field(..., description="PV Report title")
    content: Optional[Dict[str, Any]] = Field(None, description="PV Report content/data")


class AccessLogInfo(BaseModel):
    """Information about who accessed the project."""
    
    accessed_by: str = Field(..., description="User ID who accessed the project")
    accessed_at: datetime = Field(..., description="Access timestamp")
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class MemberProjectDetailResponse(BaseModel):
    """Detailed response for a single member project."""
    
    project: Dict[str, Any] = Field(..., description="Complete project information with data")
    owner: ProjectOwnerInfo = Field(..., description="Project owner information")
    pv_report: Optional[PVReportInfo] = Field(None, description="Linked PV Report information")
    access_log: AccessLogInfo = Field(..., description="Access audit information")
    
    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat()}


# ============================================================================
# Organization Owner Chat with Member Project Models
# ============================================================================

class OrgChatThreadStatus(str):
    """Thread status enum matching the chat module."""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class OrgChatCreateThreadRequest(BaseModel):
    """Request to create a chat thread for a member project."""
    
    title: Optional[str] = Field(None, max_length=200, description="Optional thread title")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata")


class OrgChatPostMessageRequest(BaseModel):
    """Request to post a message to a chat thread."""
    
    content: str = Field(..., min_length=1, max_length=10000, description="Message content")


class OrgChatThreadResponse(BaseModel):
    """Response for a chat thread."""
    
    id: str = Field(..., description="Thread unique identifier")
    project_id: str = Field(..., description="VMP project ID")
    title: Optional[str] = Field(None, description="Thread title")
    status: str = Field(..., description="Thread status")
    created_at: datetime = Field(..., description="Thread creation timestamp")
    updated_at: datetime = Field(..., description="Thread last update timestamp")
    last_message_at: Optional[datetime] = Field(None, description="Last message timestamp")
    message_count: Optional[int] = Field(None, description="Total message count")
    org_owner_access: bool = Field(True, description="Indicates org owner chat access")
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class OrgChatThreadListResponse(BaseModel):
    """Response for listing chat threads."""
    
    threads: List[OrgChatThreadResponse] = Field(..., description="List of threads")
    total_count: int = Field(..., description="Total number of threads")
    has_more: bool = Field(..., description="Whether there are more threads")


class OrgChatCitation(BaseModel):
    """Citation reference in a message."""
    
    id: str = Field(..., description="Citation ID (e.g., P1, W1)")
    source_type: str = Field(..., description="Source type: project or web")
    title: Optional[str] = Field(None, description="Source title")
    content_preview: Optional[str] = Field(None, description="Content preview")
    url: Optional[str] = Field(None, description="URL for web sources")
    
    class Config:
        from_attributes = True


class OrgChatMessageResponse(BaseModel):
    """Response for a single message."""
    
    id: str = Field(..., description="Message unique identifier")
    thread_id: str = Field(..., description="Thread ID")
    role: str = Field(..., description="Message role: user or assistant")
    content: str = Field(..., description="Message content")
    citations: List[OrgChatCitation] = Field(default_factory=list, description="Citations")
    created_at: datetime = Field(..., description="Message creation timestamp")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Message metadata")
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class OrgChatAssistantResponse(BaseModel):
    """Response after posting a message, includes both user and assistant messages."""
    
    user_message: OrgChatMessageResponse = Field(..., description="User's message")
    assistant_message: OrgChatMessageResponse = Field(..., description="Assistant's response")
    thread_id: str = Field(..., description="Thread ID")
    citations: List[OrgChatCitation] = Field(default_factory=list, description="All citations")
    follow_ups: List[str] = Field(default_factory=list, description="Suggested follow-up questions")


class OrgChatMessageListResponse(BaseModel):
    """Response for listing messages."""
    
    messages: List[OrgChatMessageResponse] = Field(..., description="List of messages")
    has_more: bool = Field(..., description="Whether there are more messages")
    next_cursor: Optional[str] = Field(None, description="Cursor for next page")


# =============================================================================
# CREDIT REQUEST MODELS
# =============================================================================

class CreditRequestStatus(str):
    """Credit request status values."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    FULFILLED = "fulfilled"


class CreditRequestCreate(BaseModel):
    """Request body for creating a credit request (generic - used internally)."""
    
    organization_id: str = Field(..., description="Organization ID")
    team_id: Optional[str] = Field(None, description="Team ID (for team members)")
    requested_amount: int = Field(..., gt=0, description="Amount of credits requested")
    reason: Optional[str] = Field(None, max_length=1000, description="Reason for requesting credits")


class TeamMemberCreditRequestCreate(BaseModel):
    """Request body for team member credit request."""
    
    team_id: str = Field(..., description="Team ID")
    requested_amount: int = Field(..., gt=0, description="Amount of credits requested")
    reason: Optional[str] = Field(None, max_length=1000, description="Reason for requesting credits")


class IndividualMemberCreditRequestCreate(BaseModel):
    """Request body for individual member credit request."""
    
    requested_amount: int = Field(..., gt=0, description="Amount of credits requested")
    reason: Optional[str] = Field(None, max_length=1000, description="Reason for requesting credits")


class CreditRequestUpdate(BaseModel):
    """Request body for updating a credit request (approve/reject)."""
    
    status: str = Field(..., description="New status: approved, rejected")
    review_notes: Optional[str] = Field(None, max_length=500, description="Notes from reviewer")


class CreditRequestResponse(BaseModel):
    """Response model for a credit request."""
    
    id: str = Field(..., description="Credit request ID")
    user_id: str = Field(..., description="Requester user ID")
    user_name: Optional[str] = Field(None, description="Requester name")
    user_email: Optional[str] = Field(None, description="Requester email")
    organization_id: str = Field(..., description="Organization ID")
    team_id: Optional[str] = Field(None, description="Team ID if team member")
    team_name: Optional[str] = Field(None, description="Team name if team member")
    requested_amount: int = Field(..., description="Amount of credits requested")
    reason: Optional[str] = Field(None, description="Reason for request")
    status: str = Field(..., description="Request status")
    reviewed_by: Optional[str] = Field(None, description="Reviewer user ID")
    reviewed_at: Optional[datetime] = Field(None, description="Review timestamp")
    review_notes: Optional[str] = Field(None, description="Review notes")
    created_at: datetime = Field(..., description="Request creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


class CreditRequestListResponse(BaseModel):
    """Response for listing credit requests."""
    
    requests: List[CreditRequestResponse] = Field(..., description="List of credit requests")
    total_count: int = Field(..., description="Total number of requests")
    pending_count: int = Field(0, description="Number of pending requests")


class UserCreditRequestStatus(BaseModel):
    """Credit request status for a user (used in member list responses)."""
    
    has_pending_request: bool = Field(False, description="Whether user has a pending request")
    pending_request_id: Optional[str] = Field(None, description="Pending request ID")
    pending_request_amount: Optional[int] = Field(None, description="Pending request amount")
    pending_request_date: Optional[datetime] = Field(None, description="Pending request date")
    last_request_status: Optional[str] = Field(None, description="Status of most recent request")
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


class OrgAdminCreditRequestCreate(BaseModel):
    """Request body for org admin to request credits from Yuba (grant orgs only)."""
    
    requested_amount: int = Field(..., gt=0, description="Amount of credits requested")
    reason: str = Field(..., min_length=10, max_length=2000, description="Reason for requesting credits")
    urgency: Optional[str] = Field("normal", description="Urgency level: normal, high, urgent")


class OrgAdminCreditRequestResponse(BaseModel):
    """Response for org admin credit request."""
    
    success: bool = Field(..., description="Whether request was submitted successfully")
    message: str = Field(..., description="Response message")
    request_reference: Optional[str] = Field(None, description="Reference ID for tracking")

