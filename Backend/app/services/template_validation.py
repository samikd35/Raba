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
        return (len(errors) == 0, errors)

    def validate_image(self, template: str) -> Tuple[bool, list[str]]:
        ok, errs = self.builder.quality_validate(template, ["scene_description", "style"], 150)
        errors = list(errs)
        must = ["lighting", "color", "composition", "resolution"]
        tl = template.lower()
        for kw in must:
            if kw not in tl:
                errors.append(f"missing section: {kw}")
        return (len(errors) == 0, errors)

    def validate_video(self, template: str) -> Tuple[bool, list[str]]:
        ok, errs = self.builder.quality_validate(template, ["script", "duration"], 150)
        errors = list(errs)
        must = ["camera", "angle", "pacing", "effects", "audio", "consistency"]
        tl = template.lower()
        for kw in must:
            if kw not in tl:
                errors.append(f"missing section: {kw}")
        return (len(errors) == 0, errors)


_template_validator: TemplateValidationService | None = None


def get_template_validator() -> TemplateValidationService:
    global _template_validator
    if _template_validator is None:
        _template_validator = TemplateValidationService()
    return _template_validator

