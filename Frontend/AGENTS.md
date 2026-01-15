# AGENTS.md - Frontend (RABA)

**Purpose:** Frontend-specific rules for AI agents.

**Read First:** Root `AGENTS.md` and `FRONTEND_REQUIREMENTS.md`

---

## Tech Stack

Next.js 15 (App Router), TypeScript 5+, Tailwind CSS v4, Shadcn/ui, TanStack Query v5, Framer Motion, next-themes, TipTap

---

## Project Structure

```
Frontend/
├── app/              # Next.js App Router (Server Components by default)
├── components/       # UI components (ui/, layout/, workflow/, forms/, common/)
├── lib/             # API clients, query-client, utils
├── hooks/           # Custom React hooks
└── types/           # TypeScript types
```

---

## Code Style

**Naming:** Components PascalCase, hooks `use*`, utilities camelCase, types PascalCase  
**Components:** Use Server Components by default, `'use client'` only for interactivity (hooks, events, browser APIs)  
**TypeScript:** Strict mode, explicit types, no `any`, interfaces for props

```typescript
// ✅ Good: Typed, accessible, error handling
'use client'
interface WorkflowCardProps {
  workflow: Workflow
  onView: (id: string) => void
}
export function WorkflowCard({ workflow, onView }: WorkflowCardProps) {
  // Implementation with error handling
}
```

---

## Responsive Design

**Breakpoints:** Mobile (< 768px), Tablet (768px-1024px), Desktop (> 1024px)  
**Pattern:** Mobile-first (base styles mobile, add `md:`, `lg:` for larger)  
**Navigation:** Mobile=bottom nav, Tablet=collapsible sidebar, Desktop=permanent sidebar (240px)

---

## Theme System

**Library:** `next-themes`  
**Colors:** Use CSS variables (not hardcoded), test both themes, WCAG AA contrast  
**Toggle:** Header (Light/Dark/System), smooth 300ms transition, accessible

---

## API Integration

**Pattern:** Typed client functions in `lib/api/`, TanStack Query for server state, optimistic updates  
**Polling:** 3-5s intervals for workflow status, stop when completed/failed

```typescript
// ✅ Good: Typed, error handling, proper query config
const { data } = useQuery({
  queryKey: ['workflows', 'detail', id],
  queryFn: () => getWorkflow(id),
  refetchInterval: (data) => data?.status === 'running' ? 3000 : false,
})
```

---

## Component Patterns

**Loading:** Skeleton screens (match content), minimum 300ms display time  
**Error:** User-friendly messages, retry actions, proper logging  
**Empty:** Friendly illustrations, clear messaging, CTAs

---

## Accessibility

✅ **ALWAYS:** Semantic HTML, ARIA labels, keyboard nav, focus management, screen reader testing, color contrast

---

## Performance

**Code Splitting:** Dynamic imports for heavy components, lazy load offscreen  
**Images:** Next.js `<Image>`, responsive `sizes`, WebP/AVIF, lazy loading

---

## Pages Required

1. **Create** (`/`) - Form, validation, image upload, HITL toggle  
2. **Workflow Detail** (`/workflows/[id]`) - Pipeline stepper, polling, HITL gates, video player  
3. **Workflows List** (`/workflows`) - Grid, filters, search, pagination  
4. **Tools** (`/tools`) - Tool grid, create modal  
5. **Monitoring** (`/monitoring`) - Cost charts, usage metrics

**Commands:** `npm run dev`, `npm run build`, `npm test`, `npm run lint`, `npm run type-check`  
**Checklist:** Responsive, both themes, accessible, error handling, tests, optimized
