# Venture Builder Declaration of Interest - Software Requirements Specification

## 1. Overview

### 1.1 Purpose
This document specifies the requirements for implementing a **Venture Builder Declaration of Interest** feature. This feature allows potential venture builders to express interest in joining the platform by submitting their professional information, expertise, and availability.

### 1.2 Current VB Flow (Existing)
```
Admin → Send VB Invitation → VB Receives Email → VB Creates Profile → Admin Reviews → Approve/Reject
```

### 1.3 New Flow (Declaration of Interest)
```
Potential VB → Submits Interest Form (Public) → Admin Reviews Submissions → Admin Approves → System Sends VB Invitation → VB Creates Profile → Admin Reviews Profile → Activate
```

### 1.4 Key Difference
- **Current**: Admin-initiated (admin must know who to invite)
- **New**: Self-service (anyone can express interest, admin reviews and decides)

---

## 2. Functional Requirements

### 2.1 Form Sections & Fields

#### Section 1: Personal Information
| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `full_name` | text | ✅ | min: 2, max: 200 chars |
| `work_email` | email | ✅ | Valid email format |
| `phone_number` | text | ✅ | E.164 format with country code |
| `phone_country_code` | text | ✅ | ISO 3166-1 alpha-2 (e.g., "ET", "KE", "NG") |
| `country` | text | ✅ | Valid country name, max: 100 chars |
| `city` | text | ✅ | max: 100 chars |

#### Section 2: Professional Profile
| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `primary_role` | text | ✅ | max: 200 chars |
| `company_organization` | text | ❌ | max: 200 chars |
| `linkedin_url` | url | ✅ | Valid LinkedIn URL pattern |
| `personal_website` | url | ❌ | Valid URL format |

#### Section 3: Venture Building Experience
| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `has_founded_venture` | boolean | ✅ | true/false |
| `ventures_founded_count` | integer | ❌ | Only if has_founded_venture=true, min: 1 |
| `ventures_stage_reached` | text | ❌ | Only if has_founded_venture=true, max: 500 chars |
| `ventures_outcome` | text | ❌ | Only if has_founded_venture=true, max: 500 chars |
| `coaching_experience` | enum | ✅ | "none", "1-2_years", "3-5_years", "5+_years" |
| `programs_worked_with` | text | ❌ | max: 1000 chars (accelerators, incubators, ESOs) |

#### Section 4: Expertise & Coverage (Core Matching Fields)
| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `support_areas` | array[enum] | ✅ | min: 1 selection, multi-select from predefined list |
| `support_areas_other` | text | ❌ | Only if "other" in support_areas, max: 200 chars |
| `industries_of_focus` | array[enum] | ✅ | min: 1 selection, multi-select from predefined list |
| `industries_other` | text | ❌ | Only if "other" in industries, max: 200 chars |
| `founder_stages` | array[enum] | ✅ | min: 1 selection, multi-select from predefined list |
| `founder_stages_other` | text | ❌ | Only if "other" in founder_stages, max: 200 chars |
| `geographies` | array[enum] | ✅ | min: 1 selection, multi-select from predefined list |
| `languages` | array[enum] | ✅ | min: 1, max: 3 selections from predefined list |
| `languages_other` | text | ❌ | Only if "other" in languages, max: 100 chars |
| `weekly_availability` | enum | ✅ | "2_hrs", "4_hrs", "6_hrs", "8_hrs", "10_hrs", "other" |
| `weekly_availability_other` | text | ❌ | Only if weekly_availability="other", max: 50 chars |
| `hourly_rate_usd` | decimal | ✅ | min: 0, max: 10000 |

### 2.2 Predefined Enum Values

#### Support Areas
```python
SUPPORT_AREAS = [
    "generalist",
    "product_development",
    "software_development",
    "hardware_development",
    "strategy",  # GTM, Pricing, Sales, Marketing
    "management_practices",  # Accounting, Finance
    "legal",
    "execution",
    "other"
]
```

