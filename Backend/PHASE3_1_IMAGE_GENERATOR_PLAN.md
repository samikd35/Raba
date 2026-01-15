# Phase 3.1: Image Generator Agent - Implementation Plan

**Version**: 1.0  
**Created**: January 15, 2026  
**Depends On**: Phase 2.4 (Script Generator Agent) ✅ Completed  
**Est. Duration**: 1.5-2 days

---

## Overview

The Image Generator Agent creates 1-5 reference images using **Nano Banana Pro** (gemini-3-pro-image-preview) or **Nano Banana** (gemini-2.5-flash-image) based on the script's scene descriptions. These images serve as visual references for the Video Generator Agent.

### Key References
- `@Guides/RABA_Architecture.md:421-482` - Image Generator Agent architecture
- `@Guides/SRS.md:114-128` - Functional requirements FR-5xx
- `@Guides/rule.md:53` - Image Generator uses Nano Banana Pro
- `@Backend/Documentations/nanao_banana_doc.md` - Nano Banana API documentation
- `@Backend/Documentations/nano_prompt_guide.md` - Image generation prompting best practices

---

## Architecture Summary

```
                    ┌──────────────────────────────┐
                    │     INPUT FROM STATE          │
                    │ - script_output (scenes[])    │
                    │ - selected_tool (style specs) │
                    │ - user_reference_image_url    │
                    │ - research_images[]           │
                    │ - aspect_ratio, resolution    │
                    └──────────────┬───────────────┘
                                   │
                    ┌──────────────▼───────────────┐
                    │   IMAGE GENERATOR AGENT      │
                    │   (Nano Banana Pro/Flash)    │
                    ├──────────────────────────────┤
                    │ 1. Calculate images needed   │
                    │ 2. Build prompts from scenes │
                    │ 3. Generate images (1-5)     │
                    │ 4. Upload to Supabase        │
                    │ 5. Combine all image sources │
                    └──────────────┬───────────────┘
                                   │
                    ┌──────────────▼───────────────┐
                    │     OUTPUT TO STATE          │
                    │ - generated_images[]         │
                    │ - all_images[]               │
                    │ - image_metadata[]           │
                    └──────────────────────────────┘
```

---

## Functional Requirements (from SRS.md FR-5xx)

| ID | Requirement | Priority |
|----|-------------|----------|
| **FR-501** | Generate 1-5 reference images using Nano Banana Pro | Must |
| **FR-502** | Reduce generated count if user provided reference image | Must |
| **FR-503** | Reduce generated count if research found relevant images | Must |
| **FR-504** | Always generate at least 1 image | Must |
| **FR-505** | Never generate more than 5 images | Must |
| **FR-506** | Upload generated images to Supabase Storage | Must |
| **FR-507** | Persist image metadata to `workflows.generated_images` | Must |
| **FR-508** | HITL Gate 4: Pause for user review in manual mode | Must |
| **FR-509** | At Gate 4: User can add additional reference images | Should |
| **FR-510** | At Gate 4: User can provide feedback for regeneration | Should |

---

## Implementation Tasks

### 3.1.1 Create Image Models (`app/models/image.py`)

**Estimated Time**: 30 minutes

**Models to Create**:

| Model | Description | Key Fields |
|-------|-------------|------------|
| `ImageGenerationConfig` | Config for image generation | model, aspect_ratio, resolution, style_keywords |
| `GeneratedImage` | Single generated image metadata | url, prompt, scene_number, generation_time_ms, model_used |
| `ImageGeneratorOutput` | Complete output from agent | generated_images[], all_images[], total_generation_time_ms |

**Reference Schema** (from `@Guides/RABA_Architecture.md:463-468`):
```python
class ImageGeneratorOutput(BaseModel):
    generated_images: List[GeneratedImage]
    all_images: List[str]  # user_ref + research + generated
    image_metadata: List[dict]
    total_generation_time_ms: int
```

---

### 3.1.2 Implement Image Count Calculator (`app/agents/image_generator.py`)

**Estimated Time**: 30 minutes

**Logic** (from `@Guides/RABA_Architecture.md:431-446`):
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

**Validation Rules**:
- Minimum: 1 image (FR-504)
- Maximum: 5 images (FR-505)
- Reduce count based on external images (FR-502, FR-503)

---

### 3.1.3 Implement Prompt Builder (`app/agents/image_generator.py`)

**Estimated Time**: 1 hour

**Description**: Build image generation prompts from scene descriptions using tool-specific visual vocabulary.

