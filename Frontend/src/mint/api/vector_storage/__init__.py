"""
Vector Storage Module

This module provides comprehensive vector storage and RAG functionality for preserving
context across modules in the Yuba platform.

Key Features:
- Document storage with vector embeddings
- Problem validation report storage
- Actionable insights with semantic search
- Module context preservation
- Cross-module information retrieval
"""

from .endpoints import router as vector_storage_router
from .service import VectorStorageService
from .models import (
    Document, DocumentCreate, DocumentUpdate, DocumentResponse, DocumentListResponse,
    Chunk, ChunkCreate, ChunkUpdate,
    ProblemValidationReport, ProblemValidationReportCreate, ProblemValidationReportUpdate,
    ProblemValidationReportResponse,
    ActionableInsight, ActionableInsightCreate, ActionableInsightUpdate, ActionableInsightResponse,
    VectorSearchRequest, VectorSearchResponse, VectorSearchResult,
    SourceType
)

__all__ = [
    # Router
    "vector_storage_router",
    
    # Service
    "VectorStorageService",
    
    # Models
    "Document", "DocumentCreate", "DocumentUpdate", "DocumentResponse", "DocumentListResponse",
    "Chunk", "ChunkCreate", "ChunkUpdate",
    "ProblemValidationReport", "ProblemValidationReportCreate", "ProblemValidationReportUpdate",
    "ProblemValidationReportResponse",
    "ActionableInsight", "ActionableInsightCreate", "ActionableInsightUpdate", "ActionableInsightResponse",
    "VectorSearchRequest", "VectorSearchResponse", "VectorSearchResult",
    "SourceType"
]
