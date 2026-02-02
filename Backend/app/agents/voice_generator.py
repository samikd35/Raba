"""RABA Voice Generator Agent.

Generates Gemini TTS audio segments before video generation.
"""

import time
from typing import Any, Optional

from app.graph.state import VideoGenerationState
from app.models.audio import AudioManifest, AudioSegment, VoiceProfile
from app.agents.video_generator import plan_video_segments
from app.services.gemini_tts import get_gemini_tts_service
from app.services.segment_splitter import compute_segment_context_blocks
from app.services.supabase import get_supabase_client
from app.utils.helpers import utc_now_iso
from app.utils.logging import get_logger

logger = get_logger(__name__)


DEFAULT_VOICE_NAME = "Kore"
SECONDARY_VOICE_NAME = "Puck"
VOICE_POOL = ["Kore", "Puck", "Charon", "Leda"]


def _build_voice_prompt(
    character_name: str,
    transcript: str,
    mood: str,
    style_preset: str,
    scene_description: str,
) -> str:
    """Build a Gemini TTS prompt with director-style guidance."""
    mood_line = f"Mood: {mood}." if mood else ""
    style_line = f"Style: {style_preset}." if style_preset else ""
    scene_line = f"Scene: {scene_description}." if scene_description else ""

    return (
        f"AUDIO PROFILE: {character_name}\n"
        f"{scene_line}\n"
        f"DIRECTOR'S NOTES: {mood_line} {style_line}\n"
        f"TRANSCRIPT:\n{transcript}\n"
    )


