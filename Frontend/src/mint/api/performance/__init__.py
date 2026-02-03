"""
Performance Management Module

This module provides performance monitoring and optimization functionality for the MINT system,
including performance metrics, monitoring, and optimization services.

Components:
- endpoints: Performance API endpoints
- monitoring: Performance monitoring service
- optimizer: Performance optimization service
"""

from .endpoints import router as performance_router
from .monitoring import PerformanceMonitoringService, get_performance_monitoring_service
from .optimizer import PerformanceOptimizer, get_performance_optimizer

# Public API
__all__ = [
    # Endpoints
    "performance_router",
    
    # Monitoring
    "PerformanceMonitoringService",
    "get_performance_monitoring_service",
    
    # Optimization
    "PerformanceOptimizer",
    "get_performance_optimizer"
]

# Module metadata
__version__ = "1.0.0"
__author__ = "MINT Development Team"
__description__ = "Performance management module for MINT API"
