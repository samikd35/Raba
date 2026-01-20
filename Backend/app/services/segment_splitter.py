"""Segment Splitter Service.

Produces per-segment context blocks from the script and the planned
segment windows. This is a lightweight, deterministic implementation
that slices scenes by time window and derives concise fields used by
the Video Generator and template placeholders.

Output fields per segment:
- segment_index, total_segments, start_time, end_time
- segment_script, segment_action
- anchor_state, goal_state
- dialogue_cue (<=15 words), sfx_cue, ambient_cue, music_cue (optional)

This mirrors the CRITIC_IMPROVEMENT_PLAN requirements for P0/P1 while
remaining backward compatible with legacy prompts.
"""

from typing import Any, Dict, List, Tuple

from app.utils.logging import get_logger

logger = get_logger(__name__)


def _truncate_words(text: str, max_words: int = 15) -> str:
    """Truncate a string to at most max_words words."""
    words = (text or "").strip().split()
    if len(words) <= max_words:
        return " ".join(words)
    return " ".join(words[:max_words])


def _slice_scenes_for_window(scenes: List[dict], start: float, end: float) -> List[dict]:
    """Return scenes that overlap [start, end)."""
    window: List[dict] = []
    for sc in scenes or []:
        s = sc.get("timestamp_start") or sc.get("start_time", 0.0)
        e = sc.get("timestamp_end") or sc.get("end_time", (s or 0.0) + 3.0)
        if e > start and s < end:
            window.append(sc)
    return window


def _derive_action_from_scenes(scenes: List[dict]) -> str:
    """Create a succinct action description for the segment."""
    if not scenes:
        return "Continue scene with consistent style and motion."
    # Prefer camera directions + description keywords
    parts: List[str] = []
    for sc in scenes[:2]:  # keep short
        cam = sc.get("camera_direction") or ""
        desc = sc.get("description") or ""
        if cam:
            parts.append(cam.strip())
        if desc:
            parts.append(desc.strip())
    action = ". ".join(p for p in parts if p)
    return action[:300] if action else "Evolve the moment with coherent motion."


def _derive_states(prev_goal: str | None, scenes: List[dict]) -> Tuple[str, str]:
    """Return (anchor_state, goal_state) for the segment."""
    anchor_state = prev_goal or "Initial state"
    # Goal state = last scene description or brief summary
    goal_state = ""
    for sc in reversed(scenes or []):
        if sc.get("description"):
            goal_state = sc["description"]
            break
    if not goal_state:
        goal_state = "Scene continues"
    # Keep short
    if len(goal_state) > 280:
        goal_state = goal_state[:277] + "..."
    return anchor_state, goal_state


def _derive_audio_slice(scenes: List[dict]) -> Dict[str, str]:
    """Derive Dialogue, SFX, Ambient, Music cues from scenes.

    - Dialogue: first non-empty dialogue within the window (<=15 words)
    - SFX: tie first audio_cues entry (if any) to visual action
    - Ambient: fallback to mood/lighting if audio_cues empty
    - Music: optional mood/genre hint from mood
    """
    dialogue_cue = ""
    for sc in scenes or []:
        if sc.get("dialogue"):
            dialogue_cue = _truncate_words(str(sc["dialogue"]).strip(), 15)
            break

    sfx_cue = ""
    ambient_cue = ""
    music_cue = ""

    # Collect audio cues from scenes in order
    raw_audio: List[str] = []
    for sc in scenes or []:
        for cue in sc.get("audio_cues", []) or []:
            if isinstance(cue, str) and cue.strip():
                raw_audio.append(cue.strip())

    if raw_audio:
        sfx_cue = f"{raw_audio[0]} exactly when the visual action occurs."

    # Ambient from mood/lighting as fallback
    for sc in scenes or []:
        mood = sc.get("mood") or ""
        light = sc.get("lighting") or ""
        if mood or light:
            ambient_cue = (mood + ", " + light).strip(", ")
            break

    # Music from mood if available
    for sc in scenes or []:
        mood = sc.get("mood") or ""
        if mood:
            # Simple mapping
            music_cue = f"{mood} score"
            break

    return {
        "dialogue_cue": dialogue_cue,
        "sfx_cue": sfx_cue,
        "ambient_cue": ambient_cue,
        "music_cue": music_cue,
    }


def compute_segment_context_blocks(script_output: dict, segment_plans: List[dict]) -> List[Dict[str, Any]]:
    """Compute per-segment context blocks from script and segment plans."""
    scenes = script_output.get("scenes", []) or []
    total = len(segment_plans or [])
    blocks: List[Dict[str, Any]] = []
    prev_goal: str | None = None

    for seg in segment_plans or []:
        start = float(seg.get("start_time", 0.0))
        end = float(seg.get("end_time", start + float(seg.get("duration", 0.0))))
        window_scenes = _slice_scenes_for_window(scenes, start, end)

        segment_script = " ".join((sc.get("description") or "").strip() for sc in window_scenes)[:800]
        segment_action = _derive_action_from_scenes(window_scenes)
        anchor_state, goal_state = _derive_states(prev_goal, window_scenes)
        audio = _derive_audio_slice(window_scenes)

        block: Dict[str, Any] = {
            "segment_index": int(seg.get("segment_number", 0)),
            "total_segments": total,
            "start_time": start,
            "end_time": end,
            "segment_script": segment_script,
            "segment_action": segment_action,
            "anchor_state": anchor_state,
            "goal_state": goal_state,
            **audio,
        }
        blocks.append(block)
        prev_goal = goal_state

    logger.info(f"Segment Splitter: produced {len(blocks)} context blocks")
    return blocks

