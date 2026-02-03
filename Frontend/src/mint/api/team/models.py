from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field


class TeamBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None


class TeamCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    size: Optional[str] = None
    country: Optional[str] = None
    settings: Optional[Dict] = None


class TeamUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    size: Optional[str] = None
    country: Optional[str] = None
    settings: Optional[Dict] = None


class TeamIndResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    website: Optional[str]
    industry: Optional[str]
    size: Optional[str]
    country: Optional[str]
    settings: Optional[Dict]
    created_at: datetime


class TeamResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    description: Optional[str]
    website: Optional[str]
    industry: Optional[str]
    size: Optional[str]
    country: Optional[str]
    settings: Optional[Dict]
    created_at: datetime


class TeamMembershipResponse(BaseModel):
    id: str
    team_id: str
    user_id: str
    role: str
    is_active: bool
    joined_at: datetime


class TeamInviteRequest(BaseModel):
    emails: List[EmailStr]
    is_admin: bool = Field(False, description="member or admin")


class TeamInviteResponse(BaseModel):
    success: bool
    message: str
    invitations: List[str]  # list of invitation IDs


class TeamJoinRequest(BaseModel):
    invite_token: str


class TeamMemberResponse(BaseModel):
    id: str
    user_id: str
    name: str
    email: str
    role: str
    team_id: str
    status: str
    joined_date: Optional[str]
    permissions: Optional[Dict] = None


class TeamMembersListResponse(BaseModel):
    members: List[TeamMemberResponse]
    total: int
