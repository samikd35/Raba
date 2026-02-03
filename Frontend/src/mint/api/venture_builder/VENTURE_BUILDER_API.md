# Venture Builder Feature

## Overview

The Venture Builder feature connects entrepreneurs with experienced advisors for one-on-one coaching sessions. This comprehensive platform handles:
- VB profile management and onboarding
- Session booking with credit-based payments
- Earnings tracking and payment reconciliation
- Session notes and coaching insights
- Dispute resolution system

## Key Features

### Core Functionality
- **Profile Management**: VBs create detailed profiles with work experience, expertise areas, and biography
- **Session Booking**: Users book 1-hour sessions using tenant credits
- **Earnings Dashboard**: VBs track earnings with USD conversion and commission deduction
- **Payment Reconciliation**: Admins settle payments and mark sessions as paid
- **Session Notes**: VBs create coaching notes visible to users or kept private
- **Dispute System**: Users can report problems with completed sessions

### Payment Flow
1. User books session → Credits deducted (FIFO lot-based)
2. Session completed → Earnings calculated (Credits × USD rate - Commission)
3. Admin reconciles → Sessions marked as **SETTLED**, VB gets paid
4. History tracked → Full audit trail of all reconciliations

### Session Status Lifecycle

Sessions progress through the following statuses:

```
CONFIRMED → COMPLETED → SETTLED → (Final)
     ↓
CANCELED
```

- **CONFIRMED**: Session confirmed and scheduled
- **COMPLETED**: Session finished, awaiting payment reconciliation
- **SETTLED**: Session paid/reconciled
- **CANCELED**: Session canceled

> **Note**: The `SETTLED` status was added to track which sessions have been paid for through the reconciliation process. This provides clear distinction between completed sessions (finished but unpaid) and settled sessions (paid/reconciled).

## API Routes

### Base URL
```
/api/venture-builder
```

### Authentication
- **Admin routes**: Require admin role (`get_admin_user`)
- **Super Admin routes**: Require super admin role (`get_super_admin_user`)
- **VB routes**: Require venture_builder role (`get_vb_or_admin_user`)
- **User routes**: Require authenticated user (`get_current_user`)

### Response Format

All Venture Builder API endpoints return responses in a standardized format:

**Success Response:**
```json
{
  "success": true,
  "data": { /* endpoint-specific data */ },
  "error": null
}
```

**Error Response:**
```json
{
  "success": false,
  "data": null,
  "error": "Error message describing what went wrong"
}
```

**Error Status Codes:**
- `400 Bad Request` - Validation errors, invalid input
- `402 Payment Required` - Insufficient credits
- `403 Forbidden` - Access denied
- `404 Not Found` - Resource not found
- `409 Conflict` - Booking conflicts, duplicate disputes
- `422 Unprocessable Entity` - Incomplete profile
- `500 Internal Server Error` - Unexpected server errors

---

