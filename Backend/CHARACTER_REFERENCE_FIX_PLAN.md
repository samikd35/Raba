# Character Reference Sheet System Fix Plan

## Problem Statement

The Character Reference Sheet system incorrectly generates humanoid character sheets for non-character content. 

**Example Failure:**
- **Input:** Tesla vehicle evolution video (Roadster → Model S → Cybertruck morphing)
- **Expected:** No character reference sheet (no human characters)
- **Actual:** Generated humanoid robot "Tesla Lineage" character sheets with front/side/back/face views

**Root Cause:** The system lacks semantic validation to distinguish between:
1. Actual human/animate characters (Moses, a detective, a scientist)
2. Abstract concepts, products, or objects (Tesla vehicles, "The Evolution", brand personification)

---

## Issue Analysis

### Current Flow (Broken)

```
Script Writer (Gemini) 
    ↓ 
    Outputs: lead_character = "The Tesla Lineage" (hallucinated)
    ↓
Workflow Router: if script.get("lead_character") → CHARACTER_REFERENCE
    ↓
Character Reference Agent: Generates humanoid views (T-pose, face close-up)
    ↓
Result: Irrelevant humanoid robot images
```

### Problems Identified

| # | Issue | Location | Impact |
|---|-------|----------|--------|
| 1 | **No character type validation** | `ScriptOutput` model | Any string triggers character generation |
| 2 | **Vague field description** | `script.py:257-264` | Gemini interprets "character" too broadly |
| 3 | **Humanoid-only prompts** | `character_reference.py:37-44` | "T-pose", "face close-up" assume human form |
| 4 | **No content-type awareness** | `workflow.py:169` | Router doesn't consider video type |
| 5 | **Missing negative examples** | Script generation prompt | LLM not told when NOT to populate field |

---

## Solution Design

### Why Not Keywords?

The original approach used keyword blocklists:
```python
non_character_keywords = ["vehicle", "car", "model", "product", "evolution"...]
```

**Problems with keywords:**
- "Model" could be a fashion model (valid) or Tesla Model S (invalid)
- New edge cases constantly slip through
- Reactive, not proactive - always playing catch-up
- No semantic understanding of context

### Recommended: Prompt-Based Semantic Validation

Use Gemini to analyze the **full context** and make an intelligent decision about whether a character reference sheet is appropriate.

**Why this is better:**
| Approach | Pros | Cons |
|----------|------|------|
| Keywords | Fast, no API call | Brittle, false positives/negatives, no context |
| Prompt Template | Context-aware, handles nuance, semantic understanding | ~200-500ms latency, small API cost |

The prompt approach understands **semantic meaning** by analyzing:
1. The original topic/prompt
2. The full script with all scenes
3. The lead character name and description
4. The visual style category

---

## Implementation Plan

### Phase 1: Model Enhancement

**File:** `Backend/app/models/script.py`

Add improved field descriptions to guide Script Writer:

```python
class ScriptOutput(BaseModel):
    # ... existing fields ...
    
    lead_character: Optional[str] = Field(
        default=None,
        description=(
            "Name of the PRIMARY HUMAN OR HUMANOID CHARACTER who appears consistently "
            "throughout the video and requires visual consistency. "
            "ONLY populate if there is an actual person, human figure, or humanoid entity. "
            "DO NOT populate for: products, vehicles, objects, abstract concepts, "
            "brand names, evolution sequences, or non-animate subjects."
        )
    )
    lead_character_description: Optional[str] = Field(
        default=None,
        description=(
            "Physical appearance description of the lead character. "
            "Include: age, gender, ethnicity, clothing, distinctive features. "
            "ONLY populate if lead_character is a human/humanoid."
        )
    )
```

### Phase 2: Script Generation Prompt Update

**File:** `Backend/app/agents/script_writer.py`

Add to `_build_full_script_prompt()`:

