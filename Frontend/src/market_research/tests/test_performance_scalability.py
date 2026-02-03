"""
Performance and Scalability Tests for Market Research Analysis

Tests large dataset processing, concurrent request handling, caching effectiveness,
and optimization strategies to verify scalability limits and performance improvements.
"""

import pytest
import asyncio
import time
import psutil
import tempfile
import csv
import io
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import UploadFile
import pandas as pd

from ..services.performance_optimizer import (
    StreamingCSVProcessor, BatchPDFProcessor, 
    EfficientEmbeddingGenerator, IntelligentChunkingStrategy
)
from ..services.caching_optimization_system import (
    StatisticsRegistryCache, TokenBudgetOptimizer, ResourceManager
)
from ..services.dynamic_csv_extractor import DynamicCSVStatisticsExtractor
from ..services.structured_pdf_extractor import StructuredPDFExtractor
from ..services.statistics_registry_service import StatisticsRegistryService
from ..services.evidence_retrieval_engine import EvidenceRetrievalEngine


class TestLargeDatasetProcessing:
    """Test processing of large CSV files with memory monitoring."""
    
    @pytest.fixture
    def large_csv_data(self):
        """Generate large CSV data for testing."""
        def create_csv(rows: int) -> bytes:
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            headers = [
                'respondent_id', 'age', 'gender', 'occupation', 'income_range',
                'satisfaction_level', 'usage_frequency', 'pain_points', 'preferred_features',
                'likelihood_to_recommend', 'comments'
            ]
            writer.writerow(headers)
            
            # Write data rows
            for i in range(rows):
                row = [
                    f"resp_{i:06d}",
                    25 + (i % 40),  # Age 25-65
                    'Male' if i % 2 == 0 else 'Female',
                    f"Job_{i % 20}",
                    f"Range_{i % 5}",
                    f"Level_{i % 5}",
                    f"Frequency_{i % 4}",
                    f"Pain point {i % 10} is very frustrating and causes delays",
                    f"Feature {i % 8} would be very helpful for daily tasks",
                    i % 10 + 1,  # 1-10 scale
                    f"This is a detailed comment from respondent {i} about their experience with the product. " * 3
                ]
                writer.writerow(row)
            
            return output.getvalue().encode('utf-8')
        
        return create_csv
    
    @pytest.fixture
    def mock_upload_file(self):
        """Create mock UploadFile for testing."""
        def create_file(content: bytes, filename: str = "test.csv"):
            file_obj = io.BytesIO(content)
            upload_file = UploadFile(
                filename=filename,
                file=file_obj,
                content_type="text/csv"
            )
            return upload_file
        return create_file
    
    @pytest.mark.asyncio
    async def test_streaming_csv_processing_10k_rows(self, large_csv_data, mock_upload_file):
        """Test streaming processing with 10k+ rows and memory monitoring."""
        # Create large CSV (10k rows)
        csv_content = large_csv_data(10000)
        upload_file = mock_upload_file(csv_content, "large_test.csv")
        
        processor = StreamingCSVProcessor(chunk_size=500)
        
        # Monitor memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        peak_memory = initial_memory
        
        chunks_processed = 0
        total_rows = 0
        
        start_time = time.time()
        
        # Process streaming chunks
        async for chunk_result in processor.process_large_csv_streaming(
            upload_file, "test_project", "test_persona"
        ):
            chunks_processed += 1
            chunk_stats = chunk_result["chunk_statistics"]
            total_rows += chunk_stats.get("row_count", 0)
            
            # Monitor memory
            current_memory = process.memory_info().rss / 1024 / 1024
            peak_memory = max(peak_memory, current_memory)
            
            # Verify chunk processing
            assert chunk_stats["row_count"] > 0
            assert "field_types" in chunk_stats
            assert "categorical_distributions" in chunk_stats
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Verify results
        assert chunks_processed > 0
        assert total_rows == 10000
        assert processing_time < 60  # Should complete within 60 seconds
        
        # Memory usage should be reasonable (not grow linearly with data size)
        memory_increase = peak_memory - initial_memory
        assert memory_increase < 200  # Should not use more than 200MB additional memory
        
        # Processing rate should be reasonable
        processing_rate = total_rows / processing_time
        assert processing_rate > 100  # At least 100 rows per second
        
        print(f"Processed {total_rows} rows in {processing_time:.2f}s ({processing_rate:.1f} rows/s)")
        print(f"Memory usage: {initial_memory:.1f}MB -> {peak_memory:.1f}MB (+{memory_increase:.1f}MB)")
    
    @pytest.mark.asyncio
    async def test_adaptive_chunk_sizing(self, large_csv_data, mock_upload_file):
        """Test adaptive chunk sizing based on memory usage."""
        csv_content = large_csv_data(5000)
        upload_file = mock_upload_file(csv_content)
        
        processor = StreamingCSVProcessor(chunk_size=1000)
        initial_chunk_size = processor.chunk_size
        
        chunk_sizes = []
        
        async for chunk_result in processor.process_large_csv_streaming(
            upload_file, "test_project"
        ):
            metrics = chunk_result["processing_metrics"]
            chunk_sizes.append(metrics["adaptive_chunk_size"])
        
        # Verify adaptive sizing occurred
        assert len(set(chunk_sizes)) > 1  # Chunk size should have changed
        assert min(chunk_sizes) >= processor.MIN_CHUNK_SIZE
        assert max(chunk_sizes) <= processor.MAX_CHUNK_SIZE
    
    @pytest.mark.asyncio
    async def test_memory_threshold_handling(self, large_csv_data, mock_upload_file):
        """Test memory threshold handling and garbage collection."""
        csv_content = large_csv_data(3000)
        upload_file = mock_upload_file(csv_content)
        
        # Set low memory threshold for testing
        processor = StreamingCSVProcessor()
        processor.MEMORY_THRESHOLD_MB = 50  # Very low threshold
        
        memory_warnings = []
        
        # Mock memory monitoring to simulate high usage
        with patch.object(processor, '_get_memory_usage_mb') as mock_memory:
            # Simulate memory spike then reduction
            memory_values = [30, 60, 40, 70, 35, 45]  # MB values
            mock_memory.side_effect = memory_values + [35] * 100  # Stable after
            
            chunks_processed = 0
            async for chunk_result in processor.process_large_csv_streaming(
                upload_file, "test_project"
            ):
                chunks_processed += 1
                if chunks_processed >= 3:  # Process a few chunks
                    break
            
            # Verify memory monitoring was called
            assert mock_memory.call_count > 0
    
    @pytest.mark.asyncio
    async def test_csv_extractor_performance_with_large_file(self, large_csv_data, mock_upload_file):
        """Test CSV extractor performance with large files."""
        csv_content = large_csv_data(8000)
        upload_file = mock_upload_file(csv_content)
        
        extractor = DynamicCSVStatisticsExtractor()
        
        start_time = time.time()
        
        # Mock the file size check to trigger streaming
        with patch.object(extractor, '_get_file_size_mb', return_value=60):  # 60MB
            statistics = await extractor.extract_statistics(
                upload_file, "test_project", "test_persona"
            )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Verify results
        assert statistics is not None
        assert statistics["metadata"]["processing_method"] == "streaming"
        assert statistics["metadata"]["total_rows"] == 8000
        assert len(statistics["categorical_distributions"]) > 0
        
        # Performance requirements
        assert processing_time < 120  # Should complete within 2 minutes
        
        print(f"Large CSV extraction completed in {processing_time:.2f}s")


