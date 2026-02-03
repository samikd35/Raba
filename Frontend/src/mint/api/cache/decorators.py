"""
Query Cache Decorators for Yuba Backend.

Provides decorators for caching FastAPI endpoint results and general function results.

This module implements:
- @cached_query: Decorator for caching FastAPI endpoint responses (Requirements 4.1-4.6)
- @cache_result: Decorator for caching general async function results (Requirements 4.1, 4.2)

Key features:
- Tenant-isolated cache keys
- Cache bypass with X-Skip-Cache header
- Configurable TTL
- Error handling (don't cache None or exceptions)
"""

import asyncio
import hashlib
import json
import logging
from functools import wraps
from typing import Any, Callable, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar('T')


def _generate_params_hash(params: dict) -> str:
    """
    Generate a short hash from query parameters.
    
    Args:
        params: Dictionary of query parameters
        
    Returns:
        8-character hash string
    """
    try:
        # Sort keys for consistent hashing
        sorted_params = json.dumps(params, sort_keys=True, default=str)
        return hashlib.md5(sorted_params.encode()).hexdigest()[:8]
    except (TypeError, ValueError):
        # Fallback for non-serializable params
        return hashlib.md5(str(params).encode()).hexdigest()[:8]


def _build_query_cache_key(
    query_name: str,
    tenant_id: str,
    user_id: Optional[str],
    params_hash: str
) -> str:
    """
    Build a cache key for query results.
    
    Key format: query:{query_name}:{tenant_id}:{user_id}:{params_hash}
    
    Args:
        query_name: Name of the query/endpoint
        tenant_id: Tenant ID for isolation
        user_id: User ID (or "_" if not user-specific)
        params_hash: Hash of query parameters
        
    Returns:
        Formatted cache key
        
    Requirement 4.3: Cache key includes query_name, tenant_id, user_id, params hash
    """
    user_part = user_id if user_id else "_"
    return f"query:{query_name}:{tenant_id}:{user_part}:{params_hash}"


