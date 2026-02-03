# Data Analysis Agent - Comprehensive Testing Suite

This directory contains comprehensive quality assurance tests for the Data Analysis Agent, including stress testing, integration testing, and security/performance validation.

## Test Categories

### 1. Stress Testing (`test_stress_testing.py`)
Tests system behavior under extreme conditions:
- **Large Document Processing**: 100+ page PDFs, 10,000+ row CSV files
- **Concurrent User Load**: Multiple users running analysis simultaneously  
- **Memory Usage Validation**: Memory consumption and leak detection
- **Performance Under Load**: Throughput and resource utilization

### 2. End-to-End Integration Testing (`test_end_to_end_integration.py`)
Tests complete workflow integration:
- **Complete Analysis Workflow**: File upload to report generation
- **VMP Service Integration**: Integration with Field Prep and existing services
- **Error Scenarios**: Recovery mechanisms and error handling
- **API Endpoint Integration**: RESTful API functionality

### 3. Security & Performance Validation (`test_security_performance_validation.py`)
Tests security and performance aspects:
- **File Upload Security**: Malicious content detection and sanitization
- **Tenant Isolation**: Cross-tenant data access prevention
- **Access Control**: User permission validation
- **Load Testing**: Concurrent request handling
- **Performance Optimization**: Response time and resource efficiency

## Running Tests

### Quick Test Execution
```bash
# Run all tests
python -m pytest Backend/src/market_research/tests/ -v

# Run specific test category
python -m pytest Backend/src/market_research/tests/test_stress_testing.py -v
python -m pytest Backend/src/market_research/tests/test_end_to_end_integration.py -v
python -m pytest Backend/src/market_research/tests/test_security_performance_validation.py -v

# Run tests with specific markers
python -m pytest -m "stress" -v
python -m pytest -m "integration" -v
python -m pytest -m "security" -v
```

### Comprehensive Test Suite
```bash
# Run comprehensive test suite with reporting
python Backend/src/market_research/tests/run_comprehensive_tests.py

# Run specific categories
python Backend/src/market_research/tests/run_comprehensive_tests.py --categories stress integration

# Use custom configuration
python Backend/src/market_research/tests/run_comprehensive_tests.py --config test_config.json
```

## Test Configuration

### Environment Variables
Configure test parameters using environment variables:

```bash
# Stress test configuration
export STRESS_TEST_PDF_PAGES=150
export STRESS_TEST_CSV_ROWS=12000
export STRESS_TEST_MAX_USERS=20
export STRESS_TEST_MAX_MEMORY_MB=3000

# Performance thresholds
export STRESS_TEST_MAX_PDF_TIME=30.0
export STRESS_TEST_MAX_CSV_TIME=20.0
export STRESS_TEST_TARGET_RPS=5.0
```

### Configuration File
Create `test_config.json` for custom configuration:

```json
{
  "large_pdf_pages": 150,
  "large_csv_rows": 12000,
  "max_concurrent_users": 20,
  "max_memory_usage": 3000.0,
  "target_requests_per_second": 5.0,
  "max_error_rate": 0.1
}
```

## Test Data

### Stress Test Data
- **Large PDF**: 150-page interview transcripts with realistic content
- **Large CSV**: 12,000-row survey data with comprehensive fields
- **Concurrent Scenarios**: Multiple user simulation with realistic load patterns

### Integration Test Data
- **Complete Project Data**: Full VMP project with personas, assumptions, and context
- **Research Documents**: Realistic interview transcripts and survey responses
- **Error Scenarios**: Various failure conditions and edge cases

### Security Test Data
- **Malicious Content**: PDF with JavaScript, CSV with formula injection
- **Invalid Files**: Wrong file types, oversized files, corrupted content
- **Access Control**: Cross-tenant access attempts, unauthorized operations

## Performance Benchmarks

### Expected Performance Thresholds
- **PDF Processing**: < 30 seconds for 150-page documents
- **CSV Processing**: < 20 seconds for 12,000-row files
- **Memory Usage**: < 3GB peak memory consumption
- **Concurrent Load**: Handle 20+ concurrent users
- **Error Rate**: < 10% under normal load, < 5% under concurrent load
- **Throughput**: 5+ requests per second sustained

### Resource Limits
- **Memory Growth**: < 2x increase during test execution
- **CPU Usage**: < 90% peak utilization
- **Response Time**: < 10 seconds for analysis completion
- **Recovery Time**: < 0.5 seconds for error recovery

## Test Reports

### Automated Reporting
Test results are automatically saved to:
- `test_reports/comprehensive_test_results_YYYYMMDD_HHMMSS.json` - Machine-readable results
- `test_reports/comprehensive_test_report_YYYYMMDD_HHMMSS.md` - Human-readable report

### Report Contents
- **Overall Summary**: Pass/fail rates, duration, success metrics
- **Category Breakdown**: Detailed results per test category
- **Performance Metrics**: Memory usage, response times, throughput
- **Error Analysis**: Failed test details and error messages
- **Recommendations**: Actionable items for improvement

## Troubleshooting

### Common Issues

#### Memory Errors
```bash
# Increase available memory for tests
export PYTEST_CURRENT_TEST_MEMORY_LIMIT=4000
```

#### Timeout Issues
```bash
# Increase test timeouts
export PYTEST_TIMEOUT=600
```

#### Mock Service Failures
Ensure all required mock services are properly configured in test fixtures.

#### Database Connection Issues
Verify database adapters are properly mocked in integration tests.

### Debug Mode
```bash
# Run tests with debug output
python -m pytest Backend/src/market_research/tests/ -v -s --tb=long

# Run single test with debugging
python -m pytest Backend/src/market_research/tests/test_stress_testing.py::TestStressTestingLargeDocuments::test_large_pdf_processing -v -s
```

## Continuous Integration

### CI/CD Integration
Add to your CI/CD pipeline:

```yaml
# Example GitHub Actions workflow
- name: Run Comprehensive Tests
  run: |
    python Backend/src/market_research/tests/run_comprehensive_tests.py
    
- name: Upload Test Reports
  uses: actions/upload-artifact@v2
  with:
    name: test-reports
    path: test_reports/
```

### Quality Gates
Recommended quality gates for production deployment:
- **All security tests must pass** (0% failure tolerance)
- **Integration tests pass rate > 95%**
- **Stress tests pass rate > 90%**
- **Performance benchmarks met**
- **No critical security vulnerabilities**

## Contributing

### Adding New Tests
1. Follow existing test patterns and naming conventions
2. Include appropriate test markers (`@pytest.mark.stress`, etc.)
3. Add comprehensive docstrings and comments
4. Update this README with new test descriptions

### Test Data Guidelines
- Use realistic, representative test data
- Avoid sensitive or personally identifiable information
- Create reusable test data generators
- Document test data sources and formats

### Performance Considerations
- Mock external services to avoid network dependencies
- Use appropriate timeouts for long-running tests
- Clean up resources in test teardown
- Monitor memory usage in resource-intensive tests