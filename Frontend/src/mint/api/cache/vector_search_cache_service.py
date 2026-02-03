#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Vector Search Cache Service for Yuba Backend.

Provides specialized caching for vector search results with 5-minute TTL.
Implements cache key generation from report_id, query_hash, and options_hash.
Supports invalidation on document re-chunking.

This service implements:
- 5-minute TTL for search results to balance freshness and performance
- Cache key format: vsearch:{report_id}:{query_hash}:{options_hash}
- Invalidation on document re-chunking
- Statistics tracking for cache performance monitoring
"""

import hashlib
import json
import logging
from typing import Any, Dict, List, Optional

from .redis_service import RedisCacheService, get_cache_service

logger = logging.getLogger(__name__)

# Constants
VECTOR_SEARCH_TTL = 300  # 5 minutes in seconds


class VectorSearchCacheService:
    """
    Specialized cache for vector search results with 5-minute TTL.
    
    Vector search results are cached to reduce expensive embedding generation
    and database searches for repeated RAG queries.
    """
    
    def __init__(self, cache_service: Optional[RedisCacheService] = None):
        """
        Initialize vector search cache service.
        
        Args:
            cache_service: Optional RedisCacheService instance.
                          If not provided, uses the global singleton.
        """
        self.cache = cache_service or get_cache_service()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "invalidations": 0,
        }
    
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
    
    def _hash_options(self, options: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate a hash for search options.
        
        Args:
            options: Dictionary of search options
            
        Returns:
            Truncated SHA256 hash of the options
        """
        if not options:
            return "default"
        
        # Sort keys for consistent hashing
        options_str = json.dumps(options, sort_keys=True)
        return hashlib.sha256(options_str.encode('utf-8')).hexdigest()[:8]
    
    def _build_key(
        self,
        report_id: str,
        query: str,
        options: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Build cache key for vector search results.
        
        Key format: vsearch:{report_id}:{query_hash}:{options_hash}
        
        Args:
            report_id: ID of the report being searched
            query: Search query string
            options: Optional search options dictionary
            
        Returns:
            Cache key string
        """
        query_hash = self._hash_query(query)
        options_hash = self._hash_options(options)
        return f"vsearch:{report_id}:{query_hash}:{options_hash}"
    
    async def get_search_results(
        self,
        report_id: str,
        query: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get cached vector search results if they exist.
        
        Args:
            report_id: ID of the report being searched
            query: Search query string
            options: Optional search options dictionary
            
        Returns:
            Cached search results or None if not found
        """
        key = self._build_key(report_id, query, options)
        
        try:
            result = await self.cache.get(key)
            if result is not None:
                self._stats["hits"] += 1
                logger.debug(f"Vector search cache hit for key: {key}")
                return result
            
            self._stats["misses"] += 1
            logger.debug(f"Vector search cache miss for key: {key}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting vector search results from cache: {e}")
            self._stats["misses"] += 1
            return None
    
    async def set_search_results(
        self,
        report_id: str,
        query: str,
        results: List[Dict[str, Any]],
        options: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Cache vector search results with 5-minute TTL.
        
        Args:
            report_id: ID of the report being searched
            query: Search query string
            results: Search results to cache
            options: Optional search options dictionary
            
        Returns:
            True if cached successfully, False otherwise
        """
        key = self._build_key(report_id, query, options)
        
        try:
            result = await self.cache.set(key, results, ttl=VECTOR_SEARCH_TTL)
            if result:
                self._stats["sets"] += 1
                logger.debug(f"Cached vector search results for key: {key}")
            return result
            
        except Exception as e:
            logger.error(f"Error caching vector search results: {e}")
            return False
    
    async def invalidate_report_cache(self, report_id: str) -> int:
        """
        Invalidate all cached search results for a report.
        
        Called when documents are re-chunked to ensure fresh results.
        
        Args:
            report_id: ID of the report to invalidate
            
        Returns:
            Number of keys invalidated
        """
        pattern = f"vsearch:{report_id}:*"
        
        try:
            deleted_count = await self.cache.delete_pattern(pattern)
            self._stats["invalidations"] += deleted_count
            logger.info(f"Invalidated {deleted_count} vector search cache entries for report {report_id}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error invalidating vector search cache for report {report_id}: {e}")
            return 0
    
    async def invalidate_project_cache(self, project_id: str) -> int:
        """
        Invalidate all cached search results for a project.
        
        Called when project documents are re-chunked.
        
        Args:
            project_id: ID of the project to invalidate
            
        Returns:
            Number of keys invalidated
        """
        # Project-level invalidation uses the same pattern as report
        # since report_id is typically the project's PV report ID
        return await self.invalidate_report_cache(project_id)
    
    async def get_or_search(
        self,
        report_id: str,
        query: str,
        search_fn,
        options: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get cached results or execute search if not cached.
        
        This is a convenience method that combines cache lookup
        and search execution in a single call.
        
        Args:
            report_id: ID of the report being searched
            query: Search query string
            search_fn: Async function to execute search if not cached
            options: Optional search options dictionary
            
        Returns:
            Search results (from cache or newly executed)
        """
        # Try cache first
        cached = await self.get_search_results(report_id, query, options)
        if cached is not None:
            return cached
        
        # Execute search
        try:
            results = await search_fn()
            
            # Cache the results
            if results is not None:
                await self.set_search_results(report_id, query, results, options)
            
            return results or []
            
        except Exception as e:
            logger.error(f"Error executing vector search: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get vector search cache statistics.
        
        Returns:
            Dictionary with hit/miss/set/invalidation counts and hit rate
        """
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = (self._stats["hits"] / total * 100) if total > 0 else 0.0
        
        return {
            **self._stats,
            "total_lookups": total,
            "hit_rate_percent": round(hit_rate, 2),
            "ttl_seconds": VECTOR_SEARCH_TTL,
        }


# Global singleton instance
_vector_search_cache_service: Optional[VectorSearchCacheService] = None


def get_vector_search_cache_service() -> VectorSearchCacheService:
    """
    Get global vector search cache service instance.
    
    Returns:
        VectorSearchCacheService singleton instance
    """
    global _vector_search_cache_service
    if _vector_search_cache_service is None:
        _vector_search_cache_service = VectorSearchCacheService()
    return _vector_search_cache_service


async def init_vector_search_cache_service() -> VectorSearchCacheService:
    """
    Initialize vector search cache service at application startup.
    
    Returns:
        Initialized VectorSearchCacheService instance
    """
    service = get_vector_search_cache_service()
    logger.info("Vector search cache service initialized")
    return service


async def shutdown_vector_search_cache_service() -> None:
    """Shutdown vector search cache service at application shutdown."""
    global _vector_search_cache_service
    if _vector_search_cache_service:
        logger.info("Vector search cache service shutdown")
        _vector_search_cache_service = None
