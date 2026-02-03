"""
Venture Builder Interest Submission Models

Pydantic models for the VB Declaration of Interest feature.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, HttpUrl, validator


# =====================================================
# ENUMS
# =====================================================

class CoachingExperience(str, Enum):
    """Coaching/mentoring experience levels"""
    NONE = "none"
    ONE_TO_TWO_YEARS = "1-2_years"
    THREE_TO_FIVE_YEARS = "3-5_years"
    FIVE_PLUS_YEARS = "5+_years"


class WeeklyAvailability(str, Enum):
    """Estimated weekly availability options"""
    TWO_HRS = "2_hrs"
    FOUR_HRS = "4_hrs"
    SIX_HRS = "6_hrs"
    EIGHT_HRS = "8_hrs"
    TEN_HRS = "10_hrs"
    OTHER = "other"


class SupportArea(str, Enum):
    """Areas a VB can support founders on"""
    GENERALIST = "generalist"
    PRODUCT_DEVELOPMENT = "product_development"
    SOFTWARE_DEVELOPMENT = "software_development"
    HARDWARE_DEVELOPMENT = "hardware_development"
    STRATEGY = "strategy"
    MANAGEMENT_PRACTICES = "management_practices"
    LEGAL = "legal"
    EXECUTION = "execution"
    OTHER = "other"


class Industry(str, Enum):
    """Industries of focus"""
    GENERALIST = "generalist"
    FINANCIAL_SYSTEMS = "financial_systems"
    HEALTHCARE_SYSTEMS = "healthcare_systems"
    AGRICULTURE = "agriculture"
    FOOD_SYSTEMS = "food_systems"
    EDUCATION = "education"
    CLIMATE_ACTION = "climate_action"
    LOGISTICS = "logistics"
    CONSUMER_TECH = "consumer_tech"
    FMCG = "fmcg"
    CONSTRUCTION = "construction"
    TRANSPORTATION = "transportation"
    ARTIFICIAL_INTELLIGENCE = "artificial_intelligence"
    CONSERVATION = "conservation"
    LEGAL = "legal"
    TELECOMMUNICATION = "telecommunication"
    OTHER = "other"


class FounderStage(str, Enum):
    """Founder stages a VB works best with"""
    EARLY_STAGE = "early_stage"
    POST_PMF = "post_pmf"
    GROWTH = "growth"
    SCALE = "scale"
    EXIT = "exit"
    OTHER = "other"


class Geography(str, Enum):
    """Geographic specialization"""
    AFRICA_WIDE = "africa_wide"
    EAST_AFRICA = "east_africa"
    WEST_AFRICA = "west_africa"
    NORTH_AFRICA = "north_africa"
    SOUTHERN_AFRICA = "southern_africa"
    SPECIFIC_COUNTRIES = "specific_countries"


class Language(str, Enum):
    """Languages VB is comfortable with"""
    ENGLISH = "english"
    FRENCH = "french"
    SWAHILI = "swahili"
    ARABIC = "arabic"
    AMHARIC = "amharic"
    IGBO = "igbo"
    ZULU = "zulu"
    LINGALA = "lingala"
    KINYARWANDA = "kinyarwanda"
    LUGANDA = "luganda"
    PORTUGUESE = "portuguese"
    OTHER = "other"


class InterestSubmissionStatus(str, Enum):
    """Status of an interest submission"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    INVITED = "invited"


# =====================================================
# REQUEST MODELS
# =====================================================

