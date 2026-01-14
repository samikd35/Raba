# RABA Implementation Plan

**Version**: 1.0  
**Created**: January 14, 2026  
**Based on**: [Guides/RABA_Architecture.md](../Guides/RABA_Architecture.md), [Guides/SRS.md](../Guides/SRS.md)

---

## Overview

This document provides a **step-by-step implementation plan** for building the RABA multi-agent YouTube Shorts generation system. Tasks are organized in **logical dependency order** - each phase builds on the previous one.

```
IMPLEMENTATION FLOW
═══════════════════

Phase 1: Foundation          Phase 2: Core Agents         Phase 3: Generation         Phase 4: Advanced
─────────────────────        ────────────────────         ───────────────────         ────────────────
├─ Project Setup             ├─ Intent/Tool Selector      ├─ Image Generator          ├─ HITL System
├─ Environment Config        ├─ Deep Research Agent       ├─ Video Generator          ├─ Multi-Segment Video
├─ Database Schema           ├─ Script Generator          ├─ Output Processing        ├─ Caching Layer
├─ API Scaffold              └─ Tool Repository           └─ Media Storage            └─ Monitoring
└─ LangGraph Base                                                                     └─ Production Deploy
```

---

## Phase 1: Foundation Infrastructure

> **Goal**: Set up project structure, database, configuration, and basic API scaffold.  
> **Duration**: 3-4 days  
> **No agent logic yet** - just infrastructure.

### 1.1 Project Setup

| Task ID | Task | Description | Files to Create | Est. Time |
|---------|------|-------------|-----------------|-----------|
| **1.1.1** | Initialize Python project | Create `pyproject.toml` or `requirements.txt` with dependencies | `requirements.txt`, `pyproject.toml` | 30 min |
| **1.1.2** | Create directory structure | Set up folders for agents, models, services, utils | See structure below | 30 min |
| **1.1.3** | Set up virtual environment | Create venv, install dependencies | - | 15 min |
| **1.1.4** | Configure linting/formatting | Set up black, isort, ruff | `pyproject.toml`, `.pre-commit-config.yaml` | 30 min |

**Directory Structure**:
```
Backend/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI entry point
│   ├── config.py                  # Settings & env loading
│   ├── agents/                    # All agent implementations
│   │   ├── __init__.py
│   │   ├── intent_tool_selector.py
│   │   ├── deep_research.py
│   │   ├── script_writer.py
│   │   ├── image_generator.py
│   │   └── video_generator.py
│   ├── models/                    # Pydantic models & schemas
│   │   ├── __init__.py
│   │   ├── workflow.py
│   │   ├── tool.py
│   │   ├── script.py
│   │   └── media.py
│   ├── services/                  # External service clients
│   │   ├── __init__.py
│   │   ├── gemini.py              # Gemini API client
│   │   ├── supabase.py            # Supabase client
│   │   ├── redis.py               # Redis cache client
│   │   └── storage.py             # File upload/download
│   ├── graph/                     # LangGraph workflow
│   │   ├── __init__.py
│   │   ├── state.py               # VideoGenerationState
│   │   ├── nodes.py               # Node functions
│   │   ├── edges.py               # Routing logic
│   │   └── workflow.py            # Graph definition
│   ├── tools/                     # Tool repository
│   │   ├── __init__.py
│   │   ├── base.py                # VideoGenerationTool base class
│   │   ├── registry.py            # ToolRegistry
│   │   └── implementations/
│   │       ├── surreal_realism.py
│   │       ├── high_octane_anime.py
│   │       └── stylized_3d.py
│   ├── api/                       # API routes
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── generate.py        # POST /api/v1/generate
│   │   │   ├── workflows.py       # GET /api/v1/workflows/{id}
│   │   │   ├── tools.py           # GET/POST /api/v1/tools
│   │   │   └── hitl.py            # HITL feedback endpoints
│   │   └── dependencies.py        # FastAPI dependencies
│   └── utils/
│       ├── __init__.py
│       └── helpers.py
├── tests/
│   ├── __init__.py
│   ├── test_agents/
│   ├── test_api/
│   └── test_services/
├── .env.example
├── .env
├── requirements.txt
└── README.md
```

