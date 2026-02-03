# "Other" Option for Enum Fields

## Overview

Users can now select "Other" for dropdown fields and enter custom values. Admins can convert these suggestions into official enum options.

---

## User-Facing Changes

### Profile Submission - New Optional Fields

When saving a draft (`POST /profiles/me/save-draft`), you can now include:

```json
{
  // Standard fields...
  "industries_of_interest": ["Technology", "Healthcare"],
  "responsibilities_offered": ["Marketing", "Sales"],
  "venture_stage": ["Idea Stage"],
  "preferred_venture_stage": ["Growth Stage"],
  "expected_commitment": "Full-time",
  "preferred_commitment": "Part-time",

  // NEW: "Other" custom values
  "other_industries": ["Quantum Computing", "Space Tech"],
  "other_responsibilities": ["Community Building"],
  "other_venture_stages": ["Pre-seed Fundraising"],
  "other_preferred_venture_stages": ["Series A"],
  "other_languages": ["Swahili", "Tagalog"],
  "other_expected_commitment": "Flexible Hours",
  "other_preferred_commitment": "Remote Only"
}
```

### Rules

- All `other_*` fields are **optional**
- `other_industries`, `other_responsibilities`, `other_venture_stages`, `other_preferred_venture_stages`, `other_languages` are **arrays**
- `other_expected_commitment`, `other_preferred_commitment` are **single strings**
- Values are automatically tracked as suggestions for admin review

---

## Admin Endpoints

Base path: `/profiles/admin/enum-suggestions`

### 1. List Suggestions

```
GET /profiles/admin/enum-suggestions/
```

**Query Params**:
- `enum_type` (optional): `industries` | `responsibilities` | `venture_stages` | `commitments` | `languages`
- `status` (optional, default: `pending`): `pending` | `approved` | `rejected`
- `page` (default: 1)
- `page_size` (default: 50, max: 200)
- `order_by` (default: `times_suggested`)

**Response**:
```json
{
  "total": 42,
  "items": [
    {
      "id": "uuid",
      "enum_type": "industries",
      "field_context": null,
      "suggested_value": "Quantum Computing",
      "suggested_by": "user_uuid",
      "profile_version_id": "version_uuid",
      "times_suggested": 15,
      "status": "pending",
      "created_at": "2025-01-15T10:00:00Z",
      "updated_at": "2025-01-15T10:00:00Z"
    }
  ]
}
```

---

### 2. Get Statistics

```
GET /profiles/admin/enum-suggestions/stats
```

**Response**:
```json
{
  "items": [
    {
      "enum_type": "industries",
      "status": "pending",
      "count": 12,
      "total_suggestions": 47
    }
  ]
}
```

---

### 3. Get Top Suggestions

```
GET /profiles/admin/enum-suggestions/top?limit=10
```

Returns most frequently suggested values (pending only).

---

### 4. Get Suggestions by Type

```
GET /profiles/admin/enum-suggestions/by-type/{enum_type}?status=pending&limit=50
```

**Path Params**:
- `enum_type`: `industries` | `responsibilities` | `venture_stages` | `commitments` | `languages`

---

### 5. Get Specific Suggestion

```
GET /profiles/admin/enum-suggestions/{suggestion_id}
```

---

### 6. Approve Suggestion

```
POST /profiles/admin/enum-suggestions/{suggestion_id}/approve
```

**Body**:
```json
{
  "enum_name": "Quantum Computing",
  "enum_description": "Quantum computing and quantum information science",
  "admin_notes": "Popular request from 15 users"
}
```

**Response**:
```json
{
  "ok": true,
  "enum_id": "new_enum_uuid",
  "message": "Suggestion approved and 'Quantum Computing' added to enum options"
}
```

**What happens**:
1. Creates new enum entry in appropriate table
2. Updates all profiles with this "other" value to use the official enum
3. New value appears in dropdown immediately

---

### 7. Reject Suggestion

```
POST /profiles/admin/enum-suggestions/{suggestion_id}/reject
```

**Body**:
```json
{
  "admin_notes": "Too specific, use existing 'Technology' category"
}
```

**Response**:
```json
{
  "ok": true,
  "message": "Suggestion rejected"
}
```
