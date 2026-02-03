# MVP Requirements Generator (AMRG) — Implementation Plan

## Overview

AMRG is a LangGraph-based, multi-agent backend service that generates template-compliant MVP Product Requirements artifacts for existing Yuba projects.

---

## Phase 1: Foundation & Models

### Task 1.1: Create Enums and Constants ✅
**File:** `models/enums.py`
- [x] `TemplateCode` enum (A1, A2, A3, A4, A5, B1, C1, C2)
- [x] `ResearchMode` enum (off, auto, on)
- [x] `RunStatus` enum (created, awaiting_answers, running, completed, failed)

### Task 1.2: Create State Models ✅
**File:** `models/state_models.py`
- [x] `ContextPack` TypedDict (artifacts + metadata)
- [x] `TemplateRoutingResult` TypedDict (top_templates, confidence, rationale)
- [x] `ClarifyingQuestion` TypedDict (index, question_text, category)
- [x] `AMRGState` TypedDict (full LangGraph state)

### Task 1.3: Create Response Models ✅
**File:** `models/response_models.py`
- [x] `AMRGGenerateRequest` (research_mode, force_regenerate)
- [x] `AMRGGenerateResponse` (run_id, status, questions, coarse_routing)
- [x] `AMRGAnswersRequest` (answers array)
- [x] `AMRGStatusResponse` (status, progress, etc.)
- [x] `AMRGResultsResponse` (prd_json, metadata)
- [x] `ErrorResponse` (error_code, missing_artifacts, message)

---

## Phase 2: Template System

### Task 2.1: Create Template Registry ✅
**File:** `templates/registry.py`
- [x] `TemplateSpec` dataclass (code, name, prompt_path, schema_path, versions)
- [x] `TEMPLATE_REGISTRY` dict mapping TemplateCode → TemplateSpec
- [x] `get_template_spec(code)` function

### Task 2.2: Create JSON Schemas for Each Template ✅
**Directory:** `templates/schemas/`
- [x] `a1_schema.json` (Software/SaaS)
- [x] `a2_schema.json` (Digital Content/EdTech)
- [x] `a3_schema.json` (Platform/Marketplace)
- [x] `a4_schema.json` (Tech-Enabled Service)
- [x] `a5_schema.json` (Fintech)
- [x] `b1_schema.json` (Analog Services)
- [x] `c1_schema.json` (CPG/FMCG)
- [x] `c2_schema.json` (Hardware/IoT)
- [x] `base_schema.json` (common fields for all templates)

### Task 2.3: Create Jinja2 Prompt Templates ✅
**Directory:** `templates/prompts/`
- [x] `routing_coarse.j2` (coarse template routing prompt)
- [x] `routing_final.j2` (final template routing prompt)
- [x] `questions_base.j2` (clarifying questions base prompt)
- [x] `prd_a1.j2` through `prd_c2.j2` (8 PRD generation prompts)
- [ ] `research_planner.j2` (research planning prompt) - *deferred to future*

---

## Phase 3: Services Layer

### Task 3.1: Create Context Loader Service ✅
**File:** `services/context_loader.py`
- [x] `ContextLoaderService` class
- [x] `load_context_pack()` - load VPS v1/v2, BMC v1/v2, Critique, VPC v2 (optional)
- [x] `validate_eligibility()` - check all required artifacts exist
- [x] `extract_metadata()` - extract project title, industry, geography

### Task 3.2: Create Database Adapter Extension ✅
**File:** `services/database_adapter.py`
- [x] Extend `MVPDatabaseAdapter` with AMRG methods:
  - [x] `save_amrg_run()` - save run state
  - [x] `get_amrg_run()` - get run by ID
  - [x] `update_amrg_status()` - update run status
  - [x] `save_amrg_qna()` - save questions/answers
  - [x] `save_amrg_output()` - save PRD JSON output
  - [x] `get_amrg_history()` - get output versions

### Task 3.3: Create Schema Validator Service ✅
**File:** `services/schema_validator.py`
- [x] `SchemaValidatorService` class
- [x] `validate_prd_json()` - validate against template schema
- [x] `get_validation_errors()` - return detailed errors
- [x] `merge_with_base_schema()` - merge template schema with base

---

## Phase 4: Agents

### Task 4.1: Create Base Agent ✅
**File:** `agents/base_agent.py`
- [x] `BaseAMRGAgent` abstract class
- [x] Common AI service integration (reuse AIServiceWrapper)
- [x] Common monitoring context setup
- [x] Abstract methods for subclasses

