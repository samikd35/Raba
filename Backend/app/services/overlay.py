"""Overlay Generation and Compositor Services.

Generates subtitle overlays from script dialogue and composes onto clean video.
Images generation is optional; if unavailable, metadata-only overlays are returned
and compositor passes through the clean video.
"""

from __future__ import annotations

from typing import Iterable, Optional

from app.models.overlay import OverlayItem
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

    async def composite(self, clean_video_url: str, overlays: Iterable[OverlayItem]) -> str:
        # Placeholder: pass-through URL; a real implementation would download clean
        # video, render overlay images, and use ffmpeg filter_complex drawtext or overlay.
        count = len(list(overlays))
        if count == 0:
            logger.info("No overlays provided; returning clean video URL")
            return clean_video_url
        logger.info(f"Compositor received {count} overlays; returning clean video (no-op)")
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

