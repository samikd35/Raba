"""Video Compositor Agent.

Composes subtitle overlays onto the clean video when enabled.
"""

from typing import Any

from app.graph.state import VideoGenerationState
from app.models.overlay import OverlayItem
from app.services.overlay import get_video_compositor
from app.utils.logging import get_logger

logger = get_logger(__name__)


class VideoCompositorAgent:
    def __init__(self):
        self.compositor = get_video_compositor()
        logger.info("VideoCompositorAgent initialized")

    async def run(self, state: VideoGenerationState) -> dict[str, Any]:
        if not state.get("enable_subtitles", False):
            logger.info("Subtitles disabled; compositor pass-through")
            return {}
        clean = state.get("clean_video_url") or state.get("final_video_url")
        items = state.get("subtitle_overlays", []) or []
        overlays = [OverlayItem(**i) for i in items]
        final_url = await self.compositor.composite(
            clean, overlays, workflow_id=state.get("workflow_id")
        )
        from app.utils.helpers import utc_now_iso
        return {
            "final_video_url": final_url,
            "phase_timestamps": {
                **state.get("phase_timestamps", {}),
                "video_compositor_completed": utc_now_iso(),
            },
        }


async def video_compositor_node(state: VideoGenerationState) -> dict[str, Any]:
    agent = VideoCompositorAgent()
    return await agent.run(state)
