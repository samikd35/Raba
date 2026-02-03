# Module 3 Bootstrap Route - Implementation Guide

This document provides step-by-step implementation tasks for the Module 3 Bootstrap Route feature. Each task references existing patterns in the codebase to ensure consistency.

---

## Pre-Implementation Analysis Summary

### Existing Patterns Identified

| Component | Existing Pattern | Location |
|-----------|-----------------|----------|
| **Database** | `vmp_projects` table with JSONB columns | `docs/tables.sql:1073-1100` |
| **Credit System** | `CreditService.consume_feature()` with idempotency via `request_id` | `src/mint/api/credit/service.py` |
| **Super Admin Bypass** | `is_super_admin = roles[0] == "super_admin"` | All endpoint files |
| **VPS/BMC Generation** | `VPSService`, `BMCService` with context loaders | `src/mvp/services/vps_service.py`, `src/mvp/bmc/services/bmc_service.py` |
| **Context Loading** | `MVPContextLoader`, `BMCContextLoader` | `src/mvp/utils/context_loader.py`, `src/mvp/bmc/utils/bmc_context_loader.py` |
| **Vector/RAG** | `YubaVectorAdapter.dual_context_search()` | `src/vpm/adapters/vector_adapter.py` |
| **Search Service** | `BraveSearchProvider`, `TavilySearchProvider`, `SerperSearchProvider` | `src/mint/providers/search.py` |
| **Web Research** | `WebResearcher` with batch execution | `src/mvp/soln_critique/services/web_researcher.py` |
| **Workflow State** | `save_workflow_state()`, `CheckpointManager` | `src/mint/workflow.py`, `src/mint/utils/checkpointer.py` |
| **Auth** | `get_current_user` dependency | `src/mint/api/auth_v2/utils.py` |

### SRS vs Existing System Conflicts

| SRS Requirement | Existing System | Resolution |
|-----------------|-----------------|------------|
| `pv_report_id NOT NULL` in `vmp_projects` | SRS wants bootstrap without PV report | **Add nullable `pv_report_id` OR create placeholder document** |
| Credit deduction at finalization | Existing pattern deducts after action completes | ✅ Consistent |
| Vector storage with `source_type` | Existing uses `pv_report`, `actionable_insights` | **Add new source types for bootstrap** |

---

## Implementation Tasks

### Phase 1: Database Schema Updates

#### Task 1.1: Add Bootstrap Columns to `vmp_projects` Table

**File to Modify**: Create new migration file  
**Pattern Reference**: `docs/migrations/add_vpc_image_url_column.sql`

```sql
-- Migration: Add Module 3 Bootstrap columns to vmp_projects

ALTER TABLE public.vmp_projects
  ADD COLUMN IF NOT EXISTS enhanced_context JSONB DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS context_mode TEXT NOT NULL DEFAULT 'normal' 
    CHECK (context_mode IN ('normal', 'bootstrap', 'hybrid')),
  ADD COLUMN IF NOT EXISTS context_status TEXT NOT NULL DEFAULT 'not_started'
    CHECK (context_status IN (
      'not_started', 'embedding', 'questions_pending', 'answers_received', 
      'researching', 'payment_required', 'context_ready', 'context_confirmed', 'failed'
    )),
  ADD COLUMN IF NOT EXISTS context_version INT NOT NULL DEFAULT 1;

-- Make pv_report_id nullable for bootstrap projects
ALTER TABLE public.vmp_projects
  ALTER COLUMN pv_report_id DROP NOT NULL;

-- Add index for efficient querying by context_mode
CREATE INDEX IF NOT EXISTS idx_vmp_projects_context_mode ON public.vmp_projects(context_mode);

COMMENT ON COLUMN public.vmp_projects.enhanced_context IS 'Stores bootstrap-generated context pack with draft/confirmed fields';
COMMENT ON COLUMN public.vmp_projects.context_mode IS 'normal=standard workflow, bootstrap=Module 3 direct entry, hybrid=mixed';
COMMENT ON COLUMN public.vmp_projects.context_status IS 'Status of bootstrap context generation workflow';
```

**Verification**: Update `docs/tables.sql` to reflect the new schema.

---