**Prompt Structure** (from `@Backend/Documentations/nano_prompt_guide.md:4332-4343`):
- **Be Hyper-Specific**: Rich sensory detail from scene descriptions
- **Provide Context and Intent**: Include tool category aesthetic
- **Use Step-by-Step Instructions**: For complex scenes
- **Control the Camera**: Use photographic/cinematic language

**Tool-Specific Vocabulary** (from `@Guides/RABA_Architecture.md:793-852`):

| Tool Category | Visual Vocabulary |
|---------------|-------------------|
| `surreal_realism` | "flowing liquid-glass", "photorealistic grounding", "impossible physics" |
| `high_octane_anime` | "Sakuga-style", "ink-splashes", "elemental explosions", "dynamic motion lines" |
| `stylized_3d` | "miniature landscape", "data diorama", "clean 3D aesthetic", "isometric view" |

**Prompt Template**:
```
[SCENE CONTEXT]
Scene {scene_number} of {total_scenes} for a {duration}s YouTube Short.
Topic: {topic}

[VISUAL DESCRIPTION]
{scene.description}

[STYLE REQUIREMENTS]
Category: {tool_category}
Visual Style: {tool_visual_vocabulary}
Mood: {scene.mood}
Lighting: {scene.lighting}

[CAMERA DIRECTION]
{scene.camera_direction}

[TECHNICAL SPECS]
Aspect Ratio: {aspect_ratio}
Resolution: {resolution}
```

---

### 3.1.4 Implement Nano Banana Integration (`app/services/nano_banana.py`)

**Estimated Time**: 1.5 hours

**Description**: Create service for Nano Banana Pro/Flash image generation API.

**Model Selection** (from `@Backend/Documentations/nano_prompt_guide.md:4584-4591`):

| Model | Use Case | Resolution | Latency |
|-------|----------|------------|---------|
| `gemini-3-pro-image-preview` (Nano Banana Pro) | Complex scenes, professional quality | Up to 4K | Higher |
| `gemini-2.5-flash-image` (Nano Banana) | Simple scenes, speed priority | 1024px | Lower |

**API Configuration** (from `@Backend/Documentations/nanao_banana_doc.md`):
```python
from google import genai
from google.genai import types

client = genai.Client()

response = client.models.generate_content(
    model="gemini-3-pro-image-preview",  # or "gemini-2.5-flash-image"
    contents=[prompt],
    config=types.GenerateContentConfig(
        response_modalities=['TEXT', 'IMAGE'],
        image_config=types.ImageConfig(
            aspect_ratio="9:16",  # Match video aspect ratio
            image_size="2K"  # "1K", "2K", "4K"
        )
    )
)
```

**Aspect Ratio Mapping** (from `@Backend/Documentations/nano_prompt_guide.md:4552-4582`):

| Video Aspect | Image Aspect | Resolution (2K) |
|--------------|--------------|-----------------|
| 9:16 | 9:16 | 1536x2752 |
| 16:9 | 16:9 | 2752x1536 |

**Error Handling**:
- Retry with exponential backoff (max 3 attempts)
- Fallback to `gemini-2.5-flash-image` if Pro fails
- Log generation failures for debugging

---

### 3.1.5 Implement Sequential Generation with Style Consistency

**Estimated Time**: 1 hour

**Description**: Generate images sequentially, using previous images as reference for style consistency.

**Multi-Image Reference Strategy** (from `@Backend/Documentations/nano_prompt_guide.md:713-720`):
- Gemini 3 Pro supports up to 14 reference images
- Up to 6 images of objects with high-fidelity
- Up to 5 images of humans for character consistency

**Sequential Generation Flow**:
```
1. Generate Image 1 (first scene)
   - Use user_reference_image if available
   - Use research_images for context
   
2. Generate Image 2+ (subsequent scenes)
   - Include Image 1 as style reference
   - Prompt: "Maintain the same visual style as the reference image"
   - Include character descriptions for consistency
```

**Implementation** (from `@Backend/Documentations/nanao_banana_doc.md:3408-3439`):
```python
# Multi-image input for style consistency
response = client.models.generate_content(
    model="gemini-3-pro-image-preview",
    contents=[
        previous_image,  # Style reference
        user_reference_image,  # If available
        text_prompt
    ],
    config=types.GenerateContentConfig(
        response_modalities=['TEXT', 'IMAGE'],
        image_config=types.ImageConfig(
            aspect_ratio=aspect_ratio,
            image_size="2K"
        )
    )
)
```

