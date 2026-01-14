# Phase 2.2: Tool Repository System - Implementation Plan

**Version**: 1.0  
**Created**: January 14, 2026  
**Based on**: IMPLEMENTATION_PLAN.md, RABA_Architecture.md, Gemini Documentation

---

## Overview

The **Tool Repository System** provides the tools that the Intent/Tool Selector Agent selects from. This phase includes:

1. **Tool Management**: Full CRUD operations for video generation tools
2. **AI-Enhanced Creation**: Users provide a simple idea → Gemini 2.5 Flash enhances it into a proper tool structure
3. **Tool Execution**: Endpoint to invoke tools with parameters

### Key Features
- Users provide a simple **idea** → Gemini AI enhances it into a proper tool structure
- Tools are stored in Supabase with Redis caching
- All tools are equal - seed tools are just pre-populated for testing, future tools added via API are the same

### LLM Model
- **Gemini 2.5 Flash** (`gemini-2.5-flash-preview`) - For tool enhancement
- Per `gemini_doc.md`: Keep temperature at default `1.0`, use `thinking_level="low"` for fast responses

---

## Architecture

```
TOOL MANAGEMENT ARCHITECTURE
════════════════════════════

┌─────────────────────────────────────────────────────────────────────────┐
│                           TOOL REPOSITORY                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────────┐         ┌──────────────────────────┐        │
│  │    All Tools         │         │    Tool Enhancement      │        │
│  │   (DB-stored)        │◀────────│    Service (Gemini)      │        │
│  └──────────┬───────────┘         └──────────────────────────┘        │
│             │                                                          │
│                     │                                                    │
│           ┌─────────▼─────────┐                                         │
│           │   ToolRegistry    │                                         │
│           │  (Unified Access) │                                         │
│           └─────────┬─────────┘                                         │
│                     │                                                    │
│  ┌──────────────────▼──────────────────┐                                │
│  │           REST API Endpoints         │                                │
│  │  GET /tools     POST /tools          │                                │
│  │  GET /tools/:id PUT /tools/:id       │                                │
│  │  DELETE /tools/:id                   │                                │
│  │  POST /tools/:id/execute             │                                │
│  └──────────────────────────────────────┘                                │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Steps

### Step 1: Database Schema Enhancement (`migrations/005_enhance_tools_table.sql`)
**Est. Time**: 30 min

Update the `tools` table to support dynamic tool creation and enhanced metadata.

#### New Columns to Add:

```
tools (existing table - add columns)
├── version: INTEGER DEFAULT 1
├── usage_count: INTEGER DEFAULT 0
├── success_rate: FLOAT DEFAULT 0.0
├── parameters_schema: JSONB  -- JSON Schema for tool parameters
├── original_idea: TEXT  -- User's original tool idea (if created via AI enhancement)
└── created_by: UUID  -- User who created the tool (nullable for seed tools)
```

#### Migration SQL:

```sql
-- migrations/005_enhance_tools_table.sql

ALTER TABLE tools ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1;
ALTER TABLE tools ADD COLUMN IF NOT EXISTS usage_count INTEGER DEFAULT 0;
ALTER TABLE tools ADD COLUMN IF NOT EXISTS success_rate FLOAT DEFAULT 0.0;
ALTER TABLE tools ADD COLUMN IF NOT EXISTS parameters_schema JSONB;
ALTER TABLE tools ADD COLUMN IF NOT EXISTS original_idea TEXT;
ALTER TABLE tools ADD COLUMN IF NOT EXISTS created_by UUID;
```

#### Reference:
- Existing schema: `migrations/002_create_tools.sql`

---

### Step 2: Pydantic Models for Tools (`app/models/tool.py`)
**Est. Time**: 45 min

Create comprehensive schema definitions for tool management. These extend the models created in Phase 2.1.

#### Models to Create:

```
ToolCreate (User Input - Minimal)
├── tool_name: str  -- User's name for the tool
├── idea: str  -- User's description of what they want
└── category: Optional[str]  -- Optional category hint

