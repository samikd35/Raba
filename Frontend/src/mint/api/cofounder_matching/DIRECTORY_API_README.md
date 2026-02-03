# Directory API - Frontend Integration Guide

## Overview
Search and view approved co-founder profiles with advanced filtering.

**Base URL:** `/profiles`

---

## Authentication
All endpoints require JWT token:
```
Authorization: Bearer <token>
```

**Requirements:**
- User must be logged in
- User's profile must be approved
- Non-approved users get `403 Forbidden`

---

## Endpoints

### 1. Search Directory
**POST** `/profiles/directory/search`

#### Request Body
```typescript
{
  countries?: string[]              // lowercase country names
  languages?: string[]              // language IDs (UUIDs) from profile_languages table
  age_min?: number                  // 0-120
  age_max?: number                  // 0-120
  preferred_commitment?: string     // "Full-time" | "Part-time"
  preferred_venture_stage?: string[] // ["have ideas but open to explore"] | ["devoted to a venture"]
  page: number                      // default: 1
  limit: number                     // 1-1000, default: 20
}
```

#### Response (200 OK)
```typescript
{
  total: number
  page: number
  total_pages: number
  limit: number
  offset: number
  items: Array<{
    user_id: string
    profile_id: string
    version_id: string
    full_name: string | null
    country: string | null
    date_of_birth: string | null
    profile_picture_url: string | null
    professional_background: string | null
  }>
}
```

---

### 2. Get Profile Version Details
**GET** `/profiles/directory/versions/{version_id}`

#### Response (200 OK)
```typescript
{
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
  created_at: string
  updated_at: string
}
```

---

## Getting Enum Values

### Languages
**GET** `/profiles/enums/languages?page=1&page_size=100`

Use `id` field for filtering.

### Commitments
**GET** `/profiles/enums/commitment?page=1&page_size=100`

Use `name` field for filtering ("Full-time", "Part-time").

### Venture Stages
**GET** `/profiles/enums/venture_stages?page=1&page_size=100`

Use `name` field for filtering:
- "have ideas but open to explore"
- "devoted to a venture"

#### Enum Response Format
```typescript
{
  success: boolean
  message: string
  total: number
  page: number
  page_size: number
  data: Array<{
    id: string
    name: string
    slug: string
    description: string | null
    is_active: boolean
    created_at: string
    updated_at: string
  }>
}
```

---

## Error Responses

### 401 Unauthorized
```json
{"detail": "Invalid or missing token"}
```

### 403 Forbidden
```json
{"detail": "Directory visible only to approved users"}
```

### 404 Not Found
```json
{"detail": "Version not found"}
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

## Filter Behavior

- **countries**: Case-insensitive, matches ANY country in list
- **languages**: Matches if user has ANY language ID in list
- **age_min/age_max**: Inclusive range from date_of_birth
- **preferred_commitment**: Exact match
- **preferred_venture_stage**: Matches if ANY stage overlaps
- **Empty arrays = no filter**

---

## Important Notes

1. **Countries**: lowercase (e.g., "united states")
2. **Languages**: Use UUIDs from profile_languages table
3. **Venture Stages**: Use exact names:
   - "have ideas but open to explore"
   - "devoted to a venture"
4. **Commitment**: "Full-time" or "Part-time"
5. **Pagination**: `offset = (page - 1) * limit`
