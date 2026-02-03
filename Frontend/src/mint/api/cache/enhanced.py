"""
Enhanced Cache Service

Provides advanced caching capabilities with Redis backend, compression,
and intelligent cache management for improved performance.
"""

import json
import logging
import pickle
import time
import zlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Union, Callable
from functools import wraps
import hashlib
import asyncio

from .models import CacheStats, CacheConfig, CacheBackend, CacheHealthCheck
from .utils import (
    generate_cache_key, validate_cache_key, serialize_value, deserialize_value,
    estimate_memory_usage, format_cache_size, create_cache_key_info,
    calculate_hit_rate, format_percentage, measure_execution_time
)

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)

# CacheStats is now imported from models


class EnhancedCacheService:
    """
    Enhanced caching service with Redis backend, compression, and advanced features.
    Falls back to in-memory cache if Redis is not available.
    """
    
    def __init__(
        self,
        redis_url: Optional[str] = None,
        default_ttl: int = 3600,
        max_memory_size: int = 100 * 1024 * 1024,  # 100MB
        compression_threshold: int = 1024,  # Compress data larger than 1KB
        key_prefix: str = "mint_cache:",
        enable_stats: bool = True
    ):
        """
        Initialize the enhanced cache service.
        
        Args:
            redis_url: Redis connection URL
            default_ttl: Default TTL in seconds
            max_memory_size: Maximum memory size for in-memory cache
            compression_threshold: Minimum size to enable compression
            key_prefix: Prefix for all cache keys
            enable_stats: Whether to track cache statistics
        """
        self.default_ttl = default_ttl
        self.max_memory_size = max_memory_size
        self.compression_threshold = compression_threshold
        self.key_prefix = key_prefix
        self.enable_stats = enable_stats
        
        # Initialize statistics
        self.stats = CacheStats() if enable_stats else None
        
        # Initialize Redis connection
        self.redis_client = None
        if REDIS_AVAILABLE and redis_url:
            try:
                self.redis_client = redis.from_url(
                    redis_url,
                    decode_responses=False,  # We handle encoding ourselves
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                    health_check_interval=30
                )
                # Test connection
                self.redis_client.ping()
                logger.info("Redis cache backend initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Redis cache: {e}")
                self.redis_client = None
        
        # Fallback to in-memory cache
        if not self.redis_client:
            self._memory_cache = {}
            self._memory_usage = 0
            self._access_times = {}
            logger.info("Using in-memory cache backend")
            
    def _make_key(self, key: str) -> str:
        """Create a prefixed cache key."""
        return f"{self.key_prefix}{key}"
        
    def _serialize_value(self, value: Any) -> bytes:
        """Serialize and optionally compress a value."""
        try:
            # Serialize using pickle for better type support
            serialized = pickle.dumps(value)
            
            # Compress if above threshold
            if len(serialized) > self.compression_threshold:
                compressed = zlib.compress(serialized)
                # Only use compression if it actually reduces size
                if len(compressed) < len(serialized):
                    return b'compressed:' + compressed
                    
            return b'raw:' + serialized
            
        except Exception as e:
            logger.error(f"Error serializing value: {e}")
            raise
            
    def _deserialize_value(self, data: bytes) -> Any:
        """Deserialize and optionally decompress a value."""
        try:
            if data.startswith(b'compressed:'):
                # Decompress and deserialize
                compressed_data = data[11:]  # Remove 'compressed:' prefix
                decompressed = zlib.decompress(compressed_data)
                return pickle.loads(decompressed)
            elif data.startswith(b'raw:'):
                # Just deserialize
                raw_data = data[4:]  # Remove 'raw:' prefix
                return pickle.loads(raw_data)
            else:
                # Legacy format, assume raw pickle
                return pickle.loads(data)
                
        except Exception as e:
            logger.error(f"Error deserializing value: {e}")
            raise
            
    def _evict_lru_memory(self, needed_space: int):
        """Evict least recently used items from memory cache."""
        if not hasattr(self, '_memory_cache'):
            return
            
        # Sort by access time (oldest first)
        sorted_keys = sorted(
            self._access_times.keys(),
            key=lambda k: self._access_times[k]
        )
        
        freed_space = 0
        for key in sorted_keys:
            if freed_space >= needed_space:
                break
                
            if key in self._memory_cache:
                value_size = len(self._serialize_value(self._memory_cache[key]))
                del self._memory_cache[key]
                del self._access_times[key]
                self._memory_usage -= value_size
                freed_space += value_size
                
                if self.stats:
                    self.stats.evict()
                    
    async def get(self, key: str, default: Any = None) -> Any:
        """
        Get a value from cache.
        
        Args:
            key: Cache key
            default: Default value if key not found
            
        Returns:
            Cached value or default
        """
        cache_key = self._make_key(key)
        
        try:
            if self.redis_client:
                # Try Redis first
                data = self.redis_client.get(cache_key)
                if data is not None:
                    if self.stats:
                        self.stats.hit()
                    return self._deserialize_value(data)
            else:
                # Use memory cache
                if cache_key in self._memory_cache:
                    # Update access time
                    self._access_times[cache_key] = time.time()
                    if self.stats:
                        self.stats.hit()
                    return self._memory_cache[cache_key]
                    
            if self.stats:
                self.stats.miss()
            return default
            
        except Exception as e:
            logger.error(f"Error getting cache key {key}: {e}")
            if self.stats:
                self.stats.miss()
            return default
            
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        nx: bool = False
    ) -> bool:
        """
        Set a value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            nx: Only set if key doesn't exist
            
        Returns:
            True if set successfully, False otherwise
        """
        cache_key = self._make_key(key)
        ttl = ttl or self.default_ttl
        
        try:
            serialized_value = self._serialize_value(value)
            
            if self.redis_client:
                # Use Redis
                result = self.redis_client.set(
                    cache_key,
                    serialized_value,
                    ex=ttl,
                    nx=nx
                )
                success = result is not False
            else:
                # Use memory cache
                if nx and cache_key in self._memory_cache:
                    return False
                    
                # Check if we need to evict items
                value_size = len(serialized_value)
                if self._memory_usage + value_size > self.max_memory_size:
                    self._evict_lru_memory(value_size)
                    
                # Store in memory
                if cache_key in self._memory_cache:
                    # Update existing item
                    old_size = len(self._serialize_value(self._memory_cache[cache_key]))
                    self._memory_usage -= old_size
                    
                self._memory_cache[cache_key] = value
                self._access_times[cache_key] = time.time()
                self._memory_usage += value_size
                success = True
                
            if success and self.stats:
                self.stats.set()
                
            return success
            
        except Exception as e:
            logger.error(f"Error setting cache key {key}: {e}")
            return False
            
    async def delete(self, key: str) -> bool:
        """
        Delete a key from cache.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if deleted, False if key didn't exist
        """
        cache_key = self._make_key(key)
        
        try:
            if self.redis_client:
                result = self.redis_client.delete(cache_key)
                success = result > 0
            else:
                success = cache_key in self._memory_cache
                if success:
                    value_size = len(self._serialize_value(self._memory_cache[cache_key]))
                    del self._memory_cache[cache_key]
                    del self._access_times[cache_key]
                    self._memory_usage -= value_size
                    
            if success and self.stats:
                self.stats.delete()
                
            return success
            
        except Exception as e:
            logger.error(f"Error deleting cache key {key}: {e}")
            return False
            
    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in cache.
        
        Args:
            key: Cache key to check
            
        Returns:
            True if key exists, False otherwise
        """
        cache_key = self._make_key(key)
        
        try:
            if self.redis_client:
                return self.redis_client.exists(cache_key) > 0
            else:
                return cache_key in self._memory_cache
                
        except Exception as e:
            logger.error(f"Error checking cache key existence {key}: {e}")
            return False
            
    async def clear_pattern(self, pattern: str) -> int:
        """
        Clear all keys matching a pattern.
        
        Args:
            pattern: Pattern to match (supports * wildcards)
            
        Returns:
            Number of keys deleted
        """
        full_pattern = self._make_key(pattern)
        
        try:
            if self.redis_client:
                keys = self.redis_client.keys(full_pattern)
                if keys:
                    deleted = self.redis_client.delete(*keys)
                    if self.stats:
                        self.stats.deletes += deleted
                    return deleted
                return 0
            else:
                # Simple pattern matching for memory cache
                import fnmatch
                matching_keys = [
                    key for key in self._memory_cache.keys()
                    if fnmatch.fnmatch(key, full_pattern)
                ]
                
                for key in matching_keys:
                    value_size = len(self._serialize_value(self._memory_cache[key]))
                    del self._memory_cache[key]
                    del self._access_times[key]
                    self._memory_usage -= value_size
                    
                if self.stats:
                    self.stats.deletes += len(matching_keys)
                    
                return len(matching_keys)
                
        except Exception as e:
            logger.error(f"Error clearing cache pattern {pattern}: {e}")
            return 0
            
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        if not self.stats:
            return {"stats_disabled": True}
            
        base_stats = self.stats.to_dict()
        
        if self.redis_client:
            try:
                info = self.redis_client.info('memory')
                base_stats.update({
                    "backend": "redis",
                    "memory_used": info.get('used_memory', 0),
                    "memory_peak": info.get('used_memory_peak', 0),
                    "connected_clients": self.redis_client.info('clients').get('connected_clients', 0)
                })
            except Exception as e:
                logger.error(f"Error getting Redis stats: {e}")
                base_stats["backend"] = "redis (stats unavailable)"
        else:
            base_stats.update({
                "backend": "memory",
                "memory_used": self._memory_usage,
                "memory_limit": self.max_memory_size,
                "key_count": len(self._memory_cache)
            })
            
        return base_stats
        
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the cache service.
        
        Returns:
            Health check results
        """
        health = {
            "healthy": True,
            "backend": "redis" if self.redis_client else "memory",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            if self.redis_client:
                # Test Redis connection
                start_time = time.time()
                self.redis_client.ping()
                health["ping_time"] = time.time() - start_time
                health["redis_info"] = {
                    "version": self.redis_client.info().get('redis_version', 'unknown'),
                    "uptime": self.redis_client.info().get('uptime_in_seconds', 0)
                }
            else:
                # Test memory cache
                test_key = f"health_check_{int(time.time())}"
                await self.set(test_key, "test", ttl=1)
                test_value = await self.get(test_key)
                await self.delete(test_key)
                
                if test_value != "test":
                    health["healthy"] = False
                    health["error"] = "Memory cache test failed"
                    
        except Exception as e:
            health["healthy"] = False
            health["error"] = str(e)
            
        return health


def cache_result(
    ttl: int = 3600,
    key_func: Optional[Callable] = None,
    cache_service: Optional[EnhancedCacheService] = None
):
    """
    Decorator to cache function results.
    
    Args:
        ttl: Time to live in seconds
        key_func: Function to generate cache key from arguments
        cache_service: Cache service instance to use
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Use global cache service if none provided
            nonlocal cache_service
            if cache_service is None:
                cache_service = _global_cache_service
                
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default key generation
                key_parts = [func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = hashlib.md5(":".join(key_parts).encode()).hexdigest()
                
            # Try to get from cache
            cached_result = await cache_service.get(cache_key)
            if cached_result is not None:
                return cached_result
                
            # Execute function and cache result
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
                
            await cache_service.set(cache_key, result, ttl=ttl)
            return result
            
        return wrapper
    return decorator


# Global cache service instance
_global_cache_service = None


def get_cache_service() -> EnhancedCacheService:
    """Get the global cache service instance."""
    global _global_cache_service
    if _global_cache_service is None:
        _global_cache_service = EnhancedCacheService()
    return _global_cache_service


async def initialize_cache_service(
    redis_url: Optional[str] = None,
    **kwargs
) -> EnhancedCacheService:
    """
    Initialize the global cache service.
    
    Args:
        redis_url: Redis connection URL
        **kwargs: Additional arguments for EnhancedCacheService
        
    Returns:
        Initialized cache service
    """
    global _global_cache_service
    _global_cache_service = EnhancedCacheService(redis_url=redis_url, **kwargs)
    return _global_cache_service