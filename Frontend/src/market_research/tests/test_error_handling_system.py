"""
Tests for Comprehensive Error Handling System

Test suite for error handling, monitoring, and recovery mechanisms
in the market research analysis system.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from typing import Dict, Any, List

from ..utils.error_handling import (
    ErrorHandlingService,
    ErrorMonitor,
    PerformanceMonitor,
    ResourceMonitor,
    ErrorCategory,
    ErrorSeverity,
    DocumentProcessingError,
    AIServiceError,
    FactValidationError,
    StatisticsRegistryError,
    handle_fact_validation_errors,
    handle_statistics_registry_errors,
    retry_with_exponential_backoff,
    error_monitor,
    performance_monitor,
    resource_monitor
)


class TestErrorHandlingService:
    """Test suite for ErrorHandlingService"""
    
    @pytest.fixture
    def error_service(self):
        """Create error handling service instance"""
        return ErrorHandlingService()
    
    @pytest.mark.asyncio
    async def test_handle_context_building_error(self, error_service):
        """Test handling of context building errors"""
        error = Exception("Statistics registry unavailable")
        context = {"project_id": "test_project", "analysis_type": "pain"}
        
        fallback_context = await error_service.handle_context_building_error(error, context)
        
        # Should return fallback context
        assert isinstance(fallback_context, str)
        assert "STATISTICS UNAVAILABLE" in fallback_context
        assert "qualitative analysis only" in fallback_context.lower()
    
    @pytest.mark.asyncio
    async def test_handle_evidence_retrieval_error(self, error_service):
        """Test handling of evidence retrieval errors"""
        error = Exception("Vector search failed")
        context = {"query": "test query", "project_id": "test_project"}
        
        fallback_evidence = await error_service.handle_evidence_retrieval_error(error, context)
        
        # Should return fallback evidence list
        assert isinstance(fallback_evidence, list)
        assert len(fallback_evidence) >= 1
        assert fallback_evidence[0]["error_fallback"] is True
        assert fallback_evidence[0]["source_type"] == "system"
    
    @pytest.mark.asyncio
    async def test_handle_statistics_extraction_error(self, error_service):
        """Test handling of statistics extraction errors"""
        error = Exception("CSV parsing failed")
        file_info = {"filename": "test.csv", "size": 1024}
        
        fallback_stats = await error_service.handle_statistics_extraction_error(error, file_info)
        
        # Should return minimal statistics structure
        assert isinstance(fallback_stats, dict)
        assert "metadata" in fallback_stats
        assert fallback_stats["metadata"]["extraction_failed"] is True
        assert "categorical_distributions" in fallback_stats
        assert "citation_registry" in fallback_stats
    
    @pytest.mark.asyncio
    async def test_handle_fact_validation_error(self, error_service):
        """Test handling of fact validation errors"""
        error = FactValidationError("Claim extraction failed")
        ai_response = "72% of users are satisfied"
        context = {"analysis_type": "satisfaction"}
        
        fallback_validation = await error_service.handle_fact_validation_error(
            error, ai_response, context
        )
        
        # Should return fallback validation results
        assert isinstance(fallback_validation, dict)
        assert fallback_validation["fact_check_score"] == 0.5  # Neutral score
        assert fallback_validation["validation_method"] == "error_fallback"
        assert "error" in fallback_validation
    
    @pytest.mark.asyncio
    async def test_handle_statistics_registry_error(self, error_service):
        """Test handling of statistics registry errors"""
        error = StatisticsRegistryError("Database connection failed")
        project_id = "test_project"
        analysis_type = "pain"
        context = {"tenant_id": "test_tenant"}
        
        fallback_registry = await error_service.handle_statistics_registry_error(
            error, project_id, analysis_type, context
        )
        
        # Should return empty registry structure
        assert isinstance(fallback_registry, dict)
        assert "csv_statistics" in fallback_registry
        assert "pdf_statistics" in fallback_registry
        assert fallback_registry["fallback_used"] is True
        assert "error" in fallback_registry
    
    @pytest.mark.asyncio
    async def test_handle_ai_service_unavailable(self, error_service):
        """Test handling of AI service unavailability"""
        error = AIServiceError("Service timeout")
        context = {
            "analysis_type": "pain",
            "assumption": {"text": "Users need better pricing"}
        }
        
        fallback_response = await error_service.handle_ai_service_unavailable(error, context)
        
        # Should return fallback AI response
        assert isinstance(fallback_response, dict)
        assert fallback_response["fallback"] is True
        assert "content" in fallback_response
        
        # Content should be valid JSON
        import json
        content = json.loads(fallback_response["content"])
        assert "claim" in content
        assert content["accuracy_level"] == "low"
        assert content["confidence_score"] == 0.0
    
    def test_detect_failure_patterns(self, error_service):
        """Test detection of systematic failure patterns"""
        # Create mock error history with patterns
        error_history = [
            {
                "timestamp": datetime.utcnow().isoformat(),
                "error_type": "ConnectionError",
                "category": "ai_service"
            },
            {
                "timestamp": datetime.utcnow().isoformat(),
                "error_type": "ConnectionError",
                "category": "ai_service"
            },
            {
                "timestamp": datetime.utcnow().isoformat(),
                "error_type": "ConnectionError",
                "category": "ai_service"
            },
            {
                "timestamp": datetime.utcnow().isoformat(),
                "error_type": "ConnectionError",
                "category": "ai_service"
            },
            {
                "timestamp": datetime.utcnow().isoformat(),
                "error_type": "ConnectionError",
                "category": "ai_service"
            }
        ]
        
        patterns = error_service.detect_failure_patterns(error_history)
        
        # Should detect recurring errors
        assert "recurring_errors" in patterns
        assert "ai_service_ConnectionError" in patterns["recurring_errors"]
        assert patterns["recurring_errors"]["ai_service_ConnectionError"] == 5
        
        # Should provide recommendations
        assert "recommendations" in patterns
        assert len(patterns["recommendations"]) > 0
    
    @pytest.mark.asyncio
    async def test_implement_recovery_strategy(self, error_service):
        """Test implementation of recovery strategies"""
        # Test statistics extraction recovery
        context = {
            "file_info": {
                "file_type": "csv",
                "filename": "test.csv"
            }
        }
        
        recovery_result = await error_service.implement_recovery_strategy(
            "statistics_extraction_failed", context
        )
        
        assert recovery_result["recovery_attempted"] is True
        assert "alternative_methods_tried" in recovery_result
        assert "utf-8_encoding" in recovery_result["alternative_methods_tried"]
        
        # Test AI service timeout recovery
        recovery_result = await error_service.implement_recovery_strategy(
            "ai_service_timeout", {}
        )
        
        assert recovery_result["retry_recommended"] is True
        assert "retry_delay_seconds" in recovery_result


class TestErrorMonitor:
    """Test suite for ErrorMonitor"""
    
    @pytest.fixture
    def monitor(self):
        """Create fresh error monitor instance"""
        return ErrorMonitor()
    
    def test_record_error(self, monitor):
        """Test error recording functionality"""
        error = Exception("Test error")
        context = {"test_key": "test_value"}
        
        monitor.record_error(error, ErrorCategory.AI_SERVICE, ErrorSeverity.HIGH, context)
        
        # Should record error in history
        assert len(monitor.error_history) == 1
        
        error_record = monitor.error_history[0]
        assert error_record["error_type"] == "Exception"
        assert error_record["message"] == "Test error"
        assert error_record["category"] == "ai_service"
        assert error_record["severity"] == "high"
        assert error_record["context"] == context
    
    def test_error_count_tracking(self, monitor):
        """Test error count tracking and cleanup"""
        error = Exception("Test error")
        
        # Record multiple errors
        for _ in range(3):
            monitor.record_error(error, ErrorCategory.AI_SERVICE, ErrorSeverity.HIGH)
        
        # Should track counts
        key = "ai_service_high"
        assert key in monitor.error_counts
        assert len(monitor.error_counts[key]) == 3
    
    def test_alert_threshold_detection(self, monitor):
        """Test alert threshold detection"""
        error = Exception("Test error")
        
        # Set low threshold for testing
        monitor.alert_thresholds[ErrorCategory.AI_SERVICE] = {"count": 2, "window": 300}
        
        with patch.object(monitor, '_trigger_alert') as mock_alert:
            # Record errors to exceed threshold
            for _ in range(3):
                monitor.record_error(error, ErrorCategory.AI_SERVICE, ErrorSeverity.HIGH)
            
            # Should trigger alert
            mock_alert.assert_called()
    
    def test_get_error_summary(self, monitor):
        """Test error summary generation"""
        # Record various errors
        errors = [
            (Exception("Error 1"), ErrorCategory.AI_SERVICE, ErrorSeverity.HIGH),
            (Exception("Error 2"), ErrorCategory.DATABASE, ErrorSeverity.MEDIUM),
            (Exception("Error 3"), ErrorCategory.AI_SERVICE, ErrorSeverity.LOW)
        ]
        
        for error, category, severity in errors:
            monitor.record_error(error, category, severity)
        
        summary = monitor.get_error_summary(hours=1)
        
        # Should provide comprehensive summary
        assert summary["total_errors"] == 3
        assert "by_category" in summary
        assert "by_severity" in summary
        assert summary["by_category"]["ai_service"] == 2
        assert summary["by_category"]["database"] == 1
        assert summary["by_severity"]["high"] == 1
        assert summary["by_severity"]["medium"] == 1
        assert summary["by_severity"]["low"] == 1
    
    def test_memory_leak_prevention(self, monitor):
        """Test that error history doesn't grow indefinitely"""
        error = Exception("Test error")
        
        # Record many errors
        for _ in range(100):
            monitor.record_error(error, ErrorCategory.SYSTEM, ErrorSeverity.LOW)
        
        # Simulate time passage by manually setting old timestamps
        old_time = datetime.utcnow() - timedelta(hours=2)
        for record in monitor.error_history[:50]:
            record["timestamp"] = old_time.isoformat()
        
        # Record new error to trigger cleanup
        monitor.record_error(error, ErrorCategory.SYSTEM, ErrorSeverity.LOW)
        
        # Should have cleaned up old entries
        assert len(monitor.error_history) <= 51  # 50 old + 1 new, but old should be cleaned


