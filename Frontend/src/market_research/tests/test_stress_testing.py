"""
Stress testing for Data Analysis Agent with large documents and concurrent users.

This module tests system behavior under stress conditions including:
- Large PDF files (100+ pages)
- Large CSV files (10,000+ rows)
- Concurrent analysis execution by multiple users
- Memory usage and performance validation
"""

import pytest
import asyncio
import time
import psutil
import os
import tempfile
import csv
from typing import List, Dict, Any
from unittest.mock import AsyncMock, patch
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from io import BytesIO

from fastapi import UploadFile


class StressTestMetrics:
    """Track performance metrics during stress testing."""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.peak_memory_mb = 0
        self.peak_cpu_percent = 0
        self.processing_times = []
        self.errors = []
        self.concurrent_operations = 0
        self.max_concurrent_operations = 0
    
    def start_monitoring(self):
        """Start performance monitoring."""
        self.start_time = time.time()
        self.peak_memory_mb = 0
        self.peak_cpu_percent = 0
    
    def update_metrics(self):
        """Update current performance metrics."""
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        cpu_percent = process.cpu_percent()
        
        self.peak_memory_mb = max(self.peak_memory_mb, memory_mb)
        self.peak_cpu_percent = max(self.peak_cpu_percent, cpu_percent)
    
    def record_operation_start(self):
        """Record start of concurrent operation."""
        self.concurrent_operations += 1
        self.max_concurrent_operations = max(
            self.max_concurrent_operations, 
            self.concurrent_operations
        )
    
    def record_operation_end(self, duration: float, error: str = None):
        """Record end of concurrent operation."""
        self.concurrent_operations -= 1
        self.processing_times.append(duration)
        if error:
            self.errors.append(error)
    
    def stop_monitoring(self):
        """Stop performance monitoring."""
        self.end_time = time.time()
    
    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        total_time = self.end_time - self.start_time if self.end_time else 0
        avg_processing_time = sum(self.processing_times) / len(self.processing_times) if self.processing_times else 0
        
        return {
            "total_duration_seconds": total_time,
            "peak_memory_mb": self.peak_memory_mb,
            "peak_cpu_percent": self.peak_cpu_percent,
            "max_concurrent_operations": self.max_concurrent_operations,
            "total_operations": len(self.processing_times),
            "average_processing_time": avg_processing_time,
            "error_count": len(self.errors),
            "error_rate": len(self.errors) / len(self.processing_times) if self.processing_times else 0,
            "errors": self.errors[:10]  # First 10 errors for analysis
        }


def create_large_pdf_content(pages: int = 100) -> str:
    """Create large PDF-like text content for testing."""
    content = []
    
    for page in range(1, pages + 1):
        page_content = f"""
        PAGE {page}
        
        Interview Transcript - Market Research Study
        
        Interviewer: Thank you for participating in our market research study. Can you tell me about the main challenges you face in your daily work?
        
        Participant: Well, the biggest issue I encounter is the lack of efficient tools for data analysis. We spend hours manually processing information that could be automated. This creates significant bottlenecks in our workflow and affects our productivity.
        
        The pain points are particularly acute when dealing with large datasets. We often encounter errors due to manual processing, which leads to rework and delays. Our team of 12 people is constantly struggling with these inefficiencies.
        
        END OF PAGE {page}
        """
        content.append(page_content)
    
    return "\n".join(content)


def create_large_csv_data(rows: int = 10000) -> List[Dict[str, Any]]:
    """Create large CSV data for testing."""
    csv_data = []
    
    for i in range(1, rows + 1):
        row = {
            "respondent_id": f"RESP_{i:06d}",
            "age": 25 + (i % 40),
            "gender": "Male" if i % 2 == 0 else "Female",
            "occupation": ["Manager", "Analyst", "Director", "Specialist"][i % 4],
            "industry": ["Technology", "Finance", "Healthcare", "Manufacturing"][i % 4],
            "pain_point_1": "Time-consuming manual processes",
            "pain_point_2": "Lack of automation capabilities",
            "current_solution": ["Excel", "Custom Software", "Manual Process"][i % 3],
            "satisfaction_level": (i % 5) + 1,
            "comments": f"Additional feedback from respondent {i}."
        }
        csv_data.append(row)
    
    return csv_data