## Table of Contents
1. [VB Invitations](#vb-invitations)
2. [Expertise Areas](#expertise-areas)
3. [VB Profile Management](#vb-profile-management)
4. [Admin VB Management](#admin-vb-management)
5. [Session Booking](#session-booking)
6. [VB Portal - Sessions](#vb-portal---sessions)
7. [Session Notes](#session-notes)
8. [Earnings](#earnings)
9. [Reconciliation](#reconciliation)
10. [VB Portal - Projects](#vb-portal---projects)
11. [Disputes](#disputes)

---

## VB Invitations

### Send VB Invitation (Admin)

**Endpoint:** `POST /api/venture-builder/admin/invite`

**Authentication:** Admin required

**Request Body:**
```json
{
  "email": "advisor@example.com"
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "message": "Invitation sent to advisor@example.com",
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "email": "advisor@example.com"
  },
  "error": null
}
```

**Error Response (400 Bad Request):**
```json
{
  "success": false,
  "data": null,
  "error": "Invalid email address"
}
```

**Error Response (403 Forbidden):**
```json
{
  "success": false,
  "data": null,
  "error": "Admin access required"
}
```

---

## Expertise Areas

### List All Expertise Areas (Admin)

**Endpoint:** `GET /api/venture-builder/admin/expertise`

**Authentication:** Admin required

**Query Parameters:**
- `include_inactive` (boolean, optional): Include inactive expertise areas (default: false)

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Product Strategy",
      "description": "Product development and go-to-market strategy",
      "display_order": 1,
      "is_active": true,
      "created_at": "2024-12-26T10:00:00Z",
      "updated_at": "2024-12-26T10:00:00Z"
    },
    {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "name": "Fundraising",
      "description": "Venture capital and fundraising strategy",
      "display_order": 2,
      "is_active": true,
      "created_at": "2024-12-26T10:00:00Z",
      "updated_at": "2024-12-26T10:00:00Z"
    }
  ],
  "error": null
}
```

**Error Response (403 Forbidden):**
```json
{
  "success": false,
  "data": null,
  "error": "Admin access required"
}
```

### List Active Expertise Areas (Public)

**Endpoint:** `GET /api/venture-builder/expertise`

**Authentication:** None required (public)

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Product Strategy",
      "description": "Product development and go-to-market strategy",
      "display_order": 1,
      "is_active": true,
      "created_at": "2024-12-26T10:00:00Z",
      "updated_at": "2024-12-26T10:00:00Z"
    }
  ],
  "error": null
}
```

### Create Expertise Area (Admin)

**Endpoint:** `POST /api/venture-builder/admin/expertise`

**Authentication:** Admin required

**Request Body:**
```json
{
  "name": "Product Strategy",
  "description": "Product development and go-to-market strategy",
  "display_order": 1
}
```

**Success Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Product Strategy",
    "description": "Product development and go-to-market strategy",
    "display_order": 1,
    "is_active": true,
    "created_at": "2024-12-26T10:00:00Z",
    "updated_at": "2024-12-26T10:00:00Z"
  },
  "error": null
}
```

**Error Response (400 Bad Request):**
```json
{
  "success": false,
  "data": null,
  "error": "Name is required and must be between 1-100 characters"
}
```

### Update Expertise Area (Admin)

**Endpoint:** `PATCH /api/venture-builder/admin/expertise/{expertise_id}`

**Authentication:** Admin required

**Path Parameters:**
- `expertise_id` (UUID, required): Expertise area ID

**Request Body (all fields optional):**
```json
{
  "name": "Updated Product Strategy",
  "description": "Updated description",
  "display_order": 2,
  "is_active": false
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Updated Product Strategy",
    "description": "Updated description",
    "display_order": 2,
    "is_active": false,
    "created_at": "2024-12-26T10:00:00Z",
    "updated_at": "2024-12-26T11:00:00Z"
  },
  "error": null
}
```

**Error Response (404 Not Found):**
```json
{
  "success": false,
  "data": null,
  "error": "Expertise area not found"
}
```

### Delete Expertise Area (Super Admin)

**Endpoint:** `DELETE /api/venture-builder/admin/expertise/{expertise_id}`

**Authentication:** Super Admin required

**Path Parameters:**
- `expertise_id` (UUID, required): Expertise area ID

**Success Response (204 No Content):**
```json
{
  "success": true,
  "data": null,
  "error": null
}
```

**Error Response (403 Forbidden):**
```json
{
  "success": false,
  "data": null,
  "error": "Super admin access required"
}
```

**Error Response (404 Not Found):**
```json
{
  "success": false,
  "data": null,
  "error": "Expertise area not found"
}
```

---

## VB Profile Management

### Create VB Profile (VB)

**Endpoint:** `POST /api/venture-builder/profile/create`

**Authentication:** User required (authenticated)

**Query Parameters:**
- `invitation_token` (string, required): VB invitation token from email

**Request Body (multipart/form-data):**
- `data` (JSON string, required): Profile data
- `profile_picture` (file, optional): Profile picture file (jpg, jpeg, png, gif, webp, bmp, max 5MB)

**JSON data structure:**
```json
{
  "name": "John Doe",
  "contact_email": "john@example.com",
  "main_expertise": "Product Strategy and Go-to-Market",
  "short_intro": "15+ years building successful startups",
  "biography": "Experienced entrepreneur with deep expertise in product strategy and scaling businesses. Founded 3 successful startups with exits totaling $50M+.",
  "linkedin_url": "https://linkedin.com/in/johndoe",
  "work_experience": [
    {
      "position": "CEO & Founder",
      "organization": "TechCorp Inc",
      "years": "2015-2020",
      "description": "Led team of 50+ employees, raised $10M Series A"
    },
    {
      "position": "VP of Product",
      "organization": "StartupXYZ",
      "years": "2010-2015",
      "description": "Built product from 0 to 1M users"
    }
  ],
  "expertise_ids": [
    "550e8400-e29b-41d4-a716-446655440000",
    "660e8400-e29b-41d4-a716-446655440001"
  ]
}
```

**Success Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "id": "770e8400-e29b-41d4-a716-446655440002",
    "user_id": "880e8400-e29b-41d4-a716-446655440003",
    "name": "John Doe",
    "contact_email": "john@example.com",
    "main_expertise": "Product Strategy and Go-to-Market",
    "short_intro": "15+ years building successful startups",
    "profile_picture_url": "https://storage.example.com/profiles/abc123.jpg",
    "biography": "Experienced entrepreneur with deep expertise...",
    "linkedin_url": "https://linkedin.com/in/johndoe",
    "work_experience": [...],
    "calendar_booking_url": null,
    "credit_price_per_hour": 0,
    "status": "pending_admin_review",
    "areas_of_expertise": [...],
    "created_at": "2024-12-26T10:00:00Z",
    "updated_at": "2024-12-26T10:00:00Z"
  },
  "error": null
}
```

**Error Response (400 Bad Request):**
```json
{
  "success": false,
  "data": null,
  "error": "Invalid invitation token"
}
```

**Error Response (403 Forbidden):**
```json
{
  "success": false,
  "data": null,
  "error": "Invitation email does not match your account"
}
```

### Update VB Profile (VB)

**Endpoint:** `PATCH /api/venture-builder/profile`

**Authentication:** VB or Admin required

**Request Body (multipart/form-data, all fields optional):**
- `data` (JSON string, optional): Profile data to update
- `profile_picture` (file, optional): New profile picture

**JSON data structure (all fields optional):**
```json
{
  "name": "John Doe",
  "contact_email": "john.new@example.com",
  "main_expertise": "Updated expertise",
  "short_intro": "Updated intro",
  "biography": "Updated biography with at least 50 characters for validation to pass",
  "linkedin_url": "https://linkedin.com/in/johndoe-updated",
  "work_experience": [...],
  "expertise_ids": [...]
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "id": "770e8400-e29b-41d4-a716-446655440002",
    "user_id": "880e8400-e29b-41d4-a716-446655440003",
    "name": "John Doe",
    "contact_email": "john.new@example.com",
    "main_expertise": "Updated expertise",
    "short_intro": "Updated intro",
    "profile_picture_url": "https://storage.example.com/profiles/new123.jpg",
    "biography": "Updated biography...",
    "linkedin_url": "https://linkedin.com/in/johndoe-updated",
    "work_experience": [...],
    "calendar_booking_url": "https://calendar.google.com/...",
    "credit_price_per_hour": 100,
    "status": "active",
    "areas_of_expertise": [...],
    "created_at": "2024-12-26T10:00:00Z",
    "updated_at": "2024-12-26T11:00:00Z"
  },
  "error": null
}
```

**Error Response (404 Not Found):**
```json
{
  "success": false,
  "data": null,
  "error": "VB profile not found for current user"
}
```

### Get My VB Profile (VB)

**Endpoint:** `GET /api/venture-builder/profile`

**Authentication:** VB or Admin required

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "id": "770e8400-e29b-41d4-a716-446655440002",
    "user_id": "880e8400-e29b-41d4-a716-446655440003",
    "name": "John Doe",
    "contact_email": "john@example.com",
    "main_expertise": "Product Strategy and Go-to-Market",
    "short_intro": "15+ years building successful startups",
    "profile_picture_url": "https://storage.example.com/profiles/abc123.jpg",
    "biography": "Experienced entrepreneur...",
    "linkedin_url": "https://linkedin.com/in/johndoe",
    "work_experience": [...],
    "calendar_booking_url": "https://calendar.google.com/...",
    "credit_price_per_hour": 100,
    "status": "active",
    "areas_of_expertise": [...],
    "created_at": "2024-12-26T10:00:00Z",
    "updated_at": "2024-12-26T10:00:00Z"
  },
  "error": null
}
```

**Error Response (404 Not Found):**
```json
{
  "success": false,
  "data": null,
  "error": "VB profile not found"
}
```

**Error Response (422 Unprocessable Entity):**
```json
{
  "success": false,
  "data": null,
  "error": "Profile incomplete. Please complete your profile before accessing this information."
}
```

### Delete My VB Profile (VB/Super Admin)

**Endpoint:** `DELETE /api/venture-builder/profile`

**Authentication:** VB or Super Admin required

**Success Response (204 No Content):**

No response body is returned for successful deletion.

**Error Response (404 Not Found):**
```json
{
  "success": false,
  "data": null,
  "error": "VB profile not found"
}
```

---

## Admin VB Management

### List Pending VBs (Admin)

**Endpoint:** `GET /api/venture-builder/admin/vb/pending`

**Authentication:** Admin required

**Description:** Get all VB profiles that are pending admin review.

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "id": "770e8400-e29b-41d4-a716-446655440002",
      "user_id": "880e8400-e29b-41d4-a716-446655440003",
      "name": "John Doe",
      "contact_email": "john@example.com",
      "main_expertise": "Product Strategy",
      "short_intro": "15+ years experience",
      "profile_picture_url": "https://storage.example.com/profiles/abc.jpg",
      "biography": "Experienced entrepreneur...",
      "linkedin_url": "https://linkedin.com/in/johndoe",
      "work_experience": [...],
      "calendar_booking_url": null,
      "credit_price_per_hour": 0,
      "status": "pending_admin_review",
      "areas_of_expertise": [...],
      "created_at": "2024-12-26T10:00:00Z",
      "updated_at": "2024-12-26T10:00:00Z"
    }
  ],
  "error": null
}
```

**Error Response (403 Forbidden):**
```json
{
  "success": false,
  "data": null,
  "error": "Admin access required"
}
```

### Approve VB (Admin)

**Endpoint:** `POST /api/venture-builder/admin/vb/{vb_id}/approve`

**Authentication:** Admin required

**Path Parameters:**
- `vb_id` (UUID, required): VB profile ID

**Request Body:**
```json
{
  "credit_price_per_hour": 100,
  "calendar_booking_url": "https://calendar.google.com/calendar/appointments/schedules/..."
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "id": "770e8400-e29b-41d4-a716-446655440002",
    "user_id": "880e8400-e29b-41d4-a716-446655440003",
    "name": "John Doe",
    "contact_email": "john@example.com",
    "main_expertise": "Product Strategy",
    "short_intro": "15+ years experience",
    "profile_picture_url": "https://storage.example.com/profiles/abc.jpg",
    "biography": "Experienced entrepreneur...",
    "linkedin_url": "https://linkedin.com/in/johndoe",
    "work_experience": [...],
    "calendar_booking_url": "https://calendar.google.com/...",
    "credit_price_per_hour": 100,
    "status": "active",
    "areas_of_expertise": [...],
    "created_at": "2024-12-26T10:00:00Z",
    "updated_at": "2024-12-26T11:00:00Z"
  },
  "error": null
}
```

**Error Response (404 Not Found):**
```json
{
  "success": false,
  "data": null,
  "error": "VB profile not found"
}
```

**Error Response (400 Bad Request):**
```json
{
  "success": false,
  "data": null,
  "error": "VB is not in pending_admin_review status"
}
```

### Update VB Pricing (Admin)

**Endpoint:** `PATCH /api/venture-builder/admin/vb/{vb_id}/pricing`

**Authentication:** Admin required

**Path Parameters:**
- `vb_id` (UUID, required): VB profile ID

**Request Body:**
```json
{
  "credit_price_per_hour": 120
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "id": "770e8400-e29b-41d4-a716-446655440002",
    "user_id": "880e8400-e29b-41d4-a716-446655440003",
    "name": "John Doe",
    "contact_email": "john@example.com",
    "credit_price_per_hour": 120,
    "status": "active",
    "created_at": "2024-12-26T10:00:00Z",
    "updated_at": "2024-12-26T12:00:00Z",
    ...
  },
  "error": null
}
```

**Error Response (404 Not Found):**
```json
{
  "success": false,
  "data": null,
  "error": "VB profile not found"
}
```

### Publish/Unpublish VB (Admin)

**Endpoint:** `PATCH /api/venture-builder/admin/vb/{vb_id}/publish`

**Authentication:** Admin required

**Path Parameters:**
- `vb_id` (UUID, required): VB profile ID

**Request Body:**
```json
{
  "is_active": true
}
```

**Description:** Toggles between 'active' and 'inactive' status.

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "id": "770e8400-e29b-41d4-a716-446655440002",
    "user_id": "880e8400-e29b-41d4-a716-446655440003",
    "name": "John Doe",
    "status": "active",
    "created_at": "2024-12-26T10:00:00Z",
    "updated_at": "2024-12-26T12:00:00Z",
    ...
  },
  "error": null
}
```

**Error Response (404 Not Found):**
```json
{
  "success": false,
  "data": null,
  "error": "VB profile not found"
}
```

---

## Session Booking

### Browse VBs (Public)

**Endpoint:** `GET /api/venture-builder/browse`

**Authentication:** None required (public)

**Query Parameters:**
- `expertise_ids` (array of UUIDs, optional): Filter by expertise areas
- `search_query` (string, optional, max 200 chars): Search in name, expertise, bio
- `page` (integer, optional, default: 1, min: 1): Page number
- `page_size` (integer, optional, default: 20, min: 1, max: 100): Items per page

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "total": 25,
    "items": [
      {
        "id": "770e8400-e29b-41d4-a716-446655440002",
        "user_id": "880e8400-e29b-41d4-a716-446655440003",
        "name": "John Doe",
        "profile_picture_url": "https://storage.example.com/profiles/abc.jpg",
        "main_expertise": "Product Strategy and Go-to-Market",
        "short_intro": "15+ years building successful startups",
        "biography": "Experienced entrepreneur...",
        "linkedin_url": "https://linkedin.com/in/johndoe",
        "credit_price_per_hour": 100,
        "areas_of_expertise": [
          {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "name": "Product Strategy",
            "description": "Product development strategy",
            "display_order": 1,
            "is_active": true,
            "created_at": "2024-12-26T10:00:00Z",
            "updated_at": "2024-12-26T10:00:00Z"
          }
        ]
      }
    ],
    "page": 1,
    "page_size": 20
  },
  "error": null
}
```

### Get VB Details (Public)

**Endpoint:** `GET /api/venture-builder/browse/{vb_id}`

**Authentication:** None required (public)

**Path Parameters:**
- `vb_id` (UUID, required): VB profile ID

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "id": "770e8400-e29b-41d4-a716-446655440002",
    "user_id": "880e8400-e29b-41d4-a716-446655440003",
    "name": "John Doe",
    "contact_email": "john@example.com",
    "main_expertise": "Product Strategy and Go-to-Market",
    "short_intro": "15+ years building successful startups",
    "profile_picture_url": "https://storage.example.com/profiles/abc.jpg",
    "biography": "Experienced entrepreneur with deep expertise in product strategy...",
    "linkedin_url": "https://linkedin.com/in/johndoe",
    "work_experience": [
      {
        "position": "CEO & Founder",
        "organization": "TechCorp Inc",
        "years": "2015-2020",
        "description": "Led team of 50+ employees"
      }
    ],
    "calendar_booking_url": "https://calendar.google.com/...",
    "credit_price_per_hour": 100,
    "status": "active",
    "areas_of_expertise": [...],
    "created_at": "2024-12-26T10:00:00Z",
    "updated_at": "2024-12-26T10:00:00Z"
  },
  "error": null
}
```

**Error Response (404 Not Found):**
```json
{
  "success": false,
  "data": null,
  "error": "VB profile not found or incomplete"
}
```

### Get Tenant Projects (User)

**Endpoint:** `GET /api/venture-builder/booking/projects`

**Authentication:** User required

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "id": "990e8400-e29b-41d4-a716-446655440004",
      "name": "Mobile App Project",
      "tenant_id": "aa0e8400-e29b-41d4-a716-446655440005"
    },
    {
      "id": "bb0e8400-e29b-41d4-a716-446655440006",
      "name": "SaaS Platform",
      "tenant_id": "aa0e8400-e29b-41d4-a716-446655440005"
    }
  ],
  "error": null
}
```

