"""
Pydantic models for report sharing functionality.

These models handle:
- Creating share links
- Managing share settings
- Accessing shared reports
- Tracking share analytics
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator


# =============================================
# REQUEST MODELS
# =============================================

class CreateShareRequest(BaseModel):
    """Request model for creating a share link"""
    session_id: str = Field(..., description="Workflow session ID")
    
    # Access control
    access_type: str = Field(default="view", description="Access type: view or download")
    password: Optional[str] = Field(None, description="Optional password protection")
    is_public: bool = Field(default=True, description="If true, anyone with link can access")
    allowed_emails: Optional[List[str]] = Field(None, description="Whitelist of allowed email addresses")
    
    # Limits
    max_views: Optional[int] = Field(None, ge=1, description="Maximum number of views allowed")
    expires_in_days: Optional[int] = Field(None, ge=1, le=365, description="Expiration in days from now")
    
    # Content control
    share_message: Optional[str] = Field(None, max_length=500, description="Message to share recipients")
    
    @validator('access_type')
    def validate_access_type(cls, v):
        if v not in ['view', 'download']:
            raise ValueError("access_type must be 'view' or 'download'")
        return v
    
    @validator('allowed_emails')
    def validate_emails(cls, v):
        if v is not None:
            if len(v) == 0:
                return None
            # Filter out placeholder values like "string"
            valid_emails = [email for email in v if email and email != "string" and "@" in email]
            if len(valid_emails) == 0:
                return None
            return valid_emails
        return v


class UpdateShareRequest(BaseModel):
    """Request model for updating share settings"""
    is_active: Optional[bool] = Field(None, description="Enable/disable the share")
    access_type: Optional[str] = Field(None, description="Update access type")
    password: Optional[str] = Field(None, description="Update password (empty string to remove)")
    allowed_emails: Optional[List[str]] = Field(None, description="Update email whitelist")
    max_views: Optional[int] = Field(None, ge=1, description="Update max views")
    expires_in_days: Optional[int] = Field(None, ge=1, le=365, description="Extend expiration")
    share_message: Optional[str] = Field(None, max_length=500, description="Update share message")
    
    @validator('access_type')
    def validate_access_type(cls, v):
        if v is not None and v not in ['view', 'download']:
            raise ValueError("access_type must be 'view' or 'download'")
        return v


class AccessShareRequest(BaseModel):
    """Request model for accessing a shared report"""
    share_token: str = Field(..., description="Share token from URL")
    password: Optional[str] = Field(None, description="Password if required")
    accessor_email: Optional[str] = Field(None, description="Email of accessor (optional)")


class RevokeShareRequest(BaseModel):
    """Request model for revoking a share"""
    share_id: UUID = Field(..., description="ID of share to revoke")


# =============================================
# RESPONSE MODELS
# =============================================

class ShareInfo(BaseModel):
    """Share information model"""
    id: UUID = Field(..., description="Share ID")
    share_token: str = Field(..., description="Unique share token")
    share_url: str = Field(..., description="Full shareable URL")
    
    # Report info
    session_id: UUID = Field(..., description="Workflow session ID")
    report_id: UUID = Field(..., description="Problem validation report ID")
    report_title: str = Field(..., description="Report title")
    
    # Access settings
    access_type: str = Field(..., description="Access type")
    is_public: bool = Field(..., description="Public access flag")
    has_password: bool = Field(..., description="Whether password is set")
    allowed_emails: Optional[List[str]] = Field(None, description="Email whitelist")
    
    # Limits and usage
    max_views: Optional[int] = Field(None, description="Maximum views allowed")
    view_count: int = Field(..., description="Current view count")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")
    
    # Status
    is_active: bool = Field(..., description="Active status")
    is_expired: bool = Field(..., description="Whether share has expired")
    is_view_limit_reached: bool = Field(..., description="Whether view limit reached")
    
    # Metadata
    share_message: Optional[str] = Field(None, description="Share message")
    
    # Timestamps
    created_at: datetime = Field(..., description="Creation timestamp")
    last_accessed_at: Optional[datetime] = Field(None, description="Last access timestamp")
    revoked_at: Optional[datetime] = Field(None, description="Revocation timestamp")
    
    class Config:
        from_attributes = True


class ShareListResponse(BaseModel):
    """Response model for listing shares"""
    success: bool = Field(..., description="Operation success")
    message: str = Field(..., description="Response message")
    shares: List[ShareInfo] = Field(..., description="List of shares")
    total: int = Field(..., description="Total count")


class CreateShareResponse(BaseModel):
    """Response model for creating a share"""
    success: bool = Field(..., description="Operation success")
    message: str = Field(..., description="Response message")
    share: ShareInfo = Field(..., description="Created share info")


class UpdateShareResponse(BaseModel):
    """Response model for updating a share"""
    success: bool = Field(..., description="Operation success")
    message: str = Field(..., description="Response message")
    share: ShareInfo = Field(..., description="Updated share info")


class RevokeShareResponse(BaseModel):
    """Response model for revoking a share"""
    success: bool = Field(..., description="Operation success")
    message: str = Field(..., description="Response message")


class SharedReportContent(BaseModel):
    """Shared report content model"""
    # Report metadata
    title: str = Field(..., description="Report title")
    
    # PV Report sections (only fields that actually have content, in order)
    executive_summary: Optional[str] = Field(None, description="Executive summary")
    industry_analysis: Optional[str] = Field(None, description="Industry analysis")
    challenges_analysis: Optional[str] = Field(None, description="Challenges analysis")
    recommendations: Optional[str] = Field(None, description="Recommendations")
    sources: Optional[List[Dict[str, Any]]] = Field(None, description="Report sources")
    
    # Metadata
    report_type: str = Field(..., description="Report type")
    
    # Share metadata
    share_message: Optional[str] = Field(None, description="Message from sharer")
    shared_by: str = Field(..., description="Name/email of sharer")
    shared_at: datetime = Field(..., description="When it was shared")


class AccessShareResponse(BaseModel):
    """Response model for accessing a shared report"""
    success: bool = Field(..., description="Operation success")
    message: str = Field(..., description="Response message")
    report: Optional[SharedReportContent] = Field(None, description="Report content")
    access_type: str = Field(..., description="Access type granted")
    can_download: bool = Field(..., description="Whether download is allowed")


class ShareAnalytics(BaseModel):
    """Share analytics model"""
    share_id: UUID = Field(..., description="Share ID")
    total_views: int = Field(..., description="Total views")
    unique_accessors: int = Field(..., description="Unique accessor count")
    last_accessed_at: Optional[datetime] = Field(None, description="Last access time")
    
    # Access breakdown
    access_by_date: List[Dict[str, Any]] = Field(..., description="Access counts by date")
    access_by_email: List[Dict[str, Any]] = Field(..., description="Access counts by email")
    
    # Geographic data (if available)
    access_by_location: Optional[List[Dict[str, Any]]] = Field(None, description="Access by location")


class ShareAnalyticsResponse(BaseModel):
    """Response model for share analytics"""
    success: bool = Field(..., description="Operation success")
    message: str = Field(..., description="Response message")
    analytics: ShareAnalytics = Field(..., description="Share analytics")


# =============================================
# ACCESS LOG MODELS
# =============================================

class AccessLogEntry(BaseModel):
    """Access log entry model"""
    id: UUID = Field(..., description="Log entry ID")
    accessed_at: datetime = Field(..., description="Access timestamp")
    accessor_email: Optional[str] = Field(None, description="Accessor email")
    accessor_ip: Optional[str] = Field(None, description="Accessor IP")
    access_granted: bool = Field(..., description="Whether access was granted")
    access_denied_reason: Optional[str] = Field(None, description="Denial reason")
    sections_viewed: Optional[List[str]] = Field(None, description="Sections viewed")
    download_attempted: bool = Field(..., description="Download attempt flag")
    
    class Config:
        from_attributes = True


class AccessLogsResponse(BaseModel):
    """Response model for access logs"""
    success: bool = Field(..., description="Operation success")
    message: str = Field(..., description="Response message")
    logs: List[AccessLogEntry] = Field(..., description="Access log entries")
    total: int = Field(..., description="Total count")