### 1.2 Environment Configuration

| Task ID | Task | Description | Files | Est. Time |
|---------|------|-------------|-------|-----------|
| **1.2.1** | Create `.env.example` | Template with all required env vars | `.env.example` | 15 min |
| **1.2.2** | Create config module | Pydantic Settings for type-safe config | `app/config.py` | 45 min |
| **1.2.3** | Test config loading | Verify all env vars load correctly | - | 15 min |

**Environment Variables Required**:
```bash
# .env.example

# === Google Gemini API ===
GOOGLE_API_KEY=

# === Supabase ===
SUPABASE_URL=
SUPABASE_KEY=
SUPABASE_SERVICE_KEY=  # For admin operations

# === Redis (Upstash) ===
UPSTASH_REDIS_URL=

# === Google Custom Search (Image Search) ===
GOOGLE_CUSTOM_SEARCH_API_KEY=
GOOGLE_CUSTOM_SEARCH_CX=

# === LangSmith Tracing ===
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=
LANGCHAIN_PROJECT=Raba

# === App Settings ===
ENVIRONMENT=development  # development | staging | production
DEBUG=true
```

### 1.3 Database Schema Setup

| Task ID | Task | Description | Files | Est. Time |
|---------|------|-------------|-------|-----------|
| **1.3.1** | Create Supabase project | Set up project in Supabase dashboard | - | 15 min |
| **1.3.2** | Create `workflows` table | Main table for all workflow data | SQL migration | 30 min |
| **1.3.3** | Create `tools` table | Tool registry storage | SQL migration | 15 min |
| **1.3.4** | Create `media` table | Track all generated media | SQL migration | 15 min |
| **1.3.5** | Create `config` table | Dynamic configuration | SQL migration | 15 min |
| **1.3.6** | Set up RLS policies | Row-level security for all tables | SQL migration | 30 min |
| **1.3.7** | Create Supabase Storage buckets | For images and videos | Supabase dashboard | 15 min |
| **1.3.8** | Test database connection | Verify Python client works | `test_supabase.py` | 15 min |

**SQL Migrations** (in order):
```sql
-- migrations/001_create_workflows.sql
-- migrations/002_create_tools.sql
-- migrations/003_create_media.sql
-- migrations/004_create_config.sql
-- migrations/005_create_rls_policies.sql
```

### 1.4 API Scaffold

| Task ID | Task | Description | Files | Est. Time |
|---------|------|-------------|-------|-----------|
| **1.4.1** | Create FastAPI app | Basic app with CORS, docs | `app/main.py` | 30 min |
| **1.4.2** | Create health endpoint | `GET /health` for monitoring | `app/main.py` | 10 min |
| **1.4.3** | Create generate endpoint stub | `POST /api/v1/generate` (returns mock) | `app/api/routes/generate.py` | 30 min |
| **1.4.4** | Create workflows endpoint stub | `GET /api/v1/workflows/{id}` | `app/api/routes/workflows.py` | 20 min |
| **1.4.5** | Add request validation | Pydantic models for input | `app/models/workflow.py` | 30 min |
| **1.4.6** | Test API with Postman/curl | Verify endpoints respond | - | 15 min |

### 1.5 LangGraph Base Setup

| Task ID | Task | Description | Files | Est. Time |
|---------|------|-------------|-------|-----------|
| **1.5.1** | Define VideoGenerationState | TypedDict for workflow state | `app/graph/state.py` | 45 min |
| **1.5.2** | Create empty node stubs | Placeholder functions for each agent | `app/graph/nodes.py` | 30 min |
| **1.5.3** | Define workflow graph | StateGraph with nodes and edges | `app/graph/workflow.py` | 45 min |
| **1.5.4** | Add Supabase checkpointer | State persistence between steps | `app/graph/workflow.py` | 30 min |
| **1.5.5** | Test graph execution | Run empty graph end-to-end | `tests/test_graph.py` | 30 min |

