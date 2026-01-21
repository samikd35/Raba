# Master Image Storyboard Composition Improvement Plan

## Executive Summary

Transform the single-scene master image into a **storyboard-style composite frame** that captures the complete visual DNA of the video. This is a **system-wide improvement** applied through the tool template system, enabling bulk updates to all existing tools.

---

## Problem Statement

### The Core Issue

The current system generates a **single-entity, single-moment master image** when it should generate a **storyboard composite** that captures ALL visual elements needed across the entire video. This fundamentally breaks visual consistency for any video with multiple distinct entities, transformations, or scene progressions.

### Concrete Example: Tesla Evolution Video

**User Input:**
```
Topic: "A seamless, liquid-morphing evolution of Tesla vehicles from 2008 to 2026"
Duration: 32 seconds
Scenes: 8 scenes featuring 7 distinct Tesla models
```

**Script Generated (8 scenes):**
| Scene | Visual Content | Key Entity |
|-------|---------------|------------|
| 1 | Liquid metal solidifying into 2008 Roadster | Tesla Roadster |
| 2 | Roadster morphs into Model S | Model S |
| 3 | Model S transforms into Model X with Falcon doors | Model X |
| 4 | Model X compresses into Model 3 Highland (red) | Model 3 |
| 5 | Model 3 evolves into Model Y Juniper | Model Y |
| 6 | Model Y shatters and reforms into Cybertruck | Cybertruck |
| 7 | Cybertruck softens into glass-heavy Cybercab | Cybercab |
| 8 | Cybercab liquifies, ready to loop back | Loop transition |

**Current Master Image Generated:**
- Shows ONLY the 2008 Roadster with liquid metal pouring onto it
- Captures ~12.5% of the visual information needed (1 of 8 scenes)
- Provides ZERO visual reference for Model S, Model X, Model 3, Model Y, Cybertruck, or Cybercab

**What Happens During Video Generation:**
- Scene 1: ✅ Looks correct (matches master image)
- Scene 2-8: ❌ Video generator "hallucinates" each vehicle with no reference
- Result: Inconsistent vehicle designs, style drift, generic interpretations instead of specific Tesla models

**What the Master Image SHOULD Look Like:**
A storyboard composite showing ALL 7 Tesla vehicles arranged left-to-right, connected by liquid metal morphing effects, in a single unified frame. This gives the video generator complete visual DNA for every scene.

### Why This Happens (Root Cause)

1. **Single-Scene Prompt Building:** The `build_image_prompt()` function only uses the FIRST scene's description
   ```python
   # Current: Only first scene used
   selected_scenes = scenes[:1]  # Takes only scene 1
   description = scene.get("description", "")  # Only scene 1's description
   ```

2. **No Entity Aggregation:** The system doesn't extract or list all visual entities from the full script

3. **Character Reference Not Used:** The `character_reference_sheet` exists in state but is never passed to image generation

4. **Template Limitation:** Tool templates don't have placeholders for multi-scene/multi-entity composition

### The Problem is Universal (Not Just Tesla)

This issue affects ANY video with:
- **Evolution/Timeline content:** Product evolution, historical progression, technology advancement
- **Character journeys:** A character in multiple locations/situations
- **Transformation narratives:** Before/after, metamorphosis, state changes
- **Comparison content:** A vs B, multiple options, alternatives
- **Process/Tutorial content:** Step 1 → Step 2 → Step 3

**Examples:**
- "iPhone evolution from 2007 to 2024" → Master image shows only iPhone 1
- "A day in the life of a software developer" → Master image shows only morning scene
- "Water cycle explained" → Master image shows only evaporation, missing condensation/precipitation
- "Moses parting the Red Sea" → Master image shows Moses but not the parting sea or Israelites crossing

### Current vs Desired Behavior

| Aspect | Current Behavior | Desired Behavior |
|--------|-----------------|------------------|
| Scene coverage | First scene only | ALL key scenes in storyboard panels |
| Entity representation | Single primary entity | ALL distinct entities visible |
| Transformation flow | Not captured | Visual progression shown (A → B → C) |
| Character reference | Not used | Integrated as consistency anchor |
| Template support | Single-scene placeholders | Multi-scene storyboard placeholders |
| Video generator guidance | Minimal (1 reference point) | Complete (full visual DNA) |

