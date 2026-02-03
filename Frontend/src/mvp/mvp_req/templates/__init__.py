"""
Template System for MVP Requirements Generator

Contains:
- Template registry mapping TemplateCode -> TemplateSpec
- JSON schemas for each template
- Jinja2 prompt templates for PRD generation
"""

from .registry import (
    TemplateSpec,
    TEMPLATE_REGISTRY,
    get_template_spec,
    get_all_template_codes,
    get_templates_by_category
)

__all__ = [
    "TemplateSpec",
    "TEMPLATE_REGISTRY",
    "get_template_spec",
    "get_all_template_codes",
    "get_templates_by_category"
]
