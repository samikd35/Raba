# Go-To-Market (GTM) Strategy Generator - Implementation Plan

## Executive Summary

Build a **backend-only GTM Strategy Generator** for VMP projects using FastAPI endpoints and a LangGraph RAG workflow. The system will:
- Read from the project's already chunked/embedded artifact corpus (strictly filtered by tenant/workspace/project_id)
- Optionally perform bounded web search when external context is required
- Generate a complete GTM Strategy Pack in a fixed 8-step structure
- Include citations, versioning, and full retrieval/web tool traces

---

## Architecture Overview

### Existing System Integration Points

| Component | Location | Purpose |
|-----------|----------|---------|
| `VMPProjectChunkingService` | `/src/vpm/services/project_chunking_service.py` | Background chunking/embedding after GTM generation |
| `ProjectRAGService` | `/src/mav/chat/services/project_rag_service.py` | Vector similarity search pattern |
| `PitchDeckRAGService` | `/src/mav/Pitch/services/pitch_rag_service.py` | Artifact-aware retrieval (closest pattern) |
| `WebSearchService` | `/src/mav/chat/services/web_search_service.py` | Bounded web search with evidence extraction |
| `PitchDeckWorkflow` | `/src/mav/Pitch/workflow/pitch_workflow.py` | LangGraph workflow pattern to follow |
| `PitchDeckDatabaseAdapter` | `/src/mav/Pitch/adapters/database_adapter.py` | JSONB storage pattern in vmp_projects |
| `get_client_config` | `/src/mint/api/ai/config.py` | Azure OpenAI LLM/Embedding configuration |
| `EmbeddingService` | `/src/mint/api/services/ai/embedding_service.py` | Embedding generation |

### Data Storage

GTM data will be stored in `vmp_projects.gtm_data` (new JSONB column) following the same pattern as `pitch_deck_data`.

---

## Directory Structure

```
Backend/src/mav/Pitch/GTM/
├── __init__.py
├── models.py                    # Pydantic models, LangGraph state, API models
├── adapters/
│   ├── __init__.py
│   └── database_adapter.py      # GTM CRUD operations
├── services/
│   ├── __init__.py
│   └── gtm_rag_service.py       # Step-scoped RAG with artifact routing
├── workflow/
│   ├── __init__.py
│   ├── gtm_workflow.py          # LangGraph 10-node workflow
│   └── prompts/
│       ├── __init__.py
│       └── gtm_prompts.py       # All GTM prompt templates
└── api/
    ├── __init__.py
    └── endpoints.py             # FastAPI endpoints
```

---

## Phase 1: Database Schema

### Task 1.1: Add GTM columns to vmp_projects

**File:** `/Backend/src/mav/Pitch/GTM/migrations/001_add_gtm_columns.sql`

```sql
-- Add gtm_data column to store GTM strategy versions
ALTER TABLE vmp_projects 
ADD COLUMN IF NOT EXISTS gtm_data JSONB DEFAULT '{}'::jsonb;

-- Add gtm_status column to track generation status
ALTER TABLE vmp_projects 
ADD COLUMN IF NOT EXISTS gtm_status VARCHAR DEFAULT 'not_started'
CHECK (gtm_status IN ('not_started', 'processing', 'completed', 'failed'));

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_vmp_projects_gtm_status ON vmp_projects(gtm_status);
```

### Task 1.2: Update tables.sql documentation

Add the new columns to `@/Backend/docs/tables.sql:L1441-L1474` documentation.

---

## Phase 2: Data Models

### Task 2.1: Create models.py

**File:** `/Backend/src/mav/Pitch/GTM/models.py`

**Key Models:**

