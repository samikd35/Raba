# Raba System Improvement Plan: "Ingredients" Strategy & Veo 3.1 Optimization

**Date**: 2026-02-02  
**Status**: Ready for Implementation  
**Priority**: CRITICAL - Fixes core generation quality issues

---

## Executive Summary

This plan addresses the critical issue where the image generator only produces 1 reference image instead of the required 3 "Ingredients" images for Veo 3.1. It also implements Veo 3.1 best practices from official documentation and aligns all agents with the robustness strategy.

**Root Cause Identified**: Line 387 in `image_generator.py` hardcodes `images_to_generate = 1`, overriding the "Ingredients" strategy despite documentation claiming otherwise.

---

## Part 1: Fix Image Generator - "3 Ingredients" Strategy

### 1.1 Problem Analysis

**Current State** (Lines 386-387 in `image_generator.py`):
```python
# CRITIC: Always generate a single Master Style Frame
images_to_generate = 1
```

**Impact**:
- Only 1 reference image is passed to Veo 3.1
- "Style poisoning" occurs because single complex image over-indexes on specific visual details
- Cannot implement Subject/Environment/Object composition strategy

### 1.2 Solution: Implement True "Ingredients" Generation

**File**: `Backend/app/agents/image_generator.py`

#### Change 1: Update `calculate_images_to_generate` function (lines 61-102)

**Current**:
```python
def calculate_images_to_generate(...) -> int:
    # CRITIC: Master Style Frame only – always generate 1 image
    to_generate = 1
    ...
    return to_generate
```

**New**:
```python
def calculate_images_to_generate(
    scene_count: int,
    user_has_reference: bool = False,
    research_image_count: int = 0,
    enable_ingredients_mode: bool = True,  # NEW PARAMETER
) -> int:
    """Calculate how many images to generate with Nano Banana.
    
    INGREDIENTS MODE (Veo 3.1 Best Practice):
    Generate exactly 3 distinct "ingredient" images:
    1. Subject - The main character/host/actor
    2. Environment - The background/setting
    3. Object/Concept - The key diagram/element
    
    This prevents "style poisoning" by giving Veo 3.1 independent elements to
    composite rather than a single baked-in complex scene.
    """
    if enable_ingredients_mode:
        # Veo 3.1 "Ingredients" strategy: Always generate 3 distinct assets
        to_generate = 3
        logger.info(
            f"Ingredients mode enabled: generating {to_generate} reference images "
            f"(Subject, Environment, Object)"
        )
    else:
        # Legacy storyboard mode: single composite
        to_generate = 1
        logger.info("Legacy storyboard mode: generating 1 composite image")
    
    return to_generate
```

#### Change 2: Update `ImageGeneratorAgent.run()` to actually use the count (line 386-398)

**Current**:
```python
# CRITIC: Always generate a single Master Style Frame
images_to_generate = 1
```

**New**:
```python
# Enable Ingredients mode for Veo 3.1 optimization
images_to_generate = calculate_images_to_generate(
    scene_count=len(scenes),
    user_has_reference=bool(user_reference_url),
    research_image_count=len(research_images),
    enable_ingredients_mode=True,  # Veo 3.1 best practice
)

logger.info(f"Will generate {images_to_generate} ingredient images for Veo 3.1")
```

#### Change 3: Create Distinct Prompts for Each Ingredient (lines 397-502)

**Current**: Single storyboard prompt created

**New**: Create 3 specialized prompts