class TestPerformanceMonitor:
    """Test suite for PerformanceMonitor"""
    
    @pytest.fixture
    def perf_monitor(self):
        """Create performance monitor instance"""
        return PerformanceMonitor()
    
    def test_record_performance(self, perf_monitor):
        """Test performance recording"""
        operation = "test_operation"
        duration = 1.5
        context = {"file_size": 1024}
        
        perf_monitor.record_performance(operation, duration, context)
        
        # Should record in history
        assert len(perf_monitor.performance_history) == 1
        
        record = perf_monitor.performance_history[0]
        assert record["operation"] == operation
        assert record["duration"] == duration
        assert record["context"] == context
        
        # Should update metrics
        assert operation in perf_monitor.metrics
        metrics = perf_monitor.metrics[operation]
        assert metrics["count"] == 1
        assert metrics["total_duration"] == duration
        assert metrics["avg_duration"] == duration
    
    def test_slow_operation_detection(self, perf_monitor):
        """Test detection of slow operations"""
        with patch('logging.Logger.warning') as mock_warning:
            # Record slow operation (>30 seconds)
            perf_monitor.record_performance("slow_operation", 35.0)
            
            # Should log warning
            mock_warning.assert_called()
            args = mock_warning.call_args[0]
            assert "Slow operation detected" in args[0]
    
    def test_performance_summary(self, perf_monitor):
        """Test performance summary generation"""
        # Record various operations
        operations = [
            ("operation_a", 1.0),
            ("operation_a", 2.0),
            ("operation_b", 5.0),
            ("operation_b", 35.0)  # Slow operation
        ]
        
        for op, duration in operations:
            perf_monitor.record_performance(op, duration)
        
        summary = perf_monitor.get_performance_summary(hours=1)
        
        # Should provide comprehensive summary
        assert summary["total_operations"] == 4
        assert "by_operation" in summary
        assert "slow_operations" in summary
        
        # Check operation summaries
        assert "operation_a" in summary["by_operation"]
        assert summary["by_operation"]["operation_a"]["count"] == 2
        assert summary["by_operation"]["operation_a"]["avg_duration"] == 1.5
        
        # Check slow operations
        assert len(summary["slow_operations"]) == 1
        assert summary["slow_operations"][0]["duration"] == 35.0


