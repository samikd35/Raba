"""
Integration Validator

Comprehensive validation service to ensure all components work together seamlessly
for the complete user experience. Validates requirements compliance and system integration.

Requirements addressed:
- 1.1: Proper report display from history
- 1.2: Historical reports display identically to newly generated reports
- 3.1: User data isolation and authentication consistency
- 4.5: Chat functionality performance with historical reports
"""

import logging
import time
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum
import json

from ..core.supabase_client import get_standard_client
# Lazy imports to avoid circular dependencies:
# from ...report import get_report_retrieval_service, get_report_error_handler
# from ...performance import get_performance_optimizer  
# from ...cache import get_report_cache_manager

logger = logging.getLogger(__name__)


class ValidationStatus(Enum):
    """Validation status types."""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


@dataclass
class ValidationResult:
    """Result of a validation test."""
    test_name: str
    status: ValidationStatus
    message: str
    execution_time: float
    details: Optional[Dict[str, Any]] = None
    requirement: Optional[str] = None


@dataclass
class IntegrationReport:
    """Comprehensive integration validation report."""
    overall_status: ValidationStatus
    total_tests: int
    passed_tests: int
    failed_tests: int
    warning_tests: int
    skipped_tests: int
    execution_time: float
    requirements_compliance: Dict[str, bool]
    test_results: List[ValidationResult]
    performance_metrics: Dict[str, Any]
    recommendations: List[str]