```python
prompts = []

if images_to_generate == 3:
    # INGREDIENTS MODE: Generate 3 distinct assets
    
    # Ingredient 1: SUBJECT (Character/Host)
    subject_prompt = build_ingredient_prompt(
        ingredient_type="subject",
        scenes=scenes,
        topic=topic,
        tool_category=tool_category,
        character_sheet=character_sheet,
        script_output=script_output,
        anchor=anchor,
    )
    prompts.append(subject_prompt)
    
    # Ingredient 2: ENVIRONMENT (Background/Setting)
    environment_prompt = build_ingredient_prompt(
        ingredient_type="environment",
        scenes=scenes,
        topic=topic,
        tool_category=tool_category,
        anchor=anchor,
    )
    prompts.append(environment_prompt)
    
    # Ingredient 3: OBJECT/CONCEPT (Key Diagram/Element)
    object_prompt = build_ingredient_prompt(
        ingredient_type="object",
        scenes=scenes,
        topic=topic,
        tool_category=tool_category,
        anchor=anchor,
    )
    prompts.append(object_prompt)
    
else:
    # LEGACY MODE: Single storyboard composite
    # [KEEP EXISTING STORYBOARD LOGIC]
```

#### Change 4: Implement `build_ingredient_prompt` Helper (NEW FUNCTION)

Add new function before `build_storyboard_prompt` (~line 277):

```python
def build_ingredient_prompt(
    ingredient_type: str,  # "subject", "environment", or "object"
    scenes: list[dict],
    topic: str,
    tool_category: str,
    anchor: dict | None = None,
    character_sheet: dict | None = None,
    script_output: dict | None = None,
) -> str:
    """Build prompt for a specific ingredient type.
    
    Args:
        ingredient_type: One of "subject", "environment", "object"
        scenes: Script scenes for context
        topic: Video topic
        tool_category: Visual style category
        anchor: Global style anchor
        character_sheet: Character reference (for subject only)
        script_output: Full script output
        
    Returns:
        Specialized prompt for the ingredient
    """
    parts = []
    
    if ingredient_type == "subject":
        # SUBJECT: The consistent character/host
        parts.append(
            f"[INGREDIENT: SUBJECT - Character/Host Consistency]\\n"
            f"Generate a REFERENCE SHEET showing the main character/host for: {topic}\\n\\n"
        )
        
        if character_sheet:
            char_name, char_ref = build_character_reference_context(character_sheet, script_output or {})
            if char_ref:
                parts.append(f"CHARACTER: {char_ref}\\n\\n")
        elif script_output and script_output.get("lead_character"):
            lead = script_output.get("lead_character")
            desc = script_output.get("lead_character_description", "")
            parts.append(f"CHARACTER: {lead}. {desc}\\n\\n")
        else:
            # Generic host
            parts.append(
                f"CHARACTER: A professional host/presenter suitable for {topic}. \\n"
                f"Clean, neutral appearance for maximum compositing flexibility.\\n\\n"
            )
        
        parts.append(
            "REQUIREMENTS:\\n"
            "- Multiple views: Front, 3/4 profile, side view\\n"
            "- Consistent appearance, clothing, proportions across all views\\n"
            "- Clean background for easy compositing\\n"
            "- High detail on face and distinguishing features\\n"
        )
        
    elif ingredient_type == "environment":
        # ENVIRONMENT: The neutral, high-quality background
        parts.append(
            f"[INGREDIENT: ENVIRONMENT - Background/Setting]\\n"
            f"Generate a CLEAN, HIGH-QUALITY background environment for: {topic}\\n\\n"
        )
        
        # Infer environment from scenes
        key_settings = extract_environment_from_scenes(scenes)
        if key_settings:
            parts.append(f"SETTING: {key_settings}\\n\\n")
        else:
            parts.append(
                f"SETTING: Professional studio environment suitable for {topic}.\\n"
                f"Neutral, clean, no distracting elements.\\n\\n"
            )
        
        parts.append(
            "REQUIREMENTS:\\n"
            "- NO characters or objects (pure background)\\n"
            "- High-resolution, clean composition\\n"
            "- Neutral lighting that works with any foreground\\n"
            "- Style consistent with {tool_category}\\n"
        )
        
    elif ingredient_type == "object":
        # OBJECT/CONCEPT: The key diagram/element
        parts.append(
            f"[INGREDIENT: OBJECT/CONCEPT - Key Visual Element]\\n"
            f"Generate a TECHNICAL DIAGRAM or KEY OBJECT for: {topic}\\n\\n"
        )
        
        # Extract key visual entities from scenes
        key_entities = extract_key_entities(scenes, topic)
        if key_entities:
            parts.append(f"KEY ENTITIES: {key_entities}\\n\\n")
        
        # Scientific/technical emphasis
        parts.append(
            "SCIENTIFIC CINEMATOGRAPHER REQUIREMENTS:\\n"
            "- [Subject]: The specific object/concept (e.g., 'red blood cell', 'DNA strand')\\n"
            "- [Composition]: Extreme close-up OR technical cross-section\\n"
            "- [Style]: Scientific infographic, 4K resolution, sharp focus\\n"
            "- [Constraint]: Clean labels with sans-serif typography (if text_overlay_mode allows)\\n"
            "- [Constraint]: Clinical white or neutral background for maximum clarity\\n"
            "- NO artistic interpretation - FACTUAL ACCURACY REQUIRED\\n"
        )
    
    # Apply global style anchor
    if anchor:
        parts.append("\\nSTYLE ANCHOR:\\n")
        parts.append(f"- Palette: {', '.join(anchor.get('color_palette', [])[:4])}\\n")
        if anchor.get('lighting'):
            parts.append(f"- Lighting: {anchor.get('lighting')}\\n")
    
    parts.append(f"\\nSTYLE CATEGORY: {tool_category}\\n")
    parts.append("TECHNICAL: 8K resolution, sharp detail, professional quality.\\n")
    
    return "".join(parts)


def extract_environment_from_scenes(scenes: list[dict]) -> str:
    """Extract primary environment/setting from scenes."""
    environments = set()
    for scene in scenes or []:
        desc = (scene.get("description", "") or "").lower()
        # Look for location keywords
        for keyword in ["laboratory", "studio", "office", "forest", "space", "underwater", "city", "desert"]:
            if keyword in desc:
                environments.add(keyword)
    
    if environments:
        return ", ".join(list(environments)[:2])
    return ""
```

