# RABA Category System & Instruction Following Improvement Plan

**Status**: Analysis & Recommendations  
**Date**: January 2026  
**Priority**: High - Production-Critical Issues

---

## Executive Summary

This document analyzes two critical issues in RABA's video generation system:

1. **Rigid Category System**: The current three categories (surreal_realism, high_octane_anime, stylized_3d) are overly specific and limiting, constraining creativity and tool flexibility.

2. **Instruction Following Failures**: User parameters (audio on/off, subtitles, video topic) are not being strictly enforced, resulting in videos that ignore user preferences.

---

## Table of Contents

1. [Issue 1: Rigid Category System](#issue-1-rigid-category-system)
2. [Issue 2: Instruction Following Failures](#issue-2-instruction-following-failures)
3. [Root Cause Analysis](#root-cause-analysis)
4. [Recommended Fixes](#recommended-fixes)
5. [Implementation Plan](#implementation-plan)
6. [Database Migration Strategy](#database-migration-strategy)
7. [Bulk Tool Update Strategy](#bulk-tool-update-strategy)

---

## Issue 1: Rigid Category System

### Current State

The system uses three rigid, overly-specific categories:

| Current Category | Description | Problem |
|-----------------|-------------|---------|
| `surreal_realism` | Photorealistic with impossible elements | Too narrow - locks tools into specific visual rules |
| `high_octane_anime` | Sakuga-style anime action | Too specific - not all anime is "high octane" |
| `stylized_3d` | Stylized 3D/miniatures | Conflates style (3D) with presentation (miniatures) |

### Affected Files

```
app/models/workflow.py:29-35          → CategoryEnum definition
app/models/tool.py:96-98              → ToolMetadata.category field
app/agents/intent_tool_selector.py:142-215  → DEFAULT_TOOLS with hardcoded categories
app/services/tool_enhancer.py:23-196  → TOOL_ENHANCEMENT_SYSTEM_PROMPT with category rules
```

### Problems Identified

1. **Over-specification in Tool Enhancer Prompts**
   - The `TOOL_ENHANCEMENT_SYSTEM_PROMPT` enforces strict category-specific rules:
     - `stylized_3d` → "MUST use Tilt-Shift miniature look (35mm/50mm), NEVER anamorphic"
     - `surreal_realism` → "Wide-angle anamorphic (14–24mm)"
     - `high_octane_anime` → "Dynamic long lens (85–200mm)"
   - These rules are applied to ALL tools in a category, limiting creative flexibility

2. **Category-Tool Coupling**
   - Every tool MUST belong to exactly one category
   - Users can't create tools that blend styles (e.g., "realistic anime" or "stylized documentary")

3. **Frontend/API Confusion**
   - Users see "surreal_realism" when they might expect "Realistic"
   - Names are technical jargon, not user-friendly

### Proposed Solution: Simplified Categories

Replace the three specific categories with three intuitive parent categories:

| New Category | Maps From | Description |
|--------------|-----------|-------------|
| `realistic` | `surreal_realism` | Photorealistic and live-action styles |
| `anime` | `high_octane_anime` | 2D animated/anime styles (any energy level) |
| `animation` | `stylized_3d` | 3D animated, stylized, motion graphics |

---

## Issue 2: Instruction Following Failures

### Symptoms Reported

1. **Audio Ignores User Choice**: When `enable_audio=false`, videos still have audio
2. **Topic Not Followed**: User requests "background video" but gets a person speaking
3. **Subtitles Ignored**: Subtitle preferences not enforced
4. **Video Parameters Overridden**: Size/resolution choices ignored

### Root Cause Analysis

#### A. Audio Issue - Veo 3.1 API Limitation

**Location**: `app/services/veo.py:128-137`

```python
generation_config = types.GenerateVideosConfig(
    aspect_ratio=config.aspect_ratio.value,
    number_of_videos=1,
)
# NOTE: No audio parameter is set - Veo 3.1 generates audio by default
```

**Problem**: The Veo 3.1 API does not have an `enable_audio` parameter in `GenerateVideosConfig`. Audio is generated natively by default with no API-level control to disable it.

**Current Workaround Attempt** (Insufficient):

`app/agents/video_generator.py:365-368`:
```python
if not enable_audio:
    parts.append("- Audio: no audio, silent video\n")
```

This only adds text to the prompt, which Veo may ignore. It's not an API-level control.

#### B. Topic/Content Not Followed - Prompt Dilution

**Problem**: User topic gets mixed with:
- Tool-specific prompt templates (150+ words of technical jargon)
- Research data
- Style anchors
- Character references

The actual user intent gets buried in template boilerplate.

**Location**: `app/agents/video_generator.py:204-370` - `build_video_prompt()` function

The prompt structure prioritizes technical cinematographic directions over user content requirements.

#### C. Parameter Flow Gaps

**Observation**: Parameters flow correctly from API → Database → State → Agents

```
API (generate.py:284-299)
  → DB (workflow_data)
    → State (workflow_runner.py:174-189)
      → Video Generator (video_generator.py:444)
```

However, the enforcement is weak:
- Parameters are passed but only used as prompt hints, not hard constraints
- No validation that the generated video matches the requested parameters

---

## Root Cause Analysis

### Category System Issues

| Issue | Location | Impact |
|-------|----------|--------|
| Hardcoded CategoryEnum | `workflow.py:29-35` | Can't add/modify categories without code change |
| Category-specific optics rules | `tool_enhancer.py:91-93` | Forces lens/camera choices per category |
| Fallback always to "surreal_realism" | `intent_tool_selector.py:567-580` | Biases toward one category |

### Instruction Following Issues

| Issue | Location | Impact |
|-------|----------|--------|
| No Veo API audio control | `veo.py` | Cannot programmatically disable audio |
| Prompt text-only enforcement | `video_generator.py:365-368` | Veo ignores text instructions |
| Topic diluted in prompt | `video_generator.py:204-370` | User intent buried in templates |
| No post-generation validation | Entire pipeline | No check that output matches input |

---

## Recommended Fixes

### Fix 1: Simplify Categories (High Priority)

#### 1.1 Update CategoryEnum

**File**: `app/models/workflow.py`

```python
class CategoryEnum(str, Enum):
    """Video category/style enum - simplified parent categories."""
    AUTO = "auto"
    REALISTIC = "realistic"      # Was: surreal_realism
    ANIME = "anime"              # Was: high_octane_anime  
    ANIMATION = "animation"      # Was: stylized_3d
    
    # Aliases for backward compatibility (deprecated)
    SURREAL_REALISM = "realistic"
    HIGH_OCTANE_ANIME = "anime"
    STYLIZED_3D = "animation"
```

#### 1.2 Update Tool Enhancer Prompts

**File**: `app/services/tool_enhancer.py`

Remove rigid category-specific rules. Replace with guidance:

```markdown
## RABA Visual Categories (Simplified)

1. **realistic**: Live-action, photorealistic, documentary styles. 
   Guidance: Use camera techniques appropriate to subject matter.
   
2. **anime**: 2D animated, anime-inspired styles (any energy level).
   Guidance: Match animation intensity to content needs.
   
3. **animation**: 3D animated, motion graphics, stylized visuals.
   Guidance: Use style that serves the narrative.

## CRITICAL: Tool-Level Customization
Categories are HIGH-LEVEL guides only. Each tool defines its own:
- Camera/lens preferences
- Visual aesthetics
- Motion intensity
The category should NOT enforce rigid technical rules.
```

#### 1.3 Database Migration

Create migration to update existing tools:

```sql
-- Map old categories to new
UPDATE tools SET category = 'realistic' WHERE category = 'surreal_realism';
UPDATE tools SET category = 'anime' WHERE category = 'high_octane_anime';
UPDATE tools SET category = 'animation' WHERE category = 'stylized_3d';

-- Update workflows table
UPDATE workflows SET category = 'realistic' WHERE category = 'surreal_realism';
UPDATE workflows SET category = 'anime' WHERE category = 'high_octane_anime';
UPDATE workflows SET category = 'animation' WHERE category = 'stylized_3d';
```

---

### Fix 2: Audio Control - Post-Processing Solution (High Priority)

Since Veo 3.1 API doesn't support disabling audio, implement post-processing:

#### 2.1 Add FFmpeg Audio Strip

**New Function in**: `app/services/video_trimmer.py`

```python
async def strip_audio(video_path: str, output_path: str) -> str:
    """Remove audio track from video using FFmpeg.
    
    Args:
        video_path: Path to input video
        output_path: Path for output video (no audio)
        
    Returns:
        Path to processed video
    """
    cmd = [
        "ffmpeg", "-i", video_path,
        "-an",  # Remove audio
        "-c:v", "copy",  # Copy video stream (no re-encode)
        "-y", output_path
    ]
    # Execute and return output_path
```

#### 2.2 Update Video Generator to Call Strip

**File**: `app/agents/video_generator.py`

After video generation, if `enable_audio=False`:

```python
if not state.get("enable_audio", False):
    # Strip audio in post-processing
    from app.services.video_trimmer import strip_audio
    clean_video_path = await strip_audio(video_path, f"{video_path}_silent.mp4")
    # Upload clean video to storage
```

---

### Fix 3: Strengthen Topic/Intent Following (Medium Priority)

#### 3.1 Add User Intent Block at Prompt Start

**File**: `app/agents/video_generator.py`

Modify `build_video_prompt()` to ALWAYS start with user intent:

```python
def build_video_prompt(...):
    parts = []
    
    # USER INTENT FIRST - HIGHEST PRIORITY
    parts.append("[USER REQUEST - MUST FOLLOW EXACTLY]\n")
    parts.append(f"Topic: {topic}\n")
    if not enable_audio:
        parts.append("Audio: SILENT VIDEO - No speaking, no dialogue, no voice-over\n")
    if not enable_subtitles:
        parts.append("Subtitles: NO TEXT OVERLAYS of any kind\n")
    parts.append(f"Duration: {duration_seconds} seconds\n")
    parts.append(f"Style: {tool_category}\n")
    parts.append("\n[END USER REQUEST]\n\n")
    
    # Then add scene details, etc.
```

#### 3.2 Negative Prompt Enforcement

**File**: `app/services/veo.py`

Build stronger negative prompts based on user choices:

```python
def build_negative_prompt(enable_audio: bool, enable_subtitles: bool) -> str:
    negatives = ["text overlays", "watermarks", "logos", "UI elements", "low quality", "blurry"]
    
    if not enable_audio:
        negatives.extend(["speaking person", "moving lips", "dialogue scene", "voice-over"])
    
    if not enable_subtitles:
        negatives.extend(["subtitle text", "caption text", "on-screen text"])
    
    return ", ".join(negatives)
```

---

### Fix 4: Bulk Tool Update System (Medium Priority)

#### 4.1 API Endpoint for Bulk Category Migration

**File**: `app/api/routes/tools.py`

```python
@router.post("/bulk-migrate-categories")
async def bulk_migrate_categories(
    old_category: str,
    new_category: str,
    dry_run: bool = True
) -> dict:
    """Migrate tools from old category to new."""
    # Implementation
```

#### 4.2 Bulk Prompt Template Update

**File**: `app/api/routes/tools.py`

Enhance existing `/bulk-update` endpoint to handle category-aware prompt regeneration:

```python
@router.post("/bulk-improve")
async def bulk_improve_tools(
    request: BulkImproveRequest,
    regenerate_prompts: bool = True,
    update_category: Optional[str] = None
) -> BulkImproveResponse:
    """Bulk improve tools with optional category migration."""
```

---

## Implementation Plan

### Phase 1: Category Simplification (Week 1)

| Task | Priority | Effort | Files |
|------|----------|--------|-------|
| Update CategoryEnum with new values | High | 1hr | `workflow.py` |
| Add backward compatibility aliases | High | 1hr | `workflow.py` |
| Update tool_enhancer prompts | High | 2hr | `tool_enhancer.py` |
| Create DB migration script | High | 1hr | `migrations/` |
| Update intent_tool_selector defaults | Medium | 1hr | `intent_tool_selector.py` |
| Update API validation | Medium | 1hr | `generate.py`, `tools.py` |

### Phase 2: Audio Post-Processing (Week 1)

| Task | Priority | Effort | Files |
|------|----------|--------|-------|
| Implement `strip_audio()` function | High | 2hr | `video_trimmer.py` |
| Integrate into video_generator | High | 2hr | `video_generator.py` |
| Update output processor for clean videos | Medium | 1hr | `output_processor.py` |
| Test audio stripping pipeline | High | 2hr | `tests/` |

### Phase 3: Intent Following (Week 2)

| Task | Priority | Effort | Files |
|------|----------|--------|-------|
| Add USER REQUEST block to prompts | High | 2hr | `video_generator.py` |
| Implement dynamic negative prompts | Medium | 1hr | `veo.py` |
| Add prompt validation logging | Medium | 1hr | Logging |
| Test with various user inputs | High | 3hr | Manual testing |

### Phase 4: Bulk Tool Updates (Week 2)

| Task | Priority | Effort | Files |
|------|----------|--------|-------|
| Add bulk category migration endpoint | Medium | 2hr | `tools.py` |
| Add bulk prompt regeneration | Medium | 2hr | `tool_enhancer.py` |
| Run migration on existing tools | High | 1hr | DB operations |
| Validate migrated tools | High | 2hr | Manual review |

---

## Database Migration Strategy

### Migration Script

**File**: `migrations/migrate_categories.py`

```python
"""
Migrate category system from specific to simplified categories.

Old → New Mapping:
- surreal_realism → realistic
- high_octane_anime → anime
- stylized_3d → animation
"""

async def migrate_categories(dry_run: bool = True):
    mapping = {
        "surreal_realism": "realistic",
        "high_octane_anime": "anime",
        "stylized_3d": "animation",
    }
    
    # Update tools table
    for old, new in mapping.items():
        if dry_run:
            count = await count_tools_by_category(old)
            print(f"Would update {count} tools from '{old}' to '{new}'")
        else:
            await update_tools_category(old, new)
    
    # Update workflows table
    for old, new in mapping.items():
        if dry_run:
            count = await count_workflows_by_category(old)
            print(f"Would update {count} workflows from '{old}' to '{new}'")
        else:
            await update_workflows_category(old, new)
```

---

## Bulk Tool Update Strategy

### Approach

1. **Category Migration**: Update category field for all tools
2. **Prompt Regeneration**: Optionally regenerate prompts with new category guidance
3. **Validation**: Ensure all tools remain functional after migration

### API for Bulk Operations

```python
class BulkToolMigrationRequest(BaseModel):
    """Request for bulk tool migration."""
    migrate_categories: bool = True
    regenerate_prompts: bool = False
    improvement_hint: Optional[str] = None

class BulkToolMigrationResponse(BaseModel):
    """Response from bulk tool migration."""
    tools_updated: int
    tools_failed: list[str]
    category_mapping: dict[str, int]  # {category: count}
```

---

## Testing Checklist

### Category System Tests

- [ ] New categories accepted in API
- [ ] Old categories mapped to new (backward compat)
- [ ] Tool creation works with new categories
- [ ] Tool selection works with new categories
- [ ] Existing tools still functional after migration

### Audio Control Tests

- [ ] `enable_audio=false` produces silent video
- [ ] `enable_audio=true` produces video with audio
- [ ] Audio stripping doesn't affect video quality
- [ ] Silent videos play correctly in all browsers

### Instruction Following Tests

- [ ] User topic appears prominently in video
- [ ] "Background video" request produces no speaking person
- [ ] Subtitle preference respected
- [ ] Video duration matches request
- [ ] Aspect ratio matches request

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Old tools break after migration | Medium | High | Keep old category values as aliases |
| Audio stripping adds latency | Low | Medium | Use stream copy (no re-encode) |
| Veo still ignores prompt instructions | High | Medium | Post-processing fallbacks |
| Users confused by category name change | Low | Low | Update frontend labels simultaneously |

---

## Appendix: File Change Summary

### Files to Modify

| File | Changes |
|------|---------|
| `app/models/workflow.py` | Update CategoryEnum |
| `app/models/tool.py` | Update category validation |
| `app/agents/intent_tool_selector.py` | Update default tools, fallback logic |
| `app/services/tool_enhancer.py` | Remove rigid category rules |
| `app/services/veo.py` | Add dynamic negative prompts |
| `app/agents/video_generator.py` | Add USER REQUEST block, audio stripping |
| `app/services/video_trimmer.py` | Add `strip_audio()` function |
| `app/api/routes/tools.py` | Add bulk migration endpoints |
| `app/api/routes/generate.py` | Validate new categories |

### New Files

| File | Purpose |
|------|---------|
| `migrations/migrate_categories.py` | Category migration script |

---

## Critical: Tool Creation/Enhancer Maintenance

**IMPORTANT**: The tool creation and enhancement system (`app/services/tool_enhancer.py`) is the source of truth for prompt template generation. When making changes to:

- **Script prompt templates** - Update `TOOL_ENHANCEMENT_SYSTEM_PROMPT` and `TOOL_IMPROVEMENT_SYSTEM_PROMPT`
- **Image prompt templates** - Update both system prompts with new requirements
- **Video prompt templates** - Update both system prompts with new requirements
- **Instruction placeholders** - Add new placeholders to template requirements

The tool enhancer generates the prompt templates that tools use for script, image, and video generation. Any architectural changes to prompts must be reflected in:

1. **`TOOL_ENHANCEMENT_SYSTEM_PROMPT`** - For new tool creation
2. **`TOOL_IMPROVEMENT_SYSTEM_PROMPT`** - For improving existing tools
3. **Template validation** in `app/services/template_validation.py`

### Files to Update for Template Changes

| Change Type | Files to Modify |
|-------------|-----------------|
| New placeholder added | `tool_enhancer.py` (both prompts), `video_generator.py` (placeholder filling) |
| New template section | `tool_enhancer.py` (both prompts), relevant agent files |
| Category changes | `tool_enhancer.py`, `workflow.py`, `tool.py`, `intent_tool_selector.py` |
| Instruction following | `tool_enhancer.py`, `video_generator.py`, `script_writer.py` |

### Bulk Tool Update After Template Changes

After modifying template requirements, existing tools may need to be regenerated:

```python
# API endpoint to bulk-improve all tools with new template requirements
POST /api/v1/tools/bulk-improve
{
    "improvement_hint": "Update templates to include new USER REQUEST block",
    "regenerate_prompts": true,
    "dry_run": false
}
```

---

## Next Steps

1. **Review this plan** with stakeholders
2. **Prioritize** which fixes to implement first
3. **Create branch** for category simplification
4. **Implement and test** in development environment
5. **Run migration** on staging database
6. **Deploy** to production with monitoring

---

*Document created: January 2026*  
*Last updated: January 2026*
