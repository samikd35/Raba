# RABA Phase 1: Foundation Infrastructure - Detailed Plan

**Status**: Ready for Review  
**Duration**: 3-4 days  
**Goal**: Set up project structure, database, configuration, and basic API scaffold with LangGraph base.

---

## 📚 Documentation References

Before starting, these are the key documentation sources we'll reference:

| Component | Documentation | Purpose |
|-----------|--------------|---------|
| **FastAPI** | https://fastapi.tiangolo.com/ | Web framework |
| **Pydantic Settings** | https://docs.pydantic.dev/latest/concepts/pydantic_settings/ | Environment configuration |
| **LangGraph** | https://docs.langchain.com/oss/python/langgraph/overview | Agent orchestration |
| **Google Gen AI SDK** | https://github.com/googleapis/python-genai | Gemini API (new unified SDK) |
| **Supabase Python** | https://supabase.com/docs/reference/python/introduction | Database client |
| **Upstash Redis** | https://github.com/upstash/redis-py | Redis cache client |

### Key Notes from Documentation:

1. **Google Gen AI SDK**: The legacy `google-generativeai` is deprecated. Use the new `google-genai` package:
   ```python
   from google import genai
   from google.genai import types
   client = genai.Client(api_key='GEMINI_API_KEY')
   ```

2. **LangGraph StateGraph**: Basic pattern:
   ```python
   from langgraph.graph import StateGraph, START, END
   graph = StateGraph(State)
   graph.add_node("node_name", node_function)
   graph.add_edge(START, "node_name")
   graph.compile()
   ```

3. **Pydantic Settings**: Uses `BaseSettings` with `SettingsConfigDict` for env loading.

---

## Step-by-Step Implementation Plan

### 1.1 Project Setup

#### Step 1.1.1: Initialize Python Project
**Files to create**: `pyproject.toml`, `requirements.txt`

**Actions**:
- Create `pyproject.toml` with project metadata and tool configurations (black, isort, ruff)
- Create `requirements.txt` with pinned dependencies

**Dependencies** (based on latest documentation):
```txt
# Core
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
pydantic>=2.10.0
pydantic-settings>=2.6.0
python-dotenv>=1.0.1

# LangChain/LangGraph
langgraph>=0.2.0
langchain-core>=0.3.0
langsmith>=0.2.0

# Google Gen AI (NEW unified SDK - replaces deprecated google-generativeai)
google-genai>=1.0.0

# Database & Cache
supabase>=2.10.0
redis>=5.2.0

# HTTP & Async
httpx>=0.28.0
aiofiles>=24.1.0

# Testing
pytest>=8.3.0
pytest-asyncio>=0.24.0

# Utilities
python-multipart>=0.0.12
```

---

#### Step 1.1.2: Create Directory Structure
**Files to create**: All `__init__.py` files and directory structure

**Structure**:
```
Backend/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI entry point
│   ├── config.py                  # Settings & env loading
│   ├── agents/                    # Agent implementations (empty for Phase 1)
│   │   └── __init__.py
│   ├── models/                    # Pydantic models & schemas
│   │   ├── __init__.py
│   │   └── workflow.py            # WorkflowInput, WorkflowOutput schemas
│   ├── services/                  # External service clients
│   │   ├── __init__.py
│   │   ├── supabase.py            # Supabase client
│   │   └── redis.py               # Redis cache client (stub)
│   ├── graph/                     # LangGraph workflow
│   │   ├── __init__.py
│   │   ├── state.py               # VideoGenerationState TypedDict
│   │   └── workflow.py            # Graph definition (no agent implementations)
│   ├── tools/                     # Tool repository (empty for Phase 1)
│   │   └── __init__.py
│   ├── api/                       # API routes
│   │   ├── __init__.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── generate.py        # POST /api/v1/generate (stub)
│   │       └── workflows.py       # GET /api/v1/workflows/{id} (stub)
│   └── utils/
│       ├── __init__.py
│       └── helpers.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py                # pytest fixtures
│   └── test_api/
│       ├── __init__.py
│       └── test_health.py
├── migrations/                    # SQL migrations
│   ├── 001_create_workflows.sql
│   ├── 002_create_tools.sql
│   ├── 003_create_media.sql
│   └── 004_create_config.sql
├── .env.example
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

### 1.2 Environment Configuration

#### Step 1.2.1: Create `.env.example`
**File**: `.env.example`

**Content**:
```bash
# === Google Gen AI (NEW unified SDK) ===
GOOGLE_API_KEY=

# === Supabase ===
SUPABASE_URL=
SUPABASE_KEY=
SUPABASE_SERVICE_KEY=

