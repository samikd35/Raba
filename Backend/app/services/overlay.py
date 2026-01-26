"""Overlay Generation and Compositor Services.

Generates subtitle overlays from script dialogue and composes onto clean video.
Images generation is optional; if unavailable, metadata-only overlays are returned
and compositor passes through the clean video.
"""

from __future__ import annotations

from typing import Iterable, Optional

import aiohttp
from app.models.overlay import OverlayItem
from app.models.text_overlay import TextOverlay
from app.services.text_overlay import get_text_overlay_service
from app.services.supabase import get_supabase_client
from app.utils.logging import get_logger

logger = get_logger(__name__)


class OverlayGeneratorService:
    """Creates subtitle overlay metadata from scenes/dialogue."""

    def generate_overlays(self, script_output: dict) -> list[OverlayItem]:
        items: list[OverlayItem] = []
        if not script_output:
            return items
        # Walk hook + scenes and collect dialogue into timed overlays
        hook = script_output.get("hook") or {}
        if hook and hook.get("script"):
            dur = float(hook.get("duration_seconds", 2.0))
            items.append(OverlayItem(text=hook.get("script"), start_time=0.0, end_time=dur))

        scenes = script_output.get("scenes") or []
        for s in scenes:
            text = s.get("dialogue")
            if not text:
                continue
            start = float(s.get("timestamp_start") or s.get("start_time") or 0.0)
            end = float(s.get("timestamp_end") or s.get("end_time") or (start + 3.0))
            if end <= start:
                end = start + 1.0
            items.append(OverlayItem(text=text, start_time=start, end_time=end))
        logger.info(f"Generated {len(items)} subtitle overlay items")
        return items


class VideoCompositorService:
    """Composites overlay images/metadata onto clean videos.

    In environments without image overlays, returns the clean video URL unchanged.
    """

    async def composite(
        self,
        clean_video_url: str,
        overlays: Iterable[OverlayItem],
        *,
        workflow_id: Optional[str] = None,
    ) -> str:
        """Composite overlays onto the clean video and return a new storage URL.

        If ffmpeg is unavailable or any step fails, returns the original URL.
        """
        items = list(overlays or [])
        if not items:
            logger.info("No overlays provided; returning clean video URL")
            return clean_video_url

        # Download the clean video
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(clean_video_url) as resp:
                    if resp.status != 200:
                        logger.warning(
                            f"Failed to download clean video for compositing: {resp.status}"
                        )
                        return clean_video_url
                    video_bytes = await resp.read()
        except Exception as e:
            logger.warning(f"Compositor download failed: {e}")
            return clean_video_url

        # Convert to TextOverlay with defaults
        text_overlays: list[TextOverlay] = [
            TextOverlay(
                text=i.text,
                start_time=i.start_time,
                end_time=i.end_time,
                position=(40, 40) if i.position.value == "top" else (40, 1000 if i.position.value == "bottom" else 600),
                font_size=48,
                font_color="white",
                background_color="black@0.5",
                animation="fade_in",
            )
            for i in items
        ]

        # Apply overlays with FFmpeg (graceful fallback inside service)
        try:
            svc = get_text_overlay_service()
            out_bytes = await svc.add_text_overlays(video_bytes, text_overlays)
        except Exception as e:
            logger.warning(f"Text overlay application failed: {e}")
            return clean_video_url

        # Upload new video to storage
        try:
            supabase = get_supabase_client()
            bucket = "media"
            folder = (
                f"videos/{workflow_id}" if workflow_id else "generated_videos"
            )
            storage_path = f"{folder}/final_composited_{__import__('time').time():.0f}.mp4"
            supabase.storage.from_(bucket).upload(
                path=storage_path, file=out_bytes, file_options={"content-type": "video/mp4"}
            )
            public_url = supabase.storage.from_(bucket).get_public_url(storage_path)
            logger.info("Uploaded composited video to storage")
            return public_url
        except Exception as e:
            logger.warning(f"Upload of composited video failed; returning clean URL: {e}")
            return clean_video_url


_overlay_generator: Optional[OverlayGeneratorService] = None
_video_compositor: Optional[VideoCompositorService] = None


def get_overlay_generator() -> OverlayGeneratorService:
    global _overlay_generator
    if _overlay_generator is None:
        _overlay_generator = OverlayGeneratorService()
    return _overlay_generator


def get_video_compositor() -> VideoCompositorService:
    global _video_compositor
    if _video_compositor is None:
        _video_compositor = VideoCompositorService()
    return _video_compositor