#### Task 1.2: Register Bootstrap Feature in `module_features` Table

**Pattern Reference**: Existing features in `module_features` table

```sql
INSERT INTO public.module_features (name, display_name, description, feature_type, credit_cost, is_active)
VALUES (
  'module3_bootstrap_context',
  'Module 3 Bootstrap Context Generation',
  'Generate enhanced context pack for direct Module 3 entry without completing Modules 1-2',
  'generator',
  15,  -- Adjust based on business requirements
  true
);
```

---

### Phase 2: Core Services

#### Task 2.1: Create Bootstrap Database Adapter

**File to Create**: `src/mvp/bootstrap/adapters/database_adapter.py`  
**Pattern Reference**: `src/mvp/adapters/database_adapter.py`

```python
# Key methods to implement:
class BootstrapDatabaseAdapter:
    def create_bootstrap_project(self, tenant_id, user_id, name, idea_text, file_keys) -> Dict
    def update_context_status(self, project_id, tenant_id, status) -> bool
    def save_clarifying_questions(self, project_id, tenant_id, questions) -> bool
    def save_clarifying_answers(self, project_id, tenant_id, answers) -> bool
    def save_enhanced_context(self, project_id, tenant_id, enhanced_context, version) -> bool
    def get_bootstrap_project(self, project_id, tenant_id) -> Optional[Dict]
    def confirm_enhanced_context(self, project_id, tenant_id, confirmed_context) -> bool
```

---

#### Task 2.2: Create PDF Extraction Service

**File to Create**: `src/mvp/bootstrap/services/pdf_extractor.py`  
**Pattern Reference**: Market research document upload (if exists), or use PyPDF2/pdfplumber

```python
# Key methods to implement:
class PDFExtractorService:
    async def extract_text_from_pdf(self, file_path: str) -> str
    async def extract_text_from_files(self, file_keys: List[str]) -> List[Dict[str, Any]]
```

**Dependencies**: `PyPDF2` or `pdfplumber` (check if already in requirements.txt)

---

#### Task 2.3: Create Bootstrap Embedding Service

**File to Create**: `src/mvp/bootstrap/services/embedding_service.py`  
**Pattern Reference**: `src/vpm/adapters/vector_adapter.py`, `src/mint/api/services/ai/vector_search_service.py`

```python
# Key methods to implement:
class BootstrapEmbeddingService:
    async def chunk_content(self, content: str, source_type: str, metadata: Dict) -> List[Dict]
    async def embed_chunks(self, chunks: List[Dict]) -> List[Dict]  # Add embedding vector
    async def store_chunks(self, project_id: str, chunks: List[Dict]) -> bool
    async def retrieve(self, project_id: str, query: str, top_k: int, source_filters: List[str]) -> List[Dict]
```

**Storage Table**: Use existing `chunks` table with new `source_type` values:
- `bootstrap_idea_text`
- `bootstrap_pdf_extract`
- `bootstrap_qa_answer`
- `bootstrap_web_research`

---

#### Task 2.4: Create Question Generation Service

**File to Create**: `src/mvp/bootstrap/services/question_generator.py`  
**Pattern Reference**: Field prep questionnaire generation (`src/vpm/services/field_prep_service.py`)

```python
# Priority ladder from SRS:
QUESTION_PRIORITIES = {
    "P0": [  # Must-have for VPS/BMC
        "target_customer_segment",
        "geography_market_scope", 
        "problem_pain_impact",
        "solution_overview",
        "differentiation",
        "monetization_hypothesis"
    ],
    "P1": [  # Improves BMC
        "channels_distribution",
        "alternatives_competitors",
        "constraints_regulatory"
    ],
    "P2": [  # Nice-to-have
        "success_signals",
        "key_partner_dependencies"
    ]
}

class QuestionGeneratorService:
    async def generate_questions(
        self, 
        project_id: str, 
        tenant_id: str,
        max_questions: int = 6
    ) -> List[Dict[str, Any]]
```

Uses RAG over embedded intake content to determine which P0/P1/P2 questions are needed.

---

#### Task 2.5: Create Web Research Service

**File to Create**: `src/mvp/bootstrap/services/research_service.py`  
**Pattern Reference**: `src/mvp/soln_critique/services/web_researcher.py`