---

## Phase 2: Core Agents (Sequential Implementation)

> **Goal**: Implement agents in order of data flow dependency.  
> **Duration**: 5-7 days  
> **Order matters**: Each agent depends on the previous one's output.

```
AGENT DEPENDENCY CHAIN
══════════════════════

[Intent/Tool Selector] ──▶ [Deep Research] ──▶ [Script Generator]
        │                        │                    │
        │                        │                    │
        ▼                        ▼                    ▼
   Provides:              Provides:              Provides:
   - selected_tool        - research_data        - script
   - intent_metadata      - research_images      - scenes[]
   - validated_params     - citations            - hook/punchline
```

### 2.1 Intent/Tool Selector Agent

> **Must be implemented FIRST** - all other agents depend on its output.

| Task ID | Task | Description | Files | Est. Time |
|---------|------|-------------|-------|-----------|
| **2.1.1** | Create Pydantic models | IntentMetadata, ToolSelection schemas | `app/models/tool.py` | 30 min |
| **2.1.2** | Create Gemini service | Wrapper for Gemini 2.5 Flash API | `app/services/gemini.py` | 45 min |
| **2.1.3** | Implement intent extraction | LLM call to parse topic → intent | `app/agents/intent_tool_selector.py` | 1 hr |
| **2.1.4** | Implement parameter validation | Validate duration, resolution, etc. | `app/agents/intent_tool_selector.py` | 30 min |
| **2.1.5** | Implement tool scoring | Score tools by topic relevance | `app/agents/intent_tool_selector.py` | 45 min |
| **2.1.6** | Implement tool selection | Select best tool from category | `app/agents/intent_tool_selector.py` | 30 min |
| **2.1.7** | Create fallback logic | Default to Surreal Realism if no match | `app/agents/intent_tool_selector.py` | 20 min |
| **2.1.8** | Wire to LangGraph node | Connect agent to graph | `app/graph/nodes.py` | 20 min |
| **2.1.9** | Write unit tests | Test intent extraction, tool selection | `tests/test_agents/test_intent.py` | 45 min |
| **2.1.10** | Integration test | End-to-end test via API | - | 30 min |

**Output Schema**:
```python
class IntentToolOutput(BaseModel):
    topic: str
    intent_type: Literal["educational", "entertainment", "inspirational", "tutorial"]
    target_audience: str
    tone: str
    validated_params: ValidatedParams
    selected_tool: ToolMetadata
    tool_execution_params: dict
    confidence: float
```

### 2.2 Tool Repository System

> **Implement alongside Intent/Tool Selector** - provides tools to select from.

| Task ID | Task | Description | Files | Est. Time |
|---------|------|-------------|-------|-----------|
| **2.2.1** | Create base tool class | Abstract VideoGenerationTool | `app/tools/base.py` | 45 min |
| **2.2.2** | Create ToolRegistry | Tool registration and lookup | `app/tools/registry.py` | 45 min |
| **2.2.3** | Implement Surreal Realism tool | "Impossible Simulations" tool | `app/tools/implementations/surreal_realism.py` | 1 hr |
| **2.2.4** | Implement High-Octane Anime tool | "Concept Combat" tool | `app/tools/implementations/high_octane_anime.py` | 1 hr |
| **2.2.5** | Implement Stylized 3D tool | Basic 3D style tool | `app/tools/implementations/stylized_3d.py` | 45 min |
| **2.2.6** | Create tools API endpoints | GET /tools, POST /tools/register | `app/api/routes/tools.py` | 30 min |
| **2.2.7** | Seed initial tools | Insert tools into database | `scripts/seed_tools.py` | 20 min |
| **2.2.8** | Test tool registry | Verify lookup and scoring | `tests/test_tools.py` | 30 min |

