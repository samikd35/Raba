#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Cache Module for MINT.

This module provides comprehensive caching functionality for the MINT system,
including in-memory caching, Redis backend, compression, and intelligent cache management.

Module Structure:
- models: Pydantic models and data structures
- core: Basic in-memory cache implementation
- enhanced: Advanced cache with Redis backend and compression
- report: Specialized cache for report history functionality
- utils: Utility functions and helpers
"""

from .models import (
    # Enums
    CacheStrategy, CacheBackend, CacheItemStatus,
    
    # Core Models
    CacheItem, CacheStats, CacheConfig, CacheEntry, CacheMetrics,
    CacheStrategyConfig, CacheInvalidationRequest, CacheWarmingRequest,
    CacheHealthCheck, CacheKeyInfo, CacheTagInfo, CacheCompressionInfo,
    CacheEvictionInfo, CachePerformanceReport, CacheOperationResult,
    CacheBatchOperation, CacheBatchResult,
    
    # Constants
    DEFAULT_TTL_SECONDS, DEFAULT_MAX_SIZE, DEFAULT_CLEANUP_INTERVAL,
    DEFAULT_COMPRESSION_THRESHOLD, DEFAULT_KEY_PREFIX,
    CACHE_STRATEGY_CONFIGS, CACHE_ERROR_CODES, CACHE_OPERATIONS,
    COMPRESSION_ALGORITHMS, EVICTION_POLICIES
)
from .core import AdminCache
from .enhanced import EnhancedCacheService, get_cache_service
from .report import ReportCacheManager, get_report_cache_manager
from .entity_cache_service import (
    EntityType,
    EntityCacheService,
    ENTITY_TTL_CONFIG,
    get_entity_ttl,
    get_entity_cache_service,
    init_entity_cache_service,
    shutdown_entity_cache_service,
)
from .decorators import (
    cached_query,
    cache_result,
    build_query_cache_key,
    get_query_cache_pattern,
)
from .invalidation_service import (
    CacheInvalidationService,
    WriteOperation,
    WORKFLOW_DEPENDENCIES,
    TABLE_TO_QUERY_CACHE_MAP,
    TABLE_TO_ENTITY_TYPE_MAP,
    get_invalidation_service,
    init_invalidation_service,
    shutdown_invalidation_service,
)
from .embedding_cache_service import (
    EmbeddingCacheService,
    EMBEDDING_TTL,
    MAX_TEXT_LENGTH,
    get_embedding_cache_service,
    init_embedding_cache_service,
    shutdown_embedding_cache_service,
)
from .auth_cache_service import (
    AuthCacheService,
    USER_CONTEXT_TTL,
    SESSION_TTL,
    get_auth_cache_service,
    init_auth_cache_service,
)
from .vector_search_cache_service import (
    VectorSearchCacheService,
    VECTOR_SEARCH_TTL,
    get_vector_search_cache_service,
    init_vector_search_cache_service,
    shutdown_vector_search_cache_service,
)
from .search_provider_cache_service import (
    SearchProviderCacheService,
    SearchType,
    SEARCH_TTL_CONFIG,
    get_search_provider_cache_service,
    init_search_provider_cache_service,
    shutdown_search_provider_cache_service,
)
from .utils import (
    # Key and Validation Functions
    generate_cache_key, generate_key_hash, validate_cache_key,
    validate_ttl, validate_cache_tags,
    
    # Serialization Functions
    serialize_value, deserialize_value, calculate_compression_ratio,
    
    # Memory and Size Functions
    estimate_memory_usage, format_cache_size, format_duration,
    
    # Information Creation Functions
    create_cache_key_info, create_cache_tag_info, create_compression_info,
    create_eviction_info, create_operation_result, create_batch_result,
    
    # Calculation Functions
    calculate_hit_rate, calculate_miss_rate, format_percentage,
    
    # Utility Functions
    create_error_message, measure_execution_time, get_cache_strategy_config,
    format_cache_stats
)

# Convenience functions for common operations
from .core import cached, invalidate_by_tag

__all__ = [
    # Enums
    "CacheStrategy",
    "CacheBackend",
    "CacheItemStatus",
    
    # Core Models
    "CacheItem",
    "CacheStats",
    "CacheConfig",
    "CacheEntry",
    "CacheMetrics",
    "CacheStrategyConfig",
    "CacheInvalidationRequest",
    "CacheWarmingRequest",
    "CacheHealthCheck",
    "CacheKeyInfo",
    "CacheTagInfo",
    "CacheCompressionInfo",
    "CacheEvictionInfo",
    "CachePerformanceReport",
    "CacheOperationResult",
    "CacheBatchOperation",
    "CacheBatchResult",
    
    # Constants
    "DEFAULT_TTL_SECONDS",
    "DEFAULT_MAX_SIZE",
    "DEFAULT_CLEANUP_INTERVAL",
    "DEFAULT_COMPRESSION_THRESHOLD",
    "DEFAULT_KEY_PREFIX",
    "CACHE_STRATEGY_CONFIGS",
    "CACHE_ERROR_CODES",
    "CACHE_OPERATIONS",
    "COMPRESSION_ALGORITHMS",
    "EVICTION_POLICIES",
    
    # Main Classes
    "AdminCache",
    "EnhancedCacheService",
    "ReportCacheManager",
    "EntityCacheService",
    
    # Entity Cache
    "EntityType",
    "ENTITY_TTL_CONFIG",
    "get_entity_ttl",
    "get_entity_cache_service",
    "init_entity_cache_service",
    "shutdown_entity_cache_service",
    
    # Query Cache Decorators
    "cached_query",
    "cache_result",
    "build_query_cache_key",
    "get_query_cache_pattern",
    
    # Cache Invalidation Service
    "CacheInvalidationService",
    "WriteOperation",
    "WORKFLOW_DEPENDENCIES",
    "TABLE_TO_QUERY_CACHE_MAP",
    "TABLE_TO_ENTITY_TYPE_MAP",
    "get_invalidation_service",
    "init_invalidation_service",
    "shutdown_invalidation_service",
    
    # Embedding Cache Service
    "EmbeddingCacheService",
    "EMBEDDING_TTL",
    "MAX_TEXT_LENGTH",
    "get_embedding_cache_service",
    "init_embedding_cache_service",
    "shutdown_embedding_cache_service",
    
    # Auth Cache Service
    "AuthCacheService",
    "USER_CONTEXT_TTL",
    "SESSION_TTL",
    "get_auth_cache_service",
    "init_auth_cache_service",
    
    # Vector Search Cache Service
    "VectorSearchCacheService",
    "VECTOR_SEARCH_TTL",
    "get_vector_search_cache_service",
    "init_vector_search_cache_service",
    "shutdown_vector_search_cache_service",
    
    # Search Provider Cache Service
    "SearchProviderCacheService",
    "SearchType",
    "SEARCH_TTL_CONFIG",
    "get_search_provider_cache_service",
    "init_search_provider_cache_service",
    "shutdown_search_provider_cache_service",
    
    # Key and Validation Functions
    "generate_cache_key",
    "generate_key_hash",
    "validate_cache_key",
    "validate_ttl",
    "validate_cache_tags",
    
    # Serialization Functions
    "serialize_value",
    "deserialize_value",
    "calculate_compression_ratio",
    
    # Memory and Size Functions
    "estimate_memory_usage",
    "format_cache_size",
    "format_duration",
    
    # Information Creation Functions
    "create_cache_key_info",
    "create_cache_tag_info",
    "create_compression_info",
    "create_eviction_info",
    "create_operation_result",
    "create_batch_result",
    
    # Calculation Functions
    "calculate_hit_rate",
    "calculate_miss_rate",
    "format_percentage",
    
    # Utility Functions
    "create_error_message",
    "measure_execution_time",
    "get_cache_strategy_config",
    "format_cache_stats",
    
    # Convenience Functions
    "get_cache_service",
    "get_report_cache_manager",
    "cached",
    "invalidate_by_tag"
]
