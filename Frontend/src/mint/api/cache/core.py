"""
Cache service for admin dashboard data.
Provides caching mechanisms for frequently accessed admin data.
"""
import time
from typing import Any, Dict, Optional, Callable, TypeVar, Generic, List, Set
import logging
from functools import wraps
import asyncio
import json
import re
import threading

from .models import CacheItem, CacheStats, CacheConfig, CacheStrategy
from .utils import (
    generate_cache_key, validate_cache_key, serialize_value, deserialize_value,
    estimate_memory_usage, format_cache_size, create_cache_key_info
)

T = TypeVar('T')
logger = logging.getLogger(__name__)

# CacheItem is now imported from models


class AdminCache:
    """In-memory cache for admin dashboard data with advanced features."""
    
    def __init__(self, default_ttl: int = 300, max_size: int = 1000, cleanup_interval: int = 60):
        """
        Initialize the cache with configuration options.
        
        Args:
            default_ttl: Default time-to-live in seconds
            max_size: Maximum number of items in cache before eviction
            cleanup_interval: Interval in seconds for automatic cleanup
        """
        self._cache: Dict[str, CacheItem] = {}
        self._default_ttl = default_ttl
        self._max_size = max_size
        self._tag_index: Dict[str, Set[str]] = {}  # Maps tags to sets of keys
        self._lock = threading.RLock()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expirations": 0
        }
        
        # Start cleanup thread
        self._cleanup_interval = cleanup_interval
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache."""
        with self._lock:
            if key not in self._cache:
                self._stats["misses"] += 1
                return None
            
            item = self._cache[key]
            if item.is_expired():
                self._remove_item(key)
                self._stats["expirations"] += 1
                self._stats["misses"] += 1
                return None
            
            item.record_hit()
            self._stats["hits"] += 1
            return item.value
    
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None, tags: Optional[List[str]] = None) -> None:
        """
        Set a value in the cache with optional TTL and tags.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Time-to-live in seconds (uses default if None)
            tags: List of tags to associate with this cache item
        """
        with self._lock:
            # Check if we need to evict items
            if len(self._cache) >= self._max_size and key not in self._cache:
                self._evict_items()
            
            ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
            tag_set = set(tags) if tags else set()
            
            # Remove old item if it exists
            if key in self._cache:
                old_item = self._cache[key]
                for tag in old_item.tags:
                    if tag in self._tag_index:
                        self._tag_index[tag].discard(key)
            
            # Create new item
            self._cache[key] = CacheItem(value, ttl, tag_set)
            
            # Update tag index
            for tag in tag_set:
                if tag not in self._tag_index:
                    self._tag_index[tag] = set()
                self._tag_index[tag].add(key)
    
    def delete(self, key: str) -> None:
        """Delete a value from the cache."""
        with self._lock:
            self._remove_item(key)
    
    def _remove_item(self, key: str) -> None:
        """Internal method to remove an item and update indexes."""
        if key in self._cache:
            item = self._cache[key]
            # Remove from tag index
            for tag in item.tags:
                if tag in self._tag_index:
                    self._tag_index[tag].discard(key)
                    if not self._tag_index[tag]:
                        del self._tag_index[tag]
            # Remove from cache
            del self._cache[key]
    
    def clear(self) -> None:
        """Clear all values from the cache."""
        with self._lock:
            self._cache.clear()
            self._tag_index.clear()
    
    def clear_pattern(self, pattern: str) -> None:
        """Clear all values from the cache that match a pattern."""
        with self._lock:
            keys_to_delete = [k for k in self._cache.keys() if pattern in k]
            for key in keys_to_delete:
                self._remove_item(key)
    
    def clear_regex(self, pattern: str) -> int:
        """
        Clear all values from the cache that match a regex pattern.
        
        Args:
            pattern: Regular expression pattern
            
        Returns:
            Number of items cleared
        """
        with self._lock:
            regex = re.compile(pattern)
            keys_to_delete = [k for k in self._cache.keys() if regex.search(k)]
            for key in keys_to_delete:
                self._remove_item(key)
            return len(keys_to_delete)
    
    def clear_tag(self, tag: str) -> int:
        """
        Clear all values from the cache with a specific tag.
        
        Args:
            tag: Tag to match
            
        Returns:
            Number of items cleared
        """
        with self._lock:
            if tag not in self._tag_index:
                return 0
            
            keys_to_delete = list(self._tag_index[tag])
            for key in keys_to_delete:
                self._remove_item(key)
            return len(keys_to_delete)
    
    def _evict_items(self) -> None:
        """Evict least recently used items when cache is full."""
        if not self._cache:
            return
        
        # Find least recently accessed items
        items_to_evict = len(self._cache) // 10  # Evict 10% of items
        if items_to_evict < 1:
            items_to_evict = 1
        
        # Sort by last accessed time
        sorted_items = sorted(
            self._cache.items(),
            key=lambda x: x[1].last_accessed
        )
        
        # Evict oldest items
        for i in range(min(items_to_evict, len(sorted_items))):
            key, _ = sorted_items[i]
            self._remove_item(key)
            self._stats["evictions"] += 1
    
    def _cleanup_loop(self) -> None:
        """Background thread to clean up expired items."""
        while True:
            time.sleep(self._cleanup_interval)
            try:
                self._cleanup_expired()
            except Exception as e:
                logger.error(f"Error in cache cleanup: {str(e)}")
    
    def _cleanup_expired(self) -> None:
        """Remove all expired items from the cache."""
        with self._lock:
            now = time.time()
            expired_keys = [
                key for key, item in self._cache.items()
                if item.is_expired()
            ]
            for key in expired_keys:
                self._remove_item(key)
                self._stats["expirations"] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            stats = dict(self._stats)
            stats.update({
                "size": len(self._cache),
                "max_size": self._max_size,
                "tag_count": len(self._tag_index),
                "hit_ratio": self._calculate_hit_ratio()
            })
            return stats
    
    def _calculate_hit_ratio(self) -> float:
        """Calculate cache hit ratio."""
        total = self._stats["hits"] + self._stats["misses"]
        if total == 0:
            return 0.0
        return self._stats["hits"] / total


# Create a global cache instance
admin_cache = AdminCache(default_ttl=300, max_size=1000, cleanup_interval=60)


def cached(ttl_seconds: Optional[int] = None, key_prefix: str = "", tags: Optional[List[str]] = None):
    """
    Decorator to cache function results.
    
    Args:
        ttl_seconds: Time to live in seconds. If None, uses the default TTL.
        key_prefix: Prefix for the cache key.
        tags: List of tags to associate with this cache entry.
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Create a cache key from the function name and arguments
            cache_key = f"{key_prefix}:{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Try to get the result from the cache
            cached_result = admin_cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached_result
            
            # If not in cache, call the function
            logger.debug(f"Cache miss for {cache_key}")
            result = await func(*args, **kwargs)
            
            # Store the result in the cache
            admin_cache.set(cache_key, result, ttl_seconds, tags)
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Create a cache key from the function name and arguments
            cache_key = f"{key_prefix}:{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Try to get the result from the cache
            cached_result = admin_cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached_result
            
            # If not in cache, call the function
            logger.debug(f"Cache miss for {cache_key}")
            result = func(*args, **kwargs)
            
            # Store the result in the cache
            admin_cache.set(cache_key, result, ttl_seconds, tags)
            
            return result
        
        # Return the appropriate wrapper based on whether the function is async or not
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def invalidate_cache(key_pattern: str) -> int:
    """
    Invalidate cache entries matching a pattern.
    
    Args:
        key_pattern: Pattern to match cache keys.
        
    Returns:
        Number of items invalidated
    """
    return admin_cache.clear_pattern(key_pattern)


def invalidate_by_regex(pattern: str) -> int:
    """
    Invalidate cache entries matching a regex pattern.
    
    Args:
        pattern: Regular expression pattern
        
    Returns:
        Number of items invalidated
    """
    return admin_cache.clear_regex(pattern)


def invalidate_by_tag(tag: str) -> int:
    """
    Invalidate cache entries with a specific tag.
    
    Args:
        tag: Tag to match
        
    Returns:
        Number of items invalidated
    """
    return admin_cache.clear_tag(tag)


def get_cache_stats() -> Dict[str, Any]:
    """
    Get detailed statistics about the cache.
    
    Returns:
        Dictionary with cache statistics
    """
    return admin_cache.get_stats()


def warm_cache(func, *args, **kwargs) -> None:
    """
    Pre-warm the cache by executing a function and caching its result.
    
    Args:
        func: Function to execute
        *args: Positional arguments for the function
        **kwargs: Keyword arguments for the function
    """
    if asyncio.iscoroutinefunction(func):
        async def warm():
            await func(*args, **kwargs)
        asyncio.create_task(warm())
    else:
        func(*args, **kwargs)