# Phase 2.3: Deep Research Agent Implementation Plan

**Version**: 1.0  
**Created**: January 14, 2026  
**Based on**: 
- [Guides/SRS.md](../Guides/SRS.md) - FR-301 to FR-309
- [Guides/RABA_Architecture.md](../Guides/RABA_Architecture.md) - Section 2.4
- [Guides/rule.md](../Guides/rule.md) - Agent definitions
- [Backend/Documentations/deep_research_Doc.md](./Documentations/deep_research_Doc.md) - Gemini Deep Research API

---

## Overview

Phase 2.3 implements the **Deep Research Agent** - the second agent in the RABA pipeline responsible for gathering factual research and reference images for video generation.

```
┌──────────────────────┐     ┌──────────────────────┐     ┌──────────────────────┐
│  Intent/Tool         │────▶│   DEEP RESEARCH      │────▶│   Script Generator   │
│  Selector (2.1)      │     │   AGENT (2.3)        │     │   (2.4)              │
│  ✅ COMPLETED        │     │   🎯 THIS PHASE      │     │   NEXT PHASE         │
└──────────────────────┘     └──────────────────────┘     └──────────────────────┘
```

### Key Responsibilities (from SRS.md FR-3xx)
| Requirement | Description |
|-------------|-------------|
| **FR-301** | Use Gemini Deep Research with Google Search grounding |
| **FR-302** | Gather factual data with source citations |
| **FR-303** | Search for relevant reference images using Google Custom Search API |
| **FR-304** | Download and store research images in Supabase Storage |
| **FR-305** | Persist research output to `workflows.research_output` |
| **FR-306** | Persist research image URLs to `workflows.research_images` |
| **FR-307** | Cache research results in Redis with configurable TTL (7 days) |
| **FR-308** | In manual HITL mode, pause at Gate 2 for user review |
| **FR-309** | At Gate 2, user can edit facts or provide feedback |

---

## Content Type Routing: Factual vs Creative/Fictional

**Critical Design Decision**: Not all topics require factual grounding. The agent must intelligently route based on content type.

### Content Type Classification

The Intent/Tool Selector (Phase 2.1) provides `intent_type` which we use for routing:

| Intent Type | Content Nature | Research Strategy |
|-------------|----------------|-------------------|
| `educational` | Factual | Deep Research with Google Search grounding |
| `tutorial` | Factual | Deep Research with Google Search grounding |
| `inspirational` | Mixed | Light grounding + creative enhancement |
| `entertainment` | Creative | Creative ideation (NO fact-checking) |

### Additional Signals for Routing

Beyond `intent_type`, detect creative content via topic analysis:

```
CREATIVE INDICATORS (skip fact-grounding):
├── "What if..." scenarios
├── Fictional characters/worlds
├── "Imagine..." prompts
├── Storytelling keywords (dragon, wizard, superhero, etc.)
├── Hypothetical situations
├── Sci-fi/fantasy concepts
├── Emotional narratives without factual claims

FACTUAL INDICATORS (use Deep Research):
├── Historical events/figures
├── Scientific concepts
├── "How does X work?"
├── Statistics/data claims
├── Real-world phenomena
├── Educational explainers
```

### Research Strategy by Content Type

#### Strategy A: Factual Research (Deep Research Agent)
```
Input: "How black holes work"
Process:
├── Use Gemini Deep Research Agent
├── Google Search grounding enabled
├── Gather citations and sources
├── Verify factual accuracy
Output:
├── Grounded facts with citations
├── Reference images from real sources
```

#### Strategy B: Creative Ideation (Gemini Pro WITHOUT grounding)
```
Input: "A dragon who learns to code"
Process:
├── Use Gemini 3 Pro (standard, no grounding)
├── Generate story elements, characters, plot
├── Create visual descriptions for scenes
├── Build emotional narrative arc
Output:
├── Story outline with scenes
├── Character descriptions
├── Visual mood/style guidance
├── NO citations (not applicable)
```