---

### 3.1.6 Implement Supabase Storage Upload (`app/services/supabase.py`)

**Estimated Time**: 30 minutes

**Description**: Upload generated images to Supabase Storage and return public URLs.

**Storage Path Convention**:
```
generated_images/{workflow_id}/scene_{scene_number}_{timestamp}.png
```

**Upload Flow**:
1. Decode base64 image data from API response
2. Generate unique filename with workflow_id and scene_number
3. Upload to Supabase Storage bucket `generated-images`
4. Return public URL for the uploaded image

**Error Handling**:
- Retry upload on transient failures
- Log storage errors with image metadata
- Return placeholder URL if upload fails (don't block workflow)

---

### 3.1.7 Implement Image Generator Agent (`app/agents/image_generator.py`)

**Estimated Time**: 1 hour

**Description**: Main agent class that orchestrates image generation.

**Agent Flow**:
```
1. Extract inputs from state
   - script_output.scenes[]
   - selected_tool (style specs)
   - user_reference_image_url
   - research_images[]
   - aspect_ratio, resolution

2. Calculate images to generate
   - Apply FR-502, FR-503 reduction logic
   - Ensure 1-5 range (FR-504, FR-505)

3. Build prompts for each image
   - Use scene descriptions
   - Apply tool visual vocabulary
   - Include camera/lighting directions

4. Generate images sequentially
   - Use Nano Banana Pro for complex scenes
   - Use Nano Banana Flash for simple scenes
   - Maintain style consistency with references

5. Upload to Supabase Storage
   - Store in generated-images bucket
   - Track metadata for each image

6. Combine all image sources
   - all_images = user_ref + research + generated

7. Persist to workflows table
   - Update generated_images column
   - Update all_image_urls column

8. Return output to state
```

**State Output**:
```python
{
    "generated_images": ["url1", "url2", ...],
    "all_images": ["user_ref", "research1", "generated1", ...],
    "image_metadata": [
        {
            "url": "...",
            "scene_number": 1,
            "prompt": "...",
            "model_used": "gemini-3-pro-image-preview",
            "generation_time_ms": 12500,
            "aspect_ratio": "9:16",
            "resolution": "2K"
        }
    ],
    "phase_timestamps": {
        "image_generator_completed": "2026-01-15T05:30:00Z"
    }
}
```

---

### 3.1.8 Wire to LangGraph Node (`app/graph/nodes.py`)

**Estimated Time**: 20 minutes

**Node Function** (`image_generator_node`):

**Input from State**:
- `workflow_id` - For storage path
- `script_output` - Contains scenes[]
- `selected_tool` - Tool metadata with style specs
- `user_reference_image_url` - Optional user reference
- `research_images` - Images from Deep Research
- `aspect_ratio`, `resolution` - Video specs

**Output to State**:
- `generated_images` - List of generated image URLs
- `all_images` - Combined list of all image URLs
- `image_metadata` - Metadata for each image
- `phase_timestamps.image_generator_completed` - Completion timestamp

**Conditional Routing**:
```python
def route_after_images(state: VideoGenerationState) -> str:
    """Route after image generation"""
    if state.get("error"):
        return "error_handler"
    if state.get("hitl_mode") == "manual" and not state.get("hitl_approved", {}).get("images"):
        return "hitl_image_gate"
    return "video_generator"
```

---

### 3.1.9 Implement HITL Gate 4 (`app/graph/nodes.py`)

**Estimated Time**: 30 minutes

**Description**: Implement HITL gate for image review in manual mode.

**Gate 4 User Actions** (from `@Guides/SRS.md:126-127`):
- **View**: See all generated images
- **Add**: Upload additional reference images (FR-509)
- **Remove**: Remove unwanted images
- **Regenerate**: Provide feedback for regeneration (FR-510)
- **Approve**: Continue to video generation

**Implementation**:
```python
async def hitl_image_gate_node(state: VideoGenerationState) -> dict:
    """HITL Gate 4: Image review and approval."""
    workflow_id = state["workflow_id"]
    
    # Update workflow status
    await supabase.table("workflows").update({
        "current_hitl_gate": "image_generation",
        "status": "awaiting_image_approval"
    }).eq("id", workflow_id).execute()
    
    # Return interrupt signal for LangGraph
    return {"current_hitl_gate": "image_generation"}
```

**Regeneration Handling**:
- Track regeneration count in `state["regeneration_counts"]["images"]`
- Max 3 regeneration attempts per gate
- Use feedback to adjust prompts on regeneration

---

### 3.1.10 Implement Persistence (`app/agents/image_generator.py`)

**Estimated Time**: 20 minutes

**Description**: Save image output to Supabase `workflows.generated_images` column.

**Persistence Flow**:
1. Generate complete `ImageGeneratorOutput`
2. Convert to dict via `model_dump()`
3. Update workflow record in Supabase
4. Insert records into `media` table for each image

**Supabase Updates**:
```python
# Update workflows table
await supabase.table("workflows").update({
    "generated_images": image_output.model_dump(),
    "all_image_urls": all_image_urls,
    "updated_at": utc_now_iso()
}).eq("id", workflow_id).execute()

# Insert into media table
for image in generated_images:
    await supabase.table("media").insert({
        "workflow_id": workflow_id,
        "media_type": "generated_image",
        "storage_url": image.url,
        "metadata": {
            "scene_number": image.scene_number,
            "prompt": image.prompt,
            "model_used": image.model_used
        }
    }).execute()
```

---

### 3.1.11 Write Unit Tests (`tests/test_agents/test_image_generator.py`)

**Estimated Time**: 45 minutes

**Test Cases**:

| Test | Description |
|------|-------------|
| `test_image_count_no_external` | 5 scenes, no external images → 5 generated |
| `test_image_count_with_user_ref` | 5 scenes, user ref → 4 generated |
| `test_image_count_with_research` | 5 scenes, 2 research images → 3 generated |
| `test_image_count_minimum` | Always at least 1 image |
| `test_image_count_maximum` | Never more than 5 images |
| `test_prompt_builder_surreal` | Prompt includes surreal_realism vocabulary |
| `test_prompt_builder_anime` | Prompt includes high_octane_anime vocabulary |
| `test_prompt_builder_3d` | Prompt includes stylized_3d vocabulary |
| `test_aspect_ratio_mapping` | 9:16 video → 9:16 image |
| `test_sequential_generation` | Images generated in order with references |
| `test_storage_upload` | Images uploaded to Supabase Storage |
| `test_all_images_combined` | user_ref + research + generated combined |
| `test_hitl_gate_triggered` | Gate triggered in manual mode |
| `test_regeneration_with_feedback` | Feedback applied to prompts |

**Mock Requirements**:
- Mock Nano Banana API calls
- Mock Supabase Storage uploads
- Use fixture data for script output

---

### 3.1.12 Integration Test

**Estimated Time**: 30 minutes

**Description**: Test full image generation flow from script to images.

**Integration Test Flow**:
1. Create mock state with completed script output
2. Run `image_generator_node(state)`
3. Verify state update contains all required fields
4. Verify images uploaded to storage
5. Verify metadata persisted to database

**Test Scenarios**:
- 8s video (2-3 scenes) → 2-3 images
- 18s video (4-6 scenes) → 4-5 images
- With user reference image → reduced count
- With research images → reduced count
- Different tool categories → different visual styles

---

## Nano Banana API Details

### Model Selection Logic

```python
def select_image_model(scene: Scene, tool_category: str) -> str:
    """Select appropriate Nano Banana model based on scene complexity."""
    
    # Use Pro for complex scenes
    if any([
        len(scene.description) > 200,  # Detailed description
        scene.pattern_interrupt_type == "visual_effect",
        tool_category == "surreal_realism",  # Requires photorealism
    ]):
        return "gemini-3-pro-image-preview"  # Nano Banana Pro
    
    # Use Flash for simpler scenes
    return "gemini-2.5-flash-image"  # Nano Banana
```

### Resolution Mapping

| Video Resolution | Image Size | Nano Banana Pro | Nano Banana Flash |
|------------------|------------|-----------------|-------------------|
| 1080p | 2K | ✅ Supported | ❌ Max 1K |
| 720p | 1K | ✅ Supported | ✅ Supported |

### API Response Handling

```python
for part in response.parts:
    if part.text is not None:
        # Log any text response (descriptions, warnings)
        logger.info(f"Image generation text: {part.text}")
    elif part.inline_data is not None:
        # Extract image data
        image = part.as_image()
        image.save(f"temp_{scene_number}.png")
        # Upload to Supabase Storage
        url = await upload_to_storage(image, workflow_id, scene_number)
```

---

## File Structure After Implementation

```
Backend/app/
├── agents/
│   ├── __init__.py  # Add ImageGeneratorAgent export
│   ├── intent_tool_selector.py ✅
│   ├── deep_research.py ✅
│   ├── script_writer.py ✅
│   └── image_generator.py  # NEW
├── models/
│   ├── __init__.py  # Add image model exports
│   ├── research.py ✅
│   ├── script.py ✅
│   ├── tool.py ✅
│   └── image.py  # NEW
├── services/
│   ├── __init__.py  # Add NanoBananaService export
│   ├── gemini.py ✅
│   ├── supabase.py ✅ (extend with storage methods)
│   └── nano_banana.py  # NEW
├── graph/
│   ├── nodes.py  # Add image_generator_node, hitl_image_gate_node
│   └── ...
└── ...

tests/
├── test_agents/
│   ├── test_intent.py ✅
│   ├── test_research.py ✅
│   ├── test_script.py ✅
│   └── test_image_generator.py  # NEW
└── ...
```

---

## Dependencies

### Python Packages (Add to requirements.txt)
```
google-genai>=0.5.0  # Already present, verify version supports image generation
Pillow>=10.0.0  # For image processing
```

### API Requirements
- **Gemini API Key** (`GOOGLE_API_KEY`) - For Nano Banana Pro/Flash

### Service Dependencies
- Gemini Service (`app/services/gemini.py`) ✅ - Extend for image generation
- Supabase Service (`app/services/supabase.py`) ✅ - Extend for storage uploads

---

## Acceptance Criteria

| Criteria | Verification |
|----------|--------------|
| 1-5 images generated based on scene count | Unit test |
| Image count reduced with external images | Unit test |
| Tool visual vocabulary in prompts | Unit test |
| Images uploaded to Supabase Storage | Integration test |
| Metadata persisted to workflows table | Integration test |
| HITL Gate 4 triggered in manual mode | Integration test |
| Style consistency across images | Manual review |
| Aspect ratio matches video specs | Unit test |

---

## Estimated Timeline

| Task | Est. Time | Cumulative |
|------|-----------|------------|
| 3.1.1 Create image models | 30 min | 30 min |
| 3.1.2 Implement image count calculator | 30 min | 1h |
| 3.1.3 Implement prompt builder | 1 hr | 2h |
| 3.1.4 Implement Nano Banana integration | 1.5 hr | 3h 30m |
| 3.1.5 Implement sequential generation | 1 hr | 4h 30m |
| 3.1.6 Implement Supabase storage upload | 30 min | 5h |
| 3.1.7 Implement Image Generator Agent | 1 hr | 6h |
| 3.1.8 Wire to LangGraph node | 20 min | 6h 20m |
| 3.1.9 Implement HITL Gate 4 | 30 min | 6h 50m |
| 3.1.10 Implement persistence | 20 min | 7h 10m |
| 3.1.11 Write unit tests | 45 min | 7h 55m |
| 3.1.12 Integration test | 30 min | **8h 25m** |

**Total Estimated Time**: ~8.5 hours (1.5-2 days)

---

## Next Steps After Completion

After Phase 3.1 is complete, proceed to **Phase 3.2: Video Generator Agent** which depends on:
- `all_images[]` - Reference images for video generation
- `script_output` - Script with scenes and dialogue
- `duration_seconds`, `aspect_ratio`, `resolution` - Video specs

---

## Checklist for Implementation

- [ ] 3.1.1 Create `app/models/image.py` with all models
- [ ] 3.1.2 Implement `calculate_images_to_generate()` in `app/agents/image_generator.py`
- [ ] 3.1.3 Implement `build_image_prompt()` in `app/agents/image_generator.py`
- [ ] 3.1.4 Create `app/services/nano_banana.py` with API integration
- [ ] 3.1.5 Implement `generate_images_sequentially()` in `app/agents/image_generator.py`
- [ ] 3.1.6 Extend `app/services/supabase.py` with storage upload methods
- [ ] 3.1.7 Implement `ImageGeneratorAgent` class in `app/agents/image_generator.py`
- [ ] 3.1.8 Add `image_generator_node()` to `app/graph/nodes.py`
- [ ] 3.1.9 Add `hitl_image_gate_node()` to `app/graph/nodes.py`
- [ ] 3.1.10 Implement `persist_images()` in `app/agents/image_generator.py`
- [ ] 3.1.11 Create `tests/test_agents/test_image_generator.py`
- [ ] 3.1.12 Run integration tests
- [ ] Update `app/agents/__init__.py` with new exports
- [ ] Update `app/models/__init__.py` with new exports
- [ ] Update `app/services/__init__.py` with new exports
