# Phase 2.1: Intent/Tool Selector Agent - Implementation Plan

**Version**: 1.0  
**Created**: January 14, 2026  
**Based on**: IMPLEMENTATION_PLAN.md, RABA_Architecture.md, Gemini Documentation

---

## Overview

The **Intent/Tool Selector Agent** is the first agent in the RABA pipeline and is **critical** - all other agents depend on its output. Per `rule.md` and architecture guidelines, Intent extraction and Tool selection are **combined into a single agent** to reduce latency.

### Agent Responsibilities
1. **Extract intent** from user's topic input
2. **Validate parameters** (duration, resolution, aspect ratio)
3. **Query tool repository** and select the best-fit tool
4. **Return structured output** for downstream agents

### LLM Model
- **Gemini 3 Flash Preview** (`gemini-3-flash-preview`) - Low-latency, cost-optimized
- Per `gemini_doc.md`: Keep temperature at default `1.0`, use `thinking_level="low"` for fast responses

---

## Implementation Steps

### Step 1: Create Pydantic Models (`app/models/tool.py`)
**Est. Time**: 30-45 min

Create comprehensive schema definitions for intent metadata, tool selection, and validated parameters.

#### Models to Create:

```
IntentType (Enum)
├── educational
├── entertainment  
├── inspirational
└── tutorial

ToneType (Enum)
├── serious
├── humorous
├── dramatic
└── casual

TargetAudience (Enum)
├── general
├── tech
├── science
└── business

GenerationMode (Enum)
├── text_2_video
└── image_2_video

ValidatedParams (BaseModel)
├── duration_seconds: int (8-25)
├── aspect_ratio: AspectRatioEnum
├── resolution: ResolutionEnum
└── generation_mode: GenerationMode

ToolCapabilities (BaseModel)
├── flow_visualization: bool
├── invisible_forces: bool
├── photorealistic_grounding: bool
├── philosophical_debates: bool
├── sakuga_style: bool
├── viral_signal: str

ToolMetadata (BaseModel)
├── tool_id: str
├── tool_name: str
├── category: CategoryEnum
├── description: str
├── capabilities: ToolCapabilities
├── supported_aspect_ratios: list[str]
├── supported_resolutions: list[str]
├── max_duration_seconds: int
├── cost_per_request: float
├── estimated_quality: float (0-1)

IntentMetadata (BaseModel)
├── topic: str
├── intent_type: IntentType
├── target_audience: TargetAudience
├── tone: ToneType
├── keywords: list[str]
├── complexity_score: float (0-1)

IntentToolOutput (BaseModel) [MAIN OUTPUT]
├── topic: str
├── intent_metadata: IntentMetadata
├── validated_params: ValidatedParams
├── selected_tool: ToolMetadata
├── tool_execution_params: dict
├── confidence: float (0-1)
├── fallback_used: bool
```

#### Key Considerations:
- Use `Field(description="...")` for all fields per structured output best practices
- Inherit from existing `CategoryEnum`, `AspectRatioEnum`, `ResolutionEnum` in `workflow.py`
- Add validators for parameter ranges

---

### Step 2: Create Gemini Service (`app/services/gemini.py`)
**Est. Time**: 45-60 min

Create a reusable wrapper for the Google GenAI SDK.

#### Service Structure:

```
GeminiService
├── __init__(api_key: str)
├── _get_client() -> genai.Client
│
├── generate_structured_output[T](
│   │   prompt: str,
│   │   response_model: Type[T],
│   │   model: str = "gemini-3-flash-preview",
│   │   thinking_level: str = "low",
│   │   system_instruction: Optional[str] = None
│   └── ) -> T
│
├── generate_text(
│   │   prompt: str,
│   │   model: str = "gemini-3-flash-preview",
│   │   thinking_level: str = "high"
│   └── ) -> str
│
└── generate_with_grounding(
    │   prompt: str,
    │   model: str = "gemini-3-pro-preview"
    └── ) -> tuple[str, list[Citation]]
```

#### Implementation References:

