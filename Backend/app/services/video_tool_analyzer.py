"""Video Tool Analyzer Service.

Analyzes uploaded reference videos using Gemini video understanding
and returns structured style insights for tool creation.
"""

from __future__ import annotations

import os
from typing import Optional

from fastapi import UploadFile

from app.models.tool import ToolVideoAnalysis
from app.services.gemini import GEMINI_2_5_FLASH, GeminiServiceError, get_gemini_service
from app.services.supabase import get_supabase_service
from app.utils.logging import get_logger

logger = get_logger(__name__)

ALLOWED_VIDEO_TYPES = {
    "video/mp4",
    "video/quicktime",
    "video/webm",
}

MAX_VIDEO_MB = 50
INLINE_VIDEO_MAX_MB = 20


class VideoToolAnalyzerError(Exception):
    """Base exception for video tool analysis errors."""


class VideoToolAnalyzerService:
    """Service for analyzing reference videos to create tools."""

    def __init__(self):
        self._gemini = get_gemini_service()
        self._supabase = get_supabase_service()

    async def analyze_video(
        self,
        file: UploadFile,
        draft_id: str,
        notes: Optional[str] = None,
    ) -> tuple[ToolVideoAnalysis, str]:
        """Analyze a video and upload it to storage.

        Returns:
            Tuple of (analysis, source_video_url)
        """
        if file is None or not file.filename:
            raise VideoToolAnalyzerError("No reference video provided")

        content_type = file.content_type or self._guess_mime_type(file.filename)
        if content_type not in ALLOWED_VIDEO_TYPES:
            raise VideoToolAnalyzerError(
                f"Invalid video type. Allowed: {', '.join(sorted(ALLOWED_VIDEO_TYPES))}"
            )

        logger.info(f"Analyzing reference video: {file.filename} (draft {draft_id})")
        video_bytes = await file.read()
        if not video_bytes:
            raise VideoToolAnalyzerError("Empty video file")
        size_mb = len(video_bytes) / (1024 * 1024)
        if size_mb > MAX_VIDEO_MB:
            raise VideoToolAnalyzerError(f"File too large. Maximum size: {MAX_VIDEO_MB}MB")

        ext = self._file_extension(file.filename, content_type)
        storage_path = f"reference_videos/{draft_id}/source.{ext}"
        source_url = await self._supabase.upload_file(
            bucket="media",
            path=storage_path,
            file_data=video_bytes,
            content_type=content_type,
        )
        if not source_url:
            raise VideoToolAnalyzerError("Failed to upload reference video")

        use_file_api = size_mb > INLINE_VIDEO_MAX_MB
        prompt = self._build_analysis_prompt(notes)

        try:
            analysis = await self._gemini.generate_structured_output_with_video(
                prompt=prompt,
                response_model=ToolVideoAnalysis,
                video_bytes=video_bytes,
                mime_type=content_type,
                model=GEMINI_2_5_FLASH,
                use_file_api=use_file_api,
                file_display_name=f"tool_reference_{draft_id}",
            )
        except GeminiServiceError as e:
            raise VideoToolAnalyzerError(f"Video analysis failed: {e}") from e

        return analysis, source_url

    def _build_analysis_prompt(self, notes: Optional[str]) -> str:
        base = (
            "Analyze the uploaded short video for the purpose of recreating its style in AI generation. "
            "Return a JSON object that matches the schema exactly. "
            "Focus on actionable creative attributes: script style, visual aesthetics, camera language, "
            "editing pace, audio profile, and text overlay usage. "
            "Also produce a concise tool_idea string suitable for tool enhancement. "
            "Avoid speculation about the creator or brand identity."
        )
        if notes:
            return f"{base}\n\nUser constraints:\n{notes}"
        return base

    def _guess_mime_type(self, filename: str) -> str:
        ext = os.path.splitext(filename or "")[1].lower()
        if ext in {".mp4", ".m4v"}:
            return "video/mp4"
        if ext in {".mov"}:
            return "video/quicktime"
        if ext in {".webm"}:
            return "video/webm"
        return "video/mp4"

    def _file_extension(self, filename: str, content_type: str) -> str:
        ext = os.path.splitext(filename or "")[1].lower().lstrip(".")
        if ext:
            return ext
        if content_type == "video/quicktime":
            return "mov"
        if content_type == "video/webm":
            return "webm"
        return "mp4"


_video_tool_analyzer: Optional[VideoToolAnalyzerService] = None


def get_video_tool_analyzer() -> VideoToolAnalyzerService:
    """Get singleton VideoToolAnalyzerService instance."""
    global _video_tool_analyzer
    if _video_tool_analyzer is None:
        _video_tool_analyzer = VideoToolAnalyzerService()
    return _video_tool_analyzer