### Task 4.2: Create Template Router Agent (Coarse) ✅
**File:** `agents/template_router_coarse.py`
- [x] `TemplateRouterCoarseAgent` class
- [x] `route()` method - analyze context, return top 2-3 templates with confidence
- [x] Uses `routing_coarse.j2` prompt

### Task 4.3: Create Clarifying Questions Agent ✅
**File:** `agents/clarifying_questions.py`
- [x] `ClarifyingQuestionsAgent` class
- [x] `generate_questions()` - generate exactly 3 questions
- [x] Q1 must disambiguate between top template candidates when confidence < threshold
- [x] Uses context gaps + coarse routing uncertainty

### Task 4.4: Create Template Router Agent (Final) ✅
**File:** `agents/template_router_final.py`
- [x] `TemplateRouterFinalAgent` class
- [x] `route()` method - use context + 3 answers to lock final template
- [x] Returns single `selected_template_code` + confidence + rationale

### Task 4.5: Create Research Planner Agent (Optional) - *Deferred*
**File:** `agents/research_planner.py`
- [ ] `ResearchPlannerAgent` class - *Deferred to future iteration*
- [ ] `should_research()` - decide if research needed (for auto mode)
- [ ] `plan_research()` - create bounded research plan (max queries, targets)

### Task 4.6: Create Web Researcher (Optional) - *Deferred*
**File:** `agents/web_researcher.py`
- [ ] Reuse existing `WebResearcher` from soln_critique - *Deferred to future iteration*
- [ ] Adapt for AMRG context

### Task 4.7: Create PRD Generation Agent ✅
**File:** `agents/prd_generator.py`
- [x] `PRDGeneratorAgent` class
- [x] `generate_prd()` - render template prompt + call LLM + return JSON
- [x] Uses template-specific `.j2` prompts
- [x] Returns JSON-only output

### Task 4.8: Create Repair Agent ✅
**File:** `agents/repair_agent.py`
- [x] `RepairAgent` class
- [x] `repair_prd()` - fix validation errors (bounded to N attempts)
- [x] Returns repaired JSON or structured error

---

## Phase 5: LangGraph Workflow

### Task 5.1: Create Workflow Orchestrator ✅
**File:** `services/amrg_workflow.py`
- [x] `AMRGWorkflow` class
- [x] Build workflow with nodes:
  1. `eligibility_gate` - validate project + artifacts
  2. `load_context` - load context_pack
  3. `coarse_routing` - initial template routing
  4. `generate_questions` - create 3 clarifying questions
  5. `wait_for_answers` - interrupt/persist state
  6. `normalize_answers` - parse answers
  7. `final_routing` - lock template selection
  8. `research_planner` (conditional) - *deferred*
  9. `web_research` (conditional) - *deferred*
  10. `generate_prd` - generate PRD JSON
  11. `validate_schema` - validate against schema
  12. `repair_prd` (conditional loop) - fix validation errors
  13. `persist_output` - save to database

### Task 5.2: Implement State Persistence ✅
**File:** `services/database_adapter.py` (integrated into AMRGDatabaseAdapter)
- [x] State persistence integrated into database adapter
- [x] `save_amrg_run()` - saves workflow state
- [x] `get_amrg_run()` - retrieves state for resume
- [x] State cleanup on completion

---

## Phase 6: API Layer

### Task 6.1: Create API Endpoints ✅
**File:** `api/endpoints.py`
- [x] `POST /projects/{project_id}/amrg/runs` - start generation, return run_id + questions
- [x] `POST /amrg/runs/{run_id}/answers` - submit answers, trigger PRD generation
- [x] `GET /amrg/runs/{run_id}` - get status and PRD when complete
- [ ] `POST /amrg/runs/{run_id}/regenerate` - regenerate with revisions - *Deferred*
- [x] `GET /projects/{project_id}/amrg/history` - get output versions

### Task 6.2: Integrate Auth & Credits ✅
**File:** `api/endpoints.py`
- [x] Add `get_current_user` dependency
- [x] Add credit check via `resolve_feature_id("mvp_requirements")`
- [x] Super admin bypass pattern
- [ ] Credit consumption on successful generation - *Needs feature registration*

### Task 6.3: Register Router ✅
**File:** `src/mint/main_app.py`
- [x] Import and include AMRG router
- [x] Add to OpenAPI tags

---

## Phase 7: Database & Integration