class VBInterestSubmissionCreate(BaseModel):
    """Create a VB interest submission (public endpoint)"""
    
    # Section 1: Personal Information
    full_name: str = Field(..., min_length=2, max_length=200, description="Full name of the applicant")
    work_email: EmailStr = Field(..., description="Work email address")
    phone_country_code: str = Field(..., min_length=2, max_length=3, description="ISO country code (e.g., KE, NG, ET)")
    phone_number: str = Field(..., min_length=8, max_length=20, description="Phone number with country code")
    country: str = Field(..., max_length=100, description="Country of residence")
    city: str = Field(..., max_length=100, description="City of residence")
    
    # Section 2: Professional Profile
    primary_role: str = Field(..., max_length=200, description="Primary role/title")
    company_organization: Optional[str] = Field(None, max_length=200, description="Current company or organization")
    linkedin_url: str = Field(..., description="LinkedIn profile URL")
    personal_website: Optional[str] = Field(None, description="Personal website URL")
    
    # Section 3: Venture Building Experience
    has_founded_venture: bool = Field(..., description="Has the applicant founded or co-founded a venture?")
    ventures_founded_count: Optional[int] = Field(None, ge=1, description="Number of ventures founded (if applicable)")
    ventures_stage_reached: Optional[str] = Field(None, max_length=500, description="Highest stage reached with ventures")
    ventures_outcome: Optional[str] = Field(None, max_length=500, description="Outcome of ventures (acquired, operating, etc.)")
    coaching_experience: CoachingExperience = Field(..., description="Coaching/mentoring experience level")
    programs_worked_with: Optional[str] = Field(None, max_length=1000, description="Accelerators, incubators, ESOs worked with")
    
    # Section 4: Expertise & Coverage
    support_areas: List[SupportArea] = Field(..., min_items=1, description="Areas the VB can support founders on")
    support_areas_other: Optional[str] = Field(None, max_length=200, description="Other support areas if 'other' selected")
    industries_of_focus: List[Industry] = Field(..., min_items=1, description="Industries of focus")
    industries_other: Optional[str] = Field(None, max_length=200, description="Other industries if 'other' selected")
    founder_stages: List[FounderStage] = Field(..., min_items=1, description="Founder stages the VB works best with")
    founder_stages_other: Optional[str] = Field(None, max_length=200, description="Other founder stages if 'other' selected")
    geographies: List[Geography] = Field(..., min_items=1, description="Geographic specialization")
    geographies_specific_countries: Optional[str] = Field(None, max_length=500, description="Specific countries if 'specific_countries' selected")
    languages: List[Language] = Field(..., min_items=1, max_items=3, description="Languages (max 3)")
    languages_other: Optional[str] = Field(None, max_length=100, description="Other languages if 'other' selected")
    weekly_availability: WeeklyAvailability = Field(..., description="Estimated weekly availability")
    weekly_availability_other: Optional[str] = Field(None, max_length=50, description="Custom availability if 'other' selected")
    hourly_rate_usd: Decimal = Field(..., ge=0, le=10000, description="Hourly rate in USD")

    @validator('linkedin_url')
    def validate_linkedin_url(cls, v):
        if v and 'linkedin.com' not in v.lower():
            raise ValueError('Must be a valid LinkedIn URL (must contain linkedin.com)')
        return v

    @validator('personal_website')
    def validate_personal_website(cls, v):
        if v and not (v.startswith('http://') or v.startswith('https://')):
            raise ValueError('Personal website must be a valid URL starting with http:// or https://')
        return v

    @validator('phone_country_code')
    def validate_country_code(cls, v):
        if v and not v.isupper():
            return v.upper()
        return v

    @validator('support_areas_other')
    def validate_support_other(cls, v, values):
        if SupportArea.OTHER in values.get('support_areas', []) and not v:
            raise ValueError('support_areas_other is required when "other" is selected in support_areas')
        return v

    @validator('industries_other')
    def validate_industries_other(cls, v, values):
        if Industry.OTHER in values.get('industries_of_focus', []) and not v:
            raise ValueError('industries_other is required when "other" is selected in industries_of_focus')
        return v

    @validator('founder_stages_other')
    def validate_founder_stages_other(cls, v, values):
        if FounderStage.OTHER in values.get('founder_stages', []) and not v:
            raise ValueError('founder_stages_other is required when "other" is selected in founder_stages')
        return v

    @validator('geographies_specific_countries')
    def validate_geographies_specific(cls, v, values):
        if Geography.SPECIFIC_COUNTRIES in values.get('geographies', []) and not v:
            raise ValueError('geographies_specific_countries is required when "specific_countries" is selected')
        return v

    @validator('languages_other')
    def validate_languages_other(cls, v, values):
        if Language.OTHER in values.get('languages', []) and not v:
            raise ValueError('languages_other is required when "other" is selected in languages')
        return v

    @validator('weekly_availability_other')
    def validate_availability_other(cls, v, values):
        if values.get('weekly_availability') == WeeklyAvailability.OTHER and not v:
            raise ValueError('weekly_availability_other is required when weekly_availability is "other"')
        return v

    @validator('languages')
    def validate_languages_max(cls, v):
        if len(v) > 3:
            raise ValueError('Maximum 3 languages allowed')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "full_name": "John Doe",
                "work_email": "john@example.com",
                "phone_country_code": "KE",
                "phone_number": "+254712345678",
                "country": "Kenya",
                "city": "Nairobi",
                "primary_role": "Startup Mentor",
                "company_organization": "TechHub Africa",
                "linkedin_url": "https://linkedin.com/in/johndoe",
                "personal_website": "https://johndoe.com",
                "has_founded_venture": True,
                "ventures_founded_count": 2,
                "ventures_stage_reached": "Series A",
                "ventures_outcome": "1 acquired, 1 operating",
                "coaching_experience": "3-5_years",
                "programs_worked_with": "Y Combinator, Techstars",
                "support_areas": ["product_development", "strategy"],
                "industries_of_focus": ["financial_systems", "agriculture"],
                "founder_stages": ["early_stage", "post_pmf"],
                "geographies": ["east_africa"],
                "languages": ["english", "swahili"],
                "weekly_availability": "6_hrs",
                "hourly_rate_usd": 150.00
            }
        }


