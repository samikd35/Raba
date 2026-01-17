"""Trim Agent.

Trims clean video edges to remove jitter and prepares for overlay.
"""

from typing import Any

from app.graph.state import VideoGenerationState
from app.services.veo import get_veo_service
from app.services.video_trimmer import get_video_trimmer
from app.utils.logging import get_logger

logger = get_logger(__name__)


class TrimAgent:
    def __init__(self):
        self.trimmer = get_video_trimmer()
        self.veo = get_veo_service()
        logger.info("TrimAgent initialized")

    async def run(self, state: VideoGenerationState) -> dict[str, Any]:
        video_output = state.get("video_output", {}) or {}
        url = state.get("final_video_url") or video_output.get("video", {}).get("url")
        duration = float(video_output.get("total_duration_seconds") or state.get("duration_seconds", 18))
        if not url:
            logger.warning("No video URL available for trimming")
            return {}

        try:
            # Download, trim, upload
            data = await self.veo.download_video(video_output.get("video", {}))
            trimmed = await self.trimmer.trim_edges(data, duration)
            # Re-upload trimmed file
            from app.services.supabase import get_supabase_client
            supabase = get_supabase_client()
            import time
            path = f"videos/{state.get('workflow_id','unknown')}/clean_{int(time.time())}.mp4"
            bucket = "media"
            full_path = f"generated_videos/{path}"
            supabase.storage.from_(bucket).upload(path=full_path, file=trimmed, file_options={"content-type": "video/mp4"})
            clean_url = supabase.storage.from_(bucket).get_public_url(full_path)
        except Exception as e:
            logger.warning(f"Trim operation failed, using original: {e}")
            clean_url = url

        from app.utils.helpers import utc_now_iso
        return {
            "clean_video_url": clean_url,
            "phase_timestamps": {
                **state.get("phase_timestamps", {}),
                "trim_agent_completed": utc_now_iso(),
            },
        }


async def trim_agent_node(state: VideoGenerationState) -> dict[str, Any]:
    agent = TrimAgent()
    return await agent.run(state)

