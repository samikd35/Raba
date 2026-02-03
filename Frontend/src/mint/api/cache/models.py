#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Cache Models and Data Structures.

This module contains Pydantic models and data structures for cache functionality,
including cache items, statistics, configurations, and strategies.
"""

from enum import Enum
from typing import Dict, Any, Optional, List, Set, Union, Generic, TypeVar
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field
from dataclasses import dataclass, field
import time

T = TypeVar('T')


class CacheStrategy(str, Enum):
    """Cache strategy types."""
    AGGRESSIVE = "aggressive"  # Cache everything for maximum performance
    BALANCED = "balanced"     # Cache frequently accessed items
    CONSERVATIVE = "conservative"  # Cache only critical items


class CacheBackend(str, Enum):
    """Cache backend types."""
    MEMORY = "memory"
    REDIS = "redis"
    HYBRID = "hybrid"


class CacheItemStatus(str, Enum):
    """Cache item status."""
    ACTIVE = "active"
    EXPIRED = "expired"
    EVICTED = "evicted"
    INVALIDATED = "invalidated"


@dataclass
class CacheItem(Generic[T]):
    """Cache item with expiration time and metadata."""
    value: T
    ttl_seconds: int
    tags: Optional[Set[str]] = None
    hit_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    created_at: float = field(default_factory=time.time)
    size_bytes: int = 0
    
    def is_expired(self) -> bool:
        """Check if the cache item is expired."""
        return time.time() > (self.created_at + self.ttl_seconds)
    
    def record_hit(self) -> None:
        """Record a cache hit."""
        self.hit_count += 1
        self.last_accessed = time.time()


class CacheStats(BaseModel):
    """Cache statistics tracking."""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    evictions: int = 0
    expirations: int = 0
    start_time: float = Field(default_factory=time.time)
    
    @property
    def hit_rate(self) -> float:
        """Calculate hit rate percentage."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
    
    @property
    def uptime(self) -> float:
        """Calculate uptime in seconds."""
        return time.time() - self.start_time
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "sets": self.sets,
            "deletes": self.deletes,
            "evictions": self.evictions,
            "expirations": self.expirations,
            "hit_rate": self.hit_rate,
            "uptime": self.uptime
        }


class CacheEntry(BaseModel):
    """Cache entry metadata."""
    key: str
    size_bytes: int
    created_at: datetime
    last_accessed: datetime
    access_count: int
    ttl_seconds: int
    strategy: CacheStrategy
    status: CacheItemStatus = CacheItemStatus.ACTIVE


class CacheMetrics(BaseModel):
    """Cache performance metrics."""
    total_entries: int = 0
    total_size_bytes: int = 0
    hit_rate: float = 0.0
    miss_rate: float = 0.0
    avg_response_time_ms: float = 0.0
    memory_usage_percent: float = 0.0
    eviction_rate: float = 0.0
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CacheConfig(BaseModel):
    """Cache configuration."""
    default_ttl: int = 3600
    max_size: int = 1000
    max_memory_size: int = 100 * 1024 * 1024  # 100MB
    cleanup_interval: int = 60
    compression_threshold: int = 1024
    key_prefix: str = "mint_cache:"
    enable_stats: bool = True
    enable_compression: bool = True
    backend: CacheBackend = CacheBackend.MEMORY
    redis_url: Optional[str] = None


class CacheStrategyConfig(BaseModel):
    """Configuration for cache strategies."""
    strategy: CacheStrategy
    ttl_multiplier: float = 1.0
    priority: int = 0
    max_size: Optional[int] = None
    tags: List[str] = Field(default_factory=list)


class CacheInvalidationRequest(BaseModel):
    """Request for cache invalidation."""
    keys: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    pattern: Optional[str] = None
    all: bool = False


class CacheWarmingRequest(BaseModel):
    """Request for cache warming."""
    keys: List[str]
    strategy: CacheStrategy = CacheStrategy.BALANCED
    priority: int = 0
    ttl_seconds: Optional[int] = None


class CacheHealthCheck(BaseModel):
    """Cache health check result."""
    healthy: bool
    backend_status: Dict[str, Any] = Field(default_factory=dict)
    stats: CacheStats
    metrics: CacheMetrics
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CacheKeyInfo(BaseModel):
    """Information about a cache key."""
    key: str
    exists: bool
    ttl_seconds: Optional[int] = None
    size_bytes: int = 0
    hit_count: int = 0
    last_accessed: Optional[datetime] = None
    created_at: Optional[datetime] = None
    tags: List[str] = Field(default_factory=list)


