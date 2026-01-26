"""Character Reference Generator Agent.

Generates a character reference sheet if the script identifies a lead character.
Includes semantic validation to prevent generating sheets for non-character content.
"""

from typing import Any

from app.graph.state import VideoGenerationState
from app.models.overlay import CharacterReferenceImage, CharacterReferenceSheet
from app.models.image import ImageGenerationConfig, ImageModel, ImageAspectRatio, ImageResolution, StyleReference
from app.services.nano_banana import get_nano_banana_service
from app.services.gemini import get_gemini_service
from app.services.supabase import get_supabase_client
from app.utils.logging import get_logger

logger = get_logger(__name__)


# Validation result model for semantic character validation
from pydantic import BaseModel, Field


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

Your task is to determine if a \"lead character\" extracted from a script is actually a human or humanoid character that would benefit from a character reference sheet (front view, side view, back view, face close-up).

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

## Invalid \"Characters\" (SKIP reference sheet)
- Products: vehicles, phones, shoes, electronics
- Objects: buildings, logos, artifacts
- Abstract concepts: \"The Evolution\", \"Time\", \"Innovation\", \"The Journey\"
- Brand personifications: \"The Tesla Lineage\", \"Apple's Vision\", \"Nike's Spirit\"
- Transforming/morphing subjects: \"The Morphing Car\", \"Design Evolution\"
- Multiple different people without a single consistent lead
- Narrators who are voice-only (not shown on screen)

## Analysis Required
1. What is the video actually about? (products, story, concept, etc.)
2. Is the \"lead character\" a real person/humanoid or a conceptual/product entity?
3. Would front/side/back/face reference views make sense for this subject?
4. Could this subject realistically do a \"T-pose\" or have a \"face close-up\"?

## Response Format
Respond with a JSON object:
{{
    "is_valid_character": true/false,
    "character_type": "human|humanoid|animal|object|abstract|product|none",
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation",
    "suggested_action": "generate|skip"
}}

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
        if not name:
            logger.info("No lead character detected; skipping character reference generation")
            return {}

        # Semantic validation to ensure this is a real character, not a product/abstract
        validation_result = await self._validate_character_with_context(
            state=state,
            lead_character=name,
            lead_character_description=desc,
        )

        if not validation_result.is_valid_character:
            logger.warning(
                f"Character validation FAILED for '{name}': {validation_result.reasoning} "
                f"(type={validation_result.character_type}, confidence={validation_result.confidence:.2f})"
            )
            return {
                "character_validation": validation_result.model_dump(),
                "character_reference_skipped": True,
                "skip_reason": validation_result.reasoning,
            }

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
            ("front", base + " Full front view, T-pose or relaxed neutral arms.")
            ,("side", base + " Side profile view, consistent lighting with front view.")
            ,("back", base + " Back view, ensure hair/clothing/back details visible.")
            ,("face", base + " Close-up face, straight-on, neutral expression.")
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
                self.supabase.storage.from_(bucket).upload(path=full_path, file=img_bytes, file_options={"content-type": "image/png"})
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
        """Use Gemini to semantically validate if the lead character warrants a reference sheet."""
        try:
            # Extract context
            topic = state.get("topic", "") or state.get("user_prompt", "") or ""
            script = state.get("script_output", {}) or {}
            category = (state.get("selected_tool") or {}).get("category") or state.get("category", "")

            # Summarize script
            script_summary = self._build_script_summary(script)

            prompt = CHARACTER_VALIDATION_PROMPT.format(
                topic=topic or "Not provided",
                lead_character=lead_character,
                lead_character_description=lead_character_description or "Not provided",
                script_summary=script_summary or "Not provided",
                category=category or "Not provided",
            )

            resp = await self.gemini.generate_structured_output(
                prompt=prompt,
                response_model=CharacterValidationResult,
                temperature=0.1,
                video_id=state.get("workflow_id"),
            )
            return resp
        except Exception as e:
            logger.error(f"Character validation failed with error: {e}")
            return CharacterValidationResult(
                is_valid_character=False,
                character_type="error",
                confidence=0.0,
                reasoning=f"Validation error: {str(e)}; skipping as precaution",
                suggested_action="skip",
            )

    def _build_script_summary(self, script: dict) -> str:
        """Build a concise summary of the script for validation context."""
        parts: list[str] = []
        try:
            hook = script.get("hook", {}) or {}
            if hook:
                parts.append(
                    f"Hook: {hook.get('script', '')} - {hook.get('visual_direction', '')}"
                )

            scenes = script.get("scenes", []) or []
            for i, scene in enumerate(scenes[:4]):
                desc = scene.get("description", "") or ""
                dialogue = scene.get("dialogue", "") or ""
                o = f"Scene {i+1}: {desc}"
                if dialogue:
                    o += f" | Dialogue: {dialogue}"
                parts.append(o)

            cta = script.get("call_to_action", {}) or {}
            if cta and cta.get("script"):
                parts.append(f"CTA: {cta.get('script')}")
        except Exception:
            # If script is malformed, just return empty summary
            pass
        return "\n".join([p for p in parts if p])
    
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
                # URL format: https://...supabase.co/storage/v1/object/public/media/generated_images/...
                storage_path = None
                if "/storage/v1/object/public/media/" in ref.url:
                    storage_path = ref.url.split("/storage/v1/object/public/media/")[1]
                elif "/generated_images/" in ref.url:
                    # Fallback: construct path if URL format is different
                    parts = ref.url.split("/generated_images/")
                    if len(parts) > 1:
                        storage_path = f"generated_images/{parts[1]}"
                
                # Get file size from storage if possible
                file_size_bytes = None
                try:
                    bucket = "media"
                    if storage_path:
                        # Try to get file info from storage
                        file_info = self.supabase.storage.from_(bucket).list(
                            path=os.path.dirname(storage_path),
                            search=os.path.basename(storage_path)
                        )
                        # Note: Supabase storage list doesn't return size directly
                        # We'll leave it as None for now
                except Exception:
                    pass
                
                self.supabase.table("media").insert({
                    "workflow_id": workflow_id,
                    "media_type": "image",  # Allowed: image, video, audio
                    "source": "generated",  # Allowed: user_upload, research, generated
                    "storage_url": ref.url,
                    "storage_path": storage_path,
                    "mime_type": "image/png",
                    "metadata": {
                        "character_name": character_name,
                        "view": ref.view,
                        "type": "character_reference",
                    },
                    "file_size_bytes": file_size_bytes,
                    "created_at": utc_now_iso(),
                }).execute()
            
            logger.info(f"Persisted {len(reference_images)} character reference images to database for workflow {workflow_id}")
            
        except Exception as e:
            logger.error(f"Failed to persist character reference images to database: {e}")


async def character_reference_node(state: VideoGenerationState) -> dict[str, Any]:
    agent = CharacterReferenceGeneratorAgent()
    return await agent.run(state)