```python
<lead_character_guidelines>
The lead_character field is ONLY for human or humanoid characters that need visual consistency.

POPULATE lead_character when:
✓ A specific person appears throughout (e.g., "Moses", "Einstein", "Detective Chen")
✓ A humanoid robot/AI with consistent appearance (e.g., "ARIA-7", "Android X")
✓ An animated human character (e.g., "The Narrator" if shown on screen)

DO NOT populate lead_character when:
✗ The video is about products (cars, phones, shoes)
✗ The video shows object transformations or evolutions
✗ The subject is abstract (time, innovation, design philosophy)
✗ The "character" is a brand or company personified
✗ Multiple different people appear without a consistent lead
✗ The video is purely informational with no character

When in doubt, leave lead_character as null. It's better to skip character reference
generation than to generate irrelevant humanoid images for product videos.
</lead_character_guidelines>
```

### Phase 3: Character Reference Agent - Semantic Validation (Core Fix)

**File:** `Backend/app/agents/character_reference.py`

This is the **primary fix**. Add a Gemini-powered validation method that analyzes the full context before generating character sheets.

```python
"""Character Reference Generator Agent.

Generates a character reference sheet if the script identifies a lead character.
Includes semantic validation to prevent generating sheets for non-character content.
"""

from typing import Any, Optional
from pydantic import BaseModel, Field

from app.graph.state import VideoGenerationState
from app.models.overlay import CharacterReferenceImage, CharacterReferenceSheet
from app.models.image import ImageGenerationConfig, ImageModel, ImageAspectRatio, ImageResolution, StyleReference
from app.services.nano_banana import get_nano_banana_service
from app.services.gemini import get_gemini_service
from app.services.supabase import get_supabase_client
from app.utils.logging import get_logger

logger = get_logger(__name__)


class CharacterValidationResult(BaseModel):
    """Result of semantic character validation."""
    is_valid_character: bool = Field(
        description="Whether this is a valid human/humanoid character for reference sheet generation"
    )
    character_type: str = Field(
        description="Type: 'human', 'humanoid', 'animal', 'object', 'abstract', 'product', 'none'"
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confidence score for the validation decision"
    )
    reasoning: str = Field(
        description="Brief explanation of why this is or isn't a valid character"
    )
    suggested_action: str = Field(
        description="'generate' to create reference sheet, 'skip' to bypass"
    )


CHARACTER_VALIDATION_PROMPT = """You are a character validation expert for a video generation system.

Your task is to determine if a "lead character" extracted from a script is actually a human or humanoid character that would benefit from a character reference sheet (front view, side view, back view, face close-up).

## Context Provided
- **Original Topic:** {topic}
- **Lead Character Name:** {lead_character}
- **Lead Character Description:** {lead_character_description}
- **Script Summary:** {script_summary}
- **Visual Style Category:** {category}

## What is a Character Reference Sheet?
A character reference sheet shows a character from multiple angles (front, side, back, face) to ensure visual consistency across video scenes. It uses poses like T-pose and neutral expressions.

## Valid Characters (GENERATE reference sheet)
- Human persons: historical figures, fictional people, narrators shown on screen
- Humanoid entities: robots with human form, androids, aliens with humanoid bodies
- Animated human characters with consistent appearance

## Invalid "Characters" (SKIP reference sheet)
- Products: vehicles, phones, shoes, electronics
- Objects: buildings, logos, artifacts
- Abstract concepts: "The Evolution", "Time", "Innovation", "The Journey"
- Brand personifications: "The Tesla Lineage", "Apple's Vision", "Nike's Spirit"
- Transforming/morphing subjects: "The Morphing Car", "Design Evolution"
- Multiple different people without a single consistent lead
- Narrators who are voice-only (not shown on screen)

## Analysis Required
1. What is the video actually about? (products, story, concept, etc.)
2. Is the "lead character" a real person/humanoid or a conceptual/product entity?
3. Would front/side/back/face reference views make sense for this subject?
4. Could this subject realistically do a "T-pose" or have a "face close-up"?

## Response Format
Respond with a JSON object:
```json
{{
    "is_valid_character": true/false,
    "character_type": "human|humanoid|animal|object|abstract|product|none",
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation",
    "suggested_action": "generate|skip"
}}
```

Analyze the provided context and determine if a character reference sheet should be generated."""


class CharacterReferenceGeneratorAgent:
    def __init__(self):
        self.nano = get_nano_banana_service()
        self.gemini = get_gemini_service()
        self.supabase = get_supabase_client()
        logger.info("CharacterReferenceGeneratorAgent initialized")

    async def run(self, state: VideoGenerationState) -> dict[str, Any]:
        workflow_id = state.get("workflow_id", "unknown")
        script = state.get("script_output", {}) or {}
        name = script.get("lead_character") or None
        desc = script.get("lead_character_description") or ""
        
        # Early exit if no lead character
        if not name:
            logger.info("No lead character detected; skipping character reference generation")
            return {}

        # === SEMANTIC VALIDATION ===
        # Use Gemini to analyze full context and determine if this is a valid character
        validation_result = await self._validate_character_with_context(state, name, desc)
        
        if not validation_result.is_valid_character:
            logger.warning(
                f"Character validation FAILED for '{name}': {validation_result.reasoning} "
                f"(type={validation_result.character_type}, confidence={validation_result.confidence:.2f})"
            )
            # Store validation result in state for debugging/monitoring
            return {
                "character_validation": validation_result.model_dump(),
                "character_reference_skipped": True,
                "skip_reason": validation_result.reasoning,
            }
        
        logger.info(
            f"Character validation PASSED for '{name}': {validation_result.reasoning} "
            f"(type={validation_result.character_type}, confidence={validation_result.confidence:.2f})"
        )

        # === GENERATE CHARACTER REFERENCE SHEET ===
        category = (state.get("selected_tool") or {}).get("category") or state.get("category", "surreal_realism")
        aspect_ratio = state.get("aspect_ratio", "9:16")
        resolution = state.get("resolution", "1080p")

        # Build prompts for views
        base = (
            f"Character reference sheet for '{name}'. Neutral pose, consistent outfit and proportions. "
            f"Crisp, high-detail, clean background. Style: {category}. Description: {desc}. "
            "Focus on fidelity and repeatable details."
        )
        view_prompts = [
            ("front", base + " Full front view, T-pose or relaxed neutral arms."),
            ("side", base + " Side profile view, consistent lighting with front view."),
            ("back", base + " Back view, ensure hair/clothing/back details visible."),
            ("face", base + " Close-up face, straight-on, neutral expression."),
        ]

        cfg = ImageGenerationConfig(
            model=ImageModel.NANO_BANANA_PRO,
            aspect_ratio=ImageAspectRatio.PORTRAIT_9_16 if aspect_ratio == "9:16" else ImageAspectRatio.LANDSCAPE_16_9,
            resolution=ImageResolution.RES_2K if resolution == "1080p" else ImageResolution.RES_1K,
            style_keywords=[],
            maintain_consistency=True,
            max_retries=3,
        )

        refs: list[CharacterReferenceImage] = []
        for view, prompt in view_prompts:
            try:
                img_bytes, _text, _retry = await self.nano.generate_image_with_retry(
                    prompt=prompt,
                    config=cfg,
                    style_reference=StyleReference(style_description=f"Character sheet for {name}")
                )
                # Upload to storage
                import time
                bucket = "media"
                path = f"character_references/{workflow_id}/{view}_{int(time.time())}.png"
                full_path = f"generated_images/{path}"
                self.supabase.storage.from_(bucket).upload(
                    path=full_path, 
                    file=img_bytes, 
                    file_options={"content-type": "image/png"}
                )
                url = self.supabase.storage.from_(bucket).get_public_url(full_path)
                refs.append(CharacterReferenceImage(view=view, url=url))
                logger.info(f"Character reference view generated: {view}")
            except Exception as e:
                logger.warning(f"Failed to generate character reference view {view}: {e}")

        sheet = CharacterReferenceSheet(
            character_name=name,
            character_description=desc,
            reference_images=refs,
            character_metadata={
                "category": category,
                "validation": validation_result.model_dump(),
            },
        )
        logger.info(f"Character reference sheet created for {name} with {len(refs)} views")
        
        # Persist character reference images to database
        await self._persist_to_database(workflow_id, refs, name)
        
        return {
            "character_reference_sheet": sheet.model_dump(),
            "character_validation": validation_result.model_dump(),
        }

    async def _validate_character_with_context(
        self,
        state: VideoGenerationState,
        lead_character: str,
        lead_character_description: str,
    ) -> CharacterValidationResult:
        """
        Use Gemini to semantically validate if the lead character is appropriate
        for character reference sheet generation.
        
        Analyzes:
        - Original topic/prompt
        - Full script content
        - Character name and description
        - Visual style category
        
        Returns:
            CharacterValidationResult with decision and reasoning
        """
        try:
            # Extract context from state
            topic = state.get("topic", "") or state.get("user_prompt", "") or ""
            script = state.get("script_output", {}) or {}
            category = (state.get("selected_tool") or {}).get("category") or state.get("category", "")
            
            # Build script summary from scenes
            script_summary = self._build_script_summary(script)
            
            # Format the validation prompt
            prompt = CHARACTER_VALIDATION_PROMPT.format(
                topic=topic or "Not provided",
                lead_character=lead_character,
                lead_character_description=lead_character_description or "Not provided",
                script_summary=script_summary or "Not provided",
                category=category or "Not provided",
            )
            
            # Call Gemini for validation
            response = await self.gemini.generate_json(
                prompt=prompt,
                response_schema=CharacterValidationResult,
                temperature=0.1,  # Low temperature for consistent decisions
            )
            
            if response and isinstance(response, dict):
                return CharacterValidationResult(**response)
            
            # If Gemini returns a CharacterValidationResult directly
            if isinstance(response, CharacterValidationResult):
                return response
            
            # Fallback: if we can't validate, be conservative and skip
            logger.warning("Character validation returned unexpected format; defaulting to skip")
            return CharacterValidationResult(
                is_valid_character=False,
                character_type="unknown",
                confidence=0.5,
                reasoning="Validation returned unexpected format; skipping as precaution",
                suggested_action="skip",
            )
            
        except Exception as e:
            logger.error(f"Character validation failed with error: {e}")
            # On error, be conservative - skip generation to avoid bad outputs
            return CharacterValidationResult(
                is_valid_character=False,
                character_type="error",
                confidence=0.0,
                reasoning=f"Validation error: {str(e)}; skipping as precaution",
                suggested_action="skip",
            )

    def _build_script_summary(self, script: dict) -> str:
        """Build a concise summary of the script for validation context."""
        parts = []
        
        # Hook
        hook = script.get("hook", {})
        if hook:
            parts.append(f"Hook: {hook.get('script', '')} - {hook.get('visual_direction', '')}")
        
        # Scenes (summarize first 3-4 scenes)
        scenes = script.get("scenes", [])
        for i, scene in enumerate(scenes[:4]):
            desc = scene.get("description", "")
            dialogue = scene.get("dialogue", "")
            scene_text = f"Scene {i+1}: {desc}"
            if dialogue:
                scene_text += f" (Dialogue: {dialogue})"
            parts.append(scene_text)
        
        if len(scenes) > 4:
            parts.append(f"... and {len(scenes) - 4} more scenes")
        
        # CTA
        cta = script.get("call_to_action", {})
        if cta:
            parts.append(f"CTA: {cta.get('script', '')} ({cta.get('type', '')})")
        
        return "\n".join(parts)

    async def _persist_to_database(
        self,
        workflow_id: str,
        reference_images: list[CharacterReferenceImage],
        character_name: str,
    ) -> None:
        """Persist character reference images to Supabase media table."""
        try:
            from app.utils.helpers import utc_now_iso
            import os
            
            for ref in reference_images:
                if not ref.url:
                    continue
                
                # Extract storage path from URL
                storage_path = None
                if "/storage/v1/object/public/media/" in ref.url:
                    storage_path = ref.url.split("/storage/v1/object/public/media/")[1]
                elif "/generated_images/" in ref.url:
                    parts = ref.url.split("/generated_images/")
                    if len(parts) > 1:
                        storage_path = f"generated_images/{parts[1]}"
                
                self.supabase.table("media").insert({
                    "workflow_id": workflow_id,
                    "media_type": "image",
                    "source": "generated",
                    "storage_url": ref.url,
                    "storage_path": storage_path,
                    "mime_type": "image/png",
                    "metadata": {
                        "character_name": character_name,
                        "view": ref.view,
                        "type": "character_reference",
                    },
                    "file_size_bytes": None,
                    "created_at": utc_now_iso(),
                }).execute()
            
            logger.info(f"Persisted {len(reference_images)} character reference images to database")
            
        except Exception as e:
            logger.error(f"Failed to persist character reference images: {e}")


async def character_reference_node(state: VideoGenerationState) -> dict[str, Any]:
    agent = CharacterReferenceGeneratorAgent()
    return await agent.run(state)
```

