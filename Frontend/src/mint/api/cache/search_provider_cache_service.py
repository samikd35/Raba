#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Search Provider Cache Service for Yuba Backend.

Provides specialized caching for external search API responses (Brave, Tavily, Serper).
Implements different TTLs based on search type to reduce API costs and rate limit issues.

This service implements:
- TTLs: 30 minutes for news, 1 hour for general, 4 hours for research
- Cache key format: {provider}:{query_hash}:{num_results}
- Statistics tracking for cache performance monitoring
"""

import hashlib
import logging
from enum import Enum
from typing import Any, Dict, List, Optional

from .redis_service import RedisCacheService, get_cache_service

logger = logging.getLogger(__name__)


class SearchType(Enum):
    """Types of search with different TTL configurations."""
    NEWS = "news"
    GENERAL = "general"
    RESEARCH = "research"


# TTL Configuration per search type (in seconds)
SEARCH_TTL_CONFIG = {
    SearchType.NEWS: 1800,      # 30 minutes - news changes frequently
    SearchType.GENERAL: 3600,   # 1 hour - general search results
    SearchType.RESEARCH: 14400, # 4 hours - research content is more stable
}

# Default TTL for unknown search types
DEFAULT_SEARCH_TTL = 3600  # 1 hour


class SearchProviderCacheService:
    """
    Specialized cache for external search API responses.
    
    Caches responses from Brave, Tavily, and Serper to reduce API costs
    and avoid rate limit issues.
    """
    
    def __init__(self, cache_service: Optional[RedisCacheService] = None):
        """
        Initialize search provider cache service.
        
        Args:
            cache_service: Optional RedisCacheService instance.
                          If not provided, uses the global singleton.
        """
        self.cache = cache_service or get_cache_service()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "api_calls_saved": 0,
        }
        # Track stats per provider
        self._provider_stats: Dict[str, Dict[str, int]] = {}
    
    def _hash_query(self, query: str) -> str:
        """
        Generate a hash for the search query.
        
        Args:
            query: The search query string
            
        Returns:
            Truncated SHA256 hash of the query
        """
        # Normalize query: lowercase and strip whitespace
        normalized = query.lower().strip()
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()[:12]
    
    def _build_key(
        self,
        provider: str,
        query: str,
        num_results: int
    ) -> str:
        """
        Build cache key for search provider results.
        
        Key format: {provider}:{query_hash}:{num_results}
        
        Args:
            provider: Name of the search provider (brave, tavily, serper)
            query: Search query string
            num_results: Number of results requested
            
        Returns:
            Cache key string
        """
        query_hash = self._hash_query(query)
        provider_normalized = provider.lower().strip()
        return f"{provider_normalized}:{query_hash}:{num_results}"
    
    def _get_ttl(self, search_type: SearchType) -> int:
        """
        Get TTL for a search type.
        
        Args:
            search_type: Type of search (news, general, research)
            
        Returns:
            TTL in seconds
        """
        return SEARCH_TTL_CONFIG.get(search_type, DEFAULT_SEARCH_TTL)
    
    def _init_provider_stats(self, provider: str) -> None:
        """Initialize stats for a provider if not exists."""
        if provider not in self._provider_stats:
            self._provider_stats[provider] = {
                "hits": 0,
                "misses": 0,
                "sets": 0,
            }
    
    async def get_search_results(
        self,
        provider: str,
        query: str,
        num_results: int = 10
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get cached search results if they exist.
        
        Args:
            provider: Name of the search provider
            query: Search query string
            num_results: Number of results requested
            
        Returns:
            Cached search results or None if not found
        """
        key = self._build_key(provider, query, num_results)
        provider_lower = provider.lower()
        self._init_provider_stats(provider_lower)
        
        try:
            result = await self.cache.get(key)
            if result is not None:
                self._stats["hits"] += 1
                self._stats["api_calls_saved"] += 1
                self._provider_stats[provider_lower]["hits"] += 1
                logger.debug(f"Search provider cache hit for key: {key}")
                return result
            
            self._stats["misses"] += 1
            self._provider_stats[provider_lower]["misses"] += 1
            logger.debug(f"Search provider cache miss for key: {key}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting search results from cache: {e}")
            self._stats["misses"] += 1
            self._provider_stats[provider_lower]["misses"] += 1
            return None
    
    async def set_search_results(
        self,
        provider: str,
        query: str,
        results: List[Dict[str, Any]],
        num_results: int = 10,
        search_type: SearchType = SearchType.GENERAL
    ) -> bool:
        """
        Cache search results with appropriate TTL based on search type.
        
        Args:
            provider: Name of the search provider
            query: Search query string
            results: Search results to cache
            num_results: Number of results requested
            search_type: Type of search (affects TTL)
            
        Returns:
            True if cached successfully, False otherwise
        """
        key = self._build_key(provider, query, num_results)
        ttl = self._get_ttl(search_type)
        provider_lower = provider.lower()
        self._init_provider_stats(provider_lower)
        
        try:
            result = await self.cache.set(key, results, ttl=ttl)
            if result:
                self._stats["sets"] += 1
                self._provider_stats[provider_lower]["sets"] += 1
                logger.debug(f"Cached search results for key: {key} with TTL: {ttl}s")
            return result
            
        except Exception as e:
            logger.error(f"Error caching search results: {e}")
            return False
    
    async def get_or_search(
        self,
        provider: str,
        query: str,
        search_fn,
        num_results: int = 10,
        search_type: SearchType = SearchType.GENERAL
    ) -> List[Dict[str, Any]]:
        """
        Get cached results or execute search if not cached.
        
        This is a convenience method that combines cache lookup
        and search execution in a single call.
        
        Args:
            provider: Name of the search provider
            query: Search query string
            search_fn: Async function to execute search if not cached
            num_results: Number of results requested
            search_type: Type of search (affects TTL)
            
        Returns:
            Search results (from cache or newly executed)
        """
        # Try cache first
        cached = await self.get_search_results(provider, query, num_results)
        if cached is not None:
            return cached
        
        # Execute search
        try:
            results = await search_fn()
            
            # Cache the results
            if results is not None:
                await self.set_search_results(
                    provider, query, results, num_results, search_type
                )
            
            return results or []
            
        except Exception as e:
            logger.error(f"Error executing search with provider {provider}: {e}")
            return []
    
    async def invalidate_provider_cache(self, provider: str) -> int:
        """
        Invalidate all cached results for a specific provider.
        
        Args:
            provider: Name of the search provider
            
        Returns:
            Number of keys invalidated
        """
        pattern = f"{provider.lower()}:*"
        
        try:
            deleted_count = await self.cache.delete_pattern(pattern)
            logger.info(f"Invalidated {deleted_count} cache entries for provider {provider}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error invalidating cache for provider {provider}: {e}")
            return 0
    
    async def invalidate_query_cache(self, query: str) -> int:
        """
        Invalidate all cached results for a specific query across all providers.
        
        Args:
            query: Search query string
            
        Returns:
            Number of keys invalidated
        """
        query_hash = self._hash_query(query)
        pattern = f"*:{query_hash}:*"
        
        try:
            deleted_count = await self.cache.delete_pattern(pattern)
            logger.info(f"Invalidated {deleted_count} cache entries for query hash {query_hash}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error invalidating cache for query: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get search provider cache statistics.
        
        Returns:
            Dictionary with hit/miss/set counts, hit rate, and per-provider stats
        """
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = (self._stats["hits"] / total * 100) if total > 0 else 0.0
        
        return {
            **self._stats,
            "total_lookups": total,
            "hit_rate_percent": round(hit_rate, 2),
            "provider_stats": self._provider_stats,
            "ttl_config": {
                search_type.value: ttl 
                for search_type, ttl in SEARCH_TTL_CONFIG.items()
            },
        }
    
    def get_provider_stats(self, provider: str) -> Dict[str, Any]:
        """
        Get statistics for a specific provider.
        
        Args:
            provider: Name of the search provider
            
        Returns:
            Dictionary with hit/miss/set counts for the provider
        """
        provider_lower = provider.lower()
        if provider_lower not in self._provider_stats:
            return {"hits": 0, "misses": 0, "sets": 0}
        
        stats = self._provider_stats[provider_lower]
        total = stats["hits"] + stats["misses"]
        hit_rate = (stats["hits"] / total * 100) if total > 0 else 0.0
        
        return {
            **stats,
            "total_lookups": total,
            "hit_rate_percent": round(hit_rate, 2),
        }


# Global singleton instance
_search_provider_cache_service: Optional[SearchProviderCacheService] = None


def get_search_provider_cache_service() -> SearchProviderCacheService:
    """
    Get global search provider cache service instance.
    
    Returns:
        SearchProviderCacheService singleton instance
    """
    global _search_provider_cache_service
    if _search_provider_cache_service is None:
        _search_provider_cache_service = SearchProviderCacheService()
    return _search_provider_cache_service


async def init_search_provider_cache_service() -> SearchProviderCacheService:
    """
    Initialize search provider cache service at application startup.
    
    Returns:
        Initialized SearchProviderCacheService instance
    """
    service = get_search_provider_cache_service()
    logger.info("Search provider cache service initialized")
    return service


async def shutdown_search_provider_cache_service() -> None:
    """Shutdown search provider cache service at application shutdown."""
    global _search_provider_cache_service
    if _search_provider_cache_service:
        logger.info("Search provider cache service shutdown")
        _search_provider_cache_service = None