#### Change 5: Update Metadata for Generated Images (lines 565-590)

```python
# Label each generated image with its ingredient role
ingredient_roles = ["subject", "environment", "object"] if images_to_generate == 3 else ["master_style_frame"]

for i, (image_bytes, text_response, usage_metadata, retry_count) in enumerate(results):
    role = ingredient_roles[i] if i < len(ingredient_roles) else f"scene_{i+1}"
    
    storage_path = f"generated_images/{workflow_id}/{role}_{int(time.time())}.png"
    image_url = await self._upload_to_storage(image_bytes, storage_path)
    
    generated_image = GeneratedImage(
        url=image_url,
        storage_path=storage_path,
        prompt=prompts[i],
        scene_number=i + 1,
        model_used=config.model,
        aspect_ratio=config.aspect_ratio,
        resolution=config.resolution,
        generation_time_ms=0,
        used_style_reference=(i > 0 or user_ref_bytes is not None),
        style_reference_url=user_reference_url if i == 0 else None,
        retry_count=retry_count,
        role=role,  # <-- NEW: "subject", "environment", "object"
    )
    generated_images.append(generated_image)
```

---

## Part 2: Update Tool Templates for "Ingredients" Support

### 2.1 Tool Enhancer System Prompts

**File**: `Backend/app/services/tool_enhancer.py`

#### Update `TOOL_ENHANCEMENT_SYSTEM_PROMPT` (lines 118-121)

**Current**:
```python
**CRITICAL: INGREDIENTS/STORYBOARD COMPOSITION**
- Adopt an Ingredients-first composition: explicitly account for Subject (character/host), Environment (background), and Object/Concept (diagram/specific element).
- Either include explicit placeholders `{ingredient_subject}`, `{ingredient_environment}`, `{ingredient_object}` OR instruct a STORYBOARD COMPOSITE that shows multiple states/panels containing all key entities and transformation flow.
```