```python
# Enums
class GTMStepType(str, Enum):
    PROBLEM = "problem"
    AUDIENCE_ICP = "audience_icp"
    MARKET_INSIGHTS = "market_insights"
    VALUE_PROPOSITION = "value_proposition"
    MESSAGING = "messaging"
    CHANNELS = "channels"
    CUSTOMER_SUCCESS = "customer_success"
    GOALS_METRICS = "goals_metrics"

class EvidenceGrade(str, Enum):
    SUFFICIENT = "SUFFICIENT"
    PARTIAL = "PARTIAL"
    INSUFFICIENT = "INSUFFICIENT"

class GTMGenerationStatus(str, Enum):
    NOT_STARTED = "not_started"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

# Step Content
class GTMStepContent(BaseModel):
    step: int
    name: str
    content: Dict[str, Any]  # decisions, plan, experiments
    description: str  # rationale + citations [P#]/[W#]
    sources_used: List[str]
    assumptions_applied: List[str]

# Execution Layer
class ExecutionPlan30_60_90(BaseModel):
    days_0_30: List[Dict[str, Any]]
    days_31_60: List[Dict[str, Any]]
    days_61_90: List[Dict[str, Any]]

class ExperimentBacklog(BaseModel):
    channel_experiments: List[Dict[str, Any]]
    messaging_experiments: List[Dict[str, Any]]

class MetricsDashboardSpec(BaseModel):
    north_star: str
    funnel_kpis: List[Dict[str, Any]]
    targets_30_60_90: Dict[str, Any]

# Citations
class ProjectCitation(BaseModel):
    id: str  # P1, P2, etc.
    type: Literal["project"] = "project"
    artifact_ref: str
    artifact_version: Optional[int]
    chunk_ref: str
    snippet: str

class WebCitation(BaseModel):
    id: str  # W1, W2, etc.
    type: Literal["web"] = "web"
    url: str
    title: str
    domain: str
    snippet: str
    fetched_at: str

# Full GTM Pack
class GTMStrategyPack(BaseModel):
    version: int
    summary: str
    steps: List[GTMStepContent]  # 8 steps
    channel_plan: Dict[str, Any]
    customer_success_motion: Dict[str, Any]
    metrics_plan: MetricsDashboardSpec
    execution_plan_30_60_90: ExecutionPlan30_60_90
    experiment_backlog: ExperimentBacklog
    sources: List[Union[ProjectCitation, WebCitation]]
    run_trace: Dict[str, Any]
    consistency_check_results: Dict[str, Any]
    created_at: str
    created_by: Optional[str]
    status: str

# LangGraph State
class GTMState(TypedDict, total=False):
    # Inputs
    project_id: str
    tenant_id: str
    user_id: str
    context_constraints: Dict[str, Any]  # geography, timeline, budget, etc.
    
    # Project Context
    project_summary: str
    available_artifacts: List[str]
    artifact_version_map: Dict[str, int]  # Track latest versions
    enhanced_context: Dict[str, Any]
    
    # GTM Planning
    gtm_steps_plan: List[Dict[str, Any]]  # 8 steps with deliverables
    execution_layer_plan: Dict[str, Any]
    
    # Current Step Processing
    current_step_index: int
    current_step_spec: Dict[str, Any]
    current_retrieval_query: str
    current_artifact_hints: List[str]
    current_project_evidence: List[Dict[str, Any]]
    current_web_evidence: List[Dict[str, Any]]
    current_evidence_grade: str
    current_missing_items: List[str]
    current_next_step: str
    
    # Web Research
    web_queries: List[str]
    extraction_targets: List[str]
    
    # Accumulated Steps
    steps_draft: List[Dict[str, Any]]
    all_project_citations: List[Dict[str, Any]]
    all_web_citations: List[Dict[str, Any]]
    
    # Final Output
    gtm_pack: Dict[str, Any]
    consistency_issues: List[Dict[str, Any]]
    auto_fixes: List[Dict[str, Any]]
    
    # Trace
    tool_trace: Dict[str, Any]
    start_time: str
    
    # Output
    gtm_version: int
    generation_status: str
    error_message: Optional[str]

# API Models
class GenerateGTMRequest(BaseModel):
    geography_focus: Optional[str] = None
    launch_timeline: Optional[str] = None
    budget_band: Optional[str] = None
    target_segment_priority: Optional[str] = None
    deck_purpose_alignment: Optional[str] = None  # fundraising vs sales
    product_stage: Optional[str] = None

class GenerateGTMResponse(BaseModel):
    gtm_id: str
    version: int
    status: str
    message: str

class GTMPackResponse(BaseModel):
    project_id: str
    version: int
    summary: str
    steps: List[GTMStepContent]
    channel_plan: Dict[str, Any]
    customer_success_motion: Dict[str, Any]
    metrics_plan: Dict[str, Any]
    execution_plan_30_60_90: Dict[str, Any]
    experiment_backlog: Dict[str, Any]
    sources: List[Union[ProjectCitation, WebCitation]]
    created_at: str
    run_trace: Optional[Dict[str, Any]]

class GTMStatusResponse(BaseModel):
    project_id: str
    version: int
    status: str
    message: str
    progress: Optional[Dict[str, Any]]
```

