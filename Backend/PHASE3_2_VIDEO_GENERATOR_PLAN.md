# Phase 3.2: Video Generator Agent Implementation Plan

**Document Version**: 1.0  
**Created**: January 15, 2026  
**Phase**: 3.2 - Video Generator Agent  
**Dependencies**: Phase 3.1 (Image Generator) ✅ Complete

---

## 1. Overview

### 1.1 Objective

Implement the **Video Generator Agent** using **Veo 3.1** to produce final YouTube Shorts (8-25 seconds) with native audio from script, reference images, and workflow state.

### 1.2 Key References

| Document | Section | Purpose |
|----------|---------|---------|
| `Guides/SRS.md` | Section 3.6 (FR-6xx) | Functional requirements for video generation |
| `Guides/RABA_Architecture.md` | Section 2.7 | Video Generator Agent architecture |
| `Guides/rule.md` | Tech Stack & Agents | Veo 3.1 specifications |
| `Backend/Documentations/veo_doc.md` | Full doc | Veo 3.1 API reference |
| `Backend/Documentations/veo_prompting_guide.md` | Full doc | Prompt engineering for Veo |

### 1.3 Technical Stack

| Component | Technology | Reference |
|-----------|------------|-----------|
| **Video Model** | Veo 3.1 (`veo-3.1-generate-preview`) | veo_doc.md |
| **Fallback Model** | Veo 3.1 Fast (`veo-3.1-fast-generate-preview`) | veo_doc.md |
| **SDK** | `google-genai` Python SDK | Same as nano_banana.py |
| **Audio** | Native Veo 3.1 audio generation | veo_doc.md - Audio section |
| **Storage** | Supabase Storage | Existing pattern |

---

## 2. Requirements Analysis

### 2.1 Functional Requirements (from SRS.md Section 3.6)

| ID | Requirement | Priority | Implementation Notes |
|----|-------------|----------|---------------------|
| **FR-601** | Generate video using Veo 3.1 API | Must | Primary generation method |
| **FR-602** | Use all available reference images (user + research + generated) | Must | Max 3 reference images per Veo API limit |
| **FR-603** | For videos >8s, generate multiple segments with max 8s each | Must | Use video extension feature |
| **FR-604** | Maintain visual continuity between segments | Must | Use lastFrame technique for extensions |
| **FR-605** | Generate native audio if `enable_audio` is true | Must | Veo 3.1 native audio (always on) |
| **FR-606** | Generate subtitles if `enable_subtitles` is true | Should | Post-processing with Gemini |
| **FR-607** | Support 9:16 and 16:9 aspect ratios | Must | API parameter |
| **FR-608** | Support 720p and 1080p resolutions | Must | 1080p only for 8s duration |
| **FR-609** | Persist video output to `workflows.video_output` | Must | Database update |
| **FR-610** | Upload final video to Supabase Storage | Must | Storage service |
| **FR-611** | HITL Gate 5 pause in manual mode | Must | Workflow interrupt |
| **FR-612** | Regeneration with user feedback | Should | HITL feedback processing |

### 2.2 Veo 3.1 API Constraints (from veo_doc.md)

| Constraint | Value | Impact |
|------------|-------|--------|
| **Max segment duration** | 8 seconds | Multi-segment for >8s videos |
| **Max reference images** | 3 images | **CRITICAL: Always exactly 3 images to Veo** |
| **Resolutions** | 720p, 1080p (8s only for 1080p) | Resolution planning |
| **Aspect ratios** | 16:9, 9:16 | Both supported |
| **Audio** | Native, always generated | No separate audio pipeline |
| **Extension limit** | Up to 20 times, max 141s input | Supports our 8-25s range |
| **Request latency** | 11s min, 6min max | Polling required |
| **Video retention** | 2 days | Must download immediately |

### 2.3 Video Duration Planning (from RABA_Architecture.md:489-521)

