#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Startup script for MINT API.

This module initializes services that need to be started when the application starts.
"""

import logging
import asyncio
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def initialize_services():
    """Initialize services that need to be started when the application starts."""
    logger.info("Initializing services...")
    
    # Initialize Redis cache service (primary distributed cache)
    await initialize_redis_cache_service()
    
    # Initialize enhanced cache service (legacy/fallback)
    await initialize_cache_service()
    
    # Initialize performance monitoring service
    initialize_performance_monitoring()
    
    # Credit system removed
    # await initialize_credit_background_processor()
    # await initialize_credit_reset_scheduler()
    
    logger.info("Services initialized successfully")

async def initialize_redis_cache_service():
    """Initialize the Redis cache service for distributed caching."""
    try:
        from ..cache.redis_service import init_cache_service
        
        logger.info("🔄 Initializing Redis cache service...")
        service = await init_cache_service()
        
        if service._using_fallback:
            logger.warning("⚠️ Redis cache service using in-memory fallback")
        else:
            logger.info("✅ Redis cache service connected to Azure Redis")
        
        # Log initial stats
        stats = await service.get_stats()
        logger.info(f"📊 Cache backend: {stats.get('backend', 'unknown')}")
        
    except Exception as e:
        logger.error(f"❌ Error initializing Redis cache service: {e}")
        logger.warning("⚠️ Application will continue without Redis caching")

async def initialize_cache_service():
    """Initialize the enhanced cache service."""
    try:
        from ..cache.enhanced import initialize_cache_service
        
        logger.info("Initializing enhanced cache service...")
        await initialize_cache_service()
        logger.info("Enhanced cache service initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing enhanced cache service: {e}")

def initialize_performance_monitoring():
    """Initialize the performance monitoring service."""
    try:
        from ..performance.monitoring import get_performance_monitoring_service
        
        logger.info("Initializing performance monitoring service...")
        perf_service = get_performance_monitoring_service()
        logger.info("Performance monitoring service initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing performance monitoring service: {e}")

# Credit system removed - all credit initialization functions removed

async def shutdown_services():
    """Shutdown services when the application stops."""
    logger.info("Shutting down services...")
    
    # Shutdown Redis cache service
    await shutdown_redis_cache_service()
    
    # Credit system removed
    # await shutdown_credit_background_processor()
    # await shutdown_credit_reset_scheduler()
    
    logger.info("Services shutdown completed")

async def shutdown_redis_cache_service():
    """Shutdown the Redis cache service gracefully."""
    try:
        from ..cache.redis_service import shutdown_cache_service
        
        logger.info("🔄 Shutting down Redis cache service...")
        await shutdown_cache_service()
        logger.info("✅ Redis cache service shut down gracefully")
        
    except Exception as e:
        logger.error(f"❌ Error shutting down Redis cache service: {e}")

def warm_up_cache():
    """Pre-warm the cache with frequently accessed data."""
    try:
        logger.info("Pre-warming cache...")
        
        # This function can be expanded to pre-warm specific cache entries
        # For example, loading common vector embeddings, etc.
        
        logger.info("Cache pre-warming completed")
    except Exception as e:
        logger.error(f"Error pre-warming cache: {e}")