ToolCreateEnhanced (After Gemini Enhancement)
├── tool_id: str  -- Auto-generated slug
├── tool_name: str
├── category: CategoryEnum
├── description: str  -- AI-enhanced description
├── original_idea: str  -- Preserved user input
├── capabilities: ToolCapabilities
├── parameters_schema: dict  -- JSON Schema
├── script_prompt_template: str
├── image_prompt_template: str
└── video_prompt_template: str

ToolUpdate (Partial Update)
├── tool_name: Optional[str]
├── idea: Optional[str]  -- Re-enhancement if changed
├── description: Optional[str]
├── capabilities: Optional[ToolCapabilities]
├── is_active: Optional[bool]
├── script_prompt_template: Optional[str]
├── image_prompt_template: Optional[str]
└── video_prompt_template: Optional[str]

ToolResponse (API Response)
├── id: UUID
├── tool_id: str
├── tool_name: str
├── category: str
├── description: str
├── original_idea: Optional[str]
├── capabilities: ToolCapabilities
├── parameters_schema: Optional[dict]
├── script_prompt_template: str
├── image_prompt_template: str
├── video_prompt_template: str
├── is_active: bool
├── usage_count: int
├── success_rate: float
├── created_at: datetime
└── updated_at: datetime

ToolExecutionRequest
├── topic: str
└── parameters: Optional[dict]

ToolExecutionResponse
├── tool_id: str
├── generated_prompts: ToolPrompts
└── estimated_generation_time: float

ToolPrompts
├── script_prompt: str
├── image_prompt: str
└── video_prompt: str

ToolListResponse
├── tools: list[ToolResponse]
├── total: int
├── limit: int
└── offset: int

DeleteResponse
├── success: bool
└── tool_id: str
```

#### Key Considerations:
- Use `Field(description="...")` for OpenAPI documentation
- Add validators for category, tool_id format
- Inherit from Phase 2.1's `ToolCapabilities` and `ToolMetadata`

---

### Step 3: Tool Enhancement Service (`app/services/tool_enhancer.py`)
**Est. Time**: 1.5 hr

Create a service that uses Gemini 2.5 Flash to enhance user tool ideas into properly structured tools.

#### Workflow:

```
User Idea ──▶ Gemini 2.5 Flash ──▶ Structured Tool
    │                                    │
    │  "I want a tool that creates       │  {
    │   cyberpunk-style videos with      │    tool_id: "cyberpunk_neon_dreams",
    │   neon colors and rain"            │    category: "stylized_3d",
    │                                    │    capabilities: {...},
    └────────────────────────────────────│    prompts: {...}
                                         │  }
```

#### Service Structure:

```
ToolEnhancerService
├── __init__(gemini_service: GeminiService)
│
├── enhance_tool_idea(
│   │   idea: str,
│   │   category_hint: Optional[str] = None,
│   │   tool_name: Optional[str] = None
│   └── ) -> ToolCreateEnhanced
│
├── _build_enhancement_prompt(idea: str, category_hint: str) -> str
├── _classify_category(idea: str) -> CategoryEnum
├── _generate_tool_id(tool_name: str) -> str
├── _generate_capabilities(idea: str, category: str) -> ToolCapabilities
└── _generate_prompt_templates(idea: str, category: str) -> ToolPrompts
```

#### System Prompt for Enhancement:

```xml
<role>
You are an expert video generation tool designer for the RABA system.
Your task is to transform user ideas into properly structured video generation tools.
</role>

<context>
RABA generates YouTube Shorts (8-25 seconds) in these visual categories:
- surreal_realism: Photorealistic with impossible/surreal elements
- high_octane_anime: Sakuga-style anime with dynamic action
- stylized_3d: Stylized 3D graphics and data visualization
</context>

<output_requirements>
Generate a complete tool definition including:
1. tool_id: A unique slug (lowercase, underscores)
2. category: One of the three categories above
3. description: Enhanced description (2-3 sentences)
4. capabilities: Object with boolean flags for tool features
5. script_prompt_template: Template for script generation
6. image_prompt_template: Template for image generation
7. video_prompt_template: Template for video generation
8. parameters_schema: JSON Schema for tool parameters
</output_requirements>