```
Duration → Segments Calculation:
├─ 8s  → 1 segment (8s)
├─ 12s → 2 segments (8s + ~7s extension = 15s, trimmed to 12s)
├─ 18s → 3 segments (8s + 7s + 7s = 22s, trimmed to 18s)
├─ 25s → 4 segments (8s + 7s + 7s + 7s = 29s, trimmed to 25s)
```

**Strategy**: Generate first 8s segment with reference images, then extend iteratively.

### 2.4 Seamless Video Extension Strategy (CRITICAL)

**Key Insight from Research**: Veo 3.1's extension feature **outputs a SINGLE combined video**, not separate segments. No manual merging is required!

**How Extension Works** (from veo_doc.md + web research):
```
┌─────────────────────────────────────────────────────────────────────────┐
│              VEO 3.1 SEAMLESS EXTENSION MECHANISM                       │
└─────────────────────────────────────────────────────────────────────────┘

1. Initial Generation (8s):
   ├─ Uses up to 3 reference images
   ├─ Output: Single 8s video with audio
   └─ Resolution: 720p or 1080p (8s only for 1080p)

2. Extension Hop (~7s each):
   ├─ Input: Previous Veo-generated video object (NOT file)
   ├─ Conditioning: Last second (~24 frames) analyzed for continuity
   ├─ Output: SINGLE combined video (input + extension)
   ├─ Audio: Native audio continuity preserved
   └─ Resolution: Must be 720p for extension

3. Chaining Extensions:
   ├─ Each extension returns combined video
   ├─ Next extension uses that combined video as input
   ├─ Maximum: 20 extensions, 148s total output
   └─ Result: ONE seamless video file
```

**Why This Is Seamless**:
- Extension uses "alignment embeddings" on last-second frames
- Pixel-space similarity matching for visual continuity
- Native audio blending between segments
- Character/style consistency from reference conditioning
- >95% visual continuity reported across hops

**Resolution Strategy**:
```
For videos > 8s:
├─ Start at 720p (required for extension compatibility)
├─ All extensions at 720p
└─ Final video remains 720p (consistent quality throughout)

For videos ≤ 8s:
├─ Can use 1080p directly
└─ No extension needed
```

### 2.5 Reference Image Constraints (UPDATED)

**CRITICAL RULE**: Maximum 3 images reach Veo, regardless of source.

| Source | Priority | Max Count |
|--------|----------|----------|
| User-provided reference | 1 (Highest) | 1 |
| Generated images | 2 | Up to 3 |
| Research images | 3 (Lowest) | 0-2 |

**Selection Logic**:
```python
def select_reference_images(user_ref, generated, research, max_count=3):
    selected = []
    
    # Priority 1: User reference (if exists)
    if user_ref:
        selected.append(user_ref)
    
    # Priority 2: Generated images (first, middle, last for coverage)
    remaining = max_count - len(selected)
    if generated and remaining > 0:
        if len(generated) == 1:
            selected.append(generated[0])
        elif len(generated) == 2:
            selected.extend(generated[:remaining])
        else:  # 3 generated images
            # Select first + last for scene coverage
            indices = [0, len(generated)-1]
            for idx in indices[:remaining]:
                selected.append(generated[idx])
    
    # Priority 3: Research images (only if slots remain)
    remaining = max_count - len(selected)
    if research and remaining > 0:
        selected.extend(research[:remaining])
    
    return selected[:3]  # Always max 3
```

**Image Generator Update Required**:
- Change `MAX_IMAGES` from 5 to 3 in `app/agents/image_generator.py`
- Update `calculate_images_to_generate()` to cap at 3

---

## 3. Architecture Design

### 3.1 Component Structure

```
Backend/app/
├── agents/
│   └── video_generator.py          # NEW: Video Generator Agent
├── services/
│   └── veo.py                       # NEW: Veo 3.1 API service
├── models/
│   └── video.py                     # NEW: Video Pydantic models
└── graph/
    └── nodes.py                     # UPDATE: Add video_generator_node
```

