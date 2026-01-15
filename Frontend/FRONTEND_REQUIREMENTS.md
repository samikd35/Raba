# RABA Frontend Requirements Specification

**Version:** 1.0  
**Date:** January 2026  
**Status:** Implementation Ready  
**Tech Stack:** Next.js 15 (App Router), Tailwind CSS, Shadcn/ui, TanStack Query, Framer Motion

---

## Table of Contents

1. [Overview](#overview)
2. [Page Structure](#page-structure)
3. [Responsive Design Requirements](#responsive-design-requirements)
4. [Theme System (Light/Dark Mode)](#theme-system-lightdark-mode)
5. [Caching Strategy](#caching-strategy)
6. [Edge Cases & Error Handling](#edge-cases--error-handling)
7. [Component Architecture](#component-architecture)
8. [Real-Time Updates](#real-time-updates)
9. [Performance Requirements](#performance-requirements)
10. [Accessibility Requirements](#accessibility-requirements)
11. [Testing Requirements](#testing-requirements)

---

## 1. Overview

### 1.1 Purpose

This document defines the complete frontend requirements for the RABA web application—an AI-powered YouTube Shorts generator. The frontend must provide a seamless, responsive, and accessible experience across all devices while handling complex multi-agent workflows with real-time status updates.

### 1.2 Core Principles

- **Mobile-First Design**: Start with mobile, progressively enhance for larger screens
- **Real-Time Experience**: Zero-refresh workflow status updates
- **Accessibility First**: WCAG 2.1 AA compliance minimum
- **Performance Optimized**: Fast initial load, smooth interactions
- **Edge Case Resilient**: Graceful handling of all failure scenarios

### 1.3 Tech Stack Summary

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Framework** | Next.js 15 (App Router) | Server components, routing, optimization |
| **Styling** | Tailwind CSS v4 | Utility-first styling, responsive design |
| **UI Components** | Shadcn/ui | Accessible, customizable components |
| **State Management** | TanStack Query v5 | Server state, caching, polling |
| **Animations** | Framer Motion | Smooth transitions, pipeline visualization |
| **Theme** | next-themes | Dark/light mode with system preference |
| **Real-Time** | TanStack Query + Polling | Workflow status updates |
| **Forms** | React Hook Form + Zod | Form validation |
| **Editor** | TipTap | Script editing in HITL mode |
| **Video Player** | Video.js or native HTML5 | 9:16 video preview |

---

## 2. Page Structure

### 2.1 Page Inventory

| Page | Route | Priority | Complexity | Purpose |
|------|-------|----------|------------|---------|
| **Create Page** | `/` | **Must Have** | Medium | Primary entry point for video generation |
| **Workflow Detail** | `/workflows/[id]` | **Must Have** | High | Real-time progress tracking & HITL interactions |
| **Workflows List** | `/workflows` | **Must Have** | Medium | Browse and manage all workflows |
| **Tools Management** | `/tools` | **Should Have** | Medium | Browse and manage video generation tools |
| **Monitoring** | `/monitoring` | **Should Have** | Low | Usage metrics and cost tracking |

**Total Pages:** 5  
**MVP Pages:** 3 (Create, Detail, List)  
**Full Implementation:** All 5 pages

---

### 2.2 Page 1: Create Page (`/`)

#### Purpose
Primary entry point where users input topic and parameters to start video generation.

#### Layout Structure

```
┌─────────────────────────────────────────────────────────┐
│  HEADER (Global Navigation)                             │
│  [RABA Logo] [Create] [Workflows] [Tools] [Theme Toggle]│
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  PAGE TITLE: "Create Your Video"                  │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  TOPIC INPUT (Required)                           │  │
│  │  ┌────────────────────────────────────────────┐  │  │
│  │  │ Textarea (3-500 chars)                      │  │  │
│  │  │ Placeholder: "What video do you want to    │  │  │
│  │  │ create? Describe your topic..."            │  │  │
│  │  └────────────────────────────────────────────┘  │  │
│  │  Character count: 0/500                          │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  VIDEO PARAMETERS                                 │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐       │  │
│  │  │ Duration │  │ Aspect  │  │Resolution│       │  │
│  │  │ [18s ▼]  │  │ [9:16▼] │  │[1080p▼] │       │  │
│  │  └──────────┘  └──────────┘  └──────────┘       │  │
│  │                                                  │  │
│  │  ┌──────────┐                                    │  │
│  │  │Category  │                                    │  │
│  │  │[Auto ▼]  │                                    │  │
│  │  └──────────┘                                    │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  REFERENCE IMAGE (Optional)                      │  │
│  │  ┌────────────────────────────────────────────┐  │  │
│  │  │ Drag & Drop Zone                          │  │  │
│  │  │ or [Upload Image] button                  │  │  │
│  │  │ Max 10MB, JPG/PNG/WEBP                    │  │  │
│  │  └────────────────────────────────────────────┘  │  │
│  │  [Preview if uploaded]                           │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  OPTIONS                                          │  │
│  │  ☑ Enable Audio  ☐ Enable Subtitles              │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  HITL MODE                                       │  │
│  │  ○ Auto (End-to-end, no approval gates)          │  │
│  │  ● Manual (5 approval gates for review)          │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│        [Generate Video →] (Primary CTA)                 │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  ESTIMATED COST: ~$1.50 - $2.50                  │  │
│  │  ESTIMATED TIME: 4-5 minutes                      │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

#### Key Components

1. **TopicInput**
   - Large textarea (min-height: 120px)
   - Character counter (0/500)
   - Validation: min 3, max 500 chars
   - Auto-resize on mobile

2. **ParameterSelectors**
   - Duration: Slider or select (8-25s, default: 18)
   - Aspect Ratio: Radio buttons or select (9:16, 16:9)
   - Resolution: Select (720p, 1080p)
   - Category: Select (auto, surreal_realism, high_octane_anime, stylized_3d)

3. **ImageUpload**
   - Drag & drop zone
   - File picker button
   - Preview thumbnail
   - File size validation (max 10MB)
   - Format validation (jpg, png, webp)
   - Progress indicator during upload

4. **HITLModeToggle**
   - Radio buttons or toggle switch
   - Clear explanation of each mode
   - Tooltip/help text

5. **GenerateButton**
   - Primary CTA button
   - Loading state during submission
   - Disabled if topic invalid
   - Redirects to workflow detail on success

#### Responsive Behavior

- **Mobile (< 768px)**:
  - Single column layout
  - Stacked parameter selectors
  - Full-width inputs
  - Bottom-fixed CTA button (sticky)

- **Tablet (768px - 1024px)**:
  - 2-column grid for parameters
  - Larger textarea
  - Side-by-side options

- **Desktop (> 1024px)**:
  - Centered container (max-width: 800px)
  - 3-column grid for parameters
  - Larger spacing

#### Edge Cases

- **Empty topic**: Show validation error, disable submit
- **Topic too long**: Show character limit error
- **Invalid file type**: Show error, prevent upload
- **File too large**: Show error with max size
- **Network error**: Show retry button, preserve form state
- **Rate limit**: Show friendly message, suggest waiting

---

### 2.3 Page 2: Workflow Detail Page (`/workflows/[id]`)

#### Purpose
Real-time progress tracking, HITL gate interactions, and final video preview.

#### Layout Structure

```
┌─────────────────────────────────────────────────────────┐
│  HEADER                                                  │
│  ← Back to Workflows    Workflow: wf_abc123             │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  5-AGENT PIPELINE VISUALIZATION                  │  │
│  │                                                   │  │
│  │  ✅ 1. Intent/Tool Selector    [2.3s]            │  │
│  │     └─ Tool: Cosmic Flow Visualizer              │  │
│  │                                                   │  │
│  │  ✅ 2. Deep Research           [15.7s]           │  │
│  │     └─ 3 sources, 2 images found                │  │
│  │                                                   │  │
│  │  ⏸️ 3. Script Writer          [Awaiting Review] │  │
│  │     └─ [View Script] [Edit] [Approve]            │  │
│  │                                                   │  │
│  │  ⏳ 4. Image Generator         [Pending]          │  │
│  │                                                   │  │
│  │  ⏳ 5. Video Generator         [Pending]          │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────────────┐  ┌──────────────────────┐   │
│  │   CURRENT OUTPUT      │  │   HITL ACTIONS       │   │
│  │   (Left Pane)         │  │   (Right Pane)       │   │
│  │                       │  │                      │   │
│  │  [Script Preview]     │  │  [Approve]           │   │
│  │                       │  │  [Edit Script]       │   │
│  │  Hook: "You won't    │  │  [Regenerate]         │   │
│  │  believe..."         │  │                      │   │
│  │                       │  │  Feedback:           │   │
│  │  Body: [...]         │  │  [Textarea]          │   │
│  │                       │  │                      │   │
│  │  [TipTap Editor]     │  │  Regenerations: 0/3  │   │
│  └──────────────────────┘  └──────────────────────┘   │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  RESEARCH FINDINGS (Collapsible)                  │  │
│  │  • Black holes warp spacetime...                 │  │
│  │  • Sources: NASA, ESA                            │  │
│  │  [View Images] [View Citations]                  │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  GENERATED IMAGES (Gallery)                      │  │
│  │  [Img1] [Img2] [Img3] [Img4]                     │  │
│  │  [Add Image] [Remove]                            │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  FINAL VIDEO (When Complete)                     │  │
│  │  ┌──────────────────────────────────────────┐   │  │
│  │  │  [9:16 Video Player]                     │   │  │
│  │  │  Duration: 18s | Resolution: 1080p      │   │  │
│  │  └──────────────────────────────────────────┘   │  │
│  │  [Download] [Share] [Delete] [Regenerate]        │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  COST BREAKDOWN (Sidebar/Accordion)              │  │
│  │  • Research: $0.23                               │  │
│  │  • Script: $0.09                                 │  │
│  │  • Images: $0.52                                │  │
│  │  • Video: $1.48                                 │  │
│  │  Total: $2.32                                   │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

#### Key Components

1. **PipelineStepper**
   - Vertical or horizontal stepper
   - 5 agent stages with status icons
   - Animated transitions (Framer Motion)
   - Status: pending, running, completed, awaiting_approval, failed
   - Click to expand/collapse agent details

2. **RealTimeStatusPolling**
   - TanStack Query with 3-5 second interval
   - Background refetch when tab visible
   - Optimistic updates
   - Connection status indicator

3. **HITLGateUI**
   - Conditional rendering when `current_hitl_gate` exists
   - Dual-pane layout (output + actions)
   - Actions: Approve, Edit, Regenerate, Add Image
   - Feedback textarea for regeneration
   - Regeneration counter (0/3)
   - Loading states for each action

4. **ScriptEditor** (TipTap)
   - Rich text editor for script editing
   - Syntax highlighting for dialogue/narration
   - Auto-save draft
   - Preview mode toggle

5. **VideoPlayer**
   - 9:16 aspect ratio container
   - Native HTML5 or Video.js
   - Controls: play, pause, volume, fullscreen
   - Mobile-optimized touch controls
   - Loading spinner during buffering

6. **ImageGallery**
   - Grid layout (responsive)
   - Lightbox on click
   - Add/remove images (HITL mode)
   - Lazy loading

7. **CostBreakdown**
   - Accordion or sidebar widget
   - Per-step cost breakdown
   - Total cost
   - Estimated cost (if not complete)

#### Responsive Behavior

- **Mobile (< 768px)**:
  - Vertical pipeline stepper
  - Stacked panes (output above actions)
  - Full-width video player
  - Collapsible cost breakdown
  - Bottom sheet for HITL actions

- **Tablet (768px - 1024px)**:
  - Horizontal pipeline stepper
  - Side-by-side panes (if space allows)
  - Centered video player
  - Sidebar cost breakdown

- **Desktop (> 1024px)**:
  - Horizontal pipeline stepper
  - Dual-pane HITL UI
  - Large video player
  - Persistent sidebar cost breakdown

#### Edge Cases

- **Workflow not found**: 404 page with "Back to Workflows" link
- **Workflow failed**: Error message with retry option
- **Network disconnect**: Show offline indicator, pause polling
- **Polling timeout**: Show warning, manual refresh button
- **HITL gate timeout**: Show warning, allow manual continue
- **Video load failure**: Show error, retry button
- **Image load failure**: Show placeholder, retry option
- **Rate limit during HITL**: Show message, disable actions temporarily

---

### 2.4 Page 3: Workflows List Page (`/workflows`)

#### Purpose
Browse, filter, and manage all video generation workflows.

#### Layout Structure

```
┌─────────────────────────────────────────────────────────┐
│  HEADER                                                  │
│  RABA - Video Workflows              [+ Create Video]   │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  FILTERS & SEARCH                                 │  │
│  │  [All] [Pending] [Running] [Completed] [Failed]  │  │
│  │  [Search: "black holes"...]                       │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │ [Thumb]  │  │ [Thumb]  │  │ [Thumb]  │             │
│  │          │  │          │  │          │             │
│  │ "How     │  │ "Ancient │  │ "Quantum │             │
│  │  black   │  │  Roman   │  │  physics │             │
│  │  holes   │  │  engin.."│  │  expla.."│             │
│  │  work"   │  │          │  │          │             │
│  │          │  │          │  │          │             │
│  │ ✅ Done  │  │ ⏳ Running│  │ ✅ Done  │             │
│  │ 18s      │  │ 20s      │  │ 15s      │             │
│  │ 2h ago   │  │ Now      │  │ 1d ago   │             │
│  │          │  │          │  │          │             │
│  │ [View]   │  │ [View]   │  │ [View]   │             │
│  │ [Delete] │  │ [Delete] │  │ [Delete] │             │
│  └──────────┘  └──────────┘  └──────────┘             │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │ [Thumb]  │  │ [Thumb]  │  │ [Thumb]  │             │
│  │ ...      │  │ ...      │  │ ...      │             │
│  └──────────┘  └──────────┘  └──────────┘             │
│                                                          │
│  [Load More] or [Pagination: 1 2 3 ...]                 │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  EMPTY STATE (if no workflows)                    │  │
│  │  [Illustration]                                   │  │
│  │  "No workflows yet"                               │  │
│  │  "Create your first video to get started"        │  │
│  │  [Create Video]                                   │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

#### Key Components

1. **WorkflowGrid**
   - Responsive grid (1 col mobile, 2-3 tablet, 3-4 desktop)
   - Workflow cards with thumbnail
   - Hover effects
   - Click to navigate to detail page

2. **StatusFilters**
   - Tab navigation or buttons
   - Active filter highlight
   - Count badges (e.g., "Completed (12)")

3. **SearchBar**
   - Debounced search (300ms)
   - Search by topic
   - Clear button
   - Loading indicator during search

4. **WorkflowCard**
   - Thumbnail (video or placeholder)
   - Topic preview (truncated)
   - Status badge
   - Metadata (duration, category, date)
   - Quick actions (view, delete on hover)

5. **Pagination**
   - Infinite scroll (preferred) or page numbers
   - Load more button
   - Loading skeleton during fetch

6. **EmptyState**
   - Illustration or icon
   - Friendly message
   - CTA to create first workflow

#### Responsive Behavior

- **Mobile (< 768px)**:
  - Single column grid
  - Stacked filters (scrollable)
  - Full-width cards
  - Bottom navigation for pagination

- **Tablet (768px - 1024px)**:
  - 2-column grid
  - Horizontal filter tabs
  - Medium-sized cards

- **Desktop (> 1024px)**:
  - 3-4 column grid
  - Horizontal filter tabs
  - Large cards with hover effects

#### Edge Cases

- **No workflows**: Show empty state
- **Filter returns no results**: Show "No workflows match your filters"
- **Search returns no results**: Show "No results for 'query'"
- **Pagination error**: Show error, retry button
- **Delete confirmation**: Modal with confirmation
- **Bulk operations**: Select multiple, bulk delete (future)

---

### 2.5 Page 4: Tools Management Page (`/tools`)

#### Purpose
Browse available video generation tools and create new ones.

#### Layout Structure

```
┌─────────────────────────────────────────────────────────┐
│  HEADER                                                  │
│  RABA - Tools                        [+ Create Tool]    │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  CATEGORY FILTERS                                 │  │
│  │  [All] [Surreal Realism] [Anime] [3D]            │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │ Tool Card│  │ Tool Card│  │ Tool Card│             │
│  │          │  │          │  │          │             │
│  │ "Cosmic  │  │ "Concept │  │ "Data    │             │
│  │  Flow    │  │  Combat" │  │  Diorama"│             │
│  │  Visual."│  │          │  │          │             │
│  │          │  │          │  │          │             │
│  │ Category:│  │ Category:│  │ Category:│             │
│  │ Surreal  │  │ Anime    │  │ 3D       │             │
│  │          │  │          │  │          │             │
│  │ Usage:   │  │ Usage:   │  │ Usage:   │             │
│  │ 156x     │  │ 89x      │  │ 23x      │             │
│  │          │  │          │  │          │             │
│  │ [View]   │  │ [View]   │  │ [View]   │             │
│  └──────────┘  └──────────┘  └──────────┘             │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  CREATE TOOL MODAL (when clicked)                │  │
│  │  Tool Name: [Input]                              │  │
│  │  Idea: [Textarea]                                │  │
│  │  Category: [Select]                              │  │
│  │  [Preview Enhancement] [Create Tool]            │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

#### Key Components

1. **ToolGrid**
   - Responsive grid layout
   - Tool cards with description
   - Category badges

2. **ToolCard**
   - Tool name and description
   - Category badge
   - Usage statistics
   - Success rate indicator
   - View details button

3. **CreateToolModal**
   - Form with name, idea, category
   - Preview enhancement button
   - AI-enhanced preview display
   - Create button

#### Responsive Behavior

- Similar to Workflows List page
- Modal full-screen on mobile, centered on desktop

---

### 2.6 Page 5: Monitoring Page (`/monitoring`)

#### Purpose
View usage metrics, cost tracking, and pricing information.

#### Layout Structure

```
┌─────────────────────────────────────────────────────────┐
│  HEADER                                                  │
│  RABA - Monitoring                                      │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  PERIOD SELECTOR                                 │  │
│  │  [Last 7 days ▼] [Last 30 days] [Last 90 days]  │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │ Total    │  │ Videos   │  │ Success  │             │
│  │ Cost     │  │ Generated│  │ Rate     │             │
│  │          │  │          │  │          │             │
│  │ $45.67   │  │ 23       │  │ 87%      │             │
│  └──────────┘  └──────────┘  └──────────┘             │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  COST BREAKDOWN CHART                            │  │
│  │  [Bar/Line Chart by Type]                        │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  COST BY MODEL                                   │  │
│  │  • Gemini 2.5 Flash: $4.55                      │  │
│  │  • Gemini 2.5 Pro: $4.00                        │  │
│  │  • Veo 3.1: $18.50                              │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

#### Key Components

1. **SummaryCards**
   - Total cost, videos generated, success rate
   - Large numbers, trend indicators

2. **CostChart**
   - Recharts or similar
   - Bar/line chart by generation type
   - Responsive sizing

3. **ModelBreakdown**
   - List or table of costs by model
   - Percentage indicators

#### Responsive Behavior

- Stacked cards on mobile
- Side-by-side on desktop
- Charts responsive with mobile-friendly tooltips

---

## 3. Responsive Design Requirements

### 3.1 Breakpoints

| Breakpoint | Min Width | Device Type | Layout Strategy |
|------------|-----------|-------------|-----------------|
| **Mobile** | 0px | Phones | Single column, full width, bottom navigation |
| **Tablet** | 768px | Tablets | 2-column grid, side navigation |
| **Desktop** | 1024px | Laptops | 3-4 column grid, sidebar navigation |
| **Large Desktop** | 1280px | Large monitors | Max-width container, centered content |

### 3.2 Tailwind CSS Configuration

```javascript
// tailwind.config.js
module.exports = {
  theme: {
    screens: {
      'sm': '640px',   // Small tablets
      'md': '768px',   // Tablets
      'lg': '1024px',  // Laptops
      'xl': '1280px',  // Desktops
      '2xl': '1536px', // Large desktops
    },
    container: {
      center: true,
      padding: {
        DEFAULT: '1rem',
        sm: '2rem',
        lg: '4rem',
        xl: '5rem',
        '2xl': '6rem',
      },
    },
  },
}
```

### 3.3 Mobile-First Approach

- **Base styles**: Mobile (0px+)
- **Progressive enhancement**: Add styles for larger breakpoints
- **Touch targets**: Minimum 44×44px on mobile
- **Font sizes**: Responsive (clamp() or Tailwind responsive classes)
- **Spacing**: Smaller on mobile, larger on desktop

### 3.4 Responsive Patterns

#### Navigation
- **Mobile**: Hamburger menu, bottom navigation
- **Tablet**: Horizontal tabs, collapsible sidebar
- **Desktop**: Full sidebar, top navigation

#### Grid Layouts
- **Mobile**: 1 column
- **Tablet**: 2 columns
- **Desktop**: 3-4 columns

#### Forms
- **Mobile**: Stacked inputs, full width
- **Tablet**: 2-column grid where appropriate
- **Desktop**: 3-column grid, larger inputs

#### Video Player
- **Mobile**: Full width, 9:16 aspect ratio maintained
- **Tablet**: Centered, max-width 400px
- **Desktop**: Centered, max-width 500px

### 3.5 Image Optimization

- Use Next.js `<Image>` component
- Responsive `sizes` attribute:
  ```jsx
  <Image
    sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
    ...
  />
  ```
- Lazy loading for offscreen images
- WebP/AVIF formats with fallbacks

### 3.6 Orientation Support

- Handle portrait/landscape on mobile/tablet
- Adjust layout for orientation changes
- Test on real devices

---

## 4. Theme System (Light/Dark Mode)

### 4.1 Implementation Strategy

**Library**: `next-themes` (recommended for Next.js 15)

**Configuration**:
- `darkMode: 'class'` in Tailwind config
- Theme provider wraps entire app
- Three states: `light`, `dark`, `system`
- Persist preference in `localStorage`
- System preference as fallback

### 4.2 Color System

#### Dark Mode (Primary)
```css
/* Background */
--bg-primary: #09090B;      /* Rich Zinc Black */
--bg-secondary: #121217;   /* Deep Charcoal */
--bg-tertiary: #1A1A1F;    /* Lighter Charcoal */

/* Text */
--text-primary: #F2F4F7;   /* Cloud Dancer */
--text-secondary: #A1A1AA; /* Muted Gray */
--text-tertiary: #71717A;  /* Dim Gray */

/* Accents */
--accent-primary: #6366F1;  /* Electric Indigo */
--accent-secondary: #06B6D4; /* Cyber Cyan */
--accent-highlight: #BEF264; /* Neon Lime */

/* Borders */
--border-primary: rgba(255, 255, 255, 0.08);
--border-secondary: rgba(255, 255, 255, 0.12);

/* Glow Effects */
--glow-primary: rgba(99, 102, 241, 0.15);
```

#### Light Mode
```css
/* Background */
--bg-primary: #F2F4F7;     /* Cloud Dancer */
--bg-secondary: #FFFFFF;   /* Pure White */
--bg-tertiary: #E2E8F0;    /* Light Slate */

/* Text */
--text-primary: #0F172A;   /* Ink Navy */
--text-secondary: #475569; /* Slate Gray */
--text-tertiary: #94A3B8;  /* Light Slate */

/* Accents */
--accent-primary: #6366F1;  /* Electric Indigo */
--accent-secondary: #06B6D4; /* Cyber Cyan */
--accent-highlight: #BEF264; /* Neon Lime */

/* Borders */
--border-primary: #E2E8F0;
--border-secondary: #CBD5E1;

/* Shadows */
--shadow-primary: rgba(0, 0, 0, 0.1);
```

### 4.3 Theme Toggle Component

**Location**: Header (global navigation)

**Features**:
- Sun/Moon icon toggle
- Three-state selector (Light/Dark/System)
- Smooth transition (300ms)
- Accessible (keyboard navigation, ARIA labels)

**Implementation**:
```tsx
// components/ThemeToggle.tsx
'use client'

import { useTheme } from 'next-themes'
import { Moon, Sun, Monitor } from 'lucide-react'

export function ThemeToggle() {
  const { theme, setTheme } = useTheme()
  
  return (
    <div className="flex items-center gap-2">
      <button onClick={() => setTheme('light')}>
        <Sun />
      </button>
      <button onClick={() => setTheme('dark')}>
        <Moon />
      </button>
      <button onClick={() => setTheme('system')}>
        <Monitor />
      </button>
    </div>
  )
}
```

### 4.4 Preventing Flash of Unstyled Content (FOUC)

**Critical**: Inject theme script before render

```tsx
// app/layout.tsx
import Script from 'next/script'

export default function RootLayout({ children }) {
  return (
    <html suppressHydrationWarning>
      <head>
        <Script
          id="theme-script"
          strategy="beforeInteractive"
          dangerouslySetInnerHTML={{
            __html: `
              (function() {
                const theme = localStorage.getItem('theme') || 
                  (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
                document.documentElement.classList.add(theme);
              })();
            `,
          }}
        />
      </head>
      <body>{children}</body>
    </html>
  )
}
```

### 4.5 CSS Variables Setup

```css
/* app/globals.css */
@layer base {
  :root {
    /* Light mode colors */
    --bg-primary: #F2F4F7;
    --text-primary: #0F172A;
    /* ... */
  }
  
  .dark {
    /* Dark mode colors */
    --bg-primary: #09090B;
    --text-primary: #F2F4F7;
    /* ... */
  }
}
```

### 4.6 Component-Level Theme Support

- Use CSS variables for all colors
- Test contrast ratios (WCAG AA minimum)
- Handle images/media for both themes
- Smooth transitions on theme change

---

## 5. Caching Strategy

### 5.1 TanStack Query Configuration

```typescript
// lib/query-client.ts
import { QueryClient } from '@tanstack/react-query'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60 * 1000,        // 1 minute
      cacheTime: 5 * 60 * 1000,   // 5 minutes
      refetchOnWindowFocus: false,
      refetchOnReconnect: true,
      refetchOnMount: 'onStale',
      retry: 3,
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    },
  },
})
```

### 5.2 Cache Strategies by Data Type

| Data Type | staleTime | cacheTime | Refetch Strategy |
|-----------|-----------|-----------|------------------|
| **Workflow Status** | 0 (always stale) | 1 minute | Poll every 3-5s |
| **Workflow List** | 30 seconds | 5 minutes | On mount, window focus |
| **Tool List** | 5 minutes | 30 minutes | Manual refresh |
| **Tool Details** | 10 minutes | 1 hour | Manual refresh |
| **Monitoring Summary** | 1 minute | 5 minutes | Poll every 1 minute |
| **Pricing Info** | 1 hour | 24 hours | Manual refresh |

### 5.3 Query Key Structure

```typescript
// Consistent query key patterns
const queryKeys = {
  workflows: {
    all: ['workflows'] as const,
    lists: () => [...queryKeys.workflows.all, 'list'] as const,
    list: (filters: WorkflowFilters) => [...queryKeys.workflows.lists(), filters] as const,
    details: () => [...queryKeys.workflows.all, 'detail'] as const,
    detail: (id: string) => [...queryKeys.workflows.details(), id] as const,
    gate: (id: string) => [...queryKeys.workflows.detail(id), 'gate'] as const,
    gateOutput: (id: string, gate: string) => [...queryKeys.workflows.gate(id), gate] as const,
  },
  tools: {
    all: ['tools'] as const,
    lists: () => [...queryKeys.tools.all, 'list'] as const,
    list: (filters: ToolFilters) => [...queryKeys.tools.lists(), filters] as const,
    details: () => [...queryKeys.tools.all, 'detail'] as const,
    detail: (id: string) => [...queryKeys.tools.details(), id] as const,
  },
  monitoring: {
    summary: (days: number) => ['monitoring', 'summary', days] as const,
    video: (id: string) => ['monitoring', 'video', id] as const,
    pricing: () => ['monitoring', 'pricing'] as const,
  },
}
```

### 5.4 Optimistic Updates

```typescript
// Example: Approve HITL gate
const approveMutation = useMutation({
  mutationFn: approveGate,
  onMutate: async (variables) => {
    // Cancel outgoing refetches
    await queryClient.cancelQueries({ queryKey: ['workflows', 'detail', variables.id] })
    
    // Snapshot previous value
    const previous = queryClient.getQueryData(['workflows', 'detail', variables.id])
    
    // Optimistically update
    queryClient.setQueryData(['workflows', 'detail', variables.id], (old: any) => ({
      ...old,
      hitl_approved: { ...old.hitl_approved, [variables.gate]: true },
    }))
    
    return { previous }
  },
  onError: (err, variables, context) => {
    // Rollback on error
    queryClient.setQueryData(['workflows', 'detail', variables.id], context?.previous)
  },
  onSettled: (data, error, variables) => {
    // Refetch to ensure consistency
    queryClient.invalidateQueries({ queryKey: ['workflows', 'detail', variables.id] })
  },
})
```

### 5.5 Cache Invalidation

```typescript
// Invalidate related queries after mutations
const createWorkflowMutation = useMutation({
  mutationFn: createWorkflow,
  onSuccess: () => {
    // Invalidate workflow list
    queryClient.invalidateQueries({ queryKey: ['workflows', 'list'] })
  },
})

const deleteWorkflowMutation = useMutation({
  mutationFn: deleteWorkflow,
  onSuccess: (_, deletedId) => {
    // Remove from cache
    queryClient.removeQueries({ queryKey: ['workflows', 'detail', deletedId] })
    // Invalidate list
    queryClient.invalidateQueries({ queryKey: ['workflows', 'list'] })
  },
})
```

### 5.6 Server-Side Prefetching

```typescript
// app/workflows/[id]/page.tsx
import { dehydrate, HydrationBoundary, QueryClient } from '@tanstack/react-query'

export default async function WorkflowPage({ params }: { params: { id: string } }) {
  const queryClient = new QueryClient()
  
  // Prefetch workflow data
  await queryClient.prefetchQuery({
    queryKey: ['workflows', 'detail', params.id],
    queryFn: () => fetchWorkflow(params.id),
    staleTime: 60 * 1000, // 1 minute
  })
  
  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <WorkflowDetailClient id={params.id} />
    </HydrationBoundary>
  )
}
```

### 5.7 Background Refetching

```typescript
// Polling for workflow status
const { data, status } = useQuery({
  queryKey: ['workflows', 'detail', workflowId],
  queryFn: () => fetchWorkflow(workflowId),
  enabled: workflowStatus !== 'completed' && workflowStatus !== 'failed',
  refetchInterval: (data) => {
    // Poll every 3 seconds if running, 5 seconds if awaiting approval
    if (data?.status === 'running') return 3000
    if (data?.status?.startsWith('awaiting_')) return 5000
    return false // Stop polling if completed/failed
  },
  refetchIntervalInBackground: true,
})
```

---

## 6. Edge Cases & Error Handling

### 6.1 Network Errors

#### Offline Detection
```typescript
// hooks/useOnlineStatus.ts
export function useOnlineStatus() {
  const [isOnline, setIsOnline] = useState(navigator.onLine)
  
  useEffect(() => {
    const handleOnline = () => setIsOnline(true)
    const handleOffline = () => setIsOnline(false)
    
    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)
    
    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])
  
  return isOnline
}
```

#### Error UI Component
```tsx
// components/ErrorBoundary.tsx
'use client'

import { Component, ReactNode } from 'react'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }
  
  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }
  
  componentDidCatch(error: Error, errorInfo: any) {
    console.error('Error caught by boundary:', error, errorInfo)
  }
  
  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div className="error-boundary">
          <h2>Something went wrong</h2>
          <p>{this.state.error?.message}</p>
          <button onClick={() => this.setState({ hasError: false, error: null })}>
            Try again
          </button>
        </div>
      )
    }
    
    return this.props.children
  }
}
```

### 6.2 Loading States

#### Skeleton Screens
```tsx
// components/WorkflowCardSkeleton.tsx
export function WorkflowCardSkeleton() {
  return (
    <div className="animate-pulse">
      <div className="h-48 bg-gray-200 dark:bg-gray-700 rounded" />
      <div className="mt-4 space-y-2">
        <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4" />
        <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/2" />
      </div>
    </div>
  )
}
```

#### Minimum Display Time
```typescript
// hooks/useMinimumLoadingTime.ts
export function useMinimumLoadingTime(isLoading: boolean, minTime: number = 300) {
  const [showLoading, setShowLoading] = useState(false)
  const startTimeRef = useRef<number | null>(null)
  
  useEffect(() => {
    if (isLoading) {
      startTimeRef.current = Date.now()
      setShowLoading(true)
    } else if (startTimeRef.current !== null) {
      const elapsed = Date.now() - startTimeRef.current
      const remaining = Math.max(0, minTime - elapsed)
      
      setTimeout(() => {
        setShowLoading(false)
        startTimeRef.current = null
      }, remaining)
    }
  }, [isLoading, minTime])
  
  return showLoading
}
```

### 6.3 Empty States

#### Empty State Component
```tsx
// components/EmptyState.tsx
interface EmptyStateProps {
  icon?: ReactNode
  title: string
  description: string
  action?: {
    label: string
    onClick: () => void
  }
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="empty-state">
      {icon && <div className="empty-state-icon">{icon}</div>}
      <h3>{title}</h3>
      <p>{description}</p>
      {action && (
        <button onClick={action.onClick}>{action.label}</button>
      )}
    </div>
  )
}
```

### 6.4 Error Messages

#### User-Friendly Error Messages
```typescript
// lib/error-messages.ts
export const ERROR_MESSAGES = {
  NETWORK_ERROR: 'Connection lost. Please check your internet and try again.',
  RATE_LIMIT: 'Too many requests. Please wait a moment and try again.',
  NOT_FOUND: 'The requested resource was not found.',
  VALIDATION_ERROR: 'Please check your input and try again.',
  SERVER_ERROR: 'Something went wrong on our end. We\'re working on it!',
  TIMEOUT: 'Request took too long. Please try again.',
  UNAUTHORIZED: 'You don\'t have permission to perform this action.',
}