class TestResourceMonitor:
    """Test suite for ResourceMonitor"""
    
    @pytest.fixture
    def resource_monitor_instance(self):
        """Create resource monitor instance"""
        return ResourceMonitor()
    
    def test_operation_tracking(self, resource_monitor_instance):
        """Test resource-intensive operation tracking"""
        operation_id = "test_operation_123"
        context = {"file_size": 2048}
        
        # Start operation
        operation_data = resource_monitor_instance.start_operation(operation_id, context)
        
        assert operation_data["operation_id"] == operation_id
        assert operation_data["context"] == context
        assert "start_time" in operation_data
        assert resource_monitor_instance.current_operations == 1
        
        # End operation
        resource_monitor_instance.end_operation(operation_data)
        
        assert resource_monitor_instance.current_operations == 0
        assert len(resource_monitor_instance.resource_history) == 1
    
    def test_concurrent_operation_alert(self, resource_monitor_instance):
        """Test alert for high concurrent operations"""
        # Set low threshold for testing
        resource_monitor_instance.alert_thresholds["concurrent_operations"] = 2
        
        with patch('logging.Logger.warning') as mock_warning:
            # Start multiple operations
            for i in range(3):
                resource_monitor_instance.start_operation(f"operation_{i}")
            
            # Should trigger warning
            mock_warning.assert_called()
            args = mock_warning.call_args[0]
            assert "High concurrent operations" in args[0]
    
    def test_resource_summary(self, resource_monitor_instance):
        """Test resource usage summary"""
        # Start and end some operations
        for i in range(3):
            op_data = resource_monitor_instance.start_operation(f"operation_{i}")
            resource_monitor_instance.end_operation(op_data)
        
        summary = resource_monitor_instance.get_resource_summary()
        
        assert "current_operations" in summary
        assert "recent_operations" in summary
        assert "avg_operation_time" in summary
        assert summary["current_operations"] == 0