### 3.2 Class Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    VideoGeneratorAgent                           │
├─────────────────────────────────────────────────────────────────┤
│ - veo_service: VeoService                                        │
│ - supabase: SupabaseClient                                       │
│ - prompt_builder: VideoPromptBuilder                             │
├─────────────────────────────────────────────────────────────────┤
│ + run(state: VideoGenerationState) -> dict[str, Any]            │
│ - _plan_video_segments(duration: int) -> list[VideoSegment]     │
│ - _select_reference_images(all_images: list, max: int) -> list  │
│ - _build_video_prompt(script, tool_category, segment) -> str    │
│ - _generate_initial_segment(prompt, images, config) -> Video    │
│ - _extend_video(video, prompt, segment) -> Video                │
│ - _upload_to_storage(video_bytes, path) -> str                  │
│ - _persist_to_database(workflow_id, output) -> None             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ uses
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         VeoService                               │
├─────────────────────────────────────────────────────────────────┤
│ - client: genai.Client                                           │
├─────────────────────────────────────────────────────────────────┤
│ + generate_video(prompt, config, images?) -> GeneratedVideo     │
│ + extend_video(video, prompt, config) -> GeneratedVideo         │
│ + generate_with_frames(prompt, first, last, config) -> Video    │
│ - _poll_operation(operation) -> GeneratedVideo                  │
│ - _download_video(video) -> bytes                               │
└─────────────────────────────────────────────────────────────────┘
```

### 3.3 Data Flow

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        VIDEO GENERATOR DATA FLOW                          │
└──────────────────────────────────────────────────────────────────────────┘

Input State:
├── script_output (from Script Writer)
│   ├── hook
│   ├── scenes[]
│   └── call_to_action
├── all_images[] (from Image Generator - max use 3)
├── duration_seconds (8-25)
├── aspect_ratio ("9:16" or "16:9")
├── resolution ("720p" or "1080p")
├── enable_audio (boolean)
├── tool_category (for prompt style)
└── topic (for context)

Processing:
├── 1. Determine resolution (720p if >8s, else can be 1080p)
├── 2. Select EXACTLY 3 reference images (user > generated > research)
├── 3. Build Veo prompt from script + tool vocabulary
├── 4. Generate initial 8s segment with 3 reference images
├── 5. For each extension (if duration > 8s):
│   ├── Build continuation prompt for next scenes
│   ├── Call extend_video with video OBJECT (not file)
│   └── Receive SINGLE combined video (seamless)
├── 6. Download final SINGLE video (already merged by Veo)
├── 7. Trim to exact target duration (FFmpeg if needed)
├── 8. Upload to Supabase Storage
└── 9. Persist metadata to database

Output State Update:
├── video_output (JSONB with full metadata)
├── final_video_url (public URL)
├── video_metadata (duration, segments, quality scores)
└── phase_timestamps.video_generator_completed
```

---

## 4. Implementation Steps

### Step 0: Update Image Generator (PREREQUISITE)

**File**: `app/agents/image_generator.py`

**Changes Required**:
```python
# Current:
MIN_IMAGES = 1
MAX_IMAGES = 5

# Updated:
MIN_IMAGES = 1
MAX_IMAGES = 3  # Veo 3.1 max reference images
```

**Update `calculate_images_to_generate()` function**:
- Cap output at 3 instead of 5
- Adjust logic for external image accounting

**Rationale**: 
- Veo 3.1 accepts maximum 3 reference images
- Generating more than 3 wastes resources and time
- Ensures all generated images can be used by Video Generator

---

### Step 1: Create Video Models (`app/models/video.py`)

**Purpose**: Define Pydantic models for video generation

**Models to Create**:
- `VideoModel` (Enum): veo-3.1-generate-preview, veo-3.1-fast-generate-preview
- `VideoAspectRatio` (Enum): LANDSCAPE_16_9, PORTRAIT_9_16
- `VideoResolution` (Enum): RES_720P, RES_1080P
- `VideoSegment` (BaseModel): segment_num, duration, start_time, is_extension
- `VideoGenerationConfig` (BaseModel): model, aspect_ratio, resolution, duration, enable_audio, negative_prompt
- `GeneratedVideo` (BaseModel): url, storage_path, duration, resolution, aspect_ratio, segments, generation_time_ms, audio_included
- `VideoGeneratorOutput` (BaseModel): video, segments, total_duration, total_generation_time_ms

