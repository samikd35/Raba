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
                    "ffmpeg",
                    "-y",
                    "-i",
                    in_path,
                    "-ss",
                    str(start),
                    "-to",
                    str(end),
                    "-c",
                    "copy",
                    out_path,
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
                    "ffmpeg",
                    "-y",
                    "-i",
                    in_path,
                    "-t",
                    str(float(target_duration_seconds)),
                    "-c",
                    "copy",
                    out_path,
                ]
                proc = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                _out, err = await proc.communicate()
                if proc.returncode != 0:
                    logger.warning(
                        f"ffmpeg trim_to_duration failed: {err.decode(errors='ignore')[:200]}"
                    )
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
                    "ffmpeg",
                    "-y",
                    "-i",
                    in_path,
                    "-an",  # Remove audio
                    "-c:v",
                    "copy",  # Copy video stream without re-encoding
                    out_path,
                ]
                proc = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                _out, err = await proc.communicate()
                if proc.returncode != 0:
                    logger.warning(
                        f"ffmpeg audio strip failed: {err.decode(errors='ignore')[:200]}"
                    )
                    return input_bytes

                with open(out_path, "rb") as f:
                    out_bytes = f.read()

                logger.info(
                    f"Audio stripped successfully: {len(input_bytes)} -> {len(out_bytes)} bytes"
                )
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


async def replace_audio_in_video(
    video_bytes: bytes,
    audio_segments: list[tuple[bytes, float]],
) -> bytes:
    """Replace video audio track with provided audio segments.

    Strips existing audio from video and merges with provided audio segments,
    concatenated in order. Uses FFmpeg for processing.

    Args:
        video_bytes: Input video bytes (with Veo audio to be replaced)
        audio_segments: List of (audio_bytes, start_time) tuples for each segment

    Returns:
        Video bytes with replaced audio track
    """
    try:
        import shutil
        import tempfile
        import os

        has_ffmpeg = shutil.which("ffmpeg") is not None
        if not has_ffmpeg:
            logger.warning(
                "ffmpeg not found; cannot replace audio - video will retain original audio"
            )
            return video_bytes

        if not audio_segments:
            logger.warning("No audio segments provided; returning original video")
            return video_bytes

        with tempfile.TemporaryDirectory() as td:
            video_path = os.path.join(td, "input_video.mp4")
            silent_path = os.path.join(td, "silent_video.mp4")
            merged_audio_path = os.path.join(td, "merged_audio.wav")
            output_path = os.path.join(td, "final_output.mp4")

            # Write input video
            with open(video_path, "wb") as f:
                f.write(video_bytes)

            # Step 1: Strip audio from video
            strip_cmd = [
                "ffmpeg",
                "-y",
                "-i",
                video_path,
                "-an",
                "-c:v",
                "copy",
                silent_path,
            ]
            proc = await asyncio.create_subprocess_exec(
                *strip_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            _, err = await proc.communicate()
            if proc.returncode != 0:
                logger.warning(f"ffmpeg strip audio failed: {err.decode(errors='ignore')[:200]}")
                return video_bytes

            logger.info("Stripped Veo audio from video")

            # Step 2: Write and concatenate audio segments
            audio_file_list = []
            concat_list_path = os.path.join(td, "audio_list.txt")

            sorted_segments = sorted(audio_segments, key=lambda seg: float(seg[1] or 0.0))
            concat_entries = []
            current_time = 0.0
            for idx, (audio_bytes, start_time) in enumerate(sorted_segments):
                start_time = float(start_time or 0.0)
                if start_time > current_time + 0.01:
                    gap_seconds = max(0.0, start_time - current_time)
                    silence_path = os.path.join(td, f"silence_{idx}.wav")
                    silence_cmd = [
                        "ffmpeg",
                        "-y",
                        "-f",
                        "lavfi",
                        "-i",
                        f"anullsrc=channel_layout=mono:sample_rate=24000",
                        "-t",
                        f"{gap_seconds:.3f}",
                        "-c:a",
                        "pcm_s16le",
                        silence_path,
                    ]
                    proc = await asyncio.create_subprocess_exec(
                        *silence_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                    )
                    _, err = await proc.communicate()
                    if proc.returncode != 0:
                        logger.warning(
                            f"ffmpeg silence generation failed: {err.decode(errors='ignore')[:200]}"
                        )
                        return video_bytes
                    concat_entries.append(f"file '{silence_path}'")
                    current_time += gap_seconds

                audio_path = os.path.join(td, f"audio_{idx}.wav")
                with open(audio_path, "wb") as f:
                    f.write(audio_bytes)
                normalized_path = os.path.join(td, f"audio_norm_{idx}.wav")
                normalize_cmd = [
                    "ffmpeg",
                    "-y",
                    "-i",
                    audio_path,
                    "-ac",
                    "1",
                    "-ar",
                    "24000",
                    "-c:a",
                    "pcm_s16le",
                    normalized_path,
                ]
                proc = await asyncio.create_subprocess_exec(
                    *normalize_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                _, err = await proc.communicate()
                if proc.returncode != 0:
                    logger.warning(
                        f"ffmpeg audio normalize failed: {err.decode(errors='ignore')[:200]}"
                    )
                    return video_bytes
                concat_entries.append(f"file '{normalized_path}'")

                try:
                    import wave

                    with wave.open(normalized_path, "rb") as wf:
                        frames = wf.getnframes()
                        rate = wf.getframerate() or 24000
                        current_time += frames / float(rate)
                except Exception:
                    pass

            if not concat_entries:
                logger.warning("No audio entries to concat after processing")
                return video_bytes

            with open(concat_list_path, "w") as f:
                f.write("\n".join(concat_entries))

            # Concatenate audio segments (re-encode to avoid format mismatches)
            concat_cmd = [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                concat_list_path,
                "-c:a",
                "pcm_s16le",
                merged_audio_path,
            ]
            proc = await asyncio.create_subprocess_exec(
                *concat_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            _, err = await proc.communicate()
            if proc.returncode != 0:
                logger.warning(f"ffmpeg concat audio failed: {err.decode(errors='ignore')[:200]}")
                return video_bytes

            logger.info(f"Concatenated {len(audio_segments)} audio segments")

            # Step 3: Merge silent video with new audio
            # Use -shortest to handle duration mismatch
            merge_cmd = [
                "ffmpeg",
                "-y",
                "-i",
                silent_path,
                "-i",
                merged_audio_path,
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-shortest",
                output_path,
            ]
            proc = await asyncio.create_subprocess_exec(
                *merge_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            _, err = await proc.communicate()
            if proc.returncode != 0:
                logger.warning(f"ffmpeg merge audio failed: {err.decode(errors='ignore')[:200]}")
                return video_bytes

            with open(output_path, "rb") as f:
                output_bytes = f.read()

            logger.info(
                f"Audio replaced successfully: {len(video_bytes)} -> {len(output_bytes)} bytes"
            )
            return output_bytes or video_bytes

    except Exception as e:
        logger.warning(f"Audio replacement failed, returning original video: {e}")
        return video_bytes
