"""Overlay Generator Agent.

Generates programmatic subtitle overlays when enabled by user.
"""

from typing import Any

from app.graph.state import VideoGenerationState
from app.services.overlay import get_overlay_generator
from app.utils.logging import get_logger

logger = get_logger(__name__)


class OverlayGeneratorAgent:
    def __init__(self):
        self.generator = get_overlay_generator()
        logger.info("OverlayGeneratorAgent initialized")

    async def run(self, state: VideoGenerationState) -> dict[str, Any]:
        if not state.get("enable_subtitles", False):
            logger.info("Subtitles disabled; skipping overlay generation")
            return {}
        script = state.get("script_output", {})
        items = self.generator.generate_overlays(script)
        from app.utils.helpers import utc_now_iso
        return {
            "subtitle_overlays": [i.model_dump() for i in items],
            "phase_timestamps": {
                **state.get("phase_timestamps", {}),
                "overlay_generator_completed": utc_now_iso(),
            },
        }


async def overlay_generator_node(state: VideoGenerationState) -> dict[str, Any]:
    agent = OverlayGeneratorAgent()
    return await agent.run(state)