<constraints>
- Templates must include {topic}, {tone}, {duration} placeholders
- Categories must be exactly: surreal_realism, high_octane_anime, or stylized_3d
- tool_id must be unique and URL-safe
</constraints>
```

#### Few-Shot Examples:

| User Idea | Category | Tool ID |
|-----------|----------|---------|
| "Visualize physics and quantum effects" | surreal_realism | quantum_physics_visualizer |
| "Epic anime battles for debates" | high_octane_anime | concept_combat |
| "Turn data into miniature scenes" | stylized_3d | data_dioramas |

#### Gemini Configuration:
- Model: `gemini-2.5-flash-preview`
- Thinking level: `low` (per `gemini_doc.md:92`)
- Response format: `application/json`
- Temperature: `1.0` (per `gemini_doc.md:263`)

#### Reference:
- Gemini Structured Outputs: `gemini_doc.md:509-608`
- Tool Abstraction: `RABA_Architecture.md:712-788`

---

### Step 4: Base Tool Class & Static Implementations (`app/tools/`)
**Est. Time**: 2 hr

Create the abstract base class and implement the 3 initial static tools.

#### File Structure:

```
app/tools/
├── __init__.py
├── base.py                         # Abstract VideoGenerationTool
└── implementations/
    ├── __init__.py
    ├── surreal_realism.py          # "Impossible Simulations"
    ├── high_octane_anime.py        # "Concept Combat"
    └── stylized_3d.py              # "Data Dioramas"
```

#### Base Class (`app/tools/base.py`):

```
VideoGenerationTool (ABC)
├── Attributes:
│   ├── tool_id: str
│   ├── tool_name: str
│   ├── category: str
│   ├── capabilities: ToolCapabilities
│   ├── description: str
│   ├── supported_aspect_ratios: list[str]
│   ├── supported_resolutions: list[str]
│   ├── max_duration_seconds: int
│   ├── cost_per_request: float
│   └── estimated_quality: float
│
├── Abstract Methods:
│   ├── get_optimal_script_format() -> ScriptFormatSpec
│   ├── get_image_prompt_template() -> str
│   ├── get_video_prompt_template() -> str
│   ├── validate_topic_fit(topic: str, intent: str) -> float
│   └── estimate_generation_time() -> float
│
├── Concrete Methods:
│   ├── execute(topic: str, parameters: dict) -> ToolExecutionResult
│   ├── to_dict() -> dict
│   └── from_db_record(record: dict) -> VideoGenerationTool
```

#### Static Tool Implementations:

**1. Surreal Realism - "Impossible Simulations"** (`surreal_realism.py`)

```
ImpossibleSimulationsTool(VideoGenerationTool)
├── tool_id: "surreal_impossible_sims"
├── tool_name: "Impossible Simulations"
├── category: "surreal_realism"
├── capabilities:
│   ├── flow_visualization: true
│   ├── invisible_forces: true
│   └── photorealistic_grounding: true
├── viral_signal: "Information without Boredom"
└── keywords: ["physics", "quantum", "magnetic", "force", "invisible", "structure"]
```

**2. High-Octane Anime - "Concept Combat"** (`high_octane_anime.py`)

```
ConceptCombatTool(VideoGenerationTool)
├── tool_id: "anime_concept_combat"
├── tool_name: "Concept Combat"
├── category: "high_octane_anime"
├── capabilities:
│   ├── philosophical_debates: true
│   ├── sakuga_style: true
│   └── calligraphic_combat: true
├── viral_signal: "Zen-Action"
└── keywords: ["philosophy", "ethics", "science", "history", "discovery", "debate"]
```

**3. Stylized 3D - "Data Dioramas"** (`stylized_3d.py`)

```
DataDioramasTool(VideoGenerationTool)
├── tool_id: "stylized_data_dioramas"
├── tool_name: "Data Dioramas"
├── category: "stylized_3d"
├── capabilities:
│   ├── data_visualization: true
│   ├── miniature_style: true
│   └── 3d_rendering: true
├── viral_signal: "Abstract made Tangible"
└── keywords: ["data", "statistics", "numbers", "trends", "comparison"]
```

#### Reference:
- Tool implementations: `RABA_Architecture.md:793-852`

---

### Step 5: Tool Registry Service (`app/tools/registry.py`)
**Est. Time**: 1 hr

Create a unified registry that manages both static and dynamic tools.

#### Service Structure:

```
ToolRegistry
├── __init__(supabase: SupabaseClient, redis: RedisClient)
│
├── CRUD Operations:
│   ├── register_tool(tool: ToolCreateEnhanced) -> ToolResponse
│   ├── get_tool(tool_id: str) -> Optional[ToolResponse]
│   ├── list_all_tools(filters: ToolFilters) -> ToolListResponse
│   ├── get_tools_by_category(category: str) -> list[ToolResponse]
│   ├── update_tool(tool_id: str, updates: ToolUpdate) -> ToolResponse
│   └── delete_tool(tool_id: str) -> bool  # Soft delete
│
├── Query Operations:
│   ├── score_tools_for_topic(topic: str, intent: IntentMetadata) -> list[ScoredTool]
│   └── increment_usage(tool_id: str) -> None
│
├── Cache Operations:
│   ├── invalidate_cache() -> None
│   ├── _get_from_cache(key: str) -> Optional[Any]
│   └── _set_cache(key: str, value: Any, ttl: int) -> None
│
└── Internal:
    └── _load_tools_from_db() -> list[ToolResponse]