#### Strategy C: Hybrid (Mixed Content)
```
Input: "What if dinosaurs had survived?"
Process:
├── Use Deep Research for factual base (dinosaur facts)
├── Use Gemini Pro for creative extrapolation
├── Blend grounded science with speculation
Output:
├── Factual foundation (cited)
├── Creative extensions (uncited, marked as speculative)
```

### Implementation: Content Type Router

**New method in `deep_research.py`**:
```
determine_research_strategy(state: VideoGenerationState) -> ResearchStrategy

Input:
├── intent_type: str (from Intent/Tool Selector)
├── topic: str
├── tone: str

Process:
1. Check intent_type:
   - educational/tutorial → FACTUAL
   - entertainment → CREATIVE
   - inspirational → HYBRID
2. Analyze topic for creative indicators
3. Return strategy enum

Output:
├── ResearchStrategy.FACTUAL
├── ResearchStrategy.CREATIVE
├── ResearchStrategy.HYBRID
```

### Creative Research Output Schema

For creative/fictional content, output structure differs:

```
CreativeIdeationOutput
├── story_concept: str
├── characters: list[CharacterDescription]
│   ├── name: str
│   ├── appearance: str
│   ├── personality: str
│   └── role: str
├── scenes: list[SceneIdea]
│   ├── description: str
│   ├── mood: str
│   ├── visual_style: str
│   └── key_elements: list[str]
├── narrative_arc: NarrativeArc
│   ├── hook: str
│   ├── conflict: str
│   ├── resolution: str
│   └── emotional_beat: str
├── visual_inspiration: list[str]  # Style references, not factual images
├── is_fictional: bool = True
├── citations: list = []  # Empty for creative content
```

### Image Search Adaptation

| Content Type | Image Search Strategy |
|--------------|----------------------|
| **Factual** | Search for real reference images (Google Custom Search) |
| **Creative** | Search for style/mood inspiration OR skip entirely |
| **Hybrid** | Search for factual base + style inspiration |

For creative content, image prompts are generated for the Image Generator (Phase 3.1) rather than searching for existing images.

### Example Flows

**Example 1: Factual Topic**
```
Topic: "The history of the Roman Empire"
Intent: educational
Strategy: FACTUAL

→ Deep Research Agent (grounded)
→ Google Image Search for historical images
→ Output: Facts with citations, reference images
```

**Example 2: Creative Topic**
```
Topic: "A lonely robot finding friendship in space"
Intent: entertainment
Strategy: CREATIVE

→ Gemini 3 Pro (ungrounded)
→ Generate story elements, character designs
→ Skip factual image search
→ Output: Story outline, character descriptions, visual style guide
```

**Example 3: Hybrid Topic**
```
Topic: "What if Einstein met Tesla?"
Intent: inspirational
Strategy: HYBRID

→ Deep Research: Facts about Einstein and Tesla
→ Creative Generation: Imagined conversation/interaction
→ Image Search: Historical photos of both figures
→ Output: Factual base + creative narrative
```

---

## Architecture Decision: Gemini Deep Research Agent

Per `deep_research_Doc.md`, we will use the **Gemini Deep Research Agent** via the **Interactions API** instead of basic grounded search.

### Why Deep Research Agent?
| Feature | Basic Grounded Search | Deep Research Agent |
|---------|----------------------|---------------------|
| **Process** | Single query → response | Plan → Search → Read → Iterate → Synthesize |
| **Output** | Short grounded text | Detailed reports with structured citations |
| **Depth** | Surface-level facts | Multi-step iterative research |
| **Best For** | Quick fact-checking | Comprehensive topic research |

### Agent Configuration
```python
# Agent name from documentation
DEEP_RESEARCH_AGENT = "deep-research-pro-preview-12-2025"

# Key parameters
background = True  # Required for long-running tasks
stream = True      # Optional: real-time progress updates
agent_config = {
    "type": "deep-research",
    "thinking_summaries": "auto"  # Enable progress tracking
}
```

---

## Implementation Steps

### Step 1: Create Research Models (`app/models/research.py`)

**Purpose**: Define Pydantic models for research data structures.

