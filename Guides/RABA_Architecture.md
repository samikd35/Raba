# RABA: Multi-Agent YouTube Shorts Generation System
## Production-Grade Technical Architecture

**Status**: Design Document  
**Version**: 1.0  
**Date**: January 2026  
**Framework**: Python/FastAPI + LangGraph + Supabase + Redis

---

## Executive Summary

RABA is a production-grade, multi-agent system that automatically generates 18-25 second YouTube Shorts optimized for virality. The architecture combines specialized agents orchestrated through LangGraph's graph-based state machines, with dynamic tool repositories supporting unlimited video generation strategies. The system prioritizes viral engagement mechanics (completion rates, hook effectiveness, pattern interrupts) while maintaining factual accuracy through grounded web research and production-ready scalability from 2 initial tools to 100+ at production scale.

---

## Table of Contents

1. [High-Level Architecture](#high-level-architecture)
2. [Component Breakdown](#component-breakdown)
3. [Data Flow](#data-flow)
4. [Tool Repository System](#tool-repository-system)
5. [Agent Workflows](#agent-workflows)
6. [Viral Video Optimization](#viral-video-optimization)
7. [Configuration Management](#configuration-management)
8. [Database Schema](#database-schema)
9. [Caching Strategy](#caching-strategy)
10. [Bottlenecks & Security](#bottlenecks--security)
11. [Deployment & Monitoring](#deployment--monitoring)

---

## 1. High-Level Architecture

### System Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INPUT LAYER                         │
│  Topic, Duration (8-25s), Aspect Ratio, Resolution, Category,   │
│  HITL Mode (auto/manual), Audio, Subtitles, Reference Image     │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│               INTENT/TOOL SELECTOR AGENT                        │
│  (Extract intent, validate params, select best tool strategy)   │
│  Returns: {topic, intent_metadata, selected_tool, exec_params} │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│              DEEP RESEARCH AGENT                                │
│  (Use Gemini Deep Research API + Google Search for facts)       │
│  Returns: {research_data, citations, source_metadata}          │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│              SCRIPT WRITER/SCENE CREATOR AGENT                  │
│  (Generate rich, detailed script optimized for virality)        │
│  Returns: {scene_descriptions[], dialogue, timing, cues}       │
└────────────────────┬────────────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        ▼                         ▼
┌──────────────────┐     ┌──────────────────┐
│  IMAGE GENERATOR │     │ VIDEO GENERATOR  │
│  (Reference Img) │     │  (Final Output)  │
│ Nano Banana Pro  │     │   Veo 3.1        │
└────────┬─────────┘     └──────┬───────────┘
        │                       │
        └───────────┬───────────┘
                    ▼
        ┌───────────────────────┐
        │   OUTPUT PROCESSOR    │
        │  (Metadata, Upload)   │
        └───────────┬───────────┘
                    ▼
         ┌─────────────────────┐
         │   SUPABASE & S3     │
         │ (Storage + Metadata)│
         └─────────────────────┘
```

### Key Architecture Principles

1. **Modular Agent Design**: Each agent has a single responsibility with clear input/output contracts
2. **Graph-Based Orchestration**: LangGraph manages complex workflows with state persistence and cycles
3. **Dynamic Tool Abstraction**: Tool repository pattern enables 100+ strategies without code modification
4. **Viral-First Design**: Script generation and scene direction optimized for YouTube algorithm metrics
5. **Production Scalability**: Redis caching, async/await throughout, containerized deployment ready

---

## 2. Component Breakdown

### 2.1 FastAPI Backend (`main.py`)

**Purpose**: HTTP interface, session management, request routing to LangGraph workflows

```python
# Core responsibilities:
- Input validation and parameter normalization
- Session/user context tracking (Supabase auth)
- Async endpoint handlers triggering LangGraph execution
- Job status tracking and polling mechanisms
- Error handling and retry logic
- API rate limiting and metrics collection
```

**Key Endpoints**:
- `POST /api/v1/generate` - Initiate video generation
- `GET /api/v1/jobs/{job_id}` - Poll job status
- `GET /api/v1/jobs/{job_id}/result` - Retrieve final video
- `POST /api/v1/tools/register` - Register new tool (admin)
- `GET /api/v1/tools` - List available tools (with caching)

**Dependencies**: FastAPI, Uvicorn, Pydantic, python-jose, supabase-py (async)

---

### 2.2 LangGraph Orchestrator (`langgraph/orchestrator.py`)

**Purpose**: Graph-based workflow management with state machines

```
Core Components:
├── StateGraph Definition
│   ├── State Schema (shared across all agents)
│   ├── Node Functions (agents)
│   └── Edge Functions (conditional routing)
├── Checkpointer Configuration
│   └── Supabase-backed state persistence
└── Compiled Graph Executor
    └── invoke() with context tracking
```

**State Schema Structure**:
```python
class VideoGenerationState(TypedDict):
    # Input
    user_topic: str
    user_params: UserParameters  # duration, aspect_ratio, resolution
    
    # Tool Selection
    selected_tool: ToolMetadata
    tool_execution_params: dict
    
    # Research Phase
    research_data: ResearchOutput
    cached_research: bool
    
    # Script Generation
    script: ScriptOutput
    scene_descriptions: list[SceneDescription]
    
    # Image Generation
    reference_image_url: str
    reference_image_metadata: dict
    
    # Video Generation
    final_video_url: str
    video_metadata: VideoMetadata
    
    # Tracking
    job_id: str
    workflow_started_at: datetime
    phase_timestamps: dict
    error_state: Optional[ErrorMetadata]
```

**Node Functions**:

| Node | Input | Output | Timeout | Fallback |
|------|-------|--------|---------|----------|
| intent_tool_selector | user_topic + params | intent_metadata + selected_tool | 8s | Default tool (Surreal) |
| deep_research | topic + research_params | research_data | 60s | Cached/fallback data |
| script_writer | research_data + tool_specs | script_output | 45s | Template-based script |
| image_generator | script + tool_specs | reference_image | 120s | Generic reference (fast model) |
| video_generator | script + image + params | final_video | 180s | Lower resolution output |

> **Note**: Per rule.md, Intent Router and Tool Selector are combined into a single `intent_tool_selector` node.

---

### 2.3 Intent/Tool Selector Agent (`agents/intent_tool_selector.py`)

**Purpose**: Parse user input, extract intent, validate parameters, AND select optimal tool

> **Note**: Per design principles (rule.md), Intent extraction and Tool selection are combined 
> into a single agent to reduce latency and simplify the architecture.

**Responsibilities**:
- Extract topic/concept from user input
- Validate video parameters (duration, aspect ratio, resolution)
- Normalize input to standard schema
- Infer parameters like desired mood or tone via LLM (no rigid keyword rules)
- Query tool repository and select best-fit tool based on intent
- Handle edge cases (missing params, invalid ranges)

**Algorithm**:
1. Parse user input and extract intent via LLM
2. Validate and normalize parameters
3. Query tool repository for all available tools
4. Compute tool-topic relevance scores
5. Check tool capabilities against user parameters
6. Return combined intent + selected tool

**Fallback Logic**:
- Primary tool unavailable → secondary from same category
- Category unavailable → fallback to "Surreal Realism" (most flexible)
- All tools unavailable → queue for manual human review

**Tool Scoring Formula**:
```
score = (relevance_match * 0.4) + (capability_match * 0.3) + (cost_efficiency * 0.2) + (recency_success * 0.1)
```

**Output Schema**:
```python
{
    "topic": str,
    "intent_type": "educational|entertainment|inspirational|tutorial",
    "target_audience": "general|tech|science|business",
    "tone": "serious|humorous|dramatic|casual",
    "validated_params": {
        "duration_seconds": int,  # 8-25
        "aspect_ratio": "16:9|9:16",
        "resolution": "720p|1080p",
        "generation_mode": "text_2_video|image_2_video"
    },
    "selected_tool": ToolMetadata,
    "tool_execution_params": dict,
    "confidence": float
}
```

**LLM Model**: Gemini 2.5 Flash (low-latency, cost-optimized)

---

### 2.4 Deep Research Agent (`agents/deep_research.py`)

**Purpose**: Conduct fact-grounded research using Gemini 2.5 Pro + Google Search, including image discovery

**Architecture**:

```
Input: {topic, research_depth, user_context, user_reference_image}
    ↓
Check Redis Cache (L1)
    ↓
If MISS: Invoke Gemini 2.5 Pro with Google Search Grounding
    - Multi-step iterative searching
    - Identifies knowledge gaps
    - Synthesizes from multiple sources
    - Generates cited report
    ↓
Image Search (Google Custom Search API)
    - Search for relevant reference images
    - Download and store in Supabase Storage
    - Return image URLs for use in generation
    ↓
Cache Results in Redis
    - Key: hash(topic + context)
    - TTL: 7 days (configurable)
    - Value: {citations, facts, metadata, research_images[]}
    ↓
Persist to Supabase (workflows.research_output)
    ↓
Output: {research_data, sources[], confidence_scores, research_images[]}
```

**Image Search Integration** (Google Custom Search API):
```python
from googleapiclient.discovery import build
import httpx

class ResearchImageSearcher:
    """Search and download reference images during research."""
    
    def __init__(self, api_key: str, cx: str):
        self.service = build("customsearch", "v1", developerKey=api_key)
        self.cx = cx  # Custom Search Engine ID
    
    async def search_images(self, query: str, num_images: int = 3) -> list[dict]:
        """Search for images related to the research topic."""
        results = self.service.cse().list(
            q=query,
            cx=self.cx,
            searchType="image",
            num=min(num_images, 10),
            imgSize="large",
            safe="active"
        ).execute()
        
        return [
            {"url": item["link"], "title": item.get("title", "")}
            for item in results.get("items", [])
        ]
    
    async def download_and_store(self, image_url: str, workflow_id: str) -> str:
        """Download image and upload to Supabase Storage."""
        async with httpx.AsyncClient() as client:
            response = await client.get(image_url)
            if response.status_code == 200:
                # Upload to Supabase Storage
                path = f"research_images/{workflow_id}/{hash(image_url)}.jpg"
                # ... upload logic ...
                return storage_url
        return None
```

**Integration Details**:
- **LLM**: Gemini 2.5 Pro (high quality for factual research)
- **Grounding**: Automatic web search integration
- **Citation Format**: Structured [source_id] references
- **Depth Levels**: quick (5m), standard (15m), deep (30m)
- **Cost Model**: ~$0.10-0.50 per request (depending on depth)

**Output Schema**:
```python
{
    "research_findings": [
        {
            "topic_segment": str,
            "key_facts": str[],
            "citations": [{"source": str, "url": str, "quote": str}],
            "confidence": float  # 0.7-1.0
        }
    ],
    "research_depth_used": "quick|standard|deep",
    "total_sources": int,
    "generated_at": datetime,
    "cache_hit": bool
}
```

---

### 2.5 Script Writer Agent (`agents/script_writer.py`)

**Purpose**: Generate rich, detailed scripts optimized for YouTube Shorts virality

**Viral Optimization Algorithms**:

#### A. Hook Effectiveness Engine

```python
class HookArchetype(Enum):
    FORTUNETELLER = "Promise future outcome (transformation hook)"
    TEACHER = "Fast, actionable value (solution hook)"
    DISRUPTOR = "Challenge status quo (contrarian hook)"
    STORYTELLER = "Relatable narrative (emotional hook)"

hook_structure = {
    "archetype": HookArchetype,
    "verbal_hook": str,  # 1-2 seconds, spoken with confidence
    "visual_hook": str,  # High-contrast, immediate communication
    "psychological_lever": "curiosity_gap|fomo|relatability|dopamine",
    "estimated_vvsa_impact": float  # Views vs Swiped Away ratio
}
```

#### B. Pattern Interrupt Placement

```
Timeline for 18-25 second video:
├─ 0:00-0:03   [HOOK] Strongest opening, must stop scroll
├─ 0:03-0:08   [Pattern Interrupt 1] New visual/fact every 3-5s
├─ 0:08-0:13   [Pattern Interrupt 2] Shift perspective/introduce conflict
├─ 0:13-0:18   [Pattern Interrupt 3] Consequence/payoff setup
└─ 0:18-0:25   [RESOLUTION + CTA] Satisfying conclusion + call-to-action
```

#### C. Sensory Density Optimization

Script writing focuses on:
- **Specificity**: "Shuffling with hunched shoulders" > "walking sadly"
- **Sensory Detail**: Light, texture, atmosphere, sound
- **Emotional Triggers**: Authenticity, relatability, aspirational (not flashy)
- **Dialogue Precision**: Natural speech patterns, short phrasing for 8-second segments

**Output Schema**:
```python
{
    "hook": {
        "archetype": str,
        "script": str,
        "duration_seconds": float,
        "visual_direction": str
    },
    "scenes": [
        {
            "scene_number": int,
            "timestamp": "MM:SS-MM:SS",
            "description": str,  # Rich sensory detail
            "dialogue": Optional[str],
            "audio_cues": str[],
            "camera_direction": str,
            "lighting": str,
            "mood": str,
            "pattern_interrupt_type": Optional[str]
        }
    ],
    "call_to_action": {
        "type": "follow|like|comment|share|subscribe",
        "placement_seconds": float,
        "script": str
    },
    "estimated_completion_rate": float,  # 0.0-1.0
    "viral_score": float  # Composite metric
}
```

**LLM Model**: Gemini 2.5 Pro (with tool use for scene composition)

---

### 2.6 Image Generator Agent (`agents/image_generator.py`)

**Purpose**: Generate reference images using Nano Banana Pro (Gemini 2.5 Pro Image)

**Image Count Logic**:
- **Minimum**: 1 image
- **Maximum**: 5 images
- **Smart Reduction**: If user provided reference image OR research found images, reduce generated count

```python
def calculate_images_to_generate(
    user_has_reference: bool,
    research_image_count: int,
    scene_count: int
) -> int:
    """Calculate how many images to generate (1-5 limit)."""
    base_needed = min(scene_count, 5)  # Max 5 images
    
    # Reduce if we have external images
    external_images = (1 if user_has_reference else 0) + research_image_count
    
    # Generate fewer if we have external images
    to_generate = max(1, base_needed - external_images)
    
    return min(to_generate, 5)  # Never exceed 5
```

**Workflow**:
```
Input: {script, scenes[], user_reference_image?, research_images[]}
    ↓
Calculate images needed (1-5, reduced if external images exist)
    ↓
For each image:
    - Build prompt from scene description
    - Include user reference for style consistency
    - Apply category-specific style
    ↓
Invoke Nano Banana Pro (Gemini 2.5 Pro Image)
    ↓
Upload to Supabase Storage
    ↓
Persist to workflows.generated_images
    ↓
Combine all images: user_ref + research + generated
    ↓
Output: {all_image_urls[], generated_images[], metadata}
```

**Integration Details**:
- **API**: Nano Banana Pro (gemini-2.5-pro-image)
- **Fallback**: Gemini 2.5 Flash for simple scenes
- **Resolution Support**: 1K (1024×1024), 2K (2048×2048)
- **Generation Time**: ~13s @ 1K, ~16s @ 2K
- **Cost Model**: ~$0.05 per image
- **Aspect Ratio**: 1:1 primary, configurable via API

**Multi-Image Reference Strategy** (Future Enhancement):
- Up to 3 reference images for style consistency (Veo API limit)
- Character consistency across scenes
- Maintain aesthetic across multiple video variants

---

### 2.7 Video Generator Agent (`agents/video_generator.py`)

**Purpose**: Generate final video using Veo 3.1 with multi-segment support for videos >8s

**Multi-Segment Generation** (for videos >8 seconds):
```python
def plan_video_segments(duration_seconds: int) -> list[dict]:
    """
    Plan video segments for the requested duration.
    Veo 3.1 max segment duration is 8 seconds.
    
    For consistency, we maintain:
    - Same characters/style across segments
    - Smooth narrative flow
    - Use lastFrame of previous segment as reference for next
    """
    MAX_SEGMENT_DURATION = 8
    segments = []
    remaining = duration_seconds
    segment_num = 0
    
    while remaining > 0:
        segment_duration = min(remaining, MAX_SEGMENT_DURATION)
        segments.append({
            "segment_num": segment_num,
            "duration": segment_duration,
            "start_time": segment_num * MAX_SEGMENT_DURATION,
            "use_previous_frame": segment_num > 0  # For continuity
        })
        remaining -= segment_duration
        segment_num += 1
    
    return segments

# Example: 18s video = 3 segments (8s + 8s + 2s)
# Example: 25s video = 4 segments (8s + 8s + 8s + 1s)
```

**Segment Continuity Strategy**:
1. **First Segment**: Use reference images (user + research + generated)
2. **Subsequent Segments**: Extract last frame from previous segment as `firstFrame` reference
3. **Style Lock**: Apply same style/character prompts across all segments
4. **Narrative Flow**: Script is split proportionally across segments

**Prompt Engineering Strategy**:

The script and reference image are used **extensively**:

```python
veo_prompt = f"""
[REFERENCE IMAGE PROVIDED]
{script.hook.visual_direction}

{script.scenes[0].description}
{script.scenes[0].dialogue or ""}
Audio: {script.scenes[0].audio_cues[0]}

[00:00-00:03] {script.scenes[0].camera_direction}
[00:03-00:06] {script.scenes[1].description}
...

[CRITICAL]: Synchronize dialogue with provided script word-for-word.
Maintain visual consistency with reference image throughout.
Emotional tone: {script.scenes[0].mood}
Visual style: {tool_specs.aesthetic}
No subtitles, no text overlay.
"""
```

**Veo 3.1 Generation Parameters**:

| Parameter | Value Range | Default |
|-----------|-------------|---------|
| resolution | 720p, 1080p | User selected |
| aspect_ratio | 16:9, 9:16 | User selected |
| duration_seconds | 8-25 | User selected (per rule.md: direct 8-25s generation) |
| frame_rate | 24 fps | Fixed |
| audio_generation | true | Always enabled |
| video_mode | TEXT_2_VIDEO or IMAGE_2_VIDEO | Determined by availability |

**Quality Assurance Checks**:
1. Dialogue lip-sync alignment with script
2. Visual consistency with reference image
3. Audio presence and layering (dialogue + ambient)
4. Scene transitions smoothness
5. Compliance with platform guidelines (no watermarks except SynthID)

**Output Schema**:
```python
{
    "video_url": str,  # S3/Supabase Storage
    "video_duration": float,
    "resolution": str,
    "aspect_ratio": str,
    "file_size_mb": float,
    "generation_time_seconds": float,
    "quality_scores": {
        "dialogue_sync": float,
        "visual_consistency": float,
        "audio_quality": float,
        "overall_quality": float
    },
    "metadata": {
        "veo_model": "veo3.1",
        "generation_timestamp": datetime,
        "generation_cost_usd": float
    }
}
```

**Model Specs**:
- **Model**: Google Veo 3.1 (state-of-the-art, native audio)
- **Resolutions**: 720p, 1080p (per rule.md)
- **Duration**: 8-25 seconds (direct generation, no stitching required per rule.md)
- **Audio**: Native multi-layer audio (dialogue, SFX, ambient)
- **Cost Model**: ~$0.20-0.80 per video (depending on resolution/duration)

---

### 2.8 Output Processing (Post-Video Workflow Step)

**Purpose**: Handle metadata, storage, and delivery

> **Note**: Per rule.md, output processing is NOT a separate agent but a post-processing
> step in the workflow after the Video Generator Agent completes.

**Responsibilities**:
- Upload video to S3/Supabase Storage
- Generate metadata (thumbnail, duration, encoding info)
- Create job completion record in Supabase
- Trigger webhook notifications
- Return shareable links
- In manual mode: pause for user approval before final return

---

## 3. Data Flow

### End-to-End Workflow Sequence

```
1. USER INPUT
   POST /api/v1/generate {
     topic: str,
     duration_seconds: 8-25,
     aspect_ratio: "9:16" | "16:9",
     resolution: "720p" | "1080p",
     category: "surreal_realism" | "high_octane_anime" | "stylized_3d" | "auto",
     hitl_mode: "auto" | "manual",
     enable_audio: bool,
     enable_subtitles: bool,
     reference_image?: File  # Optional user-uploaded reference
   }
   ↓
2. REQUEST VALIDATION & STORAGE
   - Validate all parameters
   - Upload reference image to Supabase Storage (if provided)
   - Create workflow record in Supabase
   - Initialize LangSmith trace
   ↓
3. INTENT/TOOL SELECTION
   - Analyze topic and user parameters
   - Select category (or use user's choice if not "auto")
   - Select best tool for the category
   - [HITL GATE 1] If manual: pause for user approval/feedback
     * User can change category
     * User can provide feedback
   - Persist: workflows.tool_selection
   ↓
4. DEEP RESEARCH
   - Research topic with Gemini 2.5 Pro + Google Search
   - Search and download reference images (Google Custom Search API)
   - [HITL GATE 2] If manual: pause for user review
     * User can edit/add facts
     * User can provide feedback to regenerate
   - Persist: workflows.research_output, workflows.research_images
   ↓
5. SCRIPT GENERATION
   - Generate script using research + tool specs
   - [HITL GATE 3] If manual: pause for user review
     * User can edit script directly
     * User can provide feedback to regenerate
   - Persist: workflows.script_output
   ↓
6. IMAGE GENERATION (1-5 images)
   - Calculate images needed (reduced if external images exist)
   - Generate with Nano Banana Pro (Gemini 2.5 Pro Image)
   - [HITL GATE 4] If manual: pause for user review
     * User can add additional reference images
     * User can provide feedback to regenerate
   - Persist: workflows.generated_images, media table
   ↓
7. VIDEO GENERATION (Veo 3.1)
   - Plan segments if duration > 8s
   - Generate video with all reference images
   - Include audio if enabled
   - Generate subtitles if enabled
   - [HITL GATE 5] If manual: pause for user approval
     * User can approve or regenerate
   - Persist: workflows.video_output, media table
   ↓
8. OUTPUT PROCESSING
   - Finalize video in Supabase Storage
   - Update workflow status to 'completed'
   - Complete LangSmith trace
   ↓
9. RETURN RESULT
   GET /api/v1/workflows/{workflow_id}
   → {video_url, all_media, metadata, generation_time}
```

### State Persistence During Workflow

> **Note**: Per rule.md, Intent Router and Tool Selector are combined.

- **Checkpoint 1**: After Intent/Tool Selection (combined per rule.md)
- **Checkpoint 2**: After Deep Research (expensive, cacheable)
- **Checkpoint 3**: After Script Generation (allow script refinement in manual mode)
- **Checkpoint 4**: After Image Generation (cached for retries)
- **Final**: After Video Generation (job complete)

---

## 4. Tool Repository System

### 4.1 Tool Abstraction Architecture

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List

class VideoGenerationTool(ABC):
    """Base class for all video generation tools"""
    
    def __init__(self, config: ToolConfig):
        self.tool_id: str
        self.tool_name: str
        self.category: str  # "surreal_realism", "high_octane_anime", "stylized_3d"
        self.capabilities: ToolCapabilities
        self.api_endpoint: str
        self.model_version: str
        self.cost_per_request: float
        self.estimated_quality: float  # 0-1
        self.supported_aspect_ratios: List[str]
        self.supported_resolutions: List[str]
        self.max_duration_seconds: int
        self.description: str
        self.example_outputs: List[str]
    
    @abstractmethod
    def get_optimal_script_format(self) -> ScriptFormatSpec:
        """Return script formatting requirements"""
        pass
    
    @abstractmethod
    def get_image_prompt_template(self) -> str:
        """Return image generation prompt template"""
        pass
    
    @abstractmethod
    def get_video_prompt_template(self) -> str:
        """Return video generation prompt template"""
        pass
    
    @abstractmethod
    def validate_topic_fit(self, topic: str, intent: str) -> float:
        """Return relevance score (0-1)"""
        pass
    
    @abstractmethod
    def estimate_generation_time(self) -> float:
        """Return estimated time in seconds"""
        pass

class ToolRegistry:
    """Centralized tool management"""
    
    def __init__(self, db_client):
        self.tools: Dict[str, VideoGenerationTool] = {}
        self.db = db_client
        self.cache_ttl = 3600  # 1 hour
    
    def register_tool(self, tool: VideoGenerationTool) -> bool:
        """Add new tool to registry"""
        self.tools[tool.tool_id] = tool
        # Persist to Supabase
        self.db.table("tools").insert({
            "tool_id": tool.tool_id,
            "metadata": tool.to_dict()
        })
        return True
    
    def get_tool(self, tool_id: str) -> VideoGenerationTool:
        """Retrieve tool by ID"""
        return self.tools.get(tool_id)
    
    def get_tools_by_category(self, category: str) -> List[VideoGenerationTool]:
        """Get all tools in a category"""
        return [t for t in self.tools.values() if t.category == category]
    
    def list_all_tools(self) -> List[Dict]:
        """Return all tools metadata (cached)"""
        # Check Redis cache first
        return self._get_from_cache("tools_list") or self._fetch_from_db()
```

### 4.2 Initial Tool Implementations (Phase 1)

#### Tool 1: "Impossible Simulations" (Surreal Realism)

```python
class ImpossibleSimulationsTool(VideoGenerationTool):
    tool_id = "surreal_impossible_sims"
    tool_name = "Impossible Simulations"
    category = "surreal_realism"
    
    capabilities = ToolCapabilities(
        flow_visualization=True,  # Magnetic fields, stress points
        invisible_forces=True,
        photorealistic_grounding=True,
        viral_signal="Information without Boredom"
    )
    
    def validate_topic_fit(self, topic: str, intent: str) -> float:
        keywords = ["physics", "quantum", "magnetic", "force", "invisible", "structure"]
        score = sum(1 for kw in keywords if kw in topic.lower()) / len(keywords)
        return score * 0.8  # Base multiplier
    
    def get_video_prompt_template(self) -> str:
        return """
        Visualize the invisible forces and structures in {topic} using flowing, 
        liquid-glass aesthetics. Show {element} as a tangible phenomenon with 
        color gradients representing {attribute}. Use photorealistic grounding 
        while depicting impossible physical phenomena. Maintain scientific accuracy 
        while ensuring visual wonder. Focus on {focus_area}.
        """
```

#### Tool 2: "Concept Combat" (High-Octane Anime)

```python
class ConceptCombatTool(VideoGenerationTool):
    tool_id = "anime_concept_combat"
    tool_name = "Concept Combat"
    category = "high_octane_anime"
    
    capabilities = ToolCapabilities(
        philosophical_debates=True,
        sakuga_style=True,
        calligraphic_combat=True,
        scientific_origin_reconstruction=True,
        viral_signal="Zen-Action"
    )
    
    def validate_topic_fit(self, topic: str, intent: str) -> float:
        keywords = ["philosophy", "ethics", "science", "history", "discovery", "debate"]
        score = sum(1 for kw in keywords if kw in topic.lower()) / len(keywords)
        return score * 0.85  # Higher for abstract topics
    
    def get_video_prompt_template(self) -> str:
        return """
        Recreate the {topic} as a high-energy Sakuga-style battle. Personify 
        {concept1} and {concept2} as opposing forces engaging in a philosophical 
        duel. Each strike represents a logical argument. Use ink-splashes to form 
        key definitions on screen. Camera movements should be dynamic with 
        elemental explosions. Scientific laws warp the environment visually.
        """
```

### 4.3 Scaling to 100+ Tools

**Registry Expansion Strategy**:

```
Phase 1 (Now): 2 tools (Impossible Simulations, Concept Combat)
Phase 2 (Q1 2026): 10 tools (add Data Dioramas variants, educational tools)
Phase 3 (Q2 2026): 50+ tools (expand across niches: finance, health, tech, art)
Phase 4 (Q3 2026): 100+ tools (hyper-specialized by niche + sub-niche)

Tool addition process:
1. Create tool class inheriting VideoGenerationTool
2. Implement required abstract methods
3. Test via sandbox endpoint
4. Register via POST /api/v1/tools/register
5. Automatic indexing + caching
```

**Dynamic Tool Addition** (Admin API):
```bash
curl -X POST http://localhost:8000/api/v1/tools/register \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer admin_token" \
  -d '{
    "tool_id": "stylized_data_dioramas",
    "tool_name": "Data Dioramas",
    "category": "stylized_3d",
    "implementation_module": "tools.stylized_3d.data_dioramas",
    "description": "Turn statistics into physical miniature landscapes"
  }'
```

---

## 5. Agent Workflows

### 5.1 Supervisor Agent Pattern

> **Note**: Per rule.md, Intent Router and Tool Selector are combined into a single agent.
> Output Processing is a workflow step, not a separate agent.

```
                    ┌─────────────────────┐
                    │   User Request      │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │  SUPERVISOR AGENT   │
                    │ (Route Orchestrator)│
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                                 ▼
     ┌─────────────────┐              ┌──────────────┐
     │ Intent/Tool     │              │ Research     │
     │ Selector Agent  │              │ Coordinator  │
     └────────┬────────┘              └──────┬───────┘
              │                              │
     ┌────────▼────────┐              ┌──────▼───────┐
     │ Intent +        │              │ Grounded     │
     │ Selected Tool   │              │ Facts        │
     └────────┬────────┘              └──────┬───────┘
              │                              │
              └──────────────┼──────────────┘
                              │
                    ┌─────────▼─────────┐
                    │  Script Writer    │
                    │    (Tool-Aware)   │
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │  Image Generator  │
                    │ (Dynamic Model)   │
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │ Video Generator   │
                    │ (8-25s direct)    │
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │ Output Processing │
                    │ (Workflow Step)   │
                    └───────────────────┘
```

### 5.2 HITL (Human-in-the-Loop) Feedback System

When `hitl_mode="manual"`, the workflow pauses at each gate for user review.

**HITL Gate Flow**:
```
┌─────────────────────────────────────────────────────────────────────┐
│                         HITL GATE FLOW                              │
└─────────────────────────────────┬─────────────────────────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │  Agent Generates Output   │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │  hitl_mode == "manual"?   │
                    └──────┬────────────┬──────┘
                           │ YES        │ NO
              ┌────────────▼──────────┐  │
              │ Pause for User Review │  │
              │ - View output         │  │
              │ - Edit directly       │  │
              │ - Provide feedback    │  │
              │ - Add images (if img) │  │
              └───────────┬───────────┘  │
                        │              │
           ┌────────────▼───────────┐  │
           │ User Action?           │  │
           └──┬──────┬──────┬──────┘  │
              │      │      │         │
         APPROVE  EDIT  REGENERATE   │
              │      │      │         │
              │      │      └─────────┤
              │      │              │  │
              │      └──────────────┤  │
              │                     │  │
              └─────────────────────┤  │
                                    │  │
                    ┌─────────────▼─▼───────────┐
                    │   Continue to Next Agent   │
                    └────────────────────────────┘
```

**HITL Gate Implementation**:
```python
from enum import Enum
from typing import Optional
from pydantic import BaseModel

class HITLAction(Enum):
    APPROVE = "approve"      # Continue to next step
    EDIT = "edit"           # User directly edited the content
    REGENERATE = "regenerate"  # Regenerate with feedback
    ADD_IMAGE = "add_image"    # User adds image (image gate only)

class HITLFeedback(BaseModel):
    gate: str  # tool_selection, deep_research, script, image, video
    action: HITLAction
    feedback: Optional[str] = None  # User's feedback for regeneration
    edited_content: Optional[dict] = None  # User's direct edits
    additional_images: Optional[list[str]] = None  # User-added images

async def handle_hitl_gate(
    workflow_id: str,
    gate: str,
    current_output: dict,
    max_regenerations: int = 3
) -> dict:
    """
    Handle HITL gate - pause workflow and wait for user action.
    
    Returns the final output after user approval/edit.
    """
    # Update workflow status
    await supabase.table("workflows").update({
        "current_hitl_gate": gate,
        "status": f"awaiting_{gate}_approval"
    }).eq("id", workflow_id).execute()
    
    # Wait for user action (webhook or polling)
    # This is handled by the API endpoint
    return current_output

async def process_hitl_feedback(
    workflow_id: str,
    feedback: HITLFeedback
) -> dict:
    """Process user's HITL feedback."""
    workflow = await get_workflow(workflow_id)
    regeneration_count = len([
        f for f in workflow.hitl_feedback 
        if f["gate"] == feedback.gate and f["action"] == "regenerate"
    ])
    
    if feedback.action == HITLAction.APPROVE:
        # Clear gate, continue
        await update_workflow(workflow_id, {"current_hitl_gate": None})
        return {"continue": True}
    
    elif feedback.action == HITLAction.EDIT:
        # Apply user's direct edits
        await apply_user_edits(workflow_id, feedback.gate, feedback.edited_content)
        return {"continue": True}
    
    elif feedback.action == HITLAction.REGENERATE:
        if regeneration_count >= 3:
            raise ValueError("Max regeneration attempts reached")
        # Store feedback and trigger regeneration
        await store_feedback(workflow_id, feedback)
        return {"regenerate": True, "feedback": feedback.feedback}
    
    elif feedback.action == HITLAction.ADD_IMAGE:
        # Add user's images to workflow
        await add_user_images(workflow_id, feedback.additional_images)
        return {"continue": True}
```

**HITL Gates by Phase**:

| Gate | User Can | Regenerate With |
|------|----------|----------------|
| **Tool Selection** | Change category, approve tool | Different category preference |
| **Deep Research** | Edit facts, view sources | Different research angle |
| **Script** | Edit text, change hook/punchline | Feedback on tone/content |
| **Image Generation** | Add images, remove images | Style/composition feedback |
| **Video Generation** | Approve/reject final | Pacing/transition feedback |

### 5.3 Conditional Routing Logic

```python
def route_after_intent_tool_selection(state: VideoGenerationState) -> str:
    """Determine next node after Intent/Tool Selection"""
    if not state.intent_metadata.get("is_valid"):
        return "error_handler"
    if not state.selected_tool:
        return "error_handler"
    
    # Check for HITL gate
    if state.hitl_mode == "manual" and not state.hitl_approved.get("tool_selection"):
        return "hitl_tool_selection_gate"
    
    return "deep_research"

def route_after_research(state: VideoGenerationState) -> str:
    """Check research quality and HITL"""
    if state.research_data.get("confidence") < 0.6:
        return "deep_research"  # Retry
    
    if state.hitl_mode == "manual" and not state.hitl_approved.get("research"):
        return "hitl_research_gate"
    
    return "script_writer"

def route_after_script(state: VideoGenerationState) -> str:
    """Route after script generation"""
    if state.hitl_mode == "manual" and not state.hitl_approved.get("script"):
        return "hitl_script_gate"
    return "image_generator"

def route_after_images(state: VideoGenerationState) -> str:
    """Route after image generation"""
    if state.hitl_mode == "manual" and not state.hitl_approved.get("images"):
        return "hitl_image_gate"
    return "video_generator"

def route_after_video(state: VideoGenerationState) -> str:
    """Route after video generation"""
    if state.hitl_mode == "manual" and not state.hitl_approved.get("video"):
        return "hitl_video_gate"
    return "output_processing"
```

### 5.4 Error Handling & Fallbacks

```python
class ErrorRecoveryStrategy(Enum):
    RETRY_CURRENT = "Retry current node with fresh params"
    FALLBACK_TOOL = "Switch to backup tool from same category"
    DEGRADE_QUALITY = "Reduce resolution/duration, continue"
    MANUAL_REVIEW = "Queue for human review"
    USER_PROMPT = "Ask user for clarification"

error_handlers = {
    "deep_research_timeout": {
        "strategy": ErrorRecoveryStrategy.DEGRADE_QUALITY,
        "action": "Use cached research + reduce depth",
        "max_retries": 1
    },
    "image_generator_failure": {
        "strategy": ErrorRecoveryStrategy.FALLBACK_TOOL,
        "action": "Use alternative image generation service",
        "max_retries": 2
    },
    "video_generator_api_limit": {
        "strategy": ErrorRecoveryStrategy.DEGRADE_QUALITY,
        "action": "Generate 720p instead of 1080p",
        "max_retries": 3
    },
    "invalid_topic": {
        "strategy": ErrorRecoveryStrategy.USER_PROMPT,
        "action": "Return clarification request",
        "max_retries": 0
    }
}
```

### 5.5 LangSmith Tracing Integration

**Environment Configuration** (from `.env`):
```bash
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_pt_xxxxx
LANGCHAIN_PROJECT=Raba
```

**Tracing Implementation**:
```python
import os
from langsmith import traceable
from langsmith.run_trees import RunTree

# Environment variables are automatically picked up by LangChain/LangGraph
# when LANGCHAIN_TRACING_V2=true

class TracingManager:
    """Centralized tracing for all workflow steps."""
    
    def __init__(self):
        self.enabled = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
        self.project = os.getenv("LANGCHAIN_PROJECT", "Raba")
    
    @traceable(name="intent_tool_selection")
    async def trace_intent_tool_selection(self, workflow_id: str, input_data: dict):
        """Trace Intent/Tool Selection step."""
        # LangSmith automatically captures input/output
        pass
    
    @traceable(name="deep_research")
    async def trace_deep_research(self, workflow_id: str, topic: str):
        """Trace Deep Research step."""
        pass
    
    @traceable(name="script_generation")
    async def trace_script_generation(self, workflow_id: str, research: dict):
        """Trace Script Generation step."""
        pass
    
    @traceable(name="image_generation")
    async def trace_image_generation(self, workflow_id: str, scene_count: int):
        """Trace Image Generation step."""
        pass
    
    @traceable(name="video_generation")
    async def trace_video_generation(self, workflow_id: str, duration: int):
        """Trace Video Generation step."""
        pass

# LangGraph Integration - traces are automatic when env vars are set
from langgraph.graph import StateGraph

def create_workflow_graph():
    """Create LangGraph workflow with automatic LangSmith tracing."""
    workflow = StateGraph(VideoGenerationState)
    
    # All nodes are automatically traced when LANGCHAIN_TRACING_V2=true
    workflow.add_node("intent_tool_selector", intent_tool_selector_node)
    workflow.add_node("deep_research", deep_research_node)
    workflow.add_node("script_writer", script_writer_node)
    workflow.add_node("image_generator", image_generator_node)
    workflow.add_node("video_generator", video_generator_node)
    
    # Add HITL gates (only active when hitl_mode="manual")
    workflow.add_node("hitl_tool_selection_gate", hitl_gate_node)
    workflow.add_node("hitl_research_gate", hitl_gate_node)
    workflow.add_node("hitl_script_gate", hitl_gate_node)
    workflow.add_node("hitl_image_gate", hitl_gate_node)
    workflow.add_node("hitl_video_gate", hitl_gate_node)
    
    # ... edges and routing ...
    
    return workflow.compile()
```

**Trace Structure in LangSmith Dashboard**:
```
Raba Project
└── Workflow: {workflow_id}
    ├── intent_tool_selection (2.3s)
    │   ├── Input: {topic, params}
    │   └── Output: {tool_id, category}
    ├── deep_research (15.2s)
    │   ├── Input: {topic}
    │   ├── Gemini API Call
    │   ├── Google Search Grounding
    │   ├── Image Search
    │   └── Output: {findings, images}
    ├── script_generation (8.1s)
    │   ├── Input: {research, tool_specs}
    │   └── Output: {script, viral_score}
    ├── image_generation (45.3s)
    │   ├── Input: {scenes, reference_images}
    │   ├── Nano Banana Pro x3
    │   └── Output: {image_urls}
    └── video_generation (120.5s)
        ├── Input: {script, images, duration}
        ├── Veo 3.1 Segment 1
        ├── Veo 3.1 Segment 2
        ├── Veo 3.1 Segment 3
        └── Output: {video_url, audio_url}
```

---

## 6. Viral Video Optimization

### 6.1 Hook Architecture Integration

**Hooks are embedded in every script generation**:

```python
class HookOptimizer:
    """Ensures maximum video completion rates"""
    
    def select_hook_archetype(self, topic: str, intent: str) -> HookArchetype:
        """Choose optimal hook type"""
        if "how to" in topic.lower():
            return HookArchetype.TEACHER
        elif "new discovery" in topic.lower():
            return HookArchetype.FORTUNETELLER
        elif "belief" in topic.lower():
            return HookArchetype.DISRUPTOR
        else:
            return HookArchetype.STORYTELLER
    
    def generate_hook_script(self, archetype: HookArchetype, 
                            research: ResearchOutput) -> str:
        """Generate 1-2 second hook optimized for platform"""
        
        if archetype == HookArchetype.TEACHER:
            return f"You've been understanding {topic} wrong. Here's the truth:"
        elif archetype == HookArchetype.FORTUNETELLER:
            return f"In 30 seconds, you'll understand why {finding}"
        elif archetype == HookArchetype.DISRUPTOR:
            return f"Everything you know about {topic} is misleading"
        else:
            return f"This is what nobody expected about {topic}"
    
    def calculate_vvsa_score(self, hook_archetype: HookArchetype, 
                            visual_hook: str) -> float:
        """Estimate Views vs Swiped Away ratio"""
        # Composite of archetype effectiveness + visual impact
        archetype_scores = {
            HookArchetype.TEACHER: 0.82,
            HookArchetype.FORTUNETELLER: 0.85,
            HookArchetype.DISRUPTOR: 0.88,
            HookArchetype.STORYTELLER: 0.80
        }
        return archetype_scores[hook_archetype] * 0.95  # Conservative estimate
```

### 6.2 Pattern Interrupt Scheduling

**Every 3-5 seconds, introduce new visual/conceptual element**:

```python
class PatternInterruptScheduler:
    """Prevent attention decay in short-form video"""
    
    interrupt_types = [
        "scene_change",        # New location/subject
        "visual_effect",       # Transition, animation shift
        "new_fact",           # Information reveal
        "perspective_shift",  # Different angle/interpretation
        "emotional_pivot",    # Mood change
        "sensory_cue"        # Sound/visual surprise
    ]
    
    def schedule_interrupts(self, total_duration: int, 
                           scene_descriptions: list) -> list:
        """Place interrupts to maximize retention"""
        interrupts = []
        interval = 3  # Every 3 seconds minimum
        
        for timestamp in range(0, total_duration, interval):
            scene_idx = min(len(scene_descriptions) - 1, 
                          timestamp // (total_duration // len(scene_descriptions)))
            interrupts.append({
                "timestamp": timestamp,
                "type": self._select_interrupt_type(scene_idx),
                "scene_description": scene_descriptions[scene_idx]
            })
        
        return interrupts
    
    def _select_interrupt_type(self, scene_idx: int) -> str:
        """Vary interrupt types to prevent habituation"""
        rotation = [
            "visual_effect",
            "new_fact",
            "perspective_shift",
            "sensory_cue"
        ]
        return rotation[scene_idx % len(rotation)]
```

### 6.3 Completion Rate Prediction

**Estimate script quality before generation**:

```python
class CompletionRatePredictor:
    """ML-based retention score"""
    
    def predict_completion_rate(self, script_output: ScriptOutput) -> float:
        """Estimate % of viewers who watch entire video"""
        
        score = 0.0
        weights = {
            "hook_strength": 0.25,
            "pattern_interrupt_density": 0.20,
            "emotional_arc": 0.20,
            "call_to_action_clarity": 0.15,
            "audience_fit": 0.10,
            "novelty_factor": 0.10
        }
        
        score += self._evaluate_hook(script_output.hook) * weights["hook_strength"]
        score += self._evaluate_interrupts(script_output.scenes) * weights["pattern_interrupt_density"]
        score += self._evaluate_emotional_arc(script_output.scenes) * weights["emotional_arc"]
        score += self._evaluate_cta(script_output.call_to_action) * weights["call_to_action_clarity"]
        score += self._evaluate_audience_fit(script_output.intent) * weights["audience_fit"]
        score += self._evaluate_novelty(script_output.research) * weights["novelty_factor"]
        
        return min(0.98, score)  # Conservative cap at 98%
    
    def _evaluate_hook(self, hook: dict) -> float:
        """Hook effectiveness (0-1)"""
        # Check: is it <3 seconds, clear value prop, psychologically resonant?
        if hook.get("duration_seconds", 0) > 3:
            return 0.6
        if "?" in hook.get("script", ""):  # Question format
            return 0.85
        return 0.75
```

---

## 7. Configuration Management

### 7.1 Centralized Configuration (`config/settings.py`)

```python
from pydantic_settings import BaseSettings
from typing import Optional

class LLMConfig(BaseSettings):
    """LLM Model Configuration"""
    # All models use Gemini 2.5 family (no Gemini 3)
    intent_tool_selector_model: str = "gemini-2.5-flash"  # Fast, cost-optimized
    deep_research_model: str = "gemini-2.5-pro"  # High quality for research
    script_writer_model: str = "gemini-2.5-pro"  # Creative, detailed scripts
    
    intent_router_temp: float = 0.3
    script_writer_temp: float = 0.7
    
    max_tokens_intent: int = 500
    max_tokens_script: int = 2000

class ImageGenConfig(BaseSettings):
    """Image Generation Configuration"""
    # Use Gemini 2.5 family only (Nano Banana Pro is gemini-2.5-pro-image)
    model_fast: str = "gemini-2.5-flash"  # For simple scenes (speed)
    model_quality: str = "gemini-2.5-pro-image"  # Nano Banana Pro for complex scenes
    min_images: int = 1  # Minimum images to generate
    max_images: int = 5  # Maximum images to generate
    endpoint: str = "https://api.nanobanana.ai/v1/generate"
    default_resolution: str = "1080p"  # 1K, 2K
    max_aspect_ratios: list = ["1:1"]
    generation_timeout_seconds: int = 120
    fallback_service: str = "gemini-2.5-flash"  # Fallback to fast model

class VideoGenConfig(BaseSettings):
    """Video Generation Configuration"""
    model: str = "veo-3.1"
    endpoint: str = "https://vertex-ai.googleapis.com/v1"
    default_resolution: str = "1080p"  # 720p, 1080p (per rule.md)
    supported_aspect_ratios: list = ["16:9", "9:16"]
    frame_rate: int = 24
    max_duration_seconds: int = 25  # Per rule.md: 8-25s direct generation
    generation_timeout_seconds: int = 180
    enable_audio: bool = True

class ResearchConfig(BaseSettings):
    """Deep Research Configuration"""
    model: str = "gemini-2.5-pro"  # High quality for factual research
    enable_image_search: bool = True  # Search and download reference images
    api_endpoint: str = "https://generativelanguage.googleapis.com"
    default_depth: str = "standard"  # quick, standard, deep
    enable_web_grounding: bool = True
    research_timeout_seconds: int = 60
    cache_ttl_seconds: int = 604800  # 7 days

class RedisConfig(BaseSettings):
    """Redis Cache Configuration"""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    ttl_short: int = 3600  # 1 hour
    ttl_medium: int = 86400  # 1 day
    ttl_long: int = 604800  # 7 days
    
    # Cache keys
    cache_prefix: str = "raba:"
    cache_research: str = "raba:research:{topic_hash}"
    cache_tools: str = "raba:tools:list"
    cache_scripts: str = "raba:script:{prompt_hash}"

class SupabaseConfig(BaseSettings):
    """Supabase Configuration"""
    url: str
    api_key: str
    db_schema: str = "public"
    enable_async: bool = True
    connection_pool_size: int = 20

class ViralityConfig(BaseSettings):
    """Viral Optimization Tuning"""
    hook_archetype_weights: dict = {
        "fortuneteller": 0.85,
        "teacher": 0.82,
        "disruptor": 0.88,
        "storyteller": 0.80
    }
    pattern_interrupt_interval_seconds: int = 3
    target_completion_rate: float = 0.90
    min_completion_rate_threshold: float = 0.70
    enable_smart_retry: bool = True

class HITLConfig(BaseSettings):
    """Human-in-the-Loop Configuration"""
    default_mode: str = "auto"  # "auto" or "manual"
    # In manual mode, HITL gates appear at these transitions:
    gates: list = [
        "tool_selection",      # After tool selection - user can accept/change category
        "deep_research",       # After research - user can review/edit facts
        "script_generation",   # After script - user can edit/regenerate
        "image_generation",    # After images - user can add images/regenerate
        "video_generation"     # After video - user can approve/regenerate
    ]
    max_regeneration_attempts: int = 3  # Max times user can regenerate at each gate

class LangSmithConfig(BaseSettings):
    """LangSmith Tracing Configuration"""
    enabled: bool = True
    api_key: str = ""  # From LANGCHAIN_API_KEY env var
    project: str = "Raba"  # From LANGCHAIN_PROJECT env var
    tracing_v2: bool = True  # From LANGCHAIN_TRACING_V2 env var

class UserInputConfig(BaseSettings):
    """User Input Parameters Configuration"""
    # Video parameters
    min_duration_seconds: int = 8
    max_duration_seconds: int = 30
    default_duration_seconds: int = 18
    supported_aspect_ratios: list = ["9:16", "16:9"]
    default_aspect_ratio: str = "9:16"
    supported_resolutions: list = ["720p", "1080p"]
    default_resolution: str = "1080p"
    
    # Content parameters
    supported_categories: list = ["surreal_realism", "high_octane_anime", "stylized_3d", "auto"]
    default_category: str = "auto"  # Agent selects best category
    
    # Audio/Subtitle parameters
    enable_audio: bool = True  # Default: generate audio
    enable_subtitles: bool = False  # Default: no subtitles
    
    # Reference image
    allow_reference_image: bool = True  # User can upload reference image
    max_reference_image_size_mb: int = 10

class Settings(BaseSettings):
    """Master Configuration"""
    environment: str = "development"  # development, staging, production
    debug: bool = True if environment == "development" else False
    api_version: str = "v1"
    
    llm: LLMConfig = LLMConfig()
    image_gen: ImageGenConfig = ImageGenConfig()
    video_gen: VideoGenConfig = VideoGenConfig()
    research: ResearchConfig = ResearchConfig()
    redis: RedisConfig = RedisConfig()
    supabase: SupabaseConfig = SupabaseConfig()
    virality: ViralityConfig = ViralityConfig()
    hitl: HITLConfig = HITLConfig()
    langsmith: LangSmithConfig = LangSmithConfig()
    user_input: UserInputConfig = UserInputConfig()
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        # Load from environment variables with prefix
        env_nested_delimiter = "__"

settings = Settings()

# LangSmith tracing is configured via environment variables:
# LANGCHAIN_TRACING_V2=true
# LANGCHAIN_API_KEY=<your-api-key>
# LANGCHAIN_PROJECT=Raba
```

### 7.2 Environment-Specific Loading

```
# .env.development
ENVIRONMENT=development
DEBUG=true
SUPABASE_URL=http://localhost:54321
SUPABASE_API_KEY=dev-key

LLM_INTENT_ROUTER_MODEL=gemini-2.5-flash
LLM_SCRIPT_WRITER_MODEL=gemini-2.5-pro

IMAGE_GEN_MODEL=nano-banana-pro
IMAGE_GEN_DEFAULT_RESOLUTION=720p

VIDEO_GEN_MODEL=veo-3.1
VIDEO_GEN_DEFAULT_RESOLUTION=720p

REDIS_HOST=localhost
REDIS_PORT=6379

# .env.production
ENVIRONMENT=production
DEBUG=false
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_API_KEY=prod-key

LLM_INTENT_ROUTER_MODEL=gemini-2.5-flash
LLM_SCRIPT_WRITER_MODEL=gemini-2.5-pro-turbo

IMAGE_GEN_MODEL=nano-banana-pro
IMAGE_GEN_DEFAULT_RESOLUTION=1080p

VIDEO_GEN_MODEL=veo-3.1
VIDEO_GEN_DEFAULT_RESOLUTION=1080p

REDIS_HOST=redis.production.internal
REDIS_PORT=6380
```

**Runtime Model Switching**:
```python
def get_llm_model(agent_type: str) -> str:
    """Dynamically select model based on config"""
    if settings.environment == "production":
        return settings.llm.script_writer_model  # Higher quality
    else:
        return settings.llm.intent_router_model  # Faster/cheaper
```

---

## 8. Database Schema

### 8.1 Design Principles

> **Best Practice**: Minimize table count by using JSONB for extensible data.
> Store all workflow-related data in a single `workflows` table with JSONB columns
> for each phase's output. This enables atomic updates and simpler queries.

### 8.2 Supabase Tables (Consolidated Design)

```sql
-- ============================================================
-- CORE TABLE: workflows (main workflow tracking with all outputs)
-- This is the PRIMARY table - stores everything for a video generation
-- ============================================================
CREATE TABLE workflows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN (
        'pending', 'tool_selection', 'researching', 'scripting', 
        'generating_images', 'generating_video', 'completed', 'failed'
    )),
    
    -- ========== USER INPUT PARAMETERS ==========
    topic TEXT NOT NULL,
    duration_seconds INT CHECK (duration_seconds BETWEEN 8 AND 25) DEFAULT 18,
    aspect_ratio VARCHAR(10) DEFAULT '9:16',
    resolution VARCHAR(10) DEFAULT '1080p',
    category VARCHAR(50) DEFAULT 'auto',  -- surreal_realism, high_octane_anime, stylized_3d, auto
    hitl_mode VARCHAR(10) DEFAULT 'auto' CHECK (hitl_mode IN ('auto', 'manual')),
    enable_audio BOOLEAN DEFAULT true,
    enable_subtitles BOOLEAN DEFAULT false,
    user_reference_image_url TEXT,  -- Optional user-uploaded reference image
    
    -- ========== AGENT OUTPUTS (stored as JSONB for flexibility) ==========
    -- Tool Selection Output
    tool_selection JSONB,  -- {tool_id, tool_name, category, confidence, recommended_changes}
    
    -- Deep Research Output (persisted per requirement #3)
    research_output JSONB,  -- {findings[], sources[], citations[], confidence, research_images[]}
    research_images TEXT[],  -- URLs of images found during research
    
    -- Script Output (persisted per requirement #3)
    script_output JSONB,  -- {hook, scenes[], narration, punchline, viral_score}
    
    -- Image Generation Output (persisted per requirement #3)
    generated_images JSONB,  -- {image_urls[], metadata, generation_params}
    all_image_urls TEXT[],  -- Combined: user_ref + research_images + generated (for video)
    
    -- Video Output (persisted per requirement #3)
    video_output JSONB,  -- {video_url, duration, segments[], audio_url, subtitle_url}
    final_video_url TEXT,
    
    -- ========== HITL FEEDBACK TRACKING ==========
    hitl_feedback JSONB DEFAULT '[]',  -- [{gate, feedback, timestamp, regeneration_count}]
    current_hitl_gate VARCHAR(50),  -- Current gate awaiting approval (if manual mode)
    
    -- ========== TIMING & METRICS ==========
    created_at TIMESTAMPTZ DEFAULT now(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    phase_timings JSONB DEFAULT '{}',  -- {phase_name: {start, end, duration_ms}}
    total_cost_usd FLOAT DEFAULT 0,
    
    -- ========== ERROR TRACKING ==========
    error_message TEXT,
    error_phase VARCHAR(50),
    retry_count INT DEFAULT 0,
    
    -- ========== ANALYTICS ==========
    viral_score FLOAT,
    completion_rate_estimate FLOAT,
    
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- TOOLS REGISTRY: Dynamic tool/category management
-- ============================================================
CREATE TABLE tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_id VARCHAR(100) UNIQUE NOT NULL,
    tool_name VARCHAR(200) NOT NULL,
    category VARCHAR(50) NOT NULL CHECK (category IN (
        'surreal_realism', 'high_octane_anime', 'stylized_3d'
    )),
    description TEXT,
    capabilities JSONB,  -- {flow_visualization, sakuga_style, etc.}
    prompt_templates JSONB,  -- {script_template, image_template, video_template}
    example_outputs TEXT[],
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- MEDIA STORAGE: Track all images and videos with metadata
-- ============================================================
CREATE TABLE media (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID REFERENCES workflows(id) ON DELETE CASCADE,
    media_type VARCHAR(20) NOT NULL CHECK (media_type IN (
        'user_reference', 'research_image', 'generated_image', 
        'video_segment', 'final_video', 'audio', 'subtitle'
    )),
    storage_url TEXT NOT NULL,  -- Supabase Storage URL
    storage_path TEXT,  -- Path in bucket
    file_size_bytes BIGINT,
    mime_type VARCHAR(100),
    metadata JSONB,  -- {width, height, duration, generation_params, etc.}
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- CONFIG: Centralized dynamic configuration (per requirement #11)
-- ============================================================
CREATE TABLE config (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Insert default config values
INSERT INTO config (key, value, description) VALUES
('llm_models', '{"intent_tool_selector": "gemini-2.5-flash", "deep_research": "gemini-2.5-pro", "script_writer": "gemini-2.5-pro"}', 'LLM model configuration'),
('image_gen', '{"model_fast": "gemini-2.5-flash", "model_quality": "gemini-2.5-pro-image", "min_images": 1, "max_images": 5}', 'Image generation config'),
('video_gen', '{"model": "veo-3.1", "max_segment_duration": 8, "enable_audio": true}', 'Video generation config'),
('categories', '["surreal_realism", "high_octane_anime", "stylized_3d"]', 'Available categories'),
('hitl_gates', '["tool_selection", "deep_research", "script_generation", "image_generation", "video_generation"]', 'HITL gate points');
```

### 8.3 Key Indexes

```sql
-- Fast workflow lookups
CREATE INDEX idx_workflows_user_status ON workflows(user_id, status);
CREATE INDEX idx_workflows_created ON workflows(created_at DESC);
CREATE INDEX idx_workflows_hitl_gate ON workflows(current_hitl_gate) WHERE hitl_mode = 'manual';

-- Tool lookups
CREATE INDEX idx_tools_category ON tools(category, enabled);

-- Media lookups
CREATE INDEX idx_media_workflow ON media(workflow_id, media_type);
```

### 8.4 Row Level Security (RLS)

```sql
-- Users can only access their own workflows
ALTER TABLE workflows ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own workflows"
ON workflows FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can create workflows"
ON workflows FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own workflows"
ON workflows FOR UPDATE USING (auth.uid() = user_id);

-- Media inherits access from workflow
ALTER TABLE media ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own media"
ON media FOR SELECT USING (
    EXISTS (SELECT 1 FROM workflows WHERE workflows.id = media.workflow_id AND workflows.user_id = auth.uid())
);

-- Tools and config are public read
ALTER TABLE tools ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Tools are public" ON tools FOR SELECT USING (true);

ALTER TABLE config ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Config is public" ON config FOR SELECT USING (true);
```

---

## 9. Caching Strategy

### 9.1 Multi-Layer Cache Architecture

```
┌──────────────────────────────────────┐
│   Request comes in                   │
└──────────────┬───────────────────────┘
               │
               ▼
    ┌─────────────────────┐
    │  L1: Redis In-Memory│ (TTL: 1 hour)
    │  - Hot tools list   │
    │  - Session data     │
    │  - Recent scripts   │
    └─────────────┬───────┘
                  │ MISS
                  ▼
    ┌─────────────────────┐
    │  L2: Redis Semantic │ (TTL: 1-7 days)
    │  - Research results │
    │  - Script templates │
    │  - Similar queries  │
    └─────────────┬───────┘
                  │ MISS
                  ▼
    ┌─────────────────────┐
    │  L3: Supabase DB    │
    │  - Persistent state │
    │  - Long-term cache  │
    └─────────────┬───────┘
                  │ MISS
                  ▼
          ┌─────────────┐
          │  Fresh Gen  │
          │  (Expensive)│
          └──────┬──────┘
                 │
          ┌──────▼──────┐
          │ Store Result│
          │ In All Tiers│
          └─────────────┘
```

### 9.2 Cache Key Naming Convention

```python
class CacheKeys:
    """Standardized cache key naming"""
    
    # Research cache
    @staticmethod
    def research(topic: str, depth: str = "standard") -> str:
        topic_hash = hashlib.sha256(topic.lower().encode()).hexdigest()[:16]
        return f"raba:research:{topic_hash}:{depth}"
    
    # Script cache
    @staticmethod
    def script(research_hash: str, tool_id: str) -> str:
        return f"raba:script:{research_hash}:{tool_id}"
    
    # Image prompt cache
    @staticmethod
    def image_prompt(script_hash: str) -> str:
        return f"raba:image_prompt:{script_hash}"
    
    # Tools list (global)
    @staticmethod
    def tools_list() -> str:
        return "raba:tools:list"
    
    # User session
    @staticmethod
    def user_session(user_id: str) -> str:
        return f"raba:session:{user_id}"
    
    # Job status
    @staticmethod
    def job_status(job_id: str) -> str:
        return f"raba:job:{job_id}"
```

### 9.3 Cache Invalidation Strategy

```python
class CacheInvalidationManager:
    """Intelligent cache invalidation"""
    
    async def invalidate_on_new_tool(self, tool_id: str):
        """When new tool added, invalidate tools list"""
        await redis.delete(CacheKeys.tools_list())
    
    async def invalidate_stale_research(self, topic: str, days: int = 7):
        """Research older than N days gets invalidated"""
        key = CacheKeys.research(topic)
        created_at = await redis.hget(key, "created_at")
        if (datetime.now() - created_at).days > days:
            await redis.delete(key)
    
    async def cascade_invalidate(self, research_hash: str):
        """Invalidate scripts dependent on research"""
        pattern = f"raba:script:{research_hash}:*"
        keys = await redis.keys(pattern)
        for key in keys:
            await redis.delete(key)
```

---

## 10. Bottlenecks & Security

### 10.1 Identified Bottlenecks

| Bottleneck | Impact | Mitigation |
|-----------|--------|-----------|
| **Deep Research** | 15-60s latency | Caching (7-day TTL), parallel research with multiple agents (Phase 2) |
| **Video Generation** | 2-3m latency | Queue system with priority, batch processing, GPU resource pooling |
| **Image Generation** | 13-120s latency | Caching, concurrent requests, fallback to lower resolution |
| **LLM Token Usage** | High cost at scale | Prompt caching (semantic), tool filtering per agent, model quantization (Phase 2) |
| **Database Connections** | Connection pool exhaustion | Connection pooling (Supabase), async client, circuit breaker pattern |
| **API Rate Limits** | Veo 3.1, Nano Banana API quotas | Queue with exponential backoff, per-user rate limiting, fallback models |
| **Concurrent Job Processing** | Memory spike, GPU contention | Queue system (Celery/Bull), horizontal scaling, job prioritization |

### 10.2 Mitigation Details

#### A. Rate Limiting (FastAPI)

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter

@app.post("/api/v1/generate")
@limiter.limit("5/minute")  # 5 requests per minute per IP
async def generate_video(request: GenerateRequest):
    pass
```

#### B. Queue System for Video Generation

```python
# Using Celery + Redis for job queuing
from celery import Celery

celery_app = Celery('raba', broker='redis://localhost:6379')

@celery_app.task(bind=True, max_retries=3)
def generate_video_task(self, job_id: str):
    try:
        # Long-running video generation
        result = veo_client.generate(...)
        return result
    except Exception as exc:
        # Exponential backoff: 5m, 10m, 20m
        raise self.retry(exc=exc, countdown=5 * 60 * (2 ** self.request.retries))
```

#### C. Circuit Breaker for External APIs

```python
from pybreaker import CircuitBreaker

veo_breaker = CircuitBreaker(
    fail_max=5,  # Fail 5 times before breaking
    reset_timeout=60  # Wait 60s before retry
)

try:
    veo_breaker.call(veo_client.generate, prompt, params)
except Exception:
    # Use fallback model or cached result
    return fallback_video_generation()
```

### 10.3 Security Vulnerabilities & Protections

| Vulnerability | Severity | Mitigation |
|-------------|----------|-----------|
| **API Key Exposure** | Critical | Environment variables, AWS Secrets Manager, key rotation policy |
| **Prompt Injection** | High | Input sanitization, prompt validation, token limits |
| **Data Exfiltration** | High | Encryption at rest (Supabase), encryption in transit (HTTPS/TLS), access controls |
| **Unauthorized Tool Access** | High | Role-based access control (RBAC), API key scoping, audit logging |
| **SQL Injection** | High | Parameterized queries (ORM), Supabase RLS (Row Level Security) |
| **DDoS Attacks** | Medium | Rate limiting, WAF (cloud provider), IP whitelisting |
| **Malicious Script Execution** | Medium | Sandboxed LLM inference, output validation, content filtering |
| **Excessive API Costs** | Medium | Per-user quotas, cost tracking, alerts, model fallbacks |

### 10.4 Implementation: RLS (Row Level Security)

```sql
-- Only users can access their own jobs
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own jobs"
ON jobs FOR SELECT
USING (auth.uid() = user_id);

CREATE POLICY "Users can create jobs"
ON jobs FOR INSERT
WITH CHECK (auth.uid() = user_id);

-- Research cache is public (read-only)
ALTER TABLE research_cache ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Research cache is public"
ON research_cache FOR SELECT
USING (true);
```

### 10.5 Audit Logging

```python
class AuditLogger:
    """Track all sensitive operations"""
    
    async def log_tool_registration(self, tool_id: str, admin_id: str):
        await supabase.table("audit_logs").insert({
            "action": "TOOL_REGISTERED",
            "tool_id": tool_id,
            "admin_id": admin_id,
            "timestamp": datetime.now()
        })
    
    async def log_api_key_usage(self, key_prefix: str, api: str, cost: float):
        await supabase.table("audit_logs").insert({
            "action": "API_CALL",
            "api_service": api,
            "estimated_cost": cost,
            "timestamp": datetime.now()
        })
```



## 11 Monitoring & Observability

```python
# Prometheus Metrics
from prometheus_client import Counter, Histogram, Gauge

# Metrics definitions
generation_requests = Counter(
    'raba_generation_requests_total',
    'Total video generation requests',
    ['status', 'tool_category']
)

generation_latency = Histogram(
    'raba_generation_latency_seconds',
    'Video generation latency',
    buckets=(1, 10, 30, 60, 120, 180, 300)
)

active_jobs = Gauge(
    'raba_active_jobs',
    'Number of active generation jobs'
)

api_costs = Counter(
    'raba_api_costs_usd',
    'Accumulated API costs',
    ['provider']  # google, anthropic, etc.
)

# Usage in endpoint
@app.post("/api/v1/generate")
async def generate_video(request: GenerateRequest):
    with generation_latency.time():
        try:
            result = await orchestrator.run(request)
            generation_requests.labels(status='success', tool_category=result.tool_category).inc()
            return result
        except Exception as e:
            generation_requests.labels(status='error', tool_category='unknown').inc()
            raise
```

### 11.3 Logging Configuration

```python
import logging
from pythonjsonlogger import jsonlogger

# JSON logging for structured logs (ELK/CloudWatch compatible)
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)

logger = logging.getLogger()
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)

# Log all workflow phases
logger.info("workflow_started", extra={
    "job_id": job_id,
    "topic": topic,
    "phase": "intent_router",
    "timestamp": datetime.now().isoformat()
})
```

### 11.4 Performance Targets

| Metric | Target | Current (Baseline) |
|--------|--------|-------------------|
| Intent Router Latency | <5s | 2-4s |
| Tool Selection Latency | <3s | 1-2s |
| Deep Research Latency | <60s | 15-45s (cached) |
| Script Generation Latency | <45s | 30-40s |
| Image Generation Latency | <120s | 60-90s |
| Video Generation Latency | <3m | 2-3m |
| **Total E2E Latency** | <6m | 4-5m (avg) |
| API Cost per Video | <$1.50 | $0.80-1.20 |
| Video Completion Rate | >85% | 80-90% (estimate) |
| System Uptime | 99.5% | - |
| Cache Hit Rate | >60% | - |

---

## Summary: Design Decisions

### Why LangGraph?
- **Graph-based orchestration** enables complex non-linear workflows with clear visualization
- **Built-in state management** eliminates context passing boilerplate
- **Checkpointing** ensures recovery from failures without restarting entire workflow
- **Parallel execution** (fan-out/fan-in) for concurrent image + video generation

### Why Veo 3.1 + Nano Banana Pro?
- **Native audio generation** in Veo 3.1 ensures dialogue-video sync
- **Nano Banana Pro's 4K support** enables reference image quality
- **Structured prompt support** allows script-driven video generation
- **Cost efficiency** competitive with alternatives (~50% savings)

### Why Gemini Deep Research?
- **Autonomous multi-step research** with knowledge gap identification
- **Web grounding** ensures factual accuracy (critical for virality)
- **Iterative searching** produces comprehensive, cited reports
- **Background execution** supports long-running async operations

### Why Tool Repository Pattern?
- **Dynamic extensibility** from 2 to 100+ tools without core changes
- **Abstract base classes** enforce consistency across tools
- **Category-based selection** enables tool clustering and fallbacks
- **Registry pattern** decouples tool definition from orchestration logic

### Why Redis + Supabase?
- **Redis L1 caching** reduces expensive API calls (semantic + prompt caching)
- **Supabase async client** supports FastAPI's async/await model
- **Supabase RLS** provides row-level security out of the box
- **Both are serverless/managed** reducing operational burden

### Why Viral-First Design?
- **Hook archetypes** in script generation (FORTUNE TELLER, TEACHER, DISRUPTOR)
- **Pattern interrupt scheduling** every 3-5 seconds prevents attention decay
- **Completion rate prediction** validates script quality before generation
- **Emotional authenticity** optimized over visual flashiness

---

## Next Steps & Roadmap

### Phase 1 (Current)
- ✅ 2 initial tools (Impossible Simulations, Concept Combat)
- ✅ Intent router + tool selector agents
- ✅ Deep research + script writing with viral optimization
- ✅ Image + video generation pipeline
- ⬜ Local deployment, manual testing

### Phase 2 (Q1 2026)
- Add 8 more tools (10 total)
- Implement Celery queue system for async job processing
- Deploy to AWS/GCP with auto-scaling
- Add observability (Prometheus + Grafana)
- Implement semantic caching with vector embeddings

### Phase 3 (Q2 2026)
- Expand to 50+ tools
- Multi-agent research parallelization
- A/B testing framework for script variants
- Advanced analytics dashboard
- Enhanced HITL approval workflows

### Phase 4 (Q3 2026+)
- 100+ tools, specialized by niche
- Fine-tuned LLMs for script generation
- Real-time viral metric tracking
- Human-in-the-loop refinement workflows
- Enterprise deployment options

---

**Document Version**: 1.0  
**Last Updated**: January 2026  
**Owner**: Senior Software Architect  
**Confidentiality**: Internal Use