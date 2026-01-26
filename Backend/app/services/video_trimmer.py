"""Video Trimmer Service.

FFmpeg-based trimming to remove jitter at clip boundaries.
If FFmpeg is unavailable, performs a no-op and logs a warning.
"""

import asyncio
from typing import Optional

from app.utils.logging import get_logger

logger = get_logger(__name__)


class VideoTrimmerService:
    """Service to trim edges from a video file or bytes."""

    def __init__(self, trim_edge_seconds: float = 0.5):
        self.trim_edge_seconds = max(0.0, float(trim_edge_seconds))

    async def trim_edges(self, input_bytes: bytes, duration_seconds: float) -> bytes:
        """Trim first/last edge seconds from a single video buffer.

        This is a best-effort implementation. In environments without ffmpeg,
        returns the original bytes.
        """
        start = self.trim_edge_seconds
        end = max(0.0, duration_seconds - self.trim_edge_seconds)
        if end - start <= 0:
            logger.warning("Trim range is invalid, returning original video")
            return input_bytes

        # Attempt to call ffmpeg via subprocess if available
        try:
            import shutil
            has_ffmpeg = shutil.which("ffmpeg") is not None
            if not has_ffmpeg:
                logger.warning("ffmpeg not found; skipping trimming")
                return input_bytes

            # Write input to temp file and read output
            import tempfile, os
            with tempfile.TemporaryDirectory() as td:
                in_path = os.path.join(td, "in.mp4")
                out_path = os.path.join(td, "out.mp4")
                with open(in_path, "wb") as f:
                    f.write(input_bytes)
                # Use -ss for start and -to for end
                cmd = [
                    "ffmpeg", "-y", "-i", in_path,
                    "-ss", str(start), "-to", str(end),
                    "-c", "copy", out_path,
                ]
                proc = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                _out, err = await proc.communicate()
                if proc.returncode != 0:
                    logger.warning(f"ffmpeg trimming failed: {err.decode(errors='ignore')[:200]}")
                    return input_bytes
                with open(out_path, "rb") as f:
                    out_bytes = f.read()
                logger.info("Video trimmed with ffmpeg")
                return out_bytes or input_bytes
        except Exception as e:
            logger.warning(f"Trimming failed, returning original video: {e}")
            return input_bytes


    async def trim_to_duration(self, input_bytes: bytes, target_duration_seconds: float) -> bytes:
        """Hard-trim the video to target duration from start (0 to target).

        If ffmpeg is unavailable, returns the original bytes.
        """
        try:
            import shutil
            has_ffmpeg = shutil.which("ffmpeg") is not None
            if not has_ffmpeg:
                logger.warning("ffmpeg not found; skipping trim_to_duration")
                return input_bytes

            import tempfile, os
            with tempfile.TemporaryDirectory() as td:
                in_path = os.path.join(td, "in.mp4")
                out_path = os.path.join(td, "out.mp4")
                with open(in_path, "wb") as f:
                    f.write(input_bytes)
                cmd = [
                    "ffmpeg", "-y", "-i", in_path,
                    "-t", str(float(target_duration_seconds)),
                    "-c", "copy", out_path,
                ]
                proc = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                _out, err = await proc.communicate()
                if proc.returncode != 0:
                    logger.warning(f"ffmpeg trim_to_duration failed: {err.decode(errors='ignore')[:200]}")
                    return input_bytes
                with open(out_path, "rb") as f:
                    out_bytes = f.read()
                logger.info("Video hard-trimmed to target duration with ffmpeg")
                return out_bytes or input_bytes
        except Exception as e:
            logger.warning(f"trim_to_duration failed, returning original video: {e}")
            return input_bytes

    async def strip_audio(self, input_bytes: bytes) -> bytes:
        """Remove audio track from video, producing a silent video.
        
        Uses FFmpeg stream copy (no re-encode) for fast processing.
        If ffmpeg is unavailable, returns the original bytes with warning.
        
        Args:
            input_bytes: Input video bytes (with audio)
            
        Returns:
            Video bytes without audio track
        """
        try:
            import shutil
            has_ffmpeg = shutil.which("ffmpeg") is not None
            if not has_ffmpeg:
                logger.warning("ffmpeg not found; cannot strip audio - video will retain audio")
                return input_bytes

            import tempfile, os
            with tempfile.TemporaryDirectory() as td:
                in_path = os.path.join(td, "in.mp4")
                out_path = os.path.join(td, "out_silent.mp4")
                with open(in_path, "wb") as f:
                    f.write(input_bytes)
                
                # -an removes all audio streams
                # -c:v copy preserves video quality (no re-encode)
                cmd = [
                    "ffmpeg", "-y", "-i", in_path,
                    "-an",  # Remove audio
                    "-c:v", "copy",  # Copy video stream without re-encoding
                    out_path,
                ]
                proc = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                _out, err = await proc.communicate()
                if proc.returncode != 0:
                    logger.warning(f"ffmpeg audio strip failed: {err.decode(errors='ignore')[:200]}")
                    return input_bytes
                
                with open(out_path, "rb") as f:
                    out_bytes = f.read()
                
                logger.info(f"Audio stripped successfully: {len(input_bytes)} -> {len(out_bytes)} bytes")
                return out_bytes or input_bytes
                
        except Exception as e:
            logger.warning(f"Audio stripping failed, returning original video: {e}")
            return input_bytes


_video_trimmer: Optional[VideoTrimmerService] = None


def get_video_trimmer() -> VideoTrimmerService:
    global _video_trimmer
    if _video_trimmer is None:
        _video_trimmer = VideoTrimmerService()
    return _video_trimmer


async def strip_audio_from_video(video_bytes: bytes) -> bytes:
    """Convenience function to strip audio from video bytes.
    
    Args:
        video_bytes: Input video bytes
        
    Returns:
        Video bytes with audio removed
    """
    trimmer = get_video_trimmer()
    return await trimmer.strip_audio(video_bytes)