def create_upload_file_from_text(content: str, filename: str) -> UploadFile:
    """Create UploadFile object from text content."""
    file_obj = BytesIO(content.encode('utf-8'))
    return UploadFile(filename=filename, file=file_obj)


def create_upload_file_from_csv(data: List[Dict], filename: str) -> UploadFile:
    """Create UploadFile object from CSV data."""
    import io
    output = io.StringIO()
    if data:
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
    
    # Convert to bytes
    csv_content = output.getvalue()
    bytes_output = BytesIO(csv_content.encode('utf-8'))
    return UploadFile(filename=filename, file=bytes_output)


@pytest.fixture
def stress_metrics():
    """Fixture for stress test metrics."""
    return StressTestMetrics()


@pytest.fixture
def large_pdf_file():
    """Fixture for large PDF file (100+ pages)."""
    content = create_large_pdf_content(pages=150)
    return create_upload_file_from_text(content, "large_interview_transcript.pdf")


@pytest.fixture
def large_csv_file():
    """Fixture for large CSV file (10,000+ rows)."""
    data = create_large_csv_data(rows=12000)
    return create_upload_file_from_csv(data, "large_survey_data.csv")


class MockDocumentParser:
    """Mock document parser for testing."""
    
    async def parse_pdf(self, file: UploadFile) -> Dict[str, Any]:
        """Mock PDF parsing with realistic delay."""
        await asyncio.sleep(0.1)  # Simulate processing time
        content = await file.read()
        return {
            "content": content.decode('utf-8'),
            "metadata": {"pages": 150, "size": len(content)},
            "chunks": []
        }
    
    async def parse_csv(self, file: UploadFile) -> Dict[str, Any]:
        """Mock CSV parsing with realistic delay."""
        await asyncio.sleep(0.05)  # Simulate processing time
        content = await file.read()
        return {
            "content": content.decode('utf-8'),
            "metadata": {"rows": 12000, "size": len(content)},
            "chunks": []
        }


class MockAnalysisService:
    """Mock analysis service for testing."""
    
    async def analyze_market_research(self, *args, **kwargs):
        """Mock analysis with realistic delay."""
        await asyncio.sleep(0.1)  # Simulate processing time
        return {
            "session_id": f"test-session-{time.time()}",
            "status": "completed",
            "results": {"analysis": "mock results"}
        }


class TestStressTestingLargeDocuments:
    """Test system behavior with large documents."""
    
    @pytest.mark.asyncio
    async def test_large_pdf_processing(self, large_pdf_file, stress_metrics):
        """Test processing of large PDF files (100+ pages)."""
        stress_metrics.start_monitoring()
        
        try:
            parser = MockDocumentParser()
            
            start_time = time.time()
            result = await parser.parse_pdf(large_pdf_file)
            processing_time = time.time() - start_time
            
            stress_metrics.update_metrics()
            stress_metrics.record_operation_end(processing_time)
            
            # Validate results
            assert result is not None
            assert "content" in result
            assert len(result["content"]) > 100000  # Should be substantial content
            
            # Performance assertions
            assert processing_time < 30.0  # Should complete within 30 seconds
            assert stress_metrics.peak_memory_mb < 1000  # Should not exceed 1GB memory
            
        finally:
            stress_metrics.stop_monitoring()
        
        summary = stress_metrics.get_summary()
        print(f"Large PDF Processing Metrics: {summary}")
    
    @pytest.mark.asyncio
    async def test_large_csv_processing(self, large_csv_file, stress_metrics):
        """Test processing of large CSV files (10,000+ rows)."""
        stress_metrics.start_monitoring()
        
        try:
            parser = MockDocumentParser()
            
            start_time = time.time()
            result = await parser.parse_csv(large_csv_file)
            processing_time = time.time() - start_time
            
            stress_metrics.update_metrics()
            stress_metrics.record_operation_end(processing_time)
            
            # Validate results
            assert result is not None
            assert "content" in result
            assert len(result["content"]) > 50000  # Should be substantial content
            
            # Performance assertions
            assert processing_time < 20.0  # Should complete within 20 seconds
            assert stress_metrics.peak_memory_mb < 500  # Should not exceed 500MB memory
            
        finally:
            stress_metrics.stop_monitoring()
        
        summary = stress_metrics.get_summary()
        print(f"Large CSV Processing Metrics: {summary}")