---

## Solution Architecture

### Core Principle: Template-Driven Storyboard Generation

Instead of modifying the `ImageGeneratorAgent` logic, we enhance the **tool prompt templates** to instruct the image model to generate storyboard-style composites. This approach:

1. Applies system-wide via bulk tool update
2. Leverages existing `ToolEnhancerService` infrastructure
3. Maintains tool-specific visual vocabularies
4. Integrates character reference sheet as input

### New Placeholders for Image Template

| Placeholder | Description | Source |
|-------------|-------------|--------|
| `{scene_descriptions}` | Concatenated descriptions of ALL scenes | Script output |
| `{scene_count}` | Total number of scenes | Script output |
| `{key_entities}` | Extracted primary visual entities | Script analysis |
| `{transformation_flow}` | Entity-to-entity transitions | Script analysis |
| `{character_reference}` | Character sheet description + view hints | Character reference sheet |
| `{character_name}` | Lead character name | Script output |
| `{composition_layout}` | Recommended storyboard layout | Auto-determined |

---

## Implementation Plan

### Phase 1: Enhance Image Generator Agent

**File:** `Backend/app/agents/image_generator.py`

#### 1.1 Add Scene Aggregation Logic

```python
def aggregate_scene_descriptions(scenes: list[dict], max_scenes: int = 6) -> str:
    """Aggregate all scene descriptions into a storyboard brief.
    
    Args:
        scenes: List of scene dicts from script output
        max_scenes: Maximum scenes to include (for prompt length)
        
    Returns:
        Formatted string of scene descriptions for storyboard
    """
    if not scenes:
        return ""
    
    # Select key scenes (first, middle, last + highest visual_cue scores)
    selected = select_key_scenes(scenes, max_scenes)
    
    parts = []
    for i, scene in enumerate(selected):
        desc = scene.get("description", "")
        keywords = scene.get("visual_keywords", [])
        scene_num = scene.get("scene_number", i + 1)
        
        parts.append(
            f"[SCENE {scene_num}]: {desc[:200]}"
            f"{' | Keywords: ' + ', '.join(keywords[:4]) if keywords else ''}"
        )
    
    return "\n".join(parts)


def select_key_scenes(scenes: list[dict], max_count: int) -> list[dict]:
    """Select most visually important scenes for storyboard.
    
    Priority: First scene, last scene, scenes with highest visual_cue scores,
    scenes with pattern_interrupt_type changes.
    """
    if len(scenes) <= max_count:
        return scenes
    
    selected = []
    selected.append(scenes[0])  # Always include first
    selected.append(scenes[-1])  # Always include last
    
    # Add middle scenes with visual variety
    remaining = [s for s in scenes[1:-1]]
    remaining.sort(key=lambda s: len(s.get("visual_keywords", [])), reverse=True)
    
    for scene in remaining:
        if len(selected) >= max_count:
            break
        if scene not in selected:
            selected.append(scene)
    
    # Sort by scene number
    selected.sort(key=lambda s: s.get("scene_number", 0))
    return selected


def extract_key_entities(scenes: list[dict], topic: str) -> str:
    """Extract primary visual entities from all scenes.
    
    Returns comma-separated list of unique entities.
    """
    entities = set()
    
    for scene in scenes:
        keywords = scene.get("visual_keywords", [])
        entities.update(keywords[:3])  # Top 3 keywords per scene
    
    # Filter to most relevant (appears in multiple scenes or in topic)
    topic_lower = topic.lower()
    prioritized = [e for e in entities if e.lower() in topic_lower]
    others = [e for e in entities if e not in prioritized]
    
    return ", ".join(prioritized[:5] + others[:5])


def extract_transformation_flow(scenes: list[dict]) -> str:
    """Extract entity transformation sequence from scenes.
    
    Returns flow description like: "Entity A → Entity B → Entity C"
    """
    if len(scenes) < 2:
        return ""
    
    # Look for morphing/transformation keywords
    flow_parts = []
    for i, scene in enumerate(scenes):
        desc = scene.get("description", "").lower()
        keywords = scene.get("visual_keywords", [])
        
        # Check for transformation indicators
        if any(word in desc for word in ["morph", "transform", "evolve", "become", "change"]):
            if keywords:
                flow_parts.append(keywords[0])
    
    if len(flow_parts) >= 2:
        return " → ".join(flow_parts)
    
    # Fallback: use first keyword from first and last scene
    first_kw = scenes[0].get("visual_keywords", ["Start"])[0] if scenes else "Start"
    last_kw = scenes[-1].get("visual_keywords", ["End"])[0] if scenes else "End"
    return f"{first_kw} → ... → {last_kw}"


def determine_composition_layout(scene_count: int, has_character: bool) -> str:
    """Determine optimal storyboard layout based on content.
    
    Returns layout instruction string.
    """
    if scene_count <= 3:
        return "horizontal triptych (3 panels left-to-right)"
    elif scene_count <= 6:
        return "2x3 grid (6 panels, read left-to-right, top-to-bottom)"
    else:
        return "horizontal timeline strip with key moments"
    
    # Character-centric videos might use focal layout
    if has_character and scene_count <= 4:
        return "central character with surrounding scene vignettes"
```

