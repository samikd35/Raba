"""
Performance Optimizer for Problem Generator

This module provides caching, connection pooling, and other performance
optimizations for the problem generation workflow.
"""

import asyncio
import hashlib
import json
import time
from typing import Dict, Any, Optional, List
from functools import wraps
from datetime import datetime, timedelta

import redis
from fastapi import HTTPException

from .logging_config import get_contextual_logger

# Initialize logger
logger = get_contextual_logger("pgen.performance")

class CacheManager:
    """Manages caching for problem generation results and intermediate data."""
    
    def __init__(self, redis_url: str = None):
        """Initialize cache manager with Redis connection."""
        self.redis_client = None
        self.memory_cache = {}  # Fallback in-memory cache
        self.cache_ttl = {
            'problem_results': 3600,  # 1 hour
            'user_analytics': 1800,   # 30 minutes
            'embedding_cache': 7200,  # 2 hours
            'parameter_validation': 600  # 10 minutes
        }
        
        if redis_url:
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                self.redis_client.ping()
                logger.info("Redis cache initialized successfully")
            except Exception as e:
                logger.warning(f"Redis not available, using memory cache: {str(e)}")
    
    def _generate_cache_key(self, prefix: str, data: Dict[str, Any]) -> str:
        """Generate a consistent cache key from data."""
        # Sort the data to ensure consistent keys
        sorted_data = json.dumps(data, sort_keys=True)
        hash_value = hashlib.md5(sorted_data.encode()).hexdigest()
        return f"{prefix}:{hash_value}"
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            if self.redis_client:
                value = self.redis_client.get(key)
                if value:
                    return json.loads(value)
            else:
                # Check memory cache with expiration
                if key in self.memory_cache:
                    cached_item = self.memory_cache[key]
                    if cached_item['expires_at'] > time.time():
                        return cached_item['data']
                    else:
                        del self.memory_cache[key]
            return None
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {str(e)}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set value in cache with TTL."""
        try:
            if self.redis_client:
                ttl = ttl or self.cache_ttl.get('problem_results', 3600)
                return self.redis_client.setex(key, ttl, json.dumps(value))
            else:
                # Memory cache with expiration
                ttl = ttl or self.cache_ttl.get('problem_results', 3600)
                self.memory_cache[key] = {
                    'data': value,
                    'expires_at': time.time() + ttl
                }
                return True
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {str(e)}")
            return False
    
    def cache_problem_results(self, parameters: Dict[str, Any], results: List[Dict[str, Any]]) -> str:
        """Cache problem generation results."""
        cache_key = self._generate_cache_key("problem_results", parameters)
        cached_data = {
            'results': results,
            'generated_at': datetime.utcnow().isoformat(),
            'parameters': parameters
        }
        self.set(cache_key, cached_data, self.cache_ttl['problem_results'])
        return cache_key
    
    def get_cached_problem_results(self, parameters: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """Get cached problem generation results."""
        cache_key = self._generate_cache_key("problem_results", parameters)
        cached_data = self.get(cache_key)
        if cached_data:
            logger.info(f"Cache hit for problem generation: {cache_key}")
            return cached_data['results']
        return None

class ConnectionPoolManager:
    """Manages connection pools for external services."""
    
    def __init__(self):
        """Initialize connection pool manager."""
        self.pools = {}
        self.max_connections = 20
        self.connection_timeout = 30
    
    async def get_http_session(self) -> Any:
        """Get HTTP session with connection pooling."""
        import httpx
        
        if 'http' not in self.pools:
            self.pools['http'] = httpx.AsyncClient(
                limits=httpx.Limits(
                    max_keepalive_connections=self.max_connections,
                    max_connections=self.max_connections * 2
                ),
                timeout=httpx.Timeout(self.connection_timeout)
            )
        
        return self.pools['http']
    
    async def close_pools(self):
        """Close all connection pools."""
        for pool_name, pool in self.pools.items():
            try:
                if hasattr(pool, 'aclose'):
                    await pool.aclose()
                logger.info(f"Closed connection pool: {pool_name}")
            except Exception as e:
                logger.error(f"Error closing pool {pool_name}: {str(e)}")

class RequestOptimizer:
    """Optimizes API requests and responses."""
    
    def __init__(self, cache_manager: CacheManager = None):
        """Initialize request optimizer."""
        self.cache_manager = cache_manager or CacheManager()
        self.connection_manager = ConnectionPoolManager()
        self.request_metrics = {}
    
    def track_request_metrics(self, endpoint: str, duration: float, success: bool):
        """Track request performance metrics."""
        if endpoint not in self.request_metrics:
            self.request_metrics[endpoint] = {
                'total_requests': 0,
                'successful_requests': 0,
                'total_duration': 0,
                'avg_duration': 0,
                'success_rate': 0
            }
        
        metrics = self.request_metrics[endpoint]
        metrics['total_requests'] += 1
        metrics['total_duration'] += duration
        metrics['avg_duration'] = metrics['total_duration'] / metrics['total_requests']
        
        if success:
            metrics['successful_requests'] += 1
        
        metrics['success_rate'] = metrics['successful_requests'] / metrics['total_requests']
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        return {
            'request_metrics': self.request_metrics,
            'cache_stats': self._get_cache_stats(),
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def _get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        if self.cache_manager.redis_client:
            try:
                info = self.cache_manager.redis_client.info()
                return {
                    'type': 'redis',
                    'connected_clients': info.get('connected_clients', 0),
                    'used_memory': info.get('used_memory_human', '0B'),
                    'keyspace_hits': info.get('keyspace_hits', 0),
                    'keyspace_misses': info.get('keyspace_misses', 0)
                }
            except Exception:
                pass
        
        return {
            'type': 'memory',
            'cached_items': len(self.cache_manager.memory_cache),
            'memory_usage': 'unknown'
        }

def performance_monitor(endpoint_name: str = None):
    """Decorator to monitor endpoint performance."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            endpoint = endpoint_name or func.__name__
            success = False
            
            try:
                result = await func(*args, **kwargs)
                success = True
                return result
            except Exception as e:
                logger.error(f"Error in {endpoint}: {str(e)}")
                raise
            finally:
                duration = time.time() - start_time
                # Track metrics (would integrate with monitoring system)
                logger.info(f"Endpoint {endpoint} completed in {duration:.3f}s (success: {success})")
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            endpoint = endpoint_name or func.__name__
            success = False
            
            try:
                result = func(*args, **kwargs)
                success = True
                return result
            except Exception as e:
                logger.error(f"Error in {endpoint}: {str(e)}")
                raise
            finally:
                duration = time.time() - start_time
                logger.info(f"Endpoint {endpoint} completed in {duration:.3f}s (success: {success})")
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