**From `gemini_doc.md`:**
```python
from google import genai
from google.genai import types

client = genai.Client()

# For structured output with Pydantic
response = client.models.generate_content(
    model="gemini-3-flash-preview",
    contents=prompt,
    config={
        "response_mime_type": "application/json",
        "response_json_schema": ResponseModel.model_json_schema(),
    },
)
result = ResponseModel.model_validate_json(response.text)
```

**Thinking Level Configuration (from `gemini_doc.md`):**
```python
config=types.GenerateContentConfig(
    thinking_config=types.ThinkingConfig(thinking_level="low")
)
```

#### Key Considerations:
- Use `thinking_level="low"` for Intent/Tool Selector (speed priority)
- Handle API errors gracefully with retries
- Add logging for debugging
- Support both sync and async operations

---

### Step 3: Implement Intent Extraction (`app/agents/intent_tool_selector.py`)
**Est. Time**: 1 hour

Extract intent from topic using LLM with structured output.

#### Prompt Design (based on `prompting_Docs.md`):

**System Instruction:**
```xml
<role>
You are an expert video content strategist specializing in YouTube Shorts.
Your task is to analyze topics and determine the optimal video generation approach.
</role>

<constraints>
1. Always infer intent from context - never ask for clarification
2. Be precise and direct in classification
3. Consider viral potential when determining tone
</constraints>

<output_format>
Return a structured JSON response matching the IntentMetadata schema.
</output_format>
```

**User Prompt Template:**
```xml
<context>
Topic: {user_topic}
Duration: {duration_seconds} seconds
Category Preference: {category} (auto = let AI decide)
</context>

<task>
Analyze the topic and extract:
1. The core intent type (educational, entertainment, inspirational, tutorial)
2. Target audience (general, tech, science, business)
3. Optimal tone for viral engagement (serious, humorous, dramatic, casual)
4. Key keywords for tool matching
5. Complexity score (0-1) based on topic depth
</task>

<final_instruction>
Think step-by-step about what would make this topic most engaging for YouTube Shorts.
</final_instruction>
```

#### Few-Shot Examples:
Per `prompting_Docs.md`, include 2-3 examples for consistency:

| Topic | Intent | Audience | Tone |
|-------|--------|----------|------|
| "How black holes work" | educational | science | serious |
| "Why cats hate water" | entertainment | general | humorous |
| "Einstein's forgotten discovery" | inspirational | science | dramatic |

---

### Step 4: Implement Parameter Validation (`app/agents/intent_tool_selector.py`)
**Est. Time**: 30 min

Validate and normalize user parameters.

#### Validation Logic:

```
validate_params(user_input: WorkflowInput) -> ValidatedParams
├── Validate duration: 8 ≤ duration ≤ 25
├── Validate aspect_ratio: ["9:16", "16:9"]
├── Validate resolution: ["720p", "1080p"]
├── Determine generation_mode:
│   ├── If user provided reference_image → image_2_video
│   └── Otherwise → text_2_video
└── Return ValidatedParams with normalized values
```

#### Default Fallbacks (from `config.py`):
- Duration: 18 seconds
- Aspect Ratio: 9:16 (vertical for Shorts)
- Resolution: 1080p
- Generation Mode: text_2_video

---

### Step 5: Implement Tool Scoring (`app/agents/intent_tool_selector.py`)
**Est. Time**: 45 min

Score tools by topic relevance using the scoring formula from Architecture doc.

#### Scoring Formula (from `RABA_Architecture.md`):
```
score = (relevance_match × 0.4) + (capability_match × 0.3) + 
        (cost_efficiency × 0.2) + (recency_success × 0.1)
```

#### Scoring Implementation:

```
score_tool(tool: ToolMetadata, intent: IntentMetadata, params: ValidatedParams) -> float
├── relevance_match: LLM-based semantic similarity (tool description ↔ topic)
├── capability_match: Binary check of required capabilities
│   └── Does tool support duration/resolution/aspect_ratio?
├── cost_efficiency: Inverse of cost_per_request (normalized)
└── recency_success: Placeholder for future analytics (default 0.5)
```

