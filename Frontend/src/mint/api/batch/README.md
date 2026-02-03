# Batch Processing Module for MINT

This module provides comprehensive batch processing functionality for database operations, including batch operations, monitoring, and performance optimization.

## 📁 Module Structure

```
batch/
├── __init__.py              # Module exports and public API
├── models.py               # Pydantic models and data structures
├── processor.py            # Main batch processor implementation
├── operations.py           # Batch operation handlers
├── monitoring.py           # Batch processing monitoring and health checks
├── utils.py               # Utility functions and helpers
└── README.md              # This documentation
```

## 🚀 Quick Start

```python
from mint.api.batch import (
    BatchProcessor, BatchOperationType, BatchProcessorConfig,
    batch_insert, batch_update, batch_delete
)

# Create batch processor with custom config
config = BatchProcessorConfig(
    batch_size=50,
    max_wait_time=3.0,
    max_queue_size=500
)
processor = BatchProcessor(config=config)

# Add operations
future = processor.add_operation(
    BatchOperationType.INSERT,
    "users",
    {"name": "John Doe", "email": "john@example.com"},
    priority=1
)

# Wait for result
result = await future
print(f"Operation successful: {result.success}")
```

## 🔧 Components

### Models (`models.py`)
- **Enums**: `BatchOperationType`, `BatchStatus`, `BatchPriority`
- **Core Models**: `BatchOperation`, `BatchResult`, `BatchOperationRequest`, `BatchOperationResponse`
- **Config Models**: `BatchProcessorConfig`, `BatchRetryConfig`
- **Monitoring Models**: `BatchStatistics`, `BatchHealthCheck`, `BatchProcessingMetrics`
- **Constants**: `DEFAULT_BATCH_SIZE`, `BATCH_ERROR_CODES`, `PRIORITY_LEVELS`

### Processor (`processor.py`)
- **Main Processor**: `BatchProcessor` class for managing batch operations
- **Global Instance**: `get_batch_processor()` for singleton access
- **Convenience Functions**: `batch_insert()`, `batch_update()`, `batch_delete()`
- **Queue Management**: Automatic batching and processing
- **Statistics Tracking**: Comprehensive performance metrics

### Operations (`operations.py`)
- **Operation Handler**: `BatchOperationHandler` for processing operations
- **Operation Types**: Insert, update, delete, and upsert operations
- **Validation**: Operation data validation and error handling
- **Grouping**: Operations grouped by table and type for efficiency
- **Retry Logic**: Automatic retry with exponential backoff

### Monitoring (`monitoring.py`)
- **Batch Monitor**: `BatchMonitor` for tracking performance
- **Health Checks**: Comprehensive health monitoring
- **Metrics Collection**: Performance and error metrics
- **Alerting**: Configurable alert thresholds
- **Dashboard Data**: Formatted data for monitoring dashboards

### Utils (`utils.py`)
- **ID Generation**: Unique operation ID generation
- **Validation**: Data and configuration validation
- **Formatting**: Result and statistics formatting
- **Calculations**: Batch size and processing time estimation
- **Grouping**: Operation grouping and sorting utilities

## 🎯 Usage Examples

### Basic Batch Operations
```python
from mint.api.batch import batch_insert, batch_update, batch_delete

# Batch insert
data = [
    {"name": "User 1", "email": "user1@example.com"},
    {"name": "User 2", "email": "user2@example.com"}
]
results = await batch_insert("users", data)

# Batch update
result = await batch_update(
    "users",
    {"status": "active"},
    {"id": 123}
)

# Batch delete
result = await batch_delete("users", {"status": "inactive"})
```

### Advanced Batch Processing
```python
from mint.api.batch import BatchProcessor, BatchProcessorConfig, BatchOperationType

# Create processor with custom configuration
config = BatchProcessorConfig(
    batch_size=100,
    max_wait_time=5.0,
    max_queue_size=1000,
    max_retries=3
)
processor = BatchProcessor(config=config)

# Add multiple operations
futures = []
for i in range(1000):
    future = processor.add_operation(
        BatchOperationType.INSERT,
        "logs",
        {"message": f"Log entry {i}", "timestamp": datetime.now()},
        priority=i % 3  # Varying priorities
    )
    futures.append(future)

# Wait for all operations to complete
results = await asyncio.gather(*futures)
successful = sum(1 for r in results if r.success)
print(f"Successfully processed {successful} operations")
```

### Monitoring and Health Checks
```python
from mint.api.batch import get_batch_processor

# Get global processor instance
processor = get_batch_processor()

# Get statistics
stats = processor.get_stats()
print(f"Total operations: {stats.total_operations}")
print(f"Success rate: {stats.success_rate:.1f}%")
print(f"Average processing time: {stats.avg_processing_time:.3f}s")

# Perform health check
health = await processor.health_check()
if health.healthy:
    print("Batch processor is healthy")
else:
    print(f"Health issues: {health.errors}")
```

### Custom Operation Handling
```python
from mint.api.batch import BatchOperationHandler, BatchOperationType

# Create operation handler
handler = BatchOperationHandler(supabase_client)

# Process operations
operations = [
    BatchOperation(
        operation_type=BatchOperationType.INSERT,
        table_name="users",
        data={"name": "John", "email": "john@example.com"}
    )
]

results = await handler.process_operation_group(operations)
for result in results:
    print(f"Operation {result.operation_id}: {'Success' if result.success else 'Failed'}")
```

## 🔒 Key Features

