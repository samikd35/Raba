# Admin API - Frontend Integration Guide

## Overview
Admin endpoints for managing profile submissions and matching algorithm thresholds.

**Base URL:** `/profiles/admin`

---

## Authentication
All endpoints require JWT token with admin or super admin role:
```
Authorization: Bearer <token>
```

**Role Requirements:**
- **Admin**: Most endpoints
- **Super Admin**: Delete operations only

---

## Profile Version Management

### 1. List Profile Submissions
**GET** `/profiles/admin/profile-versions`

#### Query Parameters
```typescript
{
  status?: string   // default: "submitted", options: "submitted" | "approved" | "rejected"
  limit?: number    // default: 50, range: 1-200
}
```

#### Response (200 OK)
```typescript
{
  items: Array<{
    id: string
    profile_id: string
    version: number
    status: string
    first_name: string
    last_name: string
    email: string
    date_of_birth: string
    profile_picture_url: string | null
    country: string
    linkedin_url: string
    website_url: string | null
    professional_background: string
    industries_of_interest: string[]
    responsibilities_offered: string[]
    skills_needed: string[]
    preferred_languages: Array<{
      id: string
      name: string
      slug: string
      code: string
      importance: "must_have" | "nice_to_have"
    }>
    preferred_country: string
    preferred_country_importance: "must_have" | "nice_to_have"
    expected_commitment: string
    preferred_commitment: string
    commitment_importance: "must_have" | "nice_to_have"
    venture_stage: string[]
    preferred_venture_stage: string[]
    age_enabled: boolean
    age_min: number | null
    age_max: number | null
    age_importance: "must_have" | "nice_to_have" | null
    submitted_at: string | null
    reviewed_at: string | null
    review_reason: string | null
    created_at: string
    updated_at: string
  }>
}
```

---

### 2. Approve Profile Version
**POST** `/profiles/admin/profile-versions/{version_id}/approve`

#### Response (200 OK)
```typescript
{
  ok: boolean
  matches_created: number   // Number of automatic matches created for this profile
}
```

**Side Effects:**
- Sets profile version status to "approved"
- Adds profile to `approved_candidates` table
- Runs matching algorithm automatically
- Sends email notifications to newly approved user and all matched users

---

### 3. Reject Profile Version
**POST** `/profiles/admin/profile-versions/{version_id}/reject`

#### Request Body
```typescript
{
  reason: string   // Required: Rejection reason
}
```

#### Response (200 OK)
```typescript
{
  ok: boolean
}
```

---

## Matching Threshold Management

### 4. Create Matching Threshold
**POST** `/profiles/admin/matching-thresholds`

#### Request Body
```typescript
{
  name: string                 // Required, 1-100 characters, unique name
  description?: string | null  // Optional description
  threshold_score: number      // Required, 0-100, minimum match score
  is_active: boolean          // default: false
}
```

#### Response (200 OK)
```typescript
{
  id: string
  name: string
  description: string | null
  threshold_score: number
  is_active: boolean
  created_at: string
  updated_at: string
  created_by: string | null
  updated_by: string | null
  metadata: object | null
}
```

---

### 5. List Matching Thresholds
**GET** `/profiles/admin/matching-thresholds`

#### Query Parameters
```typescript
{
  limit?: number   // default: 50, range: 1-200
  offset?: number  // default: 0, minimum: 0
}
```

#### Response (200 OK)
```typescript
{
  data: Array<{
    id: string
    name: string
    description: string | null
    threshold_score: number
    is_active: boolean
    created_at: string
    updated_at: string
    created_by: string | null
    updated_by: string | null
    metadata: object | null
  }>
  count: number   // Total count of thresholds
}
```

---

### 6. Get Active Threshold
**GET** `/profiles/admin/matching-thresholds/active`

#### Response (200 OK)
```typescript
{
  id: string
  name: string
  description: string | null
  threshold_score: number
  is_active: boolean
  created_at: string
  updated_at: string
  created_by: string | null
  updated_by: string | null
  metadata: object | null
} | null   // Returns null if no active threshold
```

---

### 7. Get Specific Threshold
**GET** `/profiles/admin/matching-thresholds/{threshold_id}`

#### Response (200 OK)
```typescript
{
  id: string
  name: string
  description: string | null
  threshold_score: number
  is_active: boolean
  created_at: string
  updated_at: string
  created_by: string | null
  updated_by: string | null
  metadata: object | null
}
```

---

### 8. Update Matching Threshold
**PATCH** `/profiles/admin/matching-thresholds/{threshold_id}`

#### Request Body
```typescript
{
  name?: string           // Optional, 1-100 characters
  description?: string    // Optional
  threshold_score?: number // Optional, 0-100
  is_active?: boolean     // Optional
}
```

#### Response (200 OK)
```typescript
{
  id: string
  name: string
  description: string | null
  threshold_score: number
  is_active: boolean
  created_at: string
  updated_at: string
  created_by: string | null
  updated_by: string | null
  metadata: object | null
}
```

---

### 9. Activate Threshold
**POST** `/profiles/admin/matching-thresholds/{threshold_id}/activate`

#### Response (200 OK)
```typescript
{
  id: string
  name: string
  description: string | null
  threshold_score: number
  is_active: boolean
  created_at: string
  updated_at: string
  created_by: string | null
  updated_by: string | null
  metadata: object | null
}
```

**Note:** Activating a threshold automatically deactivates all other thresholds (enforced by database trigger).

---

### 10. Deactivate Threshold
**POST** `/profiles/admin/matching-thresholds/{threshold_id}/deactivate`

#### Response (200 OK)
```typescript
{
  id: string
  name: string
  description: string | null
  threshold_score: number
  is_active: boolean
  created_at: string
  updated_at: string
  created_by: string | null
  updated_by: string | null
  metadata: object | null
}
```

---

### 11. Delete Threshold (Super Admin Only)
**DELETE** `/profiles/admin/matching-thresholds/{threshold_id}`

#### Response (200 OK)
```typescript
{
  ok: boolean
  deleted_count: number
}
```

**Role Required:** Super Admin

---

## Error Responses

### 401 Unauthorized
```json
{"detail": "Invalid or missing token"}
```

### 403 Forbidden
```json
{"detail": "Insufficient permissions"}
```

### 404 Not Found
```json
{"detail": "Resource not found"}
```

### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "field_name"],
      "msg": "error message",
      "type": "error_type"
    }
  ]
}
```

---

## Important Notes

### Profile Approval Process
1. Admin approves profile version → status changes to "approved"
2. Profile added to `approved_candidates` table automatically
3. Matching algorithm runs for the newly approved profile
4. User relationships created for matches above threshold
5. Email notifications sent to approved user and matched users

### Matching Thresholds
- **Only one threshold can be active at a time** (database enforced)
- Threshold score determines minimum compatibility for automatic matches
- Range: 0-100 (typically 70-85 for quality matches)
- Activating a threshold deactivates all others automatically

### Audit Trail
- All threshold operations track `created_by` and `updated_by`
- Profile version reviews track `reviewed_at` timestamp
- Rejected profiles store `review_reason` for transparency