#### Industries of Focus
```python
INDUSTRIES = [
    "generalist",
    "financial_systems",
    "healthcare_systems",
    "agriculture",
    "food_systems",
    "education",
    "climate_action",
    "logistics",
    "consumer_tech",
    "fmcg",
    "construction",
    "transportation",
    "artificial_intelligence",
    "conservation",
    "legal",
    "telecommunication",
    "other"
]
```

#### Founder Stages
```python
FOUNDER_STAGES = [
    "early_stage",
    "post_pmf",
    "growth",
    "scale",
    "exit",
    "other"
]
```

#### Geographies
```python
GEOGRAPHIES = [
    "africa_wide",
    "east_africa",
    "west_africa",
    "north_africa",
    "southern_africa",
    "specific_countries"
]
```

#### Languages
```python
LANGUAGES = [
    "english",
    "french",
    "swahili",
    "arabic",
    "amharic",
    "igbo",
    "zulu",
    "lingala",
    "kinyarwanda",
    "luganda",
    "portuguese",
    "other"
]
```

#### Coaching Experience
```python
COACHING_EXPERIENCE = [
    "none",
    "1-2_years",
    "3-5_years",
    "5+_years"
]
```

#### Weekly Availability
```python
WEEKLY_AVAILABILITY = [
    "2_hrs",
    "4_hrs",
    "6_hrs",
    "8_hrs",
    "10_hrs",
    "other"
]
```

---

## 3. Database Schema

### 3.1 Table: `vb_interest_submissions`

```sql
CREATE TABLE vb_interest_submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Personal Information
    full_name TEXT NOT NULL,
    work_email TEXT NOT NULL UNIQUE,
    phone_country_code TEXT NOT NULL,
    phone_number TEXT NOT NULL,
    country TEXT NOT NULL,
    city TEXT NOT NULL,
    
    -- Professional Profile
    primary_role TEXT NOT NULL,
    company_organization TEXT,
    linkedin_url TEXT NOT NULL,
    personal_website TEXT,
    
    -- Venture Building Experience
    has_founded_venture BOOLEAN NOT NULL DEFAULT FALSE,
    ventures_founded_count INTEGER,
    ventures_stage_reached TEXT,
    ventures_outcome TEXT,
    coaching_experience TEXT NOT NULL,  -- enum value
    programs_worked_with TEXT,
    
    -- Expertise & Coverage (stored as JSONB for flexibility)
    support_areas JSONB NOT NULL DEFAULT '[]',  -- array of enum values
    support_areas_other TEXT,
    industries_of_focus JSONB NOT NULL DEFAULT '[]',
    industries_other TEXT,
    founder_stages JSONB NOT NULL DEFAULT '[]',
    founder_stages_other TEXT,
    geographies JSONB NOT NULL DEFAULT '[]',
    languages JSONB NOT NULL DEFAULT '[]',
    languages_other TEXT,
    weekly_availability TEXT NOT NULL,  -- enum value
    weekly_availability_other TEXT,
    hourly_rate_usd DECIMAL(10, 2) NOT NULL,
    
    -- Submission Status
    status TEXT NOT NULL DEFAULT 'pending',  -- pending, approved, rejected, invited
    
    -- Admin Review
    reviewed_by UUID REFERENCES auth.users(id),
    reviewed_at TIMESTAMPTZ,
    admin_notes TEXT,
    rejection_reason TEXT,
    
    -- Link to invitation (if approved and invited)
    vb_invitation_id UUID REFERENCES vb_invitations(id),
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_vb_interest_status ON vb_interest_submissions(status);
CREATE INDEX idx_vb_interest_email ON vb_interest_submissions(work_email);
CREATE INDEX idx_vb_interest_created ON vb_interest_submissions(created_at DESC);

-- Check constraint for status
ALTER TABLE vb_interest_submissions 
ADD CONSTRAINT vb_interest_status_check 
CHECK (status IN ('pending', 'approved', 'rejected', 'invited'));

-- Check constraint for coaching experience
ALTER TABLE vb_interest_submissions 
ADD CONSTRAINT vb_interest_coaching_check 
CHECK (coaching_experience IN ('none', '1-2_years', '3-5_years', '5+_years'));

-- Check constraint for weekly availability
ALTER TABLE vb_interest_submissions 
ADD CONSTRAINT vb_interest_availability_check 
CHECK (weekly_availability IN ('2_hrs', '4_hrs', '6_hrs', '8_hrs', '10_hrs', 'other'));
```

