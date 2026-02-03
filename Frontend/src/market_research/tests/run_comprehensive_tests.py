"""
Comprehensive test runner for Data Analysis Agent quality assurance.

This script runs all stress tests, integration tests, and security/performance
validation tests with proper reporting and metrics collection.
"""

import asyncio
import sys
import os
import time
import json
from pathlib import Path
from typing import Dict, Any, List
import subprocess
import argparse

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from .stress_test_config import StressTestConfig, StressTestReporter
from .integration_test_helpers import IntegrationTestEnvironment


class ComprehensiveTestRunner:
    """Runs comprehensive quality assurance tests with reporting."""
    
    def __init__(self, config: StressTestConfig):
        self.config = config
        self.results = {
            "stress_tests": {},
            "integration_tests": {},
            "security_tests": {},
            "performance_tests": {},
            "summary": {}
        }
        self.start_time = None
        self.end_time = None
    
    def run_all_tests(self, test_categories: List[str] = None) -> Dict[str, Any]:
        """Run all comprehensive tests."""
        self.start_time = time.time()
        
        if test_categories is None:
            test_categories = ["stress", "integration", "security", "performance"]
        
        print("🚀 Starting Comprehensive Quality Assurance Tests")
        print(f"📋 Test Categories: {', '.join(test_categories)}")
        print(f"⚙️  Configuration: {self.config}")
        print("-" * 80)
        
        try:
            if "stress" in test_categories:
                self._run_stress_tests()
            
            if "integration" in test_categories:
                self._run_integration_tests()
            
            if "security" in test_categories:
                self._run_security_tests()
            
            if "performance" in test_categories:
                self._run_performance_tests()
            
            self._generate_summary()
            
        except Exception as e:
            print(f"❌ Test execution failed: {e}")
            self.results["error"] = str(e)
        
        finally:
            self.end_time = time.time()
            self._save_results()
        
        return self.results
    
    def _run_stress_tests(self):
        """Run stress testing suite."""
        print("\n📊 Running Stress Tests...")
        
        stress_test_commands = [
            [
                "python", "-m", "pytest",
                "Backend/src/market_research/tests/test_stress_testing.py::TestStressTestingLargeDocuments::test_large_pdf_processing",
                "-v", "-s", "--tb=short"
            ],
            [
                "python", "-m", "pytest", 
                "Backend/src/market_research/tests/test_stress_testing.py::TestStressTestingLargeDocuments::test_large_csv_processing",
                "-v", "-s", "--tb=short"
            ],
            [
                "python", "-m", "pytest",
                "Backend/src/market_research/tests/test_stress_testing.py::TestConcurrentUserStressTesting::test_concurrent_analysis_execution",
                "-v", "-s", "--tb=short"
            ],
            [
                "python", "-m", "pytest",
                "Backend/src/market_research/tests/test_stress_testing.py::TestPerformanceUnderLoad::test_throughput_performance",
                "-v", "-s", "--tb=short"
            ]
        ]
        
        stress_results = {}
        
        for i, command in enumerate(stress_test_commands):
            test_name = f"stress_test_{i+1}"
            print(f"  🔄 Running {test_name}...")
            
            try:
                start_time = time.time()
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout per test
                )
                end_time = time.time()
                
                stress_results[test_name] = {
                    "status": "passed" if result.returncode == 0 else "failed",
                    "duration": end_time - start_time,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "return_code": result.returncode
                }
                
                if result.returncode == 0:
                    print(f"    ✅ {test_name} passed ({end_time - start_time:.2f}s)")
                else:
                    print(f"    ❌ {test_name} failed ({end_time - start_time:.2f}s)")
                    print(f"    Error: {result.stderr[:200]}...")
                
            except subprocess.TimeoutExpired:
                stress_results[test_name] = {
                    "status": "timeout",
                    "duration": 300,
                    "error": "Test timed out after 5 minutes"
                }
                print(f"    ⏰ {test_name} timed out")
            
            except Exception as e:
                stress_results[test_name] = {
                    "status": "error",
                    "error": str(e)
                }
                print(f"    💥 {test_name} error: {e}")
        
        self.results["stress_tests"] = stress_results
        
        # Summary
        passed = sum(1 for r in stress_results.values() if r.get("status") == "passed")
        total = len(stress_results)
        print(f"📊 Stress Tests Summary: {passed}/{total} passed")
    
    def _run_integration_tests(self):
        """Run integration testing suite."""
        print("\n🔗 Running Integration Tests...")
        
        integration_test_commands = [
            [
                "python", "-m", "pytest",
                "Backend/src/market_research/tests/test_end_to_end_integration.py::TestEndToEndWorkflow::test_complete_analysis_workflow",
                "-v", "-s", "--tb=short"
            ],
            [
                "python", "-m", "pytest",
                "Backend/src/market_research/tests/test_end_to_end_integration.py::TestVMPServiceIntegration::test_field_prep_integration",
                "-v", "-s", "--tb=short"
            ],
            [
                "python", "-m", "pytest",
                "Backend/src/market_research/tests/test_end_to_end_integration.py::TestErrorScenariosAndRecovery::test_missing_project_context_error",
                "-v", "-s", "--tb=short"
            ]
        ]
        
        integration_results = {}
        
        for i, command in enumerate(integration_test_commands):
            test_name = f"integration_test_{i+1}"
            print(f"  🔄 Running {test_name}...")
            
            try:
                start_time = time.time()
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=180  # 3 minute timeout per test
                )
                end_time = time.time()
                
                integration_results[test_name] = {
                    "status": "passed" if result.returncode == 0 else "failed",
                    "duration": end_time - start_time,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "return_code": result.returncode
                }
                
                if result.returncode == 0:
                    print(f"    ✅ {test_name} passed ({end_time - start_time:.2f}s)")
                else:
                    print(f"    ❌ {test_name} failed ({end_time - start_time:.2f}s)")
                    print(f"    Error: {result.stderr[:200]}...")
                
            except subprocess.TimeoutExpired:
                integration_results[test_name] = {
                    "status": "timeout",
                    "duration": 180,
                    "error": "Test timed out after 3 minutes"
                }
                print(f"    ⏰ {test_name} timed out")
            
            except Exception as e:
                integration_results[test_name] = {
                    "status": "error",
                    "error": str(e)
                }
                print(f"    💥 {test_name} error: {e}")
        
        self.results["integration_tests"] = integration_results
        
        # Summary
        passed = sum(1 for r in integration_results.values() if r.get("status") == "passed")
        total = len(integration_results)
        print(f"🔗 Integration Tests Summary: {passed}/{total} passed")
    
    def _run_security_tests(self):
        """Run security validation tests."""
        print("\n🔒 Running Security Tests...")
        
        security_test_commands = [
            [
                "python", "-m", "pytest",
                "Backend/src/market_research/tests/test_security_performance_validation.py::TestFileUploadSecurity::test_malicious_pdf_detection",
                "-v", "-s", "--tb=short"
            ],
            [
                "python", "-m", "pytest",
                "Backend/src/market_research/tests/test_security_performance_validation.py::TestTenantIsolationAndAccessControl::test_tenant_isolation",
                "-v", "-s", "--tb=short"
            ],
            [
                "python", "-m", "pytest",
                "Backend/src/market_research/tests/test_security_performance_validation.py::TestSecurityComplianceValidation::test_input_validation_completeness",
                "-v", "-s", "--tb=short"
            ]
        ]
        
        security_results = {}
        
        for i, command in enumerate(security_test_commands):
            test_name = f"security_test_{i+1}"
            print(f"  🔄 Running {test_name}...")
            
            try:
                start_time = time.time()
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=120  # 2 minute timeout per test
                )
                end_time = time.time()
                
                security_results[test_name] = {
                    "status": "passed" if result.returncode == 0 else "failed",
                    "duration": end_time - start_time,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "return_code": result.returncode
                }
                
                if result.returncode == 0:
                    print(f"    ✅ {test_name} passed ({end_time - start_time:.2f}s)")
                else:
                    print(f"    ❌ {test_name} failed ({end_time - start_time:.2f}s)")
                    print(f"    Error: {result.stderr[:200]}...")
                
            except subprocess.TimeoutExpired:
                security_results[test_name] = {
                    "status": "timeout",
                    "duration": 120,
                    "error": "Test timed out after 2 minutes"
                }
                print(f"    ⏰ {test_name} timed out")
            
            except Exception as e:
                security_results[test_name] = {
                    "status": "error",
                    "error": str(e)
                }
                print(f"    💥 {test_name} error: {e}")
        
        self.results["security_tests"] = security_results
        
        # Summary
        passed = sum(1 for r in security_results.values() if r.get("status") == "passed")
        total = len(security_results)
        print(f"🔒 Security Tests Summary: {passed}/{total} passed")
    
    def _run_performance_tests(self):
        """Run performance validation tests."""
        print("\n⚡ Running Performance Tests...")
        
        performance_test_commands = [
            [
                "python", "-m", "pytest",
                "Backend/src/market_research/tests/test_security_performance_validation.py::TestLoadTestingAndPerformance::test_concurrent_analysis_load",
                "-v", "-s", "--tb=short"
            ],
            [
                "python", "-m", "pytest",
                "Backend/src/market_research/tests/test_security_performance_validation.py::TestLoadTestingAndPerformance::test_memory_usage_under_load",
                "-v", "-s", "--tb=short"
            ],
            [
                "python", "-m", "pytest",
                "Backend/src/market_research/tests/test_security_performance_validation.py::TestLoadTestingAndPerformance::test_response_time_optimization",
                "-v", "-s", "--tb=short"
            ]
        ]
        
        performance_results = {}
        
        for i, command in enumerate(performance_test_commands):
            test_name = f"performance_test_{i+1}"
            print(f"  🔄 Running {test_name}...")
            
            try:
                start_time = time.time()
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=240  # 4 minute timeout per test
                )
                end_time = time.time()
                
                performance_results[test_name] = {
                    "status": "passed" if result.returncode == 0 else "failed",
                    "duration": end_time - start_time,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "return_code": result.returncode
                }
                
                if result.returncode == 0:
                    print(f"    ✅ {test_name} passed ({end_time - start_time:.2f}s)")
                else:
                    print(f"    ❌ {test_name} failed ({end_time - start_time:.2f}s)")
                    print(f"    Error: {result.stderr[:200]}...")
                
            except subprocess.TimeoutExpired:
                performance_results[test_name] = {
                    "status": "timeout",
                    "duration": 240,
                    "error": "Test timed out after 4 minutes"
                }
                print(f"    ⏰ {test_name} timed out")
            
            except Exception as e:
                performance_results[test_name] = {
                    "status": "error",
                    "error": str(e)
                }
                print(f"    💥 {test_name} error: {e}")
        
        self.results["performance_tests"] = performance_results
        
        # Summary
        passed = sum(1 for r in performance_results.values() if r.get("status") == "passed")
        total = len(performance_results)
        print(f"⚡ Performance Tests Summary: {passed}/{total} passed")
    
    def _generate_summary(self):
        """Generate overall test summary."""
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        timeout_tests = 0
        error_tests = 0
        
        for category, tests in self.results.items():
            if category == "summary":
                continue
            
            for test_name, test_result in tests.items():
                total_tests += 1
                status = test_result.get("status", "unknown")
                
                if status == "passed":
                    passed_tests += 1
                elif status == "failed":
                    failed_tests += 1
                elif status == "timeout":
                    timeout_tests += 1
                else:
                    error_tests += 1
        
        total_duration = self.end_time - self.start_time if self.end_time and self.start_time else 0
        
        self.results["summary"] = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "timeout_tests": timeout_tests,
            "error_tests": error_tests,
            "success_rate": passed_tests / total_tests if total_tests > 0 else 0,
            "total_duration": total_duration,
            "timestamp": time.time()
        }
    
    def _save_results(self):
        """Save test results to file."""
        os.makedirs("test_reports", exist_ok=True)
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"test_reports/comprehensive_test_results_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n📄 Test results saved to: {filename}")
        
        # Generate human-readable report
        self._generate_human_readable_report(timestamp)
    
    def _generate_human_readable_report(self, timestamp: str):
        """Generate human-readable test report."""
        summary = self.results["summary"]
        
        report = f"""
# Comprehensive Quality Assurance Test Report
Generated: {time.strftime("%Y-%m-%d %H:%M:%S")}

## Overall Summary
- **Total Tests**: {summary['total_tests']}
- **Passed**: {summary['passed_tests']} ✅
- **Failed**: {summary['failed_tests']} ❌
- **Timeouts**: {summary['timeout_tests']} ⏰
- **Errors**: {summary['error_tests']} 💥
- **Success Rate**: {summary['success_rate']:.1%}
- **Total Duration**: {summary['total_duration']:.2f} seconds

## Test Categories

### Stress Tests
"""
        
        # Add details for each category
        for category, tests in self.results.items():
            if category == "summary":
                continue
            
            category_name = category.replace("_", " ").title()
            report += f"\n### {category_name}\n"
            
            for test_name, test_result in tests.items():
                status = test_result.get("status", "unknown")
                duration = test_result.get("duration", 0)
                
                status_emoji = {
                    "passed": "✅",
                    "failed": "❌", 
                    "timeout": "⏰",
                    "error": "💥"
                }.get(status, "❓")
                
                report += f"- **{test_name}**: {status_emoji} {status.upper()} ({duration:.2f}s)\n"
                
                if status != "passed" and "error" in test_result:
                    report += f"  - Error: {test_result['error']}\n"
        
        # Recommendations
        report += f"""
## Recommendations

### Performance
- Monitor memory usage during concurrent operations
- Optimize database connection pooling
- Implement proper rate limiting

### Security
- Ensure all file uploads are properly validated
- Maintain strict tenant isolation
- Implement comprehensive audit logging

### Reliability
- Add retry mechanisms for transient failures
- Improve error handling and recovery
- Monitor system resources under load

## Next Steps
1. Address any failed tests before production deployment
2. Set up continuous monitoring for performance metrics
3. Implement automated security scanning
4. Schedule regular stress testing
"""
        
        report_filename = f"test_reports/comprehensive_test_report_{timestamp}.md"
        with open(report_filename, 'w') as f:
            f.write(report)
        
        print(f"📋 Human-readable report saved to: {report_filename}")


