"""RABA Veo Service.

Service for video generation using Veo 3.1 (veo-3.1-generate-preview)
and Veo 3.1 Fast (veo-3.1-fast-generate-preview) models.

Key Features:
- Text-to-video generation with reference images
- Image-to-video generation (first frame)
- Video extension for seamless multi-segment videos
- Native audio generation with dialogue sync
- Asynchronous operation polling

Reference: 
- Backend/Documentations/veo_doc.md
- Backend/Documentations/veo_prompting_guide.md
- PHASE3_2_VIDEO_GENERATOR_PLAN.md
"""

import asyncio
import time
from typing import Optional

from google import genai
from google.genai import types

from app.config import get_settings
from app.models.video import (
    GeneratedVideo,
    VideoAspectRatio,
    VideoGenerationConfig,
    VideoModel,
    VideoResolution,
    VideoSegment,
    VideoSegmentType,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)

VEO_3_1 = "veo-3.1-generate-preview"
VEO_3_1_FAST = "veo-3.1-fast-generate-preview"

MAX_POLL_ATTEMPTS = 36  # 6 minutes at 10s intervals
DEFAULT_POLL_INTERVAL = 10
MAX_REFERENCE_IMAGES = 3


class VeoServiceError(Exception):
    """Base exception for Veo service errors."""
    pass


class VideoGenerationTimeoutError(VeoServiceError):
    """Raised when video generation times out."""
    pass


class VideoGenerationFailedError(VeoServiceError):
    """Raised when video generation fails."""
    pass


