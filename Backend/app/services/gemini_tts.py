"""RABA Gemini TTS Service.

Wrapper for Gemini native text-to-speech generation.
"""

import asyncio
import io
import wave
from typing import Any, Optional

from google import genai
from google.genai import types

from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

GEMINI_TTS_FLASH = "gemini-2.5-flash-preview-tts"
GEMINI_TTS_PRO = "gemini-2.5-pro-preview-tts"


class GeminiTTSServiceError(Exception):
    """Base exception for Gemini TTS service errors."""


class GeminiTTSAPIError(GeminiTTSServiceError):
    """Raised when the Gemini TTS API call fails."""


class GeminiTTSService:
    """Service wrapper for Gemini native TTS generation."""

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or get_settings().google_api_key
        self._client: Optional[genai.Client] = None

        if not self._api_key:
            logger.warning("No Google API key configured for Gemini TTS")

    def _get_client(self) -> genai.Client:
        if self._client is None:
            if not self._api_key:
                raise GeminiTTSServiceError("Google API key not configured")
            self._client = genai.Client(api_key=self._api_key)
            logger.info("Created GenAI client for TTS")
        return self._client

    async def generate_speech(
        self,
        prompt: str,
        *,
        voice_name: str,
        model: str = GEMINI_TTS_FLASH,
        sample_rate: int = 24000,
        speakers: Optional[list[dict[str, str]]] = None,
    ) -> tuple[bytes, float, dict[str, Any]]:
        """Generate TTS audio.

        Args:
            prompt: Full TTS prompt text
            voice_name: Prebuilt voice name for single-speaker
            model: TTS model
            sample_rate: PCM sample rate
            speakers: Optional multi-speaker config

        Returns:
            Tuple of (wav_bytes, duration_seconds, metadata)
        """
        client = self._get_client()

        speech_config = None
        if speakers:
            speaker_configs = []
            for sp in speakers[:2]:
                speaker = sp.get("speaker")
                voice = sp.get("voice_name")
                if not speaker or not voice:
                    continue
                speaker_configs.append(
                    types.SpeakerVoiceConfig(
                        speaker=speaker,
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
                        ),
                    )
                )
            if speaker_configs:
                speech_config = types.SpeechConfig(
                    multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
                        speaker_voice_configs=speaker_configs
                    )
                )

        if speech_config is None:
            speech_config = types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
                )
            )

        config = types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=speech_config,
        )

        try:
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=model,
                contents=prompt,
                config=config,
            )
        except Exception as exc:
            logger.error(f"Gemini TTS API call failed: {exc}")
            raise GeminiTTSAPIError(str(exc)) from exc

        usage_metadata = None
        usage = getattr(response, "usage_metadata", None)
        if usage:
            try:
                usage_metadata = {
                    "input_tokens": int(getattr(usage, "prompt_token_count", 0) or 0),
                    "output_tokens": int(getattr(usage, "candidates_token_count", 0) or 0),
                    "total_tokens": int(getattr(usage, "total_token_count", 0) or 0),
                }
            except Exception:
                usage_metadata = None

        try:
            candidates = response.candidates or []
            candidate_content = candidates[0].content if candidates else None
            parts = candidate_content.parts if candidate_content else []
            inline_data = parts[0].inline_data if parts else None
            pcm_data = inline_data.data if inline_data else None
        except Exception as exc:
            logger.error(f"Gemini TTS response parsing failed: {exc}")
            raise GeminiTTSServiceError("Invalid TTS response") from exc

        if not pcm_data:
            raise GeminiTTSServiceError("Empty audio data from TTS response")

        duration_seconds = len(pcm_data) / float(sample_rate * 2)

        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm_data)

        metadata = {
            "model": model,
            "voice_name": voice_name,
            "sample_rate": sample_rate,
            "multi_speaker": bool(speakers),
            "usage_metadata": usage_metadata,
        }

        return wav_buffer.getvalue(), duration_seconds, metadata


_gemini_tts_service: Optional[GeminiTTSService] = None


def get_gemini_tts_service() -> GeminiTTSService:
    """Get singleton Gemini TTS service instance."""
    global _gemini_tts_service
    if _gemini_tts_service is None:
        _gemini_tts_service = GeminiTTSService()
    return _gemini_tts_service