**Enhanced**:
```python
**CRITICAL: INGREDIENTS-FIRST COMPOSITION (Veo 3.1 Best Practice)**
The system will generate THREE SEPARATE images (not one composite):
1. SUBJECT Image: Dedicated character/host reference with multiple views
2. ENVIRONMENT Image: Clean background with NO foreground elements
3. OBJECT/CONCEPT Image: Technical diagram or key element in isolation

The template MUST provide distinct instructions for each ingredient type using these NEW PLACEHOLDERS:
- `{ingredient_type}` - Will be "subject", "environment", or "object"
- `{ingredient_subject}` - Subject-specific instructions (character consistency)
- `{ingredient_environment}` - Environment-specific instructions (background only)
- `{ingredient_object}` - Object-specific instructions (scientific/technical diagram)

**TEMPLATE STRUCTURE REQUIREMENT**:
```
[INGREDIENT: {ingredient_type}]

{% if ingredient_type == "subject" %}
Generate a character reference sheet...
{ingredient_subject}
{% elif ingredient_type == "environment" %}
Generate a clean background...
{ingredient_environment}
{% elif ingredient_type == "object" %}
Generate a technical diagram...
{ingredient_object}
{% endif %}
```

**CRITICAL: NO COMPOSITE STORYBOARDS**
- Do NOT instruct "generate a storyboard showing all scenes"
- Each image is a SINGLE, ISOLATED ingredient for Veo to composite
- Veo 3.1 handles the composition - we provide clean building blocks
```

#### Update Helper Function `_ensure_storyboard_placeholders` (lines 513-535)

**Rename to** `_ensure_ingredients_placeholders` and **rewrite**:

```python
def _ensure_ingredients_placeholders(self, text: str) -> str:
    """Ensure image template has ingredients-first composition awareness."""
    # Check if template already has ingredients structure
    has_ingredients = (
        "{ingredient_type}" in text or
        "ingredient_subject" in text or
        "ingredient_environment" in text or
        "ingredient_object" in text
    )
    
    if has_ingredients:
        return text
    
    # Inject ingredients block
    ingredients_block = (
        "\\n\\n[INGREDIENTS COMPOSITION]\\n"
        "This prompt will be called 3 times with {ingredient_type} set to: 'subject', 'environment', 'object'\\n\\n"
        
        "IF {ingredient_type} == 'subject':\\n"
        "  Generate a CHARACTER REFERENCE SHEET showing the main host/character.\\n"
        "  Multiple views (front, 3/4, side), consistent appearance.\\n"
        "  Clean background for compositing.\\n\\n"
        
        "IF {ingredient_type} == 'environment':\\n"
        "  Generate a CLEAN BACKGROUND SETTING.\\n"
        "  NO characters or foreground objects.\\n"
        "  High-quality, neutral lighting, professional finish.\\n\\n"
        
        "IF {ingredient_type} == 'object':\\n"
        "  Generate a TECHNICAL DIAGRAM or KEY OBJECT.\\n"
        "  Scientific accuracy, clean labels (if text allowed), isolated subject.\\n"
        "  Follow 'Scientific Cinematographer' formula: [Subject] + [Composition] + [Style] + [Constraint]\\n"
    )
    
    return text + ingredients_block
```

#### Update Repair Function Call (line 556)

```python
# Image template fixes
if resp.image_prompt_template:
    im = resp.image_prompt_template
    im = self._enforce_optics_in_image(im, category)
    im = self._ensure_ingredients_placeholders(im)  # <-- RENAMED
    im = self._ensure_character_reference_placeholder(im)
    im = self._ensure_image_negative(im)
    resp.image_prompt_template = im
```

### 2.2 Bulk Improve Existing Tools

After code changes, run:

```bash
# API endpoint or admin script
POST /api/tools/bulk-improve
{
  "improvement_suggestion": "Update to support Veo 3.1 'Ingredients' strategy with 3 separate reference images (Subject, Environment, Object) instead of storyboard composites."
}
```

---

## Part 3: Video Generator Veo 3.1 Optimizations

### 3.1 Update Reference Image Selection

**File**: `Backend/app/agents/video_generator.py`

