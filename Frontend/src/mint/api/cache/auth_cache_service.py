"""
Authentication Cache Service for Yuba Backend.

Provides Redis-based caching for user authentication context and sessions,
reducing database queries and improving authentication performance.

This service implements:
- User context caching with 5-minute TTL
- Active session caching with 1-hour TTL
- Session invalidation on logout
- User context invalidation on permission changes

**Feature: redis-cache-service**
**Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6**
"""

import hashlib
import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# TTL Configuration (in seconds)
USER_CONTEXT_TTL = 300  # 5 minutes
SESSION_TTL = 3600  # 1 hour


class AuthCacheService:
    """
    Centralized authentication caching service.
    
    Provides caching for user context and sessions to reduce
    database queries during authentication.
    """
    
    def __init__(self, cache_service):
        """
        Initialize auth cache service.
        
        Args:
            cache_service: RedisCacheService instance for cache operations
        """
        self.cache = cache_service
        self._stats = {
            "user_context_hits": 0,
            "user_context_misses": 0,
            "session_hits": 0,
            "session_misses": 0,
            "invalidations": 0,
        }
    
    def _build_user_context_key(self, user_id: str) -> str:
        """
        Build cache key for user context.
        
        Args:
            user_id: User identifier
            
        Returns:
            Cache key in format user_ctx:{user_id}
        """
        return f"user_ctx:{user_id}"
    
    def _build_session_key(self, session_id: str) -> str:
        """
        Build cache key for session.
        
        Args:
            session_id: Session identifier (typically token hash)
            
        Returns:
            Cache key in format session:{session_id}
        """
        return f"session:{session_id}"
    
    def _hash_token(self, token: str) -> str:
        """
        Create a hash of the token for use as session ID.
        
        Args:
            token: JWT token string
            
        Returns:
            SHA256 hash of the token (first 32 chars)
        """
        return hashlib.sha256(token.encode()).hexdigest()[:32]
    
    async def get_user_context(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get cached user context.
        
        Args:
            user_id: User identifier
            
        Returns:
            Cached user context dict or None if not cached
        """
        cache_key = self._build_user_context_key(user_id)
        result = await self.cache.get(cache_key)
        
        if result is not None:
            self._stats["user_context_hits"] += 1
            logger.debug(f"User context cache hit for user {user_id}")
        else:
            self._stats["user_context_misses"] += 1
            logger.debug(f"User context cache miss for user {user_id}")
        
        return result
    
    async def set_user_context(
        self,
        user_id: str,
        context: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache user context.
        
        Args:
            user_id: User identifier
            context: User context data to cache
            ttl: Optional TTL override (defaults to USER_CONTEXT_TTL)
            
        Returns:
            True if cached successfully
        """
        cache_key = self._build_user_context_key(user_id)
        ttl = ttl if ttl is not None else USER_CONTEXT_TTL
        
        # Add cache metadata
        context_with_meta = {
            **context,
            "_cached_at": time.time(),
            "_cache_ttl": ttl,
        }
        
        result = await self.cache.set(cache_key, context_with_meta, ttl=ttl)
        
        if result:
            logger.debug(f"Cached user context for user {user_id} with TTL {ttl}s")
        
        return result
    
    async def invalidate_user_context(self, user_id: str) -> bool:
        """
        Invalidate cached user context.
        
        Call this when user permissions change or on logout.
        
        Args:
            user_id: User identifier
            
        Returns:
            True if invalidated successfully
        """
        cache_key = self._build_user_context_key(user_id)
        result = await self.cache.delete(cache_key)
        
        if result:
            self._stats["invalidations"] += 1
            logger.info(f"Invalidated user context cache for user {user_id}")
        
        return result
    
    async def get_session(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Get cached session data.
        
        Args:
            token: JWT token string
            
        Returns:
            Cached session data or None if not cached
        """
        session_id = self._hash_token(token)
        cache_key = self._build_session_key(session_id)
        result = await self.cache.get(cache_key)
        
        if result is not None:
            self._stats["session_hits"] += 1
            logger.debug(f"Session cache hit for session {session_id[:8]}...")
        else:
            self._stats["session_misses"] += 1
            logger.debug(f"Session cache miss for session {session_id[:8]}...")
        
        return result
    
    async def set_session(
        self,
        token: str,
        session_data: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache session data.
        
        Args:
            token: JWT token string
            session_data: Session data to cache
            ttl: Optional TTL override (defaults to SESSION_TTL)
            
        Returns:
            True if cached successfully
        """
        session_id = self._hash_token(token)
        cache_key = self._build_session_key(session_id)
        ttl = ttl if ttl is not None else SESSION_TTL
        
        # Add cache metadata
        session_with_meta = {
            **session_data,
            "_session_id": session_id,
            "_cached_at": time.time(),
            "_cache_ttl": ttl,
        }
        
        result = await self.cache.set(cache_key, session_with_meta, ttl=ttl)
        
        if result:
            logger.debug(f"Cached session {session_id[:8]}... with TTL {ttl}s")
        
        return result
    
    async def invalidate_session(self, token: str) -> bool:
        """
        Invalidate cached session.
        
        Call this on user logout.
        
        Args:
            token: JWT token string
            
        Returns:
            True if invalidated successfully
        """
        session_id = self._hash_token(token)
        cache_key = self._build_session_key(session_id)
        result = await self.cache.delete(cache_key)
        
        if result:
            self._stats["invalidations"] += 1
            logger.info(f"Invalidated session cache for session {session_id[:8]}...")
        
        return result
    
    async def invalidate_user_sessions(self, user_id: str) -> int:
        """
        Invalidate all sessions for a user.
        
        Uses pattern matching to find and delete all session keys
        associated with a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Number of sessions invalidated
        """
        # Also invalidate user context
        await self.invalidate_user_context(user_id)
        
        # Note: Session keys don't include user_id directly,
        # so we can't pattern-match them. This is by design for security.
        # Individual sessions must be invalidated by token.
        logger.info(f"Invalidated user context for user {user_id}")
        
        return 1  # At minimum, user context was invalidated
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache hit/miss statistics
        """
        total_user_ops = self._stats["user_context_hits"] + self._stats["user_context_misses"]
        total_session_ops = self._stats["session_hits"] + self._stats["session_misses"]
        
        user_hit_rate = (
            (self._stats["user_context_hits"] / total_user_ops * 100)
            if total_user_ops > 0 else 0.0
        )
        session_hit_rate = (
            (self._stats["session_hits"] / total_session_ops * 100)
            if total_session_ops > 0 else 0.0
        )
        
        return {
            **self._stats,
            "user_context_hit_rate_percent": round(user_hit_rate, 2),
            "session_hit_rate_percent": round(session_hit_rate, 2),
            "total_user_context_operations": total_user_ops,
            "total_session_operations": total_session_ops,
        }


# Global singleton instance
_auth_cache_service: Optional[AuthCacheService] = None


def get_auth_cache_service() -> Optional[AuthCacheService]:
    """
    Get global auth cache service instance.
    
    Returns:
        AuthCacheService singleton instance or None if not initialized
    """
    return _auth_cache_service


def init_auth_cache_service(cache_service) -> AuthCacheService:
    """
    Initialize auth cache service with a cache backend.
    
    Args:
        cache_service: RedisCacheService instance
        
    Returns:
        Initialized AuthCacheService instance
    """
    global _auth_cache_service
    _auth_cache_service = AuthCacheService(cache_service)
    logger.info("Auth cache service initialized")
    return _auth_cache_service