class TestBatchPDFProcessing:
    """Test batch processing of large PDF files."""
    
    @pytest.fixture
    def mock_pdf_content(self):
        """Generate mock PDF content for testing."""
        def create_pdf_pages(num_pages: int) -> List[str]:
            pages = []
            for i in range(num_pages):
                page_content = f"""
                Page {i + 1} Interview Content
                
                Participant: Respondent_{i:03d}
                
                Q: What are your main challenges with the current system?
                A: I find it very frustrating when the system is slow. The main problems include:
                - Loading times are too long (mentioned {i % 5 + 1} times)
                - Interface is confusing and not intuitive
                - Lack of proper documentation and help features
                - Integration issues with other tools we use daily
                
                Q: What features would you like to see improved?
                A: I would really appreciate better performance and more user-friendly design.
                The system should be faster and more reliable. Key improvements needed:
                - Better search functionality
                - More customization options
                - Improved mobile experience
                - Better reporting capabilities
                
                Q: How often do you use the system?
                A: I use it daily for about {i % 8 + 1} hours. It's essential for my work.
                
                Additional comments: This system has potential but needs significant improvements.
                The current version causes delays in our workflow and affects productivity.
                """
                pages.append(page_content)
            return pages
        return create_pdf_pages
    
    @pytest.mark.asyncio
    async def test_batch_pdf_processing_large_file(self, mock_pdf_content):
        """Test batch processing with large PDF files."""
        # Create mock PDF with many pages
        pdf_pages = mock_pdf_content(50)  # 50 pages
        
        processor = BatchPDFProcessor(batch_size=5)
        
        # Mock PDF reader and upload file
        mock_pdf_reader = MagicMock()
        mock_pdf_reader.pages = [MagicMock() for _ in range(50)]
        
        # Set up page text extraction
        for i, page_mock in enumerate(mock_pdf_reader.pages):
            page_mock.extract_text.return_value = pdf_pages[i]
        
        mock_upload_file = MagicMock()
        mock_upload_file.read.return_value = b"mock_pdf_content"
        mock_upload_file.seek.return_value = None
        
        # Monitor processing
        batches_processed = 0
        pages_processed = 0
        start_time = time.time()
        
        with patch('pypdf.PdfReader', return_value=mock_pdf_reader):
            async for batch_result in processor.process_large_pdf_batched(
                mock_upload_file, "test_project", "test_persona"
            ):
                batches_processed += 1
                batch_pages = batch_result["batch_results"]
                pages_processed += len(batch_pages)
                
                # Verify batch processing
                assert len(batch_pages) <= processor.batch_size
                for page_result in batch_pages:
                    assert "page_number" in page_result
                    assert "content" in page_result
                    assert "word_count" in page_result
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Verify results
        assert batches_processed == 10  # 50 pages / 5 per batch
        assert pages_processed == 50
        assert processing_time < 30  # Should complete within 30 seconds
        
        print(f"Processed {pages_processed} pages in {batches_processed} batches ({processing_time:.2f}s)")
    
    @pytest.mark.asyncio
    async def test_adaptive_batch_sizing(self, mock_pdf_content):
        """Test adaptive batch sizing based on memory usage."""
        pdf_pages = mock_pdf_content(20)
        
        processor = BatchPDFProcessor(batch_size=8)
        
        # Mock PDF reader
        mock_pdf_reader = MagicMock()
        mock_pdf_reader.pages = [MagicMock() for _ in range(20)]
        
        for i, page_mock in enumerate(mock_pdf_reader.pages):
            page_mock.extract_text.return_value = pdf_pages[i]
        
        mock_upload_file = MagicMock()
        mock_upload_file.read.return_value = b"mock_pdf_content"
        mock_upload_file.seek.return_value = None
        
        batch_sizes = []
        
        # Mock memory monitoring to trigger adaptive sizing
        with patch.object(processor, '_get_memory_usage_mb') as mock_memory:
            # Simulate memory spike then reduction
            memory_values = [100, 350, 200, 400, 150]  # MB values
            mock_memory.side_effect = memory_values + [150] * 100
            
            with patch('pypdf.PdfReader', return_value=mock_pdf_reader):
                async for batch_result in processor.process_large_pdf_batched(
                    mock_upload_file, "test_project"
                ):
                    metrics = batch_result["processing_metrics"]
                    batch_sizes.append(metrics["adaptive_batch_size"])
        
        # Verify adaptive sizing occurred
        assert len(set(batch_sizes)) > 1  # Batch size should have changed
        assert min(batch_sizes) >= 1  # Minimum batch size
        assert max(batch_sizes) <= 10  # Maximum reasonable batch size