```python
class BootstrapResearchService:
    def __init__(self):
        self.web_researcher = WebResearcher()  # Reuse existing
    
    async def generate_research_queries(
        self, 
        project_id: str, 
        tenant_id: str
    ) -> List[Dict[str, Any]]
    
    async def execute_research(
        self, 
        queries: List[Dict]
    ) -> Dict[str, Any]  # Includes numbered sources
    
    async def store_research_results(
        self, 
        project_id: str, 
        results: Dict
    ) -> bool
```

**Key Constraint**: Research can only ENHANCE, not change the idea's invariants (customer segment, geography, problem, solution type).

---

#### Task 2.6: Create Enhanced Context Composer

**File to Create**: `src/mvp/bootstrap/services/context_composer.py`  
**Pattern Reference**: SRS Section 7 (Enhanced Context JSON Contract)

```python
class EnhancedContextComposer:
    async def compose_enhanced_context(
        self,
        project_id: str,
        tenant_id: str
    ) -> Dict[str, Any]  # Returns the enhanced_context structure
```

Output structure:
```json
{
  "version": 1,
  "draft": {
    "IdeaSummary": "...",
    "CustomerSegments": ["..."],
    "Problem": { "who", "what", "where", "why_now" },
    "SolutionOverview": "...",
    "Differentiation": ["..."],
    "BusinessModelSeeds": { ... },
    "AlternativesAndCompetition": { ... },
    "ConstraintsAndRisks": ["..."],
    "Research": {
      "body": "... [1] ... [2] ...",
      "sources": [{ "n": 1, "title", "publisher", "url", "captured_at", "snippet" }]
    }
  },
  "confirmed": null,
  "metadata": {
    "context_mode": "bootstrap",
    "invariants": { "customer_segment", "geography", "core_problem", "core_solution_type" }
  }
}
```

---

### Phase 3: LangGraph Workflow

#### Task 3.1: Create Bootstrap Workflow Graph

**File to Create**: `src/mvp/bootstrap/workflow/bootstrap_graph.py`  
**Pattern Reference**: `src/market_research/services/analysis_workflow.py`, `src/mint/workflow.py`

```python
from langgraph.graph import StateGraph, END

class Module3BootstrapGraph:
    """LangGraph workflow for bootstrap context generation."""
    
    def _build_workflow(self) -> StateGraph:
        workflow = StateGraph(BootstrapState)
        
        # Add nodes
        workflow.add_node("load_raw_input", self._load_raw_input)
        workflow.add_node("pdf_extract", self._pdf_extract)
        workflow.add_node("chunk_embed", self._chunk_embed)
        workflow.add_node("question_gen", self._question_gen)  # → INTERRUPT
        workflow.add_node("answers_ingest", self._answers_ingest)  # Resume point
        workflow.add_node("research_plan", self._research_plan)
        workflow.add_node("web_search", self._web_search)
        workflow.add_node("compose_context", self._compose_context)
        workflow.add_node("finalize_and_charge", self._finalize_and_charge)
        
        # Add edges
        workflow.add_edge("load_raw_input", "pdf_extract")
        workflow.add_edge("pdf_extract", "chunk_embed")
        workflow.add_edge("chunk_embed", "question_gen")
        # INTERRUPT after question_gen - wait for user answers
        workflow.add_edge("answers_ingest", "research_plan")
        workflow.add_edge("research_plan", "web_search")
        workflow.add_edge("web_search", "compose_context")
        workflow.add_edge("compose_context", "finalize_and_charge")
        workflow.add_edge("finalize_and_charge", END)
        
        workflow.set_entry_point("load_raw_input")
        return workflow
    
    async def start_run(self, project_id, tenant_id, user_id, idea_text, file_keys) -> Dict
    async def resume_with_answers(self, project_id, tenant_id, answers) -> Dict
```

---

#### Task 3.2: Create Bootstrap State Model

**File to Create**: `src/mvp/bootstrap/models/state_models.py`  
**Pattern Reference**: `src/mvp/mvp_req/models/state_models.py`