> **See**: [PHASE2_2_TOOL_REPOSITORY_PLAN.md](./PHASE2_2_TOOL_REPOSITORY_PLAN.md) for detailed implementation plan

### 2.3 Deep Research Agent

> **Depends on**: Intent/Tool Selector (needs topic and tool context)

| Task ID | Task | Description | Files | Est. Time |
|---------|------|-------------|-------|-----------|
| **2.3.1** | Create research models | ResearchOutput, Citation schemas | `app/models/research.py` | 30 min |
| **2.3.2** | Implement Gemini research | Gemini 2.5 Pro with Google Search grounding | `app/agents/deep_research.py` | 1.5 hr |
| **2.3.3** | Create Google Custom Search client | For image search | `app/services/google_search.py` | 45 min |
| **2.3.4** | Implement image search | Search for reference images | `app/agents/deep_research.py` | 45 min |
| **2.3.5** | Implement image download | Download and store in Supabase | `app/agents/deep_research.py` | 45 min |
| **2.3.6** | Add Redis caching | Cache research results (7 day TTL) | `app/agents/deep_research.py` | 30 min |
| **2.3.7** | Implement persistence | Save to workflows.research_output | `app/agents/deep_research.py` | 20 min |
| **2.3.8** | Wire to LangGraph node | Connect agent to graph | `app/graph/nodes.py` | 20 min |
| **2.3.9** | Write unit tests | Test research, image search | `tests/test_agents/test_research.py` | 45 min |
| **2.3.10** | Integration test | Full research flow | - | 30 min |

**Output Schema**:
```python
class ResearchOutput(BaseModel):
    research_findings: List[ResearchFinding]
    research_depth_used: str
    total_sources: int
    research_images: List[str]  # URLs from image search
    cache_hit: bool
    generated_at: datetime
```

### 2.4 Script Generator Agent

> **Depends on**: Deep Research (needs research data) + Tool (needs style specs)

| Task ID | Task | Description | Files | Est. Time |
|---------|------|-------------|-------|-----------|
| **2.4.1** | Create script models | ScriptOutput, Scene, Hook schemas | `app/models/script.py` | 45 min |
| **2.4.2** | Implement hook generator | Generate viral hook (first 1-2s) | `app/agents/script_writer.py` | 1 hr |
| **2.4.3** | Implement scene generator | Generate scenes with visual directions | `app/agents/script_writer.py` | 1.5 hr |
| **2.4.4** | Implement pattern interrupt logic | Insert interrupts every 3-5s | `app/agents/script_writer.py` | 30 min |
| **2.4.5** | Add viral optimization | Engagement metrics, punchline | `app/agents/script_writer.py` | 45 min |
| **2.4.6** | Integrate tool specs | Use tool's script format requirements | `app/agents/script_writer.py` | 30 min |
| **2.4.7** | Implement persistence | Save to workflows.script_output | `app/agents/script_writer.py` | 20 min |
| **2.4.8** | Wire to LangGraph node | Connect agent to graph | `app/graph/nodes.py` | 20 min |
| **2.4.9** | Write unit tests | Test script structure, viral metrics | `tests/test_agents/test_script.py` | 45 min |
| **2.4.10** | Integration test | Full script generation | - | 30 min |

**Output Schema**:
```python
class ScriptOutput(BaseModel):
    hook: HookSection
    scenes: List[Scene]
    call_to_action: CTASection
    estimated_completion_rate: float
    viral_score: float
    total_duration_seconds: float
```

---

## Phase 3: Generation Agents

> **Goal**: Implement image and video generation.  
> **Duration**: 4-5 days  
> **Depends on**: All Phase 2 agents must be complete.

### 3.1 Image Generator Agent

> **Depends on**: Script Generator (needs scenes for prompts)

