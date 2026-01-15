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
    ) -> tuple[bytes, str]:
        """Generate a single image.
        
        Args:
            prompt: Text prompt for image generation
            config: Image generation configuration
            style_reference: Optional style reference for consistency
            reference_images: Optional list of reference image bytes
            
        Returns:
            Tuple of (image_bytes, text_response)
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
                    types.Part(
                        inline_data=types.Blob(
                            data=img_bytes,
                            mime_type="image/png"
                        )
                    )
                )
            logger.info(f"Added {len(reference_images[:5])} reference images")
        
        # Add text prompt directly (SDK accepts strings in contents list)
        contents.append(prompt)
        
        # Build generation config following documentation pattern
        # Note: image_config is NOT supported in types.GenerateContentConfig in current SDK
        # Only use response_modalities for basic image generation
        try:
            generation_config = types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
            )
        except Exception as e:
            logger.debug(f"GenerateContentConfig creation failed, using dict: {e}")
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
            
            for part in response.candidates[0].content.parts:
                if hasattr(part, "text") and part.text:
                    text_response = part.text
                    logger.info(f"Text response: {text_response[:100]}...")
                elif hasattr(part, "inline_data") and part.inline_data:
                    image_bytes = part.inline_data.data
                    logger.info("Image generated successfully")
            
            if image_bytes is None:
                raise ValueError("No image generated in response")
            
            generation_time = int((time.time() - start_time) * 1000)
            logger.info(f"Image generation completed in {generation_time}ms")
            
            return image_bytes, text_response
            
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            raise
    
    async def generate_image_with_retry(
        self,
        prompt: str,
        config: ImageGenerationConfig,
        style_reference: Optional[StyleReference] = None,
        reference_images: Optional[list[bytes]] = None,
    ) -> tuple[bytes, str, int]:
        """Generate image with retry logic.
        
        Args:
            prompt: Text prompt for image generation
            config: Image generation configuration
            style_reference: Optional style reference
            reference_images: Optional reference images
            
        Returns:
            Tuple of (image_bytes, text_response, retry_count)
        """
        last_error = None
        
        for attempt in range(config.max_retries):
            try:
                image_bytes, text_response = await self.generate_image(
                    prompt=prompt,
                    config=config,
                    style_reference=style_reference,
                    reference_images=reference_images,
                )
                return image_bytes, text_response, attempt
                
            except Exception as e:
                last_error = e
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                
                if attempt < config.max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    
                    if attempt == config.max_retries - 2 and config.model == ImageModel.NANO_BANANA_PRO:
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
    ) -> list[tuple[bytes, str, int]]:
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
            List of (image_bytes, text_response, retry_count) tuples
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
            
            consistency_prompt = self._build_consistency_prompt(
                prompt=prompt,
                scene_number=i + 1,
                total_scenes=len(prompts),
                style_reference=style_reference,
                is_first_image=(i == 0),
            )
            
            image_bytes, text_response, retry_count = await self.generate_image_with_retry(
                prompt=consistency_prompt,
                config=config,
                style_reference=style_reference,
                reference_images=reference_images[-3:] if reference_images else None,
            )
            
            results.append((image_bytes, text_response, retry_count))
            
            reference_images.append(image_bytes)
            
            if i == 0 and not style_reference.style_description:
                style_reference.style_description = (
                    "Maintain the exact same visual style, color palette, "
                    "lighting, and artistic treatment as the reference image. "
                    "Keep character appearances, proportions, and clothing consistent."
                )
            
            logger.info(f"Image {i + 1} generated, added to reference pool")
        
        return results
    
    def _build_consistency_prompt(
        self,
        prompt: str,
        scene_number: int,
        total_scenes: int,
        style_reference: StyleReference,
        is_first_image: bool,
    ) -> str:
        """Build prompt with style consistency instructions.
        
        Args:
            prompt: Original scene prompt
            scene_number: Current scene number
            total_scenes: Total number of scenes
            style_reference: Style reference with consistency info
            is_first_image: Whether this is the first image
            
        Returns:
            Enhanced prompt with consistency instructions
        """
        parts = []
        
        if not is_first_image:
            parts.append(
                "CRITICAL: This image MUST maintain EXACT visual consistency with the reference image(s). "
                "Match the following precisely:\n"
                "- Art style and rendering technique\n"
                "- Color palette and color grading\n"
                "- Lighting style and direction\n"
                "- Character appearances (if any)\n"
                "- Overall mood and atmosphere\n\n"
            )
        
        parts.append(f"[Scene {scene_number} of {total_scenes}]\n\n")
        
        if style_reference.character_descriptions:
            parts.append("CHARACTER CONSISTENCY:\n")
            for char_desc in style_reference.character_descriptions:
                parts.append(f"- {char_desc}\n")
            parts.append("\n")
        
        if style_reference.color_palette:
            parts.append(f"COLOR PALETTE: {', '.join(style_reference.color_palette)}\n\n")
        
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