class TestConcurrentRequestHandling:
    """Test concurrent analysis request handling and resource management."""
    
    @pytest.mark.asyncio
    async def test_resource_manager_concurrent_requests(self):
        """Test resource manager with multiple concurrent requests."""
        manager = ResourceManager(max_concurrent_requests=3)
        
        request_results = []
        request_times = []
        
        async def mock_request(request_id: str, duration: float):
            start_time = time.time()
            async with manager.acquire_resources(request_id):
                await asyncio.sleep(duration)  # Simulate processing
                end_time = time.time()
                request_results.append({
                    'request_id': request_id,
                    'duration': end_time - start_time,
                    'processing_time': duration
                })
                request_times.append(end_time - start_time)
        
        # Create 6 concurrent requests
        tasks = []
        for i in range(6):
            task = asyncio.create_task(mock_request(f"req_{i}", 0.5))
            tasks.append(task)
        
        start_time = time.time()
        await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        # Verify results
        assert len(request_results) == 6
        
        # With max 3 concurrent, should take about 1 second (2 batches of 0.5s each)
        assert 0.8 < total_time < 1.5
        
        # Check performance metrics
        metrics = manager.get_performance_metrics()
        assert metrics["total_requests"] == 6
        assert metrics["completed_requests"] == 6
        assert metrics["failed_requests"] == 0
        assert metrics["success_rate"] == 1.0
        
        print(f"Processed 6 requests in {total_time:.2f}s with max 3 concurrent")
    
    @pytest.mark.asyncio
    async def test_resource_manager_memory_threshold(self):
        """Test resource manager memory threshold handling."""
        manager = ResourceManager(
            max_concurrent_requests=5,
            memory_threshold_mb=100  # Low threshold for testing
        )
        
        # Mock high memory usage
        with patch.object(manager, '_get_current_resource_usage') as mock_usage:
            mock_usage.return_value = MagicMock(
                memory_mb=150,  # Above threshold
                cpu_percent=50,
                active_requests=1,
                cache_size_mb=10,
                timestamp=time.time()
            )
            
            # Should raise error due to high memory
            with pytest.raises(Exception):  # PerformanceError
                async with manager.acquire_resources("test_req"):
                    pass
    
    @pytest.mark.asyncio
    async def test_resource_manager_performance_recommendations(self):
        """Test resource manager performance recommendations."""
        manager = ResourceManager(
            memory_threshold_mb=200,
            cpu_threshold_percent=70
        )
        
        # Mock resource usage near thresholds
        with patch.object(manager, '_get_current_resource_usage') as mock_usage:
            mock_usage.return_value = MagicMock(
                memory_mb=170,  # 85% of threshold
                cpu_percent=60,  # 85% of threshold
                active_requests=2,
                cache_size_mb=15,
                timestamp=time.time()
            )
            
            # Set high wait times
            manager._performance_metrics["queue_wait_times"] = [6.0, 7.0, 8.0]
            
            recommendations = await manager.get_resource_recommendations()
            
            # Should have recommendations
            assert len(recommendations["recommendations"]) > 0
            
            # Check for specific recommendation types
            rec_types = [rec["type"] for rec in recommendations["recommendations"]]
            assert "memory" in rec_types or "queue" in rec_types