| Task ID | Task | Description | Files | Est. Time |
|---------|------|-------------|-------|-----------|
| **3.1.1** | Create media models | ImageMetadata, MediaFile schemas | `app/models/media.py` | 30 min |
| **3.1.2** | Implement Nano Banana client | Gemini 2.5 Pro Image API wrapper | `app/services/gemini.py` | 45 min |
| **3.1.3** | Implement image count logic | Calculate 1-5 images needed | `app/agents/image_generator.py` | 30 min |
| **3.1.4** | Implement prompt builder | Build prompts from scenes + tool style | `app/agents/image_generator.py` | 45 min |
| **3.1.5** | Implement image generation | Generate images via API | `app/agents/image_generator.py` | 1 hr |
| **3.1.6** | Implement Supabase upload | Upload images to Storage | `app/agents/image_generator.py` | 30 min |
| **3.1.7** | Combine all images | Merge user + research + generated | `app/agents/image_generator.py` | 20 min |
| **3.1.8** | Implement persistence | Save to workflows.generated_images + media table | `app/agents/image_generator.py` | 20 min |
| **3.1.9** | Wire to LangGraph node | Connect agent to graph | `app/graph/nodes.py` | 20 min |
| **3.1.10** | Write unit tests | Test image count, prompt building | `tests/test_agents/test_image.py` | 45 min |
| **3.1.11** | Integration test | Full image generation | - | 30 min |

### 3.2 Video Generator Agent

> **Depends on**: Image Generator (needs reference images) + Script (needs prompts)

| Task ID | Task | Description | Files | Est. Time |
|---------|------|-------------|-------|-----------|
| **3.2.1** | Create video models | VideoMetadata, Segment schemas | `app/models/media.py` | 30 min |
| **3.2.2** | Implement Veo 3.1 client | Video generation API wrapper | `app/services/gemini.py` | 1 hr |
| **3.2.3** | Implement segment planner | Plan segments for >8s videos | `app/agents/video_generator.py` | 45 min |
| **3.2.4** | Implement single segment generation | Generate one 8s segment | `app/agents/video_generator.py` | 1.5 hr |
| **3.2.5** | Implement prompt engineering | Build Veo prompt from script | `app/agents/video_generator.py` | 45 min |
| **3.2.6** | Implement video upload | Upload to Supabase Storage | `app/agents/video_generator.py` | 30 min |
| **3.2.7** | Implement persistence | Save to workflows.video_output + media table | `app/agents/video_generator.py` | 20 min |
| **3.2.8** | Wire to LangGraph node | Connect agent to graph | `app/graph/nodes.py` | 20 min |
| **3.2.9** | Write unit tests | Test segment planning, prompts | `tests/test_agents/test_video.py` | 45 min |
| **3.2.10** | Integration test | Full video generation (8s) | - | 30 min |

### 3.3 Output Processing

> **Depends on**: Video Generator (processes final output)

| Task ID | Task | Description | Files | Est. Time |
|---------|------|-------------|-------|-----------|
| **3.3.1** | Implement metadata generation | Duration, size, encoding info | `app/graph/nodes.py` | 30 min |
| **3.3.2** | Implement workflow completion | Update status to 'completed' | `app/graph/nodes.py` | 20 min |
| **3.3.3** | Implement response builder | Build final API response | `app/graph/nodes.py` | 30 min |
| **3.3.4** | Wire to LangGraph node | Connect to graph | `app/graph/nodes.py` | 15 min |
| **3.3.5** | Test complete workflow | End-to-end auto mode test | - | 1 hr |

---

## Phase 4: Advanced Features

> **Goal**: Add HITL, multi-segment video, caching, and production readiness.  
> **Duration**: 5-6 days  
> **Depends on**: All Phase 3 work must be complete.

### 4.1 HITL (Human-in-the-Loop) System

