# Automatic Matching on Profile Approval

## Overview

Profiles are now automatically matched when approved by admins. Matches are stored in `user_relationships` table and can be retrieved via API.

## New User Endpoint

### Get Confirmed Matches

```
GET /profiles/me/confirmed-matches?page=1&page_size=20
```

**Requirements**: User must have an approved profile

**Response**:
```json
{
  "matches": [
    {
      "match_id": "uuid",
      "user_id": "uuid",
      "relationship": "matched",
      "match_score": 85.5,
      "matched_at": "2025-11-28T10:00:00Z",
      "profile_data": {
        "full_name": "John Doe",
        "profile_picture_url": "https://...",
        "professional_background": "...",
        "industries_of_interest": [...],
        "preferred_languages": [...],
        // ... full profile_versions data
      }
    }
  ],
  "total": 50,
  "page": 1,
  "page_size": 20,
  "total_pages": 3
}
```

## New Admin Endpoints

### Threshold Management

```
POST   /profiles/admin/matching-thresholds              # Create threshold
GET    /profiles/admin/matching-thresholds              # List all
GET    /profiles/admin/matching-thresholds/active       # Get active
GET    /profiles/admin/matching-thresholds/{id}         # Get one
PATCH  /profiles/admin/matching-thresholds/{id}         # Update
DELETE /profiles/admin/matching-thresholds/{id}         # Delete (super admin only)
POST   /profiles/admin/matching-thresholds/{id}/activate
POST   /profiles/admin/matching-thresholds/{id}/deactivate
```

**Create Request**:
```json
{
  "name": "high_quality",
  "description": "Higher threshold for quality matches",
  "threshold_score": 80.0,
  "is_active": true
}
```

## How It Works

1. Admin approves a profile
2. Backend automatically runs matching algorithm
3. Creates `user_relationships` records for matches above active threshold
4. **Email notifications are sent**:
   - Newly approved user receives email with all their matches (first 5 names listed)
   - Each matched user receives email about the new match
5. Users retrieve matches via `/confirmed-matches` endpoint

## Email Notifications

### Newly Approved User Email
- **Subject**: "You have X Cofounder Match(es)!"
- **Content**: List of matched users (full names), up to 5 shown, with "and X more" if needed
- **CTA**: "View All Matches" button linking to frontend matches page

### Matched User Email
- **Subject**: "New Cofounder Match: [Full Name]"
- **Content**: Notification that [Full Name] matched with them
- **CTA**: "View Match" button linking to frontend matches page

### Configuration
Set the frontend URL in environment variables:
```bash
FRONTEND_MATCHES_URL=https://yubanow.com/workspace/cofounder/your-matches
```
Default: `https://yubanow.com/workspace/cofounder/your-matches`

## Notes

- Default threshold: 70.0
- Only one threshold can be active at a time
- Changing threshold does NOT recalculate existing matches
- Match scores range from 0-100
- Email notifications use user's first and last name
- Emails follow Yuba's standard format with gradient header
