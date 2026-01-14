"""RABA Redis Service.

Provides Redis client for caching operations.
"""

from typing import Any, Optional

import redis

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> redis.Redis:
    """
    Get or create Redis client instance.
    
    Returns:
        Redis client
        
    Raises:
        ValueError: If Redis URL not configured
    """
    global _redis_client
    
    if _redis_client is not None:
        return _redis_client
    
    if not settings.redis_url:
        logger.error("Redis URL not configured")
        raise ValueError("Redis URL must be configured")
    
    logger.info("Initializing Redis client...")
    _redis_client = redis.from_url(
        settings.redis_url,
        decode_responses=True,
    )
    
    try:
        _redis_client.ping()
        logger.info("Redis client connected successfully")
    except redis.ConnectionError as e:
        logger.error(f"Failed to connect to Redis: {e}")
        raise
    
    return _redis_client


class CacheService:
    """Service for cache operations."""
    
    PREFIX = "raba:"
    
    def __init__(self, client: Optional[redis.Redis] = None):
        """Initialize cache service."""
        self._client = client
        self._logger = get_logger(f"{__name__}.CacheService")
    
    @property
    def client(self) -> redis.Redis:
        """Get Redis client (lazy initialization)."""
        if self._client is None:
            self._client = get_redis_client()
        return self._client
    
    def _make_key(self, key: str) -> str:
        """Create prefixed cache key."""
        return f"{self.PREFIX}{key}"
    
    async def get(self, key: str) -> Optional[str]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        full_key = self._make_key(key)
        self._logger.debug(f"Cache GET: {full_key}")
        
        value = self.client.get(full_key)
        
        if value:
            self._logger.debug(f"Cache HIT: {full_key}")
        else:
            self._logger.debug(f"Cache MISS: {full_key}")
        
        return value
    
    async def set(self, key: str, value: str, ttl_seconds: Optional[int] = None) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Time-to-live in seconds
            
        Returns:
            True if successful
        """
        full_key = self._make_key(key)
        self._logger.debug(f"Cache SET: {full_key} (TTL: {ttl_seconds}s)")
        
        if ttl_seconds:
            return self.client.setex(full_key, ttl_seconds, value)
        return self.client.set(full_key, value)
    
    async def delete(self, key: str) -> bool:
        """
        Delete value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if deleted
        """
        full_key = self._make_key(key)
        self._logger.debug(f"Cache DELETE: {full_key}")
        return bool(self.client.delete(full_key))
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        full_key = self._make_key(key)
        return bool(self.client.exists(full_key))


def get_cache_service() -> CacheService:
    """Get CacheService instance."""
    return CacheService()