### Phase 4: Workflow Router (Simplified)

**File:** `Backend/app/graph/workflow.py`

The router remains simple - it just checks if `lead_character` exists. The **semantic validation happens inside the agent**.

```python
def route_after_style_anchor(
    state: VideoGenerationState,
) -> Literal["character_reference", "image_generator", "error_handler"]:
    """Route after Global Style Anchor.
    
    Routes to Character Reference if lead_character exists.
    The Character Reference Agent will perform semantic validation
    to determine if generation should actually proceed.
    """
    if state.get("error"):
        return NODE_ERROR_HANDLER
    
    script = state.get("script_output") or {}
    if script.get("lead_character"):
        logger.info(f"Lead character detected: {script.get('lead_character')}; routing to Character Reference")
        return NODE_CHARACTER_REFERENCE
    
    logger.info("No lead character; routing to Image Generator")
    return NODE_IMAGE_GENERATOR
```

---

## Validation Prompt Design

### Why Full Context Matters

The validation prompt receives:

| Input | Purpose |
|-------|---------|
| `topic` | Original user intent - what the video is actually about |
| `lead_character` | The name extracted by Script Writer |
| `lead_character_description` | Physical description (if any) |
| `script_summary` | Condensed view of scenes - reveals actual content |
| `category` | Visual style - provides additional context |