#### Update `select_reference_images` (lines 165-226)

**Current**: Generic selection of first/middle/last

**New**: Ingredients-aware selection

```python
def select_reference_images(
    generated_images: list[str],
    image_metadata: list[dict] | None = None,  # NEW: Include metadata
    max_count: int = MAX_REFERENCE_IMAGES,
) -> list[str]:
    """Select reference images for Veo 3.1.
    
    INGREDIENTS MODE (Preferred):
    If images have 'role' metadata (subject/environment/object), use all 3 in order.
    
    LEGACY MODE:
    Select first, middle, last if more than max_count.
    """
    if not generated_images:
        logger.warning("No generated images available for video generation")
        return []
    
    # Check if we have ingredients metadata
    if image_metadata and len(image_metadata) == 3:
        roles = [img.get("role") for img in image_metadata]
        if all(role in ["subject", "environment", "object"] for role in roles):
            # INGREDIENTS MODE: Use all 3 in the correct order
            # Veo 3.1 works best with Subject first, then Environment, then Object
            role_order = ["subject", "environment", "object"]
            sorted_images = []
            for role in role_order:
                for i, img_meta in enumerate(image_metadata):
                    if img_meta.get("role") == role:
                        sorted_images.append(generated_images[i])
                        break
            
            if len(sorted_images) == 3:
                logger.info("Using Ingredients mode: Subject + Environment + Object references for Veo 3.1")
                return sorted_images
    
    # LEGACY MODE: Strategic selection
    valid_images = [
        img for img in generated_images
        if not (isinstance(img, str) and img.startswith("upload_failed://"))
    ]
    
    if not valid_images:
        logger.warning("No valid generated images after filtering")
        return []
    
    if len(valid_images) <= max_count:
        selected = valid_images[:max_count]
        logger.info(f"Using all {len(selected)} generated images as references (legacy mode)")
    else:
        # First, middle, last
        selected = [valid_images[0]]
        if max_count >= 2:
            selected.append(valid_images[-1])
        if max_count >= 3 and len(valid_images) > 2:
            mid_idx = len(valid_images) // 2
            selected.insert(1, valid_images[mid_idx])
        logger.info(f"Strategic selection: {len(selected)} images from {len(valid_images)} (legacy mode)")
    
    return selected
```

#### Update Call Site in `VideoGeneratorAgent.run()` (around line 553)

```python
# Video Generator uses generated images from Nano Banana Pro
selected_images = select_reference_images(
    generated_images=generated_images,
    image_metadata=state.get("image_metadata"),  # <-- NEW: Pass metadata
)
```

### 3.2 Implement Veo 3.1 Prompting Best Practices

**Reference**: `veo_3.1.md` lines 128-152 (Prompt writing basics)

#### Update `build_video_prompt` (lines 229-417)

Add Veo 3.1 structure:

```python
def build_video_prompt(...) -> str:
    parts = []
    
    # [USER REQUEST BLOCK] - Keep existing
    
    # NEW: Veo 3.1 REQUIRED ELEMENTS BLOCK
    parts.append("[VEO 3.1 GENERATION REQUIREMENTS]\\n")
    parts.append(f"Subject: {extract_subject_from_script(script_output)}\\n")
    parts.append(f"Action: {extract_action_from_segment(script_output, segment_info)}\\n")
    parts.append(f"Style: {tool_category}\\n")
    
    # Camera positioning (from veo_3.1.md guidance)
    camera_position = anchor.get("camera") if anchor else "eye-level"
    parts.append(f"Camera: {camera_position}\\n")
    
    # Composition
    composition = "medium shot" if not is_extension else "continuous from previous"
    parts.append(f"Composition: {composition}\\n")
    
    # Ambiance
    if anchor and anchor.get("color_palette"):
        parts.append(f"Ambiance: {', '.join(anchor.get('color_palette')[:3])} tones\\n")
    
    parts.append("[END VEO REQUIREMENTS]\\n\\n")
    
    # [CONTINUATION] block - Keep existing
    
    # [HOOK], [SCENES], [CTA] - Keep existing
    
    # ... rest of function
```