---

## Phase 3: RAG Service

### Task 3.1: Create gtm_rag_service.py

**File:** `/Backend/src/mav/Pitch/GTM/services/gtm_rag_service.py`

**Key Features:**
- Step-scoped retrieval with artifact hints per GTM step
- Version-aware retrieval (prefer v2 over v1)
- Re-ranking based on artifact type relevance
- Format evidence for prompt context

**Artifact Hints per GTM Step:**

```python
GTM_STEP_ARTIFACT_HINTS = {
    "problem": ["vmp_market_research", "vmp_hypothesis", "vmp_assumptions"],
    "audience_icp": ["vmp_persona", "vmp_customer_profile_v2", "vmp_questionnaire"],
    "market_insights": ["vmp_market_research"],  # + web_allowed
    "value_proposition": ["vmp_value_map", "vmp_vps_v2", "vmp_soln_critique"],
    "messaging": ["vmp_vps_v2", "vmp_customer_profile_v2", "vmp_pitch_deck"],
    "channels": ["vmp_bmc_v2", "vmp_market_research", "vmp_questionnaire"],  # + web_allowed
    "customer_success": ["vmp_bmc_v2", "vmp_mvp_requirements", "vmp_soln_critique"],
    "goals_metrics": ["vmp_hypothesis", "vmp_assumptions", "vmp_mvp_requirements"],
}

# Steps that allow web research
GTM_STEPS_WEB_ALLOWED = {"market_insights", "channels"}
```

**Version Priority Boost:**

```python
VERSION_PRIORITY_BOOST = {
    "vmp_bmc_v2": 0.20,
    "vmp_vps_v2": 0.20,
    "vmp_customer_profile_v2": 0.15,
    "vmp_mvp_requirements": 0.12,
    "vmp_market_research": 0.12,
    "vmp_bmc_v1": 0.05,
    "vmp_vps_v1": 0.05,
}
```

---

## Phase 4: Prompts

### Task 4.1: Create gtm_prompts.py

**File:** `/Backend/src/mav/Pitch/GTM/workflow/prompts/gtm_prompts.py`

**Prompts to Implement (from agent.md):**

1. **SYSTEM_PROMPT** - Global rules for GTM generation
2. **GTM_PLANNER_PROMPT** - Define 8-step structure + execution layer
3. **STEP_SPEC_BUILDER_PROMPT** - Tighten expectations per step
4. **RETRIEVAL_QUERY_BUILDER_PROMPT** - Artifact-aware query construction
5. **EVIDENCE_GRADER_PROMPT** - Grade sufficiency, determine web routing
6. **WEB_RESEARCH_PLANNER_PROMPT** - Plan bounded web queries (3-6 max)
7. **WEB_EVIDENCE_EXTRACTOR_PROMPT** - Extract evidence from web pages
8. **STEP_WRITER_PROMPT** - Generate step content with decisions, actions, experiments
9. **CROSS_STEP_CONSISTENCY_PROMPT** - Verify ICP↔positioning↔channels↔metrics alignment
10. **ASSEMBLER_PROMPT** - Compile final GTM pack

---

## Phase 5: LangGraph Workflow

### Task 5.1: Create gtm_workflow.py

**File:** `/Backend/src/mav/Pitch/GTM/workflow/gtm_workflow.py`

**10-Node Workflow:**