```

#### Caching Strategy:

| Cache Key | Value | TTL |
|-----------|-------|-----|
| `tools:list` | All active tools (JSON) | 1 hour |
| `tools:category:{category}` | Tools by category | 1 hour |
| `tools:id:{tool_id}` | Single tool | 1 hour |

#### Invalidation Triggers:
- `register_tool()` → invalidate all
- `update_tool()` → invalidate all
- `delete_tool()` → invalidate all

#### Reference:
- Registry Pattern: `RABA_Architecture.md:759-789`

---

### Step 6: Tool Validation Service (`app/services/tool_validator.py`)
**Est. Time**: 45 min

Validate tool configurations before persisting.

#### Validation Rules:

```
ToolValidator
├── validate(tool: ToolCreateEnhanced) -> None  # Raises ValidationError
│
├── Structure Validation:
│   ├── _validate_required_fields(tool)
│   ├── _validate_category(category: str)
│   ├── _validate_tool_id(tool_id: str)  # Slug format, unique
│   └── _validate_capabilities(capabilities: dict, category: str)
│
├── Prompt Template Validation:
│   ├── _validate_script_template(template: str)
│   │   └── Must contain: {topic}, {tone}, {duration}
│   ├── _validate_image_template(template: str)
│   │   └── Must contain: {scene_description}, {style}
│   └── _validate_video_template(template: str)
│       └── Must contain: {script}, {image_reference}
│
└── Safety Validation:
    ├── _check_blacklisted_terms(text: str)
    └── _check_content_safety(description: str)
```

#### Error Types:
- `ToolValidationError`: Base validation error
- `InvalidCategoryError`: Category not in allowed list
- `InvalidToolIdError`: Tool ID format invalid or duplicate
- `MissingPlaceholderError`: Prompt template missing required placeholders
- `UnsafeContentError`: Content contains blacklisted terms

---

### Step 7: Tools API Endpoints (`app/api/routes/tools.py`)
**Est. Time**: 2 hr

Create comprehensive REST API for tool management.

#### Endpoints Summary:

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/api/v1/tools` | List all tools (with filters) | Public |
| `GET` | `/api/v1/tools/{tool_id}` | Get tool by ID | Public |
| `POST` | `/api/v1/tools` | Create new tool (AI-enhanced) | Auth |
| `PUT` | `/api/v1/tools/{tool_id}` | Update existing tool | Auth |
| `DELETE` | `/api/v1/tools/{tool_id}` | Delete tool (soft delete) | Auth |
| `POST` | `/api/v1/tools/{tool_id}/execute` | Execute tool with params | Auth |
| `POST` | `/api/v1/tools/preview` | Preview AI enhancement (dry-run) | Auth |