class VeoService:
    """Service for Veo 3.1 video generation.
    
    Provides methods for:
    - Text-to-video generation with reference images
    - Image-to-video generation
    - Video extension for multi-segment videos
    - Seamless multi-segment video generation
    
    Reference: veo_doc.md
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Veo service.
        
        Args:
            api_key: Google API key. If None, loads from settings.
        """
        settings = get_settings()
        self._api_key = api_key or settings.google_api_key
        
        if not self._api_key:
            raise ValueError("Google API key is required for Veo video generation")
        
        self.client = genai.Client(api_key=self._api_key)
        self._initialized = True
        logger.info("VeoService initialized with API key")
    
    async def generate_video(
        self,
        prompt: str,
        config: VideoGenerationConfig,
        reference_images: Optional[list[bytes]] = None,
    ) -> tuple[object, int]:
        """Generate initial video segment with optional reference images.
        
        Args:
            prompt: Text prompt for video generation
            config: Video generation configuration
            reference_images: Optional list of reference image bytes (max 3)
            
        Returns:
            Tuple of (video_object, generation_time_ms)
            
        Reference: veo_doc.md - Text to video generation, Using reference images
        """
        start_time = time.time()
        model = config.model.value
        
        logger.info(f"Generating video with model: {model}")
        logger.info(f"Prompt: {prompt[:500]}..." if len(prompt) > 500 else f"Prompt: {prompt}")
        logger.info(f"Config: aspect_ratio={config.aspect_ratio.value}")
        
        # Build config - only use parameters supported by current SDK
        # Note: resolution and referenceImages may not be supported in all SDK versions
        try:
            generation_config = types.GenerateVideosConfig(
                aspect_ratio=config.aspect_ratio.value,
                number_of_videos=1,
            )
            if config.negative_prompt:
                generation_config.negative_prompt = config.negative_prompt
        except Exception as e:
            logger.warning(f"GenerateVideosConfig creation failed, using minimal config: {e}")
            generation_config = None
        
        # Prepare the first reference image as the starting frame if provided
        # Use types.Image with imageBytes (raw bytes, not base64)
        first_frame_image = None
        if reference_images and len(reference_images) > 0:
            try:
                # types.Image expects raw bytes, not base64
                first_frame_image = types.Image(
                    imageBytes=reference_images[0],
                    mimeType="image/png"
                )
                logger.info("Using first generated image as starting frame (types.Image)")
            except Exception as e:
                logger.warning(f"Failed to prepare reference image: {e}, proceeding without image")
                first_frame_image = None
        
        try:
            # Call generate_videos with or without image
            if first_frame_image:
                operation = await asyncio.to_thread(
                    self.client.models.generate_videos,
                    model=model,
                    prompt=prompt,
                    image=first_frame_image,
                    config=generation_config,
                )
            else:
                operation = await asyncio.to_thread(
                    self.client.models.generate_videos,
                    model=model,
                    prompt=prompt,
                    config=generation_config,
                )
            
            video = await self._poll_operation(
                operation,
                config.poll_interval_seconds,
                config.timeout_seconds
            )
            
            generation_time_ms = int((time.time() - start_time) * 1000)
            logger.info(f"Video generation completed in {generation_time_ms}ms")
            
            return video, generation_time_ms
            
        except VideoGenerationTimeoutError:
            raise
        except Exception as e:
            logger.error(f"Video generation failed: {e}")
            raise VideoGenerationFailedError(f"Video generation failed: {str(e)}")
    
    async def generate_video_from_image(
        self,
        prompt: str,
        first_frame: bytes,
        config: VideoGenerationConfig,
    ) -> tuple[object, int]:
        """Generate video starting from a specific image (first frame).
        
        Args:
            prompt: Text prompt for video generation
            first_frame: Image bytes for the first frame
            config: Video generation configuration
            
        Returns:
            Tuple of (video_object, generation_time_ms)
            
        Reference: veo_doc.md - Image to video generation
        """
        start_time = time.time()
        model = config.model.value
        
        logger.info(f"Generating video from image with model: {model}")
        
        # Prepare image using types.Image (imageBytes expects raw bytes)
        try:
            image_obj = types.Image(
                imageBytes=first_frame,
                mimeType="image/png"
            )
        except Exception as e:
            logger.error(f"Failed to prepare image: {e}")
            raise VideoGenerationFailedError(f"Failed to prepare image: {e}")
        
        # Build config without resolution (not supported in current SDK)
        try:
            generation_config = types.GenerateVideosConfig(
                aspect_ratio=config.aspect_ratio.value,
                number_of_videos=1,
            )
            if config.negative_prompt:
                generation_config.negative_prompt = config.negative_prompt
        except Exception as e:
            logger.warning(f"GenerateVideosConfig creation failed: {e}")
            generation_config = None
        
        try:
            operation = await asyncio.to_thread(
                self.client.models.generate_videos,
                model=model,
                prompt=prompt,
                image=image_obj,
                config=generation_config,
            )
            
            video = await self._poll_operation(
                operation,
                config.poll_interval_seconds,
                config.timeout_seconds
            )
            
            generation_time_ms = int((time.time() - start_time) * 1000)
            logger.info(f"Image-to-video generation completed in {generation_time_ms}ms")
            
            return video, generation_time_ms
            
        except VideoGenerationTimeoutError:
            raise
        except Exception as e:
            logger.error(f"Image-to-video generation failed: {e}")
            raise VideoGenerationFailedError(f"Image-to-video generation failed: {str(e)}")
    
    async def extend_video(
        self,
        video_object: object,
        prompt: str,
        config: VideoGenerationConfig,
    ) -> tuple[object, int]:
        """Extend an existing Veo-generated video.
        
        The output is a SINGLE combined video (input + extension).
        Extension conditions on the last second (~24 frames) for seamless transition.
        
        Args:
            video_object: Previous Veo-generated video object
            prompt: Continuation prompt for the extension
            config: Video generation configuration
            
        Returns:
            Tuple of (combined_video_object, generation_time_ms)
            
        Reference: veo_doc.md - Extending Veo videos
        
        IMPORTANT: 
        - Resolution must be 720p for extension
        - Output is a SINGLE combined video (seamless)
        - Audio continuity is preserved
        """
        start_time = time.time()
        model = config.model.value
        
        logger.info(f"Extending video with model: {model}")
        logger.info(f"Extension prompt: {prompt[:500]}..." if len(prompt) > 500 else f"Extension prompt: {prompt}")
        
        # Build config for extension - must match initial video's aspect ratio
        # Per documentation: resolution must be 720p for extension
        try:
            generation_config = types.GenerateVideosConfig(
                aspect_ratio=config.aspect_ratio.value,
            )
            logger.info(f"Extension config: aspect_ratio={config.aspect_ratio.value}")
        except Exception as e:
            logger.warning(f"GenerateVideosConfig creation failed: {e}")
            generation_config = None
        
        try:
            # Ensure we have the correct video object for extension
            # The video parameter expects a types.Video object (from generated_video.video)
            logger.info(f"Video object type for extension: {type(video_object).__name__}")
            
            # If we have a GeneratedVideo, extract the .video property
            actual_video = video_object
            if hasattr(video_object, 'video'):
                actual_video = video_object.video
                logger.info(f"Extracted video property, type: {type(actual_video).__name__}")
            
            # Log video object details for debugging
            if hasattr(actual_video, 'uri'):
                logger.info(f"Video URI for extension: {actual_video.uri[:100] if actual_video.uri else 'None'}...")
            if hasattr(actual_video, 'videoBytes'):
                logger.info(f"Video has bytes: {actual_video.videoBytes is not None}")
            
            # Call generate_videos with the video parameter for extension
            # Per Google example: video=initial_video.video
            operation = await asyncio.to_thread(
                self.client.models.generate_videos,
                model=model,
                prompt=prompt,
                video=actual_video,
                config=generation_config,
            )
            
            combined_video = await self._poll_operation(
                operation,
                config.poll_interval_seconds,
                config.timeout_seconds
            )
            
            generation_time_ms = int((time.time() - start_time) * 1000)
            logger.info(f"Video extension completed in {generation_time_ms}ms (seamless combined output)")
            
            return combined_video, generation_time_ms
            
        except VideoGenerationTimeoutError:
            raise
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Video extension failed: {error_msg}")
            
            # Check if this is the known SDK limitation
            if "video parameter is not supported" in error_msg.lower():
                logger.warning(
                    "VIDEO EXTENSION NOT SUPPORTED: The current google-genai SDK version "
                    "does not support video extension. Videos will be limited to 8 seconds. "
                    "Update SDK when video extension support is added."
                )
            
            raise VideoGenerationFailedError(f"Video extension failed: {error_msg}")
    
    async def generate_multi_segment_video(
        self,
        initial_prompt: str,
        extension_prompts: list[str],
        config: VideoGenerationConfig,
        reference_images: Optional[list[bytes]] = None,
    ) -> tuple[object, list[VideoSegment], int]:
        """Generate a seamless multi-segment video.
        
        Generates initial 8s segment with reference images, then extends
        iteratively. Each extension returns a SINGLE combined video.
        
        Args:
            initial_prompt: Prompt for the first 8s segment
            extension_prompts: List of prompts for each extension
            config: Video generation configuration
            reference_images: Optional reference images (initial segment only)
            
        Returns:
            Tuple of (final_video_object, segments, total_generation_time_ms)
            
        Reference: PHASE3_2_VIDEO_GENERATOR_PLAN.md Section 2.4
        """
        total_start_time = time.time()
        segments = []
        current_video = None
        current_duration = 0.0
        
        logger.info(f"Starting multi-segment video generation: 1 initial + {len(extension_prompts)} extensions")
        
        current_video, gen_time = await self.generate_video(
            prompt=initial_prompt,
            config=config,
            reference_images=reference_images,
        )
        
        initial_segment = VideoSegment(
            segment_number=0,
            segment_type=VideoSegmentType.INITIAL,
            duration_seconds=8.0,
            start_time=0.0,
            end_time=8.0,
            prompt=initial_prompt[:500],
            generation_time_ms=gen_time,
            used_reference_images=bool(reference_images),
        )
        segments.append(initial_segment)
        current_duration = 8.0
        
        logger.info(f"Initial segment generated: {current_duration}s total")
        
        for i, ext_prompt in enumerate(extension_prompts):
            logger.info(f"Generating extension {i + 1}/{len(extension_prompts)}")
            
            try:
                # Try to extend - video parameter may not be supported in all SDK versions
                video_to_extend = current_video.video if hasattr(current_video, 'video') else current_video
                current_video, gen_time = await self.extend_video(
                    video_object=video_to_extend,
                    prompt=ext_prompt,
                    config=config,
                )
            except Exception as ext_error:
                # Video extension not supported - use initial segment only
                logger.warning(f"Video extension not supported in current SDK: {ext_error}")
                logger.info("Continuing with initial segment only (8s video)")
                break  # Exit extension loop, use what we have
            
            extension_duration = 7.0
            extension_segment = VideoSegment(
                segment_number=i + 1,
                segment_type=VideoSegmentType.EXTENSION,
                duration_seconds=extension_duration,
                start_time=current_duration,
                end_time=current_duration + extension_duration,
                prompt=ext_prompt[:500],
                generation_time_ms=gen_time,
                used_reference_images=False,
            )
            segments.append(extension_segment)
            current_duration += extension_duration
            
            logger.info(f"Extension {i + 1} complete: {current_duration}s total (seamless)")
        
        total_generation_time_ms = int((time.time() - total_start_time) * 1000)
        
        logger.info(
            f"Multi-segment video complete: {len(segments)} segments, "
            f"{current_duration}s total, {total_generation_time_ms}ms generation time"
        )
        
        return current_video, segments, total_generation_time_ms
    
    async def download_video(self, video_object: object) -> bytes:
        """Download generated video as bytes.
        
        Args:
            video_object: Veo-generated video object
            
        Returns:
            Video bytes
            
        Reference: veo_doc.md - Download generated video
        """
        try:
            video_file = video_object.video if hasattr(video_object, 'video') else video_object
            
            await asyncio.to_thread(
                self.client.files.download,
                file=video_file
            )
            
            if hasattr(video_file, 'read'):
                video_bytes = video_file.read()
            elif hasattr(video_file, '_downloaded_bytes'):
                video_bytes = video_file._downloaded_bytes
            else:
                import tempfile
                import os
                
                temp_path = tempfile.mktemp(suffix=".mp4")
                video_file.save(temp_path)
                
                with open(temp_path, 'rb') as f:
                    video_bytes = f.read()
                
                os.remove(temp_path)
            
            logger.info(f"Video downloaded: {len(video_bytes)} bytes")
            return video_bytes
            
        except Exception as e:
            logger.error(f"Video download failed: {e}")
            raise VeoServiceError(f"Failed to download video: {str(e)}")
    
    async def _upload_image(self, image_bytes: bytes, name: str) -> object:
        """Upload image bytes to Gemini Files API.
        
        Args:
            image_bytes: Image data
            name: Name for the uploaded file
            
        Returns:
            Uploaded file object
        """
        import tempfile
        import os
        
        temp_path = tempfile.mktemp(suffix=".png")
        try:
            with open(temp_path, 'wb') as f:
                f.write(image_bytes)
            
            uploaded_file = await asyncio.to_thread(
                self.client.files.upload,
                file=temp_path,
                config=types.UploadFileConfig(
                    display_name=name,
                    mime_type="image/png"
                )
            )
            
            return uploaded_file
            
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    async def _poll_operation(
        self,
        operation: object,
        poll_interval: int = DEFAULT_POLL_INTERVAL,
        timeout: int = 360,
        return_full_response: bool = False,
    ) -> object:
        """Poll operation status until complete.
        
        Args:
            operation: The operation object from generate_videos
            poll_interval: Seconds between polls
            timeout: Total timeout in seconds
            return_full_response: If True, return the full GeneratedVideo object
            
        Returns:
            Generated video object (GeneratedVideo with .video property)
            
        Raises:
            VideoGenerationTimeoutError: If generation times out
            VideoGenerationFailedError: If generation fails
            
        Reference: veo_doc.md - Handling asynchronous operations
        """
        max_attempts = timeout // poll_interval
        attempt = 0
        
        while not operation.done and attempt < max_attempts:
            logger.info(f"Polling video generation status... (attempt {attempt + 1}/{max_attempts})")
            await asyncio.sleep(poll_interval)
            
            operation = await asyncio.to_thread(
                self.client.operations.get,
                operation
            )
            attempt += 1
        
        if not operation.done:
            raise VideoGenerationTimeoutError(
                f"Video generation timed out after {timeout} seconds"
            )
        
        if hasattr(operation, 'error') and operation.error:
            raise VideoGenerationFailedError(
                f"Video generation failed: {operation.error}"
            )
        
        # Try 'result' first (as per latest SDK examples), then fall back to 'response'
        result = None
        if hasattr(operation, 'result') and operation.result:
            result = operation.result
            logger.info("Using operation.result for video extraction")
        elif hasattr(operation, 'response') and operation.response:
            result = operation.response
            logger.info("Using operation.response for video extraction")
        
        if not result:
            raise VideoGenerationFailedError("No result/response in completed operation")
        
        if not hasattr(result, 'generated_videos') or not result.generated_videos:
            raise VideoGenerationFailedError("No videos in operation result")
        
        # Return the GeneratedVideo object (which has .video property for extension)
        generated_video = result.generated_videos[0]
        logger.info(f"Generated video object type: {type(generated_video).__name__}")
        if hasattr(generated_video, 'video'):
            video_obj = generated_video.video
            logger.info(f"Video property type: {type(video_obj).__name__}")
            if hasattr(video_obj, 'uri'):
                logger.info(f"Video URI: {video_obj.uri[:100] if video_obj.uri else 'None'}...")
        
        return generated_video
    
    async def generate_video_with_retry(
        self,
        prompt: str,
        config: VideoGenerationConfig,
        reference_images: Optional[list[bytes]] = None,
    ) -> tuple[object, int, int]:
        """Generate video with retry and fallback logic.
        
        Args:
            prompt: Text prompt for video generation
            config: Video generation configuration
            reference_images: Optional reference images
            
        Returns:
            Tuple of (video_object, generation_time_ms, retry_count)
        """
        last_error = None
        original_model = config.model
        
        for attempt in range(config.max_retries):
            try:
                video, gen_time = await self.generate_video(
                    prompt=prompt,
                    config=config,
                    reference_images=reference_images,
                )
                return video, gen_time, attempt
                
            except VideoGenerationTimeoutError as e:
                last_error = e
                logger.warning(f"Attempt {attempt + 1} timed out: {e}")
                
            except VideoGenerationFailedError as e:
                last_error = e
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
            
            if attempt < config.max_retries - 1:
                wait_time = 2 ** attempt * 5
                logger.info(f"Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
                
                if attempt == config.max_retries - 2:
                    if config.model == VideoModel.VEO_3_1:
                        logger.info("Falling back to Veo 3.1 Fast")
                        config.model = VideoModel.VEO_3_1_FAST
                    
                    if config.resolution == VideoResolution.RES_1080P:
                        logger.info("Falling back to 720p resolution")
                        config.resolution = VideoResolution.RES_720P
        
        config.model = original_model
        raise last_error


_veo_service: Optional[VeoService] = None


def get_veo_service() -> VeoService:
    """Get or create the VeoService singleton.
    
    Returns:
        VeoService instance
    """
    global _veo_service
    if _veo_service is None:
        _veo_service = VeoService()
    return _veo_service