**Reference**: Follow pattern from `app/models/image.py`

---

### Step 2: Create Veo Service (`app/services/veo.py`)

**Purpose**: Wrap Veo 3.1 API interactions

**Key Methods**:

#### 2.1 `generate_video(prompt, config, reference_images?) -> GeneratedVideo`
```
Reference: veo_doc.md - Text to video generation

API Call:
- model: "veo-3.1-generate-preview"
- prompt: str (from script)
- config: GenerateVideosConfig
  - aspect_ratio: "16:9" or "9:16"
  - resolution: "720p" or "1080p"
  - duration_seconds: 8 (max per segment)
  - negative_prompt: optional
  - reference_images: up to 3 VideoGenerationReferenceImage objects
```

#### 2.2 `generate_with_image(prompt, first_frame, config) -> GeneratedVideo`
```
Reference: veo_doc.md - Image to video generation

Use when: We have strong reference images from Image Generator
API Call:
- model: "veo-3.1-generate-preview"
- prompt: str
- image: first_frame Image object
- config: GenerateVideosConfig
```

#### 2.3 `extend_video(video, prompt, config) -> GeneratedVideo`
```
Reference: veo_doc.md - Extending Veo videos

Use when: Duration > 8s requires multiple segments
API Call:
- model: "veo-3.1-generate-preview"
- video: Previous generation's video OBJECT (operation.response.generated_videos[0].video)
- prompt: Continuation prompt describing next scene
- config: GenerateVideosConfig (resolution must be 720p for extension)

CRITICAL SEAMLESS EXTENSION DETAILS:
- Output is SINGLE combined video (input + extension)
- Extension conditions on LAST SECOND (~24 frames) for seamless transition
- Audio blends naturally between segments
- No manual merging required!
- Each hop adds ~7 seconds
- Max input video: 141 seconds
- Max output video: 148 seconds

Continuation Prompt Best Practices:
- Reference what's happening at end of current video
- Describe smooth transition to next action
- Maintain consistent style keywords
- Include audio continuity cues
```

#### 2.4 `_poll_operation(operation) -> GeneratedVideo`
```
Reference: veo_doc.md - Handling asynchronous operations

Poll every 10 seconds until operation.done == True
Timeout: 6 minutes max (from Veo docs)
Return: operation.response.generated_videos[0]
```

#### 2.5 `_download_video(video) -> bytes`
```
Reference: veo_doc.md - Download generated video

Call: client.files.download(file=video.video)
Return: video bytes for storage upload
```

**Error Handling**:
- Retry with exponential backoff (3 attempts)
- Fallback to `veo-3.1-fast-generate-preview` on persistent failures
- Fallback to 720p if 1080p fails

---

### Step 3: Create Video Generator Agent (`app/agents/video_generator.py`)

**Purpose**: LangGraph agent node for video generation

#### 3.1 Tool-Specific Video Vocabulary

```python
TOOL_VIDEO_VOCABULARY = {
    "surreal_realism": {
        "style_keywords": [
            "photorealistic", "cinematic", "hyperreal",
            "flowing liquid-glass aesthetic", "impossible physics",
            "dreamlike atmosphere"
        ],
        "camera_movements": [
            "slow dolly", "smooth tracking", "floating perspective",
            "subtle push-in", "cinematic crane"
        ],
        "audio_cues": [
            "ambient atmospheric sounds", "subtle ethereal music",
            "gentle whooshing", "resonant bass tones"
        ]
    },
    "high_octane_anime": {
        "style_keywords": [
            "Sakuga-style animation", "dynamic action",
            "ink-splash effects", "speed lines", "impact frames"
        ],
        "camera_movements": [
            "rapid cuts", "dynamic tracking", "whip pan",
            "dramatic zoom", "rotating camera"
        ],
        "audio_cues": [
            "intense orchestral", "dramatic sound effects",
            "swooshing impacts", "epic crescendo"
        ]
    },
    "stylized_3d": {
        "style_keywords": [
            "clean 3D render", "isometric perspective",
            "miniature diorama", "tilt-shift effect", "stylized materials"
        ],
        "camera_movements": [
            "orbital rotation", "smooth dolly", "subtle tilt-shift",
            "steady pan", "gentle zoom"
        ],
        "audio_cues": [
            "clean electronic", "subtle clicks and beeps",
            "ambient informative tone", "gentle chimes"
        ]
    }
}
```