class TestCachingEffectiveness:
    """Test caching system effectiveness and performance improvements."""
    
    @pytest.mark.asyncio
    async def test_statistics_cache_performance(self):
        """Test statistics cache hit/miss performance."""
        cache = StatisticsRegistryCache(max_size_mb=10)
        
        # Test data
        test_data = {
            "categorical_distributions": {
                "field1": {"distribution": [{"value": "A", "count": 100}]},
                "field2": {"distribution": [{"value": "B", "count": 200}]}
            },
            "metadata": {"total_rows": 1000}
        }
        
        # Test cache miss (first access)
        start_time = time.time()
        result = await cache.get("test_key")
        miss_time = time.time() - start_time
        assert result is None
        
        # Store data
        await cache.set("test_key", test_data)
        
        # Test cache hit
        start_time = time.time()
        result = await cache.get("test_key")
        hit_time = time.time() - start_time
        assert result == test_data
        
        # Cache hit should be much faster than miss
        assert hit_time < miss_time * 0.1  # At least 10x faster
        
        # Check cache stats
        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.5
    
    @pytest.mark.asyncio
    async def test_cache_memory_management(self):
        """Test cache memory management and eviction."""
        cache = StatisticsRegistryCache(max_size_mb=1)  # Very small cache
        
        # Fill cache with large data
        large_data = {"data": "x" * 100000}  # ~100KB
        
        # Add multiple entries to trigger eviction
        for i in range(15):  # Should exceed 1MB limit
            await cache.set(f"key_{i}", large_data)
        
        # Check that cache size is managed
        stats = cache.get_stats()
        assert stats["size_mb"] <= 1.1  # Allow small overhead
        assert stats["evictions"] > 0
        
        # Verify LRU eviction - recent keys should still be present
        recent_result = await cache.get("key_14")
        assert recent_result is not None
        
        old_result = await cache.get("key_0")
        assert old_result is None  # Should have been evicted
    
    @pytest.mark.asyncio
    async def test_cache_ttl_expiration(self):
        """Test cache TTL expiration."""
        cache = StatisticsRegistryCache()
        
        test_data = {"test": "data"}
        
        # Set with short TTL
        await cache.set("ttl_key", test_data, ttl_seconds=1)
        
        # Should be available immediately
        result = await cache.get("ttl_key")
        assert result == test_data
        
        # Wait for expiration
        await asyncio.sleep(1.1)
        
        # Should be expired
        result = await cache.get("ttl_key")
        assert result is None


