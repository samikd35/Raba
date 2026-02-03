# Error Handling and Loading States

This directory contains comprehensive error handling and loading state management utilities for the Team Leader Workspace.

## Error Handler

### Overview

The `ErrorHandler` class provides centralized error handling with user-friendly messages and appropriate actions for different error types.

### Error Types

```typescript
enum ErrorType {
  AUTHENTICATION_REQUIRED = 'auth_required',
  TOKEN_EXPIRED = 'token_expired',
  TOKEN_INVALID = 'token_invalid',
  INSUFFICIENT_PERMISSIONS = 'insufficient_permissions',
  TEAM_ALREADY_EXISTS = 'team_exists',
  INSUFFICIENT_CREDITS = 'insufficient_credits',
  NETWORK_ERROR = 'network_error',
  VALIDATION_ERROR = 'validation_error',
  NOT_FOUND = 'not_found',
  DUPLICATE_INVITATION = 'duplicate_invitation',
  RATE_LIMIT_EXCEEDED = 'rate_limit_exceeded',
  SERVER_ERROR = 'server_error',
  UNKNOWN_ERROR = 'unknown_error',
}
```

### Basic Usage

```typescript
import { ErrorHandler } from '@/lib/errors/errorHandler';

try {
  await someAsyncOperation();
} catch (error) {
  ErrorHandler.handle(error, 'TeamCreation');
}
```

### Advanced Usage with Callbacks

```typescript
ErrorHandler.handle(error, 'TeamCreation', {
  onAuthRequired: () => {
    // Custom redirect logic
    router.push('/signin');
  },
  onPermissionDenied: () => {
    // Custom permission denied handling
    router.push('/unauthorized');
  },
  onTokenExpired: () => {
    // Custom token expiry handling
    showRequestNewInvitationDialog();
  },
  silent: false, // Set to true to suppress toast notifications
});
```

### Retry Logic

```typescript
import { ErrorHandler } from '@/lib/errors/errorHandler';

const result = await ErrorHandler.retry(
  async () => {
    return await teamService.fetchTeams(orgId);
  },
  2, // max retries
  'FetchTeams' // context
);
```

### Convenience Function

```typescript
import { handleAsyncError } from '@/lib/errors/errorHandler';

const result = await handleAsyncError(
  async () => {
    return await teamService.createTeam(data);
  },
  'TeamCreation',
  {
    retry: true,
    maxRetries: 2,
    onAuthRequired: () => router.push('/signin'),
  }
);

if (result) {
  // Success
  console.log('Team created:', result);
}
```

### Validation Errors

```typescript
import { ErrorHandler } from '@/lib/errors/errorHandler';

// Handle field-specific validation errors
ErrorHandler.handleValidationErrors(
  {
    name: ['Team name is required'],
    email: ['Invalid email format'],
  },
  'TeamCreation'
);
```

## Loading States

### Components

#### LoadingSpinner

```typescript
import { LoadingSpinner } from '@/components/ui/loading-states';

<LoadingSpinner size="default" />
<LoadingSpinner size="sm" />
<LoadingSpinner size="lg" />
```

#### LoadingSpinnerWithText

```typescript
import { LoadingSpinnerWithText } from '@/components/ui/loading-states';

<LoadingSpinnerWithText text="Loading team data..." />
```

#### LoadingOverlay

```typescript
import { LoadingOverlay } from '@/components/ui/loading-states';

{isLoading && <LoadingOverlay text="Creating team..." />}
```

#### Skeleton Loaders

```typescript
import {
  TeamMetricsCardSkeleton,
  TeamMemberCardSkeleton,
  CreditRequestTableSkeleton,
  DashboardSkeleton,
  FormSkeleton,
} from '@/components/ui/loading-states';

// Show skeleton while loading
{isLoading ? (
  <TeamMetricsCardSkeleton />
) : (
  <TeamMetricsCard data={teamData} />
)}
```

#### ButtonLoading

```typescript
import { ButtonLoading } from '@/components/ui/loading-states';
import { Button } from '@/components/ui/button';

<Button disabled={isLoading}>
  {isLoading ? <ButtonLoading text="Creating..." /> : 'Create Team'}
</Button>
```

#### ProgressIndicator

```typescript
import { ProgressIndicator } from '@/components/ui/loading-states';

<ProgressIndicator
  currentStep={2}
  totalSteps={4}
  stepLabels={['Details', 'Members', 'Credits', 'Review']}
/>
```

#### EmptyState

```typescript
import { EmptyState } from '@/components/ui/loading-states';
import { Users } from 'lucide-react';

<EmptyState
  title="No team members"
  description="Invite members to get started"
  isLoading={isLoading}
  icon={Users}
  action={<Button>Invite Members</Button>}
/>
```

### Hooks

#### useLoadingState

```typescript
import { useLoadingState } from '@/hooks/useLoadingState';

function MyComponent() {
  const { isLoading, error, startLoading, stopLoading, setLoadingError } = useLoadingState();

  const handleSubmit = async () => {
    startLoading();
    try {
      await someAsyncOperation();
      stopLoading();
    } catch (err) {
      setLoadingError('Operation failed');
    }
  };

  return (
    <div>
      {isLoading && <LoadingSpinner />}
      {error && <p className="text-red-500">{error}</p>}
      <Button onClick={handleSubmit} disabled={isLoading}>
        Submit
      </Button>
    </div>
  );
}
```