### 3.2 Status Flow

```
┌─────────┐     Admin     ┌──────────┐     Send      ┌─────────┐
│ pending │ ────────────> │ approved │ ────────────> │ invited │
└─────────┘   approves    └──────────┘   invitation  └─────────┘
     │                                                     │
     │  Admin rejects                                      │
     v                                                     v
┌──────────┐                                    [VB continues with
│ rejected │                                     existing invitation
└──────────┘                                     flow]
```

---

## 4. API Endpoints

### 4.1 Public Endpoints (No Auth Required)

#### `POST /api/venture-builder/interest`
Submit a declaration of interest.

**Request Body:**
```json
{
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
  "has_founded_venture": true,
  "ventures_founded_count": 2,
  "ventures_stage_reached": "Series A",
  "ventures_outcome": "1 acquired, 1 operating",
  "coaching_experience": "3-5_years",
  "programs_worked_with": "Y Combinator, Techstars, Google Launchpad",
  "support_areas": ["product_development", "strategy"],
  "industries_of_focus": ["financial_systems", "agriculture"],
  "founder_stages": ["early_stage", "post_pmf"],
  "geographies": ["east_africa"],
  "languages": ["english", "swahili"],
  "weekly_availability": "6_hrs",
  "hourly_rate_usd": 150.00
}
```

**Success Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "full_name": "John Doe",
    "work_email": "john@example.com",
    "status": "pending",
    "message": "Thank you for your interest! Our team will review your submission and get back to you within 3-5 business days.",
    "created_at": "2025-01-27T06:00:00Z"
  },
  "error": null
}
```

**Error Response (400 - Validation Error):**
```json
{
  "success": false,
  "data": null,
  "error": "Validation failed: linkedin_url must be a valid LinkedIn URL"
}
```

**Error Response (409 - Duplicate Email):**
```json
{
  "success": false,
  "data": null,
  "error": "A submission with this email already exists"
}
```

---

#### `GET /api/venture-builder/interest/status/{email}`
Check submission status (rate-limited).

**Response:**
```json
{
  "success": true,
  "data": {
    "email": "john@example.com",
    "status": "pending",
    "submitted_at": "2025-01-27T06:00:00Z"
  },
  "error": null
}
```

---

### 4.2 Admin Endpoints (Admin Auth Required)

#### `GET /api/venture-builder/admin/interest`
List all interest submissions with filters.

**Query Parameters:**
- `status` (optional): Filter by status (pending, approved, rejected, invited)
- `page` (default: 1): Page number
- `page_size` (default: 20, max: 100): Items per page
- `search` (optional): Search by name or email

**Response:**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "full_name": "John Doe",
        "work_email": "john@example.com",
        "primary_role": "Startup Mentor",
        "coaching_experience": "3-5_years",
        "support_areas": ["product_development", "strategy"],
        "industries_of_focus": ["financial_systems", "agriculture"],
        "weekly_availability": "6_hrs",
        "hourly_rate_usd": 150.00,
        "status": "pending",
        "created_at": "2025-01-27T06:00:00Z"
      }
    ],
    "total": 25,
    "page": 1,
    "page_size": 20,
    "has_next": true
  },
  "error": null
}
```

---

