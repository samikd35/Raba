"""
Performance Benchmarking Script for Market Research Analysis

Provides comprehensive performance benchmarking and monitoring for the enhanced
market research analysis system, including scalability testing and optimization validation.
"""

import asyncio
import time
import psutil
import json
import csv
import io
from typing import Dict, Any, List, Tuple
from datetime import datetime
import matplotlib.pyplot as plt
import pandas as pd
from dataclasses import dataclass, asdict
from pathlib import Path

from ..services.performance_optimizer import (
    StreamingCSVProcessor, BatchPDFProcessor,
    EfficientEmbeddingGenerator, IntelligentChunkingStrategy
)
from ..services.caching_optimization_system import (
    StatisticsRegistryCache, TokenBudgetOptimizer, ResourceManager
)


@dataclass
class BenchmarkResult:
    """Benchmark result data structure."""
    test_name: str
    data_size: int
    processing_time: float
    memory_usage_mb: float
    peak_memory_mb: float
    throughput: float  # items per second
    success: bool
    error_message: str = ""
    metadata: Dict[str, Any] = None


class PerformanceBenchmark:
    """
    Comprehensive performance benchmarking suite for market research analysis.
    
    Features:
    - CSV processing benchmarks with various data sizes
    - PDF processing benchmarks with different page counts
    - Caching effectiveness measurements
    - Concurrent processing tests
    - Memory usage profiling
    - Scalability limit identification
    """
    
    def __init__(self, output_dir: str = "benchmark_results"):
        """Initialize performance benchmark suite."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.results: List[BenchmarkResult] = []
        self.process = psutil.Process()
        
    async def run_all_benchmarks(self) -> Dict[str, Any]:
        """Run complete benchmark suite."""
        print("🚀 Starting Performance Benchmark Suite")
        print("=" * 50)
        
        start_time = time.time()
        
        # CSV Processing Benchmarks
        await self._benchmark_csv_processing()
        
        # PDF Processing Benchmarks
        await self._benchmark_pdf_processing()
        
        # Caching Benchmarks
        await self._benchmark_caching_system()
        
        # Token Optimization Benchmarks
        await self._benchmark_token_optimization()
        
        # Concurrent Processing Benchmarks
        await self._benchmark_concurrent_processing()
        
        # Memory Usage Benchmarks
        await self._benchmark_memory_usage()
        
        total_time = time.time() - start_time
        
        # Generate report
        report = self._generate_benchmark_report(total_time)
        
        # Save results
        await self._save_results()
        
        print(f"\n✅ Benchmark suite completed in {total_time:.2f}s")
        print(f"📊 Results saved to {self.output_dir}")
        
        return report
    
    async def _benchmark_csv_processing(self):
        """Benchmark CSV processing with various data sizes."""
        print("\n📊 CSV Processing Benchmarks")
        print("-" * 30)
        
        # Test different data sizes
        test_sizes = [1000, 5000, 10000, 25000, 50000]
        
        for size in test_sizes:
            print(f"Testing CSV processing with {size:,} rows...")
            
            # Generate test data
            csv_data = self._generate_csv_data(size)
            
            # Test standard processing
            await self._benchmark_csv_standard(csv_data, size)
            
            # Test streaming processing
            await self._benchmark_csv_streaming(csv_data, size)
    
    async def _benchmark_csv_standard(self, csv_data: bytes, size: int):
        """Benchmark standard CSV processing."""
        from ..services.dynamic_csv_extractor import DynamicCSVStatisticsExtractor
        from fastapi import UploadFile
        
        extractor = DynamicCSVStatisticsExtractor()
        
        # Create upload file
        upload_file = UploadFile(
            filename=f"test_{size}.csv",
            file=io.BytesIO(csv_data),
            content_type="text/csv"
        )
        
        # Monitor memory
        initial_memory = self.process.memory_info().rss / 1024 / 1024
        peak_memory = initial_memory
        
        start_time = time.time()
        success = True
        error_msg = ""
        
        try:
            # Force standard processing
            with self._patch_file_size(5):  # Small file size
                statistics = await extractor.extract_statistics(
                    upload_file, "benchmark_project"
                )
            
            # Monitor peak memory
            current_memory = self.process.memory_info().rss / 1024 / 1024
            peak_memory = max(peak_memory, current_memory)
            
        except Exception as e:
            success = False
            error_msg = str(e)
            statistics = None
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Calculate throughput
        throughput = size / processing_time if processing_time > 0 else 0
        
        result = BenchmarkResult(
            test_name=f"CSV_Standard_{size}",
            data_size=size,
            processing_time=processing_time,
            memory_usage_mb=peak_memory - initial_memory,
            peak_memory_mb=peak_memory,
            throughput=throughput,
            success=success,
            error_message=error_msg,
            metadata={
                "processing_method": "standard",
                "has_statistics": statistics is not None,
                "categorical_fields": len(statistics.get("categorical_distributions", {})) if statistics else 0
            }
        )
        
        self.results.append(result)
        print(f"  Standard: {processing_time:.2f}s, {throughput:.0f} rows/s, {peak_memory - initial_memory:.1f}MB")
    
    async def _benchmark_csv_streaming(self, csv_data: bytes, size: int):
        """Benchmark streaming CSV processing."""
        from fastapi import UploadFile
        
        processor = StreamingCSVProcessor(chunk_size=1000)
        
        # Create upload file
        upload_file = UploadFile(
            filename=f"test_{size}.csv",
            file=io.BytesIO(csv_data),
            content_type="text/csv"
        )
        
        # Monitor memory
        initial_memory = self.process.memory_info().rss / 1024 / 1024
        peak_memory = initial_memory
        
        start_time = time.time()
        success = True
        error_msg = ""
        chunks_processed = 0
        
        try:
            async for chunk_result in processor.process_large_csv_streaming(
                upload_file, "benchmark_project"
            ):
                chunks_processed += 1
                current_memory = self.process.memory_info().rss / 1024 / 1024
                peak_memory = max(peak_memory, current_memory)
                
        except Exception as e:
            success = False
            error_msg = str(e)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Calculate throughput
        throughput = size / processing_time if processing_time > 0 else 0
        
        result = BenchmarkResult(
            test_name=f"CSV_Streaming_{size}",
            data_size=size,
            processing_time=processing_time,
            memory_usage_mb=peak_memory - initial_memory,
            peak_memory_mb=peak_memory,
            throughput=throughput,
            success=success,
            error_message=error_msg,
            metadata={
                "processing_method": "streaming",
                "chunks_processed": chunks_processed,
                "avg_chunk_size": size / chunks_processed if chunks_processed > 0 else 0
            }
        )
        
        self.results.append(result)
        print(f"  Streaming: {processing_time:.2f}s, {throughput:.0f} rows/s, {peak_memory - initial_memory:.1f}MB")
    
    async def _benchmark_pdf_processing(self):
        """Benchmark PDF processing with various page counts."""
        print("\n📄 PDF Processing Benchmarks")
        print("-" * 30)
        
        # Test different page counts
        page_counts = [10, 25, 50, 100, 200]
        
        for pages in page_counts:
            print(f"Testing PDF processing with {pages} pages...")
            
            # Test batch processing
            await self._benchmark_pdf_batch(pages)
    
    async def _benchmark_pdf_batch(self, page_count: int):
        """Benchmark batch PDF processing."""
        processor = BatchPDFProcessor(batch_size=10)
        
        # Mock PDF content
        mock_pages = [f"Page {i} content with interview data and user feedback" * 20 
                     for i in range(page_count)]
        
        # Monitor memory
        initial_memory = self.process.memory_info().rss / 1024 / 1024
        peak_memory = initial_memory
        
        start_time = time.time()
        success = True
        error_msg = ""
        batches_processed = 0
        
        try:
            # Mock the PDF processing
            from unittest.mock import MagicMock, patch
            
            mock_pdf_reader = MagicMock()
            mock_pdf_reader.pages = [MagicMock() for _ in range(page_count)]
            
            for i, page_mock in enumerate(mock_pdf_reader.pages):
                page_mock.extract_text.return_value = mock_pages[i]
            
            mock_upload_file = MagicMock()
            mock_upload_file.read.return_value = b"mock_pdf_content"
            mock_upload_file.seek.return_value = None
            
            with patch('pypdf.PdfReader', return_value=mock_pdf_reader):
                async for batch_result in processor.process_large_pdf_batched(
                    mock_upload_file, "benchmark_project"
                ):
                    batches_processed += 1
                    current_memory = self.process.memory_info().rss / 1024 / 1024
                    peak_memory = max(peak_memory, current_memory)
                    
        except Exception as e:
            success = False
            error_msg = str(e)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Calculate throughput (pages per second)
        throughput = page_count / processing_time if processing_time > 0 else 0
        
        result = BenchmarkResult(
            test_name=f"PDF_Batch_{page_count}",
            data_size=page_count,
            processing_time=processing_time,
            memory_usage_mb=peak_memory - initial_memory,
            peak_memory_mb=peak_memory,
            throughput=throughput,
            success=success,
            error_message=error_msg,
            metadata={
                "processing_method": "batch",
                "batches_processed": batches_processed,
                "avg_batch_size": page_count / batches_processed if batches_processed > 0 else 0
            }
        )
        
        self.results.append(result)
        print(f"  Batch: {processing_time:.2f}s, {throughput:.1f} pages/s, {peak_memory - initial_memory:.1f}MB")
    
    async def _benchmark_caching_system(self):
        """Benchmark caching system effectiveness."""
        print("\n💾 Caching System Benchmarks")
        print("-" * 30)
        
        cache = StatisticsRegistryCache(max_size_mb=50)
        
        # Test data of various sizes
        test_data_sizes = [1, 10, 100, 1000]  # KB
        
        for size_kb in test_data_sizes:
            print(f"Testing cache with {size_kb}KB data...")
            
            # Generate test data
            test_data = {"data": "x" * (size_kb * 1024)}
            
            # Test cache miss
            start_time = time.time()
            result = await cache.get(f"test_key_{size_kb}")
            miss_time = time.time() - start_time
            
            # Store data
            await cache.set(f"test_key_{size_kb}", test_data)
            
            # Test cache hit
            start_time = time.time()
            result = await cache.get(f"test_key_{size_kb}")
            hit_time = time.time() - start_time
            
            # Calculate speedup
            speedup = miss_time / hit_time if hit_time > 0 else float('inf')
            
            result = BenchmarkResult(
                test_name=f"Cache_{size_kb}KB",
                data_size=size_kb,
                processing_time=hit_time,
                memory_usage_mb=0,  # Cache manages its own memory
                peak_memory_mb=0,
                throughput=1 / hit_time if hit_time > 0 else float('inf'),
                success=True,
                metadata={
                    "miss_time": miss_time,
                    "hit_time": hit_time,
                    "speedup": speedup,
                    "cache_stats": cache.get_stats()
                }
            )
            
            self.results.append(result)
            print(f"  {size_kb}KB: {speedup:.1f}x speedup ({miss_time*1000:.2f}ms -> {hit_time*1000:.2f}ms)")
    
    async def _benchmark_token_optimization(self):
        """Benchmark token optimization effectiveness."""
        print("\n🎯 Token Optimization Benchmarks")
        print("-" * 30)
        
        optimizer = TokenBudgetOptimizer()
        
        # Test different content sizes and token budgets
        test_cases = [
            (50, 500),   # 50 items, 500 token budget
            (100, 1000), # 100 items, 1000 token budget
            (200, 1500), # 200 items, 1500 token budget
        ]
        
        for content_count, token_budget in test_cases:
            print(f"Testing optimization with {content_count} items, {token_budget} token budget...")
            
            # Generate test content
            available_content = []
            for i in range(content_count):
                content_text = f"Content item {i} discussing pain points and user feedback " * (i % 10 + 1)
                available_content.append({
                    "content": content_text,
                    "source_type": "csv" if i % 2 == 0 else "pdf",
                    "chunk_id": f"chunk_{i}"
                })
            
            start_time = time.time()
            
            try:
                result = await optimizer.optimize_content_selection(
                    available_content=available_content,
                    token_budget=token_budget,
                    analysis_type="pain",
                    source_balance_requirements={"csv": 0.3, "pdf": 0.4}
                )
                
                optimization_time = time.time() - start_time
                
                selected_count = len(result["selected_content"])
                token_utilization = result["optimization_metrics"]["token_utilization"]
                information_density = result["information_density"]
                
                benchmark_result = BenchmarkResult(
                    test_name=f"TokenOpt_{content_count}_{token_budget}",
                    data_size=content_count,
                    processing_time=optimization_time,
                    memory_usage_mb=0,
                    peak_memory_mb=0,
                    throughput=content_count / optimization_time,
                    success=True,
                    metadata={
                        "selected_count": selected_count,
                        "selection_ratio": selected_count / content_count,
                        "token_utilization": token_utilization,
                        "information_density": information_density,
                        "token_budget": token_budget
                    }
                )
                
                self.results.append(benchmark_result)
                print(f"  Selected {selected_count}/{content_count} items, "
                      f"utilization: {token_utilization:.3f}, "
                      f"density: {information_density:.3f}")
                
            except Exception as e:
                print(f"  Error: {e}")
    
    async def _benchmark_concurrent_processing(self):
        """Benchmark concurrent processing capabilities."""
        print("\n🔄 Concurrent Processing Benchmarks")
        print("-" * 30)
        
        # Test different concurrency levels
        concurrency_levels = [1, 2, 5, 10, 20]
        
        for max_concurrent in concurrency_levels:
            print(f"Testing with {max_concurrent} concurrent requests...")
            
            manager = ResourceManager(max_concurrent_requests=max_concurrent)
            
            async def mock_request(request_id: str):
                async with manager.acquire_resources(request_id):
                    await asyncio.sleep(0.1)  # Simulate processing
                    return f"completed_{request_id}"
            
            # Create many requests
            num_requests = 20
            tasks = [mock_request(f"req_{i}") for i in range(num_requests)]
            
            start_time = time.time()
            results = await asyncio.gather(*tasks)
            end_time = time.time()
            
            total_time = end_time - start_time
            throughput = num_requests / total_time
            
            metrics = manager.get_performance_metrics()
            
            result = BenchmarkResult(
                test_name=f"Concurrent_{max_concurrent}",
                data_size=num_requests,
                processing_time=total_time,
                memory_usage_mb=0,
                peak_memory_mb=0,
                throughput=throughput,
                success=len(results) == num_requests,
                metadata={
                    "max_concurrent": max_concurrent,
                    "success_rate": metrics["success_rate"],
                    "avg_wait_time": metrics.get("avg_wait_time", 0)
                }
            )
            
            self.results.append(result)
            print(f"  {num_requests} requests in {total_time:.2f}s ({throughput:.1f} req/s)")
    
    async def _benchmark_memory_usage(self):
        """Benchmark memory usage patterns."""
        print("\n🧠 Memory Usage Benchmarks")
        print("-" * 30)
        
        # Test memory usage with different data sizes
        data_sizes = [1, 5, 10, 25, 50]  # MB
        
        for size_mb in data_sizes:
            print(f"Testing memory usage with {size_mb}MB data...")
            
            initial_memory = self.process.memory_info().rss / 1024 / 1024
            
            # Create large data structure
            large_data = {"data": "x" * (size_mb * 1024 * 1024)}
            
            peak_memory = self.process.memory_info().rss / 1024 / 1024
            memory_increase = peak_memory - initial_memory
            
            # Clean up
            del large_data
            import gc
            gc.collect()
            
            final_memory = self.process.memory_info().rss / 1024 / 1024
            memory_recovered = peak_memory - final_memory
            
            result = BenchmarkResult(
                test_name=f"Memory_{size_mb}MB",
                data_size=size_mb,
                processing_time=0,
                memory_usage_mb=memory_increase,
                peak_memory_mb=peak_memory,
                throughput=0,
                success=True,
                metadata={
                    "initial_memory": initial_memory,
                    "peak_memory": peak_memory,
                    "final_memory": final_memory,
                    "memory_increase": memory_increase,
                    "memory_recovered": memory_recovered,
                    "recovery_rate": memory_recovered / memory_increase if memory_increase > 0 else 0
                }
            )
            
            self.results.append(result)
            print(f"  {size_mb}MB -> +{memory_increase:.1f}MB peak, -{memory_recovered:.1f}MB recovered")
    
    def _generate_csv_data(self, rows: int) -> bytes:
        """Generate CSV test data."""
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(['id', 'name', 'age', 'category', 'feedback', 'rating'])
        
        # Data rows
        for i in range(rows):
            writer.writerow([
                i,
                f"User_{i}",
                25 + (i % 40),
                f"Category_{i % 10}",
                f"Feedback {i} about pain points and user experience issues",
                (i % 5) + 1
            ])
        
        return output.getvalue().encode('utf-8')
    
    def _patch_file_size(self, size_mb: float):
        """Context manager to patch file size detection."""
        from unittest.mock import patch
        return patch('Backend.src.market_research.services.dynamic_csv_extractor.DynamicCSVStatisticsExtractor._get_file_size_mb', 
                    return_value=size_mb)
    
    def _generate_benchmark_report(self, total_time: float) -> Dict[str, Any]:
        """Generate comprehensive benchmark report."""
        successful_results = [r for r in self.results if r.success]
        failed_results = [r for r in self.results if not r.success]
        
        # Calculate summary statistics
        avg_processing_time = sum(r.processing_time for r in successful_results) / len(successful_results) if successful_results else 0
        avg_memory_usage = sum(r.memory_usage_mb for r in successful_results) / len(successful_results) if successful_results else 0
        avg_throughput = sum(r.throughput for r in successful_results) / len(successful_results) if successful_results else 0
        
        # Find best and worst performers
        best_throughput = max(successful_results, key=lambda r: r.throughput) if successful_results else None
        worst_memory = max(successful_results, key=lambda r: r.memory_usage_mb) if successful_results else None
        
        report = {
            "summary": {
                "total_tests": len(self.results),
                "successful_tests": len(successful_results),
                "failed_tests": len(failed_results),
                "success_rate": len(successful_results) / len(self.results) if self.results else 0,
                "total_benchmark_time": total_time,
                "avg_processing_time": avg_processing_time,
                "avg_memory_usage_mb": avg_memory_usage,
                "avg_throughput": avg_throughput
            },
            "performance_highlights": {
                "best_throughput": {
                    "test": best_throughput.test_name if best_throughput else None,
                    "value": best_throughput.throughput if best_throughput else 0
                },
                "highest_memory_usage": {
                    "test": worst_memory.test_name if worst_memory else None,
                    "value": worst_memory.memory_usage_mb if worst_memory else 0
                }
            },
            "test_categories": {
                "csv_processing": len([r for r in self.results if "CSV" in r.test_name]),
                "pdf_processing": len([r for r in self.results if "PDF" in r.test_name]),
                "caching": len([r for r in self.results if "Cache" in r.test_name]),
                "optimization": len([r for r in self.results if "TokenOpt" in r.test_name]),
                "concurrent": len([r for r in self.results if "Concurrent" in r.test_name]),
                "memory": len([r for r in self.results if "Memory" in r.test_name])
            },
            "failed_tests": [
                {"test": r.test_name, "error": r.error_message}
                for r in failed_results
            ]
        }
        
        return report
    
    async def _save_results(self):
        """Save benchmark results to files."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save detailed results as JSON
        results_data = [asdict(result) for result in self.results]
        
        json_file = self.output_dir / f"benchmark_results_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(results_data, f, indent=2, default=str)
        
        # Save summary as CSV
        csv_file = self.output_dir / f"benchmark_summary_{timestamp}.csv"
        
        df = pd.DataFrame([
            {
                "test_name": r.test_name,
                "data_size": r.data_size,
                "processing_time": r.processing_time,
                "memory_usage_mb": r.memory_usage_mb,
                "throughput": r.throughput,
                "success": r.success
            }
            for r in self.results
        ])
        
        df.to_csv(csv_file, index=False)
        
        # Generate performance charts
        await self._generate_charts(timestamp)
        
        print(f"\n📁 Results saved:")
        print(f"  📄 Detailed: {json_file}")
        print(f"  📊 Summary: {csv_file}")
    
    async def _generate_charts(self, timestamp: str):
        """Generate performance visualization charts."""
        try:
            # Throughput comparison chart
            csv_results = [r for r in self.results if "CSV" in r.test_name and r.success]
            if csv_results:
                sizes = [r.data_size for r in csv_results]
                throughputs = [r.throughput for r in csv_results]
                
                plt.figure(figsize=(10, 6))
                plt.plot(sizes, throughputs, 'bo-', label='CSV Processing')
                plt.xlabel('Data Size (rows)')
                plt.ylabel('Throughput (rows/sec)')
                plt.title('CSV Processing Throughput vs Data Size')
                plt.grid(True)
                plt.legend()
                
                chart_file = self.output_dir / f"throughput_chart_{timestamp}.png"
                plt.savefig(chart_file)
                plt.close()
            
            # Memory usage chart
            memory_results = [r for r in self.results if r.success and r.memory_usage_mb > 0]
            if memory_results:
                test_names = [r.test_name for r in memory_results]
                memory_usage = [r.memory_usage_mb for r in memory_results]
                
                plt.figure(figsize=(12, 6))
                plt.bar(range(len(test_names)), memory_usage)
                plt.xlabel('Test')
                plt.ylabel('Memory Usage (MB)')
                plt.title('Memory Usage by Test')
                plt.xticks(range(len(test_names)), test_names, rotation=45, ha='right')
                plt.tight_layout()
                
                memory_chart_file = self.output_dir / f"memory_chart_{timestamp}.png"
                plt.savefig(memory_chart_file)
                plt.close()
                
        except ImportError:
            print("📊 Matplotlib not available, skipping chart generation")
        except Exception as e:
            print(f"📊 Chart generation failed: {e}")


async def main():
    """Run performance benchmark suite."""
    benchmark = PerformanceBenchmark()
    
    try:
        report = await benchmark.run_all_benchmarks()
        
        print("\n" + "=" * 50)
        print("📈 BENCHMARK SUMMARY")
        print("=" * 50)
        
        summary = report["summary"]
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Success Rate: {summary['success_rate']:.1%}")
        print(f"Average Processing Time: {summary['avg_processing_time']:.3f}s")
        print(f"Average Memory Usage: {summary['avg_memory_usage_mb']:.1f}MB")
        print(f"Average Throughput: {summary['avg_throughput']:.1f} items/s")
        
        if report["failed_tests"]:
            print(f"\n❌ Failed Tests: {len(report['failed_tests'])}")
            for failed in report["failed_tests"]:
                print(f"  - {failed['test']}: {failed['error']}")
        
        highlights = report["performance_highlights"]
        if highlights["best_throughput"]["test"]:
            print(f"\n🏆 Best Throughput: {highlights['best_throughput']['test']} "
                  f"({highlights['best_throughput']['value']:.1f} items/s)")
        
        print("\n✅ Benchmark completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Benchmark failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())