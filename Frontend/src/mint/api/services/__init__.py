"""
Services Module

This module provides various utility services for the MINT system,
including email, notification, storage, and other supporting services.

Components:
- email: Email service
- notification: Notification service
- storage: Storage services
- sync: Synchronization services
- export: Export services
- monitoring: Monitoring services
"""

from .communication.email_service import EmailService, email_service
from .communication.notification_service import NotificationManager, notification_manager
from .storage.chunk_storage_service import ChunkStorageService, get_chunk_storage_service
from .sync.offline_sync_service import OfflineSyncService
from .export.engagement_export_service import EngagementExportService, engagement_export_service
from .monitoring.engagement_monitoring_service import EngagementMonitoringService, engagement_monitoring_service
from .utilities.fallback_service import FallbackService, fallback_service
from .ai.prompt_engineering_service import PromptEngineeringService
from .utilities.query_optimizer import QueryOptimizer, get_query_optimizer
from .utilities.response_processing_service import ResponseProcessingService
from .utilities.retention_policy_service import RetentionPolicyService
from .sync.sync_prioritization_service import SyncPrioritizationService
from .export.universal_export_service import UniversalExportService, universal_export_service

# Public API
__all__ = [
    # Email
    "EmailService",
    "email_service",
    
    # Notification
    "NotificationManager",
    "notification_manager",
    
    # Storage
    "ChunkStorageService",
    "get_chunk_storage_service",
    
    # Sync
    "OfflineSyncService",
    "SyncPrioritizationService",
    
    # Export
    "EngagementExportService",
    "engagement_export_service",
    "UniversalExportService",
    "universal_export_service",
    
    # Monitoring
    "EngagementMonitoringService",
    "engagement_monitoring_service",
    
    # Utilities
    "FallbackService",
    "fallback_service",
    "PromptEngineeringService",
    "QueryOptimizer",
    "get_query_optimizer",
    "ResponseProcessingService",
    "RetentionPolicyService"
]

# Module metadata
__version__ = "1.0.0"
__author__ = "MINT Development Team"
__description__ = "Services module for MINT API"
