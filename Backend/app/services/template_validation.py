"""Template Validation Service (Phase 4).

Enforces quality standards for script, image, and video templates.
Checks placeholders, minimum word count (150), and presence of key technical specs.
"""

from typing import Iterable, Tuple

from app.services.prompt_builder import PromptBuilderService, get_prompt_builder


class TemplateValidationService:
    def __init__(self, builder: PromptBuilderService | None = None):
        self.builder = builder or get_prompt_builder()

    def validate_script(self, template: str) -> Tuple[bool, list[str]]:
        ok, errs = self.builder.quality_validate(template, ["topic", "tone", "duration"], 150)
        errors = list(errs)
        # Heuristic checks
        must_have = ["HOOK", "pattern", "interrupt", "CTA"]
        text = template.lower()
        for kw in must_have:
            if kw.lower() not in text:
                errors.append(f"missing keyword: {kw}")
        # Enforce visual scaffolding language for scene outputs
        scaffolding = ["vo text", "visual action", "camera metadata"]
        for kw in scaffolding:
            if kw not in text:
                errors.append(f"missing scene scaffold: {kw}")
        return (len(errors) == 0, errors)

    def validate_image(self, template: str) -> Tuple[bool, list[str]]:
        ok, errs = self.builder.quality_validate(template, ["scene_description", "style"], 150)
        errors = list(errs)
        must = ["lighting", "color", "composition", "resolution"]
        tl = template.lower()
        for kw in must:
            if kw not in tl:
                errors.append(f"missing section: {kw}")
        # Encourage/require a negative constraints block or placeholder
        if ("negative" not in tl and "no text" not in tl and "watermark" not in tl
                and "{image_negative_constraint}" not in template):
            errors.append("missing negative constraints or {image_negative_constraint} placeholder")
        # Require ingredients-first composition awareness (preferred) or storyboard fallback
        ingredients_ok = any(
            ind in template or ind in tl
            for ind in [
                "{ingredient_type}",
                "ingredient_subject",
                "ingredient_environment",
                "ingredient_object",
                "ingredients composition",
                "[ingredients",
            ]
        )
        storyboard_ok = any(
            ind in template or ind in tl
            for ind in [
                "{scene_descriptions}",
                "{scene_count}",
                "{key_entities}",
                "{transformation_flow}",
                "{composition_layout}",
                "storyboard",
                "composite",
                "multiple scenes",
            ]
        )
        if not (ingredients_ok or storyboard_ok):
            errors.append("missing ingredients placeholders or storyboard composition awareness")
        return (len(errors) == 0, errors)

    def validate_video(self, template: str) -> Tuple[bool, list[str]]:
        ok, errs = self.builder.quality_validate(template, ["script", "duration"], 150)
        errors = list(errs)
        must = ["camera", "angle", "pacing", "effects", "audio", "consistency"]
        tl = template.lower()
        for kw in must:
            if kw not in tl:
                errors.append(f"missing section: {kw}")
        # Disallow timestamp-based SFX directives like "at 3.2s"
        import re
        if re.search(r"\b(at|@)\s*\d+(?:\.\d+)?\s*s\b", tl):
            errors.append("timestamp-based SFX detected; remove explicit timecodes for audio cues")
        # Require segment-aware placeholders or allow legacy if present
        placeholders = self.builder.extract_placeholders(template)
        segment_keys = {"segment_action", "segment_script", "previous_segment_state", "segment_index", "total_segments"}
        audio_keys = {"dialogue_cue", "sfx_cue", "ambient_cue", "music_cue"}
        has_segment = bool(segment_keys & placeholders)
        has_audio = bool(audio_keys & placeholders)
        has_legacy = ("script" in placeholders and "duration" in placeholders)
        if not (has_segment or has_legacy):
            errors.append("missing segment-aware placeholders (e.g., {segment_action}) or legacy {script}, {duration}")
        if not has_audio:
            errors.append("missing audio placeholders (e.g., {dialogue_cue}, {sfx_cue}, {ambient_cue})")
        return (len(errors) == 0, errors)


_template_validator: TemplateValidationService | None = None


def get_template_validator() -> TemplateValidationService:
    global _template_validator
    if _template_validator is None:
        _template_validator = TemplateValidationService()
    return _template_validator