export function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    // Map known error codes to messages
    if (error.message.includes('429')) return ERROR_MESSAGES.RATE_LIMIT
    if (error.message.includes('404')) return ERROR_MESSAGES.NOT_FOUND
    if (error.message.includes('401') || error.message.includes('403')) {
      return ERROR_MESSAGES.UNAUTHORIZED
    }
    if (error.message.includes('timeout')) return ERROR_MESSAGES.TIMEOUT
  }
  
  return ERROR_MESSAGES.SERVER_ERROR
}
```

### 6.5 Retry Logic

#### Exponential Backoff
```typescript
// lib/retry.ts
export async function retryWithBackoff<T>(
  fn: () => Promise<T>,
  maxRetries: number = 3,
  initialDelay: number = 1000
): Promise<T> {
  let lastError: Error
  
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await fn()
    } catch (error) {
      lastError = error as Error
      if (i < maxRetries - 1) {
        const delay = initialDelay * Math.pow(2, i)
        await new Promise(resolve => setTimeout(resolve, delay))
      }
    }
  }
  
  throw lastError!
}
```

### 6.6 Form Validation Edge Cases

- **Long text**: Truncate with "show more" option
- **Special characters**: Sanitize, show warnings
- **File uploads**: Validate size, type, show progress
- **Network interruption**: Save draft, resume on reconnect
- **Browser back/forward**: Preserve form state

### 6.7 Video Player Edge Cases

- **Video load failure**: Show error, retry button
- **Buffering**: Show loading spinner, progress
- **Unsupported format**: Show fallback message
- **Mobile autoplay restrictions**: Show play button
- **Fullscreen API unavailable**: Hide fullscreen button

---

## 7. Component Architecture

### 7.1 Component Structure

```
components/
├── ui/                    # Shadcn/ui components
│   ├── button.tsx
│   ├── input.tsx
│   ├── select.tsx
│   └── ...
├── layout/                # Layout components
│   ├── Header.tsx
│   ├── Navigation.tsx
│   ├── Footer.tsx
│   └── ThemeToggle.tsx
├── workflow/              # Workflow-specific
│   ├── PipelineStepper.tsx
│   ├── WorkflowCard.tsx
│   ├── HITLGateUI.tsx
│   ├── ScriptEditor.tsx
│   └── VideoPlayer.tsx
├── forms/                 # Form components
│   ├── TopicInput.tsx
│   ├── ParameterSelectors.tsx
│   ├── ImageUpload.tsx
│   └── HITLModeToggle.tsx
├── common/                # Shared components
│   ├── ErrorBoundary.tsx
│   ├── EmptyState.tsx
│   ├── LoadingSpinner.tsx
│   ├── Skeleton.tsx
│   └── ErrorMessage.tsx
└── monitoring/            # Monitoring components
    ├── CostBreakdown.tsx
    ├── UsageChart.tsx
    └── SummaryCards.tsx
