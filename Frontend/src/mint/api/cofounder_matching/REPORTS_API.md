# Cofounder Matching - Reporting API Documentation

## Overview

The Reporting API allows users to report inappropriate profiles and messages, and provides admin endpoints for managing and resolving reports.

**Base URL**: `/profiles/reports`

---

## User Endpoints

### 1. Report a Profile

Report a profile for policy violations.

**Endpoint**: `POST /profiles/reports/profile`

**Authentication**: Required (Bearer token)

**Request Body**:
```json
{
  "reported_profile_id": "550e8400-e29b-41d4-a716-446655440000",
  "reason": "SPAM_OR_SCAM",
  "description": "This profile is soliciting investment scams"
}
```

**Parameters**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `reported_profile_id` | UUID | Yes | ID of the profile being reported |
| `reason` | String (Enum) | Yes | Reason for reporting (see reasons below) |
| `description` | String | Conditional | Required if reason is "OTHER", optional otherwise |

**Report Reasons**:
- `SPAM_OR_SCAM` - Spam or scam content
- `HARASSMENT_OR_HATE` - Harassment or hate speech
- `MISREPRESENTATION` - False information or impersonation
- `OFF_PLATFORM_SOLICITATION` - Attempting to move conversation off-platform inappropriately
- `ADULT_CONTENT` - Inappropriate adult content
- `DUPLICATE_ACCOUNT` - User has multiple accounts
- `UNDERAGE_OR_NOT_FOUNDER` - User doesn't meet eligibility requirements
- `OTHER` - Other reason (requires description)

**Success Response** (200):
```json
{
  "success": true,
  "message": "Profile reported successfully",
  "data": {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "report_type": "PROFILE",
    "reporter_user_id": "user-uuid",
    "reported_profile_id": "550e8400-e29b-41d4-a716-446655440000",
    "reported_message_id": null,
    "reason": "SPAM_OR_SCAM",
    "description": "This profile is soliciting investment scams",
    "status": "PENDING",
    "admin_notes": null,
    "action_taken": null,
    "resolved_by": null,
    "resolved_at": null,
    "created_at": "2025-01-27T10:30:00Z",
    "updated_at": "2025-01-27T10:30:00Z"
  }
}
```

**Error Responses**:

**400 Bad Request** - Validation error:
```json
{
  "detail": "You cannot report your own profile"
}
```

```json
{
  "detail": "You have already reported this profile"
}
```

```json
{
  "detail": "Description is required when reason is OTHER"
}
```

**404 Not Found** - Profile doesn't exist:
```json
{
  "detail": "Reported profile not found"
}
```

---

### 2. Report a Message

Report a message for policy violations.

**Endpoint**: `POST /profiles/reports/message`

**Authentication**: Required (Bearer token)

**Request Body**:
```json
{
  "message_id": "msg-uuid-1234",
  "reason": "HARASSMENT_OR_HATE",
  "description": "This message contains threatening language"
}
```

