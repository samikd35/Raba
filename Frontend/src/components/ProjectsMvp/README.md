# ProjectsMvp Component

Modular component structure for displaying completed value map projects.

## Structure

```
ProjectsMvp/
├── index.ts                      # Main exports
├── types.ts                      # TypeScript interfaces
├── cacheUtils.ts                 # Cache management utilities
├── apiService.ts                 # API calls
├── ProjectsMvpComponent.tsx      # Main component logic
├── ProjectCard.tsx               # Individual project card
├── ProjectsLoading.tsx           # Loading skeleton
├── ProjectsError.tsx             # Error state
├── ProjectsEmpty.tsx             # Empty state
└── ProjectsFilters.tsx           # Search and filter controls
```

## Usage

```tsx
// Named import (recommended)
import { ProjectsMvp } from '@/components/ProjectsMvp';

// Default import (backward compatibility)
import ProjectsMvp from '@/components/ProjectsMvp';

// Import types
import type { Project, ProjectsResponse } from '@/components/ProjectsMvp';
```

## Components

### ProjectsMvp (Main)
Main orchestration component that manages state and renders sub-components.

### ProjectCard
Individual project card with status, personas, and navigation.

### ProjectsFilters
Search, sort, and filter controls for the projects list.

### ProjectsLoading
Skeleton loading state with 6 placeholder cards.

### ProjectsError
Error state with retry and navigation options.

### ProjectsEmpty
Empty state when no projects exist.

## Utilities

### cacheUtils
- `getCachedData()` - Get cached projects
- `setCachedData()` - Cache projects data
- `clearCache()` - Clear cached data

### apiService
- `fetchCompletedValueMaps()` - Fetch projects from API

## Features

- ✅ Modular architecture
- ✅ TypeScript support
- ✅ localStorage caching (5 min TTL)
- ✅ Search and filtering
- ✅ Sorting (name, date, personas)
- ✅ Error handling with retry
- ✅ Loading states
- ✅ Empty states
- ✅ Dark mode support
- ✅ Responsive design