```python
from typing import TypedDict, List, Dict, Any, Optional

class BootstrapState(TypedDict):
    project_id: str
    tenant_id: str
    user_id: str
    
    # Raw input
    idea_text: Optional[str]
    file_keys: List[str]
    
    # Extracted content
    pdf_extracts: List[Dict[str, Any]]
    
    # Embeddings
    chunks_embedded: bool
    
    # Questions
    clarifying_questions: List[Dict[str, Any]]
    clarifying_answers: List[Dict[str, Any]]
    
    # Research
    research_queries: List[Dict[str, Any]]
    research_results: Dict[str, Any]
    
    # Output
    enhanced_context: Optional[Dict[str, Any]]
    
    # Status
    status: str  # Maps to context_status
    error: Optional[str]
```

---

### Phase 4: API Endpoints

#### Task 4.1: Create Bootstrap Router

**File to Create**: `src/mvp/bootstrap/api/endpoints.py`  
**Pattern Reference**: `src/mvp/mvp_req/api/endpoints.py`, `src/mvp/api/endpoints.py`

```python
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from typing import List, Optional

router = APIRouter(
    prefix="/mvp/bootstrap",
    tags=["Module 3 Bootstrap"]
)

# Endpoint 1: Create Project + Intake
@router.post("/projects")
async def create_bootstrap_project(
    project_name: str = Form(...),
    idea_text: Optional[str] = Form(None),
    pdf_files: List[UploadFile] = File(default=[]),
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """
    Create bootstrap project and start LangGraph workflow.
    At least one of idea_text or pdf_files must be provided.
    """
    # Validate input
    # Create project with context_mode='bootstrap', context_status='embedding'
    # Store files
    # Start LangGraph run (async)
    # Return { project_id, context_status: "embedding" }

# Endpoint 2: Get Questions
@router.get("/projects/{project_id}/questions")
async def get_bootstrap_questions(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get clarifying questions when ready."""
    # Return questions if context_status == 'questions_pending'

# Endpoint 3: Submit Answers
@router.post("/projects/{project_id}/answers")
async def submit_bootstrap_answers(
    project_id: str,
    answers: List[AnswerInput],
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Submit answers and resume graph."""
    # Persist answers, embed into vectors
    # Set context_status='researching'
    # Resume LangGraph
    # Return { context_status: "researching" }

# Endpoint 4: Get Enhanced Context
@router.get("/projects/{project_id}/enhanced-context")
async def get_enhanced_context(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get enhanced context (only if paid/ready)."""
    # Check context_status
    # If 'context_ready' or 'context_confirmed': return context
    # If 'payment_required': return error

# Endpoint 5: Confirm Context
@router.put("/projects/{project_id}/enhanced-context/confirm")
async def confirm_enhanced_context(
    project_id: str,
    confirmed_context: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    """Save user-edited context and set confirmed."""
    # Write enhanced_context.confirmed
    # Bump version
    # Set context_status='context_confirmed'
```

---

#### Task 4.2: Register Router in App

**File to Modify**: `app.py`  
**Pattern Reference**: Existing router registrations

```python
from src.mvp.bootstrap.api.endpoints import router as bootstrap_router
app.include_router(bootstrap_router, prefix="/api")
```

---

### Phase 5: VPS/BMC Context Adapter

#### Task 5.1: Create Bootstrap Context Adapter for VPS/BMC

**File to Create**: `src/mvp/bootstrap/adapters/context_adapter.py`  
**Pattern Reference**: `src/mvp/bmc/utils/bmc_context_loader.py`, `src/mvp/utils/context_loader.py`

```python
class BootstrapContextAdapter:
    """
    Adapts bootstrap enhanced_context to the format expected by
    existing VPS/BMC generation agents.
    """
    
    def adapt_for_vps(self, enhanced_context: Dict) -> Dict[str, Any]:
        """
        Map enhanced_context.confirmed (or .draft) to VPS context format.
        
        VPS expects:
        - customer_profile: { jobs_to_be_done, pains, gains }
        - value_map: { products_services, pain_relievers, gain_creators }
        - personas: [...]
        - etc.
        """
        # Transform enhanced_context fields to expected VPS context shape
        
    def adapt_for_bmc(self, enhanced_context: Dict, vps_v1: Dict) -> Dict[str, Any]:
        """
        Map enhanced_context + VPS v1 to BMC context format.
        """
        # Transform to expected BMC context shape
```

