# Pitch Deck Generator - Implementation Plan

## Overview

Build a backend-only Pitch Deck Generator using FastAPI + LangGraph that:
- Reads from project's already chunked/embedded corpus (RAG)
- Uses bounded web search for external facts when needed
- Produces structured JSON slide content with citations in descriptions only
- Supports versioning and full traceability

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          PITCH DECK GENERATOR                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐    ┌─────────────────────────────────────────────────────┐ │
│  │   FastAPI   │    │              LangGraph Workflow                      │ │
│  │  Endpoints  │───▶│                                                      │ │
│  │             │    │  1. LoadProjectContext                               │ │
│  │ POST /gen   │    │  2. DeckIntentRouter (purpose/stage/category)        │ │
│  │ GET /deck   │    │  3. DeckPlanner (slides_plan[])                      │ │
│  │ GET /list   │    │  4. SlideLoop (for each slide):                      │ │
│  │ GET /preview│    │     4.1 SlideQueryBuilder                            │ │
│  └─────────────┘    │     4.2 ProjectRetrieve (RAG)                        │ │
│                     │     4.3 EvidenceGrader                               │ │
│                     │     4.4 WebResearchPlanner (if needed)               │ │
│                     │     4.5 WebSearch + Extract (if needed)              │ │
│                     │     4.6 SlideWriter                                  │ │
│                     │  5. CrossSlideConsistencyCheck                       │ │
│                     │  6. DeckAssembler                                    │ │
│                     │  7. PersistDeckRun                                   │ │
│                     └─────────────────────────────────────────────────────┘ │
│                                      │                                       │
│  ┌───────────────────────────────────┼──────────────────────────────────┐   │
│  │                    Shared Services                                    │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────────────┐ │   │
│  │  │ProjectRAG    │  │WebSearch     │  │ EmbeddingService            │ │   │
│  │  │Service       │  │Service       │  │ (Azure OpenAI)              │ │   │
│  │  │(reuse)       │  │(reuse)       │  │                             │ │   │
│  │  └──────────────┘  └──────────────┘  └─────────────────────────────┘ │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                      │                                       │
│  ┌───────────────────────────────────┼──────────────────────────────────┐   │
│  │                       Database                                        │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────────────┐ │   │
│  │  │pitch_decks   │  │chunks        │  │ vmp_projects                │ │   │
│  │  │(new table)   │  │(existing)    │  │ (existing)                  │ │   │
│  │  └──────────────┘  └──────────────┘  └─────────────────────────────┘ │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Database Schema

### New Table: `pitch_decks`

```sql
CREATE TABLE public.pitch_decks (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    project_id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    version integer NOT NULL DEFAULT 1,
    
    -- Deck context
    deck_purpose text NOT NULL CHECK (deck_purpose = ANY (ARRAY['FUNDRAISING', 'PARTNER_SALES', 'DEMO'])),
    stage text NOT NULL CHECK (stage = ANY (ARRAY['IDEATION', 'PRE_SEED', 'SEED', 'GROWTH'])),
    category text NOT NULL CHECK (category = ANY (ARRAY['PLATFORM_SAAS', 'CPG', 'INFRA_PROJECT', 'OTHER'])),
    
    -- Deck content (JSON)
    slides jsonb NOT NULL DEFAULT '[]'::jsonb,
    citations jsonb NOT NULL DEFAULT '[]'::jsonb,
    warnings jsonb DEFAULT '[]'::jsonb,
    
    -- User inputs that were provided
    user_inputs jsonb DEFAULT '{}'::jsonb,
    
    -- Run metadata
    run_trace jsonb DEFAULT '{}'::jsonb,
    generation_status text NOT NULL DEFAULT 'pending' CHECK (generation_status = ANY (ARRAY['pending', 'processing', 'completed', 'failed'])),
    error_message text,
    
    -- Timestamps
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    created_by uuid,
    
    CONSTRAINT pitch_decks_pkey PRIMARY KEY (id),
    CONSTRAINT pitch_decks_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.vmp_projects(id),
    CONSTRAINT pitch_decks_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id),
    CONSTRAINT pitch_decks_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.user_profiles(id)
);

-- Unique constraint for project + version
CREATE UNIQUE INDEX pitch_decks_project_version_idx ON public.pitch_decks(project_id, version);

-- Index for tenant queries
CREATE INDEX pitch_decks_tenant_idx ON public.pitch_decks(tenant_id);

-- RLS policies
ALTER TABLE public.pitch_decks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their tenant's pitch decks"
    ON public.pitch_decks FOR SELECT
    USING (tenant_id = auth.jwt() ->> 'tenant_id'::text);

CREATE POLICY "Users can create pitch decks for their tenant"
    ON public.pitch_decks FOR INSERT
    WITH CHECK (tenant_id = auth.jwt() ->> 'tenant_id'::text);

CREATE POLICY "Users can update their tenant's pitch decks"
    ON public.pitch_decks FOR UPDATE
    USING (tenant_id = auth.jwt() ->> 'tenant_id'::text);
```

