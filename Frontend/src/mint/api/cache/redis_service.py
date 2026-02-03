"""
Redis Cache Service for Yuba Backend.

Provides centralized Redis caching with Azure Redis SSL support,
in-memory fallback, and cache stampede prevention.

This service implements:
- Azure Cache for Redis connection with SSL on port 6380
- Automatic in-memory fallback when Redis is unavailable
- LRU eviction for memory cache
- Distributed locks for cache stampede prevention
- Health monitoring and statistics
"""

import asyncio
import hashlib
import json
import logging
import os
import time
from collections import OrderedDict
from typing import Any, Callable, Dict, Optional, TypeVar

logger = logging.getLogger(__name__)

# Try to import redis, but allow fallback if not available
try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("redis package not available, will use in-memory cache only")

T = TypeVar('T')


class LRUCache:
    """
    Thread-safe LRU cache with memory limit for in-memory fallback.
    
    Implements Least Recently Used eviction policy with configurable
    maximum memory usage to prevent OOM errors.
    """
    
    def __init__(self, max_memory_mb: int = 100):
        """
        Initialize LRU cache with memory limit.
        
        Args:
            max_memory_mb: Maximum memory usage in megabytes
        """
        self._cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._max_memory_bytes = max_memory_mb * 1024 * 1024
        self._current_memory = 0
        self._lock = asyncio.Lock()
    
    def _estimate_size(self, value: Any) -> int:
        """Estimate memory size of a value in bytes."""
        try:
            serialized = json.dumps(value)
            return len(serialized.encode('utf-8'))
        except (TypeError, ValueError):
            # Fallback for non-JSON-serializable objects
            return len(str(value).encode('utf-8'))
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache, moving it to end (most recently used)."""
        async with self._lock:
            if key not in self._cache:
                return None
            
            value, expiry = self._cache[key]
            
            # Check if expired
            if expiry > 0 and time.time() > expiry:
                del self._cache[key]
                self._current_memory -= self._estimate_size(value)
                return None
            
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            return value
    
    async def set(self, key: str, value: Any, ttl: int = 0) -> bool:
        """Set value in cache with optional TTL."""
        async with self._lock:
            value_size = self._estimate_size(value)
            
            # Remove old value if exists
            if key in self._cache:
                old_value, _ = self._cache[key]
                self._current_memory -= self._estimate_size(old_value)
                del self._cache[key]
            
            # Evict items if needed
            while self._current_memory + value_size > self._max_memory_bytes and self._cache:
                # Remove least recently used (first item)
                oldest_key, (oldest_value, _) = self._cache.popitem(last=False)
                self._current_memory -= self._estimate_size(oldest_value)
                logger.debug(f"LRU eviction: removed key {oldest_key}")
            
            # Calculate expiry time (0 means no expiration)
            expiry = time.time() + ttl if ttl > 0 else 0
            
            # Add new value
            self._cache[key] = (value, expiry)
            self._current_memory += value_size
            return True
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        async with self._lock:
            if key in self._cache:
                value, _ = self._cache[key]
                self._current_memory -= self._estimate_size(value)
                del self._cache[key]
                return True
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists and is not expired."""
        async with self._lock:
            if key not in self._cache:
                return False
            
            _, expiry = self._cache[key]
            if expiry > 0 and time.time() > expiry:
                return False
            return True
    
    async def clear(self) -> None:
        """Clear all items from cache."""
        async with self._lock:
            self._cache.clear()
            self._current_memory = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "key_count": len(self._cache),
            "memory_used_bytes": self._current_memory,
            "memory_limit_bytes": self._max_memory_bytes,
            "memory_used_mb": round(self._current_memory / (1024 * 1024), 2),
            "memory_limit_mb": self._max_memory_bytes // (1024 * 1024),
        }


