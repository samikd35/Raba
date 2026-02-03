"""
Report Management Module

This module provides comprehensive report management functionality for the MINT system,
including report creation, retrieval, analytics, validation, and lifecycle management.

Components:
- models: Report data models and schemas
- history: Report history management
- analytics: Report analytics and visualization
- services: Various report services (chunking, filtering, search, etc.)
- validation: Report validation and error handling
"""

from .report_models import *
from .report_history_endpoints import router as history_router
from .report_history_service import ReportHistoryService
from .report_analytics_visualization_service import ReportAnalyticsVisualizationService
from .report_chunking_service import ReportChunkingService
# from .report_deletion_service import ReportDeletionService  # File is empty
from .report_error_handler import ReportErrorHandler, get_report_error_handler, ReportErrorType
from .report_filtering_service import ReportFilteringService
from .report_migration_service import ReportMigrationService
from .report_retrieval_service import ReportRetrievalService, get_report_retrieval_service
from .report_search_service import ReportSearchService
from .report_sorting_pagination_service import ReportSortingPaginationService
from .report_synchronization_service import ReportSynchronizationService
from .report_trend_detection_service import ReportTrendDetectionService
from .report_usage_analytics_service import ReportUsageAnalyticsService
from .report_validation_service import ReportValidationService, get_report_validation_service

# Public API
__all__ = [
    # Models
    "ReportModel",
    "ReportHistoryModel", 
    "ReportAnalyticsModel",
    "ReportSearchModel",
    "ReportValidationModel",
    
    # History
    "history_router",
    "ReportHistoryService",
    
    # Analytics
    "ReportAnalyticsVisualizationService",
    
    # Services
    "ReportChunkingService",
    # "ReportDeletionService",  # File is empty
    "ReportFilteringService",
    "ReportMigrationService",
    "ReportRetrievalService",
    "get_report_retrieval_service",
    "ReportSearchService",
    "ReportSortingPaginationService",
    "ReportSynchronizationService",
    "ReportTrendDetectionService",
    "ReportUsageAnalyticsService",
    
    # Validation
    "ReportValidationService",
    "get_report_validation_service",
    "ReportErrorHandler",
    "get_report_error_handler",
    "ReportErrorType"
]

# Module metadata
__version__ = "1.0.0"
__author__ = "MINT Development Team"
__description__ = "Report management module for MINT API"