#### 1.2 Integrate Character Reference Sheet

```python
def build_character_reference_context(
    character_sheet: dict | None,
    script_output: dict,
) -> tuple[str, str]:
    """Build character reference context for image prompt.
    
    Args:
        character_sheet: CharacterReferenceSheet dict from state
        script_output: Script output containing lead_character info
        
    Returns:
        Tuple of (character_name, character_reference_description)
    """
    char_name = ""
    char_ref = ""
    
    # Get character name from script
    char_name = script_output.get("lead_character", "")
    char_desc = script_output.get("lead_character_description", "")
    
    if character_sheet:
        sheet_name = character_sheet.get("character_name", "")
        sheet_desc = character_sheet.get("character_description", "")
        ref_images = character_sheet.get("reference_images", [])
        
        char_name = sheet_name or char_name
        
        # Build reference description
        parts = []
        if sheet_desc:
            parts.append(f"Character: {sheet_desc}")
        elif char_desc:
            parts.append(f"Character: {char_desc}")
        
        # Add view hints from reference images
        if ref_images:
            views = [img.get("view", "") for img in ref_images if img.get("view")]
            if views:
                parts.append(f"Reference views available: {', '.join(views)}")
            parts.append("Maintain exact character appearance across all storyboard panels.")
        
        char_ref = " ".join(parts)
    elif char_desc:
        char_ref = f"Lead character: {char_desc}. Maintain consistent appearance across all panels."
    
    return char_name, char_ref
```

#### 1.3 Update `build_image_prompt()` Function