**Add helper functions**:

```python
def extract_subject_from_script(script_output: dict) -> str:
    """Extract the main subject for Veo prompt."""
    lead = script_output.get("lead_character")
    if lead:
        return lead
    
    # Fallback: Extract from scenes
    scenes = script_output.get("scenes", [])
    if scenes and scenes[0].get("visual_keywords"):
        return scenes[0]["visual_keywords"][0]
    
    return "main subject"


def extract_action_from_segment(script_output: dict, segment_info: dict) -> str:
    """Extract primary action for this segment."""
    start = segment_info.get("start_time", 0)
    end = segment_info.get("end_time", 8)
    
    scenes = script_output.get("scenes", [])
    relevant_scenes = [
        s for s in scenes
        if s.get("timestamp_start", 0) >= start and s.get("timestamp_end", 10) <= end
    ]
    
    if relevant_scenes:
        # Extract action verbs from descriptions
        desc = relevant_scenes[0].get("description", "")
        # Simple extraction: look for verbs
        for verb in ["walking", "running", "explaining", "demonstrating", "showing", "pointing"]:
            if verb in desc.lower():
                return verb
    
    return "moving"
```

---

## Part 4: Testing & Validation

### 4.1 Unit Tests

**File**: `Backend/tests/test_image_generator_ingredients.py` (NEW)

```python
import pytest
from app.agents.image_generator import (
    calculate_images_to_generate,
    build_ingredient_prompt,
)


def test_ingredients_mode_generates_3_images():
    """Verify ingredients mode produces exactly 3 images."""
    count = calculate_images_to_generate(
        scene_count=5,
        user_has_reference=False,
        research_image_count=0,
        enable_ingredients_mode=True,
    )
    assert count == 3


def test_legacy_mode_generates_1_image():
    """Verify legacy mode produces 1 image."""
    count = calculate_images_to_generate(
        scene_count=5,
        enable_ingredients_mode=False,
    )
    assert count == 1


def test_subject_ingredient_prompt():
    """Verify subject prompt contains character consistency requirements."""
    prompt = build_ingredient_prompt(
        ingredient_type="subject",
        scenes=[],
        topic="quantum physics",
        tool_category="realistic",
    )
    
    assert "SUBJECT" in prompt
    assert "character" in prompt.lower() or "host" in prompt.lower()
    assert "multiple views" in prompt.lower()


def test_environment_ingredient_prompt():
    """Verify environment prompt excludes characters and objects."""
    prompt = build_ingredient_prompt(
        ingredient_type="environment",
        scenes=[],
        topic="space exploration",
        tool_category="realistic",
    )
    
    assert "ENVIRONMENT" in prompt
    assert "NO characters" in prompt
    assert "background" in prompt.lower()


def test_object_ingredient_prompt():
    """Verify object prompt emphasizes technical accuracy."""
    prompt = build_ingredient_prompt(
        ingredient_type="object",
        scenes=[{"visual_keywords": ["mitochondria", "cell"]}],
        topic="cellular biology",
        tool_category="realistic",
    )
    
    assert "OBJECT" in prompt
    assert "scientific" in prompt.lower() or "technical" in prompt.lower()
    assert "accuracy" in prompt.lower() or "factual" in prompt.lower()
```

### 4.2 Integration Test

**File**: `Backend/tests/test_integration_ingredients_flow.py` (NEW)

```python
import pytest
from app.graph.workflow import create_video_generation_graph


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_ingredients_workflow():
    """End-to-end test of ingredients generation flow."""
    
    # Setup test input
    initial_state = {
        "topic": "How photosynthesis works",
        "duration_seconds": 18,
        "aspect_ratio": "9:16",
        "resolution": "720p",
        "enable_audio": False,
    }
    
    # Run through image generator node (mocked external API)
    graph = create_video_generation_graph()
    
    # ... (mock Nano Banana Pro to return 3 fake images)
    # ... (mock Veo to accept 3 references)
    
    # Verify results
    final_state = await graph.ainvoke(initial_state)
    
    # Check that 3 images were generated
    assert len(final_state["generated_images"]) == 3
    
    # Check that metadata has correct roles
    metadata = final_state["image_metadata"]
    roles = {img["role"] for img in metadata}
    assert roles == {"subject", "environment", "object"}
    
    # Check that video generator received all 3
    # ... assertions on video generation call
```

