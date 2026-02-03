# Venture Builder API Changes - Frontend Guide

This document covers all new/changed endpoints in the Google Calendar integration branch.

---

## 1. Profile Picture File Upload (2 endpoints modified)

### 1.1 Create VB Profile
**POST** `/api/venture-builder/profile/create`

**Changed from JSON to FormData**

```javascript
const formData = new FormData();
formData.append('data', JSON.stringify({
  contact_email: "vb@example.com",
  biography: "...",
  work_experience: [...],
  linkedin_url: "https://...",
  expertise_ids: ["uuid1", "uuid2"]
}));
formData.append('profile_picture', fileObject);  // Optional

fetch('/api/venture-builder/profile/create?invitation_token=TOKEN', {
  method: 'POST',
  body: formData
});
```

### 1.2 Update VB Profile
**PATCH** `/api/venture-builder/profile`

```javascript
const formData = new FormData();
// Both fields optional
formData.append('data', JSON.stringify({ biography: "Updated" }));
formData.append('profile_picture', newFileObject);

fetch('/api/venture-builder/profile', {
  method: 'PATCH',
  body: formData
});
```

**File requirements:** jpg/jpeg/png/gif/webp/bmp, max 5MB

---

## 2. Google Calendar Integration (6 endpoints)

### 2.1 Get Calendar Auth URL
**GET** `/api/venture-builder/calendar/auth-url`

**Response:**
```json
{
  "auth_url": "https://accounts.google.com/o/oauth2/auth?...",
  "state": "vb-id:token"
}
```

**Usage:** Redirect user to `auth_url` to authorize Google Calendar access.

### 2.2 Calendar OAuth Callback
**GET** `/api/venture-builder/calendar/callback?code=...&state=...`

**Called by Google** after authorization. Redirects to:
- Success: `{FRONTEND_URL}/venture-builder/settings?calendar_connected=true`
- Error: `{FRONTEND_URL}/venture-builder/settings?calendar_error={message}`

### 2.3 Get Calendar Connection Status
**GET** `/api/venture-builder/calendar/status`

**Response:**
```json
{
  "connected": true,
  "calendar_id": "primary@gmail.com",
  "time_zone": "America/New_York",
  "is_valid": true
}
```

### 2.4 List Available Calendars
**GET** `/api/venture-builder/calendar/list`

**Response:**
```json
{
  "calendars": [
    {
      "id": "primary@gmail.com",
      "summary": "My Calendar",
      "primary": true
    }
  ]
}
```

**Note:** Requires existing calendar connection.

### 2.5 Select Calendar
**POST** `/api/venture-builder/calendar/select`

**Request:**
```json
{
  "calendar_id": "primary@gmail.com",
  "time_zone": "America/New_York"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Calendar selected"
}
```

### 2.6 Disconnect Calendar
**DELETE** `/api/venture-builder/calendar/disconnect`

**Response:**
```json
{
  "status": "success",
  "message": "Calendar disconnected"
}
```

---

## 3. Availability Management (4 endpoints)

### 3.1 Set Availability Profiles
**PUT** `/api/venture-builder/{vb_id}/availability-profile`

**Request:**
```json
{
  "profiles": [
    {
      "day_of_week": 1,  // 0=Sun, 1=Mon, ..., 6=Sat
      "start_time": "09:00:00",
      "end_time": "17:00:00",
      "session_length_minutes": 60,
      "buffer_before_minutes": 15,
      "buffer_after_minutes": 15,
      "max_sessions_per_day": 4  // or null for unlimited
    }
  ]
}
```

**Response:** Array of created/updated profiles

**Note:** Replaces all existing availability. VB only (or admin).

### 3.2 Get Availability Profiles
**GET** `/api/venture-builder/{vb_id}/availability-profile`

**Response:**
```json
[
  {
    "vb_id": "uuid",
    "day_of_week": 1,
    "start_time": "09:00:00",
    "end_time": "17:00:00",
    "session_length_minutes": 60,
    "buffer_before_minutes": 15,
    "buffer_after_minutes": 15,
    "max_sessions_per_day": 4
  }
]
```

**Note:** Public endpoint.

### 3.3 Delete Availability for Day
**DELETE** `/api/venture-builder/{vb_id}/availability-profile/{day_of_week}`

**Path params:**
- `day_of_week`: 0-6 (0=Sunday, 6=Saturday)

**Response:**
```json
{
  "status": "success",
  "message": "Removed availability for day 1"
}
```

**Note:** VB only (or admin).

### 3.4 Get Available Booking Slots
**GET** `/api/venture-builder/{vb_id}/availability?start_date=2025-01-01&end_date=2025-01-31`

**Query params:**
- `start_date`: ISO date (YYYY-MM-DD)
- `end_date`: ISO date (YYYY-MM-DD)

**Response:**
```json
{
  "vb_id": "uuid",
  "time_zone": "America/New_York",
  "slots": [
    {
      "start": "2025-01-15T14:00:00Z",
      "end": "2025-01-15T15:00:00Z",
      "available": true
    }
  ]
}
```

**Note:**
- Public endpoint
- Combines working hours, existing bookings, and Google Calendar busy times
- Only returns future slots

---

## 4. Session Management (2 endpoints)

### 4.1 Complete Session
**POST** `/api/venture-builder/sessions/{session_id}/complete`

**Response:**
```json
{
  "id": "session-uuid",
  "status": "completed",
  ...
}
```

**Note:**
- VB or admin only
- Session must have ended (or be within 10 min of ending)
- Cannot complete cancelled/settled sessions

### 4.2 Cancel Session
**DELETE** `/api/venture-builder/sessions/{session_id}`

**Response:**
```json
{
  "id": "session-uuid",
  "status": "canceled",
  "credits_refunded": 100
}
```

**Note:**
- User who booked, VB, or admin
- Cannot cancel started/completed sessions
- Automatically refunds credits
- Deletes Google Calendar event if exists

---

## Quick Reference

### Calendar Integration Flow
```
1. GET /calendar/status → Check if connected
2. GET /calendar/auth-url → Get OAuth URL
3. [User authorizes on Google]
4. GET /calendar/callback → Handle callback (automatic)
5. GET /calendar/list → List calendars
6. POST /calendar/select → Select calendar
7. GET /calendar/status → Verify connection
```

### Availability Setup Flow
```
1. PUT /{vb_id}/availability-profile → Set working hours
2. GET /{vb_id}/availability-profile → Verify profiles
3. GET /{vb_id}/availability → View available slots
```

### Booking Flow Changes
```
1. GET /{vb_id}/availability → Show available slots to user
2. POST /booking → Create booking
   → If VB has calendar: Creates Google Calendar event
3. DELETE /sessions/{id} → Cancel booking
   → Deletes Google Calendar event + refunds credits
```

---

## Breaking Changes

### Profile Picture Upload
**Before:** Send URL as string in JSON
**After:** Send file in FormData with JSON data as string

**Migration:**
```javascript
// Old
await fetch('/api/venture-builder/profile/create', {
  body: JSON.stringify({ profile_picture_url: "https://..." })
});

// New
const formData = new FormData();
formData.append('data', JSON.stringify({ ... }));
formData.append('profile_picture', file);
await fetch('/api/venture-builder/profile/create', { body: formData });
```