| Task ID | Task | Description | Files | Est. Time |
|---------|------|-------------|-------|-----------|
| **4.1.1** | Create HITL models | HITLAction, HITLFeedback schemas | `app/models/hitl.py` | 30 min |
| **4.1.2** | Implement gate handler | Pause workflow at gate | `app/services/hitl.py` | 45 min |
| **4.1.3** | Implement feedback processor | Handle APPROVE/EDIT/REGENERATE | `app/services/hitl.py` | 1 hr |
| **4.1.4** | Create HITL API endpoints | POST /workflows/{id}/feedback | `app/api/routes/hitl.py` | 45 min |
| **4.1.5** | Add HITL routing logic | Conditional routing at each gate | `app/graph/edges.py` | 45 min |
| **4.1.6** | Implement regeneration logic | Re-run agent with feedback | `app/graph/nodes.py` | 1 hr |
| **4.1.7** | Add max regeneration limit | Cap at 3 per gate | `app/services/hitl.py` | 20 min |
| **4.1.8** | Test manual mode | Full workflow with HITL pauses | - | 1 hr |

### 4.2 Multi-Segment Video Generation

| Task ID | Task | Description | Files | Est. Time |
|---------|------|-------------|-------|-----------|
| **4.2.1** | Implement frame extraction | Get last frame from segment | `app/agents/video_generator.py` | 45 min |
| **4.2.2** | Implement segment continuity | Use last frame as next first frame | `app/agents/video_generator.py` | 1 hr |
| **4.2.3** | Implement segment stitching | Combine segments (if needed) | `app/agents/video_generator.py` | 1 hr |
| **4.2.4** | Test 18s video | Generate 3-segment video | - | 45 min |
| **4.2.5** | Test 25s video | Generate 4-segment video | - | 45 min |

### 4.3 Caching Layer

| Task ID | Task | Description | Files | Est. Time |
|---------|------|-------------|-------|-----------|
| **4.3.1** | Create Redis service | Upstash Redis client wrapper | `app/services/redis.py` | 45 min |
| **4.3.2** | Implement research caching | Cache by topic hash (7 day TTL) | `app/agents/deep_research.py` | 30 min |
| **4.3.3** | Implement tool list caching | Cache tool registry (1 hour TTL) | `app/tools/registry.py` | 20 min |
| **4.3.4** | Add cache key helpers | Standardized key generation | `app/utils/cache.py` | 20 min |
| **4.3.5** | Test cache hit/miss | Verify caching works | `tests/test_cache.py` | 30 min |

### 4.4 Observability & Monitoring

| Task ID | Task | Description | Files | Est. Time |
|---------|------|-------------|-------|-----------|
| **4.4.1** | Configure LangSmith | Set up tracing for all nodes | `app/graph/workflow.py` | 30 min |
| **4.4.2** | Add timing metrics | Track duration per step | `app/graph/nodes.py` | 30 min |
| **4.4.3** | Add error logging | Structured logging for errors | `app/utils/logging.py` | 30 min |
| **4.4.4** | Test LangSmith traces | Verify traces appear in dashboard | - | 20 min |

### 4.5 API Completion

| Task ID | Task | Description | Files | Est. Time |
|---------|------|-------------|-------|-----------|
| **4.5.1** | Complete generate endpoint | Full implementation with file upload | `app/api/routes/generate.py` | 45 min |
| **4.5.2** | Complete workflows endpoint | Status, result retrieval | `app/api/routes/workflows.py` | 30 min |
| **4.5.3** | Add rate limiting | Prevent abuse | `app/main.py` | 30 min |
| **4.5.4** | Add API documentation | OpenAPI schema improvements | `app/main.py` | 30 min |
| **4.5.5** | Integration tests | Full API test suite | `tests/test_api/` | 1 hr |

---

## Phase 5: Production Readiness

> **Goal**: Final polish, security, and deployment preparation.  
> **Duration**: 2-3 days

### 5.1 Security Hardening

