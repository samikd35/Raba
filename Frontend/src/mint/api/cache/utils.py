#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Cache Utility Functions.

This module provides utility functions for cache operations, including
key generation, validation, compression, and performance monitoring.
"""

import hashlib
import json
import time
import zlib
from typing import Any, Dict, List, Optional, Union, Callable
from datetime import datetime, timezone
import logging

from .models import (
    CacheStats, CacheMetrics, CacheKeyInfo, CacheTagInfo,
    CacheCompressionInfo, CacheEvictionInfo, CachePerformanceReport,
    CacheOperationResult, CacheBatchResult, CacheStrategy,
    CACHE_ERROR_CODES, COMPRESSION_ALGORITHMS, EVICTION_POLICIES
)

# Configure logging
logger = logging.getLogger(__name__)


def generate_cache_key(
    prefix: str,
    *args: Any,
    separator: str = ":",
    include_timestamp: bool = False
) -> str:
    """
    Generate a cache key from components.
    
    Args:
        prefix: Key prefix
        *args: Key components
        separator: Separator between components
        include_timestamp: Whether to include timestamp
        
    Returns:
        str: Generated cache key
    """
    components = [prefix]
    
    for arg in args:
        if arg is not None:
            if isinstance(arg, (dict, list)):
                # Serialize complex objects to JSON
                arg_str = json.dumps(arg, sort_keys=True)
            else:
                arg_str = str(arg)
            components.append(arg_str)
    
    if include_timestamp:
        components.append(str(int(time.time())))
    
    return separator.join(components)


def generate_key_hash(key: str, length: int = 16) -> str:
    """
    Generate a hash for a cache key.
    
    Args:
        key: Original key
        length: Hash length
        
    Returns:
        str: Hashed key
    """
    return hashlib.md5(key.encode()).hexdigest()[:length]


def validate_cache_key(key: str) -> bool:
    """
    Validate a cache key format.
    
    Args:
        key: Cache key to validate
        
    Returns:
        bool: True if valid
    """
    if not key or not isinstance(key, str):
        return False
    
    # Check for invalid characters
    invalid_chars = [' ', '\n', '\r', '\t', '\0']
    if any(char in key for char in invalid_chars):
        return False
    
    # Check length
    if len(key) > 250:  # Redis key length limit
        return False
    
    return True


def serialize_value(value: Any, compression_threshold: int = 1024) -> bytes:
    """
    Serialize a value for caching.
    
    Args:
        value: Value to serialize
        compression_threshold: Minimum size to enable compression
        
    Returns:
        bytes: Serialized value
    """
    try:
        # Serialize to JSON
        json_data = json.dumps(value, default=str).encode('utf-8')
        
        # Compress if above threshold
        if len(json_data) > compression_threshold:
            compressed_data = zlib.compress(json_data)
            return b'compressed:' + compressed_data
        else:
            return b'json:' + json_data
            
    except Exception as e:
        logger.error(f"Error serializing value: {e}")
        # Fallback to string representation
        return b'str:' + str(value).encode('utf-8')


def deserialize_value(data: bytes) -> Any:
    """
    Deserialize a value from cache.
    
    Args:
        data: Serialized data
        
    Returns:
        Any: Deserialized value
    """
    try:
        if data.startswith(b'compressed:'):
            # Decompress and deserialize
            compressed_data = data[11:]  # Remove 'compressed:' prefix
            json_data = zlib.decompress(compressed_data)
            return json.loads(json_data.decode('utf-8'))
        elif data.startswith(b'json:'):
            # Deserialize JSON
            json_data = data[5:]  # Remove 'json:' prefix
            return json.loads(json_data.decode('utf-8'))
        elif data.startswith(b'str:'):
            # Return string value
            return data[4:].decode('utf-8')  # Remove 'str:' prefix
        else:
            # Try to deserialize as JSON (backward compatibility)
            return json.loads(data.decode('utf-8'))
            
    except Exception as e:
        logger.error(f"Error deserializing value: {e}")
        return None


def calculate_compression_ratio(original_size: int, compressed_size: int) -> float:
    """
    Calculate compression ratio.
    
    Args:
        original_size: Original data size
        compressed_size: Compressed data size
        
    Returns:
        float: Compression ratio (0.0 to 1.0)
    """
    if original_size == 0:
        return 0.0
    return 1.0 - (compressed_size / original_size)


def estimate_memory_usage(value: Any) -> int:
    """
    Estimate memory usage of a value.
    
    Args:
        value: Value to estimate
        
    Returns:
        int: Estimated memory usage in bytes
    """
    try:
        if isinstance(value, str):
            return len(value.encode('utf-8'))
        elif isinstance(value, (int, float)):
            return 8  # Approximate size for numbers
        elif isinstance(value, bool):
            return 1
        elif isinstance(value, (list, tuple)):
            return sum(estimate_memory_usage(item) for item in value)
        elif isinstance(value, dict):
            return sum(
                estimate_memory_usage(k) + estimate_memory_usage(v)
                for k, v in value.items()
            )
        else:
            # Fallback to string representation
            return len(str(value).encode('utf-8'))
    except Exception:
        return 0


def format_cache_size(size_bytes: int) -> str:
    """
    Format cache size for display.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        str: Formatted size string
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def format_duration(seconds: float) -> str:
    """
    Format duration for display.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        str: Formatted duration string
    """
    if seconds < 1:
        return f"{seconds * 1000:.1f} ms"
    elif seconds < 60:
        return f"{seconds:.1f} s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds:.1f}s"
    else:
        hours = int(seconds // 3600)
        remaining_minutes = int((seconds % 3600) // 60)
        return f"{hours}h {remaining_minutes}m"


def create_cache_key_info(
    key: str,
    exists: bool = False,
    ttl_seconds: Optional[int] = None,
    size_bytes: int = 0,
    hit_count: int = 0,
    last_accessed: Optional[datetime] = None,
    created_at: Optional[datetime] = None,
    tags: Optional[List[str]] = None
) -> CacheKeyInfo:
    """
    Create cache key information.
    
    Args:
        key: Cache key
        exists: Whether key exists
        ttl_seconds: TTL in seconds
        size_bytes: Size in bytes
        hit_count: Number of hits
        last_accessed: Last access time
        created_at: Creation time
        tags: Associated tags
        
    Returns:
        CacheKeyInfo: Key information
    """
    return CacheKeyInfo(
        key=key,
        exists=exists,
        ttl_seconds=ttl_seconds,
        size_bytes=size_bytes,
        hit_count=hit_count,
        last_accessed=last_accessed,
        created_at=created_at,
        tags=tags or []
    )


def create_cache_tag_info(
    tag: str,
    key_count: int = 0,
    total_size_bytes: int = 0,
    avg_ttl_seconds: float = 0.0,
    last_accessed: Optional[datetime] = None
) -> CacheTagInfo:
    """
    Create cache tag information.
    
    Args:
        tag: Cache tag
        key_count: Number of keys with this tag
        total_size_bytes: Total size of tagged keys
        avg_ttl_seconds: Average TTL of tagged keys
        last_accessed: Last access time
        
    Returns:
        CacheTagInfo: Tag information
    """
    return CacheTagInfo(
        tag=tag,
        key_count=key_count,
        total_size_bytes=total_size_bytes,
        avg_ttl_seconds=avg_ttl_seconds,
        last_accessed=last_accessed
    )


def create_compression_info(
    original_size: int,
    compressed_size: int,
    algorithm: str = "zlib"
) -> CacheCompressionInfo:
    """
    Create compression information.
    
    Args:
        original_size: Original data size
        compressed_size: Compressed data size
        algorithm: Compression algorithm used
        
    Returns:
        CacheCompressionInfo: Compression information
    """
    return CacheCompressionInfo(
        original_size=original_size,
        compressed_size=compressed_size,
        compression_ratio=calculate_compression_ratio(original_size, compressed_size),
        algorithm=algorithm,
        compressed=compressed_size < original_size
    )


def create_eviction_info(
    evicted_keys: List[str],
    reason: str,
    strategy: CacheStrategy,
    memory_freed_bytes: int = 0
) -> CacheEvictionInfo:
    """
    Create eviction information.
    
    Args:
        evicted_keys: List of evicted keys
        reason: Reason for eviction
        strategy: Cache strategy used
        memory_freed_bytes: Memory freed in bytes
        
    Returns:
        CacheEvictionInfo: Eviction information
    """
    return CacheEvictionInfo(
        evicted_keys=evicted_keys,
        reason=reason,
        strategy=strategy,
        memory_freed_bytes=memory_freed_bytes
    )


def create_operation_result(
    success: bool,
    key: str,
    operation: str,
    execution_time_ms: float,
    error: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> CacheOperationResult:
    """
    Create operation result.
    
    Args:
        success: Whether operation was successful
        key: Cache key
        operation: Operation type
        execution_time_ms: Execution time in milliseconds
        error: Error message if failed
        metadata: Additional metadata
        
    Returns:
        CacheOperationResult: Operation result
    """
    return CacheOperationResult(
        success=success,
        key=key,
        operation=operation,
        execution_time_ms=execution_time_ms,
        error=error,
        metadata=metadata or {}
    )


def create_batch_result(
    operation: str,
    total_keys: int,
    successful_keys: int,
    failed_keys: int,
    execution_time_ms: float,
    results: List[CacheOperationResult],
    errors: List[str]
) -> CacheBatchResult:
    """
    Create batch operation result.
    
    Args:
        operation: Operation type
        total_keys: Total number of keys
        successful_keys: Number of successful operations
        failed_keys: Number of failed operations
        execution_time_ms: Execution time in milliseconds
        results: Individual operation results
        errors: Error messages
        
    Returns:
        CacheBatchResult: Batch result
    """
    return CacheBatchResult(
        operation=operation,
        total_keys=total_keys,
        successful_keys=successful_keys,
        failed_keys=failed_keys,
        execution_time_ms=execution_time_ms,
        results=results,
        errors=errors
    )


def calculate_hit_rate(hits: int, misses: int) -> float:
    """
    Calculate cache hit rate.
    
    Args:
        hits: Number of hits
        misses: Number of misses
        
    Returns:
        float: Hit rate (0.0 to 1.0)
    """
    total = hits + misses
    return hits / total if total > 0 else 0.0


def calculate_miss_rate(hits: int, misses: int) -> float:
    """
    Calculate cache miss rate.
    
    Args:
        hits: Number of hits
        misses: Number of misses
        
    Returns:
        float: Miss rate (0.0 to 1.0)
    """
    return 1.0 - calculate_hit_rate(hits, misses)


def format_percentage(value: float, decimals: int = 1) -> str:
    """
    Format percentage for display.
    
    Args:
        value: Value to format (0.0 to 1.0)
        decimals: Number of decimal places
        
    Returns:
        str: Formatted percentage
    """
    return f"{value * 100:.{decimals}f}%"


def validate_ttl(ttl_seconds: int) -> bool:
    """
    Validate TTL value.
    
    Args:
        ttl_seconds: TTL in seconds
        
    Returns:
        bool: True if valid
    """
    return isinstance(ttl_seconds, int) and ttl_seconds > 0


def validate_cache_tags(tags: List[str]) -> bool:
    """
    Validate cache tags.
    
    Args:
        tags: List of tags
        
    Returns:
        bool: True if valid
    """
    if not isinstance(tags, list):
        return False
    
    for tag in tags:
        if not isinstance(tag, str) or not tag.strip():
            return False
    
    return True


def create_error_message(error_code: str, details: Optional[str] = None) -> str:
    """
    Create error message from error code.
    
    Args:
        error_code: Error code
        details: Additional details
        
    Returns:
        str: Error message
    """
    base_message = CACHE_ERROR_CODES.get(error_code, "Unknown error")
    if details:
        return f"{base_message}: {details}"
    return base_message


def measure_execution_time(func: Callable) -> Callable:
    """
    Decorator to measure function execution time.
    
    Args:
        func: Function to measure
        
    Returns:
        Callable: Decorated function
    """
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            return result, execution_time
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            raise e
    return wrapper


def get_cache_strategy_config(strategy: CacheStrategy) -> Dict[str, Any]:
    """
    Get configuration for a cache strategy.
    
    Args:
        strategy: Cache strategy
        
    Returns:
        Dict: Strategy configuration
    """
    from .models import CACHE_STRATEGY_CONFIGS
    config = CACHE_STRATEGY_CONFIGS.get(strategy)
    return config.dict() if config else {}


def format_cache_stats(stats: CacheStats) -> Dict[str, str]:
    """
    Format cache statistics for display.
    
    Args:
        stats: Cache statistics
        
    Returns:
        Dict: Formatted statistics
    """
    return {
        "hits": f"{stats.hits:,}",
        "misses": f"{stats.misses:,}",
        "hit_rate": format_percentage(stats.hit_rate),
        "miss_rate": format_percentage(calculate_miss_rate(stats.hits, stats.misses)),
        "sets": f"{stats.sets:,}",
        "deletes": f"{stats.deletes:,}",
        "evictions": f"{stats.evictions:,}",
        "expirations": f"{stats.expirations:,}",
        "uptime": format_duration(stats.uptime)
    }