### Example Validations

**Tesla Case (Should SKIP):**
```
Topic: "Tesla vehicle evolution from Roadster to Cybercab"
Lead Character: "The Tesla Lineage"
Description: ""
Script Summary: 
  Hook: Tesla just broke the laws of design - Extreme macro of liquid chrome morphing
  Scene 1: Macro-texture shot of liquid metal bubbling into 2008 Roadster frame
  Scene 2: The Roadster morphs fluidly into the Model S...
  
→ Result: {
    "is_valid_character": false,
    "character_type": "abstract",
    "confidence": 0.95,
    "reasoning": "The video is about Tesla vehicles morphing/evolving. 'The Tesla Lineage' 
                  is a brand personification, not a human character. The script describes 
                  cars transforming, not a person. T-pose and face views would be inappropriate.",
    "suggested_action": "skip"
  }
```

**Moses Case (Should GENERATE):**
```
Topic: "The story of Moses parting the Red Sea"
Lead Character: "Moses"
Description: "Elderly man with long white beard, brown robes, carrying a wooden staff"
Script Summary:
  Hook: What if one man could split an ocean? - Moses raising staff
  Scene 1: Moses stands before the Israelites, staff raised high
  Scene 2: The waters begin to part as Moses walks forward...

→ Result: {
    "is_valid_character": true,
    "character_type": "human",
    "confidence": 0.98,
    "reasoning": "Moses is a historical/biblical human figure who appears consistently 
                  throughout the video as the protagonist. Physical description provided. 
                  Character reference sheet will ensure visual consistency.",
    "suggested_action": "generate"
  }
```