```python
def build_storyboard_prompt(
    scenes: list[dict],
    topic: str,
    duration_seconds: int,
    tool_category: str,
    anchor: dict | None = None,
    character_sheet: dict | None = None,
    script_output: dict | None = None,
) -> str:
    """Build storyboard-style master image prompt.
    
    Generates a prompt that instructs the image model to create
    a composite storyboard showing all key visual states.
    """
    script_output = script_output or {}
    
    # Aggregate scene information
    scene_descriptions = aggregate_scene_descriptions(scenes)
    scene_count = len(scenes)
    key_entities = extract_key_entities(scenes, topic)
    transformation_flow = extract_transformation_flow(scenes)
    composition_layout = determine_composition_layout(scene_count, bool(character_sheet))
    
    # Get character context
    char_name, char_ref = build_character_reference_context(character_sheet, script_output)
    
    parts = []
    
    # Header: Storyboard instruction
    parts.append(
        "Create a STORYBOARD MASTER IMAGE that shows the complete visual narrative "
        "in a single composite frame. This image defines the visual DNA for video generation.\n\n"
    )
    
    # Topic and duration context
    parts.append(f"VIDEO CONCEPT: {topic}\n")
    parts.append(f"DURATION: {duration_seconds} seconds | SCENES: {scene_count}\n\n")
    
    # Composition layout
    parts.append(f"STORYBOARD LAYOUT: {composition_layout}\n\n")
    
    # Key entities
    if key_entities:
        parts.append(f"KEY VISUAL ENTITIES (must all appear): {key_entities}\n\n")
    
    # Transformation flow
    if transformation_flow:
        parts.append(f"VISUAL FLOW/TRANSFORMATION: {transformation_flow}\n\n")
    
    # Scene descriptions
    parts.append("SCENE BREAKDOWN:\n")
    parts.append(scene_descriptions)
    parts.append("\n\n")
    
    # Character reference
    if char_ref:
        parts.append(f"CHARACTER CONSISTENCY: {char_ref}\n\n")
    
    # Style anchor
    if anchor:
        parts.append("STYLE REQUIREMENTS:\n")
        parts.append(f"- Palette: {', '.join(anchor.get('color_palette', [])[:6])}\n")
        parts.append(f"- Materials: {', '.join(anchor.get('materials', [])[:6])}\n")
        parts.append(f"- Lighting: {anchor.get('lighting', '')}\n")
        parts.append(f"- Camera: {anchor.get('camera', '')}\n\n")
    
    # Critical instruction
    parts.append(
        "CRITICAL: Generate a SINGLE composite image showing ALL listed scenes/entities. "
        "Each panel or section should represent a different scene moment. "
        "Maintain unified style treatment across all panels. "
        "This storyboard will guide video generation for visual consistency.\n"
    )
    
    return "".join(parts)
```

#### 1.4 Update `ImageGeneratorAgent.run()` to Use New Context

```python
# In ImageGeneratorAgent.run(), update the prompt building section:

# Get character reference sheet from state
character_sheet = state.get("character_reference_sheet")

# Build storyboard prompt instead of single-scene prompt
for i, scene in enumerate(selected_scenes):
    template = (state.get("selected_tool") or {}).get("image_prompt_template")
    
    if template:
        # Build context with new storyboard placeholders
        context = {
            # Existing placeholders
            "scene_description": scene.get("description", ""),
            "style": tool_category,
            "scene_number": i + 1,
            "total_scenes": len(scenes),
            "topic": topic,
            "duration_seconds": duration_seconds,
            
            # NEW: Storyboard placeholders
            "scene_descriptions": aggregate_scene_descriptions(scenes),
            "scene_count": len(scenes),
            "key_entities": extract_key_entities(scenes, topic),
            "transformation_flow": extract_transformation_flow(scenes),
            "composition_layout": determine_composition_layout(len(scenes), bool(character_sheet)),
            
            # NEW: Character reference placeholders
            "character_name": (character_sheet or {}).get("character_name", "") or script_output.get("lead_character", ""),
            "character_reference": build_character_reference_context(character_sheet, script_output)[1],
            
            # Existing style anchor placeholders
            "global_color_palette": ", ".join(anchor.get("color_palette", [])[:6]),
            "global_materials": ", ".join(anchor.get("materials", [])[:6]),
            "global_motion_language": ", ".join(anchor.get("motion_language", [])[:6]),
            "global_lighting": anchor.get("lighting", ""),
            "global_camera": anchor.get("camera", ""),
            "global_texture": anchor.get("texture", ""),
            "image_negative_constraint": negative_block,
        }
        # ... rest of template rendering
```

---

### Phase 2: Update Tool Enhancer System Prompts

**File:** `Backend/app/services/tool_enhancer.py`

#### 2.1 Add Storyboard Instructions to `TOOL_ENHANCEMENT_SYSTEM_PROMPT`

Add the following section to the image_prompt_template requirements:

