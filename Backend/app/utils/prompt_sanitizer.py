"""Prompt Sanitizer Utilities.

Utilities to sanitize visual prompt text before passing to image/video agents.

Primary goal: strip bracketed audio cues like "[Upbeat music]", "[Sound of rain]"
so visual models don't hallucinate text or audio elements into images.
"""

from __future__ import annotations

import re
from typing import Any, Dict

_BRACKETED_PATTERN = re.compile(r"\[[^\]]*\]")


def clean_visual_prompt(text: str | None) -> str:
    """Remove bracketed metadata like [SFX], [music], [caption] from text.

    Args:
        text: Input text (may be None)

    Returns:
        Sanitized text safe for visual prompting
    """
    if not text:
        return ""
    # Remove any [...] blocks
    cleaned = _BRACKETED_PATTERN.sub("", text)
    # Collapse repeated whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def sanitize_scene(scene: Dict[str, Any]) -> Dict[str, Any]:
    """Return a shallow-copied scene dict with sanitized visual fields.

    - description: stripped of bracketed cues
    - camera_direction, lighting, mood: left as-is
    - dialogue: preserved (sanitizer targets visuals)
    """
    if not isinstance(scene, dict):
        return {}
    out = dict(scene)
    out["description"] = clean_visual_prompt(scene.get("description", ""))
    # Avoid touching dialogue/audio-specific fields here
    return out