```

### 7.2 Server vs Client Components

**Server Components (Default)**:
- Layouts
- Static content
- Data fetching (initial load)

**Client Components (`'use client'`)**:
- Interactive elements (buttons, forms)
- State management (useState, useEffect)
- Browser APIs (localStorage, window)
- Event handlers
- TanStack Query hooks
- Theme toggles
- Real-time subscriptions

### 7.3 Custom Hooks

```typescript
// hooks/useWorkflowStatus.ts
export function useWorkflowStatus(workflowId: string) {
  return useQuery({
    queryKey: ['workflows', 'detail', workflowId],
    queryFn: () => fetchWorkflow(workflowId),
    refetchInterval: 3000,
  })
}

// hooks/useHITLGate.ts
export function useHITLGate(workflowId: string) {
  const { data: gateStatus } = useQuery({
    queryKey: ['workflows', 'gate', workflowId],
    queryFn: () => fetchGateStatus(workflowId),
    refetchInterval: 5000,
  })
  
  const approveMutation = useMutation({
    mutationFn: () => approveGate(workflowId),
    onSuccess: () => {
      queryClient.invalidateQueries(['workflows', 'detail', workflowId])
    },
  })
  
  return { gateStatus, approveMutation }
}
```

---

## 8. Real-Time Updates

### 8.1 Polling Strategy

**Workflow Status Polling**:
- **Running workflows**: Poll every 3 seconds
- **Awaiting approval**: Poll every 5 seconds
- **Completed/Failed**: Stop polling
- **Background**: Continue polling when tab hidden

**Implementation**:
```typescript
const { data, status } = useQuery({
  queryKey: ['workflows', 'detail', workflowId],
  queryFn: () => fetchWorkflow(workflowId),
  enabled: shouldPoll,
  refetchInterval: (data) => {
    if (data?.status === 'completed' || data?.status === 'failed') {
      return false
    }
    if (data?.status === 'running') return 3000
    if (data?.status?.startsWith('awaiting_')) return 5000
    return false
  },
  refetchIntervalInBackground: true,
})
```

### 8.2 Connection Status Indicator

```tsx
// components/ConnectionStatus.tsx
export function ConnectionStatus() {
  const isOnline = useOnlineStatus()
  
  if (!isOnline) {
    return (
      <div className="connection-status offline">
        <WifiOff /> Offline - Reconnecting...
      </div>
    )
  }
  
  return null
}
```

### 8.3 Optimistic Updates

- Update UI immediately on user actions
- Rollback on error
- Refetch to ensure consistency

---

## 9. Performance Requirements

### 9.1 Core Web Vitals Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| **LCP** (Largest Contentful Paint) | < 2.5s | First meaningful content |
| **FID** (First Input Delay) | < 100ms | Interactive responsiveness |
| **CLS** (Cumulative Layout Shift) | < 0.1 | Visual stability |

### 9.2 Bundle Size Targets

- **Initial JS bundle**: < 200KB (gzipped)
- **Total page size**: < 1MB (including images)
- **Code splitting**: Route-based, component-based

### 9.3 Image Optimization

- Use Next.js `<Image>` component
- WebP/AVIF formats
- Responsive `sizes` attribute
- Lazy loading for offscreen images
- Blur placeholders

### 9.4 Code Splitting

```typescript
// Dynamic imports for heavy components
const VideoPlayer = dynamic(() => import('@/components/workflow/VideoPlayer'), {
  loading: () => <VideoPlayerSkeleton />,
  ssr: false,
})