```python
# Add to TOOL_ENHANCEMENT_SYSTEM_PROMPT, in the image_prompt_template section:

"""
### image_prompt_template (for Nano Banana Pro)
**MINIMUM 150 WORDS - NO EXCEPTIONS**
Must include: {scene_description}, {style}

**NEW STORYBOARD PLACEHOLDERS (use these for multi-scene composition):**
- `{scene_descriptions}` - All scene descriptions concatenated
- `{scene_count}` - Total number of scenes
- `{key_entities}` - Primary visual entities that must appear
- `{transformation_flow}` - Entity transformation sequence (e.g., "A → B → C")
- `{composition_layout}` - Recommended storyboard layout
- `{character_name}` - Lead character name (if any)
- `{character_reference}` - Character consistency instructions

**CRITICAL: STORYBOARD COMPOSITION REQUIREMENT**
The image template MUST instruct the model to generate a STORYBOARD-STYLE COMPOSITE showing:
1. Multiple visual states/scenes in a single frame
2. All key entities that appear throughout the video
3. Transformation/progression flow between states
4. Consistent character appearance across all panels (if character exists)

**STORYBOARD LAYOUT OPTIONS (choose based on content):**
- Horizontal triptych: 3 panels left-to-right (for 3 or fewer scenes)
- 2x3 grid: 6 panels for longer narratives
- Timeline strip: Horizontal flow showing progression
- Focal with vignettes: Central subject with surrounding scene moments

**EXAMPLE STORYBOARD TEMPLATE:**
"Generate a STORYBOARD MASTER IMAGE for {style} showing the complete visual narrative.

LAYOUT: {composition_layout}
SCENES: {scene_count} key moments to capture
ENTITIES: {key_entities}
FLOW: {transformation_flow}

SCENE BREAKDOWN:
{scene_descriptions}

CHARACTER CONSISTENCY:
{character_reference}

COMPOSITION: Arrange scenes as {composition_layout}. Each panel shows a distinct moment.
Maintain unified {style} treatment across all panels.

RENDERING: [existing technical specs...]
LIGHTING: [existing lighting specs...]
COLOR: [existing color specs...]

NEGATIVE CONSTRAINTS: {image_negative_constraint}

CRITICAL: This is a STORYBOARD showing ALL scenes, not a single scene. 
Every listed entity must be visible. Maintain style consistency across panels."
"""
```

#### 2.2 Add Storyboard Instructions to `TOOL_IMPROVEMENT_SYSTEM_PROMPT`

Mirror the same additions in the improvement prompt.

#### 2.3 Add Template Repair for Storyboard Placeholders

```python
def _ensure_storyboard_placeholders(self, text: str) -> str:
    """Ensure image template has storyboard composition instructions."""
    
    # Check if template already has storyboard awareness
    storyboard_indicators = [
        "{scene_descriptions}",
        "{key_entities}",
        "{composition_layout}",
        "storyboard",
        "composite",
        "multiple scenes",
        "all panels",
    ]
    
    has_storyboard = any(ind.lower() in text.lower() for ind in storyboard_indicators)
    
    if has_storyboard:
        return text
    
    # Append storyboard instruction block
    storyboard_block = """

[STORYBOARD COMPOSITION]
This master image must be a STORYBOARD showing multiple visual states:
- Layout: {composition_layout}
- Key Entities: {key_entities}
- Scene Flow: {transformation_flow}
- Character: {character_reference}

Arrange as a composite with {scene_count} panels showing the complete narrative.
Each panel represents a key moment from: {scene_descriptions}

Maintain unified style across all panels. Every entity must appear."""
    
    return text + storyboard_block


def _ensure_character_reference_placeholder(self, text: str) -> str:
    """Ensure image template uses character reference."""
    
    if "{character_reference}" in text or "{character_name}" in text:
        return text
    
    # Add character consistency block
    char_block = """

[CHARACTER CONSISTENCY]
Lead Character: {character_name}
{character_reference}
Maintain identical character appearance across all storyboard panels."""
    
    return text + char_block
```

#### 2.4 Update `_repair_templates()` Method

```python
def _repair_templates(self, resp: ToolEnhancementResponse, *, category: CategoryEnum) -> ToolEnhancementResponse:
    # Video template fixes
    if resp.video_prompt_template:
        v = resp.video_prompt_template
        v = self._remove_timestamp_sfx(v)
        v = self._ensure_video_segment_placeholders(v)
        v = self._ensure_video_audio_placeholders(v)
        resp.video_prompt_template = v

    # Image template fixes
    if resp.image_prompt_template:
        im = resp.image_prompt_template
        im = self._enforce_optics_in_image(im, category)
        im = self._ensure_image_negative(im)
        # NEW: Storyboard and character reference
        im = self._ensure_storyboard_placeholders(im)
        im = self._ensure_character_reference_placeholder(im)
        resp.image_prompt_template = im
    
    return resp
```