#### useAsyncOperation

```typescript
import { useAsyncOperation } from '@/hooks/useLoadingState';

function MyComponent() {
  const { execute, isLoading, error, data } = useAsyncOperation(
    async (teamId: string) => {
      return await teamService.fetchTeam(teamId);
    },
    {
      context: 'FetchTeam',
      onSuccess: () => {
        toast.success('Team loaded successfully');
      },
      onError: (err) => {
        console.error('Failed to load team:', err);
      },
    }
  );

  useEffect(() => {
    execute('team-123');
  }, []);

  if (isLoading) return <LoadingSpinner />;
  if (error) return <p>Error: {error}</p>;
  if (!data) return null;

  return <div>{data.name}</div>;
}
```

#### useMultipleLoadingStates

```typescript
import { useMultipleLoadingStates } from '@/hooks/useLoadingState';

function MyComponent() {
  const { loadingStates, startLoading, stopLoading, isAnyLoading } = 
    useMultipleLoadingStates(['team', 'members', 'credits']);

  const loadTeam = async () => {
    startLoading('team');
    try {
      await teamService.fetchTeam();
    } finally {
      stopLoading('team');
    }
  };

  return (
    <div>
      {loadingStates.team && <p>Loading team...</p>}
      {loadingStates.members && <p>Loading members...</p>}
      {loadingStates.credits && <p>Loading credits...</p>}
      <Button disabled={isAnyLoading}>Submit</Button>
    </div>
  );
}
```

## Best Practices

### 1. Always Handle Errors

```typescript
// ❌ Bad
const data = await teamService.fetchTeam();

// ✅ Good
try {
  const data = await teamService.fetchTeam();
} catch (error) {
  ErrorHandler.handle(error, 'FetchTeam');
}
```

### 2. Show Loading States

```typescript
// ❌ Bad
const handleSubmit = async () => {
  await teamService.createTeam(data);
};

// ✅ Good
const handleSubmit = async () => {
  setIsLoading(true);
  try {
    await teamService.createTeam(data);
  } catch (error) {
    ErrorHandler.handle(error, 'CreateTeam');
  } finally {
    setIsLoading(false);
  }
};
```

### 3. Disable Buttons During Loading

```typescript
// ✅ Good
<Button onClick={handleSubmit} disabled={isLoading}>
  {isLoading ? <ButtonLoading text="Creating..." /> : 'Create Team'}
</Button>
```

### 4. Use Skeleton Loaders for Better UX

```typescript
// ✅ Good
{isLoading ? (
  <DashboardSkeleton />
) : (
  <Dashboard data={data} />
)}
```

### 5. Provide Context in Error Messages

```typescript
// ✅ Good
ErrorHandler.handle(error, 'TeamCreation'); // Clear context
ErrorHandler.handle(error, 'MemberInvitation'); // Clear context
```

### 6. Use Retry Logic for Network Errors

```typescript
// ✅ Good
const data = await ErrorHandler.retry(
  () => teamService.fetchTeam(),
  2,
  'FetchTeam'
);
```

## Integration Example

Complete example showing error handling and loading states:

```typescript
import { useState } from 'react';
import { ErrorHandler } from '@/lib/errors/errorHandler';
import { useLoadingState } from '@/hooks/useLoadingState';
import { 
  LoadingSpinner, 
  ButtonLoading,
  TeamMetricsCardSkeleton 
} from '@/components/ui/loading-states';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';

function TeamCreationForm() {
  const [formData, setFormData] = useState({ name: '', description: '' });
  const { isLoading, startLoading, stopLoading } = useLoadingState();
  const [teamData, setTeamData] = useState(null);
  const [isLoadingTeam, setIsLoadingTeam] = useState(true);

  // Load team data on mount
  useEffect(() => {
    const loadTeam = async () => {
      setIsLoadingTeam(true);
      try {
        const data = await ErrorHandler.retry(
          () => teamService.fetchTeam(),
          2,
          'FetchTeam'
        );
        setTeamData(data);
      } catch (error) {
        ErrorHandler.handle(error, 'FetchTeam');
      } finally {
        setIsLoadingTeam(false);
      }
    };
    loadTeam();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    startLoading();

    try {
      const result = await teamService.createTeam(formData);
      toast.success('Team created successfully');
      router.push('/admin/team-leader-dashboard');
    } catch (error) {
      ErrorHandler.handle(error, 'TeamCreation', {
        onAuthRequired: () => router.push('/signin'),
      });
    } finally {
      stopLoading();
    }
  };

  if (isLoadingTeam) {
    return <TeamMetricsCardSkeleton />;
  }

  return (
    <form onSubmit={handleSubmit}>
      <input
        value={formData.name}
        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
        disabled={isLoading}
      />
      <Button type="submit" disabled={isLoading}>
        {isLoading ? <ButtonLoading text="Creating..." /> : 'Create Team'}
      </Button>
    </form>
  );
}
```
