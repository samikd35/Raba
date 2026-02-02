"""RABA Nano Banana Service.

Service for image generation using Nano Banana Pro (gemini-3-pro-image-preview)
and Nano Banana (gemini-2.5-flash-image) models.

Key Features:
- Text-to-image generation
- Image editing with reference images
- Sequential generation with style consistency
- Multi-image reference for character/style consistency

Reference:
- Backend/Documentations/nanao_banana_doc.md
- Backend/Documentations/nano_prompt_guide.md
- PHASE3_1_IMAGE_GENERATOR_PLAN.md
"""

import asyncio
import base64
import io
import os
import time
from typing import Optional

from google import genai
from google.genai import types
from PIL import Image
import math

from app.config import get_settings
from app.models.image import (
    GeneratedImage,
    ImageAspectRatio,
    ImageGenerationConfig,
    ImageModel,
    ImageResolution,
    StyleReference,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)

NANO_BANANA_PRO = "gemini-3-pro-image-preview"
NANO_BANANA_FLASH = "gemini-2.5-flash-image"

ASPECT_RATIO_MAP = {
    "9:16": ImageAspectRatio.PORTRAIT_9_16,
    "16:9": ImageAspectRatio.LANDSCAPE_16_9,
    "1:1": ImageAspectRatio.SQUARE,
    "4:3": ImageAspectRatio.LANDSCAPE_4_3,
    "3:4": ImageAspectRatio.PORTRAIT_3_4,
}

RESOLUTION_MAP = {
    "720p": ImageResolution.RES_1K,
    "1080p": ImageResolution.RES_2K,
    "4k": ImageResolution.RES_4K,
}