| Task ID | Task | Description | Files | Est. Time |
|---------|------|-------------|-------|-----------|
| **5.1.1** | Input sanitization | Sanitize all user inputs | `app/utils/security.py` | 45 min |
| **5.1.2** | API key protection | Ensure keys not in logs/responses | `app/config.py` | 20 min |
| **5.1.3** | Content safety filters | Implement blacklist checks | `app/utils/safety.py` | 45 min |
| **5.1.4** | Verify RLS policies | Test database security | - | 30 min |

### 5.2 Testing & Quality

| Task ID | Task | Description | Files | Est. Time |
|---------|------|-------------|-------|-----------|
| **5.2.1** | Write E2E tests | Full workflow tests | `tests/test_e2e.py` | 2 hr |
| **5.2.2** | Performance testing | Verify latency targets | - | 1 hr |
| **5.2.3** | Error handling review | Verify all errors handled gracefully | All files | 1 hr |

### 5.3 Documentation

| Task ID | Task | Description | Files | Est. Time |
|---------|------|-------------|-------|-----------|
| **5.3.1** | Update README | Installation, usage instructions | `README.md` | 1 hr |
| **5.3.2** | API documentation | Complete endpoint docs | Auto-generated | 30 min |
| **5.3.3** | Environment setup guide | How to configure all services | `docs/setup.md` | 45 min |

---

## Dependencies & Prerequisites

### Required API Keys (Before Starting)

| Service | Required For | How to Get |
|---------|--------------|------------|
| **Google AI Studio** | Gemini 2.5, Veo 3.1, Nano Banana | https://aistudio.google.com |
| **Supabase** | Database, Storage | https://supabase.com |
| **Upstash** | Redis cache | https://upstash.com |
| **Google Cloud Console** | Custom Search API | https://console.cloud.google.com |
| **LangSmith** | Tracing | https://smith.langchain.com |

### Python Dependencies

```txt
# Core
fastapi>=0.109.0
uvicorn>=0.27.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
python-dotenv>=1.0.0

# LangChain/LangGraph
langgraph>=0.0.40
langchain>=0.1.0
langsmith>=0.0.80

# Google APIs
google-generativeai>=0.3.0
google-api-python-client>=2.100.0

# Database & Cache
supabase>=2.0.0
upstash-redis>=0.15.0

# HTTP & Async
httpx>=0.26.0
aiofiles>=23.2.0

# Testing
pytest>=7.4.0
pytest-asyncio>=0.23.0
```

---

## Estimated Timeline

| Phase | Duration | Cumulative |
|-------|----------|------------|
| **Phase 1**: Foundation | 3-4 days | 3-4 days |
| **Phase 2**: Core Agents | 5-7 days | 8-11 days |
| **Phase 3**: Generation | 4-5 days | 12-16 days |
| **Phase 4**: Advanced | 5-6 days | 17-22 days |
| **Phase 5**: Production | 2-3 days | **19-25 days** |

**Total Estimated Time**: ~3-4 weeks

---

## Quick Start Commands

```bash
# After completing Phase 1.1-1.2
cd Backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
cp .env.example .env
# Fill in .env with your API keys

# Run development server
uvicorn app.main:app --reload --port 8000

# Run tests
pytest tests/ -v
```

---

## Checkpoints & Milestones

| Milestone | Criteria | Target Date |
|-----------|----------|-------------|
| **M1**: Infrastructure Ready | API responds, DB connected | End of Phase 1 |
| **M2**: First Agent Working | Intent/Tool Selector returns valid output | After 2.1 |
| **M3**: Research Complete | Can research topic and find images | After 2.3 |
| **M4**: Script Generation | Can generate viral script | After 2.4 |
| **M5**: Image Generation | Can generate reference images | After 3.1 |
| **M6**: Basic Video | Can generate 8s video | After 3.2 |
| **M7**: Full Auto Mode | Complete end-to-end in auto mode | End of Phase 3 |
| **M8**: Manual Mode | HITL gates working | After 4.1 |
| **M9**: Long Videos | Can generate 25s video | After 4.2 |
| **M10**: Production Ready | All tests pass, docs complete | End of Phase 5 |
