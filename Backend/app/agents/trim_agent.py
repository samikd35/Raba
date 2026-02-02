"""Trim Agent.

Trims clean video edges to remove jitter, replaces Veo audio with generated
voice audio, and prepares video for overlay.
"""

from typing import Any

from app.graph.state import VideoGenerationState
from app.services.veo import get_veo_service
from app.services.video_trimmer import get_video_trimmer, replace_audio_in_video
from app.utils.logging import get_logger

logger = get_logger(__name__)


class TrimAgent:
    def __init__(self):
        self.trimmer = get_video_trimmer()
        self.veo = get_veo_service()
        logger.info("TrimAgent initialized")

    async def _download_audio_segments(
        self,
        audio_manifest: dict,
    ) -> list[tuple[bytes, float]]:
        """Download audio segments from storage URLs.

        Args:
            audio_manifest: Audio manifest with segments containing audio_file_path

        Returns:
            List of (audio_bytes, start_time) tuples
        """
        import aiohttp
        from aiohttp import ClientTimeout

        segments = audio_manifest.get("segments", [])
        if not segments:
            return []

        audio_data = []
        async with aiohttp.ClientSession(timeout=ClientTimeout(total=60)) as session:
            for seg in sorted(segments, key=lambda item: float(item.get("start_time", 0.0) or 0.0)):
                audio_url = seg.get("audio_file_path")
                start_time = float(seg.get("start_time", 0.0) if "start_time" in seg else 0.0)

                if not audio_url or audio_url.startswith("upload_failed://"):
                    logger.warning(f"Skipping invalid audio segment: {audio_url}")
                    continue

                try:
                    async with session.get(audio_url) as resp:
                        if resp.status == 200:
                            audio_bytes = await resp.read()
                            if audio_bytes:
                                audio_data.append((audio_bytes, start_time))
                            logger.info(f"Downloaded audio segment: {len(audio_bytes)} bytes")
                        else:
                            logger.warning(f"Failed to download audio segment: HTTP {resp.status}")
                except Exception as e:
                    logger.warning(f"Error downloading audio segment: {e}")

        return audio_data

    async def run(self, state: VideoGenerationState) -> dict[str, Any]:
        video_output = state.get("video_output", {}) or {}
        url = state.get("final_video_url") or video_output.get("video", {}).get("url")
        requested_duration = float(state.get("duration_seconds", 18))
        target_duration = float(video_output.get("total_duration_seconds") or requested_duration)
        audio_manifest = state.get("audio_manifest") or state.get("audio_output")
        enable_audio = state.get("enable_audio", False)

        if not url:
            logger.warning("No video URL available for trimming")
            return {}

        try:
            # Download video
            import aiohttp
            from aiohttp import ClientTimeout

            async with aiohttp.ClientSession(timeout=ClientTimeout(total=120)) as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        raise RuntimeError(f"HTTP {resp.status} downloading video")
                    data = await resp.read()

            logger.info(f"Downloaded video: {len(data)} bytes")

            # First, hard trim to target duration to remove overrun
            if enable_audio:
                drift = abs(target_duration - requested_duration)
                if drift > 0.35:
                    logger.warning(
                        "Trim target drift exceeds tolerance: requested=%.2fs, target=%.2fs",
                        requested_duration,
                        target_duration,
                    )
                    target_duration = requested_duration
            data = await self.trimmer.trim_to_duration(data, target_duration)

            # Then, optional edge trim to remove jitter
            trimmed = await self.trimmer.trim_edges(data, target_duration)

            # Replace Veo audio with generated voice audio if available
            if enable_audio and audio_manifest and isinstance(audio_manifest, dict):
                segments = audio_manifest.get("segments", [])
                if segments:
                    logger.info(
                        f"Replacing Veo audio with {len(segments)} generated voice segments"
                    )
                    audio_segments = await self._download_audio_segments(audio_manifest)

                    if audio_segments:
                        trimmed = await replace_audio_in_video(trimmed, audio_segments)
                        logger.info("Audio replacement completed")
                    else:
                        logger.warning("No valid audio segments downloaded; keeping original audio")
                else:
                    logger.info("No audio segments in manifest; keeping original audio")
            elif enable_audio:
                logger.info("Audio enabled but no audio_manifest found; keeping Veo audio")
            else:
                logger.info("Audio disabled; stripping Veo audio")
                trimmed = await self.trimmer.strip_audio(trimmed)

            # Re-upload processed file
            from app.services.supabase import get_supabase_client

            supabase = get_supabase_client()
            import time

            path = f"videos/{state.get('workflow_id', 'unknown')}/clean_{int(time.time())}.mp4"
            bucket = "media"
            full_path = f"generated_videos/{path}"
            supabase.storage.from_(bucket).upload(
                path=full_path, file=trimmed, file_options={"content-type": "video/mp4"}
            )
            clean_url = supabase.storage.from_(bucket).get_public_url(full_path)

            logger.info(f"Uploaded processed video: {clean_url}")

        except Exception as e:
            logger.warning(f"Trim/audio operation failed, using original: {e}")
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