class CacheTagInfo(BaseModel):
    """Information about cache tags."""
    tag: str
    key_count: int
    total_size_bytes: int
    avg_ttl_seconds: float
    last_accessed: Optional[datetime] = None


class CacheCompressionInfo(BaseModel):
    """Information about cache compression."""
    original_size: int
    compressed_size: int
    compression_ratio: float
    algorithm: str = "zlib"
    compressed: bool = False


class CacheEvictionInfo(BaseModel):
    """Information about cache eviction."""
    evicted_keys: List[str]
    reason: str
    strategy: CacheStrategy
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    memory_freed_bytes: int = 0


class CachePerformanceReport(BaseModel):
    """Comprehensive cache performance report."""
    period_start: datetime
    period_end: datetime
    total_requests: int
    hit_rate: float
    miss_rate: float
    avg_response_time_ms: float
    memory_usage: Dict[str, Any] = Field(default_factory=dict)
    top_keys: List[CacheKeyInfo] = Field(default_factory=list)
    top_tags: List[CacheTagInfo] = Field(default_factory=list)
    eviction_summary: Dict[str, int] = Field(default_factory=dict)
    error_summary: Dict[str, int] = Field(default_factory=dict)


class CacheOperationResult(BaseModel):
    """Result of a cache operation."""
    success: bool
    key: str
    operation: str
    execution_time_ms: float
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CacheBatchOperation(BaseModel):
    """Batch cache operation."""
    operation: str  # get, set, delete, invalidate
    keys: List[str]
    values: Optional[List[Any]] = None
    ttl_seconds: Optional[int] = None
    tags: Optional[List[str]] = None


class CacheBatchResult(BaseModel):
    """Result of a batch cache operation."""
    operation: str
    total_keys: int
    successful_keys: int
    failed_keys: int
    execution_time_ms: float
    results: List[CacheOperationResult] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


# Constants for cache operations
DEFAULT_TTL_SECONDS = 3600
DEFAULT_MAX_SIZE = 1000
DEFAULT_CLEANUP_INTERVAL = 60
DEFAULT_COMPRESSION_THRESHOLD = 1024
DEFAULT_KEY_PREFIX = "mint_cache:"

# Cache strategy configurations
CACHE_STRATEGY_CONFIGS = {
    CacheStrategy.AGGRESSIVE: CacheStrategyConfig(
        strategy=CacheStrategy.AGGRESSIVE,
        ttl_multiplier=2.0,
        priority=3,
        max_size=None
    ),
    CacheStrategy.BALANCED: CacheStrategyConfig(
        strategy=CacheStrategy.BALANCED,
        ttl_multiplier=1.0,
        priority=2,
        max_size=500
    ),
    CacheStrategy.CONSERVATIVE: CacheStrategyConfig(
        strategy=CacheStrategy.CONSERVATIVE,
        ttl_multiplier=0.5,
        priority=1,
        max_size=100
    )
}

# Cache error codes
CACHE_ERROR_CODES = {
    "KEY_NOT_FOUND": "Cache key not found",
    "TTL_EXPIRED": "Cache item has expired",
    "MEMORY_LIMIT_EXCEEDED": "Memory limit exceeded",
    "REDIS_CONNECTION_FAILED": "Redis connection failed",
    "SERIALIZATION_ERROR": "Data serialization failed",
    "DESERIALIZATION_ERROR": "Data deserialization failed",
    "COMPRESSION_ERROR": "Data compression failed",
    "DECOMPRESSION_ERROR": "Data decompression failed",
    "INVALID_KEY": "Invalid cache key format",
    "INVALID_TTL": "Invalid TTL value",
    "CACHE_FULL": "Cache is full",
    "BACKEND_UNAVAILABLE": "Cache backend unavailable"
}

# Cache operation types
CACHE_OPERATIONS = {
    "GET": "Retrieve value from cache",
    "SET": "Store value in cache",
    "DELETE": "Remove value from cache",
    "INVALIDATE": "Invalidate cache entries",
    "CLEAR": "Clear all cache entries",
    "STATS": "Get cache statistics",
    "HEALTH": "Check cache health"
}

# Cache compression algorithms
COMPRESSION_ALGORITHMS = {
    "zlib": "Standard zlib compression",
    "gzip": "Gzip compression",
    "lz4": "LZ4 fast compression",
    "brotli": "Brotli compression"
}

# Cache eviction policies
EVICTION_POLICIES = {
    "LRU": "Least Recently Used",
    "LFU": "Least Frequently Used",
    "TTL": "Time To Live",
    "RANDOM": "Random eviction",
    "SIZE": "Size-based eviction"
}