```
┌─────────────────────┐
│ 1. LoadProjectContext│
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│   2. GTMPlanner     │
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│   3. StepLoop       │◄──────────────────┐
│   (for each step)   │                   │
└──────────┬──────────┘                   │
           │                              │
┌──────────▼──────────┐                   │
│4. StepSpecBuilder   │                   │
└──────────┬──────────┘                   │
           │                              │
┌──────────▼──────────┐                   │
│5. RetrievalQueryBuilder│                │
└──────────┬──────────┘                   │
           │                              │
┌──────────▼──────────┐                   │
│6. ProjectRetrieve   │                   │
└──────────┬──────────┘                   │
           │                              │
┌──────────▼──────────┐                   │
│7. EvidenceGrader    │                   │
└──────────┬──────────┘                   │
           │                              │
      ┌────┴────┐                         │
      │ Route   │                         │
      └────┬────┘                         │
           │                              │
    ┌──────┴──────┐                       │
    ▼             ▼                       │
┌────────┐  ┌──────────┐                  │
│ Write  │  │8. WebPlan│                  │
│ Step   │  └────┬─────┘                  │
└────┬───┘       │                        │
     │     ┌─────▼─────┐                  │
     │     │9. WebSearch│                 │
     │     └─────┬─────┘                  │
     │           │                        │
     │     ┌─────▼─────┐                  │
     │     │Write Step │                  │
     │     └─────┬─────┘                  │
     │           │                        │
     └─────┬─────┘                        │
           │                              │
┌──────────▼──────────┐                   │
│ 10. StepWriter      │                   │
└──────────┬──────────┘                   │
           │                              │
      ┌────┴────┐                         │
      │ More    │─── yes ─────────────────┘
      │ Steps?  │
      └────┬────┘
           │ no
┌──────────▼──────────┐
│11. ConsistencyCheck │
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│  12. Assembler      │
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│   13. Persist       │
└──────────┬──────────┘
           │
          END
```

**Node Implementations:**

1. **LoadProjectContext** - Load project summary, artifact inventory, version map
2. **GTMPlanner** - Output fixed 8-step structure + execution layer config
3. **StepSpecBuilder** - Define step objective, must_include_checks, evidence_priority
4. **RetrievalQueryBuilder** - Build artifact-aware retrieval query
5. **ProjectRetrieve** - Vector search with strict project/tenant filter
6. **EvidenceGrader** - SUFFICIENT/PARTIAL/INSUFFICIENT, recommend next step
7. **WebResearchPlanner** - Plan 3-6 search queries (only if step allows web)
8. **WebSearch** - Execute searches, extract evidence
9. **StepWriter** - Generate content: decisions, plan, experiments
10. **CrossStepConsistencyCheck** - Verify cross-step alignment
11. **Assembler** - Compile final GTM pack with citations
12. **Persist** - Save to database with versioning

---

## Phase 6: Database Adapter

### Task 6.1: Create database_adapter.py

**File:** `/Backend/src/mav/Pitch/GTM/adapters/database_adapter.py`

**Key Methods:**

```python
class GTMDatabaseAdapter:
    async def verify_project_access(project_id, tenant_id) -> bool
    async def load_project_context(project_id, tenant_id) -> Dict
    async def get_project_summary(project_id, tenant_id) -> Dict
    async def get_gtm_data(project_id, tenant_id) -> Dict
    async def get_next_version(project_id, tenant_id) -> int
    async def update_gtm_status(project_id, tenant_id, status, error=None) -> bool
    async def save_gtm_version(project_id, tenant_id, user_id, gtm_pack) -> bool
    async def get_gtm_version(project_id, tenant_id, version=None) -> Dict
    async def list_gtm_versions(project_id, tenant_id) -> List[Dict]
```

---

## Phase 7: API Endpoints

### Task 7.1: Create endpoints.py

**File:** `/Backend/src/mav/Pitch/GTM/api/endpoints.py`

**Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| POST | `/mav/projects/{project_id}/gtm/generate` | Trigger GTM generation (async) |
| GET | `/mav/projects/{project_id}/gtm` | Get latest or specific GTM version |
| GET | `/mav/projects/{project_id}/gtm/versions` | List all GTM versions |
| GET | `/mav/projects/{project_id}/gtm/status` | Get generation status |

---

## Phase 8: Chunking Integration

### Task 8.1: Add GTM feature type to VMPProjectChunkingService

**File:** `/Backend/src/vpm/services/project_chunking_service.py`

Add `GTM = "vmp_gtm"` to `VMPFeatureType` enum.

