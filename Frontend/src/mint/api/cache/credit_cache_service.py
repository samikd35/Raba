"""
Credit Cache Service for Yuba Backend.

Provides Redis-based caching for credit balances and feature costs,
reducing database queries and improving credit check performance.

This service implements:
- Credit balance caching with 1-minute TTL (Requirements 10.1, 10.2)
- Feature cost caching with 1-hour TTL (Requirements 10.4, 10.5)
- Cache invalidation on credit transactions (Requirement 10.3)

**Feature: redis-cache-service**
**Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.5**
"""

import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# TTL Configuration (in seconds)
CREDIT_BALANCE_TTL = 60  # 1 minute - credits change frequently
FEATURE_COST_TTL = 3600  # 1 hour - feature costs rarely change


class CreditCacheService:
    """
    Centralized credit caching service.
    
    Provides caching for credit balances and feature costs to reduce
    database queries during credit checks.
    
    Key formats:
    - Credit balance: credits:{tenant_id}
    - Feature cost: feature_cost:{feature_id}:{plan_type}
    """
    
    def __init__(self, cache_service):
        """
        Initialize credit cache service.
        
        Args:
            cache_service: RedisCacheService instance for cache operations
        """
        self.cache = cache_service
        self._stats = {
            "balance_hits": 0,
            "balance_misses": 0,
            "cost_hits": 0,
            "cost_misses": 0,
            "invalidations": 0,
        }
    
    def _build_balance_key(self, tenant_id: str) -> str:
        """
        Build cache key for credit balance.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Cache key in format credits:{tenant_id}
        """
        return f"credits:{tenant_id}"
    
    def _build_feature_cost_key(self, feature_id: str, plan_type: str) -> str:
        """
        Build cache key for feature cost.
        
        Args:
            feature_id: Feature identifier
            plan_type: Plan type (individual, team, organization)
            
        Returns:
            Cache key in format feature_cost:{feature_id}:{plan_type}
        """
        return f"feature_cost:{feature_id}:{plan_type}"
    
    # ============================================================
    # Credit Balance Caching (Requirements 10.1, 10.2)
    # ============================================================
    
    async def get_credit_balance(self, tenant_id: str) -> Optional[float]:
        """
        Get cached credit balance for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Cached credit balance or None if not cached
            
        **Validates: Requirements 10.1**
        """
        cache_key = self._build_balance_key(tenant_id)
        result = await self.cache.get(cache_key)
        
        if result is not None:
            self._stats["balance_hits"] += 1
            logger.debug(f"Credit balance cache hit for tenant {tenant_id}")
            return result.get("balance") if isinstance(result, dict) else result
        
        self._stats["balance_misses"] += 1
        logger.debug(f"Credit balance cache miss for tenant {tenant_id}")
        return None
    
    async def set_credit_balance(
        self,
        tenant_id: str,
        balance: float,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache credit balance for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            balance: Credit balance to cache
            ttl: Optional TTL override (defaults to CREDIT_BALANCE_TTL)
            
        Returns:
            True if cached successfully
            
        **Validates: Requirements 10.2**
        """
        cache_key = self._build_balance_key(tenant_id)
        ttl = ttl if ttl is not None else CREDIT_BALANCE_TTL
        
        # Store with metadata
        cache_data = {
            "balance": balance,
            "tenant_id": tenant_id,
            "_cached_at": time.time(),
            "_cache_ttl": ttl,
        }
        
        result = await self.cache.set(cache_key, cache_data, ttl=ttl)
        
        if result:
            logger.debug(f"Cached credit balance for tenant {tenant_id}: {balance} with TTL {ttl}s")
        
        return result
    
    async def invalidate_credit_balance(self, tenant_id: str) -> bool:
        """
        Invalidate cached credit balance for a tenant.
        
        Call this when credits are consumed or granted.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            True if invalidated successfully
            
        **Validates: Requirements 10.3**
        """
        cache_key = self._build_balance_key(tenant_id)
        result = await self.cache.delete(cache_key)
        
        if result:
            self._stats["invalidations"] += 1
            logger.info(f"Invalidated credit balance cache for tenant {tenant_id}")
        
        return result
    
    async def get_or_fetch_balance(
        self,
        tenant_id: str,
        fetch_fn
    ) -> float:
        """
        Get credit balance from cache or fetch from database.
        
        This is a convenience method that combines cache lookup
        and database fetch in a single call.
        
        Args:
            tenant_id: Tenant identifier
            fetch_fn: Function to fetch balance from database (sync or async)
            
        Returns:
            Credit balance (from cache or database)
        """
        # Try cache first
        cached = await self.get_credit_balance(tenant_id)
        if cached is not None:
            return cached
        
        # Fetch from database
        import asyncio
        if asyncio.iscoroutinefunction(fetch_fn):
            balance = await fetch_fn(tenant_id)
        else:
            balance = fetch_fn(tenant_id)
        
        # Cache the result
        if balance is not None:
            await self.set_credit_balance(tenant_id, balance)
        
        return balance
    
    # ============================================================
    # Feature Cost Caching (Requirements 10.4, 10.5)
    # ============================================================
    
    async def get_feature_cost(
        self,
        feature_id: str,
        plan_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached feature cost.
        
        Args:
            feature_id: Feature identifier
            plan_type: Plan type (individual, team, organization)
            
        Returns:
            Cached feature cost data or None if not cached
            
        **Validates: Requirements 10.4**
        """
        cache_key = self._build_feature_cost_key(feature_id, plan_type)
        result = await self.cache.get(cache_key)
        
        if result is not None:
            self._stats["cost_hits"] += 1
            logger.debug(f"Feature cost cache hit for {feature_id}:{plan_type}")
            return result
        
        self._stats["cost_misses"] += 1
        logger.debug(f"Feature cost cache miss for {feature_id}:{plan_type}")
        return None
    
    async def set_feature_cost(
        self,
        feature_id: str,
        plan_type: str,
        cost_data: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache feature cost.
        
        Args:
            feature_id: Feature identifier
            plan_type: Plan type (individual, team, organization)
            cost_data: Feature cost data to cache
            ttl: Optional TTL override (defaults to FEATURE_COST_TTL)
            
        Returns:
            True if cached successfully
            
        **Validates: Requirements 10.5**
        """
        cache_key = self._build_feature_cost_key(feature_id, plan_type)
        ttl = ttl if ttl is not None else FEATURE_COST_TTL
        
        # Add cache metadata
        cache_data = {
            **cost_data,
            "_cached_at": time.time(),
            "_cache_ttl": ttl,
        }
        
        result = await self.cache.set(cache_key, cache_data, ttl=ttl)
        
        if result:
            logger.debug(f"Cached feature cost for {feature_id}:{plan_type} with TTL {ttl}s")
        
        return result
    
    async def invalidate_feature_cost(
        self,
        feature_id: str,
        plan_type: Optional[str] = None
    ) -> bool:
        """
        Invalidate cached feature cost.
        
        Args:
            feature_id: Feature identifier
            plan_type: Optional plan type. If None, invalidates all plan types.
            
        Returns:
            True if invalidated successfully
        """
        if plan_type:
            # Invalidate specific plan type
            cache_key = self._build_feature_cost_key(feature_id, plan_type)
            result = await self.cache.delete(cache_key)
        else:
            # Invalidate all plan types using pattern
            pattern = f"feature_cost:{feature_id}:*"
            deleted_count = await self.cache.delete_pattern(pattern)
            result = deleted_count > 0
        
        if result:
            self._stats["invalidations"] += 1
            logger.info(f"Invalidated feature cost cache for {feature_id}:{plan_type or '*'}")
        
        return result
    
    async def get_or_fetch_feature_cost(
        self,
        feature_id: str,
        plan_type: str,
        fetch_fn
    ) -> Optional[Dict[str, Any]]:
        """
        Get feature cost from cache or fetch from database.
        
        Args:
            feature_id: Feature identifier
            plan_type: Plan type
            fetch_fn: Function to fetch cost from database
            
        Returns:
            Feature cost data (from cache or database)
        """
        # Try cache first
        cached = await self.get_feature_cost(feature_id, plan_type)
        if cached is not None:
            return cached
        
        # Fetch from database
        import asyncio
        if asyncio.iscoroutinefunction(fetch_fn):
            cost_data = await fetch_fn(feature_id, plan_type)
        else:
            cost_data = fetch_fn(feature_id, plan_type)
        
        # Cache the result
        if cost_data is not None:
            await self.set_feature_cost(feature_id, plan_type, cost_data)
        
        return cost_data
    
    # ============================================================
    # Statistics
    # ============================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache hit/miss statistics
        """
        total_balance_ops = self._stats["balance_hits"] + self._stats["balance_misses"]
        total_cost_ops = self._stats["cost_hits"] + self._stats["cost_misses"]
        
        balance_hit_rate = (
            (self._stats["balance_hits"] / total_balance_ops * 100)
            if total_balance_ops > 0 else 0.0
        )
        cost_hit_rate = (
            (self._stats["cost_hits"] / total_cost_ops * 100)
            if total_cost_ops > 0 else 0.0
        )
        
        return {
            **self._stats,
            "balance_hit_rate_percent": round(balance_hit_rate, 2),
            "cost_hit_rate_percent": round(cost_hit_rate, 2),
            "total_balance_operations": total_balance_ops,
            "total_cost_operations": total_cost_ops,
        }


# Global singleton instance
_credit_cache_service: Optional[CreditCacheService] = None


def get_credit_cache_service() -> Optional[CreditCacheService]:
    """
    Get global credit cache service instance.
    
    Returns:
        CreditCacheService singleton instance or None if not initialized
    """
    return _credit_cache_service


def init_credit_cache_service(cache_service) -> CreditCacheService:
    """
    Initialize credit cache service with a cache backend.
    
    Args:
        cache_service: RedisCacheService instance
        
    Returns:
        Initialized CreditCacheService instance
    """
    global _credit_cache_service
    _credit_cache_service = CreditCacheService(cache_service)
    logger.info("Credit cache service initialized")
    return _credit_cache_service


def shutdown_credit_cache_service() -> None:
    """Shutdown credit cache service."""
    global _credit_cache_service
    _credit_cache_service = None
    logger.info("Credit cache service shutdown")