class VoiceGeneratorAgent:
    """Agent for generating TTS audio before video generation."""

    def __init__(self):
        self.tts_service = get_gemini_tts_service()
        self.supabase = get_supabase_client()
        logger.info("VoiceGeneratorAgent initialized")

    def _build_voice_profiles(self, script_output: dict) -> dict[str, VoiceProfile]:
        voice_profiles: dict[str, VoiceProfile] = {}
        lead_name = script_output.get("lead_character")
        lead_desc = script_output.get("lead_character_description") or ""
        narrator_name = "Narrator"

        narrator_profile = VoiceProfile(
            character_name=narrator_name,
            voice_name=DEFAULT_VOICE_NAME,
            gender="neutral",
            style_preset="",
        )
        voice_profiles[narrator_name] = narrator_profile

        if lead_name:
            style = f"Voice matches: {lead_desc}"[:240] if lead_desc else ""
            voice_profiles[lead_name] = VoiceProfile(
                character_name=lead_name,
                voice_name=SECONDARY_VOICE_NAME,
                gender="neutral",
                style_preset=style,
            )

        return voice_profiles

    def _ensure_voice_profile(
        self,
        voice_profiles: dict[str, VoiceProfile],
        character_name: str,
    ) -> VoiceProfile:
        if character_name in voice_profiles:
            return voice_profiles[character_name]

        used_voices = {vp.voice_name for vp in voice_profiles.values()}
        voice_name = next(
            (voice for voice in VOICE_POOL if voice not in used_voices),
            DEFAULT_VOICE_NAME,
        )
        profile = VoiceProfile(
            character_name=character_name,
            voice_name=voice_name,
            gender="neutral",
            style_preset="",
        )
        voice_profiles[character_name] = profile
        return profile

    def _select_character_for_segment(
        self,
        script_output: dict,
        window_scenes: list[dict],
    ) -> str:
        lead_name = script_output.get("lead_character")
        for scene in window_scenes:
            candidate = scene.get("character_name")
            if candidate:
                return str(candidate)
        if lead_name and any(scene.get("dialogue") for scene in window_scenes):
            return str(lead_name)
        return "Narrator"

    def _slice_scenes_for_window(
        self,
        scenes: list[dict],
        start_time: float,
        end_time: float,
    ) -> list[dict]:
        window = []
        for scene in scenes:
            scene_start = scene.get("timestamp_start") or scene.get("start_time", 0.0)
            scene_end = scene.get("timestamp_end") or scene.get("end_time", scene_start + 3.0)
            if scene_end > start_time and scene_start < end_time:
                window.append(scene)
        return window

    def _build_segment_transcript(
        self,
        hook: dict,
        scenes: list[dict],
        cta: dict,
        is_first: bool,
        is_last: bool,
    ) -> str:
        parts: list[str] = []
        if is_first and hook.get("script"):
            parts.append(str(hook.get("script")))
        for scene in scenes:
            if scene.get("dialogue"):
                parts.append(str(scene.get("dialogue")))
        if is_last and cta.get("script"):
            parts.append(str(cta.get("script")))
        return " ".join(p for p in parts if p).strip()

    async def _upload_audio(self, audio_bytes: bytes, storage_path: str) -> tuple[str, str]:
        try:
            bucket_name = "media"
            full_path = f"generated_audio/{storage_path}"
            self.supabase.storage.from_(bucket_name).upload(
                path=full_path,
                file=audio_bytes,
                file_options={"content-type": "audio/wav"},
            )
            public_url = self.supabase.storage.from_(bucket_name).get_public_url(full_path)
            logger.info(f"Uploaded audio segment to {full_path}")
            return public_url, full_path
        except Exception as exc:
            logger.error(f"Audio upload failed: {exc}")
            return f"upload_failed://{storage_path}", storage_path

    async def _persist_manifest(self, workflow_id: str, manifest: AudioManifest) -> None:
        try:
            self.supabase.table("workflows").update(
                {
                    "audio_output": manifest.model_dump(mode="json"),
                    "updated_at": utc_now_iso(),
                }
            ).eq("id", workflow_id).execute()
        except Exception as exc:
            logger.warning(f"Failed to persist audio manifest: {exc}")

    async def _persist_media_entries(
        self,
        workflow_id: str,
        manifest: AudioManifest,
        storage_paths: list[str],
    ) -> None:
        try:
            for idx, segment in enumerate(manifest.segments):
                storage_path = storage_paths[idx] if idx < len(storage_paths) else None
                self.supabase.table("media").insert(
                    {
                        "workflow_id": workflow_id,
                        "media_type": "audio",
                        "source": "generated",
                        "storage_url": segment.audio_file_path,
                        "storage_path": storage_path,
                        "mime_type": "audio/wav",
                        "duration_seconds": segment.duration_seconds,
                        "metadata": {
                            "segment_id": segment.segment_id,
                            "character_name": segment.character_name,
                            "voice": segment.voice_config_used,
                        },
                    }
                ).execute()
        except Exception as exc:
            logger.warning(f"Failed to persist audio media entries: {exc}")

    async def run(self, state: VideoGenerationState) -> dict[str, Any]:
        """Generate audio manifest from script output."""
        workflow_id = state.get("workflow_id", "unknown")
        logger.info(f"Starting voice generation for workflow: {workflow_id}")

        if state.get("audio_manifest"):
            logger.info("[CONTINUE] Skipping Voice Generator (audio_manifest already in state)")
            return {}

        start_time = time.time()
        try:
            script_output = state.get("script_output") or {}
            scenes = script_output.get("scenes", []) or []
            hook = script_output.get("hook", {}) or {}
            cta = script_output.get("call_to_action", {}) or {}

            voice_profiles = self._build_voice_profiles(script_output)
            requested_duration = float(state.get("duration_seconds", 18))
            base_duration = float(script_output.get("total_duration_seconds") or requested_duration)
            logger.info(
                f"Audio-first planning: base_duration={base_duration}s, voices={list(voice_profiles.keys())}"
            )
            segment_plans = plan_video_segments(int(base_duration))
            segment_contexts = compute_segment_context_blocks(
                script_output=script_output,
                segment_plans=segment_plans,
            )

            total_duration = 0.0
            segments: list[AudioSegment] = []
            storage_paths: list[str] = []
            timeline_cursor = 0.0

            for idx, plan in enumerate(segment_plans):
                start_time = float(plan.get("start_time", 0.0))
                end_time = float(plan.get("end_time", start_time + 4.0))
                window_scenes = self._slice_scenes_for_window(scenes, start_time, end_time)

                character = self._select_character_for_segment(script_output, window_scenes)
                profile = self._ensure_voice_profile(voice_profiles, character)
                logger.info(
                    f"Generating audio segment {idx}: {character} ({profile.voice_name}), window {start_time:.2f}-{end_time:.2f}s"
                )
                transcript = self._build_segment_transcript(
                    hook=hook,
                    scenes=window_scenes,
                    cta=cta,
                    is_first=idx == 0,
                    is_last=idx == len(segment_plans) - 1,
                )

                if not transcript:
                    logger.warning(f"Skipping audio segment {idx}: empty transcript")
                    continue

                context = segment_contexts[idx] if idx < len(segment_contexts) else {}
                prompt = _build_voice_prompt(
                    character_name=character,
                    transcript=transcript,
                    mood=context.get("ambient_cue") or "",
                    style_preset=profile.style_preset,
                    scene_description=context.get("segment_action") or "",
                )

                audio_bytes, duration, meta = await self.tts_service.generate_speech(
                    prompt=prompt,
                    voice_name=profile.voice_name,
                )
                logger.info(
                    f"Generated audio segment {idx}: {duration:.2f}s, transcript_length={len(transcript)}"
                )

                storage_path = f"{workflow_id}/segment_{idx}.wav"
                audio_url, storage_full_path = await self._upload_audio(audio_bytes, storage_path)
                storage_paths.append(storage_full_path)

                segments.append(
                    AudioSegment(
                        segment_id=idx,
                        start_time=timeline_cursor,
                        end_time=timeline_cursor + duration,
                        character_name=character,
                        text_transcript=transcript,
                        audio_file_path=audio_url,
                        duration_seconds=duration,
                        voice_config_used=meta,
                    )
                )
                timeline_cursor += duration
                total_duration += duration

            manifest = AudioManifest(
                segments=segments,
                total_duration=total_duration,
                is_generated=True,
            )

            drift = abs(total_duration - requested_duration)
            if drift > 0.35:
                logger.warning(
                    "Audio duration drift detected: requested=%.2fs, actual=%.2fs",
                    requested_duration,
                    total_duration,
                )

            await self._persist_manifest(workflow_id, manifest)
            await self._persist_media_entries(workflow_id, manifest, storage_paths)

            try:
                from app.services.monitoring import get_monitoring_service

                input_tokens = 0
                output_tokens = 0
                for seg in segments:
                    usage_meta = seg.voice_config_used.get("usage_metadata") or {}
                    input_tokens += int(usage_meta.get("input_tokens", 0) or 0)
                    output_tokens += int(usage_meta.get("output_tokens", 0) or 0)

                used_estimate = False
                if not segments or (input_tokens == 0 and output_tokens == 0):
                    used_estimate = True
                    for seg in segments:
                        transcript = seg.text_transcript or ""
                        input_tokens += max(0, int(len(transcript) / 4))
                        output_tokens += max(0, int((seg.duration_seconds * 24000 * 2) / 4))

                model_name = "gemini-2.5-flash-preview-tts"
                if segments:
                    model_name = segments[-1].voice_config_used.get("model", model_name)

                await get_monitoring_service().record_audio_usage(
                    video_id=workflow_id,
                    model=model_name,
                    audio_duration_seconds=float(total_duration),
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    generation_duration_seconds=float(time.time() - start_time),
                    success=True,
                    metadata={
                        "segments": len(segments),
                        "voices": [seg.character_name for seg in segments],
                        "estimated": used_estimate,
                    },
                )
            except Exception as me:
                logger.warning(f"Monitoring audio usage failed: {me}")

            elapsed = int((time.time() - start_time) * 1000)
            logger.info(
                f"Voice generation completed: {len(segments)} segments, {total_duration:.2f}s"
            )

            return {
                "audio_manifest": manifest.model_dump(mode="json"),
                "audio_output": manifest.model_dump(mode="json"),
                "segment_contexts": segment_contexts,
                "segment_context_status": "audio_planned",
                "phase_timestamps": {
                    **state.get("phase_timestamps", {}),
                    "voice_generator_completed": utc_now_iso(),
                    "voice_generator_duration_ms": str(elapsed),
                },
            }

        except Exception as exc:
            logger.error(f"Voice generation failed: {exc}")
            return {
                "error": f"Voice generation failed: {str(exc)}",
                "error_details": {
                    "phase": "voice_generator",
                    "workflow_id": workflow_id,
                    "error_type": type(exc).__name__,
                },
            }


_voice_generator_agent: Optional[VoiceGeneratorAgent] = None


def get_voice_generator_agent() -> VoiceGeneratorAgent:
    """Get singleton VoiceGeneratorAgent instance."""
    global _voice_generator_agent
    if _voice_generator_agent is None:
        _voice_generator_agent = VoiceGeneratorAgent()
    return _voice_generator_agent