### Files to Create
- `migrations/001_create_pitch_decks_table.sql`

---

## Phase 2: Data Models

### Core Enums
```python
class DeckPurpose(str, Enum):
    FUNDRAISING = "FUNDRAISING"
    PARTNER_SALES = "PARTNER_SALES"
    DEMO = "DEMO"

class DeckStage(str, Enum):
    IDEATION = "IDEATION"
    PRE_SEED = "PRE_SEED"
    SEED = "SEED"
    GROWTH = "GROWTH"

class DeckCategory(str, Enum):
    PLATFORM_SAAS = "PLATFORM_SAAS"
    CPG = "CPG"
    INFRA_PROJECT = "INFRA_PROJECT"
    OTHER = "OTHER"

class SlideType(str, Enum):
    TITLE = "Title"
    PROBLEM = "Problem"
    SOLUTION = "Solution"
    PRODUCT = "Product"
    MARKET = "Market"
    BUSINESS_MODEL = "BusinessModel"
    GTM = "GTM"
    COMPETITION = "Competition"
    TRACTION = "Traction"
    VALIDATION = "Validation"
    TEAM = "Team"
    FINANCIALS = "Financials"
    ASK = "Ask"
    ROADMAP = "Roadmap"
    RISKS = "Risks"
    IMPACT = "Impact"

class SlidePriority(str, Enum):
    MUST_HAVE = "MUST_HAVE"
    CONDITIONAL = "CONDITIONAL"

class PlaceholderPolicy(str, Enum):
    NONE = "NONE"
    TEMPLATE_IF_MISSING = "TEMPLATE_IF_MISSING"
    OMIT_IF_MISSING = "OMIT_IF_MISSING"
    REPLACE_IF_MISSING = "REPLACE_IF_MISSING"
```

### LangGraph State
```python
class PitchDeckState(TypedDict):
    # Inputs
    project_id: str
    tenant_id: str
    user_hints: Dict[str, Any]
    
    # Project context
    project_summary: str
    available_artifacts: List[str]
    
    # Deck planning
    deck_purpose: str
    stage: str
    category: str
    slides_plan: List[Dict[str, Any]]
    deck_warnings: List[str]
    
    # Current slide processing
    current_slide_index: int
    current_slide_spec: Dict[str, Any]
    current_retrieval_query: str
    current_project_evidence: List[Dict[str, Any]]
    current_web_evidence: List[Dict[str, Any]]
    current_evidence_grade: str
    current_missing_items: List[str]
    
    # Accumulated slides
    slides_draft: List[Dict[str, Any]]
    all_project_citations: List[Dict[str, Any]]
    all_web_citations: List[Dict[str, Any]]
    
    # Final output
    slides_final: List[Dict[str, Any]]
    citations: List[Dict[str, Any]]
    consistency_issues: List[Dict[str, Any]]
    auto_fixes: List[Dict[str, Any]]
    
    # Run trace
    tool_trace: Dict[str, Any]
```

### Slide Models
```python
class SlideSpec(BaseModel):
    slide_type: SlideType
    priority: SlidePriority
    web_allowed: bool
    data_requirements: List[str]
    placeholder_policy: PlaceholderPolicy
    replacement_slide_type: Optional[SlideType] = None

class Placeholder(BaseModel):
    field: str
    prompt: str

class SlideContent(BaseModel):
    slide_type: str
    slide_title: str
    slide_bullets: List[str]
    description: str
    citations_used: List[str]
    placeholders: List[Placeholder]
    warnings: List[str]

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
    domain: str
    title: str
    snippet: str
    fetched_at: str
```

### API Models
```python
class GenerateDeckRequest(BaseModel):
    deck_purpose: Optional[DeckPurpose] = None
    stage: Optional[DeckStage] = None
    category: Optional[DeckCategory] = None
    team_info: Optional[List[Dict[str, str]]] = None
    financial_inputs: Optional[Dict[str, Any]] = None
    traction_metrics: Optional[Dict[str, Any]] = None
    constraints: Optional[Dict[str, Any]] = None

class GenerateDeckResponse(BaseModel):
    deck_id: str
    project_id: str
    version: int
    status: str
    message: str

class DeckPackageResponse(BaseModel):
    id: str
    project_id: str
    version: int
    deck_purpose: str
    stage: str
    category: str
    slides: List[SlideContent]
    citations: List[Union[ProjectCitation, WebCitation]]
    warnings: List[str]
    created_at: str
    run_trace: Optional[Dict[str, Any]] = None

class DeckVersionListResponse(BaseModel):
    versions: List[Dict[str, Any]]
    total_count: int

class DeckPlanPreviewResponse(BaseModel):
    deck_purpose: str
    stage: str
    category: str
    slides_plan: List[SlideSpec]
    warnings: List[str]
```