**Error Response (403 Forbidden):**
```json
{
  "success": false,
  "data": null,
  "error": "User authentication required"
}
```

### Check Booking Credits (User)

**Endpoint:** `GET /api/venture-builder/booking/credits/{vb_id}`

**Authentication:** User required

**Path Parameters:**
- `vb_id` (UUID, required): Venture Builder ID

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "has_sufficient_credits": true,
    "current_balance": 500,
    "required_credits": 100,
    "vb_credit_price": 100
  },
  "error": null
}
```

**Error Response (404 Not Found):**
```json
{
  "success": false,
  "data": null,
  "error": "Venture builder not found"
}
```

### Create Booking (User)

**Endpoint:** `POST /api/venture-builder/booking`

**Authentication:** User required

**Request Body:**
```json
{
  "venture_builder_id": "770e8400-e29b-41d4-a716-446655440002",
  "project_id": "990e8400-e29b-41d4-a716-446655440004",
  "tenant_id": "aa0e8400-e29b-41d4-a716-446655440005",
  "session_datetime": "2024-12-30T14:00:00Z",
  "accepted_terms_version": "v1.0",
  "agenda": "Discuss product-market fit and go-to-market strategy for our new mobile app"
}
```

**Success Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "id": "cc0e8400-e29b-41d4-a716-446655440007",
    "tenant_id": "aa0e8400-e29b-41d4-a716-446655440005",
    "booked_by_user_id": "880e8400-e29b-41d4-a716-446655440003",
    "venture_builder_id": "770e8400-e29b-41d4-a716-446655440002",
    "project_id": "990e8400-e29b-41d4-a716-446655440004",
    "session_datetime": "2024-12-30T14:00:00Z",
    "session_duration_minutes": 60,
    "credits_charged": 100,
    "status": "confirmed",
    "calendar_event_id": "evt_abc123xyz",
    "agenda": "Discuss product-market fit and go-to-market strategy for our new mobile app",
    "created_at": "2024-12-26T10:00:00Z"
  },
  "error": null
}
```