def cached_query(
    query_name: str,
    ttl: int = 180,
    user_specific: bool = True
):
    """
    Decorator to cache FastAPI endpoint results.
    
    This decorator automatically caches endpoint responses with tenant isolation
    and supports cache bypass via the X-Skip-Cache header.
    
    Usage:
        @router.get("/projects")
        @cached_query("vmp_projects_list", ttl=180)
        async def get_projects(
            request: Request,
            current_user: dict = Depends(get_current_user)
        ):
            return await fetch_projects()
    
    Args:
        query_name: Unique name for this query (used in cache key)
        ttl: Time-to-live in seconds (default: 180 = 3 minutes)
        user_specific: Whether to include user_id in cache key (default: True)
        
    Returns:
        Decorated function
        
    Requirements:
        4.1: Provides @cached_query decorator for FastAPI endpoints
        4.2: Automatically caches endpoint response with configurable TTL
        4.3: Generates cache key from query_name, tenant_id, user_id, params hash
        4.4: Supports cache bypass with X-Skip-Cache header
        4.5: Supports TTLs from 5 seconds to 30 minutes
        4.6: Does not cache None results or exceptions
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Import here to avoid circular imports
            from .redis_service import get_cache_service
            
            # Extract current_user from kwargs
            current_user = kwargs.get("current_user")
            if current_user is None:
                # Try to find it in args (less common)
                for arg in args:
                    if isinstance(arg, dict) and "tenant_id" in arg:
                        current_user = arg
                        break
            
            # If no current_user, execute without caching
            if current_user is None:
                logger.debug(f"No current_user found for {query_name}, executing without cache")
                return await func(*args, **kwargs)
            
            # Extract tenant_id and user_id
            tenant_id = current_user.get("tenant_id")
            user_id = current_user.get("user_id") if user_specific else None
            
            # If no tenant_id, execute without caching
            if not tenant_id:
                logger.debug(f"No tenant_id found for {query_name}, executing without cache")
                return await func(*args, **kwargs)
            
            # Check for cache bypass header
            request = kwargs.get("request")
            if request is not None:
                skip_cache_header = None
                # Handle both FastAPI Request and dict-like objects
                if hasattr(request, "headers"):
                    skip_cache_header = request.headers.get("X-Skip-Cache")
                elif isinstance(request, dict):
                    headers = request.get("headers", {})
                    skip_cache_header = headers.get("X-Skip-Cache")
                
                if skip_cache_header and skip_cache_header.lower() == "true":
                    logger.debug(f"Cache bypass requested for {query_name}")
                    return await func(*args, **kwargs)
            
            # Build cache key from query params
            filters = {}
            if request is not None:
                if hasattr(request, "query_params"):
                    filters = dict(request.query_params)
                elif isinstance(request, dict):
                    filters = request.get("query_params", {})
            
            params_hash = _generate_params_hash(filters)
            cache_key = _build_query_cache_key(query_name, tenant_id, user_id, params_hash)
            
            # Try to get from cache
            cache = get_cache_service()
            try:
                cached_result = await cache.get(cache_key)
                if cached_result is not None:
                    logger.debug(f"Cache hit for {cache_key}")
                    return cached_result
            except Exception as e:
                logger.warning(f"Cache get error for {cache_key}: {e}")
                # Continue to execute function on cache error
            
            # Execute the function
            try:
                result = await func(*args, **kwargs)
            except Exception as e:
                # Don't cache exceptions - re-raise
                logger.debug(f"Function {query_name} raised exception, not caching")
                raise
            
            # Don't cache None results (Requirement 4.6)
            if result is None:
                logger.debug(f"Function {query_name} returned None, not caching")
                return result
            
            # Cache the result
            try:
                await cache.set(cache_key, result, ttl=ttl)
                logger.debug(f"Cached result for {cache_key} with TTL {ttl}s")
            except Exception as e:
                logger.warning(f"Cache set error for {cache_key}: {e}")
                # Return result even if caching fails
            
            return result
        
        return wrapper
    return decorator


def cache_result(
    ttl: int = 300,
    key_prefix: str = "",
    key_builder: Optional[Callable[..., str]] = None
):
    """
    Decorator to cache any async function result.
    
    This decorator provides flexible caching for general async functions
    with support for custom key builders and configurable TTL.
    
    Usage:
        @cache_result(ttl=604800, key_prefix="embed")
        async def generate_embedding(text: str) -> List[float]:
            ...
        
        # With custom key builder
        def build_key(text: str, model: str) -> str:
            return f"embed:{model}:{hashlib.md5(text.encode()).hexdigest()[:16]}"
        
        @cache_result(ttl=604800, key_builder=build_key)
        async def generate_embedding(text: str, model: str) -> List[float]:
            ...
    
    Args:
        ttl: Time-to-live in seconds (default: 300 = 5 minutes)
        key_prefix: Prefix for auto-generated cache keys
        key_builder: Optional custom function to build cache key from args/kwargs
        
    Returns:
        Decorated function
        
    Requirements:
        4.1: Provides caching decorator
        4.2: Supports configurable TTL
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Import here to avoid circular imports
            from .redis_service import get_cache_service
            
            cache = get_cache_service()
            
            # Build cache key
            if key_builder is not None:
                try:
                    cache_key = key_builder(*args, **kwargs)
                except Exception as e:
                    logger.warning(f"Custom key builder failed: {e}, using default")
                    cache_key = None
            else:
                cache_key = None
            
            # Default key generation if no custom builder or it failed
            if cache_key is None:
                # Create key from function name and arguments
                try:
                    key_data = f"{func.__name__}:{args}:{sorted(kwargs.items())}"
                    key_hash = hashlib.md5(key_data.encode()).hexdigest()[:12]
                except (TypeError, ValueError):
                    # Fallback for non-hashable args
                    key_hash = hashlib.md5(str((args, kwargs)).encode()).hexdigest()[:12]
                
                if key_prefix:
                    cache_key = f"{key_prefix}:{func.__name__}:{key_hash}"
                else:
                    cache_key = f"{func.__name__}:{key_hash}"
            
            # Try to get from cache
            try:
                cached_result = await cache.get(cache_key)
                if cached_result is not None:
                    logger.debug(f"Cache hit for {cache_key}")
                    return cached_result
            except Exception as e:
                logger.warning(f"Cache get error for {cache_key}: {e}")
                # Continue to execute function on cache error
            
            # Execute the function
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
            except Exception as e:
                # Don't cache exceptions - re-raise
                logger.debug(f"Function {func.__name__} raised exception, not caching")
                raise
            
            # Don't cache None results
            if result is None:
                logger.debug(f"Function {func.__name__} returned None, not caching")
                return result
            
            # Cache the result
            try:
                await cache.set(cache_key, result, ttl=ttl)
                logger.debug(f"Cached result for {cache_key} with TTL {ttl}s")
            except Exception as e:
                logger.warning(f"Cache set error for {cache_key}: {e}")
                # Return result even if caching fails
            
            return result
        
        return wrapper
    return decorator


# Utility functions for external use

def build_query_cache_key(
    query_name: str,
    tenant_id: str,
    user_id: Optional[str] = None,
    params: Optional[dict] = None
) -> str:
    """
    Build a query cache key for external use.
    
    This function can be used to manually build cache keys for
    invalidation or direct cache access.
    
    Args:
        query_name: Name of the query/endpoint
        tenant_id: Tenant ID for isolation
        user_id: User ID (optional)
        params: Query parameters (optional)
        
    Returns:
        Formatted cache key
    """
    params_hash = _generate_params_hash(params or {})
    return _build_query_cache_key(query_name, tenant_id, user_id, params_hash)


def get_query_cache_pattern(
    query_name: str,
    tenant_id: str,
    user_id: Optional[str] = None
) -> str:
    """
    Get a pattern for matching query cache keys.
    
    This function returns a pattern that can be used with
    delete_pattern to invalidate all cache entries for a query.
    
    Args:
        query_name: Name of the query/endpoint
        tenant_id: Tenant ID for isolation
        user_id: User ID (optional, use None for all users)
        
    Returns:
        Pattern string with wildcards
    """
    user_part = user_id if user_id else "*"
    return f"query:{query_name}:{tenant_id}:{user_part}:*"