### Files to Create
- `models.py`

---

## Phase 3: Prompts

All prompts follow the patterns from `agent.md`:
- JSON-only responses
- UNTRUSTED fences for retrieved content
- No citation markers in bullets/title

### Prompt Templates
1. **SYSTEM_PROMPT** - Global rules for deck generation
2. **DECK_INTENT_ROUTER_PROMPT** - Classify purpose/stage/category
3. **DECK_PLANNER_PROMPT** - Generate ordered slides plan
4. **SLIDE_QUERY_BUILDER_PROMPT** - Create retrieval query per slide
5. **EVIDENCE_GRADER_PROMPT** - Grade evidence sufficiency
6. **WEB_RESEARCH_PLANNER_PROMPT** - Generate bounded web queries
7. **WEB_EVIDENCE_EXTRACTOR_PROMPT** - Extract evidence from web results
8. **SLIDE_WRITER_PROMPT** - Write slide content with citations in description only
9. **CONSISTENCY_CHECK_PROMPT** - Verify cross-slide consistency
10. **DECK_ASSEMBLER_PROMPT** (optional) - Assign global citation IDs

### Files to Create
- `workflow/prompts/pitch_prompts.py`

---

## Phase 4: Database Adapter

### PitchDeckDatabaseAdapter Methods
```python
class PitchDeckDatabaseAdapter:
    # Deck CRUD
    async def create_deck(project_id, tenant_id, user_id, user_inputs) -> str
    async def update_deck_status(deck_id, status, error_message=None) -> bool
    async def save_deck_content(deck_id, slides, citations, warnings, run_trace, context) -> bool
    async def get_deck(deck_id, tenant_id) -> Optional[Dict]
    async def get_deck_by_project(project_id, tenant_id, version=None) -> Optional[Dict]
    async def list_deck_versions(project_id, tenant_id) -> List[Dict]
    async def get_next_version(project_id, tenant_id) -> int
    
    # Project context loading
    async def load_project_summary(project_id, tenant_id) -> Dict
    async def get_available_artifacts(project_id, tenant_id) -> List[str]
```

### Files to Create
- `adapters/database_adapter.py`

---

## Phase 5: Services

### PitchDeckRAGService
Reuse patterns from `ProjectRAGService`:
- Filter by tenant_id, project_id
- Slide-aware retrieval hints (artifact type filtering)
- Re-ranking with priority boosts

```python
class PitchDeckRAGService:
    async def retrieve_for_slide(
        query: str,
        project_id: str,
        tenant_id: str,
        artifact_hints: List[str],
        top_k: int = 8
    ) -> List[ProjectEvidence]
```

### PitchDeckWebSearchService
Reuse patterns from `WebSearchService`:
- Bounded queries (3-6 max)
- Evidence extraction with LLM
- Temporal awareness (current year)

```python
class PitchDeckWebSearchService:
    async def search_for_slide(
        queries: List[str],
        extraction_targets: List[str],
        slide_type: str
    ) -> List[WebEvidence]
```

### Files to Create
- `services/pitch_rag_service.py`
- `services/pitch_web_search_service.py`
- `services/__init__.py`

---

## Phase 6: LangGraph Workflow

### Node Structure

```
┌──────────────────┐
│LoadProjectContext│
└────────┬─────────┘
         │
┌────────▼─────────┐
│ DeckIntentRouter │
└────────┬─────────┘
         │
┌────────▼─────────┐
│   DeckPlanner    │
└────────┬─────────┘
         │
    ┌────▼────┐
    │SlideLoop│◄────────────────────┐
    └────┬────┘                     │
         │                          │
┌────────▼─────────┐                │
│SlideQueryBuilder │                │
└────────┬─────────┘                │
         │                          │
┌────────▼─────────┐                │
│ ProjectRetrieve  │                │
└────────┬─────────┘                │
         │                          │
┌────────▼─────────┐                │
│  EvidenceGrader  │                │
└────────┬─────────┘                │
         │                          │
    ┌────▼────┐     ┌───────────┐   │
    │ route   │────▶│WebResearch│   │
    └────┬────┘     └─────┬─────┘   │
         │                │         │
         └───────┬────────┘         │
                 │                  │
         ┌───────▼────────┐         │
         │  SlideWriter   │         │
         └───────┬────────┘         │
                 │                  │
         ┌───────▼────────┐         │
         │  NextSlide?    │─────────┘
         └───────┬────────┘
                 │ (all done)
         ┌───────▼────────┐
         │ConsistencyCheck│
         └───────┬────────┘
                 │
         ┌───────▼────────┐
         │ DeckAssembler  │
         └───────┬────────┘
                 │
         ┌───────▼────────┐
         │ PersistDeckRun │
         └───────┬────────┘
                 │
               [END]
```