---

#### Task 5.2: Modify VPS Context Loader

**File to Modify**: `src/mvp/utils/context_loader.py`  
**Change**: Add bootstrap context detection

```python
async def load_vps_context(self, project_id: str, tenant_id: str) -> Dict[str, Any]:
    # Get project
    project = self.db_adapter.get_project(project_id, tenant_id)
    
    # NEW: Check context_mode
    if project.get('context_mode') == 'bootstrap':
        # Use bootstrap context adapter
        from src.mvp.bootstrap.adapters.context_adapter import BootstrapContextAdapter
        adapter = BootstrapContextAdapter()
        enhanced_context = project.get('enhanced_context', {})
        context_to_use = enhanced_context.get('confirmed') or enhanced_context.get('draft')
        return adapter.adapt_for_vps(context_to_use)
    
    # EXISTING: Normal context loading
    ...
```

---

#### Task 5.3: Modify BMC Context Loader

**File to Modify**: `src/mvp/bmc/utils/bmc_context_loader.py`  
**Change**: Add bootstrap context detection (same pattern as VPS)

---

### Phase 6: Credit System Integration

#### Task 6.1: Implement Finalize and Charge Node

**Part of**: `src/mvp/bootstrap/workflow/bootstrap_graph.py`  
**Pattern Reference**: `src/mint/api/system/endpoints/workflow_endpoints.py:128-143`

```python
async def _finalize_and_charge(self, state: BootstrapState) -> BootstrapState:
    """
    Atomic finalization:
    1. Write enhanced_context.draft to vmp_projects
    2. Deduct credits (idempotent via request_id=project_id)
    3. Set context_status='context_ready'
    
    On failure: set context_status='payment_required'
    """
    project_id = state["project_id"]
    tenant_id = state["tenant_id"]
    user_id = state["user_id"]
    
    # Get user info for super admin check
    # (Need to pass this through state or retrieve from DB)
    is_super_admin = state.get("is_super_admin", False)
    plan_type = state.get("plan_type", "individual")
    
    try:
        # Step 1: Write enhanced context
        success = self.db_adapter.save_enhanced_context(
            project_id=project_id,
            tenant_id=tenant_id,
            enhanced_context=state["enhanced_context"],
            version=1
        )
        
        if not success:
            raise Exception("Failed to save enhanced context")
        
        # Step 2: Deduct credits (skip for super admins)
        if not is_super_admin:
            from src.mint.api.credit.service import CreditService
            from src.mint.api.features.dependencies import resolve_feature_id
            
            credit_service = CreditService()
            feature_id = await resolve_feature_id("module3_bootstrap_context")
            
            credit_service.consume_feature(
                tenant_id=tenant_id,
                user_id=user_id,
                feature_id=feature_id,
                plan_type=plan_type,
                request_id=project_id,  # Idempotency key
                reason="Module 3 bootstrap context generation",
                project_id=project_id,
                metadata={
                    "context_version": 1,
                    "source": "bootstrap_workflow"
                }
            )
        
        # Step 3: Set context_status='context_ready'
        self.db_adapter.update_context_status(project_id, tenant_id, "context_ready")
        
        state["status"] = "context_ready"
        return state
        
    except InsufficientCreditsError:
        # Set payment_required, do NOT expose context
        self.db_adapter.update_context_status(project_id, tenant_id, "payment_required")
        state["status"] = "payment_required"
        state["error"] = "Insufficient credits"
        return state
        
    except Exception as e:
        self.db_adapter.update_context_status(project_id, tenant_id, "failed")
        state["status"] = "failed"
        state["error"] = str(e)
        return state
```

---

### Phase 7: Testing

#### Task 7.1: Create Unit Tests

**File to Create**: `src/mvp/bootstrap/tests/test_bootstrap_service.py`

- Test project creation
- Test PDF extraction
- Test question generation
- Test answer ingestion
- Test research execution
- Test context composition
- Test credit deduction (mock)

#### Task 7.2: Create Integration Tests

**File to Create**: `src/mvp/bootstrap/tests/test_bootstrap_integration.py`

