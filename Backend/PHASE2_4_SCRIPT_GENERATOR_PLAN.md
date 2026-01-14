# Phase 2.4: Script Generator Agent - Implementation Plan

**Version**: 1.0  
**Created**: January 14, 2026  
**Depends On**: Phase 2.3 (Deep Research Agent) ✅ Completed  
**Est. Duration**: 1.5-2 days

---

## Overview

The Script Generator Agent transforms research output (factual, creative, or hybrid) into a **viral-optimized script** suitable for 8-25 second YouTube Shorts. It generates hooks, scenes with visual directions, pattern interrupts, and call-to-action - all while respecting the selected tool's style specifications.

### Key References
- `@Guides/RABA_Architecture.md:342-418` - Script Writer Agent architecture
- `@Guides/SRS.md:102-113` - Functional requirements FR-4xx
- `@Guides/rule.md:52` - Script Generator uses Gemini 2.5 Pro
- `@Backend/Documentations/gemini_doc.md:52-69` - Gemini 3 models (we'll use `gemini-3-flash-preview`)

---

## Architecture Summary

```
                    ┌──────────────────────────────┐
                    │     INPUT FROM STATE          │
                    │ - research_data (factual/     │
                    │   creative/hybrid)            │
                    │ - selected_tool (style specs) │
                    │ - intent_metadata (tone, etc) │
                    │ - duration_seconds (8-25)     │
                    └──────────────┬───────────────┘
                                   │
                    ┌──────────────▼───────────────┐
                    │   SCRIPT GENERATOR AGENT     │
                    │   (Gemini 3 Flash Preview)   │
                    ├──────────────────────────────┤
                    │ 1. Generate Hook             │
                    │ 2. Generate Scenes           │
                    │ 3. Add Pattern Interrupts    │
                    │ 4. Add Call-to-Action        │
                    │ 5. Calculate Viral Metrics   │
                    └──────────────┬───────────────┘
                                   │
                    ┌──────────────▼───────────────┐
                    │     OUTPUT TO STATE          │
                    │ - script_output              │
                    │ - hook                       │
                    │ - scenes[]                   │
                    │ - call_to_action             │
                    │ - viral_score                │
                    └──────────────────────────────┘
```

---

## Implementation Tasks

### 2.4.1 Create Script Models (`app/models/script.py`)

**Estimated Time**: 45 minutes

**Description**: Define Pydantic models for script output, scenes, hooks, and CTAs.

**Models to Create**:

| Model | Description | Key Fields |
|-------|-------------|------------|
| `HookArchetype` | Enum for hook types | FORTUNETELLER, TEACHER, DISRUPTOR, STORYTELLER |
| `HookSection` | The viral hook (first 1-2s) | archetype, script, visual_direction, duration_seconds, psychological_lever |
| `PatternInterruptType` | Enum for interrupt types | SCENE_CHANGE, VISUAL_EFFECT, NEW_FACT, PERSPECTIVE_SHIFT, EMOTIONAL_PIVOT, SENSORY_CUE |
| `Scene` | A single scene with visual directions | scene_number, timestamp_start, timestamp_end, description, dialogue, audio_cues, camera_direction, lighting, mood, pattern_interrupt_type |
| `CTASection` | Call-to-action at the end | type (follow/like/comment/share/subscribe), placement_seconds, script |
| `ScriptOutput` | Complete script output | hook, scenes[], call_to_action, estimated_completion_rate, viral_score, total_duration_seconds |

**Reference Schema** (from `@Guides/RABA_Architecture.md:385-415`):
```python
class ScriptOutput(BaseModel):
    hook: HookSection
    scenes: List[Scene]
    call_to_action: CTASection
    estimated_completion_rate: float  # 0.0-1.0
    viral_score: float  # Composite metric
    total_duration_seconds: float
```

**Validation Rules**:
- `total_duration_seconds` must equal sum of all scene durations
- At least 1 scene required
- Hook duration must be 1-3 seconds
- Pattern interrupts should occur every 3-5 seconds

---

### 2.4.2 Implement Hook Generator (`app/agents/script_writer.py`)

**Estimated Time**: 1 hour

**Description**: Generate viral hooks optimized for the first 1-2 seconds to prevent scroll-away.

**Hook Archetypes** (from `@Guides/RABA_Architecture.md:348-365`):

| Archetype | Description | Example | Best For |
|-----------|-------------|---------|----------|
| FORTUNETELLER | Promise future outcome | "In 30 seconds, you'll understand why..." | Educational, transformation |
| TEACHER | Fast, actionable value | "You've been understanding X wrong..." | How-to, tutorial |
| DISRUPTOR | Challenge status quo | "Everything you know about X is misleading" | Contrarian, myth-busting |
| STORYTELLER | Relatable narrative | "This is what nobody expected about X" | Entertainment, emotional |

**Algorithm**:
1. Analyze `intent_metadata.intent_type` from state
2. Select appropriate archetype based on intent
3. Generate hook script using Gemini 3 Flash Preview
4. Include visual direction for the hook
5. Estimate VVSA (Views vs Swiped Away) impact score

**LLM Prompt Structure**:
- System: Role as viral short-form content writer
- Context: Research summary, intent type, target audience, tone
- Instruction: Generate hook with archetype, verbal hook, visual direction
- Output Format: Structured JSON matching `HookSection` model

---

### 2.4.3 Implement Scene Generator (`app/agents/script_writer.py`)

**Estimated Time**: 1.5 hours

**Description**: Generate scenes with rich visual directions, dialogue, and timing.

**Scene Requirements** (from `@Guides/RABA_Architecture.md:378-384`):
- **Specificity**: "Shuffling with hunched shoulders" > "walking sadly"
- **Sensory Detail**: Light, texture, atmosphere, sound
- **Emotional Triggers**: Authenticity, relatability, aspirational
- **Dialogue Precision**: Natural speech patterns, short phrasing for 8-second segments

**Scene Fields to Generate**:

| Field | Description |
|-------|-------------|
| `scene_number` | Order in sequence (1-indexed) |
| `timestamp` | "MM:SS-MM:SS" format |
| `description` | Rich sensory visual description |
| `dialogue` | Optional spoken text (if any) |
| `audio_cues` | Sound design notes |
| `camera_direction` | Camera movement/angle |
| `lighting` | Lighting description |
| `mood` | Emotional tone |
| `pattern_interrupt_type` | Type of interrupt (if this is an interrupt point) |

**Scene Count Logic**:
- 8s video: 2-3 scenes
- 18s video: 4-6 scenes  
- 25s video: 6-8 scenes
- Formula: `ceil(duration_seconds / 4)` scenes (average 4s per scene)

**Implementation Notes**:
- Must handle BOTH factual (`ResearchOutput`) and creative (`CreativeIdeationOutput`) research data
- For creative content: Use `scenes` from `CreativeIdeationOutput` as starting point
- For factual content: Generate scenes from `research_findings`
- For hybrid: Blend both approaches

---

### 2.4.4 Implement Pattern Interrupt Logic (`app/agents/script_writer.py`)

**Estimated Time**: 30 minutes

**Description**: Insert pattern interrupts every 3-5 seconds to maintain viewer attention.

**Pattern Interrupt Types** (from `@Guides/RABA_Architecture.md:1302-1343`):

| Type | Description | Usage |
|------|-------------|-------|
| `SCENE_CHANGE` | New location/subject | Between major beats |
| `VISUAL_EFFECT` | Transition, animation shift | At timestamps 3s, 6s |
| `NEW_FACT` | Information reveal | For educational content |
| `PERSPECTIVE_SHIFT` | Different angle/interpretation | Mid-video |
| `EMOTIONAL_PIVOT` | Mood change | Before climax |
| `SENSORY_CUE` | Sound/visual surprise | Unpredictable moments |

**Interrupt Placement Timeline** (from `@Guides/RABA_Architecture.md:366-375`):
```
For 18-25 second video:
├─ 0:00-0:03   [HOOK] Strongest opening
├─ 0:03-0:08   [Pattern Interrupt 1] New visual/fact
├─ 0:08-0:13   [Pattern Interrupt 2] Shift perspective
├─ 0:13-0:18   [Pattern Interrupt 3] Consequence/payoff setup
└─ 0:18-0:25   [RESOLUTION + CTA] Satisfying conclusion
```

**Algorithm**:
1. Calculate interrupt positions based on duration
2. Select interrupt types (vary to prevent habituation)
3. Assign interrupt type to scenes at those timestamps
4. Ensure no two consecutive scenes have same interrupt type

---

### 2.4.5 Add Viral Optimization (`app/agents/script_writer.py`)

**Estimated Time**: 45 minutes

**Description**: Calculate engagement metrics and viral score for the script.

**Viral Score Components** (from `@Guides/RABA_Architecture.md:1345-1383`):

| Component | Weight | Description |
|-----------|--------|-------------|
| `hook_strength` | 0.25 | Hook archetype + clarity |
| `pattern_interrupt_density` | 0.20 | Interrupts per 5 seconds |
| `emotional_arc` | 0.20 | Proper story structure |
| `call_to_action_clarity` | 0.15 | Clear, natural CTA |
| `audience_fit` | 0.10 | Match to target audience |
| `novelty_factor` | 0.10 | Uniqueness of angle |

**Completion Rate Prediction**:
- Hook <3 seconds: +0.2
- Question format hook: +0.1
- Pattern interrupt every 3-5s: +0.15
- Strong emotional arc: +0.15
- Clear CTA: +0.1
- Base: 0.4

**Implementation**:
1. Create `CompletionRatePredictor` class
2. Evaluate each component
3. Calculate weighted viral score
4. Return `estimated_completion_rate` (capped at 0.98)

---

### 2.4.6 Integrate Tool Specs (`app/agents/script_writer.py`)

**Estimated Time**: 30 minutes

**Description**: Use the selected tool's script format requirements to tailor output.

**Tool Integration Points**:
- Each tool (from `selected_tool` in state) has `get_optimal_script_format()`
- Script style should match tool's aesthetic (e.g., "Impossible Simulations" = liquid-glass visuals)
- Visual directions should use tool-specific vocabulary

**Tool-Specific Adaptations**:

| Tool Category | Script Style | Visual Vocabulary |
|---------------|--------------|-------------------|
| `surreal_realism` | Scientific wonder, impossible physics | "flowing liquid-glass", "photorealistic grounding" |
| `high_octane_anime` | Dynamic action, philosophical debates | "Sakuga-style", "ink-splashes", "elemental explosions" |
| `stylized_3d` | Clean 3D aesthetic, diorama-like | "miniature landscape", "data visualization" |

**Implementation**:
1. Retrieve tool specs from `state["selected_tool"]`
2. Pass tool's visual vocabulary to LLM prompt
3. Ensure scene descriptions use tool-specific terminology
4. Apply tool's script format requirements

---

### 2.4.7 Implement Persistence (`app/agents/script_writer.py`)

**Estimated Time**: 20 minutes

**Description**: Save script output to Supabase `workflows.script_output` column.

**Persistence Flow**:
1. Generate complete `ScriptOutput`
2. Convert to dict via `model_dump()`
3. Update workflow record in Supabase
4. Log persistence status

**Supabase Update**:
```python
await supabase.table("workflows").update({
    "script_output": script_output.model_dump(),
    "updated_at": utc_now_iso()
}).eq("id", workflow_id).execute()
```

**Error Handling**:
- If persistence fails, log error but don't fail the workflow
- Include script in state update regardless of persistence success

---

### 2.4.8 Wire to LangGraph Node (`app/graph/nodes.py`)

**Estimated Time**: 20 minutes

**Description**: Connect the Script Generator agent to the LangGraph workflow.

**Node Function** (`script_writer_node`):

**Input from State**:
- `topic` - Original topic
- `research_data` - From Deep Research (factual/creative/hybrid)
- `selected_tool` - Tool metadata with style specs
- `intent_metadata` - Intent type, tone, target audience
- `duration_seconds` - Video duration

**Output to State**:
- `script_output` - Complete script as dict
- `hook` - Hook section extracted
- `scenes` - List of scenes extracted  
- `call_to_action` - CTA section extracted
- `viral_score` - Calculated viral score
- `phase_timestamps.script_writer_completed` - Completion timestamp

**Implementation**:
1. Import `ScriptWriterAgent` from `app.agents.script_writer`
2. Instantiate agent
3. Call `agent.run(state)` with required state fields
4. Extract fields for state update
5. Handle errors gracefully

---

### 2.4.9 Write Unit Tests (`tests/test_agents/test_script.py`)

**Estimated Time**: 45 minutes

**Description**: Test script generation, structure validation, and viral metrics.

**Test Cases**:

| Test | Description |
|------|-------------|
| `test_hook_generation_educational` | Hook for educational intent uses TEACHER/FORTUNETELLER |
| `test_hook_generation_entertainment` | Hook for entertainment uses STORYTELLER/DISRUPTOR |
| `test_scene_count_8s` | 8s video generates 2-3 scenes |
| `test_scene_count_18s` | 18s video generates 4-6 scenes |
| `test_scene_count_25s` | 25s video generates 6-8 scenes |
| `test_pattern_interrupt_placement` | Interrupts placed every 3-5s |
| `test_pattern_interrupt_variety` | No two consecutive same interrupt types |
| `test_viral_score_calculation` | Score is 0.0-1.0, components weighted correctly |
| `test_completion_rate_prediction` | Rate is 0.4-0.98 range |
| `test_tool_specs_integration` | Script uses tool's visual vocabulary |
| `test_factual_research_script` | Handles `ResearchOutput` correctly |
| `test_creative_research_script` | Handles `CreativeIdeationOutput` correctly |
| `test_hybrid_research_script` | Handles `HybridResearchOutput` correctly |
| `test_duration_validation` | Total scene duration equals requested duration |
| `test_script_output_schema` | Output matches `ScriptOutput` model |

**Mock Requirements**:
- Mock Gemini API calls
- Mock Supabase persistence
- Use fixture data for research outputs

---

### 2.4.10 Integration Test

**Estimated Time**: 30 minutes

**Description**: Test full script generation flow from research to script output.

**Integration Test Flow**:
1. Create mock state with completed research data
2. Run `script_writer_node(state)`
3. Verify state update contains all required fields
4. Verify script structure is valid
5. Verify viral metrics are calculated
6. Test with factual, creative, and hybrid research data

**Test Scenarios**:
- Educational factual content (physics topic)
- Entertainment fictional content (story concept)
- Hybrid content (historical "what-if")
- Different durations: 8s, 18s, 25s
- Different tools: surreal_realism, high_octane_anime

---

## Detailed Implementation Notes

### Gemini 3 Flash Preview Configuration

**Reference**: `@Backend/Documentations/gemini_doc.md:52-69`

```python
from google import genai
from google.genai import types

client = genai.Client()

response = client.models.generate_content(
    model="gemini-3-flash-preview",  # Fast, Pro-level intelligence
    contents=prompt,
    config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_level="medium"),  # Balanced for script generation
        response_mime_type="application/json",
        response_json_schema=ScriptOutput.model_json_schema(),
    ),
)
```

**Model Selection Rationale**:
- `gemini-3-flash-preview` offers Pro-level intelligence at Flash speed/pricing
- `thinking_level="medium"` balances creativity with speed
- Structured output ensures valid JSON matching our models

### Handling Different Research Types

The Deep Research Agent outputs three possible types:

| Research Type | How to Handle in Script Generator |
|--------------|-----------------------------------|
| `ResearchOutput` (factual) | Use `research_findings` to create informative scenes, cite sources naturally |
| `CreativeIdeationOutput` (creative) | Use existing `scenes` and `narrative_arc` as foundation, enhance with visual directions |
| `HybridResearchOutput` (hybrid) | Blend factual `research_findings` with creative `scenes`, mark transition points |

**Detection Logic**:
```python
research_data = state.get("research_data", {})
strategy = research_data.get("strategy_used", "factual")

if strategy == "factual":
    # Use research_findings for content
    pass
elif strategy == "creative":
    # Use scenes and narrative_arc from creative output
    pass
elif strategy == "hybrid":
    # Blend factual_base with creative_extension
    pass
```

### HITL Integration (Manual Mode)

**Reference**: `@Guides/SRS.md:105-107`

After script generation, if `hitl_mode == "manual"`:
1. Workflow pauses at Gate 3
2. User can:
   - **Edit script text directly** (FR-406)
   - **Provide feedback for regeneration** (FR-407)
3. Max 3 regeneration attempts per gate

The Script Generator should:
- Check for HITL feedback in state
- If regenerating: Use feedback to adjust generation
- Track regeneration count in `state["regeneration_counts"]["script"]`

---

## File Structure After Implementation

```
Backend/app/
├── agents/
│   ├── __init__.py  # Add ScriptWriterAgent export
│   ├── intent_tool_selector.py ✅
│   ├── deep_research.py ✅
│   └── script_writer.py  # NEW
├── models/
│   ├── __init__.py  # Add script model exports
│   ├── research.py ✅
│   ├── tool.py ✅
│   └── script.py  # NEW
├── graph/
│   ├── nodes.py  # Update script_writer_node
│   └── ...
└── ...

tests/
├── test_agents/
│   ├── test_intent.py ✅
│   ├── test_research.py ✅
│   └── test_script.py  # NEW
└── ...
```

---

## Dependencies

### Python Packages (Already in requirements.txt)
- `google-genai` - Gemini API client
- `pydantic>=2.5.0` - Model validation
- `supabase>=2.0.0` - Database persistence

### API Requirements
- **Gemini API Key** (`GOOGLE_API_KEY`) - For Gemini 3 Flash Preview

### Service Dependencies
- Gemini Service (`app/services/gemini.py`) ✅ - Already implemented
- Supabase Service (`app/services/supabase.py`) ✅ - Already implemented

---

## Acceptance Criteria

| Criteria | Verification |
|----------|--------------|
| Hook generated with appropriate archetype | Unit test |
| Scenes match requested duration | Unit test (sum of scene durations) |
| Pattern interrupts placed every 3-5s | Unit test |
| Viral score calculated (0.0-1.0) | Unit test |
| Tool specs integrated into visual directions | Manual review + unit test |
| Script persisted to Supabase | Integration test |
| Handles all research types (factual/creative/hybrid) | Unit tests per type |
| LangGraph node wired correctly | Integration test |
| HITL feedback respected on regeneration | Integration test |

---

## Estimated Timeline

| Task | Est. Time | Cumulative |
|------|-----------|------------|
| 2.4.1 Create script models | 45 min | 45 min |
| 2.4.2 Implement hook generator | 1 hr | 1h 45m |
| 2.4.3 Implement scene generator | 1.5 hr | 3h 15m |
| 2.4.4 Implement pattern interrupt logic | 30 min | 3h 45m |
| 2.4.5 Add viral optimization | 45 min | 4h 30m |
| 2.4.6 Integrate tool specs | 30 min | 5h |
| 2.4.7 Implement persistence | 20 min | 5h 20m |
| 2.4.8 Wire to LangGraph node | 20 min | 5h 40m |
| 2.4.9 Write unit tests | 45 min | 6h 25m |
| 2.4.10 Integration test | 30 min | **6h 55m** |

**Total Estimated Time**: ~7 hours (1-1.5 days)

---

## Next Steps After Completion

After Phase 2.4 is complete, proceed to **Phase 3.1: Image Generator Agent** which depends on:
- `script_output.scenes[]` - For image prompts
- `selected_tool` - For style specs
- `research_images[]` - To reduce generated count

---

## Appendix: LLM Prompt Templates

### Hook Generation Prompt

```
You are a viral short-form video content writer specializing in YouTube Shorts.

CONTEXT:
- Topic: {topic}
- Intent Type: {intent_type}
- Target Audience: {target_audience}
- Tone: {tone}
- Research Summary: {research_summary}

TASK:
Generate a viral hook for the first 1-2 seconds of the video.

HOOK ARCHETYPE OPTIONS:
- FORTUNETELLER: Promise future outcome (transformation hook)
- TEACHER: Fast, actionable value (solution hook)
- DISRUPTOR: Challenge status quo (contrarian hook)
- STORYTELLER: Relatable narrative (emotional hook)

Select the most appropriate archetype for this content and generate:
1. Verbal hook (spoken text, max 10 words)
2. Visual direction (what viewer sees)
3. Psychological lever (curiosity_gap/fomo/relatability/dopamine)

OUTPUT FORMAT: JSON matching HookSection schema
```

### Scene Generation Prompt

```
You are a viral short-form video scriptwriter.

CONTEXT:
- Topic: {topic}
- Duration: {duration_seconds} seconds
- Tool Style: {tool_category} ({tool_description})
- Research Data: {research_summary}
- Hook: {hook_script}

TASK:
Generate {scene_count} scenes for this video.

REQUIREMENTS:
- Total scene durations must equal {duration_seconds} seconds
- Include pattern interrupts every 3-5 seconds
- Use sensory-rich descriptions (light, texture, atmosphere, sound)
- Dialogue should be natural, short phrases
- Visual directions should match the {tool_category} aesthetic

TOOL-SPECIFIC VOCABULARY:
{tool_visual_vocabulary}

OUTPUT FORMAT: JSON array of Scene objects
```

---

## Checklist for Implementation

- [ ] 2.4.1 Create `app/models/script.py` with all models
- [ ] 2.4.2 Implement `generate_hook()` in `app/agents/script_writer.py`
- [ ] 2.4.3 Implement `generate_scenes()` in `app/agents/script_writer.py`
- [ ] 2.4.4 Implement `add_pattern_interrupts()` in `app/agents/script_writer.py`
- [ ] 2.4.5 Implement `calculate_viral_score()` in `app/agents/script_writer.py`
- [ ] 2.4.6 Implement `apply_tool_specs()` in `app/agents/script_writer.py`
- [ ] 2.4.7 Implement `persist_script()` in `app/agents/script_writer.py`
- [ ] 2.4.8 Update `script_writer_node()` in `app/graph/nodes.py`
- [ ] 2.4.9 Create `tests/test_agents/test_script.py`
- [ ] 2.4.10 Run integration tests
- [ ] Update `app/agents/__init__.py` with new exports
- [ ] Update `app/models/__init__.py` with new exports
