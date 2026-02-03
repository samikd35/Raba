"""
Go-To-Market (GTM) Strategy Generator Module

Generates complete GTM Strategy Packs for VMP projects using:
- RAG retrieval from project artifacts (filtered by tenant/project)
- Optional bounded web search for market insights and channel data
- 8-step GTM structure with citations and versioning
"""

from .models import (
    GTMStepType,
    GTMGenerationStatus,
    EvidenceGrade,
    GTMStepContent,
    GTMStrategyPack,
    GTMState,
    GenerateGTMRequest,
    GenerateGTMResponse,
    GTMPackResponse,
    GTMStatusResponse,
)

__all__ = [
    "GTMStepType",
    "GTMGenerationStatus",
    "EvidenceGrade",
    "GTMStepContent",
    "GTMStrategyPack",
    "GTMState",
    "GenerateGTMRequest",
    "GenerateGTMResponse",
    "GTMPackResponse",
    "GTMStatusResponse",
]