const ScriptEditor = dynamic(() => import('@/components/workflow/ScriptEditor'), {
  loading: () => <ScriptEditorSkeleton />,
})
```

### 9.5 Server Components

- Use Server Components by default
- Only mark components as `'use client'` when necessary
- Fetch data in Server Components when possible

---

## 10. Accessibility Requirements

### 10.1 WCAG 2.1 AA Compliance

- **Color contrast**: Minimum 4.5:1 for text, 3:1 for UI components
- **Keyboard navigation**: All interactive elements accessible via keyboard
- **Screen readers**: Proper ARIA labels, semantic HTML
- **Focus indicators**: Visible focus outlines

### 10.2 Semantic HTML

- Use proper heading hierarchy (h1 → h2 → h3)
- Form labels associated with inputs
- Button vs link distinction
- Landmark regions (header, nav, main, footer)

### 10.3 ARIA Labels

```tsx
<button
  aria-label="Toggle dark mode"
  aria-pressed={theme === 'dark'}
  onClick={toggleTheme}
>
  <Moon />
</button>
```

### 10.4 Keyboard Navigation

- Tab order logical
- Escape closes modals
- Enter/Space activates buttons
- Arrow keys for lists/selects

### 10.5 Focus Management

- Focus trap in modals
- Return focus after modal close
- Skip links for main content

---

## 11. Testing Requirements

### 11.1 Unit Tests

- Component rendering
- Hook logic
- Utility functions
- Error handling

### 11.2 Integration Tests

- Form submissions
- API interactions
- Navigation flows
- HITL gate interactions

### 11.3 E2E Tests

- Complete workflow creation
- HITL approval flow
- Video generation end-to-end
- Error recovery

### 11.4 Visual Regression Tests

- Component states (loading, error, empty)
- Responsive breakpoints
- Light/dark mode
- Cross-browser compatibility

### 11.5 Accessibility Tests

- Screen reader testing
- Keyboard navigation
- Color contrast validation
- ARIA attribute verification

---

## 12. Implementation Checklist

### Phase 1: Foundation
- [ ] Next.js 15 project setup
- [ ] Tailwind CSS configuration
- [ ] Shadcn/ui installation
- [ ] Theme system (next-themes)
- [ ] Global layout and navigation
- [ ] Error boundary setup

### Phase 2: Core Pages
- [ ] Create Page (form, validation, submission)
- [ ] Workflow Detail Page (pipeline stepper, polling)
- [ ] Workflows List Page (grid, filters, pagination)

### Phase 3: HITL System
- [ ] HITL Gate UI component
- [ ] Script editor (TipTap)
- [ ] Image gallery with add/remove
- [ ] Feedback submission flow

### Phase 4: Advanced Features
- [ ] Tools Management Page
- [ ] Monitoring Page
- [ ] Real-time status updates
- [ ] Cost breakdown displays

### Phase 5: Polish
- [ ] Responsive design testing
- [ ] Edge case handling
- [ ] Error messages
- [ ] Loading states
- [ ] Empty states
- [ ] Accessibility audit
- [ ] Performance optimization

---

## 13. Additional Considerations

### 13.1 Browser Support

- **Modern browsers**: Chrome, Firefox, Safari, Edge (latest 2 versions)
- **Mobile browsers**: iOS Safari, Chrome Mobile
- **Progressive enhancement**: Graceful degradation for older browsers

### 13.2 Internationalization (Future)

- Prepare for i18n (text extraction, RTL support)
- Date/time formatting
- Number formatting

### 13.3 Analytics

- Track workflow creation
- Monitor error rates
- Measure performance metrics
- User behavior analytics

### 13.4 Security

- Input sanitization
- XSS prevention
- CSRF protection
- Secure file uploads

---

**Document Version**: 1.0  
**Last Updated**: January 2026  
**Status**: Ready for Implementation