### Workflow Routing Logic
- After `EvidenceGrader`: 
  - If `grade == SUFFICIENT` or `web_allowed == False` → `SlideWriter`
  - If `grade in [PARTIAL, INSUFFICIENT]` and `web_allowed` → `WebResearchPlanner`
- After `SlideWriter`:
  - If `current_slide_index < len(slides_plan) - 1` → increment and loop
  - Else → `ConsistencyCheck`

### Files to Create
- `workflow/pitch_workflow.py`
- `workflow/__init__.py`

---

## Phase 7: API Endpoints

### FastAPI Router

```python
# POST /api/v1/mav/projects/{project_id}/pitch-decks/generate
# Trigger deck generation (async)

# GET /api/v1/mav/projects/{project_id}/pitch-decks/{deck_id}
# Get generated deck package

# GET /api/v1/mav/projects/{project_id}/pitch-decks
# List deck versions for project

# GET /api/v1/mav/projects/{project_id}/pitch-decks/preview
# Get deck plan preview (slides list only, no content)

# GET /api/v1/mav/pitch-decks/{deck_id}/status
# Get generation status
```

### Files to Create
- `api/endpoints.py`
- `api/__init__.py`

---

## Phase 8: Integration

### Register Router
Add to `main_app.py`:
```python
from src.mav.Pitch.api.endpoints import router as pitch_router
app.include_router(pitch_router, prefix="/api/v1")
```

### Test Checklist
1. ✅ Create deck for project with completed AMRG
2. ✅ Verify slides contain no citation markers in bullets/title
3. ✅ Verify citations appear only in descriptions
4. ✅ Verify Team/Financials are placeholders when missing
5. ✅ Verify web search triggers only when needed
6. ✅ Verify cross-project isolation (no data leakage)
7. ✅ Verify versioning works correctly
8. ✅ Verify run trace captures retrieval/web queries

---

## File Structure

```
src/mav/Pitch/
├── __init__.py
├── req.md
├── agent.md
├── IMPLEMENTATION_PLAN.md
├── models.py
├── migrations/
│   └── 001_create_pitch_decks_table.sql
├── adapters/
│   ├── __init__.py
│   └── database_adapter.py
├── services/
│   ├── __init__.py
│   ├── pitch_rag_service.py
│   └── pitch_web_search_service.py
├── workflow/
│   ├── __init__.py
│   ├── pitch_workflow.py
│   └── prompts/
│       ├── __init__.py
│       └── pitch_prompts.py
└── api/
    ├── __init__.py
    └── endpoints.py
```

---

## Reusable Components from Chat Module

| Component | From Chat | Reuse Strategy |
|-----------|-----------|----------------|
| `ProjectRAGService` | `mav/chat/services/` | Import and extend for slide-aware retrieval |
| `WebSearchService` | `mav/chat/services/` | Import directly, same bounded search pattern |
| `EmbeddingService` | `mint/api/services/ai/` | Import directly |
| `BraveSearchProvider` | `mint/providers/search/` | Used by WebSearchService |
| `get_client_config` | `mint/api/ai/config.py` | LLM client configuration |
| `match_project_chunks` | Supabase RPC | Vector similarity search |

---

## Slide Type → Artifact Mapping (RAG Hints)

| Slide Type | Primary Artifacts | Web Allowed |
|------------|-------------------|-------------|
| Title | VPS v2, project name/description | No |
| Problem | Market research, customer pains, problem validation | Limited |
| Solution | VPS v2, solution critique | No |
| Product | VPS v2, MVP requirements | No |
| Market | Market research (if exists) | Yes |
| BusinessModel | BMC v2 | No |
| GTM | BMC v2 channels, assumptions | Limited |
| Competition | Market research | Yes |
| Traction | Only if in artifacts | No |
| Validation | Field prep, hypotheses, questionnaires | No |
| Team | User input only | No |
| Financials | User input only | No |
| Ask | User input | No |
| Roadmap | MVP requirements | No |
| Risks | Assumptions, market research | Limited |
| Impact | VPS v2, problem validation | No |

---

## Next Steps

1. **Approve this plan** - Review and confirm the architecture
2. **Phase 1** - Create database migration
3. **Phase 2** - Create data models
4. **Continue sequentially** through remaining phases

Ready to begin implementation when you confirm.