---

### Phase 3: Bulk Update Existing Tools

**File:** `Backend/app/api/routes/tools.py` (existing bulk update endpoint)

The existing `POST /api/tools/bulk-update` endpoint with `use_ai_enhancement=True` will automatically apply the new storyboard requirements when tools are re-enhanced.

#### 3.1 Bulk Update Strategy

```python
# Example bulk update request to upgrade all tools:
{
    "update_type": "all",
    "improvement_reason": "Upgrade image templates to storyboard composition format with character reference integration",
    "use_ai_enhancement": true
}
```

This will:
1. Iterate through all active tools
2. Re-enhance each tool using the updated `TOOL_IMPROVEMENT_SYSTEM_PROMPT`
3. Apply `_repair_templates()` which now includes storyboard placeholders
4. Persist updated templates to database

#### 3.2 Migration Script (Optional)

For controlled rollout, create a migration script:

```python
# Backend/scripts/migrate_storyboard_templates.py

async def migrate_tools_to_storyboard():
    """Migrate all tools to use storyboard image templates."""
    
    registry = get_tool_registry()
    enhancer = get_tool_enhancer()
    
    tools = await registry.list_tools(is_active=True, limit=100)
    
    results = []
    for tool in tools.tools:
        try:
            # Create improvement request
            request = ToolImproveRequest(
                improvement_suggestion=(
                    "Update image_prompt_template to generate STORYBOARD-STYLE composite images "
                    "showing all key scenes in a single frame. Add placeholders: {scene_descriptions}, "
                    "{key_entities}, {transformation_flow}, {composition_layout}, {character_reference}. "
                    "The master image should capture the complete visual DNA of the video."
                ),
                preserve_templates=False,
            )
            
            # Enhance
            enhanced = await enhancer.improve_tool(tool, request)
            
            # Apply
            updated = await registry.apply_improvement(
                tool.tool_id,
                enhanced,
                request.improvement_suggestion,
            )
            
            results.append({"tool_id": tool.tool_id, "status": "success"})
            
        except Exception as e:
            results.append({"tool_id": tool.tool_id, "status": "failed", "error": str(e)})
    
    return results
```

---

### Phase 4: Update Video Generator for Storyboard Reference

**File:** `Backend/app/agents/video_generator.py`

The video generator should understand that the reference image is a storyboard and extract relevant panels for each segment.

#### 4.1 Add Storyboard Context to Video Prompts

```python
def build_segment_prompt_with_storyboard_context(
    segment_index: int,
    total_segments: int,
    scene: dict,
    master_image_is_storyboard: bool = True,
) -> str:
    """Build video prompt with storyboard reference context.
    
    Instructs Veo to reference the appropriate panel from the storyboard.
    """
    if master_image_is_storyboard:
        return (
            f"Reference the master storyboard image. "
            f"This is segment {segment_index} of {total_segments}. "
            f"Focus on panel {segment_index} of the storyboard for visual guidance. "
            f"Animate the scene depicted in that panel while maintaining "
            f"consistency with the overall storyboard style."
        )
    else:
        return f"Segment {segment_index} of {total_segments}."
```

---

## Updated State Schema

**File:** `Backend/app/graph/state.py`

Add new fields to support storyboard context:

```python
class VideoGenerationState(TypedDict, total=False):
    # ... existing fields ...
    
    # Storyboard context (computed in image_generator)
    storyboard_context: dict  # Contains: key_entities, transformation_flow, composition_layout
    master_image_type: str  # "storyboard" | "single_scene"
```

---

## Example: Before vs After

### BEFORE (Current Template)

```
Generate a high-fidelity keyframe anchor for {style} depicting {scene_description}.
Rendering Engine & Optics: Apply a 35mm Anamorphic lens...
[Technical specs for SINGLE scene]
```

**Result:** Single image of first scene only

### AFTER (Storyboard Template)