**Models to Create**:
```
ResearchFinding
├── topic_segment: str
├── key_facts: list[str]
├── citations: list[Citation]
└── confidence: float (0.7-1.0)

Citation
├── source: str
├── url: str
└── quote: Optional[str]

ResearchImage
├── url: str
├── storage_path: str
├── title: str
├── source_url: str

ResearchOutput
├── research_findings: list[ResearchFinding]
├── research_images: list[ResearchImage]
├── research_depth_used: str ("quick"|"standard"|"deep")
├── total_sources: int
├── cache_hit: bool
├── generated_at: datetime
├── interaction_id: Optional[str]  # For follow-up queries
├── strategy_used: ResearchStrategy  # NEW: tracks which strategy was used
├── is_fictional: bool              # NEW: flag for creative content
```

**Creative Content Models** (for fictional/entertainment topics):
```
ResearchStrategy (Enum)
├── FACTUAL   # Deep Research with grounding
├── CREATIVE  # Gemini Pro without grounding
├── HYBRID    # Both factual base + creative extension

CharacterDescription
├── name: str
├── appearance: str
├── personality: str
├── role: str
├── visual_keywords: list[str]  # For image generation

SceneIdea
├── scene_number: int
├── description: str
├── mood: str
├── visual_style: str
├── key_elements: list[str]
├── suggested_camera: str

NarrativeArc
├── hook: str           # Opening hook (first 1-2s)
├── setup: str          # Establish situation
├── conflict: str       # Central tension
├── climax: str         # Peak moment
├── resolution: str     # Satisfying ending
├── emotional_beats: list[str]

CreativeIdeationOutput
├── story_concept: str
├── characters: list[CharacterDescription]
├── scenes: list[SceneIdea]
├── narrative_arc: NarrativeArc
├── visual_inspiration: list[str]
├── tone: str
├── is_fictional: bool = True
├── citations: list = []  # Always empty for creative
```

**Reference**: `RABA_Architecture.md` Section 2.4 Output Schema

---

### Step 2: Implement Deep Research Service (`app/services/deep_research.py`)

**Purpose**: Wrapper for Gemini Deep Research Agent via Interactions API.

**Key Methods**:

#### 2.1 `start_research()` - Initiate Research Task
```
Input:
├── topic: str
├── context: Optional[str]  # Tool context for focused research
├── research_depth: str     # "quick", "standard", "deep"

Process:
├── Build research prompt with formatting instructions
├── Call client.interactions.create() with background=True
├── Return interaction_id for polling

Output:
├── interaction_id: str
├── status: "started"
```

**Prompt Template** (per deep_research_Doc.md steerability):
```
Research the topic: "{topic}"

Context for video generation:
- Visual style: {tool_category}
- Duration: {duration_seconds} seconds
- Target audience: {target_audience}

Format the output as a structured report with:
1. Executive Summary (2-3 key insights)
2. Key Facts (bullet points with source citations)
3. Visual Elements (describe scenes/imagery that would work well)
4. Interesting Angles (unique perspectives for viral content)

Requirements:
- All facts must have source citations
- Focus on visually demonstrable information
- Include surprising or counterintuitive facts (viral potential)
- If specific data is unavailable, explicitly state this
```

#### 2.2 `poll_research()` - Check Research Status
```
Input:
├── interaction_id: str

Process:
├── Call client.interactions.get(interaction_id)
├── Check status: "in_progress", "completed", "failed"

Output:
├── status: str
├── progress: Optional[str]  # thought_summary if streaming
├── result: Optional[str]    # Final report if completed
```

#### 2.3 `wait_for_completion()` - Poll Until Done
```
Input:
├── interaction_id: str
├── timeout_seconds: int (default: 300)
├── poll_interval: int (default: 10)

Process:
├── Loop polling every poll_interval seconds
├── Handle "in_progress" → continue polling
├── Handle "completed" → return result
├── Handle "failed" → raise error
├── Handle timeout → raise TimeoutError

Output:
├── ResearchOutput (parsed from final text)
```

