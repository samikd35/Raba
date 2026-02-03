from datetime import datetime
from enum import Enum
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, conint, validator

Commitment = Literal["Full-time", "Part-time"]
Importance = Literal["must_have", "nice_to_have"]


class EmploymentItem(BaseModel):
    organization: str
    role_title: str
    start_date: str  # 'YYYY-MM'
    end_date: str  # 'YYYY-MM' or 'Present'
    responsibilities_description: str


class LanguageImportance(str, Enum):
    must_have = "must_have"
    nice_to_have = "nice_to_have"


class LanguagePref(BaseModel):
    language_id: str = Field(
        ..., description="Language ID from the languages enum table"
    )
    importance: LanguageImportance


class DraftProfileIn(BaseModel):
    # identity
    first_name: str
    last_name: str
    gender: str
    date_of_birth: str
    email: str
    profile_picture_url: Optional[str] = None  # This will be the URL after upload
    country: str
    linkedin_url: str
    website_url: Optional[str] = None
    education: List[str]
    employment_history: List[EmploymentItem]
    achievement: str
    personal_statement: str
    social_links: Dict[str, Optional[str]]

    # matching dimensions
    professional_background: str
    industries_of_interest: List[str]
    responsibilities_offered: List[str]
    skills_needed: List[str]

    preferred_languages: List[LanguagePref]

    preferred_country: str
    preferred_country_importance: Importance

    expected_commitment: Commitment
    preferred_commitment: Commitment
    commitment_importance: Importance

    venture_stage: List[str]
    preferred_venture_stage: List[str]

    age_enabled: bool
    age_min: Optional[conint(ge=20, le=50)]
    age_max: Optional[conint(ge=20, le=50)]
    age_importance: Optional[Importance]

    # "Other" custom values
    other_industries: Optional[List[str]] = Field(default_factory=list, description="Custom industry values when 'Other' is selected")
    other_responsibilities: Optional[List[str]] = Field(default_factory=list, description="Custom responsibility values when 'Other' is selected")
    other_venture_stages: Optional[List[str]] = Field(default_factory=list, description="Custom venture stage values for venture_stage field")
    other_preferred_venture_stages: Optional[List[str]] = Field(default_factory=list, description="Custom venture stage values for preferred_venture_stage field")
    other_languages: Optional[List[str]] = Field(default_factory=list, description="Custom language values when 'Other' is selected")
    other_expected_commitment: Optional[str] = Field(None, description="Custom commitment value for expected_commitment when 'Other' is selected")
    other_preferred_commitment: Optional[str] = Field(None, description="Custom commitment value for preferred_commitment when 'Other' is selected")


# ---------- Shared base ----------
class EnumItemBase(BaseModel):
    name: str = Field(..., description="Display name")
    description: Optional[str] = Field(None, description="Optional description")
    is_active: bool = Field(True, description="Active/Visible")


class EnumItemCreate(EnumItemBase):
    pass


class EnumItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class EnumItem(EnumItemBase):
    id: str
    slug: str
    created_at: datetime
    updated_at: datetime


# ---------- Responses ----------
class EnumItemResponse(BaseModel):
    success: bool
    message: str
    data: Optional[EnumItem]


class EnumItemListResponse(BaseModel):
    success: bool
    message: str
    data: List[EnumItem]
    total: int
    page: int
    page_size: int


# Typed aliases as real subclasses (distinct names for OpenAPI)


class IndustryCreate(EnumItemCreate):
    """Payload when creating an industry."""

    pass


class IndustryUpdate(EnumItemUpdate):
    """Payload when updating an industry."""

    pass


class Industry(EnumItem):
    """Industry model returned by the API."""

    pass


class ResponsibilityCreate(EnumItemCreate):
    """Payload when creating a responsibility."""

    pass


class ResponsibilityUpdate(EnumItemUpdate):
    """Payload when updating a responsibility."""

    pass


class Responsibility(EnumItem):
    """Responsibility model returned by the API."""

    pass


class CommitmentCreate(EnumItemCreate):
    """Payload when creating a commitment."""

    pass


class CommitmentUpdate(EnumItemUpdate):
    """Payload when updating a commitment."""

    pass


class Commitment(EnumItem):
    """Commitment model returned by the API."""

    pass


class VentureStageCreate(EnumItemCreate):
    """Payload when creating a venture stage."""

    pass


class VentureStageUpdate(EnumItemUpdate):
    """Payload when updating a venture stage."""

    pass


class VentureStage(EnumItem):
    """Venture stage model returned by the API."""

    pass


class LanguageCreate(EnumItemCreate):
    """Payload when creating a language."""

    pass


class LanguageUpdate(EnumItemUpdate):
    """Payload when updating a language."""

    pass


