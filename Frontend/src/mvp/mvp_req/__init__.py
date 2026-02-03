"""
MVP Requirements Generator (AMRG)

A LangGraph-based, multi-agent backend service that generates template-compliant
MVP Product Requirements artifacts for existing Yuba projects.

Uses VPS/BMC v1 & v2, Solution Critique, and optionally VPC v2 as context.
"""

__version__ = "1.0.0"

# Lazy imports to avoid circular dependencies during testing
# Import models and templates eagerly (no external deps)
from .models.enums import TemplateCode, ResearchMode, RunStatus
from .models.state_models import AMRGState, ContextPack
from .templates.registry import TEMPLATE_REGISTRY, get_template_spec


def get_amrg_router():
    """Lazy import of AMRG router to avoid auth dependency at module load."""
    from .api.endpoints import router
    return router


def get_amrg_workflow_service():
    """Lazy import of workflow service."""
    from .services.amrg_workflow import AMRGWorkflow, get_amrg_workflow
    return AMRGWorkflow, get_amrg_workflow


def get_context_loader_service():
    """Lazy import of context loader service."""
    from .services.context_loader import ContextLoaderService
    return ContextLoaderService


def get_database_adapter():
    """Lazy import of database adapter."""
    from .services.database_adapter import AMRGDatabaseAdapter, get_amrg_database_adapter
    return AMRGDatabaseAdapter, get_amrg_database_adapter


def get_schema_validator_service():
    """Lazy import of schema validator service."""
    from .services.schema_validator import SchemaValidatorService
    return SchemaValidatorService


__all__ = [
    # Lazy loaders
    "get_amrg_router",
    "get_amrg_workflow_service",
    "get_context_loader_service",
    "get_database_adapter",
    "get_schema_validator_service",
    # Models (eager - no deps)
    "TemplateCode",
    "ResearchMode",
    "RunStatus",
    "AMRGState",
    "ContextPack",
    # Templates (eager - no deps)
    "TEMPLATE_REGISTRY",
    "get_template_spec",
]