#### LLM Relevance Scoring Prompt:
```
Rate the relevance of this video generation tool for the given topic.

Tool: {tool_name}
Description: {tool_description}
Capabilities: {capabilities}

Topic: {topic}
Intent: {intent_type}
Keywords: {keywords}

Return a score from 0.0 to 1.0 where:
- 1.0 = Perfect match
- 0.7+ = Good match
- 0.4-0.7 = Acceptable
- <0.4 = Poor match
```

---

### Step 6: Implement Tool Selection (`app/agents/intent_tool_selector.py`)
**Est. Time**: 30 min

Select the best tool from category or fallback.

#### Selection Algorithm:

```
select_tool(intent: IntentMetadata, params: ValidatedParams, tools: list[ToolMetadata]) -> ToolMetadata
│
├── 1. Filter by category (if user specified, else all)
├── 2. Filter by capability (duration, resolution support)
├── 3. Score remaining tools
├── 4. Sort by score descending
├── 5. Select top tool
│
└── Fallback chain:
    ├── Primary unavailable → Secondary from same category
    ├── Category unavailable → Default "Surreal Realism" (most flexible)
    └── All unavailable → Raise error for manual review
```

---

### Step 7: Create Fallback Logic (`app/agents/intent_tool_selector.py`)
**Est. Time**: 20 min

Implement graceful degradation when tools unavailable.

#### Fallback Strategy:

```
DEFAULT_TOOL_ID = "surreal_impossible_sims"  # Surreal Realism - most flexible

get_fallback_tool(category: CategoryEnum) -> ToolMetadata
├── Try: Get any tool from requested category
├── Catch: Get default Surreal Realism tool
└── Final: Raise IntentToolError for manual intervention
```

#### Error Handling:
- `ToolNotFoundError`: No tools in registry
- `CategoryUnavailableError`: Requested category has no tools
- `ValidationError`: Invalid parameters

---

### Step 8: Wire to LangGraph Node (`app/graph/nodes.py`)
**Est. Time**: 20 min

Connect the agent to the LangGraph workflow.

#### Node Function:

```python
async def intent_tool_selector_node(state: VideoGenerationState) -> VideoGenerationState:
    """
    LangGraph node for Intent/Tool Selection.
    
    Input: state.user_topic, state.user_params
    Output: state.intent_metadata, state.selected_tool, state.tool_execution_params
    """
    agent = IntentToolSelectorAgent()
    result = await agent.run(
        topic=state["user_topic"],
        params=state["user_params"]
    )
    
    return {
        **state,
        "intent_metadata": result.intent_metadata.model_dump(),
        "selected_tool": result.selected_tool.model_dump(),
        "tool_execution_params": result.tool_execution_params,
        "phase_timestamps": {
            **state.get("phase_timestamps", {}),
            "intent_tool_completed": datetime.utcnow().isoformat()
        }
    }
```

#### Graph Integration:
```python
# In app/graph/workflow.py
from app.graph.nodes import intent_tool_selector_node

graph.add_node("intent_tool_selector", intent_tool_selector_node)
graph.add_edge(START, "intent_tool_selector")
graph.add_edge("intent_tool_selector", "deep_research")  # Next node
```

---

### Step 9: Write Unit Tests (`tests/test_agents/test_intent.py`)
**Est. Time**: 45 min

Test intent extraction and tool selection.

#### Test Cases:

```
test_intent_tool_selector.py
│
├── TestIntentExtraction
│   ├── test_educational_topic_classification
│   ├── test_entertainment_topic_classification
│   ├── test_inspirational_topic_classification
│   ├── test_tone_inference_humorous
│   ├── test_tone_inference_serious
│   └── test_keyword_extraction
│
├── TestParameterValidation
│   ├── test_valid_duration_range
│   ├── test_invalid_duration_fallback
│   ├── test_aspect_ratio_validation
│   └── test_generation_mode_detection
│
├── TestToolScoring
│   ├── test_relevance_scoring
│   ├── test_capability_matching
│   └── test_cost_efficiency_calculation
│
├── TestToolSelection
│   ├── test_select_best_tool_for_science_topic
│   ├── test_select_best_tool_for_philosophy_topic
│   ├── test_fallback_to_default_tool
│   └── test_category_filtering
│
└── TestIntegration
    ├── test_full_intent_tool_pipeline
    ├── test_with_user_category_preference
    └── test_with_auto_category
```