**Error Response (402 Payment Required):**
```json
{
  "success": false,
  "data": null,
  "error": "Insufficient credits. Required: 100, Available: 50"
}
```

**Error Response (409 Conflict):**
```json
{
  "success": false,
  "data": null,
  "error": "This time slot is no longer available"
}
```

**Error Response (404 Not Found):**
```json
{
  "success": false,
  "data": null,
  "error": "Venture builder not found or inactive"
}
```

**Error Response (403 Forbidden):**
```json
{
  "success": false,
  "data": null,
  "error": "Tenant ID mismatch"
}
```

---

## VB Portal - Sessions

### Get My VB Sessions (VB)

**Endpoint:** `GET /api/venture-builder/sessions/vb`

**Authentication:** VB or Admin required

**Query Parameters:**
- `status_filter` (string, optional): Filter by status (confirmed, completed, settled, canceled)
- `start_date` (datetime, optional): Filter sessions after this date
- `end_date` (datetime, optional): Filter sessions before this date
- `page` (integer, optional, default: 1, min: 1): Page number
- `page_size` (integer, optional, default: 20, min: 1, max: 100): Items per page

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "id": "cc0e8400-e29b-41d4-a716-446655440007",
      "tenant_id": "aa0e8400-e29b-41d4-a716-446655440005",
      "booked_by_user_id": "880e8400-e29b-41d4-a716-446655440003",
      "venture_builder_id": "770e8400-e29b-41d4-a716-446655440002",
      "project_id": "990e8400-e29b-41d4-a716-446655440004",
      "session_datetime": "2024-12-30T14:00:00Z",
      "session_duration_minutes": 60,
      "credits_charged": 100,
      "status": "completed",
      "calendar_event_id": "evt_abc123xyz",
      "agenda": "Discuss product-market fit",
      "created_at": "2024-12-26T10:00:00Z",
      "vb_email": "john@example.com",
      "vb_picture": "https://storage.example.com/profiles/abc.jpg",
      "has_notes": true
    }
  ],
  "error": null
}
```

**Error Response (404 Not Found):**
```json
{
  "success": false,
  "data": null,
  "error": "VB profile not found"
}
```

### Get My User Sessions (User)

**Endpoint:** `GET /api/venture-builder/sessions/user`

**Authentication:** User required

**Query Parameters:**
- `status_filter` (string, optional): Filter by status (confirmed, completed, settled, canceled)
- `start_date` (datetime, optional): Filter sessions after this date
- `end_date` (datetime, optional): Filter sessions before this date
- `page` (integer, optional, default: 1, min: 1): Page number
- `page_size` (integer, optional, default: 20, min: 1, max: 100): Items per page

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "id": "cc0e8400-e29b-41d4-a716-446655440007",
      "tenant_id": "aa0e8400-e29b-41d4-a716-446655440005",
      "booked_by_user_id": "880e8400-e29b-41d4-a716-446655440003",
      "venture_builder_id": "770e8400-e29b-41d4-a716-446655440002",
      "project_id": "990e8400-e29b-41d4-a716-446655440004",
      "session_datetime": "2024-12-30T14:00:00Z",
      "session_duration_minutes": 60,
      "credits_charged": 100,
      "status": "confirmed",
      "calendar_event_id": "evt_abc123xyz",
      "agenda": "Discuss product-market fit",
      "created_at": "2024-12-26T10:00:00Z",
      "vb_email": "john@example.com",
      "vb_picture": "https://storage.example.com/profiles/abc.jpg",
      "has_notes": false
    }
  ],
  "error": null
}
```

### Complete Session (VB or Admin)

**Endpoint:** `POST /api/venture-builder/sessions/{session_id}/complete`

**Authentication:** VB or Admin required

**Path Parameters:**
- `session_id` (UUID, required): Session ID

**Description:** Mark a session as completed after it has ended (or within 10 minutes of ending). Only the VB who owns the session or an admin can complete it.

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "id": "cc0e8400-e29b-41d4-a716-446655440007",
    "status": "completed",
    "session_datetime": "2024-12-30T14:00:00Z",
    "credits_charged": 100,
    "updated_at": "2024-12-30T15:05:00Z"
  },
  "error": null
}
```

**Error Response (400 Bad Request):**
```json
{
  "success": false,
  "data": null,
  "error": "Session has not ended yet"
}
```

**Error Response (403 Forbidden):**
```json
{
  "success": false,
  "data": null,
  "error": "Only the VB who owns this session can complete it"
}
```

**Error Response (404 Not Found):**
```json
{
  "success": false,
  "data": null,
  "error": "Session not found"
}
```

### Cancel Session (VB or Admin ONLY)

**Endpoint:** `POST /api/venture-builder/sessions/{session_id}/cancel`

**Authentication:** VB or Admin required

**Path Parameters:**
- `session_id` (UUID, required): Session ID

**Request Body:**
```json
{
  "cancellation_reason": "I have an unexpected conflict and need to reschedule. I apologize for the inconvenience."
}
```

**Description:** Cancel a booked session. Only Venture Builders and admins can cancel sessions.

**What happens when a VB cancels:**
1. Session status changes to `canceled`
2. Google Calendar event is deleted (if exists)
3. Credits are fully refunded to the user's tenant
4. User receives email notification with cancellation reason and rebooking link
5. Time slot becomes available for other bookings

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "id": "cc0e8400-e29b-41d4-a716-446655440007",
    "status": "canceled",
    "credits_refunded": 100,
    "cancellation_reason": "I have an unexpected conflict and need to reschedule. I apologize for the inconvenience.",
    "updated_at": "2024-12-26T11:00:00Z"
  },
  "error": null
}
```