#### 2.4 `parse_research_output()` - Structure the Report
```
Input:
├── raw_text: str (from interaction output)

Process:
├── Use Gemini 3 Flash for structured extraction
├── Parse into ResearchOutput model
├── Extract citations into structured format

Output:
├── ResearchOutput
```

**Reference**: `deep_research_Doc.md` - Background execution and polling pattern

---

### Step 3: Implement Creative Ideation Service (`app/services/creative_ideation.py`)

**Purpose**: Generate story elements, characters, and scenes for fictional/entertainment content WITHOUT fact-grounding.

**Key Methods**:

#### 3.1 `determine_strategy()` - Route to Correct Strategy
```
Input:
├── intent_type: str (from Intent/Tool Selector)
├── topic: str
├── tone: str

Process:
1. Primary check: intent_type
   - educational/tutorial → FACTUAL
   - entertainment → CREATIVE
   - inspirational → HYBRID
2. Secondary check: topic keywords
   - Detect fictional indicators (dragon, wizard, "what if", etc.)
   - Override to CREATIVE if strong signals
3. Return strategy

Output:
├── ResearchStrategy enum
```

#### 3.2 `generate_creative_ideation()` - Story Generation
```
Input:
├── topic: str
├── tool_specs: ToolMetadata (for visual style guidance)
├── duration_seconds: int
├── tone: str

Process:
├── Build creative prompt (NO grounding tools)
├── Call Gemini 3 Pro for story generation
├── Parse into CreativeIdeationOutput

Output:
├── CreativeIdeationOutput
```

**Creative Prompt Template**:
```
You are a master storyteller creating a short video narrative.

Topic: "{topic}"
Visual Style: {tool_category} (e.g., surreal_realism, anime, 3D)
Duration: {duration_seconds} seconds
Tone: {tone}

Create a compelling short-form video story with:

1. STORY CONCEPT (1-2 sentences)
   - Core premise that hooks viewers instantly

2. CHARACTERS (if applicable)
   - Name, appearance, personality, role
   - Visual keywords for image generation

3. SCENE BREAKDOWN (for {duration_seconds}s video)
   - Scene 1 (0-3s): Hook/Opening
   - Scene 2 (3-8s): Setup/Context  
   - Scene 3 (8-15s): Development/Conflict
   - Scene 4 (15-{duration}s): Climax/Resolution
   
   For each scene include:
   - Visual description (what we SEE)
   - Mood and atmosphere
   - Camera suggestion
   - Key visual elements

4. NARRATIVE ARC
   - Hook: First 1-2 seconds grab attention
   - Conflict: Central tension or question
   - Resolution: Satisfying payoff
   - Emotional journey: What should viewers FEEL?

5. VISUAL INSPIRATION
   - Art style references
   - Color palette suggestions
   - Mood board keywords

Remember: This is FICTION. Be creative, imaginative, and visually stunning.
Do NOT include real-world citations or fact-check - embrace creativity.
```

#### 3.3 `generate_hybrid_content()` - Mixed Factual + Creative
```
Input:
├── topic: str
├── factual_research: ResearchOutput (from Deep Research)
├── creative_angle: str

Process:
├── Take factual base from Deep Research
├── Extend with creative speculation
├── Mark creative parts as "speculative"

Output:
├── HybridResearchOutput (extends ResearchOutput)
    ├── factual_base: ResearchOutput
    ├── creative_extension: CreativeIdeationOutput
    ├── blend_points: list[str]  # Where fact meets fiction
```

**Example: Hybrid Flow**
```
Topic: "What if the Roman Empire had smartphones?"

Step 1 - Factual Research:
├── Research Roman Empire facts
├── Communication methods, social structure, etc.

Step 2 - Creative Extension:
├── Imagine smartphone integration
├── Create characters (Roman citizen, emperor)
├── Build narrative around the concept

Output:
├── Grounded facts about Rome (cited)
├── Creative speculation (uncited, marked as fictional)
```

---

### Step 4: Implement Google Custom Search Service (`app/services/google_search.py`)

**Purpose**: Search and download reference images for video generation.

**Dependencies**:
```
google-api-python-client>=2.100.0
```