#### Mock Strategy:
- Mock `GeminiService` for deterministic tests
- Create fixture tools for registry testing
- Use `pytest-asyncio` for async tests

---

### Step 10: Integration Test
**Est. Time**: 30 min

End-to-end test via API.

#### Test Scenarios:

1. **Auto Category Selection**
   ```bash
   POST /api/v1/generate
   {
     "topic": "How quantum computers work",
     "duration_seconds": 18,
     "category": "auto"
   }
   ```
   Expected: Returns `surreal_realism` category with physics-focused tool

2. **Explicit Category Selection**
   ```bash
   POST /api/v1/generate
   {
     "topic": "Plato vs Aristotle debate",
     "duration_seconds": 20,
     "category": "high_octane_anime"
   }
   ```
   Expected: Returns `high_octane_anime` with Concept Combat tool

3. **Fallback Test**
   ```bash
   POST /api/v1/generate
   {
     "topic": "Random topic",
     "duration_seconds": 25,
     "category": "stylized_3d"  # No tools registered
   }
   ```
   Expected: Falls back to Surreal Realism

---

## File Structure Summary

```
Backend/
├── app/
│   ├── models/
│   │   ├── tool.py              # NEW - Intent/Tool schemas
│   │   └── workflow.py          # EXISTS - Update imports
│   │
│   ├── services/
│   │   └── gemini.py            # NEW - Gemini API wrapper
│   │
│   ├── agents/
│   │   ├── __init__.py          # UPDATE - Export agent
│   │   └── intent_tool_selector.py  # NEW - Main agent
│   │
│   └── graph/
│       ├── nodes.py             # UPDATE - Add node function
│       └── workflow.py          # UPDATE - Wire node
│
└── tests/
    └── test_agents/
        ├── __init__.py          # NEW
        └── test_intent.py       # NEW - Unit tests
```

---

## Dependencies to Add

```txt
# requirements.txt additions
google-genai>=1.0.0           # Google GenAI SDK
```

---

## Configuration Required

Ensure these are set in `.env`:

```bash
GOOGLE_API_KEY=your_gemini_api_key
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| LLM returns invalid JSON | Use `response_mime_type: application/json` + schema enforcement |
| API rate limiting | Implement exponential backoff retry |
| Tool registry empty | Seed default tools before running agent |
| High latency | Use `thinking_level="low"` for Gemini 3 Flash |

---

## Success Criteria

- [ ] Intent extraction returns valid `IntentMetadata` for any topic
- [ ] Parameter validation catches all edge cases
- [ ] Tool scoring produces consistent rankings
- [ ] Fallback logic handles all failure modes
- [ ] All unit tests pass
- [ ] Integration test completes in <10s
- [ ] LangGraph node integrates without errors

---

## Estimated Total Time

| Step | Task | Time |
|------|------|------|
| 1 | Create Pydantic models | 30-45 min |
| 2 | Create Gemini service | 45-60 min |
| 3 | Implement intent extraction | 1 hr |
| 4 | Implement parameter validation | 30 min |
| 5 | Implement tool scoring | 45 min |
| 6 | Implement tool selection | 30 min |
| 7 | Create fallback logic | 20 min |
| 8 | Wire to LangGraph node | 20 min |
| 9 | Write unit tests | 45 min |
| 10 | Integration test | 30 min |
| **Total** | | **~6-7 hours** |

---

## Next Steps After Phase 2.1

Once complete, proceed to **Phase 2.2: Tool Repository System** to create the actual tool implementations that this agent will select from.

---

## Questions for Review

1. Should we implement async-first or support both sync/async?
2. Do you want to add any additional intent types or tones?
3. Should the scoring weights be configurable via database/config?
4. Any specific error handling patterns you prefer?

---

**Please review this plan and let me know if you'd like any modifications before I begin implementation.**