#### 3.2 `_plan_video_segments(duration_seconds: int) -> list[VideoSegment]`

```
Reference: RABA_Architecture.md:489-521

Logic:
├── MAX_SEGMENT_DURATION = 8
├── EXTENSION_DURATION = 7 (approximate)
├── First segment: 8s with reference images
├── Subsequent segments: extensions (~7s each)
├── Final segment: remainder

Example for 18s:
├── Segment 0: 0-8s (initial, uses reference images)
├── Segment 1: 8-15s (extension)
└── Segment 2: 15-18s (final extension, ~3s)
```

#### 3.3 `_select_reference_images(all_images: list, max_count: int = 3) -> list`

```
Reference: veo_doc.md - Using reference images (max 3)

CRITICAL: Always select exactly 3 images (or fewer if not available)

Selection Priority:
1. User-provided reference image (if exists) - HIGHEST
2. Generated images - First and Last for scene coverage
3. Research images - Only if slots remain

For 9:16 aspect ratio:
- Reference images work for both 16:9 and 9:16
- Alternative: Use image-to-video with first_frame for stronger adherence
```

#### 3.4 `_build_video_prompt(script, tool_category, segment_info) -> str`

```
Reference: veo_prompting_guide.md - Anatomy of a Veo prompt

Prompt Structure:
├── [STYLE] Tool-specific visual style
├── [SUBJECT] Character/object descriptions from script
├── [ACTION] Scene actions with timing
├── [CAMERA] Camera movements for segment
├── [AUDIO] Dialogue and sound effect cues
├── [AMBIANCE] Mood, lighting, atmosphere
└── [COMPOSITION] Shot framing details

Audio Prompting (veo_doc.md - Prompting for audio):
├── Dialogue: Use quotes for speech "Text here"
├── Sound Effects: Explicit descriptions
└── Ambient: Environment soundscape

Example:
"[REFERENCE IMAGES PROVIDED]
A cinematic, photorealistic scene in flowing liquid-glass style.

[00:00-00:02] HOOK: {script.hook.visual_direction}
Camera slowly dollies in on {subject}.
{character} says: "{dialogue}"

[00:02-00:05] {scene_description}
{camera_movement}
Sound: {audio_cues}

[00:05-00:08] {next_scene}
Mood: {mood}, Lighting: {lighting}

CRITICAL: Synchronize dialogue exactly with script timing.
Maintain visual consistency with reference images throughout.
No text overlays or watermarks."
```

#### 3.5 `run(state: VideoGenerationState) -> dict[str, Any]`

Main agent execution flow:
```
1. Extract inputs from state
2. Determine resolution strategy:
   - If duration <= 8s: Can use 1080p
   - If duration > 8s: Must use 720p (extension requirement)
3. Select reference images (EXACTLY 3, priority: user > generated > research)
4. Build initial segment prompt from script (hook + first scenes)
5. Generate first segment (8s) with reference images
   - Store video OBJECT (not just URL) for extension
6. For each extension needed:
   a. Build continuation prompt (reference end of current video)
   b. Call extend_video with previous video OBJECT
   c. Receive COMBINED video (seamless, single file)
   d. Update video object for next extension
7. Download final SINGLE video (already seamlessly combined)
8. Trim to exact target duration if needed (FFmpeg)
9. Upload to Supabase Storage
10. Persist to database
11. Return state update with final_video_url

CRITICAL: Never manually merge videos - Veo does this automatically!
```

---

### Step 4: Create HITL Feedback Models