class Language(EnumItem):
    """Language model returned by the API."""

    pass


# -------- Request --------
class DirectoryFilters(BaseModel):
    # Countries: lowercase names, can be one or many
    countries: Optional[List[str]] = None

    # Languages: multiple language IDs (UUIDs from profile_languages table)
    languages: Optional[List[str]] = None

    # Age range (inclusive)
    age_min: Optional[int] = Field(None, ge=0, le=120)
    age_max: Optional[int] = Field(None, ge=0, le=120)

    # Commitment and venture stage
    preferred_commitment: Optional[str] = None
    preferred_venture_stage: Optional[List[str]] = None

    # Pagination
    page: int = Field(1, ge=1)
    limit: int = Field(20, ge=1, le=1000)


# -------- Response --------
class DirectoryUser(BaseModel):
    user_id: str
    profile_id: str
    version_id: str
    full_name: Optional[str] = None
    country: Optional[str] = None
    date_of_birth: Optional[str] = None
    profile_picture_url: Optional[str] = None
    professional_background: Optional[str] = None
    can_message: bool = Field(default=False, description="Whether the current user can message this profile right now")


class DirectorySearchResponse(BaseModel):
    total: int
    items: List[DirectoryUser]
    limit: int
    offset: int
    page: int
    total_pages: int


# -------- Matching Threshold Models --------
class MatchingThresholdCreate(BaseModel):
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Unique name for the threshold configuration",
    )
    description: Optional[str] = Field(
        None, description="Description of this threshold configuration"
    )
    threshold_score: float = Field(
        ...,
        ge=0,
        le=100,
        description="Minimum match score (0-100) required to create a match",
    )
    is_active: bool = Field(
        False, description="Whether this threshold is currently active"
    )


class MatchingThresholdUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    threshold_score: Optional[float] = Field(None, ge=0, le=100)
    is_active: Optional[bool] = None


class MatchingThreshold(BaseModel):
    id: str
    name: str
    description: Optional[str]
    threshold_score: float
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]
    updated_by: Optional[str]
    metadata: Optional[dict]


# -------- User Match Models --------
class UserMatch(BaseModel):
    match_id: str = Field(..., description="ID from user_relationships table")
    user_id: str
    full_name: Optional[str]
    profile_picture_url: Optional[str]
    country: Optional[str]
    preferred_commitment: Optional[str]
    preferred_venture_stage: Optional[List[str]]
    preferred_languages: Optional[list]
    match_score: Optional[float]
    matched_at: Optional[datetime]
    relationship: str = Field(
        ..., description="Relationship status: 'none', 'matched', 'contacted'"
    )


class UserMatchesResponse(BaseModel):
    total: int
    matches: List[UserMatch]


# -------- Admin Profile Review Models --------
class ProfileRejectionRequest(BaseModel):
    reason: str = Field(
        ...,
        min_length=10,
        max_length=10000,
        description="Reason for rejecting the profile (minimum 10 characters)",
    )

    @validator("reason")
    def reason_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Rejection reason cannot be empty or only whitespace")
        return v.strip()


# -------- Enum Suggestions Models --------
class EnumSuggestionStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class EnumSuggestionType(str, Enum):
    industries = "industries"
    responsibilities = "responsibilities"
    venture_stages = "venture_stages"
    commitments = "commitments"
    languages = "languages"


class EnumSuggestion(BaseModel):
    id: str
    enum_type: EnumSuggestionType
    field_context: Optional[str]
    suggested_value: str
    suggested_by: Optional[str]
    profile_version_id: Optional[str]
    times_suggested: int
    status: EnumSuggestionStatus
    converted_to_enum_id: Optional[str]
    converted_to_enum_name: Optional[str]
    admin_notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    reviewed_by: Optional[str]
    reviewed_at: Optional[datetime]


class EnumSuggestionListResponse(BaseModel):
    total: int
    items: List[EnumSuggestion]


class ApproveEnumSuggestionRequest(BaseModel):
    enum_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Display name for the new enum option"
    )
    enum_description: Optional[str] = Field(
        None,
        max_length=500,
        description="Optional description for the new enum option"
    )
    admin_notes: Optional[str] = Field(
        None,
        max_length=1000,
        description="Optional admin notes about this approval"
    )


class RejectEnumSuggestionRequest(BaseModel):
    admin_notes: str = Field(
        ...,
        min_length=10,
        max_length=1000,
        description="Reason for rejecting this suggestion (minimum 10 characters)"
    )

    @validator("admin_notes")
    def notes_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Rejection reason cannot be empty or only whitespace")
        return v.strip()


class EnumSuggestionStats(BaseModel):
    enum_type: str
    status: str
    count: int
    total_suggestions: int