---

#### Endpoint 1: GET /api/v1/tools

List all tools with optional filters.

**Query Parameters:**
- `category`: Filter by category (surreal_realism, high_octane_anime, stylized_3d)
- `is_active`: Filter by active status (default: true)
- `limit`: Pagination limit (default: 50)
- `offset`: Pagination offset (default: 0)

**Response:** `ToolListResponse`

---

#### Endpoint 2: GET /api/v1/tools/{tool_id}

Get single tool by ID.

**Path Parameters:**
- `tool_id`: Unique tool identifier

**Response:** `ToolResponse`

**Errors:**
- `404`: Tool not found

---

#### Endpoint 3: POST /api/v1/tools (AI-Enhanced Creation)

Create a new tool from user idea. Gemini 2.5 Flash enhances the idea.

**Request Body:** `ToolCreate`
```json
{
  "tool_name": "Cyberpunk Neon Dreams",
  "idea": "Create videos with neon-lit cyberpunk cityscapes, rain effects, and holographic overlays.",
  "category": "stylized_3d"
}
```

**Workflow:**
```
User Input → Gemini Enhancement → Validation → Database → Response
```

**Response:** `ToolResponse` (with AI-enhanced fields)

**Errors:**
- `400`: Invalid input
- `422`: Validation failed
- `500`: Enhancement service error

---

#### Endpoint 4: PUT /api/v1/tools/{tool_id}

Update an existing tool.

**Request Body:** `ToolUpdate` (partial)
```json
{
  "idea": "Updated idea with more details...",
  "is_active": true
}
```

**Rules:**
- If `idea` changes, re-enhance with Gemini

**Response:** `ToolResponse`

**Errors:**
- `404`: Tool not found

---

#### Endpoint 5: DELETE /api/v1/tools/{tool_id}

Soft delete a tool.

**Rules:**
- Sets `is_active = false` (soft delete)

**Response:** `DeleteResponse`

**Errors:**
- `404`: Tool not found

---

#### Endpoint 6: POST /api/v1/tools/{tool_id}/execute

Execute a tool with a topic to generate prompts.

**Request Body:** `ToolExecutionRequest`
```json
{
  "topic": "The future of quantum computing",
  "parameters": {
    "tone": "educational",
    "duration_seconds": 18
  }
}
```

**Response:** `ToolExecutionResponse`
```json
{
  "tool_id": "surreal_impossible_sims",
  "generated_prompts": {
    "script_prompt": "Visualize quantum superposition as...",
    "image_prompt": "A photorealistic scene showing...",
    "video_prompt": "Create an 18-second video depicting..."
  },
  "estimated_generation_time": 120.0
}
```

**Errors:**
- `404`: Tool not found
- `422`: Invalid parameters

---

#### Endpoint 7: POST /api/v1/tools/preview

Preview AI enhancement without saving (dry run).

**Request Body:** `ToolCreate`

**Response:** `ToolCreateEnhanced`

**Use Case:** User can review what Gemini generates before committing.

---

### Step 8: Tool Execution Logic (`app/services/tool_executor.py`)
**Est. Time**: 45 min

Implement the execution pipeline for generating prompts from tools.

#### Service Structure:

```
ToolExecutor
├── execute(tool: ToolResponse, topic: str, parameters: dict) -> ToolExecutionResult
│
├── _build_context(topic: str, parameters: dict) -> dict
│   └── Returns: {topic, tone, duration, ...parameters}
│
├── _render_template(template: str, context: dict) -> str
│   └── Substitutes {placeholders} with context values
│
└── _validate_parameters(parameters: dict, schema: dict) -> None
    └── Validates against tool's parameters_schema
```

#### Template Rendering:

```python
def _render_template(self, template: str, context: dict) -> str:
    """
    Render a prompt template with context variables.
    
    Example:
    template = "Create a {tone} video about {topic} for {duration} seconds"
    context = {"topic": "black holes", "tone": "educational", "duration": 18}
    result = "Create a educational video about black holes for 18 seconds"
    """
    return template.format(**context)
```

---

### Step 9: Seed Initial Tools (`scripts/seed_tools.py`)
**Est. Time**: 20 min

Create a script to seed the 3 static tools into the database.

#### Script Structure:

```python
# scripts/seed_tools.py

STATIC_TOOLS = [
    {
        "tool_id": "surreal_impossible_sims",
        "tool_name": "Impossible Simulations",
        "category": "surreal_realism",
        "source": "static",
        # ... full config
    },
    {
        "tool_id": "anime_concept_combat",
        "tool_name": "Concept Combat",
        "category": "high_octane_anime",
        "source": "static",
        # ... full config
    },
    {
        "tool_id": "stylized_data_dioramas",
        "tool_name": "Data Dioramas",
        "category": "stylized_3d",
        "source": "static",
        # ... full config
    }
]

async def seed_tools():
    """Insert static tools using ON CONFLICT DO UPDATE for idempotency."""
    for tool in STATIC_TOOLS:
        await supabase.table("tools").upsert(tool).execute()
```

#### Run:
```bash
python -m scripts.seed_tools
```

---

### Step 10: Unit Tests (`tests/test_tools/`)
**Est. Time**: 1.5 hr

Comprehensive test coverage for tool management.

#### Test Files:

```
tests/test_tools/
├── __init__.py
├── test_tool_models.py
├── test_tool_enhancer.py
├── test_tool_registry.py
├── test_tool_api.py
└── test_tool_validator.py
```

#### Test Cases:

**test_tool_models.py**
```
├── test_tool_create_validation
├── test_tool_update_partial_fields
├── test_tool_capabilities_nested_model
├── test_tool_response_serialization
└── test_tool_execution_request_validation
```

**test_tool_enhancer.py** (Mock Gemini)
```
├── test_enhance_simple_idea
├── test_enhance_with_category_hint
├── test_category_classification_accuracy
├── test_tool_id_generation_unique
├── test_handle_invalid_idea_gracefully
└── test_prompt_template_generation
```

**test_tool_registry.py**
```
├── test_register_new_tool
├── test_get_tool_by_id
├── test_get_tool_not_found
├── test_list_tools_with_filters
├── test_update_tool
├── test_delete_tool_soft
├── test_cache_invalidation
└── test_score_tools_for_topic
```

**test_tool_api.py**
```
├── test_get_tools_list
├── test_get_tools_filter_by_category
├── test_get_single_tool
├── test_create_tool_with_enhancement
├── test_update_tool
├── test_delete_tool
├── test_execute_tool
└── test_preview_enhancement
```

**test_tool_validator.py**
```
├── test_valid_tool_passes
├── test_invalid_category_fails
├── test_invalid_tool_id_format_fails
├── test_missing_placeholder_fails
├── test_blacklisted_terms_blocked
└── test_partial_update_validation
```

#### Mock Strategy:
- Mock `GeminiService` for deterministic tests
- Mock Supabase client for DB tests
- Use `pytest-asyncio` for async tests

---

### Step 11: Integration Tests (`tests/test_integration/test_tool_flow.py`)
**Est. Time**: 1 hr

End-to-end tests for the tool management flow.

#### Test Scenarios:

**1. Create Tool Flow**
```
User idea → POST /tools → Gemini Enhancement → Validation → DB → Response
Verify: Enhanced fields populated, persisted, cached
```

**2. Full CRUD Cycle**
```
Create → GET (verify) → Update → GET (verify changes) → Delete → GET (verify 404)
```

**3. Tool Execution in Workflow**
```
Create custom tool → Intent/Tool Selector selects it → Verify prompts generated
```

**4. Cache Behavior**
```
Create tool → Verify cache updated
Update tool → Verify cache invalidated
List tools → Verify served from cache (fast)
```

