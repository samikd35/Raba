# Team Store Caching System

## Overview

The Team Store implements a sophisticated caching system with stale-while-revalidate pattern to optimize API calls and improve user experience.

## Features

### 1. Multi-Level Caching

The store caches three types of data with different TTLs:

- **Current Team**: 5 minutes
- **Teams List**: 10 minutes  
- **Team Metrics**: 2 minutes

### 2. Stale-While-Revalidate Pattern

The system implements SWR pattern:

1. Returns cached data immediately if available
2. Checks if cache is stale (70% of TTL)
3. If stale, revalidates in background
4. Updates UI when fresh data arrives

This provides instant UI updates while ensuring data freshness.

### 3. Automatic Cache Invalidation

Cache is automatically invalidated on mutations:

- Team creation/update/deletion
- Member invitation/join/removal
- Credit requests/allocations
- Member suspension

## Usage

### Basic Usage with Custom Hook

```typescript
import { useTeamData } from '@/hooks/useTeamData';

function TeamDashboard() {
  const { user } = useAuthStore();
  
  const { 
    currentTeam, 
    teams, 
    isLoading, 
    error,
    refresh 
  } = useTeamData(user?.tenant_id, {
    enabled: true,
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  return (
    <div>
      {isLoading && <LoadingSpinner />}
      {error && <ErrorMessage message={error} />}
      {currentTeam && <TeamInfo team={currentTeam} />}
      <button onClick={refresh}>Refresh</button>
    </div>
  );
}
```

### Manual Cache Management

```typescript
import { useTeamStore } from '@/stores/teamStore';

function TeamSettings() {
  const invalidateAllCaches = useTeamStore(state => state.invalidateAllCaches);
  const isCurrentTeamCacheValid = useTeamStore(state => state.isCurrentTeamCacheValid);
  
  const handleTeamUpdate = async () => {
    await teamService.updateTeam(teamId, data);
    invalidateAllCaches(); // Force refresh
  };

  return (
    <div>
      <p>Cache valid: {isCurrentTeamCacheValid() ? 'Yes' : 'No'}</p>
      <button onClick={handleTeamUpdate}>Update Team</button>
    </div>
  );
}
```

### Cache Invalidation After Mutations

```typescript
import { useTeamCacheInvalidation } from '@/lib/cache/teamCacheInvalidation';

function InviteMemberForm() {
  const { invalidateAfterMemberInvitation } = useTeamCacheInvalidation();
  
  const handleInvite = async (emails: string[]) => {
    await teamService.inviteTeamMembers(teamId, { emails });
    invalidateAfterMemberInvitation(); // Invalidate relevant caches
    toast.success('Invitations sent');
  };

  return <form onSubmit={handleInvite}>...</form>;
}
```

## Cache Configuration

Cache TTLs can be adjusted in `teamStore.ts`:

```typescript
const CACHE_CONFIG = {
  TEAM_TTL: 5 * 60 * 1000, // 5 minutes
  TEAMS_LIST_TTL: 10 * 60 * 1000, // 10 minutes
  METRICS_TTL: 2 * 60 * 1000, // 2 minutes
  STALE_WHILE_REVALIDATE: true,
};
```

## Cache Metadata

Each cached item includes metadata:

```typescript
interface CacheMetadata {
  timestamp: number;    // When data was cached
  expiresAt: number;    // When cache expires
}
```

## Cache Validation

### Hard Expiration

Cache is considered invalid after TTL expires:

```typescript
const isCacheValid = (cache: CacheMetadata | null): boolean => {
  if (!cache) return false;
  return Date.now() < cache.expiresAt;
};
```

### Soft Revalidation

Cache is revalidated in background at 70% of TTL:

```typescript
const shouldRevalidate = (cache: CacheMetadata | null, ttl: number): boolean => {
  if (!cache) return true;
  const staleThreshold = cache.timestamp + (ttl * 0.7);
  return Date.now() > staleThreshold;
};
```

## Persistence

Cache metadata is persisted to localStorage:

- Survives page refreshes
- Automatically invalidated if expired on rehydration
- Only current team is persisted (not full teams list)

## Best Practices

### 1. Use Custom Hooks

Prefer `useTeamData` and `useTeamMetrics` hooks over direct store access:

```typescript
// ✅ Good
const { currentTeam, refresh } = useTeamData(orgId);

// ❌ Avoid
const currentTeam = useTeamStore(state => state.currentTeam);
```

### 2. Invalidate After Mutations

Always invalidate cache after mutations:

```typescript
const handleUpdate = async () => {
  await teamService.updateTeam(teamId, data);
  invalidateAfterTeamUpdate(); // Important!
};
```

### 3. Use Silent Revalidation

For background updates, use silent mode:

```typescript
// Silent revalidation (no loading state)
fetchTeams(true);

// Explicit fetch (shows loading state)
fetchTeams(false);
```

### 4. Handle Cache Misses

Always handle cases where cache is empty:

```typescript
const { currentTeam, isLoading } = useTeamData(orgId);

if (isLoading && !currentTeam) {
  return <LoadingSpinner />;
}

if (!currentTeam) {
  return <EmptyState />;
}
```

## Performance Benefits

1. **Reduced API Calls**: Cache prevents redundant requests
2. **Instant UI Updates**: Cached data displayed immediately
3. **Background Refresh**: Fresh data loaded without blocking UI
4. **Optimistic Updates**: UI updates before API confirmation
5. **Bandwidth Savings**: Less data transferred

## Monitoring

Cache operations are logged to console:

```
TeamStore: Setting current team { hasTeam: true, teamId: '123', skipCache: false }
TeamStore: Cache invalidated after team update
TeamStore: Storage rehydration completed { cacheValid: true }
```

## Migration Guide

### Before (No Caching)

```typescript
const [team, setTeam] = useState(null);
const [loading, setLoading] = useState(true);

useEffect(() => {
  const fetchTeam = async () => {
    setLoading(true);
    const data = await teamService.fetchTeams(orgId);
    setTeam(data[0]);
    setLoading(false);
  };
  fetchTeam();
}, [orgId]);
```

### After (With Caching)

```typescript
const { currentTeam, isLoading } = useTeamData(orgId, {
  refetchInterval: 30000,
});
```

## Troubleshooting

### Cache Not Invalidating

Ensure you're calling invalidation functions after mutations:

```typescript
await teamService.updateTeam(teamId, data);
invalidateAfterTeamUpdate(); // Don't forget this!
```

### Stale Data Persisting

Check if cache TTL is too long. Reduce TTL in config:

```typescript
const CACHE_CONFIG = {
  TEAM_TTL: 2 * 60 * 1000, // Reduce from 5 to 2 minutes
};
```

### Cache Not Persisting

Verify localStorage is available and not full:

```typescript
try {
  localStorage.setItem('test', 'test');
  localStorage.removeItem('test');
} catch (e) {
  console.error('localStorage not available');
}
```

## Future Enhancements

- [ ] Add cache size limits
- [ ] Implement LRU eviction policy
- [ ] Add cache warming on app start
- [ ] Support offline mode with cache
- [ ] Add cache analytics/metrics
