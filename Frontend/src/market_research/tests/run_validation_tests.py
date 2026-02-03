"""
Test Runner for Fact Validation and Error Handling Tests

Comprehensive test runner for all fact validation and error handling components.
Includes performance benchmarks and integration test scenarios.
"""

import pytest
import sys
import time
import asyncio
from pathlib import Path
from typing import Dict, Any, List
import logging

# Configure logging for test runs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ValidationTestRunner:
    """Test runner for validation and error handling tests"""
    
    def __init__(self):
        self.test_results = {}
        self.performance_metrics = {}
    
    def run_fact_validation_tests(self) -> Dict[str, Any]:
        """Run fact validation engine tests"""
        logger.info("🧪 Running Fact Validation Engine Tests...")
        
        start_time = time.time()
        
        # Run fact validation tests
        result = pytest.main([
            "Backend/src/market_research/tests/test_fact_validation_engine.py",
            "-v",
            "--tb=short",
            "--disable-warnings"
        ])
        
        duration = time.time() - start_time
        
        test_result = {
            "exit_code": result,
            "duration": duration,
            "status": "PASSED" if result == 0 else "FAILED"
        }
        
        self.test_results["fact_validation"] = test_result
        logger.info(f"✅ Fact Validation Tests: {test_result['status']} ({duration:.2f}s)")
        
        return test_result
    
    def run_error_handling_tests(self) -> Dict[str, Any]:
        """Run error handling system tests"""
        logger.info("🧪 Running Error Handling System Tests...")
        
        start_time = time.time()
        
        # Run error handling tests
        result = pytest.main([
            "Backend/src/market_research/tests/test_error_handling_system.py",
            "-v",
            "--tb=short",
            "--disable-warnings"
        ])
        
        duration = time.time() - start_time
        
        test_result = {
            "exit_code": result,
            "duration": duration,
            "status": "PASSED" if result == 0 else "FAILED"
        }
        
        self.test_results["error_handling"] = test_result
        logger.info(f"✅ Error Handling Tests: {test_result['status']} ({duration:.2f}s)")
        
        return test_result
    
    def run_integration_tests(self) -> Dict[str, Any]:
        """Run validation integration tests"""
        logger.info("🧪 Running Validation Integration Tests...")
        
        start_time = time.time()
        
        # Run integration tests
        result = pytest.main([
            "Backend/src/market_research/tests/test_validation_integration.py",
            "-v",
            "--tb=short",
            "--disable-warnings"
        ])
        
        duration = time.time() - start_time
        
        test_result = {
            "exit_code": result,
            "duration": duration,
            "status": "PASSED" if result == 0 else "FAILED"
        }
        
        self.test_results["integration"] = test_result
        logger.info(f"✅ Integration Tests: {test_result['status']} ({duration:.2f}s)")
        
        return test_result
    
    def run_performance_benchmarks(self) -> Dict[str, Any]:
        """Run performance benchmarks for validation components"""
        logger.info("🚀 Running Performance Benchmarks...")
        
        benchmarks = {}
        
        # Benchmark fact validation engine
        try:
            from ..services.fact_validation_engine import FactValidationEngine
            
            validation_engine = FactValidationEngine()
            
            # Benchmark claim extraction
            start_time = time.time()
            large_response = " ".join([
                f"Survey shows {i}% satisfaction for feature {i}. "
                f"{i * 10} respondents mentioned this aspect."
                for i in range(1, 101)
            ])
            
            claims = validation_engine.extract_quantitative_claims(large_response)
            extraction_time = time.time() - start_time
            
            benchmarks["claim_extraction"] = {
                "duration": extraction_time,
                "claims_extracted": len(claims),
                "claims_per_second": len(claims) / extraction_time if extraction_time > 0 else 0
            }
            
            logger.info(f"📊 Claim Extraction: {len(claims)} claims in {extraction_time:.3f}s")
            
            # Benchmark validation against large registry
            start_time = time.time()
            large_registry = {
                "csv_statistics": {
                    "categorical_distributions": {
                        f"field_{i}": {
                            "distribution": [
                                {
                                    "value": f"value_{j}",
                                    "count": j * 10,
                                    "percentage": float(j * 5),
                                    "citation_id": f"csv_{i}_{j}"
                                }
                                for j in range(1, 21)
                            ]
                        }
                        for i in range(1, 51)
                    }
                },
                "pdf_statistics": {
                    "themes": {
                        f"theme_{i}": {
                            "frequency": i * 2,
                            "percentage": float(i * 2),
                            "citation_id": f"pdf_theme_{i}"
                        }
                        for i in range(1, 51)
                    }
                }
            }
            
            validation_results = validation_engine.validate_claims_against_registry(
                claims[:10], large_registry  # Validate first 10 claims
            )
            validation_time = time.time() - start_time
            
            benchmarks["validation"] = {
                "duration": validation_time,
                "claims_validated": 10,
                "registry_size": len(large_registry["csv_statistics"]["categorical_distributions"]) + len(large_registry["pdf_statistics"]["themes"]),
                "validations_per_second": 10 / validation_time if validation_time > 0 else 0
            }
            
            logger.info(f"📊 Validation: 10 claims against {benchmarks['validation']['registry_size']} statistics in {validation_time:.3f}s")
            
        except Exception as e:
            logger.error(f"❌ Performance benchmark failed: {e}")
            benchmarks["error"] = str(e)
        
        self.performance_metrics = benchmarks
        return benchmarks
    
    def run_stress_tests(self) -> Dict[str, Any]:
        """Run stress tests for validation components"""
        logger.info("💪 Running Stress Tests...")
        
        stress_results = {}
        
        try:
            from ..services.fact_validation_engine import FactValidationEngine
            from ..utils.error_handling import ErrorMonitor, PerformanceMonitor
            
            # Stress test error monitoring
            error_monitor = ErrorMonitor()
            
            start_time = time.time()
            
            # Generate many errors quickly
            for i in range(1000):
                error_monitor.record_error(
                    Exception(f"Test error {i}"),
                    ErrorCategory.SYSTEM,
                    ErrorSeverity.LOW,
                    {"test_id": i}
                )
            
            error_stress_time = time.time() - start_time
            
            stress_results["error_monitoring"] = {
                "errors_recorded": 1000,
                "duration": error_stress_time,
                "errors_per_second": 1000 / error_stress_time if error_stress_time > 0 else 0,
                "memory_usage": len(error_monitor.error_history)
            }
            
            logger.info(f"📊 Error Monitoring Stress: 1000 errors in {error_stress_time:.3f}s")
            
            # Stress test performance monitoring
            perf_monitor = PerformanceMonitor()
            
            start_time = time.time()
            
            # Record many performance metrics
            for i in range(500):
                perf_monitor.record_performance(
                    f"operation_{i % 10}",
                    float(i % 30),  # Varying durations
                    {"iteration": i}
                )
            
            perf_stress_time = time.time() - start_time
            
            stress_results["performance_monitoring"] = {
                "metrics_recorded": 500,
                "duration": perf_stress_time,
                "metrics_per_second": 500 / perf_stress_time if perf_stress_time > 0 else 0,
                "unique_operations": len(perf_monitor.metrics)
            }
            
            logger.info(f"📊 Performance Monitoring Stress: 500 metrics in {perf_stress_time:.3f}s")
            
        except Exception as e:
            logger.error(f"❌ Stress test failed: {e}")
            stress_results["error"] = str(e)
        
        return stress_results
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all validation and error handling tests"""
        logger.info("🚀 Starting Comprehensive Validation Test Suite...")
        
        overall_start = time.time()
        
        # Run all test suites
        fact_validation_result = self.run_fact_validation_tests()
        error_handling_result = self.run_error_handling_tests()
        integration_result = self.run_integration_tests()
        
        # Run performance tests
        performance_benchmarks = self.run_performance_benchmarks()
        stress_test_results = self.run_stress_tests()
        
        overall_duration = time.time() - overall_start
        
        # Calculate overall results
        all_passed = all(
            result["status"] == "PASSED"
            for result in [fact_validation_result, error_handling_result, integration_result]
        )
        
        summary = {
            "overall_status": "PASSED" if all_passed else "FAILED",
            "total_duration": overall_duration,
            "test_results": self.test_results,
            "performance_benchmarks": performance_benchmarks,
            "stress_test_results": stress_test_results,
            "summary": {
                "total_test_suites": 3,
                "passed_suites": sum(1 for r in self.test_results.values() if r["status"] == "PASSED"),
                "failed_suites": sum(1 for r in self.test_results.values() if r["status"] == "FAILED")
            }
        }
        
        # Print summary
        self.print_test_summary(summary)
        
        return summary
    
    def print_test_summary(self, summary: Dict[str, Any]):
        """Print comprehensive test summary"""
        print("\n" + "=" * 80)
        print("🧪 FACT VALIDATION & ERROR HANDLING TEST SUMMARY")
        print("=" * 80)
        
        # Overall status
        status_emoji = "✅" if summary["overall_status"] == "PASSED" else "❌"
        print(f"{status_emoji} Overall Status: {summary['overall_status']}")
        print(f"⏱️  Total Duration: {summary['total_duration']:.2f} seconds")
        print()
        
        # Test suite results
        print("📋 Test Suite Results:")
        for suite_name, result in summary["test_results"].items():
            status_emoji = "✅" if result["status"] == "PASSED" else "❌"
            print(f"  {status_emoji} {suite_name.replace('_', ' ').title()}: {result['status']} ({result['duration']:.2f}s)")
        print()
        
        # Performance benchmarks
        if "performance_benchmarks" in summary and summary["performance_benchmarks"]:
            print("🚀 Performance Benchmarks:")
            benchmarks = summary["performance_benchmarks"]
            
            if "claim_extraction" in benchmarks:
                ce = benchmarks["claim_extraction"]
                print(f"  📊 Claim Extraction: {ce['claims_extracted']} claims in {ce['duration']:.3f}s ({ce['claims_per_second']:.1f} claims/sec)")
            
            if "validation" in benchmarks:
                val = benchmarks["validation"]
                print(f"  🔍 Validation: {val['claims_validated']} claims vs {val['registry_size']} statistics in {val['duration']:.3f}s")
            print()
        
        # Stress test results
        if "stress_test_results" in summary and summary["stress_test_results"]:
            print("💪 Stress Test Results:")
            stress = summary["stress_test_results"]
            
            if "error_monitoring" in stress:
                em = stress["error_monitoring"]
                print(f"  🚨 Error Monitoring: {em['errors_recorded']} errors in {em['duration']:.3f}s ({em['errors_per_second']:.1f} errors/sec)")
            
            if "performance_monitoring" in stress:
                pm = stress["performance_monitoring"]
                print(f"  📈 Performance Monitoring: {pm['metrics_recorded']} metrics in {pm['duration']:.3f}s ({pm['metrics_per_second']:.1f} metrics/sec)")
            print()
        
        # Summary statistics
        print("📊 Summary Statistics:")
        print(f"  Total Test Suites: {summary['summary']['total_test_suites']}")
        print(f"  Passed Suites: {summary['summary']['passed_suites']}")
        print(f"  Failed Suites: {summary['summary']['failed_suites']}")
        
        print("=" * 80)
        
        if summary["overall_status"] == "PASSED":
            print("🎉 All validation and error handling tests PASSED!")
        else:
            print("⚠️  Some tests FAILED. Check the detailed output above.")
        
        print("=" * 80)


def main():
    """Main test runner function"""
    runner = ValidationTestRunner()
    
    # Check if specific test suite is requested
    if len(sys.argv) > 1:
        test_type = sys.argv[1].lower()
        
        if test_type == "fact_validation":
            runner.run_fact_validation_tests()
        elif test_type == "error_handling":
            runner.run_error_handling_tests()
        elif test_type == "integration":
            runner.run_integration_tests()
        elif test_type == "performance":
            runner.run_performance_benchmarks()
        elif test_type == "stress":
            runner.run_stress_tests()
        else:
            print(f"Unknown test type: {test_type}")
            print("Available options: fact_validation, error_handling, integration, performance, stress")
            sys.exit(1)
    else:
        # Run all tests
        summary = runner.run_all_tests()
        
        # Exit with appropriate code
        sys.exit(0 if summary["overall_status"] == "PASSED" else 1)


if __name__ == "__main__":
    main()