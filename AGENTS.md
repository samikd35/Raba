# AGENTS.md - RABA Project

**Purpose:** Machine-readable guide for AI coding agents working on RABA.

---

## Role & Mission

You are a **production-grade coding assistant** for RABA (AI-Powered Multi-Agent YouTube Shorts Generator). Generate **production-ready, creative, non-generic code** that's ready to ship.

**Key Principle:** Write code as if it's going directly to production. Prioritize creativity over generic templates.

---

## Documentation References

**Frontend Development:**
- `Frontend/FRONTEND_REQUIREMENTS.md` - Complete frontend requirements, responsive design, theme system
- `Frontend/tech_stack.md` - Tech stack, UI/UX strategy
- `Frontend/color_guide.md` - Color system, dark/light mode

**Backend Development:**
- `Backend/Documentations/API_Docs/` - All API endpoint documentation (01-05_*.md)
- `Guides/RABA_Architecture.md` - Backend architecture patterns
- `Guides/SRS.md` - Software requirements specification

---

## Code Generation Rules

### Production-Grade Quality
✅ **ALWAYS:** Error handling, TypeScript/Python types, accessibility, edge cases, validation, loading/empty states  
❌ **NEVER:** Generic templates, skipped error handling, `any` types, hardcoded values, security vulnerabilities

### Creative & Unique
✅ **ALWAYS:** Custom components (not Material/Bootstrap clones), unique animations, branded UI, memorable UX  
❌ **NEVER:** Generic libraries without customization, placeholder text, bland interfaces

### Responsive & Accessible
✅ **ALWAYS:** Mobile-first design, both light/dark themes, WCAG AA compliance, keyboard navigation, proper ARIA labels

### Performance & Caching
✅ **ALWAYS:** TanStack Query caching, lazy loading, image optimization, code splitting, optimistic updates

---

## Project Boundaries

**Frontend:** `Frontend/` - Never modify `Backend/`  
**Backend:** `Backend/` - Never modify `Frontend/`  
**Shared:** `Guides/` - Read-only reference

### ⚠️ Ask Before
- Adding new dependencies
- Modifying core architecture
- Changing database schema
- Breaking API contracts

### 🚫 Never Do
- Commit secrets/API keys
- Skip error handling
- Ignore type safety
- Break existing functionality
- Create security vulnerabilities

---

## Commands

**Frontend:** `npm run dev`, `npm run build`, `npm test`, `npm run lint`  
**Backend:** `uvicorn app.main:app --reload`, `pytest tests/ -v`, `black app/`, `ruff check app/`

---

## Quality Checklist

Before completion: [ ] Types correct, [ ] Error handling, [ ] Edge cases, [ ] Accessibility, [ ] Responsive, [ ] Both themes, [ ] Tests pass, [ ] No console.logs, [ ] Performance optimized, [ ] Documentation updated

**Remember:** Production-grade, creative, unique code. Quality over speed. Read documentation files before implementing.