def batch_processor(batch_size: int = 10, max_wait_time: float = 1.0):
    """Decorator to batch process requests for efficiency."""
    def decorator(func):
        request_queue = []
        last_process_time = time.time()
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            nonlocal request_queue, last_process_time
            
            # Add request to queue
            future = asyncio.Future()
            request_queue.append((args, kwargs, future))
            
            # Process batch if conditions are met
            current_time = time.time()
            if (len(request_queue) >= batch_size or 
                current_time - last_process_time >= max_wait_time):
                
                # Process current batch
                batch = request_queue[:]
                request_queue.clear()
                last_process_time = current_time
                
                try:
                    # Process batch (implementation depends on the function)
                    results = await func([item[:2] for item in batch])  # args, kwargs pairs
                    
                    # Return results to futures
                    for i, (_, _, future) in enumerate(batch):
                        if i < len(results):
                            future.set_result(results[i])
                        else:
                            future.set_exception(Exception("Batch processing error"))
                            
                except Exception as e:
                    # Set exception for all futures
                    for _, _, future in batch:
                        future.set_exception(e)
            
            return await future
        
        return wrapper
    return decorator

# Global instances
cache_manager = CacheManager()
request_optimizer = RequestOptimizer(cache_manager)

def get_cache_manager() -> CacheManager:
    """Get the global cache manager instance."""
    return cache_manager

def get_request_optimizer() -> RequestOptimizer:
    """Get the global request optimizer instance."""
    return request_optimizer