class TestTokenOptimization:
    """Test token budget optimization effectiveness."""
    
    @pytest.mark.asyncio
    async def test_token_optimizer_content_selection(self):
        """Test token optimizer content selection and prioritization."""
        optimizer = TokenBudgetOptimizer()
        
        # Create test content with varying relevance
        available_content = [
            {
                "content": "This discusses pain points and problems users face daily",
                "source_type": "csv",
                "chunk_id": "chunk_1"
            },
            {
                "content": "Statistical data shows 75% of users experience issues",
                "source_type": "csv", 
                "chunk_id": "chunk_2"
            },
            {
                "content": "User mentioned feeling frustrated with current solution",
                "source_type": "pdf",
                "chunk_id": "chunk_3"
            },
            {
                "content": "General information about product features and capabilities",
                "source_type": "pdf",
                "chunk_id": "chunk_4"
            },
            {
                "content": "Pain point analysis reveals significant user dissatisfaction",
                "source_type": "pdf",
                "chunk_id": "chunk_5"
            }
        ]
        
        # Test optimization for pain analysis
        result = await optimizer.optimize_content_selection(
            available_content=available_content,
            token_budget=200,  # Limited budget
            analysis_type="pain",
            persona_context={"description": "frustrated user seeking solutions"},
            source_balance_requirements={"csv": 0.3, "pdf": 0.4}
        )
        
        selected_content = result["selected_content"]
        metrics = result["optimization_metrics"]
        
        # Verify selection
        assert len(selected_content) > 0
        assert len(selected_content) < len(available_content)  # Should be selective
        
        # Verify token budget respected
        assert result["token_usage"] <= 200
        
        # Verify information density
        assert result["information_density"] > 0
        
        # Verify source balancing
        source_dist = metrics["source_distribution"]
        assert "csv" in source_dist
        assert "pdf" in source_dist
        
        # Pain-related content should be prioritized
        pain_content = [item for item in selected_content if "pain" in item["content"].lower()]
        assert len(pain_content) > 0
        
        print(f"Selected {len(selected_content)}/{len(available_content)} items")
        print(f"Token utilization: {metrics['token_utilization']:.3f}")
        print(f"Information density: {result['information_density']:.3f}")
    
    @pytest.mark.asyncio
    async def test_token_optimizer_source_balancing(self):
        """Test source balancing requirements enforcement."""
        optimizer = TokenBudgetOptimizer()
        
        # Create content heavily skewed toward one source
        available_content = []
        
        # Add many CSV items
        for i in range(10):
            available_content.append({
                "content": f"CSV data point {i} with statistical information",
                "source_type": "csv",
                "chunk_id": f"csv_{i}"
            })
        
        # Add few PDF items
        for i in range(2):
            available_content.append({
                "content": f"PDF interview quote {i} with user feedback",
                "source_type": "pdf", 
                "chunk_id": f"pdf_{i}"
            })
        
        # Require balanced representation
        result = await optimizer.optimize_content_selection(
            available_content=available_content,
            token_budget=500,
            analysis_type="size",
            source_balance_requirements={"csv": 0.4, "pdf": 0.4}  # 40% each minimum
        )
        
        selected_content = result["selected_content"]
        source_dist = result["optimization_metrics"]["source_distribution"]
        
        # Verify both sources are represented despite imbalance
        assert source_dist["csv"] > 0
        assert source_dist["pdf"] > 0
        
        # PDF should be over-represented relative to availability to meet requirements
        pdf_ratio = source_dist["pdf"] / len(selected_content)
        assert pdf_ratio >= 0.3  # Should meet minimum requirement


