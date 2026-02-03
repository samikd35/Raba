"""
Agents for MVP Requirements Generator (AMRG)

Multi-agent system for PRD generation:
- TemplateRouterCoarseAgent: Initial template routing
- ClarifyingQuestionsAgent: Generate 3 clarifying questions
- TemplateRouterFinalAgent: Final template selection
- ResearchPlannerAgent: Optional research planning
- PRDGeneratorAgent: Generate PRD JSON
- RepairAgent: Fix validation errors
"""

from .base_agent import BaseAMRGAgent
from .template_router_coarse import TemplateRouterCoarseAgent
from .template_router_final import TemplateRouterFinalAgent
from .clarifying_questions import ClarifyingQuestionsAgent
from .prd_generator import PRDGeneratorAgent
from .repair_agent import RepairAgent

__all__ = [
    "BaseAMRGAgent",
    "TemplateRouterCoarseAgent",
    "TemplateRouterFinalAgent",
    "ClarifyingQuestionsAgent",
    "PRDGeneratorAgent",
    "RepairAgent"
]
