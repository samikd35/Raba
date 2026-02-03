# Cache Module for MINT

This module provides comprehensive caching functionality for the MINT system, including in-memory caching, Redis backend, compression, and intelligent cache management.

## 📁 Module Structure

```
cache/
├── __init__.py              # Module exports and public API
├── models.py               # Pydantic models and data structures
├── core.py                 # Basic in-memory cache implementation
├── enhanced.py             # Advanced cache with Redis backend and compression
├── report.py               # Specialized cache for report history functionality
├── utils.py               # Utility functions and helpers
└── README.md              # This documentation
```

## 🚀 Quick Start

```python
from mint.api.cache import (
    EnhancedCacheService, CacheConfig, CacheStrategy,
    cached, invalidate_by_tag, get_cache_service
)

# Create cache service with custom config
config = CacheConfig(
    default_ttl=3600,
    max_size=1000,
    enable_compression=True,
    backend=CacheBackend.REDIS
)
cache = EnhancedCacheService(config=config)

# Use decorator for automatic caching
@cached(ttl_seconds=300, tags=["reports"])
async def get_report_data(report_id: str):
    # Your expensive operation here
    return expensive_operation(report_id)

# Manual cache operations
await cache.set("key", "value", ttl_seconds=600)
value = await cache.get("key")
await cache.delete("key")
```

## 🔧 Components

### Models (`models.py`)
- **Enums**: `CacheStrategy`, `CacheBackend`, `CacheItemStatus`
- **Core Models**: `CacheItem`, `CacheStats`, `CacheConfig`, `CacheEntry`
- **Advanced Models**: `CacheHealthCheck`, `CachePerformanceReport`, `CacheBatchResult`
- **Constants**: `DEFAULT_TTL_SECONDS`, `CACHE_ERROR_CODES`, `EVICTION_POLICIES`

### Core (`core.py`)
- **AdminCache**: Basic in-memory cache for admin dashboard data
- **Thread-Safe**: RLock-based thread safety
- **Tag Support**: Cache invalidation by tags
- **Statistics**: Hit/miss ratio tracking
- **Automatic Cleanup**: Background cleanup thread

### Enhanced (`enhanced.py`)
- **EnhancedCacheService**: Advanced cache with Redis backend
- **Compression**: Automatic compression for large values
- **Fallback**: Falls back to in-memory cache if Redis unavailable
- **Statistics**: Comprehensive performance metrics
- **Decorators**: `@cached` decorator for automatic caching

### Report (`report.py`)
- **ReportCacheManager**: Specialized cache for report history
- **Cache Strategies**: Aggressive, balanced, and conservative strategies
- **Cache Warming**: Intelligent cache warming for frequently accessed data
- **Performance Monitoring**: Detailed performance metrics and reporting
- **Circuit Breaker**: Integration with circuit breaker pattern

### Utils (`utils.py`)
- **Key Generation**: Smart cache key generation and validation
- **Serialization**: JSON serialization with compression support
- **Memory Management**: Memory usage estimation and formatting
- **Performance**: Execution time measurement and formatting
- **Information**: Helper functions for creating cache information objects

## 🎯 Usage Examples

### Basic Caching
```python
from mint.api.cache import EnhancedCacheService, CacheConfig

# Create cache service
cache = EnhancedCacheService(
    default_ttl=3600,
    max_memory_size=100 * 1024 * 1024,  # 100MB
    enable_compression=True
)

# Basic operations
await cache.set("user:123", {"name": "John", "email": "john@example.com"})
user_data = await cache.get("user:123")
await cache.delete("user:123")

# With tags for invalidation
await cache.set(
    "report:456", 
    report_data, 
    ttl_seconds=1800,
    tags=["reports", "user:123"]
)
```

### Decorator-Based Caching
```python
from mint.api.cache import cached, invalidate_by_tag

@cached(ttl_seconds=300, tags=["reports"])
async def get_report_summary(report_id: str):
    # Expensive database operation
    return await database.get_report_summary(report_id)

@cached(ttl_seconds=600, key_prefix="user_stats")
async def get_user_statistics(user_id: str):
    # Expensive calculation
    return await calculate_user_stats(user_id)

# Invalidate cache by tag
await invalidate_by_tag("reports")
```