class TestConcurrentUserStressTesting:
    """Test concurrent analysis execution by multiple users."""
    
    @pytest.mark.asyncio
    async def test_concurrent_analysis_execution(self, stress_metrics):
        """Test concurrent analysis execution by multiple users."""
        stress_metrics.start_monitoring()
        
        num_concurrent_users = 10
        analyses_per_user = 3
        
        async def simulate_user_analysis(user_id: int):
            """Simulate analysis execution by a single user."""
            user_results = []
            service = MockAnalysisService()
            
            for analysis_id in range(analyses_per_user):
                try:
                    stress_metrics.record_operation_start()
                    stress_metrics.update_metrics()
                    
                    start_time = time.time()
                    
                    result = await service.analyze_market_research(
                        project_id=f"project-{user_id}",
                        tenant_id=f"tenant-{user_id}",
                        user_id=f"user-{user_id}"
                    )
                    
                    processing_time = time.time() - start_time
                    stress_metrics.record_operation_end(processing_time)
                    
                    user_results.append({
                        "user_id": user_id,
                        "analysis_id": analysis_id,
                        "result": result,
                        "processing_time": processing_time
                    })
                    
                except Exception as e:
                    stress_metrics.record_operation_end(0, str(e))
                    user_results.append({
                        "user_id": user_id,
                        "analysis_id": analysis_id,
                        "error": str(e)
                    })
            
            return user_results
        
        try:
            # Execute concurrent user simulations
            tasks = [
                simulate_user_analysis(user_id) 
                for user_id in range(num_concurrent_users)
            ]
            
            all_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Validate results
            successful_results = [r for r in all_results if not isinstance(r, Exception)]
            assert len(successful_results) == num_concurrent_users
            
            # Check that all users completed their analyses
            total_analyses = sum(len(user_results) for user_results in successful_results)
            expected_analyses = num_concurrent_users * analyses_per_user
            assert total_analyses == expected_analyses
            
        finally:
            stress_metrics.stop_monitoring()
        
        summary = stress_metrics.get_summary()
        print(f"Concurrent User Analysis Metrics: {summary}")
        
        # Performance assertions
        assert summary["error_rate"] < 0.1  # Less than 10% error rate
        assert summary["max_concurrent_operations"] >= num_concurrent_users


class TestPerformanceUnderLoad:
    """Test system performance under various load conditions."""
    
    @pytest.mark.asyncio
    async def test_throughput_performance(self, stress_metrics):
        """Test system throughput under sustained load."""
        stress_metrics.start_monitoring()
        
        duration_seconds = 10  # Run for 10 seconds (reduced for testing)
        target_rps = 5  # Target 5 requests per second
        
        start_time = time.time()
        completed_requests = 0
        service = MockAnalysisService()
        
        try:
            while time.time() - start_time < duration_seconds:
                batch_start = time.time()
                
                # Execute batch of requests
                batch_tasks = []
                for i in range(target_rps):
                    task = service.analyze_market_research(
                        project_id=f"perf-project-{completed_requests + i}",
                        tenant_id="perf-tenant",
                        user_id="perf-user"
                    )
                    batch_tasks.append(task)
                
                stress_metrics.record_operation_start()
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                batch_duration = time.time() - batch_start
                stress_metrics.record_operation_end(batch_duration)
                
                completed_requests += len([r for r in batch_results if not isinstance(r, Exception)])
                stress_metrics.update_metrics()
                
                # Wait for next second if needed
                elapsed = time.time() - batch_start
                if elapsed < 1.0:
                    await asyncio.sleep(1.0 - elapsed)
        
        finally:
            stress_metrics.stop_monitoring()
        
        summary = stress_metrics.get_summary()
        actual_rps = completed_requests / duration_seconds
        
        print(f"Throughput Performance Metrics: {summary}")
        print(f"Actual RPS: {actual_rps}, Target RPS: {target_rps}")
        
        # Performance assertions
        assert actual_rps >= target_rps * 0.8  # Should achieve at least 80% of target RPS
        assert summary["error_rate"] < 0.05  # Less than 5% error rate


if __name__ == "__main__":
    # Run stress tests with detailed output
    pytest.main([
        __file__,
        "-v",
        "-s",
        "--tb=short"
    ])