class VBInterestApproveRequest(BaseModel):
    """Request to approve a submission"""
    admin_notes: Optional[str] = Field(None, max_length=1000, description="Optional notes about the approval")


class VBInterestRejectRequest(BaseModel):
    """Request to reject a submission"""
    admin_notes: Optional[str] = Field(None, max_length=1000, description="Optional internal admin notes")


class VBInterestNotesUpdate(BaseModel):
    """Request to update admin notes"""
    admin_notes: str = Field(..., max_length=1000, description="Admin notes to set")


class VBInterestListFilters(BaseModel):
    """Filters for listing interest submissions"""
    status: Optional[InterestSubmissionStatus] = None
    search: Optional[str] = Field(None, max_length=200, description="Search by name or email")
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


# =====================================================
# RESPONSE MODELS
# =====================================================

class VBInterestSubmissionResponse(BaseModel):
    """Full interest submission response"""
    id: UUID
    full_name: str
    work_email: str
    phone_country_code: str
    phone_number: str
    country: str
    city: str
    primary_role: str
    company_organization: Optional[str]
    linkedin_url: str
    personal_website: Optional[str]
    has_founded_venture: bool
    ventures_founded_count: Optional[int]
    ventures_stage_reached: Optional[str]
    ventures_outcome: Optional[str]
    coaching_experience: str
    programs_worked_with: Optional[str]
    support_areas: List[str]
    support_areas_other: Optional[str]
    industries_of_focus: List[str]
    industries_other: Optional[str]
    founder_stages: List[str]
    founder_stages_other: Optional[str]
    geographies: List[str]
    geographies_specific_countries: Optional[str]
    languages: List[str]
    languages_other: Optional[str]
    weekly_availability: str
    weekly_availability_other: Optional[str]
    hourly_rate_usd: Decimal
    status: str
    reviewed_by: Optional[UUID]
    reviewed_at: Optional[datetime]
    admin_notes: Optional[str]
    rejection_reason: Optional[str]
    vb_invitation_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class VBInterestSubmissionListItem(BaseModel):
    """Simplified submission for list view"""
    id: UUID
    full_name: str
    work_email: str
    primary_role: str
    coaching_experience: str
    support_areas: List[str]
    industries_of_focus: List[str]
    weekly_availability: str
    hourly_rate_usd: Decimal
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class VBInterestSubmissionListResponse(BaseModel):
    """Paginated list response"""
    items: List[VBInterestSubmissionListItem]
    total: int
    page: int
    page_size: int
    has_next: bool


class VBInterestSubmitResponse(BaseModel):
    """Response after submitting interest"""
    id: UUID
    full_name: str
    work_email: str
    status: str
    message: str
    created_at: datetime


class VBInterestStatusResponse(BaseModel):
    """Response for public status check"""
    email: str
    status: str
    submitted_at: datetime


class VBInterestApproveResponse(BaseModel):
    """Response after approving a submission"""
    submission_id: UUID
    status: str
    invitation_sent: bool
    invitation_token: Optional[str]
    message: str


class VBInterestRejectResponse(BaseModel):
    """Response after rejecting a submission"""
    submission_id: UUID
    status: str
    message: str