- Full workflow end-to-end test
- Credit system integration test
- VPS/BMC generation with bootstrap context

---

## Implementation Order

| Phase | Task | Estimated Effort | Dependencies |
|-------|------|------------------|--------------|
| 1 | 1.1 Database Migration | 1 hour | None |
| 1 | 1.2 Register Feature | 30 min | 1.1 |
| 2 | 2.1 Database Adapter | 2 hours | 1.1 |
| 2 | 2.2 PDF Extractor | 1 hour | None |
| 2 | 2.3 Embedding Service | 3 hours | 2.1 |
| 2 | 2.4 Question Generator | 2 hours | 2.3 |
| 2 | 2.5 Research Service | 2 hours | 2.3 |
| 2 | 2.6 Context Composer | 3 hours | 2.4, 2.5 |
| 3 | 3.1 LangGraph Workflow | 4 hours | 2.1-2.6 |
| 3 | 3.2 State Models | 1 hour | None |
| 4 | 4.1 API Endpoints | 3 hours | 3.1 |
| 4 | 4.2 Register Router | 15 min | 4.1 |
| 5 | 5.1 Context Adapter | 2 hours | 2.6 |
| 5 | 5.2 Modify VPS Loader | 1 hour | 5.1 |
| 5 | 5.3 Modify BMC Loader | 1 hour | 5.1 |
| 6 | 6.1 Finalize & Charge | 2 hours | 3.1, 1.2 |
| 7 | 7.1 Unit Tests | 3 hours | All services |
| 7 | 7.2 Integration Tests | 2 hours | All components |

**Total Estimated Effort**: ~33 hours

---

## File Structure

```
src/mvp/bootstrap/
├── __init__.py
├── SRS.md                          # Already exists
├── IMPLEMENTATION_GUIDE.md         # This file
├── adapters/
│   ├── __init__.py
│   ├── database_adapter.py         # Task 2.1
│   └── context_adapter.py          # Task 5.1
├── api/
│   ├── __init__.py
│   └── endpoints.py                # Task 4.1
├── models/
│   ├── __init__.py
│   ├── state_models.py             # Task 3.2
│   └── request_models.py           # Pydantic request/response models
├── services/
│   ├── __init__.py
│   ├── pdf_extractor.py            # Task 2.2
│   ├── embedding_service.py        # Task 2.3
│   ├── question_generator.py       # Task 2.4
│   ├── research_service.py         # Task 2.5
│   └── context_composer.py         # Task 2.6
├── workflow/
│   ├── __init__.py
│   └── bootstrap_graph.py          # Task 3.1
└── tests/
    ├── __init__.py
    ├── test_bootstrap_service.py   # Task 7.1
    └── test_bootstrap_integration.py # Task 7.2
```

---

## Key Implementation Notes

### 1. PV Report ID Handling
The existing `vmp_projects.pv_report_id` is NOT NULL. Options:
- **Option A**: Make it nullable (recommended, migration in Task 1.1)
- **Option B**: Create a placeholder document with source_type='bootstrap_intake'

### 2. Idempotency
Use `project_id` as the `request_id` for credit consumption to ensure idempotency across retries.

### 3. Super Admin Bypass
Follow existing pattern:
```python
user_roles = current_user.get("roles", [])
is_super_admin = len(user_roles) > 0 and user_roles[0] == "super_admin"
```

### 4. Vector Storage Source Types
Add new source types to the `chunks` metadata:
- `bootstrap_idea_text`
- `bootstrap_pdf_extract`
- `bootstrap_qa_answer`
- `bootstrap_web_research`

### 5. Research Citations
Use format `[1]`, `[2]` in research body with numbered sources list.

### 6. Workflow Interruption
After question generation, workflow pauses. Resume via `/answers` endpoint which triggers `answers_ingest` node.

---

## Next Steps

1. Review this guide with the team
2. Start with Phase 1 (Database) to unblock parallel work
3. Implement services in Phase 2 (can be parallelized)
4. Integrate workflow in Phase 3
5. Wire up endpoints in Phase 4
6. Connect to VPS/BMC in Phase 5
7. Test thoroughly in Phase 7