# === Redis (Cloud Redis) ===
REDIS_URL=redis://redis-12421.c61.us-east-1-3.ec2.cloud.redislabs.com:12421

# === Google Custom Search (Image Search) ===
GOOGLE_CUSTOM_SEARCH_API_KEY=
GOOGLE_CUSTOM_SEARCH_CX=

# === LangSmith Tracing ===
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=
LANGCHAIN_PROJECT=Raba

# === App Settings ===
ENVIRONMENT=development
DEBUG=true
API_V1_PREFIX=/api/v1
```

---

#### Step 1.2.2: Create Config Module
**File**: `app/config.py`

**Actions**:
- Create `Settings` class using `pydantic-settings`
- Use nested config classes for organization (per Pydantic best practices)
- Load from environment variables with `.env` file support
- Implement validation for required fields

**Key patterns** (from Pydantic Settings docs):
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
```

---

### 1.3 Database Schema Setup

#### Step 1.3.1: Create SQL Migrations
**Files**: `migrations/001_create_workflows.sql`, etc.

**Table: workflows**
```sql
CREATE TABLE workflows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    topic TEXT NOT NULL,
    duration_seconds INTEGER DEFAULT 18,
    aspect_ratio VARCHAR(10) DEFAULT '9:16',
    resolution VARCHAR(10) DEFAULT '1080p',
    category VARCHAR(50) DEFAULT 'auto',
    hitl_mode VARCHAR(10) DEFAULT 'auto',
    enable_audio BOOLEAN DEFAULT true,
    enable_subtitles BOOLEAN DEFAULT false,
    
    -- Agent outputs (JSONB for flexibility)
    tool_selection JSONB,
    research_output JSONB,
    research_images JSONB,
    script_output JSONB,
    generated_images JSONB,
    video_output JSONB,
    
    -- HITL tracking
    current_hitl_gate VARCHAR(50),
    hitl_feedback JSONB DEFAULT '[]',
    
    -- Reference images
    user_reference_image_url TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);
```

