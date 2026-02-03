"""
Tenant Management Models

Pydantic models for tenant management system supporting Individual, Team, and Organization types.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, validator

# Tenant Types
TenantType = Literal["individual", "team", "organization"]
TenantRole = Literal["owner", "admin", "member"]
TenantSize = Literal["startup", "small", "medium", "large", "enterprise"]

# =============================================
# CORE TENANT MODELS
# =============================================


class TenantBase(BaseModel):
    """Base tenant model with common fields"""

    name: str = Field(..., min_length=1, max_length=255, description="Tenant name")
    tenant_type: TenantType = Field(..., description="Type of tenant")
    description: Optional[str] = Field(
        None, max_length=1000, description="Tenant description"
    )
    website: Optional[str] = Field(None, description="Tenant website URL")
    industry: Optional[str] = Field(None, description="Industry sector")
    size: Optional[TenantSize] = Field(None, description="Organization size")
    country: Optional[str] = Field(None, description="Country of operation")
    city: Optional[str] = Field(None, description="City of operation")
    contact_email: Optional[str] = Field(None, description="Contact email address")
    phone_number: Optional[str] = Field(None, description="Contact phone number")
    settings: Dict[str, Any] = Field(
        default_factory=dict, description="Tenant settings"
    )


class TenantCreate(TenantBase):
    """Model for creating a new tenant"""

    pass


class TenantUpdate(BaseModel):
    """Model for updating tenant information"""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    website: Optional[str] = Field(None)
    industry: Optional[str] = Field(None)
    size: Optional[TenantSize] = Field(None)
    country: Optional[str] = Field(None)
    city: Optional[str] = Field(None)
    contact_email: Optional[str] = Field(None)
    phone_number: Optional[str] = Field(None)
    settings: Optional[Dict[str, Any]] = Field(None)


class Tenant(TenantBase):
    """Complete tenant model with system fields"""

    id: uuid.UUID = Field(..., description="Tenant ID")
    is_active: bool = Field(..., description="Whether tenant is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


# =============================================
# TENANT MEMBERSHIP MODELS
# =============================================


class TenantMembershipBase(BaseModel):
    """Base tenant membership model"""

    role: TenantRole = Field(..., description="User role in tenant")
    permissions: Dict[str, Any] = Field(
        default_factory=dict, description="User permissions"
    )


class TenantMembershipCreate(TenantMembershipBase):
    """Model for creating tenant membership"""

    user_id: uuid.UUID = Field(..., description="User ID to add to tenant")


class TenantMembershipUpdate(BaseModel):
    """Model for updating tenant membership"""

    role: Optional[TenantRole] = Field(None, description="New role")
    permissions: Optional[Dict[str, Any]] = Field(None, description="New permissions")
    is_active: Optional[bool] = Field(None, description="Active status")


class TenantMembership(TenantMembershipBase):
    """Complete tenant membership model"""

    id: uuid.UUID = Field(..., description="Membership ID")
    tenant_id: uuid.UUID = Field(..., description="Tenant ID")
    user_id: uuid.UUID = Field(..., description="User ID")
    role: Optional[str] = Field(None, description="Tenant role")
    joined_at: datetime = Field(..., description="Join timestamp")
    is_active: bool = Field(..., description="Active status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


# =============================================
# GROUP MODELS
# =============================================


class GroupBase(BaseModel):
    """Base group model"""

    name: str = Field(..., min_length=1, max_length=255, description="Group name")
    description: Optional[str] = Field(
        None, max_length=1000, description="Group description"
    )
    settings: Dict[str, Any] = Field(default_factory=dict, description="Group settings")


class GroupCreate(GroupBase):
    """Model for creating a new group"""

    pass


class GroupUpdate(BaseModel):
    """Model for updating group information"""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    settings: Optional[Dict[str, Any]] = Field(None)


class Group(GroupBase):
    """Complete group model"""

    id: uuid.UUID = Field(..., description="Group ID")
    tenant_id: uuid.UUID = Field(..., description="Parent tenant ID")
    is_active: bool = Field(..., description="Whether group is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


# =============================================
# GROUP MEMBERSHIP MODELS
# =============================================


class GroupMembershipBase(BaseModel):
    """Base group membership model"""

    role: Literal["admin", "member"] = Field(..., description="User role in group")


class GroupMembershipCreate(GroupMembershipBase):
    """Model for creating group membership"""

    user_id: uuid.UUID = Field(..., description="User ID to add to group")


class GroupMembershipUpdate(BaseModel):
    """Model for updating group membership"""

    role: Optional[Literal["admin", "member"]] = Field(None, description="New role")
    is_active: Optional[bool] = Field(None, description="Active status")


class GroupMembership(GroupMembershipBase):
    """Complete group membership model"""

    id: uuid.UUID = Field(..., description="Membership ID")
    group_id: uuid.UUID = Field(..., description="Group ID")
    user_id: uuid.UUID = Field(..., description="User ID")
    joined_at: datetime = Field(..., description="Join timestamp")
    is_active: bool = Field(..., description="Active status")
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        from_attributes = True


# =============================================
# RESPONSE MODELS
# =============================================


class TenantResponse(BaseModel):
    """Response model for tenant operations"""

    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")
    data: Optional[Tenant] = Field(None, description="Tenant data")


class TenantListResponse(BaseModel):
    """Response model for tenant list operations"""

    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")
    data: List[Tenant] = Field(..., description="List of tenants")
    total: int = Field(..., description="Total count")
    page: int = Field(..., description="Current page")
    page_size: int = Field(..., description="Page size")


class TenantMembershipResponse(BaseModel):
    """Response model for tenant membership operations"""

    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")
    data: Optional[TenantMembership] = Field(None, description="Membership data")
    is_team_leader: Optional[bool] = Field(None, description="is a team leader")


class JoinAuthPayload(BaseModel):
    access_token: str
    tenant_id: str
    tenant_type: str
    user_id: str
    email: str
    roles: List[str]
    user: Optional[dict] = None
    is_team_leader: Optional[bool] = None
    can_skip_module: Optional[bool] = None


class JoinOrganizationHTTPResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None  # Generic dict to accept service response
    auth: Optional[JoinAuthPayload] = None


class TenantMembershipListResponse(BaseModel):
    """Response model for tenant membership list operations"""

    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")
    data: List[TenantMembership] = Field(..., description="List of memberships")
    total: int = Field(..., description="Total count")
    page: int = Field(..., description="Current page")
    page_size: int = Field(..., description="Page size")


class GroupResponse(BaseModel):
    """Response model for group operations"""

    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")
    data: Optional[Group] = Field(None, description="Group data")


class GroupListResponse(BaseModel):
    """Response model for group list operations"""

    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")
    data: List[Group] = Field(..., description="List of groups")
    total: int = Field(..., description="Total count")
    page: int = Field(..., description="Current page")
    page_size: int = Field(..., description="Page size")


# =============================================
# ADMIN DASHBOARD MODELS
# =============================================


class TenantAnalytics(BaseModel):
    """Analytics data for tenant"""

    tenant_id: uuid.UUID = Field(..., description="Tenant ID")
    tenant_name: str = Field(..., description="Tenant name")
    tenant_type: TenantType = Field(..., description="Tenant type")
    member_count: int = Field(..., description="Number of members")
    active_projects: int = Field(..., description="Number of active projects")
    total_reports: int = Field(..., description="Total reports generated")
    credits_used: int = Field(..., description="Credits consumed")
    credits_remaining: int = Field(..., description="Credits remaining")
    last_activity: Optional[datetime] = Field(
        None, description="Last activity timestamp"
    )


class TenantAnalyticsResponse(BaseModel):
    """Response model for tenant analytics"""

    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")
    data: List[TenantAnalytics] = Field(..., description="Analytics data")
    total: int = Field(..., description="Total count")


# =============================================
# INVITATION MODELS
# =============================================


class TenantInvitationCreate(BaseModel):
    """Model for creating tenant invitations"""

    email: str = Field(..., description="Email to invite")
    role: TenantRole = Field(..., description="Role to assign")
    message: Optional[str] = Field(
        None, max_length=500, description="Invitation message"
    )


class TenantInvitation(BaseModel):
    """Model for tenant invitations"""

    id: uuid.UUID = Field(..., description="Invitation ID")
    tenant_id: uuid.UUID = Field(..., description="Tenant ID")
    email: str = Field(..., description="Invited email")
    role: TenantRole = Field(..., description="Assigned role")
    status: Literal["pending", "accepted", "declined", "expired"] = Field(
        ..., description="Invitation status"
    )
    message: Optional[str] = Field(None, description="Invitation message")
    expires_at: datetime = Field(..., description="Expiration timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        from_attributes = True


class TenantInvitationResponse(BaseModel):
    """Response model for tenant invitations"""

    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")
    data: Optional[TenantInvitation] = Field(None, description="Invitation data")


class TenantInvitationListResponse(BaseModel):
    """Response model for tenant invitation list"""

    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")
    data: List[TenantInvitation] = Field(..., description="List of invitations")
    total: int = Field(..., description="Total count")


class TenantDelete(BaseModel):
    member_id: str


# =============================================
# VALIDATION
# =============================================


@validator("website")
def validate_website(cls, v):
    """Validate website URL format"""
    if v and not v.startswith(("http://", "https://")):
        raise ValueError("Website must start with http:// or https://")
    return v


@validator("email")
def validate_email(cls, v):
    """Validate email format"""
    import re

    if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", v):
        raise ValueError("Invalid email format")
    return v
