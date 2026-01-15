"""RABA Redis Service.

Provides Redis client for caching operations.
Supports cloud Redis (Redis Labs) with connection pooling.

Reference: RABA_Architecture.md Section 9 - Caching Strategy
Phase 4.3 Implementation
"""

import json
from datetime import datetime
from typing import Any, Optional, Union

import redis
from redis import ConnectionPool

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

_connection_pool: Optional[ConnectionPool] = None

_redis_client: Optional[redis.Redis] = None


def get_connection_pool() -> ConnectionPool:
    """
    Get or create Redis connection pool.
    
    Uses connection pooling for better performance with cloud Redis.
    """
    global _connection_pool
    
    if _connection_pool is None:
        if not settings.redis_url:
            raise ValueError("Redis URL must be configured")
        
        logger.info("Creating Redis connection pool...")
        _connection_pool = ConnectionPool.from_url(
            settings.redis_url,
            decode_responses=True,
            max_connections=20,
            socket_timeout=5.0,
            socket_connect_timeout=5.0,
            retry_on_timeout=True,
        )
    
    return _connection_pool


def get_redis_client() -> redis.Redis:
    """
    Get or create Redis client instance with connection pooling.
    
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
    
    logger.info("Initializing Redis client with connection pool...")
    pool = get_connection_pool()
    _redis_client = redis.Redis(connection_pool=pool)
    
    try:
        _redis_client.ping()
        logger.info("Redis client connected successfully")
    except (redis.ConnectionError, redis.AuthenticationError) as e:
        logger.warning(f"Redis connection failed (caching disabled): {e}")
        # Return client anyway - it will fail gracefully on each operation
        # This allows the application to continue without caching
    
    return _redis_client


def check_redis_health() -> dict:
    """
    Check Redis connection health.
    
    Returns:
        Dict with status and info
    """
    try:
        client = get_redis_client()
        info = client.info("server")
        return {
            "status": "healthy",
            "redis_version": info.get("redis_version"),
            "connected_clients": info.get("connected_clients"),
            "used_memory_human": info.get("used_memory_human"),
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }


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


class RedisService:
    """
    Enhanced Redis service with JSON support for caching.
    
    Features:
    - JSON serialization/deserialization
    - Graceful fallback when Redis unavailable
    - TTL management
    - Pattern-based key operations
    
    Reference: RABA_Architecture.md Section 9 - Caching Strategy
    """
    
    PREFIX = "raba:"
    
    def __init__(self):
        self._client: Optional[redis.Redis] = None
        self._logger = get_logger(f"{__name__}.RedisService")
        self._available: Optional[bool] = None  # Cache availability status
    
    @property
    def client(self) -> Optional[redis.Redis]:
        """Get Redis client (lazy initialization)."""
        if self._client is None:
            if not settings.redis_url:
                self._logger.warning("Redis URL not configured")
                return None
            try:
                self._client = get_redis_client()
            except Exception as e:
                self._logger.warning(f"Redis connection failed: {e}")
                return None
        return self._client
    
    def _make_key(self, key: str) -> str:
        """Create prefixed cache key."""
        return f"{self.PREFIX}{key}"
    
    async def get(self, key: str) -> Optional[dict]:
        """
        Get JSON value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Deserialized dict or None
        """
        if not self.client:
            return None
        
        full_key = self._make_key(key)
        self._logger.debug(f"Cache GET: {full_key}")
        
        try:
            value = self.client.get(full_key)
            if value:
                self._logger.debug(f"Cache HIT: {full_key}")
                return json.loads(value)
            self._logger.debug(f"Cache MISS: {full_key}")
            return None
        except Exception as e:
            self._logger.warning(f"Cache GET failed: {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: dict,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Set JSON value in cache.
        
        Args:
            key: Cache key
            value: Dict to cache (will be JSON serialized)
            ttl: Time-to-live in seconds
            
        Returns:
            True if successful
        """
        if not self.client:
            return False
        
        full_key = self._make_key(key)
        self._logger.debug(f"Cache SET: {full_key} (TTL: {ttl}s)")
        
        try:
            json_value = json.dumps(value, default=str)
            if ttl:
                self.client.setex(full_key, ttl, json_value)
            else:
                self.client.set(full_key, json_value)
            return True
        except Exception as e:
            self._logger.warning(f"Cache SET failed: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        if not self.client:
            return False
        
        full_key = self._make_key(key)
        try:
            return bool(self.client.delete(full_key))
        except Exception as e:
            self._logger.warning(f"Cache DELETE failed: {e}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.
        
        Used for cache invalidation (e.g., invalidate all scripts for a research).
        
        Args:
            pattern: Key pattern (e.g., "script:abc123:*")
            
        Returns:
            Number of keys deleted
        """
        if not self.client:
            return 0
        
        full_pattern = self._make_key(pattern)
        try:
            keys = self.client.keys(full_pattern)
            if keys:
                deleted = self.client.delete(*keys)
                self._logger.info(f"Deleted {deleted} keys matching {full_pattern}")
                return deleted
            return 0
        except Exception as e:
            self._logger.warning(f"Cache DELETE_PATTERN failed: {e}")
            return 0
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        if not self.client:
            return False
        
        full_key = self._make_key(key)
        try:
            return bool(self.client.exists(full_key))
        except Exception as e:
            self._logger.warning(f"Cache EXISTS failed: {e}")
            return False
    
    async def get_ttl(self, key: str) -> int:
        """
        Get remaining TTL for a key.
        
        Args:
            key: Cache key
            
        Returns:
            TTL in seconds, -1 if no TTL, -2 if key doesn't exist
        """
        if not self.client:
            return -2
        
        full_key = self._make_key(key)
        try:
            return self.client.ttl(full_key)
        except Exception as e:
            self._logger.warning(f"Cache TTL failed: {e}")
            return -2
    
    def is_available(self) -> bool:
        """
        Check if Redis is available.
        
        Caches the result to avoid repeated connection attempts.
        """
        if self._available is not None:
            return self._available
        
        try:
            if self.client:
                self.client.ping()
                self._available = True
            else:
                self._available = False
        except Exception:
            self._available = False
        
        return self._available
    
    async def get_with_metadata(self, key: str) -> Optional[dict]:
        """
        Get value with cache metadata (TTL, hit info).
        
        Returns:
            Dict with 'data', 'ttl', 'cached_at' if found, None otherwise
        """
        if not self.client:
            return None
        
        full_key = self._make_key(key)
        try:
            pipe = self.client.pipeline()
            pipe.get(full_key)
            pipe.ttl(full_key)
            results = pipe.execute()
            
            value, ttl = results
            if value:
                data = json.loads(value)
                return {
                    "data": data,
                    "ttl_remaining": ttl,
                    "cache_hit": True,
                }
            return None
        except Exception as e:
            self._logger.warning(f"Cache GET_WITH_METADATA failed: {e}")
            return None


_redis_service: Optional[RedisService] = None


def get_redis_service() -> RedisService:
    """Get singleton RedisService instance."""
    global _redis_service
    if _redis_service is None:
        _redis_service = RedisService()
    return _redis_service


def get_cache_service() -> CacheService:
    """Get CacheService instance."""
    return CacheService()
