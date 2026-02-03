# Venture Builder Declaration of Interest - Frontend Implementation Guide

## Overview

This document provides all the information needed to implement the frontend for the **Venture Builder Declaration of Interest** feature. The feature allows prospective Venture Builders (coaches/mentors) to submit their interest in joining the platform, and allows admins to review, approve, or reject applications.

**Base URL:** `/venture-builder/interest`

---

## Part 1: User-Side Implementation

### 1.1 Submit Interest Form

**Endpoint:** `POST /venture-builder/interest`  
**Authentication:** None required (public endpoint)  
**Content-Type:** `application/json`

#### Request Body

```json
{
  "full_name": "John Doe",
  "work_email": "john.doe@company.com",
  "country_code": "KE",
  "phone_number": "+254712345678",
  "country_of_residence": "Kenya",
  "city": "Nairobi",
  "current_role": "Startup Mentor",
  "company_organization": "TechHub Africa",
  "linkedin_url": "https://linkedin.com/in/johndoe",
  "personal_website": "https://johndoe.com",
  
  "has_founded_venture": true,
  "ventures_founded_count": 3,
  "ventures_stage_reached": "Series B",
  "ventures_outcome": "2 acquired, 1 operating",
  "coaching_experience": "3-5_years",
  "programs_worked_with": "Y Combinator, Techstars, 500 Startups",
  
  "support_areas": ["product_development", "fundraising", "strategy"],
  "support_areas_other": null,
  "industries_of_focus": ["fintech", "healthtech", "edtech"],
  "industries_other": null,
  "founder_stages": ["early_stage", "post_pmf"],
  "founder_stages_other": null,
  "geographies": ["east_africa", "west_africa"],
  "geographies_specific_countries": "Kenya, Nigeria, Ghana",
  "languages": ["english", "swahili"],
  "languages_other": null,
  "weekly_availability": "6_hrs",
  "weekly_availability_other": null,
  "hourly_rate_usd": 150.00
}
```

#### Field Specifications

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `full_name` | string | ✅ | 2-100 characters |
| `work_email` | string | ✅ | Valid email format |
| `country_code` | string | ✅ | 2-character ISO code (e.g., "KE", "NG") |
| `phone_number` | string | ✅ | International format with + prefix |
| `country_of_residence` | string | ✅ | 2-100 characters |
| `city` | string | ✅ | 2-100 characters |
| `current_role` | string | ✅ | 2-200 characters |
| `company_organization` | string | ✅ | 2-200 characters |
| `linkedin_url` | string | ✅ | Must be valid LinkedIn URL |
| `personal_website` | string | ❌ | Valid URL if provided |
| `has_founded_venture` | boolean | ✅ | - |
| `ventures_founded_count` | integer | ❌ | Required if `has_founded_venture` is true |
| `ventures_stage_reached` | string | ❌ | Required if `has_founded_venture` is true |
| `ventures_outcome` | string | ❌ | Required if `has_founded_venture` is true |
| `coaching_experience` | string | ✅ | Must be valid enum value (see below) |
| `programs_worked_with` | string | ❌ | Max 1000 characters |
| `support_areas` | array | ✅ | 1-10 items from enum values |
| `support_areas_other` | string | ❌ | Required if "other" is in support_areas |
| `industries_of_focus` | array | ✅ | 1-10 items from enum values |
| `industries_other` | string | ❌ | Required if "other" is in industries_of_focus |
| `founder_stages` | array | ✅ | 1-5 items from enum values |
| `founder_stages_other` | string | ❌ | Required if "other" is in founder_stages |
| `geographies` | array | ✅ | 1-10 items from enum values |
| `geographies_specific_countries` | string | ❌ | Max 500 characters |
| `languages` | array | ✅ | 1-10 items from enum values |
| `languages_other` | string | ❌ | Required if "other" is in languages |
| `weekly_availability` | string | ✅ | Must be valid enum value |
| `weekly_availability_other` | string | ❌ | Required if weekly_availability is "other" |
| `hourly_rate_usd` | number | ✅ | 0-10000 |

#### Success Response (201 Created)

```json
{
  "success": true,
  "data": {
    "id": "uuid-string",
    "full_name": "John Doe",
    "work_email": "john.doe@company.com",
    "status": "pending",
    "message": "Thank you for your interest! Our team will review your submission and get back to you within 3-5 business days.",
    "created_at": "2026-01-27T06:18:19.966531+00:00"
  }
}
```

#### Error Responses

**409 Conflict - Email Already Exists:**
```json
{
  "success": false,
  "error": "An application with this email already exists"
}
```

