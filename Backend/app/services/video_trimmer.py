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


_video_trimmer: Optional[VideoTrimmerService] = None


def get_video_trimmer() -> VideoTrimmerService:
    global _video_trimmer
    if _video_trimmer is None:
        _video_trimmer = VideoTrimmerService()
    return _video_trimmer