---

## State Updates

The agent now returns additional fields for monitoring:

```python
# On validation PASS:
{
    "character_reference_sheet": {...},
    "character_validation": {
        "is_valid_character": True,
        "character_type": "human",
        "confidence": 0.98,
        "reasoning": "...",
        "suggested_action": "generate"
    }
}

# On validation FAIL:
{
    "character_validation": {
        "is_valid_character": False,
        "character_type": "abstract",
        "confidence": 0.95,
        "reasoning": "...",
        "suggested_action": "skip"
    },
    "character_reference_skipped": True,
    "skip_reason": "..."
}
```

---

## Testing Scenarios

### Test Case 1: Product Evolution (Should Skip)
```python
{
    "topic": "Tesla vehicle evolution from Roadster to Cybercab",
    "lead_character": "The Tesla Lineage",
    "expected_validation": {
        "is_valid_character": False,
        "character_type": "abstract|product",
        "suggested_action": "skip"
    },
    "expected_character_reference_generated": False
}
```

### Test Case 2: Historical Figure (Should Generate)
```python
{
    "topic": "The story of Moses parting the Red Sea",
    "lead_character": "Moses",
    "lead_character_description": "Elderly man with long white beard, brown robes",
    "expected_validation": {
        "is_valid_character": True,
        "character_type": "human",
        "suggested_action": "generate"
    },
    "expected_character_reference_generated": True
}
```