**422 Validation Error:**
```json
{
  "detail": [
    {
      "loc": ["body", "work_email"],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    }
  ]
}
```

**500 Internal Server Error:**
```json
{
  "success": false,
  "error": "Failed to submit interest: {error_message}"
}
```

---

### 1.2 Check Application Status

**Endpoint:** `GET /venture-builder/interest/status/{email}`  
**Authentication:** None required (public endpoint)

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `email` | string | The work email used during submission |

#### Success Response (200 OK)

```json
{
  "success": true,
  "data": {
    "email": "john.doe@company.com",
    "status": "pending",
    "submitted_at": "2026-01-27T06:18:19.966531+00:00",
    "reviewed_at": null,
    "message": "Your application is currently under review. Our team will contact you within 3-5 business days."
  }
}
```

#### Status Messages by Status

| Status | Message |
|--------|---------|
| `pending` | "Your application is currently under review. Our team will contact you within 3-5 business days." |
| `approved` | "Congratulations! Your application has been approved. Please check your email for next steps." |
| `rejected` | "Thank you for your interest. Unfortunately, we are unable to proceed with your application at this time." |
| `invited` | "You have been invited to complete your Venture Builder profile. Please check your email for the invitation link." |

#### Error Response (404 Not Found)

```json
{
  "success": false,
  "error": "No application found for this email"
}
```

---

## Part 2: Admin Dashboard Implementation

> **Note:** All admin endpoints require authentication with admin privileges.

### 2.1 List All Submissions

**Endpoint:** `GET /venture-builder/interest/admin/list`  
**Authentication:** Required (Admin only)

#### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `status` | string | ❌ | null | Filter by status: `pending`, `approved`, `rejected`, `invited` |
| `page` | integer | ❌ | 1 | Page number (1-indexed) |
| `page_size` | integer | ❌ | 20 | Items per page (max 100) |

#### Example Request

```
GET /venture-builder/interest/admin/list?status=pending&page=1&page_size=20
```