### Advanced Cache Management
```python
from mint.api.cache import ReportCacheManager, CacheStrategy

# Create report cache manager
report_cache = ReportCacheManager(
    strategy=CacheStrategy.BALANCED,
    max_size=500,
    warming_enabled=True
)

# Cache warming
await report_cache.warm_cache([
    "report:123",
    "report:456",
    "report:789"
])

# Get cache statistics
stats = report_cache.get_statistics()
print(f"Hit rate: {stats.hit_rate:.2%}")
print(f"Memory usage: {stats.memory_usage_mb:.1f} MB")

# Performance report
report = await report_cache.get_performance_report(
    start_time=datetime.now() - timedelta(hours=1),
    end_time=datetime.now()
)
```

### Batch Operations
```python
from mint.api.cache import EnhancedCacheService

cache = EnhancedCacheService()

# Batch set operations
keys = [f"item:{i}" for i in range(100)]
values = [{"id": i, "data": f"data_{i}"} for i in range(100)]
await cache.batch_set(keys, values, ttl_seconds=3600)

# Batch get operations
results = await cache.batch_get(keys)
for key, value in results.items():
    print(f"{key}: {value}")

# Batch delete operations
await cache.batch_delete(keys)
```

### Cache Health Monitoring
```python
from mint.api.cache import get_cache_service

cache = get_cache_service()

# Health check
health = await cache.health_check()
if health.healthy:
    print("Cache is healthy")
    print(f"Hit rate: {health.stats.hit_rate:.2%}")
else:
    print(f"Cache issues: {health.errors}")

# Performance metrics
metrics = cache.get_metrics()
print(f"Total entries: {metrics.total_entries}")
print(f"Memory usage: {metrics.memory_usage_percent:.1f}%")
print(f"Average response time: {metrics.avg_response_time_ms:.2f}ms")
```

## 🔒 Key Features

### Multiple Backends
- **In-Memory**: Fast local caching with thread safety
- **Redis**: Distributed caching with persistence
- **Hybrid**: Automatic fallback between backends

### Compression
- **Automatic**: Compresses large values automatically
- **Configurable**: Adjustable compression threshold
- **Multiple Algorithms**: Support for zlib, gzip, lz4, brotli

### Cache Strategies
- **Aggressive**: Cache everything for maximum performance
- **Balanced**: Cache frequently accessed items
- **Conservative**: Cache only critical items

### Advanced Features
- **Tag-Based Invalidation**: Invalidate cache entries by tags
- **TTL Management**: Flexible time-to-live configuration
- **Statistics Tracking**: Comprehensive performance metrics
- **Health Monitoring**: Real-time cache health checks
- **Circuit Breaker**: Integration with circuit breaker pattern

### Performance Optimization
- **Memory Management**: Intelligent memory usage tracking
- **Eviction Policies**: LRU, LFU, TTL-based eviction
- **Batch Operations**: Efficient batch get/set/delete operations
- **Compression**: Automatic compression for large values

## 📊 Configuration

### Cache Configuration
```python
from mint.api.cache import CacheConfig, CacheBackend

config = CacheConfig(
    default_ttl=3600,                    # 1 hour default TTL
    max_size=1000,                       # Maximum cache entries
    max_memory_size=100 * 1024 * 1024,  # 100MB memory limit
    cleanup_interval=60,                 # 60 seconds cleanup interval
    compression_threshold=1024,          # Compress data > 1KB
    key_prefix="mint_cache:",            # Key prefix
    enable_stats=True,                   # Enable statistics
    enable_compression=True,             # Enable compression
    backend=CacheBackend.REDIS,          # Use Redis backend
    redis_url="redis://localhost:6379"   # Redis connection URL
)
```