**Table: tools**
```sql
CREATE TABLE tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_id VARCHAR(100) UNIQUE NOT NULL,
    tool_name VARCHAR(255) NOT NULL,
    category VARCHAR(50) NOT NULL,
    description TEXT,
    capabilities JSONB,
    prompt_templates JSONB,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Table: media**
```sql
CREATE TABLE media (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID REFERENCES workflows(id) ON DELETE CASCADE,
    media_type VARCHAR(20) NOT NULL, -- 'image', 'video'
    source VARCHAR(50) NOT NULL, -- 'user_upload', 'research', 'generated'
    storage_url TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Table: config**
```sql
CREATE TABLE config (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

#### Step 1.3.2: Create Supabase Service
**File**: `app/services/supabase.py`

**Actions**:
- Create async Supabase client wrapper
- Implement connection with settings
- Add helper methods for workflow CRUD

---

### 1.4 API Scaffold

#### Step 1.4.1: Create FastAPI App
**File**: `app/main.py`

**Actions**:
- Create FastAPI app with metadata
- Configure CORS middleware
- Include API routers
- Add health endpoint
- Configure OpenAPI docs

---

#### Step 1.4.2: Create Pydantic Models
**File**: `app/models/workflow.py`

**Models to create**:
- `WorkflowInput` - Request body for POST /generate
- `WorkflowOutput` - Response with workflow status/result
- `WorkflowStatus` - Enum for workflow states

**Validation rules** (from SRS):
- `topic`: required string
- `duration_seconds`: 8-25, default 18
- `aspect_ratio`: "9:16" or "16:9", default "9:16"
- `resolution`: "720p" or "1080p", default "1080p"
- `category`: enum, default "auto"
- `hitl_mode`: "auto" or "manual", default "auto"

---

#### Step 1.4.3: Create API Routes (Stubs)
**Files**: `app/api/routes/generate.py`, `app/api/routes/workflows.py`

**Endpoints**:
- `POST /api/v1/generate` - Accept WorkflowInput, return workflow_id (stub)
- `GET /api/v1/workflows/{workflow_id}` - Return workflow status (stub)

**Note**: These are stubs that validate input and return mock responses. Real implementation comes in Phase 2+.

---

### 1.5 LangGraph Base Setup

#### Step 1.5.1: Define VideoGenerationState
**File**: `app/graph/state.py`

**Actions**:
- Create `TypedDict` for workflow state
- Define all state fields that will be passed between agents
- Use proper type hints

**State fields** (from Architecture doc):
```python
class VideoGenerationState(TypedDict):
    # Input
    workflow_id: str
    topic: str
    duration_seconds: int
    aspect_ratio: str
    resolution: str
    category: str
    hitl_mode: str
    enable_audio: bool
    enable_subtitles: bool
    user_reference_image_url: Optional[str]
    
    # Tool Selection (populated by Intent/Tool Selector)
    selected_tool: Optional[dict]
    intent_metadata: Optional[dict]
    
    # Research (populated by Deep Research)
    research_data: Optional[dict]
    research_images: Optional[list[str]]
    
    # Script (populated by Script Generator)
    script_output: Optional[dict]
    
    # Images (populated by Image Generator)
    generated_images: Optional[list[str]]
    all_images: Optional[list[str]]  # user + research + generated
    
    # Video (populated by Video Generator)
    video_url: Optional[str]
    video_metadata: Optional[dict]
    
    # HITL tracking
    hitl_approved: dict  # {gate_name: bool}
    hitl_feedback: list[dict]
    
    # Error handling
    error: Optional[str]
    
    # Timestamps
    started_at: str
    phase_timestamps: dict
```

---

#### Step 1.5.2: Define Workflow Graph Structure (NO PLACEHOLDERS)
**File**: `app/graph/workflow.py`

**Actions**:
- Define the graph structure with node names
- Define edges between nodes
- Add conditional routing for HITL gates
- **DO NOT implement placeholder agent functions** - just define the graph structure
- The graph will NOT be functional until agents are implemented in Phase 2+

**Approach**:
```python
from langgraph.graph import StateGraph, START, END
from app.graph.state import VideoGenerationState

def create_workflow_graph():
    """
    Create the LangGraph workflow structure.
    
    NOTE: This graph is NOT functional until agents are implemented in Phase 2+.
    Agent node functions are imported from app.agents when available.
    """
    workflow = StateGraph(VideoGenerationState)
    
    # Define nodes (will raise NotImplementedError until implemented)
    # Node functions will be added in Phase 2
    
    # Define edges
    # workflow.add_edge(START, "intent_tool_selector")
    # workflow.add_edge("intent_tool_selector", "deep_research")
    # etc.
    
    # For now, return None to indicate graph is not ready
    return None
```

**Why no placeholders?**
Per your request, we won't create placeholder functions that do nothing. The graph structure file will be created with the imports and structure ready, but actual compilation will happen when agents are implemented.

---

## Implementation Order

| # | Task | Files | Depends On |
|---|------|-------|------------|
| 1 | Create `pyproject.toml` | `pyproject.toml` | - |
| 2 | Create `requirements.txt` | `requirements.txt` | - |
| 3 | Create directory structure | All `__init__.py` | 1, 2 |
| 4 | Create `.env.example` | `.env.example` | - |
| 5 | Create config module | `app/config.py` | 3, 4 |
| 6 | Create SQL migrations | `migrations/*.sql` | - |
| 7 | Create Supabase service | `app/services/supabase.py` | 5 |
| 8 | Create Pydantic models | `app/models/workflow.py` | 3 |
| 9 | Create API routes | `app/api/routes/*.py` | 8 |
| 10 | Create FastAPI app | `app/main.py` | 9 |
| 11 | Create LangGraph state | `app/graph/state.py` | 3 |
| 12 | Create workflow graph structure | `app/graph/workflow.py` | 11 |
| 13 | Create tests | `tests/*.py` | 10 |
| 14 | Create README | `README.md` | All |

---

## Verification Checklist

After Phase 1 completion, verify:

- [ ] `pip install -r requirements.txt` succeeds
- [ ] `.env.example` has all required variables
- [ ] `uvicorn app.main:app --reload` starts without errors
- [ ] `GET /health` returns `{"status": "healthy"}`
- [ ] `GET /docs` shows OpenAPI documentation
- [ ] `POST /api/v1/generate` validates input and returns workflow_id
- [ ] `GET /api/v1/workflows/{id}` returns workflow status
- [ ] SQL migrations are valid (can be run in Supabase)
- [ ] `pytest tests/` passes
- [ ] LangGraph state is properly typed

---

## What's NOT in Phase 1

These will be implemented in later phases:
- ❌ Agent implementations (Phase 2)
- ❌ Tool repository with actual tools (Phase 2)
- ❌ Gemini API calls (Phase 2+)
- ❌ Image/Video generation (Phase 3)
- ❌ HITL feedback endpoints (Phase 4)
- ❌ Redis caching logic (Phase 4)
- ❌ LangSmith tracing setup (Phase 4)

---

## Ready to Implement?

Please review this plan and let me know:
1. Any changes to the directory structure?
2. Any additional dependencies needed?
3. Any changes to the database schema?
4. Any changes to the API endpoints?

Once approved, I'll start implementing step by step.