#### `GET /api/venture-builder/admin/interest/{submission_id}`
Get full details of a submission.

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
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
    "has_founded_venture": true,
    "ventures_founded_count": 2,
    "ventures_stage_reached": "Series A",
    "ventures_outcome": "1 acquired, 1 operating",
    "coaching_experience": "3-5_years",
    "programs_worked_with": "Y Combinator, Techstars, Google Launchpad",
    "support_areas": ["product_development", "strategy"],
    "industries_of_focus": ["financial_systems", "agriculture"],
    "founder_stages": ["early_stage", "post_pmf"],
    "geographies": ["east_africa"],
    "languages": ["english", "swahili"],
    "weekly_availability": "6_hrs",
    "hourly_rate_usd": 150.00,
    "status": "pending",
    "reviewed_by": null,
    "reviewed_at": null,
    "admin_notes": null,
    "rejection_reason": null,
    "created_at": "2025-01-27T06:00:00Z",
    "updated_at": "2025-01-27T06:00:00Z"
  },
  "error": null
}
```

---

#### `POST /api/venture-builder/admin/interest/{submission_id}/approve`
Approve a submission and send VB invitation.

**Request Body:**
```json
{
  "admin_notes": "Strong candidate with excellent experience"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "submission_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "invited",
    "invitation_sent": true,
    "invitation_token": "abc123...",
    "message": "Submission approved and invitation sent to john@example.com"
  },
  "error": null
}
```

**Flow:**
1. Update submission status to `approved`
2. Automatically create VB invitation record
3. Send invitation email (reuse existing `send_vb_invitation`)
4. Update submission status to `invited`
5. Link `vb_invitation_id` to submission

---

#### `POST /api/venture-builder/admin/interest/{submission_id}/reject`
Reject a submission.

**Request Body:**
```json
{
  "rejection_reason": "Insufficient experience in our focus areas",
  "admin_notes": "Candidate has good background but not aligned with current needs"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "submission_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "rejected",
    "message": "Submission rejected"
  },
  "error": null
}
```

**Note:** Consider whether to send a rejection email (optional feature).

---

#### `PATCH /api/venture-builder/admin/interest/{submission_id}/notes`
Update admin notes on a submission.

**Request Body:**
```json
{
  "admin_notes": "Follow up in Q2 2025"
}
```

---

## 5. Pydantic Models

### 5.1 Enums

```python
class CoachingExperience(str, Enum):
    NONE = "none"
    ONE_TO_TWO_YEARS = "1-2_years"
    THREE_TO_FIVE_YEARS = "3-5_years"
    FIVE_PLUS_YEARS = "5+_years"

class WeeklyAvailability(str, Enum):
    TWO_HRS = "2_hrs"
    FOUR_HRS = "4_hrs"
    SIX_HRS = "6_hrs"
    EIGHT_HRS = "8_hrs"
    TEN_HRS = "10_hrs"
    OTHER = "other"

class SupportArea(str, Enum):
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
    EARLY_STAGE = "early_stage"
    POST_PMF = "post_pmf"
    GROWTH = "growth"
    SCALE = "scale"
    EXIT = "exit"
    OTHER = "other"

class Geography(str, Enum):
    AFRICA_WIDE = "africa_wide"
    EAST_AFRICA = "east_africa"
    WEST_AFRICA = "west_africa"
    NORTH_AFRICA = "north_africa"
    SOUTHERN_AFRICA = "southern_africa"
    SPECIFIC_COUNTRIES = "specific_countries"