### Environment Variables
```bash
# Cache Configuration
CACHE_DEFAULT_TTL=3600
CACHE_MAX_SIZE=1000
CACHE_MAX_MEMORY_SIZE=104857600
CACHE_CLEANUP_INTERVAL=60
CACHE_COMPRESSION_THRESHOLD=1024
CACHE_KEY_PREFIX=mint_cache:
CACHE_ENABLE_STATS=true
CACHE_ENABLE_COMPRESSION=true
CACHE_BACKEND=redis
REDIS_URL=redis://localhost:6379
```

## 🛠️ Advanced Usage

### Custom Cache Strategies
```python
from mint.api.cache import CacheStrategyConfig, CacheStrategy

# Create custom strategy
custom_strategy = CacheStrategyConfig(
    strategy=CacheStrategy.BALANCED,
    ttl_multiplier=1.5,
    priority=2,
    max_size=300,
    tags=["custom", "high_priority"]
)

# Apply strategy to cache operations
await cache.set_with_strategy(
    "custom_key", 
    "custom_value", 
    strategy=custom_strategy
)
```

### Cache Warming
```python
from mint.api.cache import CacheWarmingRequest

# Create warming request
warming_request = CacheWarmingRequest(
    keys=["report:123", "user:456", "stats:789"],
    strategy=CacheStrategy.AGGRESSIVE,
    priority=1,
    ttl_seconds=7200
)

# Execute warming
await cache.warm_cache(warming_request)
```

### Performance Monitoring
```python
from mint.api.cache import get_cache_service

cache = get_cache_service()

# Get detailed performance report
report = await cache.get_performance_report(
    start_time=datetime.now() - timedelta(hours=24),
    end_time=datetime.now()
)

print("Performance Report:")
print(f"Total requests: {report.total_requests}")
print(f"Hit rate: {report.hit_rate:.2%}")
print(f"Average response time: {report.avg_response_time_ms:.2f}ms")
print(f"Memory usage: {report.memory_usage}")

# Top keys by access
for key_info in report.top_keys[:10]:
    print(f"{key_info.key}: {key_info.hit_count} hits")
```

## 📝 Best Practices

### Cache Key Design
- **Use consistent prefixes**: `user:123`, `report:456`
- **Include version information**: `v1:user:123`
- **Use descriptive names**: `user_profile:123` not `up:123`
- **Avoid special characters**: Use underscores or colons

### TTL Management
- **Set appropriate TTLs**: Balance freshness vs performance
- **Use different TTLs for different data types**: Static data can have longer TTLs
- **Consider data update frequency**: Frequently updated data needs shorter TTLs

### Memory Management
- **Monitor memory usage**: Use cache metrics to track memory consumption
- **Set appropriate limits**: Configure max_size and max_memory_size
- **Use eviction policies**: Choose appropriate eviction strategy

### Error Handling
- **Handle cache failures gracefully**: Don't let cache failures break your application
- **Use fallback mechanisms**: Fall back to database when cache is unavailable
- **Monitor cache health**: Use health checks to detect issues early

### Performance Optimization
- **Use batch operations**: Batch get/set/delete operations when possible
- **Enable compression**: Use compression for large values
- **Choose appropriate strategies**: Use aggressive caching for static data
- **Monitor hit rates**: Aim for high hit rates (80%+)

## 🔍 Troubleshooting

### Common Issues
- **Low hit rate**: Check TTL settings and cache key patterns
- **High memory usage**: Reduce max_size or enable compression
- **Redis connection issues**: Check Redis configuration and connectivity
- **Serialization errors**: Ensure data is JSON-serializable

### Debugging
- **Enable detailed logging**: Set logging level to DEBUG
- **Check cache statistics**: Monitor hit rates and memory usage
- **Use health checks**: Regular health checks to detect issues
- **Review performance reports**: Analyze performance trends

## 📚 Notes

- This module follows the single responsibility principle
- Each component has a clear, focused purpose
- Performance is optimized for high-throughput scenarios
- Monitoring is built-in and comprehensive
- Modular design allows for easy testing and maintenance
- Production-ready with comprehensive error handling
- Backward compatibility maintained for existing integrations