**Error Response (403 Forbidden):**
```json
{
  "success": false,
  "data": null,
  "error": "Only the venture builder or admin can cancel a session"
}
```

**Error Response (400 Bad Request - Invalid reason):**
```json
{
  "success": false,
  "data": null,
  "error": "Cancellation reason must be between 10-500 characters"
}
```

**Error Response (400 Bad Request - Already started):**
```json
{
  "success": false,
  "data": null,
  "error": "Cannot cancel a session that has already started"
}
```

---

## Session Notes

### Create Session Note (VB)

**Endpoint:** `POST /api/venture-builder/notes`

**Authentication:** VB or Admin required

**Request Body:**
```json
{
  "vb_session_id": "cc0e8400-e29b-41d4-a716-446655440007",
  "main_outcomes": "Discussed product-market fit and identified 3 key customer segments to focus on",
  "key_takeaways": "Focus on enterprise customers first, validate pricing model, conduct 10 customer interviews",
  "next_steps": "Complete customer interviews by next week, create pricing proposal, schedule follow-up session",
  "visible_to_user": true
}
```

**Success Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "id": "dd0e8400-e29b-41d4-a716-446655440008",
    "vb_session_id": "cc0e8400-e29b-41d4-a716-446655440007",
    "venture_builder_id": "770e8400-e29b-41d4-a716-446655440002",
    "created_by_user_id": "880e8400-e29b-41d4-a716-446655440003",
    "main_outcomes": "Discussed product-market fit and identified 3 key customer segments to focus on",
    "key_takeaways": "Focus on enterprise customers first, validate pricing model, conduct 10 customer interviews",
    "next_steps": "Complete customer interviews by next week, create pricing proposal, schedule follow-up session",
    "visible_to_user": true,
    "created_at": "2024-12-30T15:30:00Z",
    "updated_at": "2024-12-30T15:30:00Z"
  },
  "error": null
}
```

**Error Response (404 Not Found):**
```json
{
  "success": false,
  "data": null,
  "error": "VB profile not found"
}
```

**Error Response (400 Bad Request):**
```json
{
  "success": false,
  "data": null,
  "error": "Session not found or does not belong to this VB"
}
```

### Update Session Note (VB)

**Endpoint:** `PATCH /api/venture-builder/notes/{note_id}`

**Authentication:** VB or Admin required

**Path Parameters:**
- `note_id` (UUID, required): Note ID

**Request Body (all fields optional):**
```json
{
  "main_outcomes": "Updated outcomes",
  "key_takeaways": "Updated takeaways",
  "next_steps": "Updated action items",
  "visible_to_user": false
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "id": "dd0e8400-e29b-41d4-a716-446655440008",
    "vb_session_id": "cc0e8400-e29b-41d4-a716-446655440007",
    "venture_builder_id": "770e8400-e29b-41d4-a716-446655440002",
    "created_by_user_id": "880e8400-e29b-41d4-a716-446655440003",
    "main_outcomes": "Updated outcomes",
    "key_takeaways": "Updated takeaways",
    "next_steps": "Updated action items",
    "visible_to_user": false,
    "created_at": "2024-12-30T15:30:00Z",
    "updated_at": "2024-12-30T16:00:00Z"
  },
  "error": null
}
```

**Error Response (404 Not Found):**
```json
{
  "success": false,
  "data": null,
  "error": "Session note not found"
}
```

**Error Response (403 Forbidden):**
```json
{
  "success": false,
  "data": null,
  "error": "You can only update your own notes"
}
```

### Get Session Note for User (User)

**Endpoint:** `GET /api/venture-builder/notes/session/{session_id}/user`

**Authentication:** User required

**Path Parameters:**
- `session_id` (UUID, required): Session ID

**Description:** Get notes for a specific session (only visible notes).

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "id": "dd0e8400-e29b-41d4-a716-446655440008",
    "vb_session_id": "cc0e8400-e29b-41d4-a716-446655440007",
    "venture_builder_id": "770e8400-e29b-41d4-a716-446655440002",
    "created_by_user_id": "880e8400-e29b-41d4-a716-446655440003",
    "main_outcomes": "Discussed product-market fit",
    "key_takeaways": "Focus on enterprise customers",
    "next_steps": "Complete customer interviews",
    "visible_to_user": true,
    "created_at": "2024-12-30T15:30:00Z",
    "updated_at": "2024-12-30T15:30:00Z"
  },
  "error": null
}
```

**Error Response (404 Not Found):**
```json
{
  "success": false,
  "data": null,
  "error": "Session note not found or not visible"
}
```

### Get Session Note for VB (VB)

**Endpoint:** `GET /api/venture-builder/notes/session/{session_id}/vb`

**Authentication:** VB or Admin required

**Path Parameters:**
- `session_id` (UUID, required): Session ID

**Description:** Get all notes for a specific session (including private notes).

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "id": "dd0e8400-e29b-41d4-a716-446655440008",
    "vb_session_id": "cc0e8400-e29b-41d4-a716-446655440007",
    "venture_builder_id": "770e8400-e29b-41d4-a716-446655440002",
    "created_by_user_id": "880e8400-e29b-41d4-a716-446655440003",
    "main_outcomes": "Discussed product-market fit",
    "key_takeaways": "Focus on enterprise customers",
    "next_steps": "Complete customer interviews",
    "visible_to_user": false,
    "created_at": "2024-12-30T15:30:00Z",
    "updated_at": "2024-12-30T15:30:00Z"
  },
  "error": null
}
```

**Error Response (404 Not Found):**
```json
{
  "success": false,
  "data": null,
  "error": "Session note not found"
}
```

### Get Tenant Coaching Notes for User (User)

**Endpoint:** `GET /api/venture-builder/notes/tenant/user`

**Authentication:** User required

**Description:** Get all coaching notes for user's tenant (only visible notes).

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "id": "dd0e8400-e29b-41d4-a716-446655440008",
      "vb_session_id": "cc0e8400-e29b-41d4-a716-446655440007",
      "venture_builder_id": "770e8400-e29b-41d4-a716-446655440002",
      "created_by_user_id": "880e8400-e29b-41d4-a716-446655440003",
      "main_outcomes": "Session 1 outcomes",
      "key_takeaways": "Session 1 takeaways",
      "next_steps": "Session 1 next steps",
      "visible_to_user": true,
      "created_at": "2024-12-30T15:30:00Z",
      "updated_at": "2024-12-30T15:30:00Z"
    }
  ],
  "error": null
}
```

### Get Tenant Coaching Notes for VB (VB)

**Endpoint:** `GET /api/venture-builder/notes/tenant/vb`

**Authentication:** VB or Admin required