class Language(str, Enum):
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
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    INVITED = "invited"
```

### 5.2 Request Models

```python
class VBInterestSubmissionCreate(BaseModel):
    """Create a VB interest submission (public endpoint)"""
    
    # Personal Information
    full_name: str = Field(..., min_length=2, max_length=200)
    work_email: EmailStr
    phone_country_code: str = Field(..., min_length=2, max_length=3, regex=r'^[A-Z]{2,3}$')
    phone_number: str = Field(..., min_length=8, max_length=20)
    country: str = Field(..., max_length=100)
    city: str = Field(..., max_length=100)
    
    # Professional Profile
    primary_role: str = Field(..., max_length=200)
    company_organization: Optional[str] = Field(None, max_length=200)
    linkedin_url: HttpUrl
    personal_website: Optional[HttpUrl] = None
    
    # Venture Building Experience
    has_founded_venture: bool
    ventures_founded_count: Optional[int] = Field(None, ge=1)
    ventures_stage_reached: Optional[str] = Field(None, max_length=500)
    ventures_outcome: Optional[str] = Field(None, max_length=500)
    coaching_experience: CoachingExperience
    programs_worked_with: Optional[str] = Field(None, max_length=1000)
    
    # Expertise & Coverage
    support_areas: List[SupportArea] = Field(..., min_items=1)
    support_areas_other: Optional[str] = Field(None, max_length=200)
    industries_of_focus: List[Industry] = Field(..., min_items=1)
    industries_other: Optional[str] = Field(None, max_length=200)
    founder_stages: List[FounderStage] = Field(..., min_items=1)
    founder_stages_other: Optional[str] = Field(None, max_length=200)
    geographies: List[Geography] = Field(..., min_items=1)
    languages: List[Language] = Field(..., min_items=1, max_items=3)
    languages_other: Optional[str] = Field(None, max_length=100)
    weekly_availability: WeeklyAvailability
    weekly_availability_other: Optional[str] = Field(None, max_length=50)
    hourly_rate_usd: Decimal = Field(..., ge=0, le=10000)
    
    @validator('linkedin_url')
    def validate_linkedin_url(cls, v):
        if v and 'linkedin.com' not in str(v).lower():
            raise ValueError('Must be a valid LinkedIn URL')
        return v
    
    @validator('ventures_founded_count')
    def validate_ventures_count(cls, v, values):
        if values.get('has_founded_venture') and v is None:
            # Optional - don't require if has_founded_venture is true
            pass
        return v
    
    @validator('support_areas_other')
    def validate_support_other(cls, v, values):
        if SupportArea.OTHER in values.get('support_areas', []) and not v:
            raise ValueError('support_areas_other is required when "other" is selected')
        return v
    
    @validator('languages')
    def validate_languages_max(cls, v):
        if len(v) > 3:
            raise ValueError('Maximum 3 languages allowed')
        return v
```

### 5.3 Response Models

```python
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

class VBInterestSubmissionListResponse(BaseModel):
    """Paginated list response"""
    items: List[VBInterestSubmissionListItem]
    total: int
    page: int
    page_size: int
    has_next: bool

class VBInterestApproveRequest(BaseModel):
    """Approve submission request"""
    admin_notes: Optional[str] = Field(None, max_length=1000)

class VBInterestRejectRequest(BaseModel):
    """Reject submission request"""
    rejection_reason: str = Field(..., min_length=10, max_length=500)
    admin_notes: Optional[str] = Field(None, max_length=1000)

class VBInterestNotesUpdate(BaseModel):
    """Update admin notes"""
    admin_notes: str = Field(..., max_length=1000)
```

---

## 6. Service Layer Methods

### 6.1 VBService Additions

```python
class VBService:
    # ... existing methods ...
    
    # =====================================================
    # VB INTEREST SUBMISSIONS
    # =====================================================
    
    def create_interest_submission(
        self,
        submission_data: dict,
    ) -> dict:
        """
        Create a new VB interest submission (public).
        
        - Validates all fields
        - Checks for duplicate email
        - Stores submission with 'pending' status
        - Returns confirmation message
        """
        pass
    
    def get_interest_submission_by_id(
        self,
        submission_id: str,
    ) -> Optional[dict]:
        """Get full submission details by ID"""
        pass
    
    def get_interest_submission_by_email(
        self,
        email: str,
    ) -> Optional[dict]:
        """Get submission status by email (public, limited fields)"""
        pass
    
    def list_interest_submissions(
        self,
        status: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[dict], int]:
        """
        List submissions with filters (admin only).
        Returns (items, total_count)
        """
        pass
    
    def approve_interest_submission(
        self,
        submission_id: str,
        admin_user_id: str,
        admin_notes: Optional[str] = None,
    ) -> dict:
        """
        Approve submission and send VB invitation.
        
        1. Validate submission exists and is pending
        2. Update status to 'approved'
        3. Create VB invitation using existing send_vb_invitation
        4. Update status to 'invited'
        5. Link vb_invitation_id
        6. Return result with invitation token
        """
        pass
    
    def reject_interest_submission(
        self,
        submission_id: str,
        admin_user_id: str,
        rejection_reason: str,
        admin_notes: Optional[str] = None,
    ) -> dict:
        """
        Reject submission.
        
        1. Validate submission exists and is pending
        2. Update status to 'rejected'
        3. Store rejection reason and admin notes
        4. Optionally send rejection email (future feature)
        """
        pass
    
    def update_interest_submission_notes(
        self,
        submission_id: str,
        admin_notes: str,
    ) -> dict:
        """Update admin notes on a submission"""
        pass
