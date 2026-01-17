# Image Generation Fixes Plan

## Problem Summary

Three critical issues identified in image generation for video workflows:

1. **Aspect Ratio Mismatch**: Only 1 of 3 images has correct 9:16 aspect ratio. Others don't match user's video size selection.
2. **Incomplete Image Usage**: Only 2 images used in video even though 3 were generated.
3. **Visual Inconsistency**: Generated images lack visual consistency across the sequence.

---

## Root Cause Analysis

### Issue 1: Aspect Ratio Mismatch

**Root Cause**: The Gemini API call in `nano_banana.py` does NOT pass `image_config` with `aspect_ratio` and `image_size` parameters. The code comment (line 133) incorrectly states "image_config is NOT supported", but according to `nano_prompt_guide.md`, it IS supported via `types.ImageConfig`.

**Current Flow**:
1. Image generator requests 9:16 aspect ratio
2. API call only passes `response_modalities=["TEXT", "IMAGE"]`
3. Gemini generates images with default aspect ratio (likely 1:1)
4. Post-processing tries to crop/resize, but this is unreliable and inefficient

**Evidence**:
- `Backend/app/services/nano_banana.py:133-141` - Missing `image_config` in API call
- `Backend/app/services/nano_banana.py:305-364` - Post-processing crop/resize as workaround
- `Backend/Documentations/nano_prompt_guide.md:4415-4550` - Shows proper `imageConfig` usage

### Issue 2: Incomplete Image Usage

**Root Cause**: The `select_reference_images` function in `video_generator.py` has logic that may not use all generated images when 3 are available.

**Current Logic** (lines 205-213):
```python
if len(generated_images) <= max_count:
    selected = generated_images[:max_count]  # ✅ Correct
else:
    selected.append(generated_images[0])      # First image
    if max_count >= 2:
        selected.append(generated_images[-1]) # Last image
    if max_count >= 3 and len(generated_images) > 2:
        mid_idx = len(generated_images) // 2
        selected.insert(1, generated_images[mid_idx]) # Middle image
```

**Problem**: When exactly 3 images are generated, the `else` branch is never reached (since `len(generated_images) == 3 <= max_count`), so it should work. However, if there's any filtering or if `generated_images` list is incomplete, images may be missed.

**Evidence**:
- `Backend/app/agents/video_generator.py:180-217` - Selection logic
- Veo 3.1 supports up to 3 reference images (MAX_REFERENCE_IMAGES = 3)

### Issue 3: Visual Inconsistency

**Root Causes**:
1. **Weak Consistency Prompts**: The consistency instructions in `_build_consistency_prompt` are not strong enough
2. **Insufficient Reference Image Usage**: Previous generated images may not be used effectively as references
3. **Missing Character Consistency**: No explicit character description extraction and consistency enforcement
4. **Style Reference Not Detailed Enough**: Style descriptions lack specific visual details

**Evidence**:
- `Backend/app/services/nano_banana.py:366-412` - Consistency prompt building
- `Backend/app/services/nano_banana.py:229-303` - Sequential generation with references
- `Backend/app/agents/image_generator.py:441-466` - Style reference building
- `Backend/Documentations/nano_prompt_guide.md:4119-4331` - Character consistency best practices

---

## Solution Plan

### Fix 1: Enforce Aspect Ratio at API Level

**File**: `Backend/app/services/nano_banana.py`