**Environment Variables** (from SRS.md 9.2):
```
GOOGLE_CUSTOM_SEARCH_API_KEY=
GOOGLE_CUSTOM_SEARCH_CX=
```

**Key Methods**:

#### 3.1 `search_images()` - Find Reference Images
```
Input:
├── query: str
├── num_images: int (default: 5, max: 10)

Process:
├── Build Custom Search Engine client
├── Call cse().list() with searchType="image"
├── Filter for large, safe images
├── Return image metadata

Output:
├── list[dict] with url, title, source
```

**Reference**: `RABA_Architecture.md` Section 2.4 ResearchImageSearcher class

#### 3.2 `download_image()` - Download Single Image
```
Input:
├── image_url: str
├── workflow_id: str

Process:
├── HTTP GET with timeout
├── Validate image format (jpg, png, webp)
├── Validate size (< 10MB)
├── Return image bytes

Output:
├── bytes (image data)
```

#### 3.3 `store_image()` - Upload to Supabase Storage
```
Input:
├── image_bytes: bytes
├── workflow_id: str
├── filename: str

Process:
├── Generate storage path: research_images/{workflow_id}/{filename}
├── Upload to Supabase Storage
├── Return public URL

Output:
├── storage_url: str
```

---

### Step 5: Implement Deep Research Agent (`app/agents/deep_research.py`)

**Purpose**: Main agent orchestrating research workflow with **content type routing**.

**Key Methods**:

#### 5.1 `research()` - Main Entry Point (with Strategy Routing)
```
Input:
├── state: VideoGenerationState
    ├── topic: str
    ├── intent_type: str          # FROM Phase 2.1
    ├── tone: str                 # FROM Phase 2.1
    ├── selected_tool: ToolMetadata
    ├── validated_params: dict
    ├── user_reference_image: Optional[str]

Process:
1. DETERMINE STRATEGY (NEW)
   ├── Call determine_strategy(intent_type, topic, tone)
   ├── Returns: FACTUAL | CREATIVE | HYBRID

2. CHECK CACHE (Redis)
   ├── Key: research:{hash(topic + tool_category + strategy)}

3. EXECUTE BASED ON STRATEGY:
   
   IF FACTUAL:
   ├── Start Gemini Deep Research (grounded)
   ├── Search for reference images (parallel)
   ├── Wait for completion
   ├── Parse into ResearchOutput
   
   IF CREATIVE:
   ├── Call generate_creative_ideation() (NO grounding)
   ├── Skip factual image search
   ├── Generate visual style keywords instead
   ├── Parse into CreativeIdeationOutput
   
   IF HYBRID:
   ├── Start Deep Research for factual base
   ├── Call generate_creative_ideation() for extension
   ├── Merge into HybridResearchOutput
   ├── Search images for factual elements only

4. CACHE results in Redis
5. PERSIST to Supabase workflows table
6. RETURN updated state

Output:
├── state: VideoGenerationState (with research_data populated)
├── state.research_data.strategy_used: ResearchStrategy
├── state.research_data.is_fictional: bool
```

#### 5.2 Cache Key Strategy
```
Key format: research:{hash(topic + tool_category + strategy)}
TTL: 7 days (604800 seconds)

Hash includes:
├── topic (normalized, lowercase, trimmed)
├── tool_category (for style-specific research)
├── strategy (FACTUAL, CREATIVE, HYBRID) # NEW
```

**Reference**: `RABA_Architecture.md` Section 2.4, `SRS.md` FR-307

#### 5.3 Parallel Execution Strategy (Factual Mode)
```
┌─────────────────────────────────────────────────────────┐
│                   research() entry                       │
└─────────────────────┬───────────────────────────────────┘
                      │
        ┌─────────────┴─────────────┐
        │                           │
        ▼                           ▼
┌───────────────┐          ┌───────────────┐
│ Deep Research │          │ Image Search  │
│ (3-5 min)     │          │ (10-30 sec)   │
└───────┬───────┘          └───────┬───────┘
        │                          │
        └──────────┬───────────────┘
                   │
                   ▼
        ┌───────────────────┐
        │ Combine Results   │
        │ Cache & Persist   │
        └───────────────────┘
```