```

### 6.2 VBDataAccess Additions

```python
class VBDataAccess:
    # ... existing methods ...
    
    # =====================================================
    # VB INTEREST SUBMISSIONS
    # =====================================================
    
    def create_interest_submission(self, data: dict) -> dict:
        """Insert new interest submission"""
        pass
    
    def get_interest_submission_by_id(self, submission_id: str) -> Optional[dict]:
        """Get submission by ID"""
        pass
    
    def get_interest_submission_by_email(self, email: str) -> Optional[dict]:
        """Get submission by email"""
        pass
    
    def list_interest_submissions(
        self,
        status: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[dict], int]:
        """List submissions with pagination"""
        pass
    
    def update_interest_submission(
        self,
        submission_id: str,
        update_data: dict,
    ) -> dict:
        """Update submission fields"""
        pass
```

---

## 7. Implementation Files

### 7.1 New Files to Create

| File | Purpose |
|------|---------|
| `interest.py` | Router for interest submission endpoints |
| `interest_models.py` | Pydantic models for interest submissions |
| (Migration) `001_vb_interest_submissions.sql` | Database migration |

### 7.2 Files to Modify

| File | Changes |
|------|---------|
| `service.py` | Add interest submission methods |
| `data_access.py` | Add interest submission data access methods |
| `models.py` | Add enums for support areas, industries, etc. |
| `__init__.py` | Register interest router |

---

## 8. Security Considerations

### 8.1 Rate Limiting
- Public submission endpoint: Max 3 submissions per IP per hour
- Status check endpoint: Max 10 requests per email per hour

### 8.2 Data Validation
- Email format validation
- LinkedIn URL pattern validation
- Phone number format validation
- Country/city sanitization

### 8.3 Spam Prevention
- CAPTCHA integration (optional, frontend)
- Email verification (optional, future enhancement)
- Honeypot fields (frontend implementation)

### 8.4 Data Privacy
- Only store necessary PII
- Admin-only access to full submission data
- Public status check returns minimal info

---

## 9. Email Templates (Future Enhancement)

### 9.1 Submission Confirmation Email
Sent to applicant after submission.

### 9.2 Invitation Email
Reuse existing VB invitation email template.

### 9.3 Rejection Email (Optional)
Polite rejection with feedback.

---

## 10. Success Metrics

- Number of submissions received
- Conversion rate (submissions → approved → invited → active VB)
- Time to review (submission to decision)
- Quality of approved VBs (session ratings, earnings)

---

## 11. Implementation Priority

### Phase 1 (MVP)
1. Database schema & migration
2. Pydantic models
3. Data access layer
4. Service layer methods
5. Public submission endpoint
6. Admin list & detail endpoints
7. Admin approve/reject endpoints

### Phase 2 (Enhancements)
1. Public status check endpoint
2. Email notifications
3. Rate limiting
4. Admin notes update endpoint

### Phase 3 (Future)
1. Rejection email
2. Analytics dashboard
3. Bulk approve/reject
4. Export to CSV

---

## 12. Testing Requirements

### 12.1 Unit Tests
- Model validation tests
- Service method tests
- Data access tests

### 12.2 Integration Tests
- Full submission flow
- Approval flow with invitation
- Rejection flow
- Duplicate email handling

### 12.3 API Tests
- Public endpoint accessibility
- Admin endpoint authorization
- Error response formats