#### Success Response (200 OK)

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "uuid-string",
        "full_name": "John Doe",
        "work_email": "john.doe@company.com",
        "country_of_residence": "Kenya",
        "city": "Nairobi",
        "current_role": "Startup Mentor",
        "company_organization": "TechHub Africa",
        "coaching_experience": "3-5_years",
        "weekly_availability": "6_hrs",
        "hourly_rate_usd": 150.00,
        "status": "pending",
        "created_at": "2026-01-27T06:18:19.966531+00:00"
      }
    ],
    "total": 45,
    "page": 1,
    "page_size": 20,
    "total_pages": 3
  }
}
```

---

### 2.2 Get Submission Details

**Endpoint:** `GET /venture-builder/interest/admin/{submission_id}`  
**Authentication:** Required (Admin only)

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `submission_id` | string (UUID) | The submission ID |

#### Success Response (200 OK)

```json
{
  "success": true,
  "data": {
    "id": "uuid-string",
    "full_name": "John Doe",
    "work_email": "john.doe@company.com",
    "country_code": "KE",
    "phone_number": "+254712345678",
    "country_of_residence": "Kenya",
    "city": "Nairobi",
    "current_role": "Startup Mentor",
    "company_organization": "TechHub Africa",
    "linkedin_url": "https://linkedin.com/in/johndoe",
    "personal_website": "https://johndoe.com",
    
    "has_founded_venture": true,
    "ventures_founded_count": 3,
    "ventures_stage_reached": "Series B",
    "ventures_outcome": "2 acquired, 1 operating",
    "coaching_experience": "3-5_years",
    "programs_worked_with": "Y Combinator, Techstars, 500 Startups",
    
    "support_areas": ["product_development", "fundraising", "strategy"],
    "support_areas_other": null,
    "industries_of_focus": ["fintech", "healthtech", "edtech"],
    "industries_other": null,
    "founder_stages": ["early_stage", "post_pmf"],
    "founder_stages_other": null,
    "geographies": ["east_africa", "west_africa"],
    "geographies_specific_countries": "Kenya, Nigeria, Ghana",
    "languages": ["english", "swahili"],
    "languages_other": null,
    "weekly_availability": "6_hrs",
    "weekly_availability_other": null,
    "hourly_rate_usd": 150.00,
    
    "status": "pending",
    "admin_notes": null,
    "reviewed_by": null,
    "reviewed_at": null,
    "rejection_reason": null,
    "invitation_sent_at": null,
    "created_at": "2026-01-27T06:18:19.966531+00:00",
    "updated_at": "2026-01-27T06:18:19.966531+00:00"
  }
}
```

#### Error Response (404 Not Found)

```json
{
  "success": false,
  "error": "Submission not found"
}
```

---

### 2.3 Approve Submission

**Endpoint:** `POST /venture-builder/interest/admin/{submission_id}/approve`  
**Authentication:** Required (Admin only)

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `submission_id` | string (UUID) | The submission ID |

#### Request Body

```json
{
  "admin_notes": "Strong candidate with excellent track record. Approved for onboarding.",
  "send_invitation": true
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `admin_notes` | string | ❌ | Internal notes (max 2000 chars) |
| `send_invitation` | boolean | ❌ | If true, sends VB invitation email (default: false) |

#### Success Response (200 OK)

```json
{
  "success": true,
  "data": {
    "id": "uuid-string",
    "status": "approved",
    "reviewed_at": "2026-01-27T08:30:00.000000+00:00",
    "reviewed_by": "admin-user-id",
    "invitation_sent": true,
    "message": "Submission approved successfully. Invitation email sent."
  }
}
```

---

### 2.4 Reject Submission

**Endpoint:** `POST /venture-builder/interest/admin/{submission_id}/reject`  
**Authentication:** Required (Admin only)

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `submission_id` | string (UUID) | The submission ID |

#### Request Body

```json
{
  "rejection_reason": "Insufficient coaching experience for our current requirements.",
  "admin_notes": "Candidate has good background but only 6 months of coaching experience.",
  "send_notification": true
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `rejection_reason` | string | ✅ | Reason shown to applicant (max 1000 chars) |
| `admin_notes` | string | ❌ | Internal notes (max 2000 chars) |
| `send_notification` | boolean | ❌ | If true, sends rejection email (default: false) |

#### Success Response (200 OK)

```json
{
  "success": true,
  "data": {
    "id": "uuid-string",
    "status": "rejected",
    "reviewed_at": "2026-01-27T08:30:00.000000+00:00",
    "reviewed_by": "admin-user-id",
    "notification_sent": true,
    "message": "Submission rejected. Notification email sent to applicant."
  }
}
```

---

### 2.5 Update Admin Notes

**Endpoint:** `PATCH /venture-builder/interest/admin/{submission_id}/notes`  
**Authentication:** Required (Admin only)

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `submission_id` | string (UUID) | The submission ID |

#### Request Body

```json
{
  "admin_notes": "Follow-up call scheduled for next week. Candidate seems promising."
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `admin_notes` | string | ✅ | Internal notes (max 2000 chars) |

#### Success Response (200 OK)

```json
{
  "success": true,
  "data": {
    "id": "uuid-string",
    "admin_notes": "Follow-up call scheduled for next week. Candidate seems promising.",
    "updated_at": "2026-01-27T08:45:00.000000+00:00",
    "message": "Notes updated successfully"
  }
}
```

---

## Part 3: Enum Values Reference

### Coaching Experience (`coaching_experience`)

| Value | Display Label |
|-------|---------------|
| `no_experience` | No formal experience |
| `less_than_1_year` | Less than 1 year |
| `1-2_years` | 1-2 years |
| `3-5_years` | 3-5 years |
| `5_plus_years` | 5+ years |

### Weekly Availability (`weekly_availability`)

| Value | Display Label |
|-------|---------------|
| `2_hrs` | Up to 2 hours |
| `4_hrs` | Up to 4 hours |
| `6_hrs` | Up to 6 hours |
| `10_hrs` | Up to 10 hours |
| `10_plus_hrs` | 10+ hours |
| `other` | Other (specify) |

### Support Areas (`support_areas`)

| Value | Display Label |
|-------|---------------|
| `product_development` | Product Development |
| `fundraising` | Fundraising |
| `strategy` | Strategy |
| `go_to_market` | Go-to-Market |
| `sales` | Sales |
| `marketing` | Marketing |
| `operations` | Operations |
| `finance` | Finance |
| `legal` | Legal |
| `hr_talent` | HR & Talent |
| `technology` | Technology |
| `leadership` | Leadership |
| `other` | Other |

### Industries (`industries_of_focus`)

| Value | Display Label |
|-------|---------------|
| `fintech` | Fintech |
| `healthtech` | Healthtech |
| `edtech` | Edtech |
| `agritech` | Agritech |
| `cleantech` | Cleantech |
| `logistics` | Logistics |
| `ecommerce` | E-commerce |
| `saas` | SaaS |
| `marketplace` | Marketplace |
| `media_entertainment` | Media & Entertainment |
| `real_estate` | Real Estate |
| `insurance` | Insurance |
| `manufacturing` | Manufacturing |
| `financial_systems` | Financial Systems |
| `agriculture` | Agriculture |
| `other` | Other |

### Founder Stages (`founder_stages`)

| Value | Display Label |
|-------|---------------|
| `ideation` | Ideation |
| `early_stage` | Early Stage (Pre-revenue) |
| `post_pmf` | Post Product-Market Fit |
| `scaling` | Scaling |
| `mature` | Mature/Growth |
| `other` | Other |

### Geographies (`geographies`)

| Value | Display Label |
|-------|---------------|
| `east_africa` | East Africa |
| `west_africa` | West Africa |
| `north_africa` | North Africa |
| `southern_africa` | Southern Africa |
| `central_africa` | Central Africa |
| `global` | Global |
| `other` | Other |

### Languages (`languages`)

| Value | Display Label |
|-------|---------------|
| `english` | English |
| `french` | French |
| `arabic` | Arabic |
| `swahili` | Swahili |
| `portuguese` | Portuguese |
| `amharic` | Amharic |
| `other` | Other |

### Submission Status (`status`)

| Value | Display Label | Description |
|-------|---------------|-------------|
| `pending` | Pending Review | New submission awaiting admin review |
| `approved` | Approved | Application approved, ready for onboarding |
| `rejected` | Rejected | Application rejected |
| `invited` | Invited | Invitation sent to complete VB profile |

---

## Part 4: UI/UX Implementation Notes

### User-Side Form

1. **Multi-step form recommended** - Break the long form into logical sections:
   - Step 1: Personal Information (name, email, phone, location)
   - Step 2: Professional Background (role, company, LinkedIn)
   - Step 3: Venture Experience (founded ventures, coaching experience)
   - Step 4: Expertise & Coverage (support areas, industries, stages)
   - Step 5: Availability & Rate

2. **Conditional fields:**
   - Show `ventures_founded_count`, `ventures_stage_reached`, `ventures_outcome` only when `has_founded_venture` is true
   - Show `*_other` text fields only when "other" is selected in the corresponding multi-select

3. **Validation:**
   - Real-time validation on blur
   - Highlight required fields
   - LinkedIn URL must start with `https://linkedin.com/`

4. **Success state:**
   - Show confirmation with submission ID
   - Provide link to status check page
   - Send confirmation email (handled by backend)

### Admin Dashboard

1. **List View:**
   - Filterable by status (tabs or dropdown)
   - Sortable by date, name
   - Quick actions: View, Approve, Reject
   - Show key info: Name, Email, Location, Experience, Status

2. **Detail View:**
   - Full application details in organized sections
   - Admin notes section (editable)
   - Action buttons: Approve, Reject
   - Status history/audit trail

3. **Bulk Actions (optional):**
   - Select multiple pending applications
   - Bulk approve/reject

---

## Part 5: TypeScript Interfaces

```typescript
// Enums
type CoachingExperience = 
  | 'no_experience' 
  | 'less_than_1_year' 
  | '1-2_years' 
  | '3-5_years' 
  | '5_plus_years';

type WeeklyAvailability = 
  | '2_hrs' 
  | '4_hrs' 
  | '6_hrs' 
  | '10_hrs' 
  | '10_plus_hrs' 
  | 'other';

type SupportArea = 
  | 'product_development' 
  | 'fundraising' 
  | 'strategy' 
  | 'go_to_market' 
  | 'sales' 
  | 'marketing' 
  | 'operations' 
  | 'finance' 
  | 'legal' 
  | 'hr_talent' 
  | 'technology' 
  | 'leadership' 
  | 'other';

type Industry = 
  | 'fintech' 
  | 'healthtech' 
  | 'edtech' 
  | 'agritech' 
  | 'cleantech' 
  | 'logistics' 
  | 'ecommerce' 
  | 'saas' 
  | 'marketplace' 
  | 'media_entertainment' 
  | 'real_estate' 
  | 'insurance' 
  | 'manufacturing' 
  | 'financial_systems' 
  | 'agriculture' 
  | 'other';

type FounderStage = 
  | 'ideation' 
  | 'early_stage' 
  | 'post_pmf' 
  | 'scaling' 
  | 'mature' 
  | 'other';

type Geography = 
  | 'east_africa' 
  | 'west_africa' 
  | 'north_africa' 
  | 'southern_africa' 
  | 'central_africa' 
  | 'global' 
  | 'other';

type Language = 
  | 'english' 
  | 'french' 
  | 'arabic' 
  | 'swahili' 
  | 'portuguese' 
  | 'amharic' 
  | 'other';

type SubmissionStatus = 'pending' | 'approved' | 'rejected' | 'invited';

// Request/Response Interfaces
interface InterestSubmissionRequest {
  full_name: string;
  work_email: string;
  country_code: string;
  phone_number: string;
  country_of_residence: string;
  city: string;
  current_role: string;
  company_organization: string;
  linkedin_url: string;
  personal_website?: string;
  
  has_founded_venture: boolean;
  ventures_founded_count?: number;
  ventures_stage_reached?: string;
  ventures_outcome?: string;
  coaching_experience: CoachingExperience;
  programs_worked_with?: string;
  
  support_areas: SupportArea[];
  support_areas_other?: string;
  industries_of_focus: Industry[];
  industries_other?: string;
  founder_stages: FounderStage[];
  founder_stages_other?: string;
  geographies: Geography[];
  geographies_specific_countries?: string;
  languages: Language[];
  languages_other?: string;
  weekly_availability: WeeklyAvailability;
  weekly_availability_other?: string;
  hourly_rate_usd: number;
}

interface InterestSubmissionResponse {
  id: string;
  full_name: string;
  work_email: string;
  status: SubmissionStatus;
  message: string;
  created_at: string;
}

interface InterestStatusResponse {
  email: string;
  status: SubmissionStatus;
  submitted_at: string;
  reviewed_at: string | null;
  message: string;
}

interface InterestListItem {
  id: string;
  full_name: string;
  work_email: string;
  country_of_residence: string;
  city: string;
  current_role: string;
  company_organization: string;
  coaching_experience: CoachingExperience;
  weekly_availability: WeeklyAvailability;
  hourly_rate_usd: number;
  status: SubmissionStatus;
  created_at: string;
}

interface InterestListResponse {
  items: InterestListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

interface InterestFullDetails extends InterestSubmissionRequest {
  id: string;
  status: SubmissionStatus;
  admin_notes: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
  rejection_reason: string | null;
  invitation_sent_at: string | null;
  created_at: string;
  updated_at: string;
}

interface ApproveRequest {
  admin_notes?: string;
  send_invitation?: boolean;
}

interface RejectRequest {
  rejection_reason: string;
  admin_notes?: string;
  send_notification?: boolean;
}

interface UpdateNotesRequest {
  admin_notes: string;
}

// API Response Wrapper
interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
}
```

---

## Part 6: API Service Example (TypeScript)

```typescript
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL;

export class VBInterestService {
  // Public endpoints (no auth required)
  
  static async submitInterest(
    data: InterestSubmissionRequest
  ): Promise<ApiResponse<InterestSubmissionResponse>> {
    const response = await fetch(`${API_BASE_URL}/venture-builder/interest`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return response.json();
  }

  static async checkStatus(
    email: string
  ): Promise<ApiResponse<InterestStatusResponse>> {
    const response = await fetch(
      `${API_BASE_URL}/venture-builder/interest/status/${encodeURIComponent(email)}`
    );
    return response.json();
  }

  // Admin endpoints (auth required)
  
  static async listSubmissions(
    params: { status?: SubmissionStatus; page?: number; page_size?: number },
    token: string
  ): Promise<ApiResponse<InterestListResponse>> {
    const searchParams = new URLSearchParams();
    if (params.status) searchParams.set('status', params.status);
    if (params.page) searchParams.set('page', params.page.toString());
    if (params.page_size) searchParams.set('page_size', params.page_size.toString());

    const response = await fetch(
      `${API_BASE_URL}/venture-builder/interest/admin/list?${searchParams}`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    return response.json();
  }

  static async getSubmissionDetails(
    submissionId: string,
    token: string
  ): Promise<ApiResponse<InterestFullDetails>> {
    const response = await fetch(
      `${API_BASE_URL}/venture-builder/interest/admin/${submissionId}`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    return response.json();
  }

  static async approveSubmission(
    submissionId: string,
    data: ApproveRequest,
    token: string
  ): Promise<ApiResponse<any>> {
    const response = await fetch(
      `${API_BASE_URL}/venture-builder/interest/admin/${submissionId}/approve`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(data),
      }
    );
    return response.json();
  }

  static async rejectSubmission(
    submissionId: string,
    data: RejectRequest,
    token: string
  ): Promise<ApiResponse<any>> {
    const response = await fetch(
      `${API_BASE_URL}/venture-builder/interest/admin/${submissionId}/reject`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(data),
      }
    );
    return response.json();
  }

  static async updateNotes(
    submissionId: string,
    data: UpdateNotesRequest,
    token: string
  ): Promise<ApiResponse<any>> {
    const response = await fetch(
      `${API_BASE_URL}/venture-builder/interest/admin/${submissionId}/notes`,
      {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(data),
      }
    );
    return response.json();
  }
}
```

---

## Questions?

Contact the backend team for any clarifications or if you encounter issues with the API.
