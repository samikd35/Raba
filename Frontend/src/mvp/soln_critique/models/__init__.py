"""
Models for Solution Critique feature
"""
from .state_models import (
    SolutionCritiqueState,
    CritiqueResult,
    SearchQuery,
    SourceReference
)
from .response_models import (
    CritiqueGenerateRequest,
    CritiqueGenerateResponse,
    CritiqueStatusResponse,
    CritiqueResultsResponse
)

__all__ = [
    'SolutionCritiqueState',
    'CritiqueResult',
    'SearchQuery',
    'SourceReference',
    'CritiqueGenerateRequest',
    'CritiqueGenerateResponse',
    'CritiqueStatusResponse',
    'CritiqueResultsResponse'
]