**Description:** Get all coaching notes for tenant (including private notes).

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "id": "dd0e8400-e29b-41d4-a716-446655440008",
      "vb_session_id": "cc0e8400-e29b-41d4-a716-446655440007",
      "venture_builder_id": "770e8400-e29b-41d4-a716-446655440002",
      "created_by_user_id": "880e8400-e29b-41d4-a716-446655440003",
      "main_outcomes": "Private notes",
      "key_takeaways": "Internal observations",
      "next_steps": "Follow-up actions",
      "visible_to_user": false,
      "created_at": "2024-12-30T15:30:00Z",
      "updated_at": "2024-12-30T15:30:00Z"
    }
  ],
  "error": null
}
```

---

## Earnings

### Get My Earnings (VB)

**Endpoint:** `GET /api/venture-builder/earnings`

**Authentication:** VB or Admin required

**Query Parameters:**
- `start_date` (datetime, optional): Filter earnings from this date
- `end_date` (datetime, optional): Filter earnings until this date

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "total_earned_credits": 1000,
    "total_earnings_usd": 1000.00,
    "commission_amount_usd": 150.00,
    "net_earnings_usd": 850.00,
    "total_reconciled_payments": 500.00,
    "pending_amount_usd": 350.00,
    "completed_sessions_period": 10,
    "total_sessions_all_time": 25,
    "sessions": [
      {
        "id": "cc0e8400-e29b-41d4-a716-446655440007",
        "session_datetime": "2024-12-30T14:00:00Z",
        "credits_charged": 100,
        "earnings_usd": 100.00,
        "commission_usd": 15.00,
        "net_earnings_usd": 85.00,
        "status": "completed"
      }
    ],
    "date_range_start": "2024-01-01",
    "date_range_end": "2024-12-31"
  },
  "error": null
}
```

**Error Response (404 Not Found):**
```json
{
  "success": false,
  "data": null,
  "error": "VB profile not found"
}
```

### Get Earnings Config (Admin)

**Endpoint:** `GET /api/venture-builder/admin/earnings/config`

**Authentication:** Admin required

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "credit_to_usd_rate": 1.0,
    "commission_rate": 0.15,
    "updated_at": "2024-01-01T00:00:00Z"
  },
  "error": null
}
```

**Error Response (403 Forbidden):**
```json
{
  "success": false,
  "data": null,
  "error": "Admin access required"
}
```

### Update Earnings Config (Admin)

**Endpoint:** `PATCH /api/venture-builder/admin/earnings/config`

**Authentication:** Admin required

**Request Body:**
```json
{
  "credit_to_usd_rate": 1.0,
  "commission_rate": 0.15
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "credit_to_usd_rate": 1.0,
    "commission_rate": 0.15,
    "updated_at": "2024-12-26T12:00:00Z"
  },
  "error": null
}
```

**Error Response (400 Bad Request):**
```json
{
  "success": false,
  "data": null,
  "error": "Commission rate must be between 0 and 1"
}
```

---

## Reconciliation

The reconciliation system allows admins to settle payments with Venture Builders. When reconciliation occurs:
1. Pending earnings are calculated and recorded
2. VB's total reconciled lifetime amount is updated
3. **Completed sessions are marked as SETTLED**
4. Audit trail is created for financial reporting

### Reconcile VB Payments (Admin)

**Endpoint:** `POST /api/venture-builder/admin/vb/{vb_id}/reconcile`

**Authentication:** Admin required

**Path Parameters:**
- `vb_id` (UUID, required): Venture Builder ID

**Request Body:**
```json
{
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2024-12-31T23:59:59Z",
  "notes": "Q4 2024 payment settlement"
}
```

**Note:** All fields are optional. If no date range is provided, reconciles ALL pending earnings (pending → 0). With date range, reconciles only sessions within that date range.

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "reconciliation_id": "ee0e8400-e29b-41d4-a716-446655440009",
    "venture_builder_id": "770e8400-e29b-41d4-a716-446655440002",
    "amount_reconciled_usd": 850.00,
    "pending_amount_before": 850.00,
    "pending_amount_after": 0.00,
    "session_count": 10,
    "sessions_marked_settled": 10,
    "total_reconciled_lifetime": 5000.00,
    "start_date": "2024-01-01T00:00:00Z",
    "end_date": "2024-12-31T23:59:59Z",
    "notes": "Q4 2024 payment settlement",
    "created_at": "2024-12-26T12:00:00Z"
  },
  "error": null
}
```

**Error Response (404 Not Found):**
```json
{
  "success": false,
  "data": null,
  "error": "VB profile not found"
}
```

**Error Response (400 Bad Request):**
```json
{
  "success": false,
  "data": null,
  "error": "No pending earnings to reconcile for the specified period"
}
```

### Get VB Reconciliation History (Admin)

**Endpoint:** `GET /api/venture-builder/admin/vb/{vb_id}/reconciliations`

**Authentication:** Admin required

**Path Parameters:**
- `vb_id` (UUID, required): Venture Builder ID

**Query Parameters:**
- `page` (integer, optional, default: 1, min: 1): Page number
- `page_size` (integer, optional, default: 20, min: 1, max: 100): Items per page

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "reconciliations": [
      {
        "id": "ee0e8400-e29b-41d4-a716-446655440009",
        "venture_builder_id": "770e8400-e29b-41d4-a716-446655440002",
        "reconciled_by": "ff0e8400-e29b-41d4-a716-446655440010",
        "reconciled_by_name": "Admin User",
        "reconciled_by_email": "admin@example.com",
        "amount_reconciled_usd": 850.00,
        "pending_amount_before": 850.00,
        "session_count": 10,
        "start_date": "2024-01-01T00:00:00Z",
        "end_date": "2024-12-31T23:59:59Z",
        "notes": "Q4 2024 payment settlement",
        "created_at": "2024-12-26T12:00:00Z"
      }
    ],
    "total_count": 50,
    "page": 1,
    "page_size": 20,
    "total_pages": 3
  },
  "error": null
}
```

**Error Response (404 Not Found):**
```json
{
  "success": false,
  "data": null,
  "error": "VB profile not found"
}
```

### Get All Reconciliations (Admin)

**Endpoint:** `GET /api/venture-builder/admin/reconciliations`

**Authentication:** Admin required

**Query Parameters:**
- `page` (integer, optional, default: 1, min: 1): Page number
- `page_size` (integer, optional, default: 20, min: 1, max: 100): Items per page

**Description:** Returns all reconciliation records across all Venture Builders.

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "reconciliations": [
      {
        "id": "ee0e8400-e29b-41d4-a716-446655440009",
        "venture_builder_id": "770e8400-e29b-41d4-a716-446655440002",
        "reconciled_by": "ff0e8400-e29b-41d4-a716-446655440010",
        "reconciled_by_name": "Admin User",
        "reconciled_by_email": "admin@example.com",
        "amount_reconciled_usd": 850.00,
        "pending_amount_before": 850.00,
        "session_count": 10,
        "start_date": "2024-01-01T00:00:00Z",
        "end_date": "2024-12-31T23:59:59Z",
        "notes": "Q4 2024 payment settlement",
        "created_at": "2024-12-26T12:00:00Z"
      }
    ],
    "total_count": 150,
    "page": 1,
    "page_size": 20,
    "total_pages": 8
  },
  "error": null
}
```