---

### Step 6: Wire to LangGraph Node (`app/graph/nodes.py`)

**Purpose**: Connect agent to workflow graph.

**Node Function**:
```python
async def deep_research_node(state: VideoGenerationState) -> VideoGenerationState:
    """
    LangGraph node for Deep Research Agent.
    
    Ref: RABA_Architecture.md Section 5.1 (Supervisor Agent Pattern)
    """
    # Implementation calls deep_research.research(state)
```

**State Updates**:
```
Input state fields used:
├── topic
├── selected_tool
├── validated_params
├── user_reference_image

Output state fields updated:
├── research_data: ResearchOutput
├── research_images: list[str]  # Storage URLs
├── cached_research: bool
├── phase_timestamps.deep_research
```

---

### Step 7: Add Redis Caching (`app/services/redis.py`)

**Purpose**: Cache research results to avoid redundant API calls.

**Methods to Add**:

#### 7.1 `get_research_cache()` - Retrieve Cached Research
```
Input:
├── topic: str
├── tool_category: str

Process:
├── Generate cache key
├── GET from Redis
├── Deserialize if found

Output:
├── Optional[ResearchOutput]
```

#### 7.2 `set_research_cache()` - Store Research
```
Input:
├── topic: str
├── tool_category: str
├── research: ResearchOutput
├── ttl_days: int (default: 7)

Process:
├── Generate cache key
├── Serialize research
├── SET with TTL
```

**Reference**: `SRS.md` FR-307, `RABA_Architecture.md` Section 9

---

### Step 8: Update Supabase Persistence

**Purpose**: Persist research output to database.

**Table**: `workflows`

**Fields to Update**:
```
research_output: jsonb
├── research_findings[]
├── research_depth_used
├── total_sources
├── generated_at

research_images: text[]
├── Array of Supabase Storage URLs

status: text
├── Update to "research_complete" or "awaiting_research_approval"
```

---

### Step 9: Implement HITL Gate 2 (Manual Mode)

**Purpose**: Pause for user review in manual mode.

**Per `SRS.md` FR-308, FR-309**:
- System pauses at Gate 2 for user review
- User can edit facts or provide feedback for regeneration

**Implementation**:
```
If hitl_mode == "manual":
├── Update status to "awaiting_research_approval"
├── Update current_hitl_gate to "research"
├── Persist current state
├── Return (workflow pauses)

On user feedback:
├── APPROVE → Continue to script generation
├── EDIT → Apply edits, continue
├── REGENERATE → Re-run with feedback (max 3 times)
```

**Reference**: `RABA_Architecture.md` Section 5.2 HITL Gate Flow

---

### Step 10: Write Unit Tests (`tests/test_agents/test_deep_research.py`)

**Test Cases**:

| Test | Description |
|------|-------------|
| `test_research_cache_hit` | Verify cached research is returned |
| `test_research_cache_miss` | Verify new research is performed |
| `test_image_search` | Verify image search returns results |
| `test_image_download` | Verify images are downloaded and stored |
| `test_research_parsing` | Verify raw output is parsed correctly |
| `test_research_timeout` | Verify timeout handling |
| `test_hitl_gate_pause` | Verify manual mode pauses correctly |
| `test_regeneration_limit` | Verify max 3 regenerations enforced |
| **Content Type Routing Tests** | |
| `test_strategy_factual_educational` | Educational intent → FACTUAL strategy |
| `test_strategy_creative_entertainment` | Entertainment intent → CREATIVE strategy |
| `test_strategy_hybrid_inspirational` | Inspirational intent → HYBRID strategy |
| `test_creative_ideation_output` | Verify CreativeIdeationOutput structure |
| `test_fictional_no_citations` | Creative content has empty citations |
| `test_hybrid_blends_content` | Hybrid merges factual + creative correctly |
| `test_creative_skips_image_search` | Creative mode skips Google image search |

---

### Step 11: Integration Test