```
Generate a STORYBOARD MASTER IMAGE for {style} showing the complete visual narrative.

LAYOUT: {composition_layout}
SCENES: {scene_count} key moments
ENTITIES: {key_entities}
FLOW: {transformation_flow}

SCENE BREAKDOWN:
{scene_descriptions}

CHARACTER CONSISTENCY:
{character_reference}

COMPOSITION: Arrange as {composition_layout}. Each panel shows a distinct moment.
Maintain unified {style} treatment across all panels.

Rendering Engine & Optics: Apply consistent lens profile across all panels...
[Technical specs applied uniformly]

CRITICAL: This is a STORYBOARD showing ALL scenes in one composite image.
Every listed entity must be visible. Maintain style consistency across panels.
```

**Result:** Composite storyboard image showing all key scenes/entities

---

## Validation Criteria

A successful storyboard master image must:

1. **Multi-Panel Composition:** Visible separation into multiple scene panels
2. **Entity Coverage:** ≥80% of `{key_entities}` visually identifiable
3. **Flow Representation:** Transformation sequence visually implied
4. **Character Consistency:** Same character appearance across all panels (if applicable)
5. **Style Unity:** Single consistent lighting/color treatment across all panels

---

## Implementation Checklist

### Phase 1: Image Generator Updates
- [ ] Add `aggregate_scene_descriptions()` function
- [ ] Add `select_key_scenes()` function
- [ ] Add `extract_key_entities()` function
- [ ] Add `extract_transformation_flow()` function
- [ ] Add `determine_composition_layout()` function
- [ ] Add `build_character_reference_context()` function
- [ ] Update `build_image_prompt()` to use storyboard format
- [ ] Update `ImageGeneratorAgent.run()` to pass new context
- [ ] Integrate character_reference_sheet into prompt context

### Phase 2: Tool Enhancer Updates
- [ ] Update `TOOL_ENHANCEMENT_SYSTEM_PROMPT` with storyboard requirements
- [ ] Update `TOOL_IMPROVEMENT_SYSTEM_PROMPT` with storyboard requirements
- [ ] Add `_ensure_storyboard_placeholders()` method
- [ ] Add `_ensure_character_reference_placeholder()` method
- [ ] Update `_repair_templates()` to include new repairs

### Phase 3: Bulk Tool Migration
- [ ] Test bulk update endpoint with new prompts
- [ ] Create migration script for controlled rollout
- [ ] Execute bulk update on all active tools
- [ ] Verify updated templates in database

### Phase 4: Video Generator Updates
- [ ] Add storyboard context to video prompts
- [ ] Update segment prompt building

### Phase 5: Testing & Validation
- [ ] Test with evolution/transformation topics (like Tesla example)
- [ ] Test with character-centric narratives
- [ ] Test with data visualization topics
- [ ] Verify character reference integration
- [ ] Validate storyboard composition quality

---

## Timeline Estimate

| Phase | Effort | Priority |
|-------|--------|----------|
| Phase 1: Image Generator | 2-3 days | P0 |
| Phase 2: Tool Enhancer | 1-2 days | P0 |
| Phase 3: Bulk Migration | 0.5 days | P0 |
| Phase 4: Video Generator | 1 day | P1 |
| Phase 5: Testing | 2 days | P0 |

**Total: ~7-9 days**

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Nano Banana struggles with complex storyboards | Fallback to simpler layouts (triptych vs grid) |
| Template too long for context window | Truncate scene_descriptions to key scenes only |
| Character reference not available | Graceful degradation - use script's lead_character_description |
| Bulk update breaks existing tools | Run on staging first, keep backup of current templates |

---

## Conclusion

This plan transforms master image generation from single-scene snapshots to comprehensive storyboard composites through:

1. **Template-driven approach** - Changes flow through tool templates, enabling system-wide updates
2. **Character reference integration** - Existing character sheets become inputs to image generation
3. **Bulk update capability** - All existing tools can be upgraded via the existing bulk update endpoint
4. **Backward compatibility** - New placeholders are optional; old templates still work

The key insight: **The tool template system is the leverage point for system-wide improvements.**