class TestErrorHandlingDecorators:
    """Test suite for error handling decorators"""
    
    @pytest.mark.asyncio
    async def test_fact_validation_error_decorator(self):
        """Test fact validation error decorator"""
        @handle_fact_validation_errors
        async def failing_validation():
            raise FactValidationError("Validation failed")
        
        result = await failing_validation()
        
        # Should return fallback validation results
        assert isinstance(result, dict)
        assert result["fact_check_score"] == 0.5
        assert result["validation_method"] == "error_fallback"
        assert "error" in result
    
    @pytest.mark.asyncio
    async def test_statistics_registry_error_decorator(self):
        """Test statistics registry error decorator"""
        @handle_statistics_registry_errors
        async def failing_registry():
            raise StatisticsRegistryError("Registry unavailable")
        
        result = await failing_registry()
        
        # Should return fallback registry structure
        assert isinstance(result, dict)
        assert "csv_statistics" in result
        assert "pdf_statistics" in result
        assert result["fallback_used"] is True
    
    @pytest.mark.asyncio
    async def test_retry_decorator(self):
        """Test retry decorator with exponential backoff"""
        call_count = 0
        
        @retry_with_exponential_backoff(max_retries=2, base_delay=0.01)
        async def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return "success"
        
        result = await failing_function()
        
        # Should succeed after retries
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_decorator_final_failure(self):
        """Test retry decorator when all attempts fail"""
        @retry_with_exponential_backoff(max_retries=1, base_delay=0.01)
        async def always_failing_function():
            raise Exception("Permanent failure")
        
        with pytest.raises(Exception, match="Permanent failure"):
            await always_failing_function()


class TestIntegrationScenarios:
    """Integration tests for error handling scenarios"""
    
    @pytest.mark.asyncio
    async def test_cascading_failure_scenario(self):
        """Test handling of cascading failures"""
        error_service = ErrorHandlingService()
        
        # Simulate cascading failures
        errors = [
            (StatisticsRegistryError("Database down"), "statistics_registry"),
            (AIServiceError("Service timeout"), "ai_service"),
            (FactValidationError("Validation impossible"), "fact_validation")
        ]
        
        results = []
        for error, error_type in errors:
            if error_type == "statistics_registry":
                result = await error_service.handle_statistics_registry_error(
                    error, "test_project", "pain", {}
                )
            elif error_type == "ai_service":
                result = await error_service.handle_ai_service_unavailable(
                    error, {"analysis_type": "pain"}
                )
            elif error_type == "fact_validation":
                result = await error_service.handle_fact_validation_error(
                    error, "test response", {}
                )
            
            results.append(result)
        
        # All should return fallback results
        assert len(results) == 3
        for result in results:
            assert isinstance(result, dict)
            assert "error" in result or "fallback" in result
    
    @pytest.mark.asyncio
    async def test_recovery_workflow(self):
        """Test complete recovery workflow"""
        error_service = ErrorHandlingService()
        
        # Test recovery for statistics extraction failure
        context = {
            "file_info": {
                "file_type": "csv",
                "filename": "problematic.csv",
                "error_details": "Encoding issue"
            }
        }
        
        recovery_result = await error_service.implement_recovery_strategy(
            "statistics_extraction_failed", context
        )
        
        # Should attempt recovery
        assert recovery_result["recovery_attempted"] is True
        assert len(recovery_result["alternative_methods_tried"]) > 0
    
    def test_monitoring_integration(self):
        """Test integration between different monitoring components"""
        # Record errors in global monitor
        error_monitor.record_error(
            Exception("Test error"),
            ErrorCategory.AI_SERVICE,
            ErrorSeverity.HIGH,
            {"test": "context"}
        )
        
        # Record performance in global monitor
        performance_monitor.record_performance("test_operation", 2.5, {"size": 1024})
        
        # Start resource tracking
        resource_data = resource_monitor.start_operation("test_resource_op")
        resource_monitor.end_operation(resource_data)
        
        # All monitors should have recorded data
        assert len(error_monitor.error_history) >= 1
        assert len(performance_monitor.performance_history) >= 1
        assert len(resource_monitor.resource_history) >= 1


if __name__ == "__main__":
    pytest.main([__file__])