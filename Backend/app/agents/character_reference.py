"""Character Reference Generator Agent.

Generates a character reference sheet if the script identifies a lead character.
"""

from typing import Any

from app.graph.state import VideoGenerationState
from app.models.overlay import CharacterReferenceImage, CharacterReferenceSheet
from app.models.image import ImageGenerationConfig, ImageModel, ImageAspectRatio, ImageResolution, StyleReference
from app.services.nano_banana import get_nano_banana_service
from app.services.supabase import get_supabase_client
from app.utils.logging import get_logger

logger = get_logger(__name__)


class CharacterReferenceGeneratorAgent:
    def __init__(self):
        self.nano = get_nano_banana_service()
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
            character_metadata={"category": category},
        )
        logger.info(f"Character reference sheet created for {name} with {len(refs)} views")
        
        # Persist character reference images to database
        await self._persist_to_database(workflow_id, refs, name)
        
        return {
            "character_reference_sheet": sheet.model_dump(),
        }
    
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
