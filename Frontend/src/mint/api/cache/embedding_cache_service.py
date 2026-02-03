#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Embedding Cache Service for Yuba Backend.

Provides specialized caching for AI text embeddings with 7-day TTL.
Implements text normalization for consistent cache keys and reduces
OpenAI API costs by avoiding redundant embedding generation.

This service implements:
- Text normalization (lowercase, trim whitespace, truncate to 8192 chars)
- SHA256-based cache key generation
- Model-specific cache isolation
- 7-day TTL for deterministic embeddings
"""

import hashlib
import logging
from typing import List, Optional

from .redis_service import RedisCacheService, get_cache_service

logger = logging.getLogger(__name__)

# Constants
EMBEDDING_TTL = 604800  # 7 days in seconds
MAX_TEXT_LENGTH = 8192  # Maximum text length for embeddings


class EmbeddingCacheService:
    """
    Specialized cache for AI embeddings with 7-day TTL.
    
    Embeddings are deterministic for the same model and input text,
    so they can be cached for extended periods to reduce API costs.
    """
    
    def __init__(self, cache_service: Optional[RedisCacheService] = None):
        """
        Initialize embedding cache service.
        
        Args:
            cache_service: Optional RedisCacheService instance.
                          If not provided, uses the global singleton.
        """
        self.cache = cache_service or get_cache_service()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
        }
    
    def _normalize_text(self, text: str) -> str:
        """
        Normalize text for consistent cache keys.
        
        Normalization ensures that semantically equivalent texts
        produce the same cache key:
        - Converts to lowercase
        - Removes extra whitespace (collapses multiple spaces)
        - Truncates to MAX_TEXT_LENGTH (8192 chars)
        
        Args:
            text: Raw input text
            
        Returns:
            Normalized text string
        """
        # Remove extra whitespace (collapse multiple spaces/newlines to single space)
        normalized = " ".join(text.split())
        # Convert to lowercase for case-insensitive matching
        normalized = normalized.lower()
        # Truncate to model maximum
        normalized = normalized[:MAX_TEXT_LENGTH]
        return normalized
    
    def _build_key(self, text: str, model: str) -> str:
        """
        Build cache key from normalized text hash.
        
        Key format: embed:{model}:{text_hash}
        
        The text hash is a truncated SHA256 hash of the normalized text,
        ensuring consistent keys for equivalent inputs while keeping
        key length manageable.
        
        Args:
            text: Raw input text (will be normalized)
            model: Model name/identifier
            
        Returns:
            Cache key string
        """
        normalized = self._normalize_text(text)
        # Use SHA256 for consistent hashing, truncate to 16 chars for key brevity
        text_hash = hashlib.sha256(normalized.encode('utf-8')).hexdigest()[:16]
        return f"embed:{model}:{text_hash}"
    
    async def get_embedding(
        self,
        text: str,
        model: str = "text-embedding-3-small"
    ) -> Optional[List[float]]:
        """
        Get cached embedding if exists.
        
        Args:
            text: Text to get embedding for
            model: Model name (default: text-embedding-3-small)
            
        Returns:
            Cached embedding vector or None if not found
        """
        key = self._build_key(text, model)
        
        try:
            result = await self.cache.get(key)
            if result is not None:
                self._stats["hits"] += 1
                logger.debug(f"Embedding cache hit for key: {key}")
                return result
            
            self._stats["misses"] += 1
            logger.debug(f"Embedding cache miss for key: {key}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting embedding from cache: {e}")
            self._stats["misses"] += 1
            return None
    
    async def set_embedding(
        self,
        text: str,
        embedding: List[float],
        model: str = "text-embedding-3-small"
    ) -> bool:
        """
        Cache embedding with 7-day TTL.
        
        Args:
            text: Original text that was embedded
            embedding: Embedding vector to cache
            model: Model name (default: text-embedding-3-small)
            
        Returns:
            True if cached successfully, False otherwise
        """
        key = self._build_key(text, model)
        
        try:
            result = await self.cache.set(key, embedding, ttl=EMBEDDING_TTL)
            if result:
                self._stats["sets"] += 1
                logger.debug(f"Cached embedding for key: {key}")
            return result
            
        except Exception as e:
            logger.error(f"Error caching embedding: {e}")
            return False
    
    async def get_or_generate(
        self,
        text: str,
        generate_fn,
        model: str = "text-embedding-3-small"
    ) -> Optional[List[float]]:
        """
        Get embedding from cache or generate if not cached.
        
        This is a convenience method that combines cache lookup
        and generation in a single call.
        
        Args:
            text: Text to get/generate embedding for
            generate_fn: Async function to generate embedding if not cached
            model: Model name (default: text-embedding-3-small)
            
        Returns:
            Embedding vector (from cache or newly generated)
        """
        # Try cache first
        cached = await self.get_embedding(text, model)
        if cached is not None:
            return cached
        
        # Generate embedding
        try:
            embedding = await generate_fn(text)
            
            # Cache the result
            if embedding is not None:
                await self.set_embedding(text, embedding, model)
            
            return embedding
            
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None
    
    def get_stats(self) -> dict:
        """
        Get embedding cache statistics.
        
        Returns:
            Dictionary with hit/miss/set counts and hit rate
        """
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = (self._stats["hits"] / total * 100) if total > 0 else 0.0
        
        return {
            **self._stats,
            "total_lookups": total,
            "hit_rate_percent": round(hit_rate, 2),
        }


# Global singleton instance
_embedding_cache_service: Optional[EmbeddingCacheService] = None


def get_embedding_cache_service() -> EmbeddingCacheService:
    """
    Get global embedding cache service instance.
    
    Returns:
        EmbeddingCacheService singleton instance
    """
    global _embedding_cache_service
    if _embedding_cache_service is None:
        _embedding_cache_service = EmbeddingCacheService()
    return _embedding_cache_service


async def init_embedding_cache_service() -> EmbeddingCacheService:
    """
    Initialize embedding cache service at application startup.
    
    Returns:
        Initialized EmbeddingCacheService instance
    """
    service = get_embedding_cache_service()
    logger.info("Embedding cache service initialized")
    return service


async def shutdown_embedding_cache_service() -> None:
    """Shutdown embedding cache service at application shutdown."""
    global _embedding_cache_service
    if _embedding_cache_service:
        logger.info("Embedding cache service shutdown")
        _embedding_cache_service = None
