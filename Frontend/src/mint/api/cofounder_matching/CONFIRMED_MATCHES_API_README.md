# Confirmed Matches API - Frontend Integration Guide

## Overview
Get the current user's confirmed matches from the matching algorithm. These are users who have been algorithmically matched based on compatibility scores.

**Base URL:** `/profiles/me`

---

## Authentication
Requires JWT token:
```
Authorization: Bearer <token>
```

**Requirements:**
- User must be logged in
- User's profile must be approved
- Non-approved users get error response with empty matches

---

## Endpoint

### Get Confirmed Matches
**GET** `/profiles/me/confirmed-matches`

#### Query Parameters
```typescript
{
  page?: number       // default: 1, minimum: 1
  page_size?: number  // default: 20, range: 1-100
}
```

#### Response (200 OK)
```typescript
{
  total: number
  page: number
  page_size: number
  total_pages: number
  matches: Array<{
    match_id: string              // ID from user_relationships table
    user_id: string               // Matched user's ID
    relationship: string          // "matched"
    match_score: number | null    // Compatibility score (0-100)
    matched_at: string | null     // ISO timestamp when match was created
    profile_data: {
      id: string
      profile_id: string
      version: number
      status: string
      first_name: string
      last_name: string
      full_name: string           // "{first_name} {last_name}"
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
  }>
}
```

#### Response (Non-Approved User)
```typescript
{
  error: "Only users with approved profiles can access confirmed matches"
  total: 0
  matches: []
  page: number
  page_size: number
  total_pages: 0
}
```

---

## Important Notes

1. **Pagination**: `offset = (page - 1) * page_size`
2. **Match Score**: Algorithmic compatibility score (0-100), may be null
3. **Relationship**: Always "matched" for this endpoint
4. **Profile Data**: Full profile version data of matched user
5. **Languages**: Enriched with full details from profile_languages table
6. **Ordering**: Matches ordered by most recently updated first

---

## Error Responses

### 401 Unauthorized
```json
{"detail": "Invalid or missing token"}
```

### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["query", "page"],
      "msg": "ensure this value is greater than or equal to 1",
      "type": "value_error"
    }
  ]
}
```
