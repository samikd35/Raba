"""
Pitch Deck Generator Module (MAV Module 4)

Generates pitch deck content for VMP projects using:
- RAG over project artifacts
- Bounded web research for external facts
- LangGraph workflow for structured generation

API Endpoints:
- POST /api/v1/mav/projects/{project_id}/pitch-deck/generate
- GET /api/v1/mav/projects/{project_id}/pitch-deck
- GET /api/v1/mav/projects/{project_id}/pitch-deck/versions
- GET /api/v1/mav/projects/{project_id}/pitch-deck/status
- GET /api/v1/mav/projects/{project_id}/pitch-deck/preview
"""

from .api.endpoints import router as pitch_router
from .models import (
    DeckPurpose,
    DeckStage,
    DeckCategory,
    SlideType,
    GenerateDeckRequest,
    GenerateDeckResponse,
    DeckPackageResponse,
)
from .workflow.pitch_workflow import run_pitch_deck_generation

__all__ = [
    "pitch_router",
    "DeckPurpose",
    "DeckStage",
    "DeckCategory",
    "SlideType",
    "GenerateDeckRequest",
    "GenerateDeckResponse",
    "DeckPackageResponse",
    "run_pitch_deck_generation",
]