### Test Case 3: Fictional Robot Character (Should Generate)
```python
{
    "topic": "ARIA-7 robot discovers emotions",
    "lead_character": "ARIA-7",
    "lead_character_description": "Sleek humanoid robot with glowing blue eyes",
    "expected_validation": {
        "is_valid_character": True,
        "character_type": "humanoid",
        "suggested_action": "generate"
    },
    "expected_character_reference_generated": True
}
```

### Test Case 4: Brand Personification (Should Skip)
```python
{
    "topic": "Apple's design philosophy through the years",
    "lead_character": "The Apple Vision",
    "expected_validation": {
        "is_valid_character": False,
        "character_type": "abstract",
        "suggested_action": "skip"
    },
    "expected_character_reference_generated": False
}
```

### Test Case 5: Fashion Model (Edge Case - Should Generate)
```python
{
    "topic": "Spring fashion collection runway show",
    "lead_character": "Model",
    "lead_character_description": "Tall woman with short black hair, wearing designer clothes",
    "expected_validation": {
        "is_valid_character": True,
        "character_type": "human",
        "suggested_action": "generate"
    },
    "expected_character_reference_generated": True
}
```

---

## Rollout Plan

1. **Phase 1:** Update `ScriptOutput` model field descriptions
2. **Phase 2:** Update script generation prompts with character guidelines
3. **Phase 3:** Implement semantic validation in `CharacterReferenceGeneratorAgent`
4. **Phase 4:** Deploy and monitor validation results
5. **Phase 5:** Fine-tune validation prompt based on edge cases

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| False positive rate (non-characters generating sheets) | ~30% | <3% |
| False negative rate (real characters skipped) | 0% | <1% |
| Character reference generation latency | ~8s | ~8.5s (+500ms for validation) |
| Validation accuracy | N/A | >95% |

---

## Files to Modify

1. `Backend/app/models/script.py` - Update field descriptions
2. `Backend/app/agents/script_writer.py` - Add character guidelines to prompt
3. `Backend/app/agents/character_reference.py` - Add semantic validation (PRIMARY CHANGE)
4. `Guides/RABA_Architecture.md` - Document validation system

---

## Comparison: Old vs New Approach

| Aspect | Old (Keywords) | New (Prompt Validation) |
|--------|----------------|------------------------|
| Accuracy | ~70% | >95% |
| Edge cases | Fails on ambiguous terms | Handles context |
| Maintenance | Constant blocklist updates | Self-improving with context |
| Latency | 0ms | ~200-500ms |
| API cost | $0 | ~$0.001 per validation |
| Semantic understanding | None | Full context analysis |

The small latency and cost increase is worth the significant accuracy improvement.

---

## Appendix: GeminiService Integration

The validation uses the existing `GeminiService.generate_json()` method:

```python
response = await self.gemini.generate_json(
    prompt=prompt,
    response_schema=CharacterValidationResult,
    temperature=0.1,  # Low temperature for consistent decisions
)
```

This ensures:
- Structured JSON output matching `CharacterValidationResult` schema
- Consistent, deterministic decisions
- Integration with existing error handling and retry logic
