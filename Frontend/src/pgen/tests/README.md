# Problem Generator Testing Framework

This directory contains comprehensive testing tools for the Problem Generator LangGraph workflow.

## Test Structure

```
tests/
├── test_data/                          # Test data and results
│   ├── mock_user_input.json           # Sample user input
│   ├── initial_state.json             # Initial workflow state
│   ├── state_after_*.json             # Node output states
│   ├── workflow_*.json                 # Workflow execution states
│   └── *_test_results.json            # Test result summaries
├── test_nodes_sequential.py           # Sequential node testing
├── test_full_workflow.py              # Complete workflow testing
├── test_individual_node.py            # Individual node debugging
├── run_all_tests.py                   # Comprehensive test runner
└── README.md                          # This documentation
```

## Test Scripts

### 1. Sequential Node Testing (`test_nodes_sequential.py`)

Tests each node individually in sequence, using the output from each node as input to the next.

**Features:**
- Tests all 12 nodes sequentially
- Saves state after each node execution
- Provides detailed logging and metrics
- Handles async/sync node functions
- Generates comprehensive test reports

**Usage:**
```bash
cd /Users/samikd/MyProjects/MIntel/Backend/src/pgen/tests
python test_nodes_sequential.py
```

**Output Files:**
- `test_data/state_after_<node_name>.json` - State after each node
- `test_data/test_results.json` - Summary of all node test results

### 2. Full Workflow Testing (`test_full_workflow.py`)

Tests the complete LangGraph workflow execution including streaming.

**Features:**
- Tests regular workflow execution
- Tests streaming workflow execution
- Measures end-to-end performance
- Validates final problem statement generation
- Captures workflow metadata

**Usage:**
```bash
cd /Users/samikd/MyProjects/MIntel/Backend/src/pgen/tests
python test_full_workflow.py
```

**Output Files:**
- `test_data/workflow_*.json` - Workflow execution states
- `test_data/workflow_test_results.json` - Workflow test summary

### 3. Individual Node Testing (`test_individual_node.py`)

Debug and test individual nodes with custom input data.

**Features:**
- Test any single node in isolation
- Load custom input states
- Detailed node-specific output logging
- Useful for debugging specific issues
- Chain multiple nodes for partial workflow testing

**Usage:**
```bash
cd /Users/samikd/MyProjects/MIntel/Backend/src/pgen/tests
python test_individual_node.py
```

**Customization:**
Edit the `main()` function to test specific nodes:
```python
# Test specific node
await tester.test_node("parameter_validator", test_state)

# Chain nodes
result1 = await tester.test_node("parameter_validator", test_state)
result2 = await tester.test_node("query_expander", result1)
```

### 4. Comprehensive Test Runner (`run_all_tests.py`)

Runs all test suites and generates comprehensive reports.

**Features:**
- Executes sequential node tests
- Executes full workflow tests
- Generates performance benchmarks
- Creates human-readable summaries
- Comprehensive error reporting

**Usage:**
```bash
cd /Users/samikd/MyProjects/MIntel/Backend/src/pgen/tests
python run_all_tests.py
```

**Output Files:**
- `test_data/comprehensive_test_report.json` - Complete test results
- `test_data/test_summary.md` - Human-readable summary

## Test Data

### Mock User Input (`test_data/mock_user_input.json`)

Sample user input representing a typical problem generation request:

```json
{
  "industry": "fintech",
  "region": "east_africa",
  "problem_type": "market_access",
  "urgency": "high",
  "impact_scale": "national",
  "stakeholder": "sme_businesses",
  "time_horizon": "short_term",
  "resource_constraint": "funding",
  "market_maturity": "emerging",
  "regulatory_environment": "complex",
  "cultural_context": "traditional_banking"
}
```

### Initial State (`test_data/initial_state.json`)

Complete initial workflow state with all required fields and configuration.

## Running Tests

### Prerequisites

Ensure you have the required dependencies and environment variables set up:

1. **Environment Variables:**
   - `OPENAI_API_KEY` - For LLM operations
   - `SUPABASE_URL` and `SUPABASE_ANON_KEY` - For database operations
   - `BRAVE_API_KEY` or `SERPER_API_KEY` - For news search
   - `TAVILY_API_KEY` - For deep search
   - `FIRECRAWL_API_KEY` - For web scraping

2. **Dependencies:**
   ```bash
   pip install openai supabase langchain langgraph scikit-learn numpy
   ```

### Quick Start

1. **Run all tests:**
   ```bash
   cd /Users/samikd/MyProjects/MIntel/Backend/src/pgen/tests
   python run_all_tests.py
   ```

2. **Test individual components:**
   ```bash
   # Test nodes sequentially
   python test_nodes_sequential.py
   
   # Test full workflow
   python test_full_workflow.py
   
   # Debug specific node
   python test_individual_node.py
   ```

### Interpreting Results

#### Success Indicators
- ✅ All nodes complete without errors
- 📊 Reasonable execution times (< 30s per node)
- 🎯 Final problem statements generated (3-5 statements)
- 📈 High relevance scores (> 0.7)

#### Common Issues
- ❌ **API Key Errors:** Check environment variables
- ⏱️ **Timeout Errors:** Increase timeout in config
- 🔍 **Empty Results:** Check search API connectivity
- 🤖 **LLM Errors:** Verify OpenAI API key and model access

## Customizing Tests

### Adding New Test Cases

1. **Create new mock input:**
   ```json
   {
     "industry": "healthcare",
     "region": "west_africa",
     "problem_type": "access_to_care",
     // ... other parameters
   }
   ```

2. **Modify test scripts:**
   ```python
   # Load custom input
   custom_input = tester.load_custom_input("custom_input.json")
   
   # Run tests with custom input
   await tester.test_workflow_execution(custom_input)
   ```

### Performance Benchmarking

The test framework automatically generates performance benchmarks:

- **Node Performance:** Execution time per node
- **Throughput:** Problems generated per second
- **Resource Usage:** Memory and CPU utilization
- **Bottleneck Analysis:** Slowest nodes identification

### Debugging Failed Tests

1. **Check error logs:** Look for specific error messages
2. **Examine state files:** Review `state_after_<node>_FAILED.json`
3. **Test individual nodes:** Use `test_individual_node.py`
4. **Verify configuration:** Check API keys and model settings

## Integration with CI/CD

The test framework is designed for integration with continuous integration:

```yaml
# Example GitHub Actions workflow
- name: Run Problem Generator Tests
  run: |
    cd Backend/src/pgen/tests
    python run_all_tests.py
    
- name: Upload Test Results
  uses: actions/upload-artifact@v2
  with:
    name: test-results
    path: Backend/src/pgen/tests/test_data/
```

## Contributing

When adding new nodes or modifying existing ones:

1. **Update test data:** Ensure mock input covers new parameters
2. **Add node-specific logging:** Update `_log_node_outputs()` methods
3. **Test thoroughly:** Run all test suites before committing
4. **Update documentation:** Modify this README for new features

## Support

For issues with the testing framework:

1. Check the error logs in `test_data/`
2. Verify environment setup and API keys
3. Run individual node tests to isolate issues
4. Review the comprehensive test report for detailed diagnostics