**Error Response (403 Forbidden):**
```json
{
  "success": false,
  "data": null,
  "error": "Admin access required"
}
```

---

## VB Portal - Projects

### Get VB Accessible Projects (VB)

**Endpoint:** `GET /api/venture-builder/portal/projects`

**Authentication:** VB or Admin required

**Description:** Returns all projects where the VB has active or completed sessions (read-only access).

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "id": "990e8400-e29b-41d4-a716-446655440004",
      "name": "Mobile App Project",
      "tenant_id": "aa0e8400-e29b-41d4-a716-446655440005",
      "description": "E-commerce mobile application",
      "created_at": "2024-11-01T10:00:00Z"
    },
    {
      "id": "bb0e8400-e29b-41d4-a716-446655440006",
      "name": "SaaS Platform",
      "tenant_id": "aa0e8400-e29b-41d4-a716-446655440005",
      "description": "B2B SaaS platform for team collaboration",
      "created_at": "2024-10-15T10:00:00Z"
    }
  ],
  "error": null
}
```

**Error Response (404 Not Found):**
```json
{
  "success": false,
  "data": null,
  "error": "VB profile not found"
}
```

---

## Disputes

### Check If Can Open Dispute (User)

**Endpoint:** `GET /api/venture-builder/sessions/{session_id}/can-dispute`

**Authentication:** User required

**Path Parameters:**
- `session_id` (UUID, required): Session ID

**Success Response (200 OK - Can dispute):**
```json
{
  "success": true,
  "data": {
    "can_open_dispute": true,
    "reason": null
  },
  "error": null
}
```

**Success Response (200 OK - Cannot dispute):**
```json
{
  "success": true,
  "data": {
    "can_open_dispute": false,
    "reason": "Session must be completed before opening a dispute"
  },
  "error": null
}
```

### Create Dispute (User)

**Endpoint:** `POST /api/venture-builder/sessions/{session_id}/disputes`

**Authentication:** User required

**Path Parameters:**
- `session_id` (UUID, required): Session ID

**Request Body:**
```json
{
  "reason": "missed_session",
  "custom_reason": null,
  "description": "The venture builder did not show up for our scheduled session at 2pm. I waited for 30 minutes but received no communication."
}
```

**Reason options:**
- `missed_session`: VB no-show
- `time_theft`: VB arrived late or ended early
- `other`: Custom reason (must provide `custom_reason`)

**Success Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "id": "120e8400-e29b-41d4-a716-446655440011",
    "session_id": "cc0e8400-e29b-41d4-a716-446655440007",
    "tenant_id": "aa0e8400-e29b-41d4-a716-446655440005",
    "created_by_user_id": "880e8400-e29b-41d4-a716-446655440003",
    "reason": "missed_session",
    "custom_reason": null,
    "description": "The venture builder did not show up for our scheduled session at 2pm. I waited for 30 minutes but received no communication.",
    "status": "submitted",
    "admin_notes": null,
    "resolved_by": null,
    "resolved_at": null,
    "created_at": "2024-12-30T14:35:00Z",
    "updated_at": "2024-12-30T14:35:00Z"
  },
  "error": null
}
```

**Error Response (409 Conflict):**
```json
{
  "success": false,
  "data": null,
  "error": "A dispute already exists for this session"
}
```

**Error Response (400 Bad Request):**
```json
{
  "success": false,
  "data": null,
  "error": "Session must be completed before opening a dispute"
}
```

**Error Response (400 Bad Request - Missing custom reason):**
```json
{
  "success": false,
  "data": null,
  "error": "custom_reason is required when reason is 'other'"
}
```

### Get My Disputes (User)

**Endpoint:** `GET /api/venture-builder/disputes`

**Authentication:** User required

**Query Parameters:**
- `page` (integer, optional, default: 1, min: 1): Page number
- `page_size` (integer, optional, default: 20, min: 1, max: 100): Items per page

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "disputes": [
      {
        "id": "120e8400-e29b-41d4-a716-446655440011",
        "session_id": "cc0e8400-e29b-41d4-a716-446655440007",
        "tenant_id": "aa0e8400-e29b-41d4-a716-446655440005",
        "created_by_user_id": "880e8400-e29b-41d4-a716-446655440003",
        "reason": "missed_session",
        "custom_reason": null,
        "description": "VB did not show up",
        "status": "under_review",
        "admin_notes": "Investigating the issue",
        "resolved_by": null,
        "resolved_at": null,
        "created_at": "2024-12-30T14:35:00Z",
        "updated_at": "2024-12-30T15:00:00Z"
      }
    ],
    "total_count": 3,
    "page": 1,
    "page_size": 20,
    "total_pages": 1
  },
  "error": null
}
```

### Get Dispute Detail (User)

**Endpoint:** `GET /api/venture-builder/disputes/{dispute_id}`

**Authentication:** User required

**Path Parameters:**
- `dispute_id` (UUID, required): Dispute ID

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "id": "120e8400-e29b-41d4-a716-446655440011",
    "session_id": "cc0e8400-e29b-41d4-a716-446655440007",
    "tenant_id": "aa0e8400-e29b-41d4-a716-446655440005",
    "created_by_user_id": "880e8400-e29b-41d4-a716-446655440003",
    "reason": "missed_session",
    "custom_reason": null,
    "description": "VB did not show up for scheduled session",
    "status": "resolved",
    "admin_notes": "Credits refunded, VB received warning",
    "resolved_by": "ff0e8400-e29b-41d4-a716-446655440010",
    "resolved_at": "2024-12-30T16:00:00Z",
    "created_at": "2024-12-30T14:35:00Z",
    "updated_at": "2024-12-30T16:00:00Z"
  },
  "error": null
}
```

**Error Response (404 Not Found):**
```json
{
  "success": false,
  "data": null,
  "error": "Dispute not found"
}
```

**Error Response (403 Forbidden):**
```json
{
  "success": false,
  "data": null,
  "error": "You can only view your own disputes"
}
```

### Get All Disputes (Admin)

**Endpoint:** `GET /api/venture-builder/admin/disputes`

**Authentication:** Admin required