class NanoBananaService:
    """Service for Nano Banana image generation.

    Provides methods for:
    - Single image generation
    - Sequential generation with style consistency
    - Image editing with reference images
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Nano Banana service.

        Args:
            api_key: Google API key. If None, loads from settings.
        """
        settings = get_settings()
        self._api_key = api_key or settings.google_api_key

        if not self._api_key:
            raise ValueError("Google API key is required for Nano Banana image generation")

        self.client = genai.Client(api_key=self._api_key)
        self._initialized = True
        logger.info("NanoBananaService initialized with API key")

    async def generate_image(
        self,
        prompt: str,
        config: ImageGenerationConfig,
        style_reference: Optional[StyleReference] = None,
        reference_images: Optional[list[bytes]] = None,
    ) -> tuple[bytes, str, Optional[dict]]:
        """Generate a single image.

        Args:
            prompt: Text prompt for image generation
            config: Image generation configuration
            style_reference: Optional style reference for consistency
            reference_images: Optional list of reference image bytes

        Returns:
            Tuple of (image_bytes, text_response, usage_metadata)
        """
        start_time = time.time()
        model = config.model.value

        logger.info(f"Generating image with model: {model}")
        logger.info(f"Prompt: {prompt[:100]}...")

        contents = []

        if style_reference and style_reference.style_description:
            style_prompt = f"STYLE CONSISTENCY: {style_reference.style_description}\n\n"
            prompt = style_prompt + prompt

        if reference_images:
            for i, img_bytes in enumerate(reference_images[:5]):
                # Use inline_data for image parts per documentation
                contents.append(
                    types.Part(inline_data=types.Blob(data=img_bytes, mime_type="image/png"))
                )
            logger.info(f"Added {len(reference_images[:5])} reference images")

        # Add text prompt directly (SDK accepts strings in contents list)
        contents.append(prompt)

        # Build generation config with image_config for aspect ratio and resolution
        # Reference: nano_prompt_guide.md:4415-4550
        try:
            # Map aspect ratio and resolution to API format
            aspect_ratio_str = config.aspect_ratio.value  # Already in "9:16" format
            resolution_str = config.resolution.value  # Already in "1K", "2K", "4K" format

            # Create ImageConfig for aspect ratio and resolution
            # Note: For gemini-2.5-flash-image, only aspect_ratio is supported
            # For gemini-3-pro-image-preview, both aspect_ratio and image_size are supported
            if model == NANO_BANANA_PRO:
                image_config = types.ImageConfig(
                    aspect_ratio=aspect_ratio_str,
                    image_size=resolution_str,
                )
            else:
                # Nano Banana Flash only supports aspect_ratio
                image_config = types.ImageConfig(
                    aspect_ratio=aspect_ratio_str,
                )

            generation_config = types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
                image_config=image_config,
            )
            logger.info(
                f"Using image_config: aspect_ratio={aspect_ratio_str}, image_size={resolution_str if model == NANO_BANANA_PRO else 'N/A'}"
            )
        except Exception as e:
            logger.warning(f"ImageConfig not supported in SDK, using fallback: {e}")
            # Fallback: try without image_config
            try:
                generation_config = types.GenerateContentConfig(
                    response_modalities=["TEXT", "IMAGE"],
                )
            except Exception as e2:
                logger.debug(f"GenerateContentConfig creation failed, using dict: {e2}")
                generation_config = {"response_modalities": ["TEXT", "IMAGE"]}

        try:
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=model,
                contents=contents,
                config=generation_config,
            )

            image_bytes = None
            text_response = ""
            usage_metadata = None

            usage = getattr(response, "usage_metadata", None)
            if usage:
                try:
                    usage_metadata = {
                        "input_tokens": int(getattr(usage, "prompt_token_count", 0) or 0),
                        "output_tokens": int(getattr(usage, "candidates_token_count", 0) or 0),
                        "total_tokens": int(getattr(usage, "total_token_count", 0) or 0),
                    }
                except Exception:
                    usage_metadata = None

            for part in response.candidates[0].content.parts:
                if hasattr(part, "text") and part.text:
                    text_response = part.text
                    logger.info(f"Text response: {text_response[:100]}...")
                elif hasattr(part, "inline_data") and part.inline_data:
                    image_bytes = part.inline_data.data
                    logger.info("Image generated successfully")

            if image_bytes is None:
                raise ValueError("No image generated in response")

            # Post-process to enforce aspect ratio/resolution as fallback
            # This should rarely be needed if API respects image_config, but kept as safety net
            try:
                image_bytes = self._enforce_aspect_ratio(
                    image_bytes,
                    target_ar=config.aspect_ratio.value,
                    target_res=config.resolution.value,
                )
                logger.debug("Applied post-processing aspect ratio enforcement (fallback)")
            except Exception as ar_e:
                logger.warning(f"Aspect ratio enforcement failed, returning raw image: {ar_e}")

            generation_time = int((time.time() - start_time) * 1000)
            logger.info(f"Image generation completed in {generation_time}ms")

            return image_bytes, text_response, usage_metadata

        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            raise

    async def generate_image_with_retry(
        self,
        prompt: str,
        config: ImageGenerationConfig,
        style_reference: Optional[StyleReference] = None,
        reference_images: Optional[list[bytes]] = None,
    ) -> tuple[bytes, str, Optional[dict], int]:
        """Generate image with retry logic.

        Args:
            prompt: Text prompt for image generation
            config: Image generation configuration
            style_reference: Optional style reference
            reference_images: Optional reference images

        Returns:
            Tuple of (image_bytes, text_response, usage_metadata, retry_count)
        """
        last_error = None

        for attempt in range(config.max_retries):
            try:
                image_bytes, text_response, usage_metadata = await self.generate_image(
                    prompt=prompt,
                    config=config,
                    style_reference=style_reference,
                    reference_images=reference_images,
                )
                return image_bytes, text_response, usage_metadata, attempt

            except Exception as e:
                last_error = e
                logger.warning(f"Attempt {attempt + 1} failed: {e}")

                if attempt < config.max_retries - 1:
                    wait_time = 2**attempt
                    logger.info(f"Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)

                    if (
                        attempt == config.max_retries - 2
                        and config.model == ImageModel.NANO_BANANA_PRO
                    ):
                        logger.info("Falling back to Nano Banana Flash")
                        config.model = ImageModel.NANO_BANANA

        raise last_error

    async def generate_sequential_images(
        self,
        prompts: list[str],
        config: ImageGenerationConfig,
        initial_style_reference: Optional[StyleReference] = None,
        user_reference_image: Optional[bytes] = None,
        research_reference_images: Optional[list[bytes]] = None,
    ) -> list[tuple[bytes, str, Optional[dict], int]]:
        """Generate multiple images sequentially with style consistency.

        Each image uses the previous image as a style reference to maintain
        visual consistency across all images in the workflow.

        Reference images from research (Google Search + user uploads) are used
        to guide the initial style, then each generated image becomes a reference
        for subsequent images.

        Args:
            prompts: List of prompts for each image
            config: Image generation configuration
            initial_style_reference: Initial style reference (from user or research)
            user_reference_image: User-provided reference image bytes
            research_reference_images: Research images (Google Search) as style reference

        Returns:
            List of (image_bytes, text_response, usage_metadata, retry_count) tuples
        """
        results = []
        reference_images = []

        # Add research images as initial references for style consistency
        if research_reference_images:
            # Use up to 3 research images as reference (Nano Banana Pro supports up to 14)
            for img_bytes in research_reference_images[:3]:
                reference_images.append(img_bytes)
            logger.info(f"Using {len(reference_images)} research images as style reference")

        if user_reference_image:
            reference_images.append(user_reference_image)
            logger.info("Added user reference image for style consistency")

        style_reference = initial_style_reference or StyleReference()

        for i, prompt in enumerate(prompts):
            logger.info(f"Generating image {i + 1}/{len(prompts)}")

            # Build reference image list for current generation
            current_references = []

            # Add research images (style guide) - up to 2 for first image
            if research_reference_images and i == 0:
                current_references.extend(research_reference_images[:2])
                logger.debug(
                    f"Added {len(research_reference_images[:2])} research images as style reference"
                )

            # Add user reference (if first image)
            if i == 0 and user_reference_image:
                current_references.append(user_reference_image)
                logger.debug("Added user reference image for style consistency")

            # Add ALL previously generated images (up to 5 for Nano Banana Pro)
            # This ensures maximum consistency across the sequence
            if i > 0:
                # Use last 5 generated images as references (Nano Banana Pro supports up to 14 total)
                previous_generated = [
                    img
                    for img in reference_images
                    if img not in (research_reference_images or []) and img != user_reference_image
                ]
                if previous_generated:
                    # Use up to 5 most recent generated images
                    recent_images = (
                        previous_generated[-5:]
                        if len(previous_generated) > 5
                        else previous_generated
                    )
                    current_references.extend(recent_images)
                    logger.debug(
                        f"Added {len(recent_images)} previous generated images as references"
                    )

            consistency_prompt = self._build_consistency_prompt(
                prompt=prompt,
                scene_number=i + 1,
                total_scenes=len(prompts),
                style_reference=style_reference,
                is_first_image=(i == 0),
                previous_image_present=(i > 0),
            )

            (
                image_bytes,
                text_response,
                usage_metadata,
                retry_count,
            ) = await self.generate_image_with_retry(
                prompt=consistency_prompt,
                config=config,
                style_reference=style_reference,
                reference_images=current_references if current_references else None,
            )

            results.append((image_bytes, text_response, usage_metadata, retry_count))

            # Add generated image to reference pool for next iterations
            reference_images.append(image_bytes)

            if i == 0 and not style_reference.style_description:
                style_reference.style_description = (
                    "Maintain the exact same visual style, color palette, "
                    "lighting, and artistic treatment as the reference image. "
                    "Keep character appearances, proportions, and clothing consistent."
                )

            logger.info(
                f"Image {i + 1} generated, added to reference pool (total references: {len(reference_images)})"
            )

        return results

    def _enforce_aspect_ratio(self, image_bytes: bytes, target_ar: str, target_res: str) -> bytes:
        """Center-crop and resize image to match target aspect ratio and resolution.

        Args:
            image_bytes: Source image bytes
            target_ar: Aspect ratio string like "9:16", "16:9", "1:1"
            target_res: Resolution label: "1K" (1024), "2K" (2048), "4K" (4096)
        Returns:
            PNG bytes of the adjusted image
        """
        # Map resolution label to max dimension in pixels
        max_dim_map = {"1K": 1024, "2K": 2048, "4K": 4096}
        max_dim = max_dim_map.get(target_res, 2048)

        # Parse aspect ratio
        try:
            w_s, h_s = target_ar.split(":")
            ar_w = int(w_s)
            ar_h = int(h_s)
        except Exception:
            ar_w, ar_h = 9, 16
        target_ratio = ar_w / ar_h

        # Determine target dimensions (long side = max_dim)
        if target_ratio >= 1.0:
            # Landscape
            tgt_w = max_dim
            tgt_h = int(round(tgt_w / target_ratio))
        else:
            # Portrait / square where ratio < 1 means height dominates
            tgt_h = max_dim
            tgt_w = int(round(tgt_h * target_ratio))

        with Image.open(io.BytesIO(image_bytes)) as img:
            src_w, src_h = img.size
            src_ratio = src_w / src_h if src_h else target_ratio

            # Compute crop region to match aspect ratio, centered
            if abs(src_ratio - target_ratio) > 1e-3:
                if src_ratio > target_ratio:
                    # Too wide -> reduce width
                    new_w = int(round(src_h * target_ratio))
                    left = (src_w - new_w) // 2
                    box = (left, 0, left + new_w, src_h)
                else:
                    # Too tall -> reduce height
                    new_h = int(round(src_w / target_ratio))
                    top = (src_h - new_h) // 2
                    box = (0, top, src_w, top + new_h)
                img = img.crop(box)

            # Resize to target dimensions with high-quality filter
            img = img.resize((max(tgt_w, 1), max(tgt_h, 1)), Image.LANCZOS)

            # Ensure RGB/PNG output
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGB")
            out = io.BytesIO()
            img.save(out, format="PNG")
            return out.getvalue()

    def _build_consistency_prompt(
        self,
        prompt: str,
        scene_number: int,
        total_scenes: int,
        style_reference: StyleReference,
        is_first_image: bool,
        previous_image_present: bool = False,
    ) -> str:
        """Build prompt with STRONG style consistency instructions.

        Args:
            prompt: Original scene prompt
            scene_number: Current scene number
            total_scenes: Total number of scenes
            style_reference: Style reference with consistency info
            is_first_image: Whether this is the first image
            previous_image_present: Whether previous generated images exist as references

        Returns:
            Enhanced prompt with consistency instructions
        """
        parts = []

        if not is_first_image and previous_image_present:
            parts.append(
                "CRITICAL CONSISTENCY REQUIREMENTS - THIS IMAGE MUST MATCH THE REFERENCE IMAGE(S) EXACTLY:\n\n"
                "1. ART STYLE: Use the EXACT same rendering technique, line quality, brush strokes, "
                "and artistic treatment as the reference image(s).\n"
                "2. COLOR PALETTE: Match colors precisely - same hues, saturation levels, color grading, "
                "and overall color temperature.\n"
                "3. LIGHTING: Maintain identical lighting direction, intensity, shadow style, highlights, "
                "and overall illumination approach.\n"
                "4. CHARACTERS: If characters appear, they MUST look identical - same appearance, "
                "facial features, clothing, proportions, and physical characteristics.\n"
                "5. MOOD & ATMOSPHERE: Preserve the exact same emotional tone, visual mood, and "
                "atmospheric quality.\n"
                "6. COMPOSITION STYLE: Use similar framing, camera angle, perspective, and visual "
                "composition approach.\n"
                "7. TEXTURE & DETAIL: Match the level of detail, texture rendering, and surface quality.\n\n"
                "DO NOT deviate from the reference style. This is part of a video sequence and must be "
                "visually cohesive. The reference image(s) show the established visual style - follow it exactly.\n\n"
            )

        parts.append(f"[Scene {scene_number} of {total_scenes}]\n\n")

        if style_reference.character_descriptions:
            parts.append("CHARACTER CONSISTENCY - MAINTAIN THESE EXACTLY:\n")
            for char_desc in style_reference.character_descriptions:
                parts.append(f"- {char_desc}\n")
            parts.append("\n")

        if style_reference.color_palette:
            parts.append(
                f"COLOR PALETTE (MUST MATCH): {', '.join(style_reference.color_palette)}\n\n"
            )

        parts.append(prompt)

        return "".join(parts)

    async def download_image_as_bytes(self, url: str) -> bytes:
        """Download an image from URL and return as bytes.

        Args:
            url: Image URL to download

        Returns:
            Image bytes
        """
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise ValueError(f"Failed to download image: {response.status}")
                return await response.read()

    def image_to_base64(self, image_bytes: bytes) -> str:
        """Convert image bytes to base64 string.

        Args:
            image_bytes: Image bytes

        Returns:
            Base64 encoded string
        """
        return base64.b64encode(image_bytes).decode("utf-8")

    def base64_to_image(self, base64_string: str) -> bytes:
        """Convert base64 string to image bytes.

        Args:
            base64_string: Base64 encoded image

        Returns:
            Image bytes
        """
        return base64.b64decode(base64_string)


_nano_banana_service: Optional[NanoBananaService] = None


def get_nano_banana_service() -> NanoBananaService:
    """Get or create the NanoBananaService singleton.

    Returns:
        NanoBananaService instance
    """
    global _nano_banana_service
    if _nano_banana_service is None:
        _nano_banana_service = NanoBananaService()
    return _nano_banana_service
