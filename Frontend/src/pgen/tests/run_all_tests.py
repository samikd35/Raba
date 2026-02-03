#!/usr/bin/env python3
"""
Test Runner for Problem Generator LangGraph

This script runs all tests for the Problem Generator workflow:
1. Sequential node tests
2. Full workflow tests
3. Performance benchmarks
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# Add the project root to the path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Import test modules
from test_nodes_sequential import NodeTester
from test_full_workflow import WorkflowTester

# Configure logging
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TestRunner:
    """Comprehensive test runner for Problem Generator"""
    
    def __init__(self, test_data_dir: str):
        self.test_data_dir = Path(test_data_dir)
        self.test_data_dir.mkdir(exist_ok=True)
        self.all_results = {}
        self.start_time = None
        self.end_time = None
    
    async def run_all_tests(self):
        """Run all test suites"""
        logger.info("🚀 Starting comprehensive Problem Generator testing...")
        self.start_time = datetime.now()
        
        try:
            # 1. Run sequential node tests
            logger.info("\\n" + "="*80)
            logger.info("PHASE 1: SEQUENTIAL NODE TESTING")
            logger.info("="*80)
            
            node_tester = NodeTester(self.test_data_dir)
            await node_tester.run_sequential_tests()
            self.all_results["sequential_nodes"] = node_tester.test_results
            
            # 2. Run full workflow tests
            logger.info("\\n" + "="*80)
            logger.info("PHASE 2: FULL WORKFLOW TESTING")
            logger.info("="*80)
            
            workflow_tester = WorkflowTester(self.test_data_dir)
            
            # Load mock input
            user_params = workflow_tester.load_mock_input()
            
            # Setup graph
            workflow_tester.setup_graph()
            
            # Get workflow info
            workflow_info = workflow_tester.get_workflow_info()
            self.all_results["workflow_info"] = workflow_info
            
            # Test regular workflow execution
            await workflow_tester.test_workflow_execution(user_params)
            
            # Test streaming workflow execution
            await workflow_tester.test_workflow_streaming(user_params)
            
            # Store workflow results
            self.all_results["workflow_tests"] = workflow_tester.test_results
            
            # 3. Generate comprehensive report
            self.end_time = datetime.now()
            self.generate_comprehensive_report()
            
            logger.info("\\n🏁 All tests completed successfully!")
            
        except Exception as e:
            self.end_time = datetime.now()
            logger.error(f"❌ Test suite failed: {str(e)}")
            self.generate_error_report(str(e))
            raise e
    
    def generate_comprehensive_report(self):
        """Generate a comprehensive test report"""
        logger.info("\\n" + "="*80)
        logger.info("COMPREHENSIVE TEST REPORT")
        logger.info("="*80)
        
        total_time = (self.end_time - self.start_time).total_seconds()
        
        # Overall statistics
        logger.info(f"⏱️  Total testing time: {total_time:.2f}s")
        logger.info(f"📅 Test date: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Sequential node test results
        if "sequential_nodes" in self.all_results:
            node_results = self.all_results["sequential_nodes"]
            total_nodes = len(node_results)
            successful_nodes = sum(1 for r in node_results.values() if r["status"] == "success")
            failed_nodes = total_nodes - successful_nodes
            
            logger.info(f"\\n📊 SEQUENTIAL NODE TESTS:")
            logger.info(f"   Total nodes: {total_nodes}")
            logger.info(f"   ✅ Successful: {successful_nodes}")
            logger.info(f"   ❌ Failed: {failed_nodes}")
            logger.info(f"   Success rate: {(successful_nodes/total_nodes)*100:.1f}%")
            
            if successful_nodes > 0:
                avg_node_time = sum(r["execution_time"] for r in node_results.values() if r["status"] == "success") / successful_nodes
                logger.info(f"   Average node time: {avg_node_time:.2f}s")
        
        # Workflow test results
        if "workflow_tests" in self.all_results:
            workflow_results = self.all_results["workflow_tests"]
            
            logger.info(f"\\n🌊 WORKFLOW TESTS:")
            for test_name, result in workflow_results.items():
                status_emoji = "✅" if result["status"] == "success" else "❌"
                logger.info(f"   {status_emoji} {test_name}:")
                logger.info(f"      Time: {result['execution_time']:.2f}s")
                logger.info(f"      Status: {result.get('workflow_status', 'unknown')}")
                
                if result.get("final_problems_count") is not None:
                    logger.info(f"      Problems generated: {result['final_problems_count']}")
        
        # Performance benchmarks
        self.generate_performance_benchmarks()
        
        # Save comprehensive report
        self.save_comprehensive_report()
    
    def generate_performance_benchmarks(self):
        """Generate performance benchmarks"""
        logger.info(f"\\n⚡ PERFORMANCE BENCHMARKS:")
        
        # Node performance analysis
        if "sequential_nodes" in self.all_results:
            node_results = self.all_results["sequential_nodes"]
            
            # Find slowest and fastest nodes
            successful_nodes = {k: v for k, v in node_results.items() if v["status"] == "success"}
            
            if successful_nodes:
                slowest_node = max(successful_nodes.items(), key=lambda x: x[1]["execution_time"])
                fastest_node = min(successful_nodes.items(), key=lambda x: x[1]["execution_time"])
                
                logger.info(f"   🐌 Slowest node: {slowest_node[0]} ({slowest_node[1]['execution_time']:.2f}s)")
                logger.info(f"   🚀 Fastest node: {fastest_node[0]} ({fastest_node[1]['execution_time']:.2f}s)")
                
                # Calculate total pipeline time
                total_pipeline_time = sum(r["execution_time"] for r in successful_nodes.values())
                logger.info(f"   🔗 Total pipeline time: {total_pipeline_time:.2f}s")
        
        # Workflow performance analysis
        if "workflow_tests" in self.all_results:
            workflow_results = self.all_results["workflow_tests"]
            
            for test_name, result in workflow_results.items():
                if result["status"] == "success":
                    problems_per_second = result.get("final_problems_count", 0) / result["execution_time"]
                    logger.info(f"   📈 {test_name} throughput: {problems_per_second:.2f} problems/second")
    
    def save_comprehensive_report(self):
        """Save the comprehensive report to file"""
        report_data = {
            "test_summary": {
                "start_time": self.start_time.isoformat(),
                "end_time": self.end_time.isoformat(),
                "total_duration": (self.end_time - self.start_time).total_seconds(),
                "test_date": self.start_time.strftime('%Y-%m-%d'),
                "test_time": self.start_time.strftime('%H:%M:%S')
            },
            "results": self.all_results
        }
        
        report_file = self.test_data_dir / "comprehensive_test_report.json"
        
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        logger.info(f"💾 Comprehensive report saved to {report_file}")
        
        # Also create a human-readable summary
        self.create_human_readable_summary()
    
    def create_human_readable_summary(self):
        """Create a human-readable test summary"""
        summary_file = self.test_data_dir / "test_summary.md"
        
        with open(summary_file, 'w') as f:
            f.write("# Problem Generator Test Report\\n\\n")
            f.write(f"**Test Date:** {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}\\n")
            f.write(f"**Total Duration:** {(self.end_time - self.start_time).total_seconds():.2f} seconds\\n\\n")
            
            # Sequential node results
            if "sequential_nodes" in self.all_results:
                f.write("## Sequential Node Tests\\n\\n")
                node_results = self.all_results["sequential_nodes"]
                
                for node_name, result in node_results.items():
                    status = "✅ PASS" if result["status"] == "success" else "❌ FAIL"
                    f.write(f"- **{node_name}**: {status} ({result['execution_time']:.2f}s)\\n")
                    if result["error"]:
                        f.write(f"  - Error: {result['error']}\\n")
                f.write("\\n")
            
            # Workflow test results
            if "workflow_tests" in self.all_results:
                f.write("## Workflow Tests\\n\\n")
                workflow_results = self.all_results["workflow_tests"]
                
                for test_name, result in workflow_results.items():
                    status = "✅ PASS" if result["status"] == "success" else "❌ FAIL"
                    f.write(f"- **{test_name}**: {status} ({result['execution_time']:.2f}s)\\n")
                    if result.get("final_problems_count") is not None:
                        f.write(f"  - Problems generated: {result['final_problems_count']}\\n")
                    if result["error"]:
                        f.write(f"  - Error: {result['error']}\\n")
        
        logger.info(f"📄 Human-readable summary saved to {summary_file}")
    
    def generate_error_report(self, error_message: str):
        """Generate an error report if tests fail"""
        error_report = {
            "error": error_message,
            "test_duration": (self.end_time - self.start_time).total_seconds() if self.end_time else 0,
            "partial_results": self.all_results,
            "timestamp": datetime.now().isoformat()
        }
        
        error_file = self.test_data_dir / "error_report.json"
        
        with open(error_file, 'w') as f:
            json.dump(error_report, f, indent=2, default=str)
        
        logger.info(f"💾 Error report saved to {error_file}")

async def main():
    """Main test runner execution"""
    # Set up test data directory
    test_data_dir = Path(__file__).parent / "test_data"
    
    # Create test runner
    runner = TestRunner(test_data_dir)
    
    # Run all tests
    await runner.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