**Query Parameters:**
- `status` (string, optional): Filter by status (submitted, under_review, resolved)
- `vb_id` (UUID, optional): Filter by venture builder
- `start_date` (datetime, optional): Filter disputes created after this date
- `end_date` (datetime, optional): Filter disputes created before this date
- `page` (integer, optional, default: 1, min: 1): Page number
- `page_size` (integer, optional, default: 20, min: 1, max: 100): Items per page

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "disputes": [
      {
        "id": "120e8400-e29b-41d4-a716-446655440011",
        "session_id": "cc0e8400-e29b-41d4-a716-446655440007",
        "tenant_id": "aa0e8400-e29b-41d4-a716-446655440005",
        "created_by_user_id": "880e8400-e29b-41d4-a716-446655440003",
        "reason": "missed_session",
        "custom_reason": null,
        "description": "VB did not show up",
        "status": "submitted",
        "admin_notes": null,
        "resolved_by": null,
        "resolved_at": null,
        "created_at": "2024-12-30T14:35:00Z",
        "updated_at": "2024-12-30T14:35:00Z",
        "session_datetime": "2024-12-30T14:00:00Z",
        "vb_name": "John Doe",
        "user_email": "user@example.com"
      }
    ],
    "total_count": 15,
    "page": 1,
    "page_size": 20,
    "total_pages": 1
  },
  "error": null
}
```

**Error Response (403 Forbidden):**
```json
{
  "success": false,
  "data": null,
  "error": "Admin access required"
}
```

### Update Dispute (Admin)

**Endpoint:** `PATCH /api/venture-builder/admin/disputes/{dispute_id}`

**Authentication:** Admin required

**Path Parameters:**
- `dispute_id` (UUID, required): Dispute ID

**Request Body (all fields optional):**
```json
{
  "status": "resolved",
  "admin_notes": "Investigated and resolved in favor of user. Credits refunded, VB received warning."
}
```

**Status options:**
- `submitted`: Initial state
- `under_review`: Admin is reviewing
- `resolved`: Dispute resolved

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "id": "120e8400-e29b-41d4-a716-446655440011",
    "session_id": "cc0e8400-e29b-41d4-a716-446655440007",
    "tenant_id": "aa0e8400-e29b-41d4-a716-446655440005",
    "created_by_user_id": "880e8400-e29b-41d4-a716-446655440003",
    "reason": "missed_session",
    "custom_reason": null,
    "description": "VB did not show up",
    "status": "resolved",
    "admin_notes": "Investigated and resolved in favor of user. Credits refunded, VB received warning.",
    "resolved_by": "ff0e8400-e29b-41d4-a716-446655440010",
    "resolved_at": "2024-12-30T16:00:00Z",
    "created_at": "2024-12-30T14:35:00Z",
    "updated_at": "2024-12-30T16:00:00Z"
  },
  "error": null
}
```

**Error Response (404 Not Found):**
```json
{
  "success": false,
  "data": null,
  "error": "Dispute not found"
}
```

**Error Response (400 Bad Request):**
```json
{
  "success": false,
  "data": null,
  "error": "Invalid status transition"
}
```

---

## Database Schema

### Key Tables

#### `venture_builders`
- VB profiles with biography, work experience, pricing
- Includes `total_reconciled_payments` for tracking lifetime earnings
- Status: pending_profile, pending_admin_review, active, inactive

#### `vb_sessions`
- Session bookings with datetime, credits, status
- Status: confirmed, completed, **settled**, canceled
- Cascades on VB deletion

#### `vb_session_notes`
- Coaching notes with outcomes, takeaways, next steps
- Visibility control (`visible_to_user`)

#### `vb_reconciliations`
- Payment reconciliation records
- Tracks amount reconciled, session count, date range
- Links to admin user who performed reconciliation

#### `vb_disputes`
- User dispute submissions
- Status: submitted, under_review, resolved
- Reason: missed_session, time_theft, other

#### `vb_earnings_config`
- Global configuration for credit-to-USD rate and commission
- Single row table

### Views

#### `vb_with_expertise`
- Joins VB profiles with their expertise areas (JSON aggregation)

#### `vb_session_details`
- Session details with VB info and note existence flag

#### `vb_reconciliation_history`
- Reconciliation records with admin user details

#### `vb_disputes_with_details`
- Disputes with session and user information

---

## Migration Guide

### Running Migrations

1. **Initial VB Schema**:
   ```sql
   -- Run the main VB schema migration
   -- (Located in your migrations folder)
   ```

2. **Reconciliation Schema**:
   ```bash
   # Apply the reconciliation migration
   psql -d your_database -f src/mint/api/venture_builder/migrations/vb_reconciliation_schema.sql
   ```

This migration adds:
- `settled` status to `vb_session_status` enum
- `total_reconciled_payments` column to `venture_builders`
- `vb_reconciliations` table
- `vb_reconciliation_history` view

### Database Enum Update

The migration safely adds the `settled` status to the existing `vb_session_status` enum:

```sql
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum
        WHERE enumlabel = 'settled'
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'vb_session_status')
    ) THEN
        ALTER TYPE public.vb_session_status ADD VALUE 'settled';
    END IF;
END$$;
```

---

## Architecture Notes

### Service Layer (`service.py`)
- Business logic and validation
- Credit integration with `CreditService`
- Email notifications via `email_service`
- Token generation/validation with `serializer`

### Data Access Layer (`data_access.py`)
- Direct Supabase client usage
- Service role for admin operations
- `mark_sessions_as_settled()` for bulk status updates

### Exception Handling

The Venture Builder API uses a **global exception handler** (`vb_exception_handler` in `utils.py`) that ensures all errors return a consistent format:

```json
{
  "success": false,
  "data": null,
  "error": "Error message"
}
```

**Exception-to-Status Code Mapping:**
- `VBValidationError` → 400 Bad Request
- `VBNotFoundError` → 404 Not Found
- `VBAccessDeniedError` → 403 Forbidden
- `VBInsufficientCreditsError` → 402 Payment Required
- `VBBookingConflictError` → 409 Conflict
- `VBDisputeAlreadyExistsError` → 409 Conflict
- `VBDisputeNotEligibleError` → 400 Bad Request
- `VBProfileIncompleteError` → 422 Unprocessable Entity
- `VBStatusError` → 400 Bad Request

The exception handler is registered globally in `main_app.py` using:
```python
app.add_exception_handler(VBBaseException, vb_exception_handler)
```

This ensures **all VB endpoints** automatically return standardized error responses without needing try-catch blocks in individual route handlers.

---

## Recent Changes

### Response Standardization (December 2024)

**Status:** ✅ Complete

All Venture Builder API endpoints now return a consistent response format with `success`, `data`, and `error` fields.

**Success Response:**
```json
{
  "success": true,
  "data": { /* endpoint data */ },
  "error": null
}
```

**Error Response:**
```json
{
  "success": false,
  "data": null,
  "error": "Error message"
}
```

**Implementation:**
- Added global `vb_exception_handler` in `utils.py`
- Registered handler in `main_app.py`
- All VB exceptions automatically return standardized format
- No try-catch blocks needed in route handlers

**Breaking Changes:**
- Error responses changed from `{"detail": "message"}` to `{"success": false, "data": null, "error": "message"}`
- Clients should check `success` field and read `error` field instead of `detail`

### Reconciliation Feature (December 2024)

**What's New:**
1. **SETTLED Session Status**: Sessions are marked as settled when payments are reconciled
2. **Reconciliation API**: Admins can reconcile VB payments with optional date range filtering
3. **Audit Trail**: Complete history of all reconciliation events
4. **Lifetime Tracking**: VB's `total_reconciled_payments` tracks cumulative earnings

**Breaking Changes:**
- None - backward compatible

**Migration Required:**
- Yes - run `vb_reconciliation_schema.sql` to add new tables and enum values

---

## Support & Documentation

For questions or issues:
1. Check this README for API documentation
2. Review the code comments in `service.py` and `data_access.py`
3. Consult the migration SQL files for schema details

---

**Last Updated**: December 2024
**Feature Version**: 2.0 (with Reconciliation)
