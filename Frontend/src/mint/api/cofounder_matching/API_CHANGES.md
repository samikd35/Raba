# API Changes - Cofounder Directory & Messaging

**Date:** 2025-12-16

## Summary

1. **Rate limit reduced:** 72 hours → 48 hours
2. **New field added:** `can_message` in directory response
3. **Directory filter:** Current user's own profile is excluded from results

---

## 1. Rate Limiting: 48 Hours

Users can now initiate conversations with 1 new user every **48 hours** (previously 72 hours).

**Error Message:**
```
"You can only initiate conversations with 1 new user every 48 hours.
You can message users you've matched with at any time."
```

---

## 2. Directory API: New `can_message` Field

### Endpoint
`POST /profiles/directory/search`

### Response Change

**New field added to each profile:**
```typescript
{
  user_id: string;
  profile_id: string;
  version_id: string;
  full_name: string | null;
  country: string | null;
  date_of_birth: string | null;
  profile_picture_url: string | null;
  professional_background: string | null;
  can_message: boolean;  // NEW
}
```

### `can_message` Logic

| Scenario | Value |
|----------|-------|
| Users have matched profiles | `true` |
| Already contacted this user | `true` |
| No active rate limit | `true` |
| Active rate limit (contacted someone else < 48h ago) | `false` |
| Blocked by this user | `false` |
| You blocked this user | `false` |

### Example Response

```json
{
  "total": 25,
  "items": [
    {
      "user_id": "user-123",
      "profile_id": "profile-456",
      "version_id": "version-789",
      "full_name": "John Doe",
      "country": "United States",
      "date_of_birth": "1990-05-15",
      "profile_picture_url": "https://...",
      "professional_background": "Software Engineer",
      "can_message": true
    },
    {
      "user_id": "user-124",
      "profile_id": "profile-457",
      "version_id": "version-790",
      "full_name": "Jane Smith",
      "country": "Canada",
      "date_of_birth": "1988-03-20",
      "profile_picture_url": "https://...",
      "professional_background": "Product Manager",
      "can_message": false
    }
  ],
  "limit": 20,
  "offset": 0,
  "page": 1,
  "total_pages": 2
}
```

---

## 3. Current User Profile Excluded

The directory no longer returns the current user's own profile in search results.

---

## Frontend Integration

### Before
```typescript
// Had to try sending to know if rate limited
async function handleSendMessage(recipientId: string, message: string) {
  try {
    await sendMessage(recipientId, message);
  } catch (error) {
    if (error.status === 429) {
      showError("Rate limit exceeded");
    }
  }
}
```

### After
```typescript
// Check can_message before showing UI
function ProfileCard({ profile }) {
  return (
    <div>
      <h3>{profile.full_name}</h3>
      {profile.can_message ? (
        <button onClick={() => openMessageDialog(profile.user_id)}>
          Send Message
        </button>
      ) : (
        <span className="text-muted">
          Rate limited - try again later
        </span>
      )}
    </div>
  );
}
```

---

## Breaking Changes

**None.** This is backward compatible. The `can_message` field is additive.