**Purpose**: Support HITL Gate 5 for video approval

**Location**: `app/models/video.py`

```python
class HITLVideoAction(Enum):
    APPROVE = "approve"
    REGENERATE = "regenerate"

class HITLVideoFeedback(BaseModel):
    action: HITLVideoAction
    feedback: Optional[str] = None  # Regeneration feedback
    pacing_feedback: Optional[str] = None
    transition_feedback: Optional[str] = None
    audio_feedback: Optional[str] = None
```

**Reference**: RABA_Architecture.md:989-1055 (HITL Gate Implementation)

---

### Step 5: Update Services __init__.py

**File**: `app/services/__init__.py`

Add exports:
```python
from app.services.veo import VeoService, get_veo_service
```

---

### Step 6: Update Agents __init__.py

**File**: `app/agents/__init__.py`

Add exports:
```python
from app.agents.video_generator import (
    VideoGeneratorAgent,
    video_generator_node,
    build_video_prompt,
)
```

---

### Step 7: Update Graph Nodes

**File**: `app/graph/nodes.py`

Add video generator node to workflow graph.

---

### Step 8: Create Unit Tests

**File**: `tests/test_agents/test_video_generator.py`

Test cases:
- `test_plan_video_segments_8s` - Single segment
- `test_plan_video_segments_18s` - Multiple segments
- `test_plan_video_segments_25s` - Max duration
- `test_select_reference_images_priority` - Image selection logic
- `test_build_video_prompt_surreal` - Prompt building for surreal style
- `test_build_video_prompt_anime` - Prompt building for anime style
- `test_video_generator_full_flow` - Integration test

---

## 5. Prompt Engineering Guidelines

### 5.1 Veo Prompt Best Practices (from veo_prompting_guide.md)

| Element | Description | Example |
|---------|-------------|---------|
| **Subject** | Who/what the video focuses on | "a seasoned detective", "flowing liquid-glass orb" |
| **Action** | What is happening | "walks with hunched shoulders", "unfurls its petals" |
| **Context** | Where and when | "in a misty forest at dawn", "neon-lit cyberpunk alley" |
| **Camera Angle** | Shot perspective | "eye-level shot", "low-angle tracking", "bird's-eye view" |
| **Camera Movement** | How camera moves | "slow dolly in", "smooth pan left", "orbital rotation" |
| **Lens Effects** | Optical style | "shallow depth of field", "wide-angle lens" |
| **Style** | Artistic direction | "cinematic film look", "Japanese anime style" |
| **Ambiance** | Mood and lighting | "warm golden hour", "cool blue tones", "dramatic backlighting" |
| **Audio** | Sound cues | dialogue in quotes, "ambient city sounds", "dramatic orchestral swell" |

### 5.2 Audio Prompting (from veo_doc.md)

```
Dialogue: Use quotes for specific speech
  Example: He murmurs, "This must be the key."

Sound Effects: Explicit description
  Example: tires screeching loudly, engine roaring

Ambient Noise: Environmental soundscape
  Example: A faint, eerie hum resonates in the background
```

### 5.3 Negative Prompts

```
DO NOT use: "no", "don't", "avoid"
DO use: Describe what you don't want

Example:
✗ "no text, don't add watermarks"
✓ "text overlays, watermarks, logos, UI elements"
```

---

## 6. Error Handling Strategy

### 6.1 Error Types and Mitigations

| Error | Cause | Mitigation |
|-------|-------|------------|
| **Generation Timeout** | Veo overloaded | Retry with exponential backoff, fallback to Fast model |
| **Safety Filter Block** | Content flagged | Regenerate with safer prompt, log for review |
| **Audio Processing Error** | Audio generation issue | Video still usable, log warning |
| **Reference Image Incompatible** | Wrong aspect ratio | Use image-to-video instead of reference_images |
| **Extension Failure** | Segment continuity issue | Retry with modified continuation prompt |
| **Resolution Downgrade** | 1080p unavailable | Fallback to 720p |

### 6.2 Fallback Chain