### Performance Optimization
- **Batch Processing**: Groups operations for efficient database access
- **Priority Queuing**: High-priority operations processed first
- **Configurable Batching**: Adjustable batch sizes and timeouts
- **Automatic Flushing**: Processes batches when full or timeout reached

### Error Handling
- **Retry Logic**: Automatic retry with exponential backoff
- **Error Tracking**: Comprehensive error logging and monitoring
- **Graceful Degradation**: Continues processing even if some operations fail
- **Detailed Error Information**: Rich error context and debugging

### Monitoring and Observability
- **Real-time Statistics**: Live performance metrics
- **Health Checks**: Comprehensive system health monitoring
- **Alerting**: Configurable thresholds and notifications
- **Dashboard Integration**: Formatted data for monitoring dashboards

### Scalability
- **Queue Management**: Efficient operation queuing and processing
- **Memory Management**: Configurable queue size limits
- **Concurrent Processing**: Async operation processing
- **Resource Optimization**: Minimal memory and CPU usage

## 📊 Configuration

### Batch Processor Configuration
```python
from mint.api.batch import BatchProcessorConfig

config = BatchProcessorConfig(
    batch_size=100,              # Operations per batch
    max_wait_time=5.0,           # Max wait time in seconds
    max_queue_size=1000,         # Max operations in queue
    max_retries=3,               # Max retry attempts
    retry_delay=1.0,             # Base retry delay
    enable_monitoring=True,      # Enable monitoring
    enable_caching=True          # Enable caching
)
```

### Environment Variables
```bash
# Batch Processing Configuration
BATCH_SIZE=100
MAX_WAIT_TIME=5.0
MAX_QUEUE_SIZE=1000
MAX_RETRIES=3
RETRY_DELAY=1.0
ENABLE_MONITORING=true
ENABLE_CACHING=true
```

## 🛠️ Advanced Usage

### Custom Operation Types
```python
from mint.api.batch import BatchOperation, BatchOperationType

# Create custom operation
operation = BatchOperation(
    operation_type=BatchOperationType.UPSERT,
    table_name="products",
    data={"id": 123, "name": "Product", "price": 29.99},
    filters={"id": 123},
    priority=2
)

# Add to processor
future = processor.add_operation(
    operation.operation_type,
    operation.table_name,
    operation.data,
    operation.filters,
    operation.priority
)
```

### Monitoring Dashboard
```python
from mint.api.batch import get_batch_processor

processor = get_batch_processor()
monitor = processor.monitor

# Get dashboard data
dashboard_data = monitor.get_monitoring_dashboard_data()

print("Batch Processing Dashboard:")
print(f"Total Operations: {dashboard_data['summary']['total_operations']}")
print(f"Success Rate: {dashboard_data['summary']['success_rate']:.1f}%")
print(f"Average Processing Time: {dashboard_data['summary']['avg_processing_time']:.3f}s")
print(f"Trend: {dashboard_data['summary']['trend']}")
```

### Error Analysis
```python
from mint.api.batch import get_batch_processor

processor = get_batch_processor()
monitor = processor.monitor

# Get error summary
error_summary = monitor.get_error_summary(hours=24)
print("Error Summary (Last 24 hours):")
for error_code, count in error_summary.items():
    print(f"  {error_code}: {count}")

# Get performance trends
trends = monitor.get_performance_trends(hours=24)
print(f"Performance Trend: {trends['trend']}")
print(f"Average Processing Time: {trends['avg_processing_time']:.3f}s")
```

## 📝 Best Practices

### Operation Batching
- **Group Similar Operations**: Batch operations of the same type and table
- **Use Appropriate Batch Sizes**: Balance between performance and memory usage
- **Set Proper Priorities**: Use priority levels to ensure important operations are processed first
- **Monitor Queue Sizes**: Keep an eye on queue sizes to prevent memory issues

### Error Handling
- **Implement Retry Logic**: Use the built-in retry mechanism for transient failures
- **Log Errors**: Ensure all errors are properly logged for debugging
- **Handle Failures Gracefully**: Don't let individual operation failures stop the entire batch
- **Monitor Error Rates**: Track error rates and investigate patterns

### Performance Optimization
- **Tune Configuration**: Adjust batch sizes and timeouts based on your workload
- **Monitor Performance**: Use the built-in monitoring to track performance
- **Optimize Data**: Ensure data is properly formatted and validated
- **Use Appropriate Priorities**: Set priorities based on business requirements

### Monitoring and Alerting
- **Set Up Health Checks**: Implement regular health checks
- **Configure Alerts**: Set up alerts for critical thresholds
- **Track Metrics**: Monitor key performance indicators
- **Regular Reviews**: Review performance metrics regularly

## 🔍 Troubleshooting

### Common Issues
- **Queue Full**: Increase `max_queue_size` or process operations faster
- **High Error Rate**: Check data validation and database connectivity
- **Slow Processing**: Optimize batch sizes and check database performance
- **Memory Issues**: Reduce queue sizes or batch sizes

### Debugging
- **Enable Logging**: Set appropriate logging levels
- **Check Health**: Use health checks to identify issues
- **Monitor Metrics**: Track performance metrics over time
- **Review Errors**: Analyze error patterns and causes

## 📚 Notes

- This module follows the single responsibility principle
- Each component has a clear, focused purpose
- Performance is optimized for high-throughput scenarios
- Monitoring is built-in and comprehensive
- Modular design allows for easy testing and maintenance
- Production-ready with comprehensive error handling
- Backward compatibility maintained for existing integrations


