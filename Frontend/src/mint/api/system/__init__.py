"""
System Management Module

This module provides system-level functionality for the MINT system,
including system metrics, integration validation, migration, and startup.

Components:
- metrics: System metrics service
- integration: Integration validation
- migration: Migration endpoints
- startup: System startup
- types: System type definitions
"""

from .monitoring import SystemMetricsService, metrics_service
from .integration.integration_validator import IntegrationValidator, get_integration_validator
from .init import initialize_services, shutdown_services
from .core.types import *

# Note: migration_router is NOT imported here to avoid circular dependency with auth_v2
# Import directly from .endpoints.migration_endpoints if needed

# Public API
__all__ = [
    # Metrics
    "SystemMetricsService",
    "metrics_service",
    
    # Integration
    "IntegrationValidator",
    "get_integration_validator",
    
    # Startup
    "initialize_services",
    "shutdown_services",
    
    # Types
    "SystemStatus",
    "IntegrationStatus",
    "MigrationStatus"
]

# Module metadata
__version__ = "1.0.0"
__author__ = "MINT Development Team"
__description__ = "System management module for MINT API"