### Task 7.1: Add Feature to Features Table ✅
**Migration:** `src/mvp/migrations/003_add_mvp_requirements_feature.sql`
- [x] Add `mvp_requirements` feature to Supabase features table
- [x] Configure credit cost (5 credits per generation)

### Task 7.2: Update Feature Mapping ✅
**File:** `src/mint/api/features/dependencies.py`
- [x] Added `mvp-requirements` → `mvp_requirements` mapping
- [x] Added `solution-critique` → `solution_critique` mapping

### Task 7.3: AMRG Database Adapter ✅
**File:** `src/mvp/mvp_req/services/database_adapter.py`
- [x] Created `AMRGDatabaseAdapter` extending `MVPDatabaseAdapter`
- [x] AMRG data stored in `mvp_data.amrg` (no schema changes needed)
- [x] All AMRG-specific save/get methods implemented

---

## Phase 8: Testing & Validation

### Task 8.1: Unit Tests ✅
**Directory:** `src/mvp/mvp_req/tests/`
- [x] `unit_template_registry.py` - Template registry tests
- [x] `unit_schema_validator.py` - Schema validation tests
- [x] `unit_context_loader.py` - Context loader eligibility tests
- [x] `unit_enums.py` - Enum tests (TemplateCode, RunStatus, etc.)

### Task 8.2: Integration Tests ✅
**File:** `src/mvp/mvp_req/tests/integration_workflow.py`
- [x] End-to-end workflow test (start_run, continue_with_answers)
- [x] API endpoint request validation tests
- [x] State persistence/resume tests

**Run tests with:**
```bash
pytest src/mvp/mvp_req/tests/ -v
```

---

## File Structure Summary

```
src/mvp/mvp_req/
├── __init__.py
├── IMPLEMENTATION_PLAN.md
├── req.md
├── templates.md
├── models/
│   ├── __init__.py
│   ├── enums.py
│   ├── state_models.py
│   └── response_models.py
├── templates/
│   ├── __init__.py
│   ├── registry.py
│   ├── schemas/
│   │   ├── base_schema.json
│   │   ├── a1_schema.json
│   │   ├── a2_schema.json
│   │   ├── a3_schema.json
│   │   ├── a4_schema.json
│   │   ├── a5_schema.json
│   │   ├── b1_schema.json
│   │   ├── c1_schema.json
│   │   └── c2_schema.json
│   └── prompts/
│       ├── routing_coarse.j2
│       ├── routing_final.j2
│       ├── questions_base.j2
│       ├── prd_a1.j2
│       ├── prd_a2.j2
│       ├── prd_a3.j2
│       ├── prd_a4.j2
│       ├── prd_a5.j2
│       ├── prd_b1.j2
│       ├── prd_c1.j2
│       ├── prd_c2.j2
│       └── research_planner.j2
├── agents/
│   ├── __init__.py
│   ├── base_agent.py
│   ├── template_router_coarse.py
│   ├── template_router_final.py
│   ├── clarifying_questions.py
│   ├── research_planner.py
│   ├── prd_generator.py
│   └── repair_agent.py
├── services/
│   ├── __init__.py
│   ├── context_loader.py
│   ├── database_adapter.py
│   ├── schema_validator.py
│   ├── amrg_workflow.py
│   └── state_persistence.py
└── api/
    ├── __init__.py
    └── endpoints.py
```

---

## Implementation Order (Recommended)

1. **Phase 1** → Models & Enums (foundation)
2. **Phase 2** → Template System (schemas, registry, prompts)
3. **Phase 3** → Services (context loader, db adapter, validator)
4. **Phase 4** → Agents (router, questions, generator, repair)
5. **Phase 5** → LangGraph Workflow (orchestration)
6. **Phase 6** → API Layer (endpoints, auth, credits)
7. **Phase 7** → Database Integration
8. **Phase 8** → Testing

---

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| VPC v2 Context | Optional | Per user request - use if exists, skip if not |
| AI Service | Reuse `AIServiceWrapper` | Existing pattern with monitoring |
| Credit System | Reuse `CreditService` | System-wide consistency |
| State Persistence | LangGraph checkpoints + DB | Resume capability |
| Research | Reuse `WebResearcher` | Existing Brave Search integration |
| JSON Validation | jsonschema library | Industry standard |

---

## Notes

- Follow existing patterns from `soln_critique` for agent structure
- Use `MVPDatabaseAdapter` for all database operations
- Store AMRG data in `mvp_data.amrg` JSON path
- Credit feature name: `mvp_requirements`
