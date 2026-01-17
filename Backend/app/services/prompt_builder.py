"""Prompt Builder Service.

Centralized service to render tool prompt templates with context,
validate placeholders and quality, and provide safe fallbacks.

Follows RABA logging patterns and error handling.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Any, Iterable, Optional, Set

from app.utils.logging import get_logger

logger = get_logger(__name__)


PLACEHOLDER_PATTERN = re.compile(r"\{([a-zA-Z0-9_]+)\}")


@dataclass
class RenderResult:
    """Result from rendering a template."""

    prompt: str
    used_placeholders: Set[str]
    missing_placeholders: Set[str]
    render_time_ms: int
    fallback_used: bool = False


class PromptBuilderService:
    """Service for rendering and validating prompt templates.

    Responsibilities:
    - Extract placeholders
    - Render templates with provided context
    - Validate presence of required placeholders and word count
    - Log detailed diagnostics for observability
    """

    MIN_WORDS_DEFAULT = 20  # runtime minimum; stricter checks can be used at write/update time

    def extract_placeholders(self, template: str) -> Set[str]:
        return set(PLACEHOLDER_PATTERN.findall(template or ""))

    def render(
        self,
        template: Optional[str],
        context: dict[str, Any],
        *,
        required: Optional[Iterable[str]] = None,
        min_words: int = MIN_WORDS_DEFAULT,
        fallback_prompt_builder: Optional[callable[[], str]] = None,
        log_context_debug: bool = True,
    ) -> RenderResult:
        """Render a template with context and optional fallback.

        If the template is None/empty or validation fails critically,
        uses the provided fallback_prompt_builder if present.
        """
        start = time.time()
        required_set: Set[str] = set(required or [])

        if not template or not template.strip():
            logger.warning("PromptBuilder: Missing template; using fallback")
            prompt = fallback_prompt_builder() if fallback_prompt_builder else ""
            return RenderResult(
                prompt=prompt,
                used_placeholders=set(),
                missing_placeholders=required_set,
                render_time_ms=int((time.time() - start) * 1000),
                fallback_used=True,
            )

        placeholders = self.extract_placeholders(template)
        if required_set:
            missing_req = required_set - placeholders
            if missing_req:
                logger.warning(
                    f"PromptBuilder: Template missing required placeholders: {sorted(missing_req)}"
                )

        # Build replacement map as strings
        safe_context: dict[str, str] = {}
        for k, v in (context or {}).items():
            try:
                safe_context[k] = str(v if v is not None else "")
            except Exception:
                safe_context[k] = ""

        # Replace placeholders: {name} -> value, leave unknown placeholders intact
        def replace(match: re.Match[str]) -> str:
            key = match.group(1)
            if key in safe_context:
                return safe_context[key]
            return match.group(0)

        rendered = PLACEHOLDER_PATTERN.sub(replace, template)

        # Compute missing placeholders that remained unreplaced (present in template but not in context)
        remained = self.extract_placeholders(rendered)
        missing_in_context = placeholders & remained
        if missing_in_context:
            logger.warning(
                f"PromptBuilder: Missing context for placeholders: {sorted(missing_in_context)}"
            )

        if log_context_debug:
            logger.debug(
                f"PromptBuilder: Context keys=({', '.join(sorted(safe_context.keys()))})"
            )

        # Basic length check
        word_count = len(rendered.split())
        if word_count < min_words:
            logger.debug(
                f"PromptBuilder: Rendered prompt is short ({word_count} words). min_words={min_words}"
            )

        elapsed = int((time.time() - start) * 1000)
        logger.info(f"PromptBuilder: Rendered in {elapsed}ms (placeholders={len(placeholders)})")

        return RenderResult(
            prompt=rendered,
            used_placeholders=placeholders - missing_in_context,
            missing_placeholders=missing_in_context,
            render_time_ms=elapsed,
            fallback_used=False,
        )

    def runtime_validate(self, template: str, required: Iterable[str], min_words: int = MIN_WORDS_DEFAULT) -> tuple[bool, list[str]]:
        """Runtime validation: check required placeholders and word count."""
        errors: list[str] = []
        placeholders = self.extract_placeholders(template)
        missing = set(required) - placeholders
        if missing:
            errors.append(f"Missing placeholders: {sorted(missing)}")
        if len(template.split()) < min_words:
            errors.append(f"Too short: {len(template.split())} words < {min_words}")
        return (len(errors) == 0, errors)

    def quality_validate(self, template: str, required: Iterable[str], min_words: int = 150) -> tuple[bool, list[str]]:
        """Stricter validation for write/update flows (Phase 2 quality standards)."""
        return self.runtime_validate(template, required=required, min_words=min_words)


_prompt_builder: Optional[PromptBuilderService] = None


def get_prompt_builder() -> PromptBuilderService:
    global _prompt_builder
    if _prompt_builder is None:
        _prompt_builder = PromptBuilderService()
    return _prompt_builder