**Changes**:
1. Add `image_config` parameter to `GenerateContentConfig` with proper `aspect_ratio` and `image_size`
2. Map aspect ratio strings to Gemini API format ("9:16" → "9:16")
3. Map resolution to Gemini API format ("1080p" → "2K", "720p" → "1K", "4k" → "4K")
4. Keep post-processing as fallback only (if API doesn't respect config)

**Implementation**:
```python
# Map aspect ratio
ASPECT_RATIO_API_MAP = {
    ImageAspectRatio.PORTRAIT_9_16: "9:16",
    ImageAspectRatio.LANDSCAPE_16_9: "16:9",
    ImageAspectRatio.SQUARE: "1:1",
    # ... add all mappings
}

# Map resolution
RESOLUTION_API_MAP = {
    ImageResolution.RES_1K: "1K",
    ImageResolution.RES_2K: "2K",
    ImageResolution.RES_4K: "4K",
}

# In generate_image method:
try:
    image_config = types.ImageConfig(
        aspect_ratio=ASPECT_RATIO_API_MAP.get(config.aspect_ratio, "9:16"),
        image_size=RESOLUTION_API_MAP.get(config.resolution, "2K"),
    )
    generation_config = types.GenerateContentConfig(
        response_modalities=["TEXT", "IMAGE"],
        image_config=image_config,
    )
except Exception as e:
    logger.warning(f"ImageConfig not supported, using fallback: {e}")
    generation_config = types.GenerateContentConfig(
        response_modalities=["TEXT", "IMAGE"],
    )
```

**Validation**:
- Generate 3 images with 9:16 aspect ratio
- Verify all 3 have correct dimensions (e.g., 1536x2752 for 2K 9:16)
- Check that post-processing is not needed (images already correct size)

---

### Fix 2: Ensure All Generated Images Are Used

**File**: `Backend/app/agents/video_generator.py`

**Changes**:
1. Simplify `select_reference_images` to always use all generated images (up to max_count)
2. Add logging to track which images are selected
3. Ensure the function returns exactly `min(len(generated_images), max_count)` images

**Implementation**:
```python
def select_reference_images(
    generated_images: list[str],
    max_count: int = MAX_REFERENCE_IMAGES,
) -> list[str]:
    """Select reference images from ONLY generated images.
    
    Uses ALL generated images up to max_count (3 for Veo 3.1).
    If more than max_count are generated, selects first, middle, and last.
    """
    if not generated_images:
        logger.warning("No generated images available for video generation")
        return []
    
    # Always use all images if we have 3 or fewer
    if len(generated_images) <= max_count:
        selected = generated_images[:max_count]
        logger.info(f"Using all {len(selected)} generated images as references")
    else:
        # If more than max_count, select strategically: first, middle, last
        selected = [generated_images[0]]
        if max_count >= 2:
            selected.append(generated_images[-1])
        if max_count >= 3:
            mid_idx = len(generated_images) // 2
            selected.insert(1, generated_images[mid_idx])
        logger.info(f"Selected {len(selected)} images from {len(generated_images)} total (first, middle, last)")
    
    logger.info(f"Reference images for Veo: {selected}")
    return selected
```

**Validation**:
- Generate 3 images
- Verify all 3 are passed to Veo video generation
- Check logs to confirm selection

---

### Fix 3: Enhance Visual Consistency

**Files**: 
- `Backend/app/services/nano_banana.py`
- `Backend/app/agents/image_generator.py`

**Changes**:

#### 3.1: Strengthen Consistency Prompts

**File**: `Backend/app/services/nano_banana.py` - `_build_consistency_prompt`

**Enhancements**:
1. Add explicit instructions to match reference images exactly
2. Include specific visual elements to maintain (colors, lighting, style)
3. Add character consistency instructions if characters are present
4. Use stronger language ("MUST", "EXACT", "PRECISELY")

**Implementation**:
```python
def _build_consistency_prompt(
    self,
    prompt: str,
    scene_number: int,
    total_scenes: int,
    style_reference: StyleReference,
    is_first_image: bool,
    previous_image_present: bool = False,
) -> str:
    """Build prompt with STRONG style consistency instructions."""
    parts = []
    
    if not is_first_image and previous_image_present:
        parts.append(
            "CRITICAL CONSISTENCY REQUIREMENTS - THIS IMAGE MUST MATCH THE REFERENCE IMAGE(S) EXACTLY:\n\n"
            "1. ART STYLE: Use the EXACT same rendering technique, line quality, and artistic treatment.\n"
            "2. COLOR PALETTE: Match colors precisely - same hues, saturation, and color grading.\n"
            "3. LIGHTING: Maintain identical lighting direction, intensity, and shadow style.\n"
            "4. CHARACTERS: If characters appear, they MUST look identical (same appearance, clothing, proportions).\n"
            "5. MOOD & ATMOSPHERE: Preserve the exact same emotional tone and visual mood.\n"
            "6. COMPOSITION STYLE: Use similar framing, camera angle, and visual composition approach.\n\n"
            "DO NOT deviate from the reference style. This is part of a video sequence and must be visually cohesive.\n\n"
        )
    
    parts.append(f"[Scene {scene_number} of {total_scenes}]\n\n")
    
    if style_reference.character_descriptions:
        parts.append("CHARACTER CONSISTENCY - MAINTAIN THESE EXACTLY:\n")
        for char_desc in style_reference.character_descriptions:
            parts.append(f"- {char_desc}\n")
        parts.append("\n")
    
    if style_reference.color_palette:
        parts.append(f"COLOR PALETTE (MUST MATCH): {', '.join(style_reference.color_palette)}\n\n")
    
    parts.append(prompt)
    
    return "".join(parts)
```

#### 3.2: Improve Reference Image Usage

**File**: `Backend/app/services/nano_banana.py` - `generate_sequential_images`

**Enhancements**:
1. Use ALL previous generated images as references (up to API limit)
2. For Nano Banana Pro, use up to 5 previous images as references
3. Include user reference and research images in the reference pool
4. Pass reference images in the correct order (most recent first)

**Implementation**:
```python
# In generate_sequential_images method:
for i, prompt in enumerate(prompts):
    logger.info(f"Generating image {i + 1}/{len(prompts)}")
    
    # Build reference image list
    current_references = []
    
    # Add research images (style guide)
    if research_reference_images:
        current_references.extend(research_reference_images[:2])  # Up to 2 research images
    
    # Add user reference (if first image)
    if i == 0 and user_reference_image:
        current_references.append(user_reference_image)
    
    # Add ALL previously generated images (up to API limit)
    # Nano Banana Pro supports up to 14 reference images total
    # We'll use up to 5 previous generated images
    if i > 0:
        # Use last 5 generated images as references
        previous_images = reference_images[-5:] if len(reference_images) > 5 else reference_images
        current_references.extend(previous_images)
    
    consistency_prompt = self._build_consistency_prompt(
        prompt=prompt,
        scene_number=i + 1,
        total_scenes=len(prompts),
        style_reference=style_reference,
        is_first_image=(i == 0),
        previous_image_present=(i > 0),
    )
    
    image_bytes, text_response, retry_count = await self.generate_image_with_retry(
        prompt=consistency_prompt,
        config=config,
        style_reference=style_reference,
        reference_images=current_references if current_references else None,
    )
    
    results.append((image_bytes, text_response, retry_count))
    reference_images.append(image_bytes)  # Add to pool for next iteration
```

#### 3.3: Enhance Style Reference Building

**File**: `Backend/app/agents/image_generator.py` - `_build_style_reference`

**Enhancements**:
1. Extract character descriptions more accurately from scenes
2. Build detailed color palette from tool vocabulary
3. Add specific visual style instructions
4. Include consistency requirements in style description

**Implementation**:
```python
def _build_style_reference(
    self,
    tool_category: str,
    scenes: list[dict],
) -> StyleReference:
    """Build comprehensive style reference for consistency."""
    vocab = TOOL_VISUAL_VOCABULARY.get(tool_category, TOOL_VISUAL_VOCABULARY["surreal_realism"])
    
    # Extract character descriptions more thoroughly
    character_descriptions = []
    for scene in scenes:
        desc = scene.get("description", "")
        dialogue = scene.get("dialogue", "")
        
        # Look for character mentions
        char_keywords = ["character", "person", "player", "man", "woman", "child", "figure", "protagonist"]
        if any(keyword in desc.lower() for keyword in char_keywords):
            # Extract character description
            char_desc = desc[:300]  # Longer description
            if dialogue:
                char_desc += f" Dialogue style: {dialogue[:100]}"
            character_descriptions.append(char_desc)
    
    # Build comprehensive style description
    style_description = (
        f"VISUAL STYLE REQUIREMENTS (MUST BE CONSISTENT ACROSS ALL IMAGES):\n"
        f"- Art Style: {', '.join(vocab['style_keywords'][:4])}\n"
        f"- Mood & Atmosphere: {', '.join(vocab['mood_keywords'][:2])}\n"
        f"- Lighting Style: {', '.join(vocab['lighting'][:2])}\n"
        f"- Camera Approach: {', '.join(vocab['camera_styles'][:2])}\n\n"
        f"CRITICAL: All images in this sequence must maintain EXACT visual consistency. "
        f"Match color grading, artistic treatment, character appearances (if any), "
        f"and overall visual style precisely across all images."
    )
    
    # Extract color palette hints from tool vocabulary
    color_palette = []
    # Add color hints based on tool category (can be enhanced)
    if "surreal" in tool_category:
        color_palette = ["vibrant blues", "golden yellows", "ethereal whites"]
    elif "anime" in tool_category:
        color_palette = ["high contrast", "saturated colors", "dramatic shadows"]
    # ... add more based on tool categories
    
    return StyleReference(
        style_description=style_description,
        character_descriptions=character_descriptions[:3],  # Up to 3 characters
        color_palette=color_palette,
    )
```

#### 3.4: Add Character Consistency from Script

**File**: `Backend/app/agents/image_generator.py` - `build_image_prompt`

**Enhancements**:
1. Extract character information from script scenes
2. Include character descriptions in image prompts
3. Ensure character consistency across scenes

**Implementation**:
```python
def build_image_prompt(
    scene: dict,
    scene_number: int,
    total_scenes: int,
    tool_category: str,
    topic: str,
    duration_seconds: int,
    character_descriptions: Optional[list[str]] = None,
) -> str:
    """Build image generation prompt with character consistency."""
    vocab = TOOL_VISUAL_VOCABULARY.get(tool_category, TOOL_VISUAL_VOCABULARY["surreal_realism"])
    
    parts = []
    
    parts.append(f"Create a high-quality image for Scene {scene_number} of {total_scenes} ")
    parts.append(f"in a {duration_seconds}-second YouTube Short about: {topic}\n\n")
    
    # Add character consistency if characters are present
    if character_descriptions:
        parts.append("CHARACTER CONSISTENCY (if characters appear):\n")
        for char_desc in character_descriptions:
            parts.append(f"- {char_desc}\n")
        parts.append("\n")
    
    parts.append("VISUAL DESCRIPTION:\n")
    description = scene.get("description", "")
    if description:
        parts.append(f"{description}\n\n")
    
    # ... rest of prompt building
```

---

## Implementation Order

1. **Fix 1 (Aspect Ratio)** - Highest priority, affects all images
2. **Fix 2 (Image Usage)** - Quick fix, ensures all images are used
3. **Fix 3 (Consistency)** - Most complex, requires multiple changes

---

## Testing Plan

### Test 1: Aspect Ratio Verification
1. Generate workflow with 9:16 aspect ratio
2. Verify all 3 generated images have dimensions matching 9:16 (e.g., 1536x2752 for 2K)
3. Check that images are NOT cropped/resized in post-processing
4. Test with different aspect ratios (16:9, 1:1) to ensure flexibility

### Test 2: Image Usage Verification
1. Generate workflow that creates 3 images
2. Check video generator logs to confirm all 3 images are selected
3. Verify Veo API receives all 3 reference images
4. Test edge cases: 1 image, 2 images, 4+ images

### Test 3: Visual Consistency Verification
1. Generate workflow with character-based story (e.g., "Story of Moses")
2. Verify all images have consistent:
   - Art style
   - Color palette
   - Character appearances (if applicable)
   - Lighting style
3. Compare images side-by-side for visual coherence
4. Test with different tool categories to ensure consistency works across styles

---

## Expected Outcomes

After implementing all fixes:

1. **Aspect Ratio**: 100% of generated images match user's selected video aspect ratio (9:16, 16:9, etc.)
2. **Image Usage**: All generated images (up to 3) are used as references in video generation
3. **Visual Consistency**: Generated images maintain consistent visual style, colors, and character appearances across the sequence

---

## References

- `Backend/Documentations/nano_prompt_guide.md` - Gemini image generation API documentation
- `Backend/app/services/nano_banana.py` - Image generation service
- `Backend/app/agents/image_generator.py` - Image generator agent
- `Backend/app/agents/video_generator.py` - Video generator agent
- `Backend/app/models/image.py` - Image models and enums