class TestScalabilityLimits:
    """Test system scalability limits and optimization strategies."""
    
    @pytest.mark.asyncio
    async def test_embedding_generation_batching(self):
        """Test efficient embedding generation with batching."""
        generator = EfficientEmbeddingGenerator(batch_size=5)
        
        # Mock embedding service
        mock_service = AsyncMock()
        mock_service.generate_embeddings.return_value = [[0.1, 0.2, 0.3]] * 5  # Mock embeddings
        
        # Test with many texts
        texts = [f"Test text {i} for embedding generation" for i in range(23)]
        
        start_time = time.time()
        embeddings = await generator.generate_embeddings_batched(
            texts=texts,
            embedding_service=mock_service
        )
        end_time = time.time()
        
        # Verify results
        assert len(embeddings) == 23
        assert len(embeddings[0]) == 3  # Mock embedding dimension
        
        # Verify batching occurred (should be 5 calls: 4 full batches + 1 partial)
        assert mock_service.generate_embeddings.call_count == 5
        
        # Performance should be reasonable
        processing_time = end_time - start_time
        assert processing_time < 10  # Should complete quickly with mocked service
        
        print(f"Generated {len(embeddings)} embeddings in {processing_time:.2f}s")
    
    @pytest.mark.asyncio
    async def test_embedding_rate_limit_handling(self):
        """Test embedding generation with rate limit handling."""
        generator = EfficientEmbeddingGenerator(batch_size=3)
        
        # Mock service that fails with rate limit then succeeds
        mock_service = AsyncMock()
        
        # First call fails with rate limit, second succeeds
        mock_service.generate_embeddings.side_effect = [
            Exception("Rate limit exceeded"),
            [[0.1, 0.2]] * 3  # Success on retry
        ]
        
        texts = ["text1", "text2", "text3"]
        
        start_time = time.time()
        embeddings = await generator.generate_embeddings_batched(
            texts=texts,
            embedding_service=mock_service
        )
        end_time = time.time()
        
        # Should eventually succeed
        assert len(embeddings) == 3
        
        # Should have retried (2 calls total)
        assert mock_service.generate_embeddings.call_count == 2
        
        # Should have taken time due to retry delay
        processing_time = end_time - start_time
        assert processing_time > 1.0  # Should include retry delay
    
    @pytest.mark.asyncio
    async def test_intelligent_chunking_optimization(self):
        """Test intelligent chunking strategy optimization."""
        strategy = IntelligentChunkingStrategy()
        
        # Test with different content types and sizes
        test_cases = [
            ("Small text content for testing", "text", None),
            ("Large " + "content " * 1000, "text", 5),  # Target 5 chunks
            ("CSV,data,content\n" * 500, "csv", None),
            ("PDF interview content with multiple paragraphs.\n\n" * 200, "pdf", None)
        ]
        
        for content, content_type, target_chunks in test_cases:
            chunks = await strategy.create_optimized_chunks(
                content=content,
                content_type=content_type,
                target_chunk_count=target_chunks
            )
            
            # Verify chunking results
            assert len(chunks) > 0
            
            if target_chunks:
                # Should be close to target (within reasonable range)
                assert abs(len(chunks) - target_chunks) <= 2
            
            # Verify chunk quality
            for chunk in chunks:
                assert chunk["word_count"] > 0
                assert chunk["char_count"] > 0
                assert "semantic_score" in chunk
                assert chunk["semantic_score"] >= 0.0
            
            # Verify no content loss
            total_chars = sum(chunk["char_count"] for chunk in chunks)
            assert total_chars <= len(content) * 1.1  # Allow for overlap
            
            print(f"{content_type}: {len(content)} chars -> {len(chunks)} chunks")