**Parameters**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message_id` | UUID | Yes | ID of the message being reported |
| `reason` | String (Enum) | Yes | Reason for reporting (same as profile reports) |
| `description` | String | Conditional | Required if reason is "OTHER" |

**Success Response** (200):
```json
{
  "success": true,
  "message": "Message reported successfully",
  "data": {
    "id": "report-uuid",
    "report_type": "MESSAGE",
    "reporter_user_id": "user-uuid",
    "reported_profile_id": null,
    "reported_message_id": "msg-uuid-1234",
    "reason": "HARASSMENT_OR_HATE",
    "description": "This message contains threatening language",
    "status": "PENDING",
    "admin_notes": null,
    "action_taken": null,
    "resolved_by": null,
    "resolved_at": null,
    "created_at": "2025-01-27T10:30:00Z",
    "updated_at": "2025-01-27T10:30:00Z"
  }
}
```

**Error Responses**:

**400 Bad Request**:
```json
{
  "detail": "Message not found"
}
```

```json
{
  "detail": "You do not have access to this message"
}
```

```json
{
  "detail": "You cannot report your own message"
}
```

---

## Admin Endpoints

### 3. List All Reports

Get a paginated list of all reports with optional filters.

**Endpoint**: `GET /profiles/reports/`

**Authentication**: Required (Admin only)

**Query Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `status` | String | No | All | Filter by status: PENDING, REVIEWED, ACTIONED, NO_ACTION |
| `report_type` | String | No | All | Filter by type: PROFILE or MESSAGE |
| `page` | Integer | No | 1 | Page number (min: 1) |
| `page_size` | Integer | No | 50 | Items per page (min: 1, max: 100) |

**Example Request**:
```
GET /profiles/reports/?status=PENDING&report_type=PROFILE&page=1&page_size=20
```

**Success Response** (200):
```json
{
  "success": true,
  "message": "Reports retrieved successfully",
  "data": [
    {
      "id": "report-uuid-1",
      "report_type": "PROFILE",
      "reporter_user_id": "user-uuid-1",
      "reported_profile_id": "profile-uuid-1",
      "reported_message_id": null,
      "reason": "SPAM_OR_SCAM",
      "description": "Soliciting scams",
      "status": "PENDING",
      "admin_notes": null,
      "action_taken": null,
      "resolved_by": null,
      "resolved_at": null,
      "created_at": "2025-01-27T10:30:00Z",
      "updated_at": "2025-01-27T10:30:00Z"
    }
  ],
  "total": 45,
  "page": 1,
  "page_size": 20
}
```

---

### 4. Get Report Statistics

Get statistics about all reports.

**Endpoint**: `GET /profiles/reports/stats`

**Authentication**: Required (Admin only)

**Success Response** (200):
```json
{
  "total_reports": 150,
  "pending_reports": 25,
  "reviewed_reports": 40,
  "actioned_reports": 60,
  "no_action_reports": 25,
  "reports_by_reason": {
    "SPAM_OR_SCAM": 45,
    "HARASSMENT_OR_HATE": 30,
    "MISREPRESENTATION": 20,
    "OFF_PLATFORM_SOLICITATION": 15,
    "ADULT_CONTENT": 10,
    "DUPLICATE_ACCOUNT": 12,
    "UNDERAGE_OR_NOT_FOUNDER": 8,
    "OTHER": 10
  }
}
```

---

### 5. Get Reports by User

Get all reports against a specific user.

**Endpoint**: `GET /profiles/reports/by-user/{user_id}`

**Authentication**: Required (Admin only)

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `user_id` | UUID | User ID to get reports for |

**Query Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `status` | String | No | All | Filter by status |
| `page` | Integer | No | 1 | Page number |
| `page_size` | Integer | No | 50 | Items per page |

**Success Response** (200):
```json
{
  "success": true,
  "message": "Reports for user {user_id} retrieved successfully",
  "data": [...],
  "total": 5,
  "page": 1,
  "page_size": 50
}
```

---

### 6. Get Reports by Profile

Get all reports against a specific profile.

**Endpoint**: `GET /profiles/reports/by-profile/{profile_id}`

**Authentication**: Required (Admin only)

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `profile_id` | UUID | Profile ID to get reports for |

**Query Parameters**: Same as "Get Reports by User"

**Success Response** (200):
```json
{
  "success": true,
  "message": "Reports for profile {profile_id} retrieved successfully",
  "data": [...],
  "total": 3,
  "page": 1,
  "page_size": 50
}
```

---

### 7. Get Specific Report

Get details of a specific report by ID.

**Endpoint**: `GET /profiles/reports/{report_id}`

**Authentication**: Required (Admin only)

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `report_id` | UUID | Report ID |

**Success Response** (200):
```json
{
  "success": true,
  "message": "Report retrieved successfully",
  "data": {
    "id": "report-uuid",
    "report_type": "PROFILE",
    "reporter_user_id": "user-uuid-1",
    "reported_profile_id": "profile-uuid-1",
    "reported_message_id": null,
    "reason": "SPAM_OR_SCAM",
    "description": "Detailed description",
    "status": "PENDING",
    "admin_notes": null,
    "action_taken": null,
    "resolved_by": null,
    "resolved_at": null,
    "created_at": "2025-01-27T10:30:00Z",
    "updated_at": "2025-01-27T10:30:00Z"
  }
}
```

**Error Response** (404):
```json
{
  "detail": "Report not found"
}
```

---

### 8. Resolve a Report

Resolve a report and optionally take action.

**Endpoint**: `POST /profiles/reports/{report_id}/resolve`

**Authentication**: Required (Admin only)

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `report_id` | UUID | Report ID to resolve |

**Request Body**:
```json
{
  "status": "ACTIONED",
  "admin_notes": "Profile violated community guidelines. User has been warned.",
  "action_taken": "Issued warning to user and removed inappropriate content"
}
```

**Parameters**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `status` | String (Enum) | Yes | New status: REVIEWED, ACTIONED, or NO_ACTION |
| `admin_notes` | String | No | Internal admin notes |
| `action_taken` | String | No | Description of action taken (if any) |

**Status Values**:
- `REVIEWED` - Admin has reviewed but not yet taken action
- `ACTIONED` - Admin has taken action (e.g., banned user, removed content)
- `NO_ACTION` - Admin reviewed and determined no action needed

**Success Response** (200):
```json
{
  "success": true,
  "message": "Report resolved successfully",
  "data": {
    "id": "report-uuid",
    "report_type": "PROFILE",
    "reporter_user_id": "user-uuid-1",
    "reported_profile_id": "profile-uuid-1",
    "reported_message_id": null,
    "reason": "SPAM_OR_SCAM",
    "description": "Soliciting scams",
    "status": "ACTIONED",
    "admin_notes": "Profile violated community guidelines. User has been warned.",
    "action_taken": "Issued warning to user and removed inappropriate content",
    "resolved_by": "admin-uuid",
    "resolved_at": "2025-01-27T11:00:00Z",
    "created_at": "2025-01-27T10:30:00Z",
    "updated_at": "2025-01-27T11:00:00Z"
  }
}
```

**Error Responses**:

**400 Bad Request**:
```json
{
  "detail": "Report has already been resolved"
}
```

**404 Not Found**:
```json
{
  "detail": "Report not found"
}
```

---

## Business Rules

### User Restrictions

1. **No Self-Reporting**: Users cannot report their own profiles or messages
2. **No Duplicate Reports**: Users cannot create multiple pending reports for the same target
3. **Message Access**: Users can only report messages they have access to (sent or received)
4. **Description Required**: When reason is "OTHER", a description must be provided

### Admin Actions

1. **Resolve Once**: Reports can only be resolved once (status changed from PENDING)
2. **Audit Trail**: All resolution actions are tracked with admin user ID and timestamp
3. **Status Flow**: PENDING → (REVIEWED | ACTIONED | NO_ACTION)

---

## Error Handling

All endpoints follow standard HTTP status codes:

- **200 OK** - Request successful
- **400 Bad Request** - Validation error or business rule violation
- **401 Unauthorized** - Not authenticated
- **403 Forbidden** - Insufficient permissions (admin endpoints)
- **404 Not Found** - Resource not found
- **500 Internal Server Error** - Unexpected server error

---

## Rate Limiting

Report creation endpoints are rate-limited to prevent abuse:
- Maximum 10 reports per user per hour
- Enforced at the application middleware level

---

## Database Schema

See [REPORTS_DB_SCHEMA.md](./REPORTS_DB_SCHEMA.md) for complete database schema documentation.