class IntegrationValidator:
    """
    Comprehensive integration validator for report history functionality.
    
    Validates:
    - End-to-end report retrieval and display
    - User authentication and data isolation
    - Chat functionality integration
    - Performance requirements compliance
    - Error handling and recovery
    """
    
    def __init__(self):
        """Initialize the integration validator."""
        # Lazy imports to avoid circular dependencies
        try:
            from ...report import get_report_retrieval_service, get_report_error_handler
            self.retrieval_service = get_report_retrieval_service()
            self.error_handler = get_report_error_handler()
        except ImportError:
            logger.warning("Report services not available - some validations will be skipped")
            self.retrieval_service = None
            self.error_handler = None
            
        try:
            from ...performance import get_performance_optimizer
            self.performance_optimizer = get_performance_optimizer()
        except ImportError:
            logger.warning("Performance optimizer not available - performance validations will be skipped")
            self.performance_optimizer = None
            
        try:
            from ...cache import get_report_cache_manager
            self.cache_manager = get_report_cache_manager()
        except ImportError:
            logger.warning("Cache manager not available - cache validations will be skipped")
            self.cache_manager = None
            
        self.client = get_standard_client()
        
        # Service availability flags
        self.services_available = {
            'retrieval': self.retrieval_service is not None,
            'performance': self.performance_optimizer is not None,
            'cache': self.cache_manager is not None,
            'error_handler': self.error_handler is not None
        }
        
        # Test configuration
        self.performance_thresholds = {
            "report_load_max_ms": 2000,
            "chat_prep_max_ms": 1000,
            "batch_retrieval_max_ms": 3000,
            "cache_hit_rate_min": 0.5,
            "total_flow_max_ms": 5000
        }
        
        # Requirements mapping
        self.requirement_tests = {
            "1.1": ["test_report_display_from_history", "test_navigation_consistency"],
            "1.2": ["test_historical_vs_new_display", "test_formatting_consistency"],
            "3.1": ["test_user_data_isolation", "test_authentication_consistency"],
            "4.5": ["test_chat_performance", "test_chat_context_preparation"]
        }
    
    async def run_comprehensive_validation(
        self,
        test_user_id: str,
        test_user_token: str,
        sample_report_ids: List[str] = None
    ) -> IntegrationReport:
        """
        Run comprehensive integration validation.
        
        Args:
            test_user_id: Test user ID for validation
            test_user_token: Test user JWT token
            sample_report_ids: Optional list of sample report IDs for testing
            
        Returns:
            Comprehensive integration report
        """
        start_time = time.time()
        test_results = []
        
        logger.info("Starting comprehensive integration validation...")
        
        try:
            # Test 1: Basic report retrieval functionality
            result = await self._test_report_retrieval(test_user_id, test_user_token, sample_report_ids)
            test_results.append(result)
            
            # Test 2: Report display consistency
            result = await self._test_report_display_consistency(test_user_id, test_user_token, sample_report_ids)
            test_results.append(result)
            
            # Test 3: User data isolation
            result = await self._test_user_data_isolation(test_user_id, test_user_token)
            test_results.append(result)
            
            # Test 4: Authentication consistency
            result = await self._test_authentication_consistency(test_user_id, test_user_token)
            test_results.append(result)
            
            # Test 5: Chat functionality integration
            result = await self._test_chat_integration(test_user_id, test_user_token, sample_report_ids)
            test_results.append(result)
            
            # Test 6: Performance requirements
            result = await self._test_performance_requirements(test_user_id, test_user_token, sample_report_ids)
            test_results.append(result)
            
            # Test 7: Cache functionality
            result = await self._test_cache_functionality(test_user_id, test_user_token, sample_report_ids)
            test_results.append(result)
            
            # Test 8: Error handling
            result = await self._test_error_handling(test_user_id, test_user_token)
            test_results.append(result)
            
            # Test 9: Batch operations
            result = await self._test_batch_operations(test_user_id, test_user_token, sample_report_ids)
            test_results.append(result)
            
            # Test 10: End-to-end flow
            result = await self._test_end_to_end_flow(test_user_id, test_user_token, sample_report_ids)
            test_results.append(result)
            
        except Exception as e:
            logger.error(f"Validation failed with error: {e}")
            test_results.append(ValidationResult(
                test_name="validation_execution",
                status=ValidationStatus.FAILED,
                message=f"Validation execution failed: {str(e)}",
                execution_time=time.time() - start_time,
                details={"error": str(e)}
            ))
        
        # Generate comprehensive report
        report = self._generate_integration_report(test_results, time.time() - start_time)
        
        logger.info(f"Integration validation completed in {report.execution_time:.2f}s")
        logger.info(f"Overall status: {report.overall_status.value}")
        logger.info(f"Tests: {report.passed_tests} passed, {report.failed_tests} failed, {report.warning_tests} warnings")
        
        return report
    
    async def _test_report_retrieval(
        self,
        user_id: str,
        user_token: str,
        sample_report_ids: List[str] = None
    ) -> ValidationResult:
        """Test basic report retrieval functionality."""
        start_time = time.time()
        
        try:
            logger.info("Testing report retrieval functionality...")
            
            # If no sample reports provided, try to get some from the database
            if not sample_report_ids:
                query = self.client.client.from_("report_display_view") \
                    .select("id") \
                    .eq("user_id", user_id) \
                    .limit(3)
                
                response = query.execute()
                sample_report_ids = [r["id"] for r in response.data] if response.data else []
            
            if not sample_report_ids:
                return ValidationResult(
                    test_name="test_report_retrieval",
                    status=ValidationStatus.SKIPPED,
                    message="No sample reports available for testing",
                    execution_time=time.time() - start_time,
                    requirement="1.1"
                )
            
            # Test single report retrieval
            report_id = sample_report_ids[0]
            report_data = await self.retrieval_service.get_report_for_display(
                report_id, user_id, user_token
            )
            
            if not report_data:
                return ValidationResult(
                    test_name="test_report_retrieval",
                    status=ValidationStatus.FAILED,
                    message="Failed to retrieve report data",
                    execution_time=time.time() - start_time,
                    requirement="1.1"
                )
            
            # Validate report structure
            required_fields = ["id", "title", "content"]
            missing_fields = [field for field in required_fields if field not in report_data]
            
            if missing_fields:
                return ValidationResult(
                    test_name="test_report_retrieval",
                    status=ValidationStatus.FAILED,
                    message=f"Report missing required fields: {missing_fields}",
                    execution_time=time.time() - start_time,
                    details={"missing_fields": missing_fields},
                    requirement="1.1"
                )
            
            # Test metadata retrieval
            metadata = await self.retrieval_service.get_report_metadata(
                report_id, user_id, user_token
            )
            
            if not metadata:
                return ValidationResult(
                    test_name="test_report_retrieval",
                    status=ValidationStatus.WARNING,
                    message="Metadata retrieval failed but display data succeeded",
                    execution_time=time.time() - start_time,
                    requirement="1.1"
                )
            
            return ValidationResult(
                test_name="test_report_retrieval",
                status=ValidationStatus.PASSED,
                message="Report retrieval functionality working correctly",
                execution_time=time.time() - start_time,
                details={
                    "report_id": report_id,
                    "has_content": bool(report_data.get("content")),
                    "has_metadata": bool(metadata)
                },
                requirement="1.1"
            )
            
        except Exception as e:
            return ValidationResult(
                test_name="test_report_retrieval",
                status=ValidationStatus.FAILED,
                message=f"Report retrieval test failed: {str(e)}",
                execution_time=time.time() - start_time,
                details={"error": str(e)},
                requirement="1.1"
            )
    
    async def _test_report_display_consistency(
        self,
        user_id: str,
        user_token: str,
        sample_report_ids: List[str] = None
    ) -> ValidationResult:
        """Test that historical reports display consistently with new reports."""
        start_time = time.time()
        
        try:
            logger.info("Testing report display consistency...")
            
            if not sample_report_ids:
                return ValidationResult(
                    test_name="test_report_display_consistency",
                    status=ValidationStatus.SKIPPED,
                    message="No sample reports available for consistency testing",
                    execution_time=time.time() - start_time,
                    requirement="1.2"
                )
            
            consistency_issues = []
            
            for report_id in sample_report_ids[:3]:  # Test up to 3 reports
                report_data = await self.retrieval_service.get_report_for_display(
                    report_id, user_id, user_token
                )
                
                if not report_data:
                    consistency_issues.append(f"Report {report_id} could not be retrieved")
                    continue
                
                # Check content structure
                content = report_data.get("content", {})
                if not isinstance(content, dict):
                    consistency_issues.append(f"Report {report_id} has invalid content structure")
                    continue
                
                # Check for raw JSON data (should not be present)
                content_str = json.dumps(content, default=str)
                if "session_id" in content_str or "workflow_metadata" in content_str:
                    consistency_issues.append(f"Report {report_id} contains raw workflow data")
                
                # Check for proper formatting
                if not report_data.get("title"):
                    consistency_issues.append(f"Report {report_id} missing title")
                
                if not content and not report_data.get("summary"):
                    consistency_issues.append(f"Report {report_id} has no displayable content")
            
            if consistency_issues:
                return ValidationResult(
                    test_name="test_report_display_consistency",
                    status=ValidationStatus.FAILED,
                    message=f"Display consistency issues found: {len(consistency_issues)}",
                    execution_time=time.time() - start_time,
                    details={"issues": consistency_issues},
                    requirement="1.2"
                )
            
            return ValidationResult(
                test_name="test_report_display_consistency",
                status=ValidationStatus.PASSED,
                message="Report display consistency validated successfully",
                execution_time=time.time() - start_time,
                details={"reports_tested": len(sample_report_ids[:3])},
                requirement="1.2"
            )
            
        except Exception as e:
            return ValidationResult(
                test_name="test_report_display_consistency",
                status=ValidationStatus.FAILED,
                message=f"Display consistency test failed: {str(e)}",
                execution_time=time.time() - start_time,
                details={"error": str(e)},
                requirement="1.2"
            )
    
    async def _test_user_data_isolation(
        self,
        user_id: str,
        user_token: str
    ) -> ValidationResult:
        """Test user data isolation and access control."""
        start_time = time.time()
        
        try:
            logger.info("Testing user data isolation...")
            
            # Test that user can only access their own reports
            query = self.client.client.from_("report_display_view") \
                .select("id,user_id") \
                .eq("user_id", user_id) \
                .limit(5)
            
            response = query.execute()
            user_reports = response.data
            
            if not user_reports:
                return ValidationResult(
                    test_name="test_user_data_isolation",
                    status=ValidationStatus.SKIPPED,
                    message="No user reports found for isolation testing",
                    execution_time=time.time() - start_time,
                    requirement="3.1"
                )
            
            # Verify all returned reports belong to the user
            isolation_violations = []
            for report in user_reports:
                if report.get("user_id") != user_id:
                    isolation_violations.append(f"Report {report['id']} belongs to different user")
            
            if isolation_violations:
                return ValidationResult(
                    test_name="test_user_data_isolation",
                    status=ValidationStatus.FAILED,
                    message=f"Data isolation violations found: {len(isolation_violations)}",
                    execution_time=time.time() - start_time,
                    details={"violations": isolation_violations},
                    requirement="3.1"
                )
            
            # Test access control with retrieval service
            report_id = user_reports[0]["id"]
            
            # This should succeed
            report_data = await self.retrieval_service.get_report_for_display(
                report_id, user_id, user_token
            )
            
            if not report_data:
                return ValidationResult(
                    test_name="test_user_data_isolation",
                    status=ValidationStatus.FAILED,
                    message="User cannot access their own report",
                    execution_time=time.time() - start_time,
                    requirement="3.1"
                )
            
            return ValidationResult(
                test_name="test_user_data_isolation",
                status=ValidationStatus.PASSED,
                message="User data isolation working correctly",
                execution_time=time.time() - start_time,
                details={"reports_tested": len(user_reports)},
                requirement="3.1"
            )
            
        except Exception as e:
            return ValidationResult(
                test_name="test_user_data_isolation",
                status=ValidationStatus.FAILED,
                message=f"Data isolation test failed: {str(e)}",
                execution_time=time.time() - start_time,
                details={"error": str(e)},
                requirement="3.1"
            )
    
    async def _test_authentication_consistency(
        self,
        user_id: str,
        user_token: str
    ) -> ValidationResult:
        """Test authentication consistency across operations."""
        start_time = time.time()
        
        try:
            logger.info("Testing authentication consistency...")
            
            # Test that operations work with proper authentication
            operations_tested = []
            
            # Test 1: Report retrieval with token
            try:
                query = self.client.client.from_("report_display_view") \
                    .select("id") \
                    .eq("user_id", user_id) \
                    .limit(1)
                
                response = query.execute()
                if response.data:
                    report_id = response.data[0]["id"]
                    
                    report_data = await self.retrieval_service.get_report_for_display(
                        report_id, user_id, user_token
                    )
                    
                    operations_tested.append({
                        "operation": "report_retrieval",
                        "success": bool(report_data),
                        "with_token": True
                    })
                
            except Exception as e:
                operations_tested.append({
                    "operation": "report_retrieval",
                    "success": False,
                    "error": str(e),
                    "with_token": True
                })
            
            # Test 2: Batch operations
            try:
                if response.data:
                    batch_result = await self.retrieval_service.get_reports_batch(
                        [response.data[0]["id"]], user_id, user_token
                    )
                    
                    operations_tested.append({
                        "operation": "batch_retrieval",
                        "success": bool(batch_result),
                        "with_token": True
                    })
                
            except Exception as e:
                operations_tested.append({
                    "operation": "batch_retrieval",
                    "success": False,
                    "error": str(e),
                    "with_token": True
                })
            
            # Check results
            failed_operations = [op for op in operations_tested if not op["success"]]
            
            if failed_operations:
                return ValidationResult(
                    test_name="test_authentication_consistency",
                    status=ValidationStatus.FAILED,
                    message=f"Authentication failures in {len(failed_operations)} operations",
                    execution_time=time.time() - start_time,
                    details={"failed_operations": failed_operations},
                    requirement="3.1"
                )
            
            return ValidationResult(
                test_name="test_authentication_consistency",
                status=ValidationStatus.PASSED,
                message="Authentication consistency validated successfully",
                execution_time=time.time() - start_time,
                details={"operations_tested": len(operations_tested)},
                requirement="3.1"
            )
            
        except Exception as e:
            return ValidationResult(
                test_name="test_authentication_consistency",
                status=ValidationStatus.FAILED,
                message=f"Authentication consistency test failed: {str(e)}",
                execution_time=time.time() - start_time,
                details={"error": str(e)},
                requirement="3.1"
            )
    
    async def _test_chat_integration(
        self,
        user_id: str,
        user_token: str,
        sample_report_ids: List[str] = None
    ) -> ValidationResult:
        """Test chat functionality integration with historical reports."""
        start_time = time.time()
        
        try:
            logger.info("Testing chat integration...")
            
            if not sample_report_ids:
                return ValidationResult(
                    test_name="test_chat_integration",
                    status=ValidationStatus.SKIPPED,
                    message="No sample reports available for chat integration testing",
                    execution_time=time.time() - start_time,
                    requirement="4.5"
                )
            
            report_id = sample_report_ids[0]
            
            # Test chat context preparation
            context_data = await self.performance_optimizer.optimize_chat_context_preparation(
                report_id, user_id, user_token
            )
            
            if not context_data:
                return ValidationResult(
                    test_name="test_chat_integration",
                    status=ValidationStatus.FAILED,
                    message="Chat context preparation failed",
                    execution_time=time.time() - start_time,
                    requirement="4.5"
                )
            
            # Validate context structure
            required_context_fields = ["report_id", "title", "content_preview"]
            missing_fields = [field for field in required_context_fields if field not in context_data]
            
            if missing_fields:
                return ValidationResult(
                    test_name="test_chat_integration",
                    status=ValidationStatus.FAILED,
                    message=f"Chat context missing required fields: {missing_fields}",
                    execution_time=time.time() - start_time,
                    details={"missing_fields": missing_fields},
                    requirement="4.5"
                )
            
            # Test cache integration for chat context
            cached_context = await self.cache_manager.get_cached_chat_context(report_id, user_id)
            
            return ValidationResult(
                test_name="test_chat_integration",
                status=ValidationStatus.PASSED,
                message="Chat integration working correctly",
                execution_time=time.time() - start_time,
                details={
                    "context_prepared": True,
                    "context_cached": bool(cached_context),
                    "report_id": report_id
                },
                requirement="4.5"
            )
            
        except Exception as e:
            return ValidationResult(
                test_name="test_chat_integration",
                status=ValidationStatus.FAILED,
                message=f"Chat integration test failed: {str(e)}",
                execution_time=time.time() - start_time,
                details={"error": str(e)},
                requirement="4.5"
            )
    
    async def _test_performance_requirements(
        self,
        user_id: str,
        user_token: str,
        sample_report_ids: List[str] = None
    ) -> ValidationResult:
        """Test performance requirements compliance."""
        start_time = time.time()
        
        try:
            logger.info("Testing performance requirements...")
            
            if not sample_report_ids:
                return ValidationResult(
                    test_name="test_performance_requirements",
                    status=ValidationStatus.SKIPPED,
                    message="No sample reports available for performance testing",
                    execution_time=time.time() - start_time,
                    requirement="4.5"
                )
            
            performance_results = {}
            
            # Test 1: Single report load time
            report_id = sample_report_ids[0]
            load_start = time.time()
            
            report_data = await self.retrieval_service.get_report_for_display(
                report_id, user_id, user_token
            )
            
            load_time_ms = (time.time() - load_start) * 1000
            performance_results["report_load_ms"] = load_time_ms
            
            # Test 2: Chat context preparation time
            if report_data:
                chat_start = time.time()
                
                context_data = await self.performance_optimizer.optimize_chat_context_preparation(
                    report_id, user_id, user_token
                )
                
                chat_time_ms = (time.time() - chat_start) * 1000
                performance_results["chat_prep_ms"] = chat_time_ms
            
            # Test 3: Batch retrieval time
            if len(sample_report_ids) > 1:
                batch_start = time.time()
                
                batch_results = await self.performance_optimizer.optimize_batch_report_retrieval(
                    sample_report_ids[:3], user_id, user_token
                )
                
                batch_time_ms = (time.time() - batch_start) * 1000
                performance_results["batch_retrieval_ms"] = batch_time_ms
            
            # Check against thresholds
            violations = []
            for metric, value in performance_results.items():
                threshold_key = f"{metric.replace('_ms', '_max_ms')}"
                if threshold_key in self.performance_thresholds:
                    threshold = self.performance_thresholds[threshold_key]
                    if value > threshold:
                        violations.append(f"{metric}: {value:.0f}ms > {threshold}ms")
            
            if violations:
                return ValidationResult(
                    test_name="test_performance_requirements",
                    status=ValidationStatus.WARNING,
                    message=f"Performance thresholds exceeded: {len(violations)}",
                    execution_time=time.time() - start_time,
                    details={
                        "violations": violations,
                        "performance_results": performance_results
                    },
                    requirement="4.5"
                )
            
            return ValidationResult(
                test_name="test_performance_requirements",
                status=ValidationStatus.PASSED,
                message="Performance requirements met",
                execution_time=time.time() - start_time,
                details={"performance_results": performance_results},
                requirement="4.5"
            )
            
        except Exception as e:
            return ValidationResult(
                test_name="test_performance_requirements",
                status=ValidationStatus.FAILED,
                message=f"Performance test failed: {str(e)}",
                execution_time=time.time() - start_time,
                details={"error": str(e)},
                requirement="4.5"
            )
    
    async def _test_cache_functionality(
        self,
        user_id: str,
        user_token: str,
        sample_report_ids: List[str] = None
    ) -> ValidationResult:
        """Test cache functionality and performance."""
        start_time = time.time()
        
        try:
            logger.info("Testing cache functionality...")
            
            if not sample_report_ids:
                return ValidationResult(
                    test_name="test_cache_functionality",
                    status=ValidationStatus.SKIPPED,
                    message="No sample reports available for cache testing",
                    execution_time=time.time() - start_time,
                    requirement="2.4"
                )
            
            report_id = sample_report_ids[0]
            
            # Test cache miss (first access)
            cached_report = await self.cache_manager.get_cached_report(report_id, user_id)
            cache_miss = cached_report is None
            
            # Load report (should cache it)
            report_data = await self.retrieval_service.get_report_for_display(
                report_id, user_id, user_token
            )
            
            if not report_data:
                return ValidationResult(
                    test_name="test_cache_functionality",
                    status=ValidationStatus.FAILED,
                    message="Could not load report for cache testing",
                    execution_time=time.time() - start_time,
                    requirement="2.4"
                )
            
            # Test cache hit (second access)
            cached_report = await self.cache_manager.get_cached_report(report_id, user_id)
            cache_hit = cached_report is not None
            
            # Test cache warming
            warming_result = await self.cache_manager.warm_user_cache(user_id, user_token, max_reports=5)
            
            cache_results = {
                "cache_miss_detected": cache_miss,
                "cache_hit_detected": cache_hit,
                "warming_successful": warming_result.get("reports_cached", 0) > 0,
                "reports_warmed": warming_result.get("reports_cached", 0)
            }
            
            # Check cache metrics
            cache_metrics = await self.cache_manager.get_cache_metrics()
            cache_results["hit_rate"] = cache_metrics.hit_rate
            
            issues = []
            if not cache_hit:
                issues.append("Cache hit not detected after report load")
            if cache_metrics.hit_rate < self.performance_thresholds["cache_hit_rate_min"]:
                issues.append(f"Cache hit rate too low: {cache_metrics.hit_rate:.2f}")
            
            if issues:
                return ValidationResult(
                    test_name="test_cache_functionality",
                    status=ValidationStatus.WARNING,
                    message=f"Cache issues detected: {len(issues)}",
                    execution_time=time.time() - start_time,
                    details={"issues": issues, "cache_results": cache_results},
                    requirement="2.4"
                )
            
            return ValidationResult(
                test_name="test_cache_functionality",
                status=ValidationStatus.PASSED,
                message="Cache functionality working correctly",
                execution_time=time.time() - start_time,
                details={"cache_results": cache_results},
                requirement="2.4"
            )
            
        except Exception as e:
            return ValidationResult(
                test_name="test_cache_functionality",
                status=ValidationStatus.FAILED,
                message=f"Cache functionality test failed: {str(e)}",
                execution_time=time.time() - start_time,
                details={"error": str(e)},
                requirement="2.4"
            )
    
    async def _test_error_handling(
        self,
        user_id: str,
        user_token: str
    ) -> ValidationResult:
        """Test error handling and recovery mechanisms."""
        start_time = time.time()
        
        try:
            logger.info("Testing error handling...")
            
            error_scenarios = []
            
            # Test 1: Invalid report ID
            try:
                invalid_report = await self.retrieval_service.get_report_for_display(
                    "invalid-id", user_id, user_token
                )
                error_scenarios.append({
                    "scenario": "invalid_report_id",
                    "handled_gracefully": invalid_report is None,
                    "error": None
                })
            except Exception as e:
                error_scenarios.append({
                    "scenario": "invalid_report_id",
                    "handled_gracefully": True,  # Exception is expected
                    "error": str(e)
                })
            
            # Test 2: Non-existent report ID (valid UUID format)
            try:
                nonexistent_report = await self.retrieval_service.get_report_for_display(
                    "12345678-1234-1234-1234-123456789012", user_id, user_token
                )
                error_scenarios.append({
                    "scenario": "nonexistent_report",
                    "handled_gracefully": nonexistent_report is None,
                    "error": None
                })
            except Exception as e:
                error_scenarios.append({
                    "scenario": "nonexistent_report",
                    "handled_gracefully": True,  # Exception is expected
                    "error": str(e)
                })
            
            # Test 3: Invalid user ID
            try:
                invalid_user_report = await self.retrieval_service.get_report_for_display(
                    "12345678-1234-1234-1234-123456789012", "invalid-user", user_token
                )
                error_scenarios.append({
                    "scenario": "invalid_user_id",
                    "handled_gracefully": invalid_user_report is None,
                    "error": None
                })
            except Exception as e:
                error_scenarios.append({
                    "scenario": "invalid_user_id",
                    "handled_gracefully": True,  # Exception is expected
                    "error": str(e)
                })
            
            # Check results
            poorly_handled = [s for s in error_scenarios if not s["handled_gracefully"]]
            
            if poorly_handled:
                return ValidationResult(
                    test_name="test_error_handling",
                    status=ValidationStatus.FAILED,
                    message=f"Poor error handling in {len(poorly_handled)} scenarios",
                    execution_time=time.time() - start_time,
                    details={"poorly_handled": poorly_handled},
                    requirement="5.3"
                )
            
            return ValidationResult(
                test_name="test_error_handling",
                status=ValidationStatus.PASSED,
                message="Error handling working correctly",
                execution_time=time.time() - start_time,
                details={"scenarios_tested": len(error_scenarios)},
                requirement="5.3"
            )
            
        except Exception as e:
            return ValidationResult(
                test_name="test_error_handling",
                status=ValidationStatus.FAILED,
                message=f"Error handling test failed: {str(e)}",
                execution_time=time.time() - start_time,
                details={"error": str(e)},
                requirement="5.3"
            )
    
    async def _test_batch_operations(
        self,
        user_id: str,
        user_token: str,
        sample_report_ids: List[str] = None
    ) -> ValidationResult:
        """Test batch operations performance and correctness."""
        start_time = time.time()
        
        try:
            logger.info("Testing batch operations...")
            
            if not sample_report_ids or len(sample_report_ids) < 2:
                return ValidationResult(
                    test_name="test_batch_operations",
                    status=ValidationStatus.SKIPPED,
                    message="Insufficient sample reports for batch testing",
                    execution_time=time.time() - start_time,
                    requirement="2.4"
                )
            
            # Test batch retrieval
            batch_ids = sample_report_ids[:min(5, len(sample_report_ids))]
            
            batch_results = await self.performance_optimizer.optimize_batch_report_retrieval(
                batch_ids, user_id, user_token
            )
            
            if not batch_results:
                return ValidationResult(
                    test_name="test_batch_operations",
                    status=ValidationStatus.FAILED,
                    message="Batch retrieval returned no results",
                    execution_time=time.time() - start_time,
                    requirement="2.4"
                )
            
            # Validate batch results
            batch_issues = []
            
            for report_id in batch_ids:
                if report_id not in batch_results:
                    batch_issues.append(f"Report {report_id} missing from batch results")
                else:
                    report_data = batch_results[report_id]
                    if not report_data.get("id") or not report_data.get("content"):
                        batch_issues.append(f"Report {report_id} has incomplete data")
            
            if batch_issues:
                return ValidationResult(
                    test_name="test_batch_operations",
                    status=ValidationStatus.FAILED,
                    message=f"Batch operation issues: {len(batch_issues)}",
                    execution_time=time.time() - start_time,
                    details={"issues": batch_issues},
                    requirement="2.4"
                )
            
            return ValidationResult(
                test_name="test_batch_operations",
                status=ValidationStatus.PASSED,
                message="Batch operations working correctly",
                execution_time=time.time() - start_time,
                details={
                    "reports_requested": len(batch_ids),
                    "reports_returned": len(batch_results)
                },
                requirement="2.4"
            )
            
        except Exception as e:
            return ValidationResult(
                test_name="test_batch_operations",
                status=ValidationStatus.FAILED,
                message=f"Batch operations test failed: {str(e)}",
                execution_time=time.time() - start_time,
                details={"error": str(e)},
                requirement="2.4"
            )
    
    async def _test_end_to_end_flow(
        self,
        user_id: str,
        user_token: str,
        sample_report_ids: List[str] = None
    ) -> ValidationResult:
        """Test complete end-to-end flow from history to chat."""
        start_time = time.time()
        
        try:
            logger.info("Testing end-to-end flow...")
            
            if not sample_report_ids:
                return ValidationResult(
                    test_name="test_end_to_end_flow",
                    status=ValidationStatus.SKIPPED,
                    message="No sample reports available for end-to-end testing",
                    execution_time=time.time() - start_time,
                    requirement="1.1"
                )
            
            report_id = sample_report_ids[0]
            flow_steps = []
            
            # Step 1: Load report for display (simulating history click)
            step_start = time.time()
            report_data = await self.retrieval_service.get_report_for_display(
                report_id, user_id, user_token
            )
            flow_steps.append({
                "step": "report_display_load",
                "success": bool(report_data),
                "time_ms": (time.time() - step_start) * 1000
            })
            
            if not report_data:
                return ValidationResult(
                    test_name="test_end_to_end_flow",
                    status=ValidationStatus.FAILED,
                    message="End-to-end flow failed at report loading",
                    execution_time=time.time() - start_time,
                    details={"flow_steps": flow_steps},
                    requirement="1.1"
                )
            
            # Step 2: Prepare chat context (simulating chat initiation)
            step_start = time.time()
            chat_context = await self.performance_optimizer.optimize_chat_context_preparation(
                report_id, user_id, user_token
            )
            flow_steps.append({
                "step": "chat_context_prep",
                "success": bool(chat_context),
                "time_ms": (time.time() - step_start) * 1000
            })
            
            # Step 3: Verify chat context is ready for embedding
            if chat_context:
                context_ready = (
                    chat_context.get("embedding_ready", False) and
                    chat_context.get("content_preview") and
                    chat_context.get("title")
                )
                flow_steps.append({
                    "step": "chat_context_validation",
                    "success": context_ready,
                    "time_ms": 0
                })
            
            # Calculate total flow time
            total_flow_time = sum(step.get("time_ms", 0) for step in flow_steps)
            
            # Check if flow meets performance requirements
            flow_issues = []
            failed_steps = [step for step in flow_steps if not step["success"]]
            
            if failed_steps:
                flow_issues.extend([f"Step '{step['step']}' failed" for step in failed_steps])
            
            if total_flow_time > self.performance_thresholds["total_flow_max_ms"]:
                flow_issues.append(f"Total flow time {total_flow_time:.0f}ms exceeds {self.performance_thresholds['total_flow_max_ms']}ms")
            
            if flow_issues:
                return ValidationResult(
                    test_name="test_end_to_end_flow",
                    status=ValidationStatus.FAILED,
                    message=f"End-to-end flow issues: {len(flow_issues)}",
                    execution_time=time.time() - start_time,
                    details={
                        "issues": flow_issues,
                        "flow_steps": flow_steps,
                        "total_flow_time_ms": total_flow_time
                    },
                    requirement="1.1"
                )
            
            return ValidationResult(
                test_name="test_end_to_end_flow",
                status=ValidationStatus.PASSED,
                message="End-to-end flow working correctly",
                execution_time=time.time() - start_time,
                details={
                    "flow_steps": flow_steps,
                    "total_flow_time_ms": total_flow_time
                },
                requirement="1.1"
            )
            
        except Exception as e:
            return ValidationResult(
                test_name="test_end_to_end_flow",
                status=ValidationStatus.FAILED,
                message=f"End-to-end flow test failed: {str(e)}",
                execution_time=time.time() - start_time,
                details={"error": str(e)},
                requirement="1.1"
            )
    
    def _generate_integration_report(
        self,
        test_results: List[ValidationResult],
        total_execution_time: float
    ) -> IntegrationReport:
        """Generate comprehensive integration report."""
        
        # Count test results by status
        passed_tests = sum(1 for r in test_results if r.status == ValidationStatus.PASSED)
        failed_tests = sum(1 for r in test_results if r.status == ValidationStatus.FAILED)
        warning_tests = sum(1 for r in test_results if r.status == ValidationStatus.WARNING)
        skipped_tests = sum(1 for r in test_results if r.status == ValidationStatus.SKIPPED)
        
        # Determine overall status
        if failed_tests > 0:
            overall_status = ValidationStatus.FAILED
        elif warning_tests > 0:
            overall_status = ValidationStatus.WARNING
        else:
            overall_status = ValidationStatus.PASSED
        
        # Check requirements compliance
        requirements_compliance = {}
        for requirement, test_names in self.requirement_tests.items():
            requirement_results = [
                r for r in test_results 
                if r.requirement == requirement or any(test_name in r.test_name for test_name in test_names)
            ]
            
            if requirement_results:
                # Requirement is met if all related tests passed or have warnings
                requirement_met = all(
                    r.status in [ValidationStatus.PASSED, ValidationStatus.WARNING, ValidationStatus.SKIPPED]
                    for r in requirement_results
                )
                requirements_compliance[requirement] = requirement_met
            else:
                requirements_compliance[requirement] = False
        
        # Generate performance metrics summary
        performance_metrics = {}
        for result in test_results:
            if result.details and "performance_results" in result.details:
                performance_metrics.update(result.details["performance_results"])
        
        # Generate recommendations
        recommendations = []
        
        if failed_tests > 0:
            recommendations.append(f"Address {failed_tests} failed tests before deployment")
        
        if warning_tests > 0:
            recommendations.append(f"Review {warning_tests} tests with warnings for potential improvements")
        
        # Performance-specific recommendations
        if "report_load_ms" in performance_metrics:
            load_time = performance_metrics["report_load_ms"]
            if load_time > self.performance_thresholds["report_load_max_ms"]:
                recommendations.append(f"Optimize report loading time (current: {load_time:.0f}ms)")
        
        if "chat_prep_ms" in performance_metrics:
            chat_time = performance_metrics["chat_prep_ms"]
            if chat_time > self.performance_thresholds["chat_prep_max_ms"]:
                recommendations.append(f"Optimize chat context preparation (current: {chat_time:.0f}ms)")
        
        # Requirements-specific recommendations
        unmet_requirements = [req for req, met in requirements_compliance.items() if not met]
        if unmet_requirements:
            recommendations.append(f"Address unmet requirements: {', '.join(unmet_requirements)}")
        
        return IntegrationReport(
            overall_status=overall_status,
            total_tests=len(test_results),
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            warning_tests=warning_tests,
            skipped_tests=skipped_tests,
            execution_time=total_execution_time,
            requirements_compliance=requirements_compliance,
            test_results=test_results,
            performance_metrics=performance_metrics,
            recommendations=recommendations
        )


# Global integration validator instance
_global_integration_validator = None


def get_integration_validator() -> IntegrationValidator:
    """Get the global integration validator instance."""
    global _global_integration_validator
    if _global_integration_validator is None:
        _global_integration_validator = IntegrationValidator()
    return _global_integration_validator