**End-to-End Flow**:
```
1. Start workflow with topic
2. Intent/Tool Selector completes (Phase 2.1)
3. Deep Research Agent:
   a. Checks cache (miss expected)
   b. Starts Gemini Deep Research
   c. Searches for images (parallel)
   d. Polls until completion
   e. Parses and structures output
   f. Downloads and stores images
   g. Caches results
   h. Persists to database
4. Verify:
   - workflows.research_output populated
   - workflows.research_images populated
   - Redis cache set
   - Storage contains images
```

---

## File Creation Summary

| File | Purpose | Est. Time |
|------|---------|-----------|
| `app/models/research.py` | Pydantic models (factual + creative) | 45 min |
| `app/services/deep_research.py` | Gemini Deep Research Agent wrapper | 1.5 hr |
| `app/services/creative_ideation.py` | **NEW**: Creative/fictional content generation | 1 hr |
| `app/services/google_search.py` | Google Custom Search for images | 45 min |
| `app/agents/deep_research.py` | Main agent with strategy routing | 2 hr |
| `app/graph/nodes.py` (update) | Add deep_research_node | 30 min |
| `app/services/redis.py` (update) | Add research caching methods | 30 min |
| `tests/test_agents/test_deep_research.py` | Unit tests (factual + creative) | 1 hr |

**Total Estimated Time**: ~8 hours

---

## Dependencies

### Python Packages (add to requirements.txt)
```
google-api-python-client>=2.100.0  # For Custom Search API
```

### Environment Variables (verify in .env)
```
# Already required:
GOOGLE_API_KEY=  # For Gemini API

# New for this phase:
GOOGLE_CUSTOM_SEARCH_API_KEY=  # For image search
GOOGLE_CUSTOM_SEARCH_CX=       # Custom Search Engine ID
```

### External Services
| Service | Purpose | Setup Required |
|---------|---------|----------------|
| Gemini Deep Research | Fact research | Use existing GOOGLE_API_KEY |
| Google Custom Search | Image search | Create Custom Search Engine |
| Supabase Storage | Image storage | Create `research_images` bucket |
| Redis (Upstash) | Caching | Already configured |

---

## Error Handling Strategy

**Per `RABA_Architecture.md` Section 5.4**:

| Error | Strategy | Action |
|-------|----------|--------|
| Deep research timeout | DEGRADE_QUALITY | Use basic grounded search fallback |
| Image search failure | RETRY_CURRENT | Retry up to 3 times, continue without images |
| Image download failure | Skip | Log error, continue with other images |
| Redis unavailable | Continue | Skip caching, proceed with persistence |
| Parse failure | RETRY_CURRENT | Retry with simpler prompt |

---

## Performance Targets

**Per `SRS.md` NFR-103**:
| Metric | Target |
|--------|--------|
| Deep Research latency | < 30 seconds (typical: 3-5 min for complex) |
| Image search latency | < 10 seconds |
| Total phase latency | < 60 seconds (with parallel execution) |

---

## Checklist Before Implementation

- [ ] Verify GOOGLE_API_KEY has Interactions API access
- [ ] Create Google Custom Search Engine and get CX
- [ ] Create `research_images` bucket in Supabase Storage
- [ ] Verify Redis connection working
- [ ] Review deep_research_Doc.md for latest API changes
- [ ] Confirm Phase 2.1 (Intent/Tool Selector) is complete and tested

---

## References

| Document | Section | Content |
|----------|---------|---------|
| `Guides/SRS.md` | FR-3xx | Functional requirements |
| `Guides/RABA_Architecture.md` | 2.4 | Deep Research Agent architecture |
| `Guides/rule.md` | Agents table | Agent responsibilities |
| `Documentations/deep_research_Doc.md` | Full | Gemini Deep Research API |
| `Documentations/gemini_doc.md` | - | General Gemini API reference |

---

## Next Phase

After completing Phase 2.3, proceed to:
- **Phase 2.4**: Script Generator Agent
  - Depends on: Deep Research output (research_data, research_images)
  - Creates: Viral-optimized script with scenes