### 4.3 Manual Verification Checklist

1. **Image Generation**:
   - [ ] Run workflow with topic "Mitochondria explanation"
   - [ ] Verify 3 separate images are generated (not 1 storyboard)
   - [ ] Check Image 1 contains a character/host reference
   - [ ] Check Image 2 is a clean background (no foreground)
   - [ ] Check Image 3 is a technical diagram of mitochondria
   - [ ] Verify metadata has `role` field for each image

2. **Video Generation**:
   - [ ] Check Veo API call receives all 3 reference images
   - [ ] Verify reference order: Subject, Environment, Object
   - [ ] Confirm no "style poisoning" (video doesn't over-index on one image's style)
   - [ ] Check final video composites all 3 elements naturally

3. **Tool Templates**:
   - [ ] Run bulk-improve on 3-5 existing tools
   - [ ] Verify templates include ingredients placeholders
   - [ ] Check validation passes for all improved templates
   - [ ] Test generation with both old and new tool templates

---

## Part 5: Database Schema Updates

### 5.1 Extend `media` Table

**File**: `Backend/Documentations/tables.sql`

Add `role` column to track ingredient type:

```sql
ALTER TABLE media 
ADD COLUMN role VARCHAR(50) DEFAULT 'generated';

-- Possible values: 'subject', 'environment', 'object', 'master_style_frame', 'user_reference'

COMMENT ON COLUMN media.role IS 'Ingredient type for Veo 3.1 multi-reference generation';
```

### 5.2 Migration Script

**File**: `Backend/migrations/009_add_media_role.sql` (NEW)

```sql
-- Migration: Add role column to media table
-- Date: 2026-02-02
-- Purpose: Support "Ingredients" strategy for Veo 3.1

BEGIN;

-- Add role column
ALTER TABLE media 
ADD COLUMN IF NOT EXISTS role VARCHAR(50) DEFAULT 'generated';

-- Backfill existing data
UPDATE media 
SET role = 'master_style_frame' 
WHERE role = 'generated' AND source = 'nano_banana_pro';

-- Add index for filtering by role
CREATE INDEX IF NOT EXISTS idx_media_role ON media(role);

COMMIT;
```

---

## Part 6: Documentation Updates

### 6.1 Update Architecture Docs

**File**: `Backend/Documentations/RABA_Architecture.md` (if exists)

Add section:

```markdown
### 2.6.5 Ingredients Generation Mode (Veo 3.1 Optimization)

Instead of generating a single composite "Master Style Frame", the system now produces 3 distinct "Ingredient" images:

1. **Subject Image**: Character reference sheet with multiple views for consistency
2. **Environment Image**: Clean background setting with no foreground elements
3. **Object/Concept Image**: Technical diagram or key visual element in isolation

**Why 3 Images?**
Veo 3.1's multi-reference feature works best when given independent elements to composite, rather than a pre-baked complex scene. This prevents "style poisoning" where the video over-indexes on the specific visual details of a single reference.

**Implementation**:
- `image_generator.py`: Generates 3 specialized prompts using `build_ingredient_prompt()`
- `video_generator.py`: Selects all 3 images in Subject → Environment → Object order
- Tool templates: Include `{ingredient_type}` conditional logic for per-type instructions
```

### 6.2 Update API Documentation

**File**: `Backend/Documentations/API_Docs/workflows.md`

Update response schema:

```markdown
#### Image Generator Output

```json
{
  "generated_images": [
    "https://storage/subject_123.png",
    "https://storage/environment_123.png",
    "https://storage/object_123.png"
  ],
  "image_metadata": [
    {
      "url": "https://storage/subject_123.png",
      "role": "subject",
      "prompt": "Generate a character reference sheet...",
      ...
    },
    {
      "url": "https://storage/environment_123.png",
      "role": "environment",
      ...
    },
    {
      "url": "https://storage/object_123.png",
      "role": "object",
      ...
    }
  ]
}
```
```

---

## Part 7: Rollout Plan

### Phase 1: Code Implementation (Days 1-2)
- [ ] Implement `calculate_images_to_generate` fix
- [ ] Implement `build_ingredient_prompt` helper
- [ ] Update `ImageGeneratorAgent.run()` to use count
- [ ] Update `select_reference_images` with metadata awareness
- [ ] Add database migration for `role` column

### Phase 2: Tool System Updates (Day 3)
- [ ] Update Tool Enhancer system prompts with Ingredients requirements
- [ ] Rename and rewrite `_ensure_storyboard_placeholders` → `_ensure_ingredients_placeholders`
- [ ] Test tool creation with new prompts
- [ ] Run bulk-improve on 5 test tools

### Phase 3: Testing (Days 4-5)
- [ ] Write and run unit tests
- [ ] Write and run integration test
- [ ] Manual verification with scientific topic (e.g., "Photosynthesis")
- [ ] Manual verification with character-based topic (e.g., "Story of Moses")

### Phase 4: Full Rollout (Day 6)
- [ ] Run bulk-improve on ALL production tools
- [ ] Monitor first 20 video generations for quality
- [ ] Check Veo API logs to confirm 3 references being passed
- [ ] Rollback plan: Set `enable_ingredients_mode=False` if issues

---

## Acceptance Criteria

### Must Have
1. ✅ Image generator produces exactly 3 images when called
2. ✅ Images have distinct roles: subject, environment, object
3. ✅ Veo receives all 3 images in correct order
4. ✅ No "style poisoning" observed in generated videos
5. ✅ All existing unit tests still pass
6. ✅ Database migration runs without errors

### Should Have
1. ✅ Tool templates validate with new placeholders
2. ✅ Bulk-improve successfully updates 90%+ of tools
3. ✅ Scientific topics produce factually accurate diagram ingredients
4. ✅ Character-based topics produce consistent character references

### Nice to Have
1. ⭕ Admin UI to preview generated ingredients before video generation
2. ⭕ A/B test metrics comparing Ingredients mode vs. Legacy mode
3. ⭕ Visual Validation Agent integration (VLM critique of ingredients)

---

## Risk Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Veo doesn't composite 3 refs well | HIGH | LOW | Test with Veo docs examples first; rollback flag available |
| Tool templates fail validation | MEDIUM | MEDIUM | Phased bulk-improve; fix validation rules iteratively |
| Increased latency (3 images) | LOW | HIGH | Already generating images; just changing count from 1 to 3 |
| Breaking existing workflows | HIGH | LOW | Extensive testing; backward compatibility via `enable_ingredients_mode` flag |

---

## Success Metrics (Week 1 Post-Rollout)

- **Quality**: >80% of videos show improved Subject+Object+Environment composition
- **Accuracy**: Scientific videos have recognizable, factually correct diagrams
- **Consistency**: Character-based videos maintain consistent character appearance
- **Performance**: Image generation time increases by <50% (3x images, but parallel)
- **Errors**: <5% regeneration rate due to validation failures

---

## References

1. **Veo 3.1 Documentation**: `Backend/Documentations/veo_3.1.md` (lines 10, 36-38, 168)
2. **AGENTS.md**: Tool enhancer rules (lines 35-48)
3. **Robustness Strategy**: `Backend/RABA_ROBUSTNESS_FIX_STRATEGY.md` (Section 3)
4. **Current Image Generator**: `Backend/app/agents/image_generator.py` (line 387 - the bug)
5. **Tool Enhancer**: `Backend/app/services/tool_enhancer.py` (lines 118-152)

---

**END OF PLAN**