---

## File Structure Summary

```
Backend/
├── app/
│   ├── models/
│   │   └── tool.py              # UPDATE - Add new models
│   │
│   ├── services/
│   │   ├── tool_enhancer.py     # NEW - Gemini enhancement service
│   │   ├── tool_validator.py    # NEW - Validation service
│   │   └── tool_executor.py     # NEW - Execution service
│   │
│   ├── tools/
│   │   ├── __init__.py          # NEW
│   │   ├── base.py              # NEW - Abstract base class
│   │   ├── registry.py          # NEW - Tool registry
│   │   └── implementations/
│   │       ├── __init__.py      # NEW
│   │       ├── surreal_realism.py    # NEW
│   │       ├── high_octane_anime.py  # NEW
│   │       └── stylized_3d.py        # NEW
│   │
│   └── api/
│       └── routes/
│           └── tools.py         # NEW - CRUD + Execute endpoints
│
├── migrations/
│   └── 005_enhance_tools_table.sql  # NEW
│
├── scripts/
│   └── seed_tools.py            # NEW
│
└── tests/
    ├── test_tools/
    │   ├── __init__.py          # NEW
    │   ├── test_tool_models.py  # NEW
    │   ├── test_tool_enhancer.py    # NEW
    │   ├── test_tool_registry.py    # NEW
    │   ├── test_tool_api.py     # NEW
    │   └── test_tool_validator.py   # NEW
    │
    └── test_integration/
        └── test_tool_flow.py    # NEW
```

---

## Dependencies

No new dependencies required beyond Phase 2.1:

```txt
# Already in requirements.txt from Phase 2.1
google-genai>=1.0.0           # Gemini API (for enhancement)
supabase>=2.0.0               # Database
upstash-redis>=0.15.0         # Caching
```

---

## Configuration Required

Ensure these are set in `.env`:

```bash
# Already configured
GOOGLE_API_KEY=your_gemini_api_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
UPSTASH_REDIS_URL=your_redis_url
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Gemini returns invalid JSON | Use `response_mime_type: application/json` + schema enforcement |
| Duplicate tool_id | Check uniqueness before insert, append suffix if needed |
| Cache stale data | Aggressive invalidation on all mutations |
| Template injection | Validate placeholders, escape user content |

---

## Success Criteria

- [ ] Database migration runs successfully
- [ ] Seed tools are seeded and retrievable
- [ ] POST /tools creates AI-enhanced tool from idea
- [ ] PUT /tools updates any tool
- [ ] DELETE /tools soft-deletes any tool
- [ ] POST /tools/{id}/execute generates valid prompts
- [ ] POST /tools/preview returns enhanced tool without saving
- [ ] Cache invalidation works on all mutations
- [ ] All unit tests pass
- [ ] Integration tests complete successfully

---

## Estimated Total Time

| Step | Task | Time |
|------|------|------|
| 1 | Database schema enhancement | 30 min |
| 2 | Pydantic models | 45 min |
| 3 | Tool Enhancement Service (Gemini) | 1.5 hr |
| 4 | Base tool class + static implementations | 2 hr |
| 5 | Tool Registry Service | 1 hr |
| 6 | Tool Validation Service | 45 min |
| 7 | Tools API Endpoints | 2 hr |
| 8 | Tool Execution Logic | 45 min |
| 9 | Seed initial tools | 20 min |
| 10 | Unit tests | 1.5 hr |
| 11 | Integration tests | 1 hr |
| **Total** | | **~12 hours** |

---

## Next Steps After Phase 2.2

Once complete, proceed to **Phase 2.3: Deep Research Agent** which will use the selected tool's specifications for research context.

---

## Questions for Review

1. Should tool_id be user-editable or always auto-generated?
2. Should we implement tool versioning with history?
3. Should tools have rate limits per tool_id?
4. Should we add a "featured" or "verified" flag for quality tools?

---

**Please review this plan and let me know if you'd like any modifications before I begin implementation.**