```
Primary: veo-3.1-generate-preview @ 1080p
    ↓ (on failure)
Fallback 1: veo-3.1-generate-preview @ 720p
    ↓ (on failure)
Fallback 2: veo-3.1-fast-generate-preview @ 720p
    ↓ (on failure)
Error: Return error state, queue for manual review
```

---

## 7. Database Persistence

### 7.1 Workflow Table Update

```sql
-- workflows.video_output JSONB structure
{
    "video_url": "https://storage.supabase.co/...",
    "storage_path": "videos/{workflow_id}/final.mp4",
    "duration_seconds": 18.0,
    "resolution": "1080p",
    "aspect_ratio": "9:16",
    "segments": [
        {"segment_num": 0, "duration": 8, "type": "initial"},
        {"segment_num": 1, "duration": 7, "type": "extension"},
        {"segment_num": 2, "duration": 3, "type": "extension"}
    ],
    "audio_included": true,
    "model_used": "veo-3.1-generate-preview",
    "generation_time_ms": 180000,
    "total_cost_usd": 0.80,
    "quality_scores": {
        "visual_consistency": 0.95,
        "audio_sync": 0.90
    }
}
```

### 7.2 Media Table Entry

```sql
INSERT INTO media (
    workflow_id,
    media_type,
    storage_url,
    storage_path,
    file_size_bytes,
    mime_type,
    metadata
) VALUES (
    '{workflow_id}',
    'final_video',
    '{public_url}',
    'videos/{workflow_id}/final.mp4',
    {file_size},
    'video/mp4',
    '{segments, duration, model, etc}'
);
```

---

## 8. Testing Strategy

### 8.1 Unit Tests

| Test | Purpose |
|------|---------|
| `test_segment_planning` | Verify segment calculation for various durations |
| `test_image_selection` | Verify priority-based image selection |
| `test_prompt_building` | Verify prompt structure for each tool category |
| `test_extension_logic` | Verify video extension sequencing |

### 8.2 Integration Tests

| Test | Purpose |
|------|---------|
| `test_veo_service_generation` | Test actual Veo API call (mocked) |
| `test_full_workflow` | Test agent with mock state |
| `test_storage_upload` | Test Supabase storage integration |
| `test_hitl_gate_5` | Test HITL interrupt in manual mode |

### 8.3 E2E Test

```
Given: Complete workflow state after Image Generator
When: Video Generator agent runs
Then: 
  - Video is generated with correct duration
  - Video is uploaded to storage
  - Database is updated with video_output
  - State includes final_video_url
```

---

## 9. Implementation Order

| Order | Task | Estimated Time | Dependencies |
|-------|------|----------------|--------------|
| 0 | Update `app/agents/image_generator.py` (MAX_IMAGES=3) | 15 min | None |
| 1 | Create `app/models/video.py` | 1 hour | None |
| 2 | Create `app/services/veo.py` | 2 hours | Step 1 |
| 3 | Create `app/agents/video_generator.py` | 3 hours | Steps 1, 2 |
| 4 | Update `app/services/__init__.py` | 10 min | Step 2 |
| 5 | Update `app/agents/__init__.py` | 10 min | Step 3 |
| 6 | Update `app/graph/nodes.py` | 30 min | Step 3 |
| 7 | Create unit tests | 1.5 hours | Steps 0-3 |
| 8 | Integration testing | 1 hour | All above |

**Total Estimated Time**: ~9.5 hours

---

## 10. Success Criteria

| Criteria | Measurement |
|----------|-------------|
| **Functional** | Video generates successfully for 8s, 18s, 25s durations |
| **Quality** | Video maintains visual consistency with reference images |
| **Audio** | Native audio generates with dialogue sync |
| **Performance** | Generation completes within 3 minutes for 18s video |
| **Storage** | Video uploads to Supabase Storage successfully |
| **Persistence** | All metadata saved to workflows table |
| **HITL** | Gate 5 pauses correctly in manual mode |
| **Fallback** | Graceful degradation on errors |

---