class ConnectionState:
    """Enum-like class for connection states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FALLBACK = "fallback"


class RedisCacheService:
    """
    Core Redis cache service with Azure Redis support.
    
    Provides connection management, serialization, and automatic
    fallback to in-memory cache when Redis is unavailable.
    Includes automatic reconnection when Redis becomes available again.
    """
    
    # Retry configuration for exponential backoff
    MAX_RETRIES = 3
    BASE_RETRY_DELAY = 0.5  # seconds
    MAX_RETRY_DELAY = 5.0  # seconds
    
    # Lock configuration for stampede prevention
    LOCK_TIMEOUT = 5  # seconds
    LOCK_RETRY_DELAY = 0.1  # seconds
    LOCK_MAX_RETRIES = 50  # 5 seconds total wait time
    
    # Reconnection configuration
    RECONNECT_INTERVAL = 30  # seconds between reconnection attempts
    RECONNECT_MAX_BACKOFF = 300  # maximum backoff interval (5 minutes)
    
    def __init__(
        self,
        redis_host: Optional[str] = None,
        redis_port: int = 6380,
        redis_password: Optional[str] = None,
        redis_ssl: bool = True,
        default_ttl: int = 300,
        key_prefix: str = "yuba:",
        max_memory_mb: int = 100,
        auto_reconnect: bool = True,
        reconnect_interval: int = None
    ):
        """
        Initialize Redis connection with Azure configuration.
        
        Args:
            redis_host: Redis host (defaults to REDIS_HOST env var)
            redis_port: Redis port (defaults to 6380 for Azure SSL)
            redis_password: Redis password (defaults to REDIS_PASSWORD env var)
            redis_ssl: Whether to use SSL (required for Azure Redis)
            default_ttl: Default TTL in seconds
            key_prefix: Prefix for all cache keys
            max_memory_mb: Maximum memory for in-memory fallback cache
            auto_reconnect: Whether to automatically attempt reconnection
            reconnect_interval: Interval between reconnection attempts in seconds
        """
        self.redis_host = redis_host or os.getenv("REDIS_HOST")
        self.redis_port = redis_port or int(os.getenv("REDIS_PORT", "6380"))
        self.redis_password = redis_password or os.getenv("REDIS_PASSWORD")
        self.redis_ssl = redis_ssl if redis_ssl is not None else os.getenv("REDIS_SSL", "true").lower() == "true"
        self.default_ttl = default_ttl
        self.key_prefix = key_prefix
        self.max_memory_mb = max_memory_mb
        self.auto_reconnect = auto_reconnect
        self.reconnect_interval = reconnect_interval or self.RECONNECT_INTERVAL
        
        # Redis client (initialized on connect)
        self._redis: Optional[aioredis.Redis] = None
        self._connected = False
        self._using_fallback = False
        
        # Connection state tracking
        self._connection_state = ConnectionState.DISCONNECTED
        self._last_state_change = time.time()
        self._reconnect_attempts = 0
        self._reconnect_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event() if asyncio.get_event_loop().is_running() else None
        
        # In-memory fallback cache
        self._memory_cache = LRUCache(max_memory_mb=max_memory_mb)
        
        # Statistics tracking
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "errors": 0,
            "fallback_activations": 0,
            "reconnect_attempts": 0,
            "successful_reconnects": 0,
        }
    
    def _log_state_change(self, old_state: str, new_state: str, reason: str = "") -> None:
        """Log connection state changes with context."""
        self._last_state_change = time.time()
        reason_str = f" - {reason}" if reason else ""
        
        if new_state == ConnectionState.CONNECTED:
            logger.info(f"🔗 Redis connection state: {old_state} → {new_state}{reason_str}")
        elif new_state == ConnectionState.FALLBACK:
            logger.warning(f"⚠️ Redis connection state: {old_state} → {new_state}{reason_str}")
        elif new_state == ConnectionState.RECONNECTING:
            logger.info(f"🔄 Redis connection state: {old_state} → {new_state}{reason_str}")
        else:
            logger.info(f"Redis connection state: {old_state} → {new_state}{reason_str}")
    
    def _set_connection_state(self, new_state: str, reason: str = "") -> None:
        """Update connection state with logging."""
        old_state = self._connection_state
        if old_state != new_state:
            self._connection_state = new_state
            self._log_state_change(old_state, new_state, reason)

    def _make_key(self, key: str) -> str:
        """Create a prefixed cache key with namespace isolation."""
        if key.startswith(self.key_prefix):
            return key
        return f"{self.key_prefix}{key}"
    
    async def _start_reconnect_task(self) -> None:
        """Start background task for automatic reconnection."""
        if not self.auto_reconnect:
            return
        
        if self._reconnect_task is not None and not self._reconnect_task.done():
            return  # Task already running
        
        # Create shutdown event if not exists
        if self._shutdown_event is None:
            try:
                self._shutdown_event = asyncio.Event()
            except RuntimeError:
                # No event loop running
                return
        
        self._reconnect_task = asyncio.create_task(self._reconnect_loop())
        logger.info("Started automatic Redis reconnection task")
    
    async def _stop_reconnect_task(self) -> None:
        """Stop the background reconnection task."""
        if self._reconnect_task is not None:
            if self._shutdown_event:
                self._shutdown_event.set()
            
            try:
                self._reconnect_task.cancel()
                await asyncio.wait_for(self._reconnect_task, timeout=2.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
            
            self._reconnect_task = None
            logger.info("Stopped automatic Redis reconnection task")
    
    async def _reconnect_loop(self) -> None:
        """Background loop that attempts to reconnect to Redis when in fallback mode."""
        while True:
            try:
                # Wait for the reconnect interval or shutdown
                if self._shutdown_event:
                    try:
                        await asyncio.wait_for(
                            self._shutdown_event.wait(),
                            timeout=self._calculate_reconnect_delay()
                        )
                        # Shutdown event was set
                        break
                    except asyncio.TimeoutError:
                        # Timeout expired, continue with reconnection attempt
                        pass
                else:
                    await asyncio.sleep(self._calculate_reconnect_delay())
                
                # Only attempt reconnection if we're in fallback mode
                if self._using_fallback and self.redis_host:
                    await self._attempt_reconnect()
                    
            except asyncio.CancelledError:
                logger.info("Reconnection task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in reconnection loop: {e}")
                await asyncio.sleep(self.reconnect_interval)
    
    def _calculate_reconnect_delay(self) -> float:
        """Calculate reconnection delay with exponential backoff."""
        # Exponential backoff: base_interval * 2^attempts, capped at max_backoff
        delay = self.reconnect_interval * (2 ** min(self._reconnect_attempts, 5))
        return min(delay, self.RECONNECT_MAX_BACKOFF)
    
    async def _attempt_reconnect(self) -> bool:
        """
        Attempt to reconnect to Redis.
        
        Returns:
            True if reconnection was successful
        """
        self._stats["reconnect_attempts"] += 1
        self._reconnect_attempts += 1
        self._set_connection_state(ConnectionState.RECONNECTING, f"attempt {self._reconnect_attempts}")
        
        try:
            # Close existing connection if any
            if self._redis:
                try:
                    await self._redis.close()
                except Exception:
                    pass
                self._redis = None
            
            # Build connection URL for Azure Redis
            if self.redis_ssl:
                url = f"rediss://:{self.redis_password}@{self.redis_host}:{self.redis_port}"
            else:
                url = f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}"
            
            self._redis = aioredis.from_url(
                url,
                encoding="utf-8",
                decode_responses=False,
                socket_connect_timeout=5,
                socket_timeout=10,
                retry_on_timeout=True,
                health_check_interval=30,
            )
            
            # Test connection
            await self._redis.ping()
            
            # Success! Update state
            self._connected = True
            self._using_fallback = False
            self._reconnect_attempts = 0
            self._stats["successful_reconnects"] += 1
            self._set_connection_state(
                ConnectionState.CONNECTED, 
                f"reconnected to {self.redis_host}:{self.redis_port}"
            )
            
            return True
            
        except Exception as e:
            logger.warning(f"Reconnection attempt {self._reconnect_attempts} failed: {e}")
            self._set_connection_state(ConnectionState.FALLBACK, f"reconnection failed: {e}")
            return False
    
    async def check_redis_availability(self) -> bool:
        """
        Check if Redis is currently available.
        
        Returns:
            True if Redis is available and responding
        """
        if not REDIS_AVAILABLE or not self.redis_host:
            return False
        
        if self._redis and self._connected and not self._using_fallback:
            try:
                await self._redis.ping()
                return True
            except Exception:
                return False
        
        return False
    
    def get_connection_state(self) -> Dict[str, Any]:
        """
        Get current connection state information.
        
        Returns:
            Dictionary with connection state details
        """
        return {
            "state": self._connection_state,
            "connected": self._connected,
            "using_fallback": self._using_fallback,
            "last_state_change": self._last_state_change,
            "reconnect_attempts": self._reconnect_attempts,
            "auto_reconnect_enabled": self.auto_reconnect,
            "reconnect_task_running": self._reconnect_task is not None and not self._reconnect_task.done(),
        }
    
    async def connect(self) -> bool:
        """
        Establish Redis connection with SSL and retry logic.
        
        Returns:
            True if connected to Redis, False if using fallback
        """
        self._set_connection_state(ConnectionState.CONNECTING, "initial connection attempt")
        
        if not REDIS_AVAILABLE:
            logger.warning("Redis package not available, using in-memory fallback")
            self._using_fallback = True
            self._stats["fallback_activations"] += 1
            self._set_connection_state(ConnectionState.FALLBACK, "redis package not available")
            return False
        
        if not self.redis_host:
            logger.warning("REDIS_HOST not configured, using in-memory fallback")
            self._using_fallback = True
            self._stats["fallback_activations"] += 1
            self._set_connection_state(ConnectionState.FALLBACK, "REDIS_HOST not configured")
            return False
        
        # Attempt connection with exponential backoff
        for attempt in range(self.MAX_RETRIES):
            try:
                # Build connection URL for Azure Redis
                if self.redis_ssl:
                    # Azure Redis requires SSL on port 6380
                    url = f"rediss://:{self.redis_password}@{self.redis_host}:{self.redis_port}"
                else:
                    url = f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}"
                
                self._redis = aioredis.from_url(
                    url,
                    encoding="utf-8",
                    decode_responses=False,  # We handle encoding ourselves
                    socket_connect_timeout=5,
                    socket_timeout=10,
                    retry_on_timeout=True,
                    health_check_interval=30,
                )
                
                # Test connection
                await self._redis.ping()
                
                self._connected = True
                self._using_fallback = False
                self._reconnect_attempts = 0
                self._set_connection_state(
                    ConnectionState.CONNECTED, 
                    f"connected to {self.redis_host}:{self.redis_port} (SSL: {self.redis_ssl})"
                )
                logger.info(f"✅ Connected to Redis at {self.redis_host}:{self.redis_port} (SSL: {self.redis_ssl})")
                return True
                
            except Exception as e:
                delay = min(self.BASE_RETRY_DELAY * (2 ** attempt), self.MAX_RETRY_DELAY)
                logger.warning(f"Redis connection attempt {attempt + 1}/{self.MAX_RETRIES} failed: {e}")
                
                if attempt < self.MAX_RETRIES - 1:
                    logger.info(f"Retrying in {delay:.1f} seconds...")
                    await asyncio.sleep(delay)
        
        # All retries failed, use fallback
        logger.warning("❌ Redis connection failed after all retries, using in-memory fallback")
        self._using_fallback = True
        self._connected = False
        self._stats["fallback_activations"] += 1
        self._set_connection_state(ConnectionState.FALLBACK, "connection failed after all retries")
        
        # Start automatic reconnection task if enabled
        if self.auto_reconnect:
            await self._start_reconnect_task()
        
        return False
    
    async def disconnect(self) -> None:
        """Gracefully close Redis connection and stop reconnection task."""
        # Stop reconnection task first
        await self._stop_reconnect_task()
        
        if self._redis:
            try:
                await self._redis.close()
                logger.info("Redis connection closed gracefully")
            except Exception as e:
                logger.error(f"Error closing Redis connection: {e}")
            finally:
                self._redis = None
                self._connected = False
        
        self._set_connection_state(ConnectionState.DISCONNECTED, "graceful shutdown")
    
    async def _execute_with_fallback(self, redis_op: Callable, memory_op: Callable) -> Any:
        """
        Execute operation with automatic fallback to memory cache.
        
        Args:
            redis_op: Async function to execute on Redis
            memory_op: Async function to execute on memory cache
            
        Returns:
            Result of the operation
        """
        if self._using_fallback or not self._redis:
            return await memory_op()
        
        try:
            return await redis_op()
        except Exception as e:
            logger.warning(f"Redis operation failed, falling back to memory: {e}")
            self._stats["errors"] += 1
            
            # Check if we should switch to fallback mode
            if not self._using_fallback:
                self._using_fallback = True
                self._connected = False
                self._stats["fallback_activations"] += 1
                self._set_connection_state(ConnectionState.FALLBACK, f"operation failed: {e}")
                
                # Start automatic reconnection task if enabled
                if self.auto_reconnect:
                    await self._start_reconnect_task()
            
            return await memory_op()
    
    def _serialize(self, value: Any) -> bytes:
        """Serialize value to bytes for Redis storage."""
        try:
            # Handle Pydantic models (v2: model_dump, v1: dict)
            if hasattr(value, 'model_dump'):
                value = value.model_dump()
            elif hasattr(value, 'dict'):
                value = value.dict()
            return json.dumps(value).encode('utf-8')
        except (TypeError, ValueError) as e:
            logger.error(f"Serialization error: {e}")
            raise
    
    def _deserialize(self, data: bytes) -> Any:
        """Deserialize bytes from Redis to Python object."""
        try:
            if isinstance(data, bytes):
                return json.loads(data.decode('utf-8'))
            return json.loads(data)
        except (TypeError, ValueError, json.JSONDecodeError) as e:
            logger.error(f"Deserialization error: {e}")
            raise
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache with automatic deserialization.
        
        Args:
            key: Cache key (prefix will be added automatically)
            
        Returns:
            Cached value or None if not found
        """
        cache_key = self._make_key(key)
        
        async def redis_get():
            data = await self._redis.get(cache_key)
            if data is not None:
                self._stats["hits"] += 1
                return self._deserialize(data)
            self._stats["misses"] += 1
            return None
        
        async def memory_get():
            result = await self._memory_cache.get(cache_key)
            if result is not None:
                self._stats["hits"] += 1
            else:
                self._stats["misses"] += 1
            return result
        
        return await self._execute_with_fallback(redis_get, memory_get)
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        nx: bool = False
    ) -> bool:
        """
        Set value in cache with serialization and optional TTL.
        
        Args:
            key: Cache key (prefix will be added automatically)
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)
            nx: Only set if key doesn't exist (for distributed locks)
            
        Returns:
            True if set successfully, False otherwise
        """
        cache_key = self._make_key(key)
        ttl = ttl if ttl is not None else self.default_ttl
        
        async def redis_set():
            serialized = self._serialize(value)
            if nx:
                result = await self._redis.set(cache_key, serialized, ex=ttl, nx=True)
            else:
                result = await self._redis.set(cache_key, serialized, ex=ttl)
            
            if result is not False and result is not None:
                self._stats["sets"] += 1
                return True
            return False
        
        async def memory_set():
            result = await self._memory_cache.set(cache_key, value, ttl=ttl)
            if result:
                self._stats["sets"] += 1
            return result
        
        return await self._execute_with_fallback(redis_set, memory_set)
    
    async def delete(self, key: str) -> bool:
        """
        Delete key from cache.
        
        Args:
            key: Cache key (prefix will be added automatically)
            
        Returns:
            True if deleted, False if key didn't exist
        """
        cache_key = self._make_key(key)
        
        async def redis_delete():
            result = await self._redis.delete(cache_key)
            if result > 0:
                self._stats["deletes"] += 1
                return True
            return False
        
        async def memory_delete():
            result = await self._memory_cache.delete(cache_key)
            if result:
                self._stats["deletes"] += 1
            return result
        
        return await self._execute_with_fallback(redis_delete, memory_delete)
    
    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: Cache key (prefix will be added automatically)
            
        Returns:
            True if key exists, False otherwise
        """
        cache_key = self._make_key(key)
        
        async def redis_exists():
            return await self._redis.exists(cache_key) > 0
        
        async def memory_exists():
            return await self._memory_cache.exists(cache_key)
        
        return await self._execute_with_fallback(redis_exists, memory_exists)

    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern using SCAN.
        
        Args:
            pattern: Pattern to match (supports * wildcards)
            
        Returns:
            Number of keys deleted
        """
        full_pattern = self._make_key(pattern)
        
        async def redis_delete_pattern():
            deleted_count = 0
            cursor = 0
            
            while True:
                cursor, keys = await self._redis.scan(cursor, match=full_pattern, count=100)
                if keys:
                    deleted_count += await self._redis.delete(*keys)
                
                if cursor == 0:
                    break
            
            self._stats["deletes"] += deleted_count
            return deleted_count
        
        async def memory_delete_pattern():
            # Simple pattern matching for memory cache
            import fnmatch
            deleted_count = 0
            
            # Get all keys that match the pattern
            keys_to_delete = []
            for key in list(self._memory_cache._cache.keys()):
                if fnmatch.fnmatch(key, full_pattern):
                    keys_to_delete.append(key)
            
            for key in keys_to_delete:
                if await self._memory_cache.delete(key):
                    deleted_count += 1
            
            self._stats["deletes"] += deleted_count
            return deleted_count
        
        return await self._execute_with_fallback(redis_delete_pattern, memory_delete_pattern)
    
    async def get_or_compute(
        self,
        key: str,
        compute_fn: Callable[[], Any],
        ttl: Optional[int] = None
    ) -> Any:
        """
        Get from cache or compute with stampede prevention.
        
        Uses distributed locks to ensure only one request computes
        the value when cache is empty or expired.
        
        Args:
            key: Cache key
            compute_fn: Async function to compute value if not cached
            ttl: Time-to-live in seconds
            
        Returns:
            Cached or computed value
        """
        # Try to get from cache first
        cached = await self.get(key)
        if cached is not None:
            return cached
        
        # Acquire lock to prevent stampede
        lock_key = f"lock:{key}"
        lock_acquired = False
        
        try:
            # Try to acquire lock with SET NX EX
            lock_acquired = await self.set(lock_key, "1", ttl=self.LOCK_TIMEOUT, nx=True)
            
            if lock_acquired:
                # We got the lock, compute the value
                if asyncio.iscoroutinefunction(compute_fn):
                    result = await compute_fn()
                else:
                    result = compute_fn()
                
                # Cache the result
                if result is not None:
                    await self.set(key, result, ttl=ttl)
                
                return result
            else:
                # Another process is computing, wait and retry
                for _ in range(self.LOCK_MAX_RETRIES):
                    await asyncio.sleep(self.LOCK_RETRY_DELAY)
                    
                    # Check if value is now available
                    cached = await self.get(key)
                    if cached is not None:
                        return cached
                
                # Timeout waiting for other process, compute ourselves
                logger.warning(f"Lock wait timeout for key {key}, computing value")
                if asyncio.iscoroutinefunction(compute_fn):
                    result = await compute_fn()
                else:
                    result = compute_fn()
                
                if result is not None:
                    await self.set(key, result, ttl=ttl)
                
                return result
                
        finally:
            # Release lock in finally block to prevent deadlocks
            if lock_acquired:
                await self.delete(lock_key)
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check and return status.
        
        Returns:
            Health check results including connectivity and latency
        """
        health = {
            "healthy": True,
            "backend": "redis" if not self._using_fallback else "memory",
            "using_fallback": self._using_fallback,
            "connection_state": self._connection_state,
            "last_state_change": self._last_state_change,
            "auto_reconnect_enabled": self.auto_reconnect,
            "reconnect_task_running": self._reconnect_task is not None and not self._reconnect_task.done(),
            "timestamp": time.time(),
        }
        
        if not self._using_fallback and self._redis:
            try:
                start_time = time.time()
                await self._redis.ping()
                health["ping_latency_ms"] = round((time.time() - start_time) * 1000, 2)
                
                # Get Redis info
                info = await self._redis.info("memory")
                health["redis_info"] = {
                    "used_memory": info.get("used_memory", 0),
                    "used_memory_human": info.get("used_memory_human", "unknown"),
                    "maxmemory": info.get("maxmemory", 0),
                }
            except Exception as e:
                health["healthy"] = False
                health["error"] = str(e)
        else:
            # Memory cache health
            health["memory_stats"] = self._memory_cache.get_stats()
        
        return health
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Statistics including hit rate, operations, and memory usage
        """
        total_ops = self._stats["hits"] + self._stats["misses"]
        hit_rate = (self._stats["hits"] / total_ops * 100) if total_ops > 0 else 0.0
        
        stats = {
            **self._stats,
            "total_operations": total_ops,
            "hit_rate_percent": round(hit_rate, 2),
            "backend": "redis" if not self._using_fallback else "memory",
            "using_fallback": self._using_fallback,
            "connection_state": self._connection_state,
            "auto_reconnect_enabled": self.auto_reconnect,
            "reconnect_task_running": self._reconnect_task is not None and not self._reconnect_task.done(),
        }
        
        # Log warning if hit rate is below 50%
        if total_ops > 100 and hit_rate < 50:
            logger.warning(f"Cache hit rate is low: {hit_rate:.1f}%")
        
        if not self._using_fallback and self._redis:
            try:
                info = await self._redis.info("memory")
                stats["redis_memory"] = {
                    "used_memory": info.get("used_memory", 0),
                    "used_memory_human": info.get("used_memory_human", "unknown"),
                }
                
                # Get key count by namespace
                key_count = 0
                cursor = 0
                while True:
                    cursor, keys = await self._redis.scan(cursor, match=f"{self.key_prefix}*", count=1000)
                    key_count += len(keys)
                    if cursor == 0:
                        break
                stats["key_count"] = key_count
                
            except Exception as e:
                stats["redis_stats_error"] = str(e)
        else:
            stats["memory_stats"] = self._memory_cache.get_stats()
        
        return stats
    
    async def reconnect(self) -> bool:
        """
        Attempt to reconnect to Redis.
        
        This method can be called manually to trigger an immediate
        reconnection attempt, regardless of the auto_reconnect setting.
        
        Returns:
            True if reconnected successfully
        """
        if not self._using_fallback and self._connected:
            # Already connected, verify connection is still good
            try:
                await self._redis.ping()
                return True
            except Exception:
                # Connection is bad, proceed with reconnection
                self._using_fallback = True
                self._connected = False
        
        logger.info("Attempting manual reconnection to Redis...")
        return await self._attempt_reconnect()
    
    async def force_fallback(self) -> None:
        """
        Force the service into fallback mode.
        
        Useful for testing graceful degradation behavior.
        """
        if self._redis:
            try:
                await self._redis.close()
            except Exception:
                pass
            self._redis = None
        
        self._connected = False
        self._using_fallback = True
        self._set_connection_state(ConnectionState.FALLBACK, "forced fallback mode")
        
        # Start reconnection task if auto_reconnect is enabled
        if self.auto_reconnect:
            await self._start_reconnect_task()
    
    async def enable_auto_reconnect(self) -> None:
        """Enable automatic reconnection and start the reconnection task if in fallback mode."""
        self.auto_reconnect = True
        if self._using_fallback:
            await self._start_reconnect_task()
    
    async def disable_auto_reconnect(self) -> None:
        """Disable automatic reconnection and stop the reconnection task."""
        self.auto_reconnect = False
        await self._stop_reconnect_task()


# Global singleton instance
_cache_service: Optional[RedisCacheService] = None


def get_cache_service() -> RedisCacheService:
    """
    Get global cache service instance.
    
    Returns:
        RedisCacheService singleton instance
    """
    global _cache_service
    if _cache_service is None:
        _cache_service = RedisCacheService(
            redis_host=os.getenv("REDIS_HOST"),
            redis_port=int(os.getenv("REDIS_PORT", "6380")),
            redis_password=os.getenv("REDIS_PASSWORD"),
            redis_ssl=os.getenv("REDIS_SSL", "true").lower() == "true"
        )
    return _cache_service


async def init_cache_service() -> RedisCacheService:
    """
    Initialize cache service at application startup.
    
    Returns:
        Initialized RedisCacheService instance
    """
    service = get_cache_service()
    await service.connect()
    return service


async def shutdown_cache_service() -> None:
    """Shutdown cache service at application shutdown."""
    global _cache_service
    if _cache_service:
        await _cache_service.disconnect()
        _cache_service = None
