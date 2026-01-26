"""FFmpeg-based Text Overlay Service.

Adds typographically correct text overlays to a video using FFmpeg drawtext.
Falls back gracefully if ffmpeg is not available in the environment.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from typing import Iterable, List

from app.models.text_overlay import TextOverlay
from app.utils.logging import get_logger

logger = get_logger(__name__)


class TextOverlayService:
    """Add typographically correct text overlays using FFmpeg."""

    def __init__(self, default_font_paths: List[str] | None = None):
        # Common font locations across platforms; pick the first that exists
        self.default_font_paths = default_font_paths or [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/Library/Fonts/Arial Unicode.ttf",
            "/Library/Fonts/Arial Bold.ttf",
        ]

    async def add_text_overlays(self, video_bytes: bytes, overlays: Iterable[TextOverlay]) -> bytes:
        """
        Add text overlays to video using FFmpeg drawtext filter.

        Args:
            video_bytes: Input video bytes
            overlays: Iterable of TextOverlay specs

        Returns:
            Video bytes with text overlays (or original on failure)
        """
        try:
            if not video_bytes:
                return video_bytes

            if not shutil.which("ffmpeg"):
                logger.warning("ffmpeg not found; returning original video without overlays")
                return video_bytes

            overlay_list = list(overlays or [])
            if not overlay_list:
                return video_bytes

            # Resolve a usable font
            fontfile = None
            for p in self.default_font_paths:
                if os.path.exists(p):
                    fontfile = p
                    break

            # Build the filter chain
            filter_chain = self._build_drawtext_filter(overlay_list, fontfile)

            with tempfile.TemporaryDirectory() as td:
                in_path = os.path.join(td, "input.mp4")
                out_path = os.path.join(td, "output.mp4")
                with open(in_path, "wb") as f:
                    f.write(video_bytes)

                cmd = [
                    "ffmpeg",
                    "-y",
                    "-i",
                    in_path,
                    "-vf",
                    filter_chain,
                    "-c:a",
                    "copy",
                    out_path,
                ]
                proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if proc.returncode != 0:
                    logger.warning(
                        f"ffmpeg text overlay failed: {proc.stderr.decode(errors='ignore')[:200]}"
                    )
                    return video_bytes

                with open(out_path, "rb") as f:
                    return f.read()
        except Exception as e:
            logger.warning(f"Text overlay service error; returning original video: {e}")
            return video_bytes

    def _build_drawtext_filter(self, overlays: List[TextOverlay], fontfile: str | None) -> str:
        # Generate multiple drawtext entries chained via ","
        parts: list[str] = []
        for ov in overlays:
            # Times
            st = max(0.0, float(ov.start_time))
            et = max(st, float(ov.end_time))
            enable = f"between(t,{st:.3f},{et:.3f})"

            # Positions
            x, y = ov.position

            # Background box
            box = "1" if ov.background_color else "0"
            boxclr = ov.background_color or "black@0.0"

            # Fontfile param if available
            font_param = f":fontfile={fontfile}" if (fontfile and not ov.fontfile) else (f":fontfile={ov.fontfile}" if ov.fontfile else "")

            # Basic animation support: fade_in (approximate via alpha)
            alpha = "1.0"
            if ov.animation == "fade_in":
                # Quick fade-in over 0.3s at start
                alpha = f"if(lt(t,{st+0.3}), (t-{st})/0.3, 1.0)"

            draw = (
                f"drawtext=text='{self._escape_text(ov.text)}'"
                f":x={x}:y={y}:fontsize={ov.font_size}:fontcolor={ov.font_color}{font_param}"
                f":box={box}:boxcolor={boxclr}:alpha={alpha}:enable='{enable}'"
            )
            parts.append(draw)
        return ",".join(parts)

    def _escape_text(self, text: str) -> str:
        # Escape characters that break drawtext
        return (
            text.replace("\\", "\\\\")
            .replace(":", "\\:")
            .replace("'", "\\'")
            .replace("[", "\\[")
            .replace("]", "\\]")
        )


_text_overlay_service: TextOverlayService | None = None


def get_text_overlay_service() -> TextOverlayService:
    global _text_overlay_service
    if _text_overlay_service is None:
        _text_overlay_service = TextOverlayService()
    return _text_overlay_service