## 11. Open Questions / Decisions Needed

1. **Subtitle Generation**: Should we implement FR-606 (subtitle generation) in this phase or defer?
   - Recommendation: Defer to Phase 3.3, focus on core video generation

2. **Quality Scoring**: Implement automated quality scores or defer?
   - Recommendation: Add placeholder, implement scoring in Phase 3.3

3. **Cost Tracking**: Track per-video generation costs?
   - Recommendation: Yes, add to video_output metadata

---

## Appendix A: Veo 3.1 API Quick Reference

```python
# Text-to-Video
operation = client.models.generate_videos(
    model="veo-3.1-generate-preview",
    prompt=prompt,
    config=types.GenerateVideosConfig(
        aspect_ratio="9:16",
        resolution="1080p",
        duration_seconds=8,
        negative_prompt="text, watermarks, logos"
    )
)

# Image-to-Video (first frame)
operation = client.models.generate_videos(
    model="veo-3.1-generate-preview",
    prompt=prompt,
    image=image_object,  # First frame
    config=types.GenerateVideosConfig(...)
)

# With Reference Images (max 3, 16:9 only)
operation = client.models.generate_videos(
    model="veo-3.1-generate-preview",
    prompt=prompt,
    config=types.GenerateVideosConfig(
        reference_images=[
            types.VideoGenerationReferenceImage(image=img1, reference_type="asset"),
            types.VideoGenerationReferenceImage(image=img2, reference_type="asset"),
            types.VideoGenerationReferenceImage(image=img3, reference_type="asset"),
        ]
    )
)

# Video Extension
operation = client.models.generate_videos(
    model="veo-3.1-generate-preview",
    video=previous_video,  # From previous generation
    prompt=continuation_prompt,
    config=types.GenerateVideosConfig(
        resolution="720p"  # Must be 720p for extension
    )
)

# Polling
while not operation.done:
    time.sleep(10)
    operation = client.operations.get(operation)

# Download
client.files.download(file=operation.response.generated_videos[0].video)
video.video.save("output.mp4")
```

---

## Appendix B: State Schema Updates

```python
# VideoGenerationState additions for video_generator
class VideoGenerationState(TypedDict):
    # ... existing fields ...
    
    # Video Generation (new)
    video_output: dict  # JSONB with full video metadata
    final_video_url: str  # Public URL to final video
    video_segments: list[dict]  # Segment breakdown
    video_generation_time_ms: int  # Total generation time
    
    # HITL Gate 5
    hitl_video_approved: bool
    hitl_video_feedback: Optional[dict]
```

---

**Document Status**: READY FOR REVIEW

**Next Steps After Approval**:
1. Begin implementation following Step order (Section 9)
2. Create files in order: models → services → agents
3. Run tests after each major component
4. Integration test full workflow

---

*This plan follows the patterns established in Phase 3.1 (Image Generator) and adheres to all specifications in SRS.md, RABA_Architecture.md, and rule.md.*

---

## Summary of Key Updates (Based on User Feedback)

### 1. Reference Image Constraint
- **Image Generator MAX_IMAGES**: Changed from 5 → **3**
- **Veo input**: Always exactly **3 reference images** (regardless of source)
- **Priority**: User-provided > Generated > Research

### 2. Seamless Multi-Segment Video Strategy
- **NO manual merging required** - Veo extension outputs SINGLE combined video
- Extension conditions on **last second (~24 frames)** for seamless transitions
- **Audio continuity** is native and automatic
- **>95% visual continuity** across extension hops

### 3. Resolution Strategy for Extensions
- Videos **> 8s**: Must use **720p** (extension requirement)
- Videos **≤ 8s**: Can use **1080p** directly
- Consistent 720p throughout for extended videos

### 4. Veo 3.1 Model Variants
| Model | Use Case | Generation Time |
|-------|----------|-----------------|
| `veo-3.1-generate-preview` | Final high-end cinematic output | ~3-5 minutes |
| `veo-3.1-fast-generate-preview` | Drafting, storyboarding, fallback | ~1-2 minutes |