### Task 8.2: Create GTM formatter

Add `_format_gtm` method to format GTM strategy pack for chunking:

```python
def _format_gtm(self, data: Dict[str, Any], persona_id: Optional[str] = None) -> str:
    """Format GTM Strategy Pack as text for chunking and embedding."""
    gtm = data.get("gtm_pack", {})
    if not gtm:
        return ""
    
    lines = [
        "=== GO-TO-MARKET STRATEGY ===",
        "",
        f"Version: {gtm.get('version', 1)}",
        "",
        f"SUMMARY: {gtm.get('summary', '')}",
        "",
    ]
    
    # Format each step
    for step in gtm.get("steps", []):
        lines.append(f"--- STEP {step.get('step')}: {step.get('name')} ---")
        content = step.get("content", {})
        if content.get("decisions"):
            lines.append("DECISIONS:")
            for d in content.get("decisions", []):
                lines.append(f"  - {d}")
        # ... continue for plan, experiments
        lines.append("")
    
    # Format execution plan, metrics, etc.
    ...
    
    return "\n".join(lines)
```

### Task 8.3: Trigger background chunking after GTM generation

In workflow's Persist node, call:

```python
await chunk_vmp_feature_background(
    project_id=project_id,
    tenant_id=tenant_id,
    feature_type=VMPFeatureType.GTM,
    feature_data={"gtm_pack": gtm_pack}
)
```

---

## Phase 9: Router Registration

### Task 9.1: Register GTM router in main_app.py

**File:** `/Backend/src/main_app.py`

```python
from src.mav.Pitch.GTM.api.endpoints import router as gtm_router

app.include_router(gtm_router, prefix="/api/v1", tags=["GTM Strategy Generator"])
```

---

## Implementation Order & Dependencies

```
Phase 1: Database Schema
    └── No dependencies, standalone migration

Phase 2: Models
    └── No dependencies

Phase 3: RAG Service
    ├── Depends on: Phase 2 (models)
    └── Uses: ProjectRAGService pattern, EmbeddingService

Phase 4: Prompts
    └── Depends on: Phase 2 (models for understanding schema)

Phase 5: LangGraph Workflow
    ├── Depends on: Phase 2, 3, 4
    └── Uses: WebSearchService, RAG Service, Prompts

Phase 6: Database Adapter
    ├── Depends on: Phase 1 (schema), Phase 2 (models)
    └── Uses: get_service_role_client

Phase 7: API Endpoints
    ├── Depends on: Phase 2, 5, 6
    └── Uses: Workflow, Database Adapter

Phase 8: Chunking Integration
    ├── Depends on: Phase 2 (models)
    └── Modifies: VMPProjectChunkingService

Phase 9: Router Registration
    └── Depends on: Phase 7
```

---

## Testing Strategy

### Unit Tests
- Test each LangGraph node independently
- Test RAG service artifact routing
- Test database adapter CRUD operations

### Integration Tests
- Test full workflow execution with mock LLM
- Test API endpoints with test project

### E2E Tests
- Generate GTM for real project with all artifacts
- Verify citations reference actual chunks
- Verify web sources are accessible

---

## Estimated Effort

| Phase | Tasks | Estimated Time |
|-------|-------|----------------|
| 1 | Database Schema | 0.5 hour |
| 2 | Models | 1 hour |
| 3 | RAG Service | 1.5 hours |
| 4 | Prompts | 2 hours |
| 5 | LangGraph Workflow | 3 hours |
| 6 | Database Adapter | 1 hour |
| 7 | API Endpoints | 1 hour |
| 8 | Chunking Integration | 0.5 hour |
| 9 | Router Registration | 0.5 hour |
| **Total** | | **~11 hours** |

---

## Success Criteria

1. ✅ Given a valid `project_id`, returns complete GTM Strategy Pack (all 8 steps)
2. ✅ Web search used only when needed (market_insights, channels steps)
3. ✅ All external claims are source-backed with citations
4. ✅ Output consistent with project's latest v2 artifacts
5. ✅ Result persisted with versioning and retrievable sources + run trace
6. ✅ No cross-project leakage in retrieval or output
7. ✅ GTM output is chunked/embedded for future "Chat with Project" usage
