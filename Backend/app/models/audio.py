"""RABA Audio Models.

Pydantic models for audio generation outputs and voice profiles.
"""

from typing import Any

from pydantic import BaseModel, Field


class VoiceProfile(BaseModel):
    """Voice profile for character consistency."""

    character_name: str = Field(..., description="Character name for the voice profile")
    voice_name: str = Field(..., description="Gemini TTS voice name (prebuilt)")
    gender: str = Field(
        default="neutral",
        description="Character gender or voice descriptor",
    )
    style_preset: str = Field(
        default="",
        description="Default style instructions for the voice",
    )


class AudioSegment(BaseModel):
    """Generated audio segment metadata."""

    segment_id: int = Field(..., ge=0, description="Matches VideoSegment.segment_number")
    start_time: float = Field(
        default=0.0,
        ge=0,
        description="Start time in seconds within the full audio timeline",
    )
    end_time: float = Field(
        default=0.0,
        ge=0,
        description="End time in seconds within the full audio timeline",
    )
    character_name: str = Field(..., description="Speaker name for the segment")
    text_transcript: str = Field(..., description="Transcript spoken in this segment")
    audio_file_path: str = Field(..., description="Local or storage path to the audio file")
    duration_seconds: float = Field(..., gt=0, description="Exact audio duration in seconds")
    voice_config_used: dict[str, Any] = Field(
        default_factory=dict,
        description="Voice config metadata for reproducibility",
    )


class AudioManifest(BaseModel):
    """Manifest tracking generated audio assets and timing."""

    segments: list[AudioSegment] = Field(
        default_factory=list,
        description="Ordered list of audio segments",
    )
    total_duration: float = Field(
        default=0.0,
        ge=0,
        description="Total duration of all segments",
    )
    is_generated: bool = Field(
        default=True,
        description="Indicates audio was generated",
    )