@pytest.mark.asyncio
async def test_end_to_end_performance_scenario():
    """Test complete end-to-end performance scenario."""
    # This test simulates a realistic performance scenario with:
    # - Large CSV processing
    # - PDF batch processing  
    # - Concurrent requests
    # - Caching utilization
    # - Token optimization
    
    # Mock services
    mock_db_adapter = AsyncMock()
    mock_vector_adapter = AsyncMock()
    
    # Create test data
    large_csv_content = "id,name,feedback\n" + "\n".join([
        f"{i},User{i},This is feedback {i} about pain points and issues"
        for i in range(1000)
    ])
    
    csv_file = UploadFile(
        filename="large_test.csv",
        file=io.BytesIO(large_csv_content.encode()),
        content_type="text/csv"
    )
    
    # Test CSV processing with caching
    extractor = DynamicCSVStatisticsExtractor()
    
    start_time = time.time()
    
    # First extraction (cache miss)
    with patch.object(extractor, '_get_file_size_mb', return_value=5):  # Small file
        statistics1 = await extractor.extract_statistics(csv_file, "test_project")
    
    first_time = time.time() - start_time
    
    # Reset file position
    csv_file.file.seek(0)
    
    # Second extraction (should use cache)
    start_time = time.time()
    with patch.object(extractor, '_get_file_size_mb', return_value=5):
        statistics2 = await extractor.extract_statistics(csv_file, "test_project")
    
    second_time = time.time() - start_time
    
    # Verify caching effectiveness
    assert statistics1 == statistics2
    assert second_time < first_time * 0.5  # Should be at least 2x faster
    
    print(f"End-to-end performance test completed")
    print(f"First extraction: {first_time:.2f}s, Second extraction: {second_time:.2f}s")
    print(f"Cache speedup: {first_time/second_time:.1f}x")


if __name__ == "__main__":
    # Run performance tests
    pytest.main([__file__, "-v", "-s"])