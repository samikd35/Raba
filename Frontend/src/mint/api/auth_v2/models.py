from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, EmailStr, Field


class SignupEmailRequest(BaseModel):
    email: EmailStr


class CompleteSignupRequest(BaseModel):
    token: str
    password: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    timezone: Optional[str] = "UTC"
    preferences: Optional[dict] = {}
    bio: Optional[str] = None
    website: Optional[str] = None
    location: Optional[str] = None


class DirectSignupRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    timezone: Optional[str] = "UTC"
    preferences: Optional[dict] = {}
    bio: Optional[str] = None
    website: Optional[str] = None
    location: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    timezone: Optional[str] = "UTC"
    preferences: Optional[dict] = {}
    bio: Optional[str] = None
    website: Optional[str] = None
    location: Optional[str] = None
    role: Literal["user", "admin", "super_admin"] = "user"


class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    timezone: Optional[str] = None
    preferences: Optional[dict] = None
    bio: Optional[str] = None
    website: Optional[str] = None
    location: Optional[str] = None


class UpdatePasswordRequest(BaseModel):
    new_password: str


class GoogleSignInRequest(BaseModel):
    id_token: str


class PasswordResetEmailRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    token: str
    new_password: str


# ============================================================
# WAITLIST MODELS
# ============================================================


class WaitlistJoinRequest(BaseModel):
    """Request to join the waitlist."""
    email: EmailStr
    source: Optional[str] = Field(default="website", max_length=50)
    referral_code: Optional[str] = Field(default=None, max_length=50)
    metadata: Optional[dict] = None


class WaitlistJoinResponse(BaseModel):
    """Response after joining waitlist."""
    success: bool
    message: str
    position: Optional[int] = None
    already_registered: bool = False


class WaitlistCheckResponse(BaseModel):
    """Response for checking waitlist status."""
    on_waitlist: bool
    status: Optional[str] = None
    position: Optional[int] = None


class WaitlistEntry(BaseModel):
    """Waitlist entry model."""
    id: str
    email: str
    status: str
    source: Optional[str] = None
    referral_code: Optional[str] = None
    created_at: datetime
    invited_at: Optional[datetime] = None
    converted_at: Optional[datetime] = None
    metadata: Optional[dict] = None


class WaitlistStatsResponse(BaseModel):
    """Admin stats for waitlist."""
    total_entries: int
    pending: int
    invited: int
    converted: int
    unsubscribed: int
    conversion_rate: float
    max_capacity: int = 1000


class WaitlistBatchInviteRequest(BaseModel):
    """Request to send batch invitations to waitlist users."""
    batch_size: Optional[int] = Field(
        default=None, 
        description="Number of emails to send. None = all pending entries.",
        ge=1,
        le=1000
    )


class WaitlistBatchInviteResponse(BaseModel):
    """Response after sending batch invitations."""
    sent_count: int
    failed_count: int
    failed_emails: List[str] = []
    total_pending: int = 0
    message: str
