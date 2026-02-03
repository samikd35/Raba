# Authentication Utilities

This directory contains authentication-related utilities for the Yuba platform.

## InvitationFlowManager

The `InvitationFlowManager` utility handles invitation token storage and authentication redirects for different types of invitations.

### Features

- **Token Storage**: Securely stores invitation tokens in sessionStorage
- **Token Validation**: Validates token structure and expiry (48-hour window)
- **Type-based Routing**: Generates appropriate redirect URLs based on invitation type
- **Error Handling**: Comprehensive error handling for storage operations

### Supported Invitation Types

1. **Organization Member** (`org_member`): Regular organization members
2. **Team Leader** (`team_leader`): Users who can create and manage teams
3. **Team Member** (`team_member`): Members joining an existing team

### Usage

#### Storing a Token Before Authentication

```typescript
import { InvitationFlowManager } from '@/lib/auth/invitationFlowManager';

// When user clicks invitation link but is not authenticated
const token = extractTokenFromUrl();
InvitationFlowManager.storeInvitationToken({
  token,
  type: 'team_member',
  teamId: 'team-123',
  timestamp: Date.now(),
});

// Redirect to sign-in
router.push('/signin');
```

#### Checking for Token After Authentication

```typescript
import { InvitationFlowManager } from '@/lib/auth/invitationFlowManager';

// In sign-in success handler
const redirectUrl = InvitationFlowManager.getRedirectUrlIfTokenExists();

if (redirectUrl) {
  router.push(redirectUrl);
} else {
  router.push('/');
}
```

#### Clearing Token After Successful Join

```typescript
import { InvitationFlowManager } from '@/lib/auth/invitationFlowManager';

// After successfully joining organization/team
InvitationFlowManager.clearInvitationToken();
```

### API Reference

#### `storeInvitationToken(token: InvitationToken): void`

Stores an invitation token in sessionStorage.

**Parameters:**
- `token`: InvitationToken object containing:
  - `token`: The invitation token string
  - `type`: Type of invitation ('org_member' | 'team_leader' | 'team_member')
  - `organizationId`: Optional organization ID
  - `teamId`: Optional team ID
  - `timestamp`: Timestamp when token was created

**Throws:** Error if storage operation fails

#### `getStoredInvitationToken(): InvitationToken | null`

Retrieves the stored invitation token from sessionStorage.

**Returns:** InvitationToken object or null if not found/invalid

#### `clearInvitationToken(): void`

Removes the invitation token from sessionStorage.

#### `isTokenExpired(token: InvitationToken): boolean`

Checks if a token has expired (48 hours from creation).

**Parameters:**
- `token`: The invitation token to check

**Returns:** true if expired, false otherwise

#### `getPostAuthRedirectUrl(token: InvitationToken): string`

Generates the appropriate redirect URL based on invitation type.

**Parameters:**
- `token`: The invitation token

**Returns:** Redirect URL string

#### `getRedirectUrlIfTokenExists(): string | null`

Convenience method that checks for a valid stored token and returns redirect URL.

**Returns:** Redirect URL if valid token exists, null otherwise

### Token Expiry

Tokens expire after **48 hours** from creation. Expired tokens are automatically cleared when detected.

### Storage

Tokens are stored in **sessionStorage** (not localStorage) for security:
- Survives page refreshes
- Cleared when browser tab is closed
- Not accessible across different tabs
- More secure than localStorage for sensitive data

### Error Handling

All methods include comprehensive error handling:
- Storage failures are logged and throw user-friendly errors
- Invalid token structures are detected and cleared
- Expired tokens are automatically removed

### Examples

See `invitationFlowManager.example.ts` for detailed usage examples.

## Integration Points

This utility is used in:
- Sign-in page (`/signin`)
- Sign-up page (`/signup`)
- Organization invite page (`/org-invite/[token]`)
- Team invite page (`/team-invite/[token]`)
- Team leader onboarding page (`/admin/team-leader-onboarding`)