def main():
    """Main entry point for comprehensive test runner."""
    parser = argparse.ArgumentParser(description="Run comprehensive quality assurance tests")
    parser.add_argument(
        "--categories",
        nargs="+",
        choices=["stress", "integration", "security", "performance"],
        default=["stress", "integration", "security", "performance"],
        help="Test categories to run"
    )
    parser.add_argument(
        "--config",
        help="Path to test configuration file"
    )
    
    args = parser.parse_args()
    
    # Load configuration
    if args.config and os.path.exists(args.config):
        with open(args.config, 'r') as f:
            config_data = json.load(f)
        config = StressTestConfig(**config_data)
    else:
        config = StressTestConfig.from_environment()
    
    # Run tests
    runner = ComprehensiveTestRunner(config)
    results = runner.run_all_tests(args.categories)
    
    # Print final summary
    summary = results["summary"]
    print("\n" + "=" * 80)
    print("🎯 FINAL RESULTS")
    print("=" * 80)
    print(f"✅ Passed: {summary['passed_tests']}")
    print(f"❌ Failed: {summary['failed_tests']}")
    print(f"⏰ Timeouts: {summary['timeout_tests']}")
    print(f"💥 Errors: {summary['error_tests']}")
    print(f"📊 Success Rate: {summary['success_rate']:.1%}")
    print(f"⏱️  Total Duration: {summary['total_duration']:.2f} seconds")
    
    # Exit with appropriate code
    if summary['failed_tests'] > 0 or summary['error_tests'] > 0:
        print("\n❌ Some tests failed. Check the detailed report for more information.")
        sys.exit(1)
    else:
        print("\n🎉 All tests passed successfully!")
        sys.exit(0)


if __name__ == "__main__":
    main()