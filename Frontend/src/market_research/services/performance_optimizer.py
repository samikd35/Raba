"""
Performance Optimization Service for Market Research Analysis

Implements streaming processing, batch operations, and memory management
for handling large datasets efficiently without memory limitations.
"""

import asyncio
import logging
import psutil
import gc
from typing import Dict, Any, Optional, List, AsyncGenerator, Tuple
from datetime import datetime
import pandas as pd
import numpy as np
from fastapi import UploadFile
from concurrent.futures import ThreadPoolExecutor, as_completed
import io
from dataclasses import dataclass
from contextlib import asynccontextmanager

from ..utils.error_handling import (
    DocumentProcessingError, PerformanceError,
    handle_document_processing_errors, monitor_performance,
    error_monitor, ErrorCategory, ErrorSeverity
)

logger = logging.getLogger(__name__)


@dataclass
class ProcessingMetrics:
    """Metrics for tracking processing performance."""
    start_time: datetime
    end_time: Optional[datetime] = None
    memory_usage_mb: float = 0.0
    peak_memory_mb: float = 0.0
    rows_processed: int = 0
    chunks_processed: int = 0
    processing_rate: float = 0.0  # rows per second
    
    def calculate_rate(self):
        """Calculate processing rate."""
        if self.end_time and self.rows_processed > 0:
            duration = (self.end_time - self.start_time).total_seconds()
            self.processing_rate = self.rows_processed / duration if duration > 0 else 0.0


class StreamingCSVProcessor:
    """
    Streaming CSV processor for handling large files without loading entire dataset into memory.
    
    Features:
    - Chunk-based processing with configurable chunk sizes
    - Memory usage monitoring and automatic garbage collection
    - Progress tracking and rate limiting
    - Adaptive chunk sizing based on available memory
    """
    
    # Configuration constants
    DEFAULT_CHUNK_SIZE = 1000  # Rows per chunk
    MIN_CHUNK_SIZE = 100
    MAX_CHUNK_SIZE = 10000
    MEMORY_THRESHOLD_MB = 500  # Memory threshold for adaptive sizing
    
    def __init__(self, chunk_size: Optional[int] = None):
        """Initialize streaming CSV processor."""
        self.chunk_size = chunk_size or self.DEFAULT_CHUNK_SIZE
        self.logger = logger
        self.metrics = None
        
    @monitor_performance("streaming_csv_processing")
    async def process_large_csv_streaming(
        self,
        csv_file: UploadFile,
        project_id: str,
        persona_id: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process large CSV files using streaming approach.
        
        Args:
            csv_file: Uploaded CSV file
            project_id: Project identifier
            persona_id: Optional persona association
            progress_callback: Optional callback for progress updates
            
        Yields:
            Dictionary containing chunk statistics and metadata
        """
        self.metrics = ProcessingMetrics(start_time=datetime.utcnow())
        
        try:
            # Read file content
            content = await csv_file.read()
            await csv_file.seek(0)
            
            # Detect encoding and delimiter
            encoding, delimiter = await self._detect_csv_format(content)
            
            # Create streaming reader
            csv_stream = io.StringIO(content.decode(encoding))
            
            # Read header to determine columns
            header_line = csv_stream.readline()
            columns = [col.strip() for col in header_line.split(delimiter)]
            csv_stream.seek(0)  # Reset to beginning
            
            # Initialize chunk processing
            chunk_number = 0
            total_rows_processed = 0
            
            # Process in chunks
            async for chunk_df in self._read_csv_chunks(csv_stream, delimiter, encoding):
                chunk_number += 1
                
                # Monitor memory usage
                current_memory = self._get_memory_usage_mb()
                self.metrics.memory_usage_mb = current_memory
                self.metrics.peak_memory_mb = max(self.metrics.peak_memory_mb, current_memory)
                
                # Adaptive chunk sizing based on memory usage
                if current_memory > self.MEMORY_THRESHOLD_MB:
                    self.chunk_size = max(self.MIN_CHUNK_SIZE, self.chunk_size // 2)
                    gc.collect()  # Force garbage collection
                elif current_memory < self.MEMORY_THRESHOLD_MB * 0.5:
                    self.chunk_size = min(self.MAX_CHUNK_SIZE, self.chunk_size * 2)
                
                # Process chunk statistics
                chunk_stats = await self._process_chunk_statistics(
                    chunk_df, chunk_number, project_id, persona_id
                )
                
                # Update metrics
                total_rows_processed += len(chunk_df)
                self.metrics.rows_processed = total_rows_processed
                self.metrics.chunks_processed = chunk_number
                
                # Progress callback
                if progress_callback:
                    await progress_callback({
                        "chunk_number": chunk_number,
                        "rows_processed": total_rows_processed,
                        "memory_usage_mb": current_memory,
                        "chunk_size": self.chunk_size
                    })
                
                # Yield chunk results
                yield {
                    "chunk_number": chunk_number,
                    "chunk_statistics": chunk_stats,
                    "processing_metrics": {
                        "rows_in_chunk": len(chunk_df),
                        "total_rows_processed": total_rows_processed,
                        "memory_usage_mb": current_memory,
                        "adaptive_chunk_size": self.chunk_size
                    }
                }
                
                # Clean up chunk data
                del chunk_df
                gc.collect()
            
            # Finalize metrics
            self.metrics.end_time = datetime.utcnow()
            self.metrics.calculate_rate()
            
            self.logger.info(
                f"Completed streaming CSV processing: {total_rows_processed} rows, "
                f"{chunk_number} chunks, {self.metrics.processing_rate:.2f} rows/sec"
            )
            
        except Exception as e:
            self.logger.error(f"Error in streaming CSV processing: {e}")
            raise PerformanceError(
                f"Streaming CSV processing failed: {str(e)}",
                error_code="STREAMING_CSV_ERROR"
            )
    
    async def _read_csv_chunks(
        self, 
        csv_stream: io.StringIO, 
        delimiter: str, 
        encoding: str
    ) -> AsyncGenerator[pd.DataFrame, None]:
        """
        Read CSV in chunks using pandas chunk reader.
        
        Args:
            csv_stream: CSV string stream
            delimiter: CSV delimiter
            encoding: File encoding
            
        Yields:
            DataFrame chunks
        """
        try:
            # Reset stream position
            csv_stream.seek(0)
            
            # Create chunk reader
            chunk_reader = pd.read_csv(
                csv_stream,
                delimiter=delimiter,
                chunksize=self.chunk_size,
                low_memory=False,
                dtype=str  # Read all as strings initially to avoid type inference overhead
            )
            
            for chunk in chunk_reader:
                # Clean column names
                chunk.columns = chunk.columns.astype(str).str.strip()
                
                # Handle empty chunks
                if chunk.empty:
                    continue
                
                yield chunk
                
        except Exception as e:
            self.logger.error(f"Error reading CSV chunks: {e}")
            raise
    
    async def _process_chunk_statistics(
        self,
        chunk_df: pd.DataFrame,
        chunk_number: int,
        project_id: str,
        persona_id: Optional[str]
    ) -> Dict[str, Any]:
        """
        Process statistics for a single chunk.
        
        Args:
            chunk_df: DataFrame chunk
            chunk_number: Chunk number
            project_id: Project identifier
            persona_id: Optional persona association
            
        Returns:
            Dictionary containing chunk statistics
        """
        try:
            # Detect field types for this chunk
            field_types = {}
            for column in chunk_df.columns:
                series = chunk_df[column].dropna()
                if len(series) == 0:
                    field_types[column] = "empty"
                    continue
                
                # Simple type detection
                unique_count = series.nunique()
                if unique_count <= 50:  # Categorical threshold
                    field_types[column] = "categorical"
                else:
                    # Try numeric conversion
                    try:
                        pd.to_numeric(series.head(100), errors='raise')
                        field_types[column] = "numerical"
                    except (ValueError, TypeError):
                        field_types[column] = "text"
            
            # Extract categorical distributions for this chunk
            categorical_stats = {}
            for column, field_type in field_types.items():
                if field_type == "categorical":
                    series = chunk_df[column].dropna()
                    if len(series) > 0:
                        value_counts = series.value_counts()
                        categorical_stats[column] = {
                            "chunk_total": len(series),
                            "unique_values": len(value_counts),
                            "top_values": value_counts.head(10).to_dict()
                        }
            
            return {
                "chunk_id": f"chunk_{chunk_number}",
                "row_count": len(chunk_df),
                "column_count": len(chunk_df.columns),
                "field_types": field_types,
                "categorical_distributions": categorical_stats,
                "null_counts": chunk_df.isnull().sum().to_dict(),
                "memory_usage_bytes": chunk_df.memory_usage(deep=True).sum()
            }
            
        except Exception as e:
            self.logger.error(f"Error processing chunk {chunk_number} statistics: {e}")
            return {
                "chunk_id": f"chunk_{chunk_number}",
                "error": str(e),
                "row_count": len(chunk_df) if chunk_df is not None else 0
            }
    
    async def _detect_csv_format(self, content: bytes) -> Tuple[str, str]:
        """
        Detect CSV encoding and delimiter.
        
        Args:
            content: Raw file content
            
        Returns:
            Tuple of (encoding, delimiter)
        """
        # Try different encodings
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
        
        for encoding in encodings:
            try:
                decoded_content = content.decode(encoding)
                
                # Detect delimiter by analyzing first few lines
                lines = decoded_content.split('\n')[:5]
                if not lines:
                    continue
                
                # Count potential delimiters
                delimiters = [',', ';', '\t', '|']
                delimiter_counts = {}
                
                for delimiter in delimiters:
                    counts = [line.count(delimiter) for line in lines if line.strip()]
                    if counts and all(count == counts[0] for count in counts) and counts[0] > 0:
                        delimiter_counts[delimiter] = counts[0]
                
                # Choose delimiter with highest consistent count
                if delimiter_counts:
                    best_delimiter = max(delimiter_counts.items(), key=lambda x: x[1])[0]
                    return encoding, best_delimiter
                
            except UnicodeDecodeError:
                continue
        
        # Default fallback
        return 'utf-8', ','
    
    def _get_memory_usage_mb(self) -> float:
        """Get current memory usage in MB."""
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024


class BatchPDFProcessor:
    """
    Batch PDF processor for handling large PDF files with multiple pages efficiently.
    
    Features:
    - Page-by-page processing with memory management
    - Progress tracking and rate limiting
    - Parallel processing for independent pages
    - Memory cleanup between batches
    """
    
    # Configuration constants
    DEFAULT_BATCH_SIZE = 5  # Pages per batch
    MAX_CONCURRENT_PAGES = 3  # Maximum concurrent page processing
    MEMORY_THRESHOLD_MB = 300  # Memory threshold for batch sizing
    
    def __init__(self, batch_size: Optional[int] = None):
        """Initialize batch PDF processor."""
        self.batch_size = batch_size or self.DEFAULT_BATCH_SIZE
        self.logger = logger
        self.metrics = None
        
    @monitor_performance("batch_pdf_processing")
    async def process_large_pdf_batched(
        self,
        pdf_file: UploadFile,
        project_id: str,
        persona_id: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process large PDF files using batch approach.
        
        Args:
            pdf_file: Uploaded PDF file
            project_id: Project identifier
            persona_id: Optional persona association
            progress_callback: Optional callback for progress updates
            
        Yields:
            Dictionary containing batch results and metadata
        """
        self.metrics = ProcessingMetrics(start_time=datetime.utcnow())
        
        try:
            # Import PDF processing here to avoid loading if not needed
            from pypdf import PdfReader
            
            # Read PDF content
            content = await pdf_file.read()
            await pdf_file.seek(0)
            
            pdf_reader = PdfReader(io.BytesIO(content))
            total_pages = len(pdf_reader.pages)
            
            if total_pages == 0:
                raise PerformanceError("PDF contains no pages", error_code="PDF_NO_PAGES")
            
            # Process pages in batches
            batch_number = 0
            pages_processed = 0
            
            for batch_start in range(0, total_pages, self.batch_size):
                batch_number += 1
                batch_end = min(batch_start + self.batch_size, total_pages)
                
                # Monitor memory usage
                current_memory = self._get_memory_usage_mb()
                self.metrics.memory_usage_mb = current_memory
                self.metrics.peak_memory_mb = max(self.metrics.peak_memory_mb, current_memory)
                
                # Adaptive batch sizing
                if current_memory > self.MEMORY_THRESHOLD_MB:
                    self.batch_size = max(1, self.batch_size // 2)
                    gc.collect()
                elif current_memory < self.MEMORY_THRESHOLD_MB * 0.5:
                    self.batch_size = min(10, self.batch_size * 2)
                
                # Process batch
                batch_results = await self._process_page_batch(
                    pdf_reader, batch_start, batch_end, project_id, persona_id
                )
                
                # Update metrics
                pages_in_batch = batch_end - batch_start
                pages_processed += pages_in_batch
                self.metrics.rows_processed = pages_processed  # Using rows_processed for pages
                self.metrics.chunks_processed = batch_number
                
                # Progress callback
                if progress_callback:
                    await progress_callback({
                        "batch_number": batch_number,
                        "pages_processed": pages_processed,
                        "total_pages": total_pages,
                        "memory_usage_mb": current_memory,
                        "batch_size": self.batch_size
                    })
                
                # Yield batch results
                yield {
                    "batch_number": batch_number,
                    "batch_results": batch_results,
                    "processing_metrics": {
                        "pages_in_batch": pages_in_batch,
                        "total_pages_processed": pages_processed,
                        "total_pages": total_pages,
                        "memory_usage_mb": current_memory,
                        "adaptive_batch_size": self.batch_size
                    }
                }
                
                # Clean up batch data
                del batch_results
                gc.collect()
            
            # Finalize metrics
            self.metrics.end_time = datetime.utcnow()
            self.metrics.calculate_rate()
            
            self.logger.info(
                f"Completed batch PDF processing: {pages_processed} pages, "
                f"{batch_number} batches, {self.metrics.processing_rate:.2f} pages/sec"
            )
            
        except Exception as e:
            self.logger.error(f"Error in batch PDF processing: {e}")
            raise PerformanceError(
                f"Batch PDF processing failed: {str(e)}",
                error_code="BATCH_PDF_ERROR"
            )
    
    async def _process_page_batch(
        self,
        pdf_reader,
        batch_start: int,
        batch_end: int,
        project_id: str,
        persona_id: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        Process a batch of PDF pages concurrently.
        
        Args:
            pdf_reader: PDF reader object
            batch_start: Starting page index
            batch_end: Ending page index
            project_id: Project identifier
            persona_id: Optional persona association
            
        Returns:
            List of page processing results
        """
        try:
            # Create tasks for concurrent processing
            tasks = []
            semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_PAGES)
            
            for page_num in range(batch_start, batch_end):
                task = self._process_single_page(
                    pdf_reader.pages[page_num], page_num + 1, semaphore, project_id
                )
                tasks.append(task)
            
            # Wait for all pages in batch to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out exceptions and log errors
            valid_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.logger.error(f"Error processing page {batch_start + i + 1}: {result}")
                    valid_results.append({
                        "page_number": batch_start + i + 1,
                        "error": str(result),
                        "content": "",
                        "word_count": 0
                    })
                else:
                    valid_results.append(result)
            
            return valid_results
            
        except Exception as e:
            self.logger.error(f"Error processing page batch {batch_start}-{batch_end}: {e}")
            return []
    
    async def _process_single_page(
        self,
        page,
        page_number: int,
        semaphore: asyncio.Semaphore,
        project_id: str
    ) -> Dict[str, Any]:
        """
        Process a single PDF page with concurrency control.
        
        Args:
            page: PDF page object
            page_number: Page number
            semaphore: Concurrency semaphore
            project_id: Project identifier
            
        Returns:
            Dictionary containing page processing results
        """
        async with semaphore:
            try:
                # Extract text from page (run in thread pool to avoid blocking)
                loop = asyncio.get_event_loop()
                with ThreadPoolExecutor(max_workers=1) as executor:
                    page_text = await loop.run_in_executor(executor, page.extract_text)
                
                # Process page content
                word_count = len(page_text.split()) if page_text else 0
                
                # Simple theme extraction for this page
                themes = await self._extract_page_themes(page_text)
                
                return {
                    "page_number": page_number,
                    "content": page_text.strip() if page_text else "",
                    "word_count": word_count,
                    "char_count": len(page_text) if page_text else 0,
                    "themes": themes,
                    "processing_timestamp": datetime.utcnow().isoformat()
                }
                
            except Exception as e:
                self.logger.error(f"Error processing page {page_number}: {e}")
                return {
                    "page_number": page_number,
                    "error": str(e),
                    "content": "",
                    "word_count": 0
                }
    
    async def _extract_page_themes(self, page_text: str) -> List[str]:
        """
        Extract basic themes from a single page.
        
        Args:
            page_text: Text content of the page
            
        Returns:
            List of identified themes
        """
        if not page_text:
            return []
        
        # Simple keyword-based theme detection
        theme_keywords = {
            'problems': ['problem', 'issue', 'challenge', 'difficulty'],
            'solutions': ['solution', 'fix', 'resolve', 'solve'],
            'benefits': ['benefit', 'advantage', 'value', 'gain'],
            'emotions': ['happy', 'frustrated', 'satisfied', 'disappointed']
        }
        
        text_lower = page_text.lower()
        found_themes = []
        
        for theme, keywords in theme_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                found_themes.append(theme)
        
        return found_themes
    
    def _get_memory_usage_mb(self) -> float:
        """Get current memory usage in MB."""
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024


class EfficientEmbeddingGenerator:
    """
    Efficient embedding generator with batching and rate limit handling.
    
    Features:
    - Batch processing for multiple texts
    - Rate limit handling with exponential backoff
    - Memory-efficient processing
    - Progress tracking and monitoring
    """
    
    # Configuration constants
    DEFAULT_BATCH_SIZE = 10  # Texts per batch
    MAX_BATCH_SIZE = 50
    RATE_LIMIT_DELAY = 1.0  # Initial delay in seconds
    MAX_RETRIES = 3
    
    def __init__(self, batch_size: Optional[int] = None):
        """Initialize efficient embedding generator."""
        self.batch_size = batch_size or self.DEFAULT_BATCH_SIZE
        self.logger = logger
        self.rate_limit_delay = self.RATE_LIMIT_DELAY
        
    @monitor_performance("efficient_embedding_generation")
    async def generate_embeddings_batched(
        self,
        texts: List[str],
        embedding_service,
        progress_callback: Optional[callable] = None
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts using efficient batching.
        
        Args:
            texts: List of texts to embed
            embedding_service: Embedding service instance
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        try:
            embeddings = []
            total_texts = len(texts)
            processed_texts = 0
            
            # Process texts in batches
            for batch_start in range(0, total_texts, self.batch_size):
                batch_end = min(batch_start + self.batch_size, total_texts)
                batch_texts = texts[batch_start:batch_end]
                
                # Generate embeddings for batch with retry logic
                batch_embeddings = await self._generate_batch_with_retry(
                    batch_texts, embedding_service
                )
                
                embeddings.extend(batch_embeddings)
                processed_texts += len(batch_texts)
                
                # Progress callback
                if progress_callback:
                    await progress_callback({
                        "processed_texts": processed_texts,
                        "total_texts": total_texts,
                        "batch_size": len(batch_texts),
                        "current_delay": self.rate_limit_delay
                    })
                
                # Rate limiting delay between batches
                if batch_end < total_texts:  # Not the last batch
                    await asyncio.sleep(self.rate_limit_delay)
            
            self.logger.info(f"Generated embeddings for {total_texts} texts in {len(range(0, total_texts, self.batch_size))} batches")
            return embeddings
            
        except Exception as e:
            self.logger.error(f"Error in batch embedding generation: {e}")
            raise PerformanceError(
                f"Batch embedding generation failed: {str(e)}",
                error_code="BATCH_EMBEDDING_ERROR"
            )
    
    async def _generate_batch_with_retry(
        self,
        batch_texts: List[str],
        embedding_service
    ) -> List[List[float]]:
        """
        Generate embeddings for a batch with retry logic and rate limit handling.
        
        Args:
            batch_texts: Batch of texts to embed
            embedding_service: Embedding service instance
            
        Returns:
            List of embedding vectors for the batch
        """
        for attempt in range(self.MAX_RETRIES):
            try:
                # Generate embeddings for the batch
                embeddings = await embedding_service.generate_embeddings(batch_texts)
                
                # Reset rate limit delay on success
                self.rate_limit_delay = self.RATE_LIMIT_DELAY
                
                return embeddings
                
            except Exception as e:
                error_str = str(e).lower()
                
                # Check if it's a rate limit error
                if 'rate limit' in error_str or 'too many requests' in error_str:
                    # Exponential backoff for rate limits
                    self.rate_limit_delay *= 2
                    wait_time = self.rate_limit_delay * (2 ** attempt)
                    
                    self.logger.warning(
                        f"Rate limit hit, waiting {wait_time:.2f}s before retry {attempt + 1}/{self.MAX_RETRIES}"
                    )
                    
                    await asyncio.sleep(wait_time)
                    continue
                
                # For other errors, retry with shorter delay
                elif attempt < self.MAX_RETRIES - 1:
                    wait_time = 1.0 * (2 ** attempt)
                    self.logger.warning(f"Embedding generation failed, retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                    continue
                
                # Final attempt failed
                raise e
        
        # If we get here, all retries failed
        raise PerformanceError(
            f"Failed to generate embeddings after {self.MAX_RETRIES} attempts",
            error_code="EMBEDDING_RETRY_EXHAUSTED"
        )


class IntelligentChunkingStrategy:
    """
    Intelligent chunking strategy that optimizes for both accuracy and performance.
    
    Features:
    - Adaptive chunk sizing based on content characteristics
    - Semantic boundary detection
    - Memory-aware chunking
    - Performance optimization for different content types
    """
    
    # Configuration constants
    DEFAULT_CHUNK_SIZE = 1000  # Characters
    MIN_CHUNK_SIZE = 200
    MAX_CHUNK_SIZE = 2000
    OVERLAP_SIZE = 100  # Character overlap between chunks
    
    def __init__(self):
        """Initialize intelligent chunking strategy."""
        self.logger = logger
    
    @monitor_performance("intelligent_chunking")
    async def create_optimized_chunks(
        self,
        content: str,
        content_type: str = "text",
        target_chunk_count: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Create optimized chunks based on content characteristics.
        
        Args:
            content: Text content to chunk
            content_type: Type of content (text, csv, pdf)
            target_chunk_count: Optional target number of chunks
            
        Returns:
            List of chunk dictionaries with metadata
        """
        if not content or not content.strip():
            return []
        
        try:
            # Determine optimal chunk size based on content
            optimal_chunk_size = self._calculate_optimal_chunk_size(
                content, content_type, target_chunk_count
            )
            
            # Create chunks with semantic boundaries
            chunks = await self._create_semantic_chunks(content, optimal_chunk_size)
            
            # Add metadata to chunks
            enhanced_chunks = []
            for i, chunk in enumerate(chunks):
                enhanced_chunks.append({
                    "chunk_id": f"chunk_{i}",
                    "content": chunk["content"],
                    "start_pos": chunk["start_pos"],
                    "end_pos": chunk["end_pos"],
                    "word_count": len(chunk["content"].split()),
                    "char_count": len(chunk["content"]),
                    "chunk_type": self._classify_chunk_content(chunk["content"]),
                    "semantic_score": chunk.get("semantic_score", 0.0)
                })
            
            self.logger.info(f"Created {len(enhanced_chunks)} optimized chunks with average size {optimal_chunk_size}")
            return enhanced_chunks
            
        except Exception as e:
            self.logger.error(f"Error in intelligent chunking: {e}")
            raise PerformanceError(
                f"Intelligent chunking failed: {str(e)}",
                error_code="INTELLIGENT_CHUNKING_ERROR"
            )
    
    def _calculate_optimal_chunk_size(
        self,
        content: str,
        content_type: str,
        target_chunk_count: Optional[int]
    ) -> int:
        """
        Calculate optimal chunk size based on content characteristics.
        
        Args:
            content: Text content
            content_type: Type of content
            target_chunk_count: Optional target number of chunks
            
        Returns:
            Optimal chunk size in characters
        """
        content_length = len(content)
        
        # If target chunk count is specified, calculate size accordingly
        if target_chunk_count and target_chunk_count > 0:
            calculated_size = content_length // target_chunk_count
            return max(self.MIN_CHUNK_SIZE, min(self.MAX_CHUNK_SIZE, calculated_size))
        
        # Content type specific optimization
        if content_type == "csv":
            # For CSV, prefer smaller chunks to maintain row integrity
            return min(self.DEFAULT_CHUNK_SIZE // 2, content_length // 10)
        elif content_type == "pdf":
            # For PDF, prefer larger chunks to maintain context
            return min(self.DEFAULT_CHUNK_SIZE * 2, content_length // 5)
        else:
            # Default text chunking
            # Adaptive sizing based on content length
            if content_length < 5000:
                return max(self.MIN_CHUNK_SIZE, content_length // 3)
            elif content_length < 20000:
                return self.DEFAULT_CHUNK_SIZE
            else:
                return min(self.MAX_CHUNK_SIZE, content_length // 20)
    
    async def _create_semantic_chunks(
        self,
        content: str,
        chunk_size: int
    ) -> List[Dict[str, Any]]:
        """
        Create chunks with semantic boundary detection.
        
        Args:
            content: Text content
            chunk_size: Target chunk size
            
        Returns:
            List of chunk dictionaries
        """
        chunks = []
        current_pos = 0
        
        while current_pos < len(content):
            # Calculate chunk end position
            chunk_end = min(current_pos + chunk_size, len(content))
            
            # Find semantic boundary if not at end of content
            if chunk_end < len(content):
                chunk_end = self._find_semantic_boundary(content, current_pos, chunk_end)
            
            # Extract chunk content
            chunk_content = content[current_pos:chunk_end].strip()
            
            if chunk_content:
                chunks.append({
                    "content": chunk_content,
                    "start_pos": current_pos,
                    "end_pos": chunk_end,
                    "semantic_score": self._calculate_semantic_score(chunk_content)
                })
            
            # Move to next chunk with overlap
            current_pos = max(chunk_end - self.OVERLAP_SIZE, chunk_end)
            
            # Prevent infinite loop
            if current_pos >= len(content):
                break
        
        return chunks
    
    def _find_semantic_boundary(self, content: str, start_pos: int, target_end: int) -> int:
        """
        Find the best semantic boundary near the target end position.
        
        Args:
            content: Full text content
            start_pos: Start position of chunk
            target_end: Target end position
            
        Returns:
            Adjusted end position at semantic boundary
        """
        # Look for boundaries in order of preference
        search_window = min(200, (target_end - start_pos) // 4)
        search_start = max(start_pos, target_end - search_window)
        search_text = content[search_start:target_end + search_window]
        
        # Sentence boundaries (highest priority)
        sentence_endings = ['.', '!', '?']
        for ending in sentence_endings:
            pos = search_text.rfind(ending)
            if pos > search_window // 2:  # Not too close to start
                return search_start + pos + 1
        
        # Paragraph boundaries
        paragraph_pos = search_text.rfind('\n\n')
        if paragraph_pos > search_window // 4:
            return search_start + paragraph_pos + 2
        
        # Line boundaries
        line_pos = search_text.rfind('\n')
        if line_pos > search_window // 4:
            return search_start + line_pos + 1
        
        # Word boundaries (lowest priority)
        word_pos = search_text.rfind(' ')
        if word_pos > search_window // 4:
            return search_start + word_pos + 1
        
        # If no good boundary found, use target position
        return target_end
    
    def _calculate_semantic_score(self, chunk_content: str) -> float:
        """
        Calculate semantic coherence score for a chunk.
        
        Args:
            chunk_content: Chunk text content
            
        Returns:
            Semantic score (0.0 to 1.0)
        """
        if not chunk_content.strip():
            return 0.0
        
        # Simple heuristics for semantic coherence
        score = 0.0
        
        # Complete sentences bonus
        sentences = chunk_content.count('.') + chunk_content.count('!') + chunk_content.count('?')
        if sentences > 0:
            score += 0.3
        
        # Paragraph structure bonus
        if '\n\n' in chunk_content:
            score += 0.2
        
        # Length appropriateness
        word_count = len(chunk_content.split())
        if 50 <= word_count <= 300:  # Optimal word count range
            score += 0.3
        
        # Avoid fragments (starting/ending mid-word)
        if chunk_content[0].isupper() or chunk_content.startswith(' '):
            score += 0.1
        
        if chunk_content.rstrip()[-1] in '.!?':
            score += 0.1
        
        return min(1.0, score)
    
    def _classify_chunk_content(self, chunk_content: str) -> str:
        """
        Classify the type of content in a chunk.
        
        Args:
            chunk_content: Chunk text content
            
        Returns:
            Content type classification
        """
        content_lower = chunk_content.lower()
        
        # Statistical content
        if any(word in content_lower for word in ['%', 'percent', 'statistics', 'data', 'survey']):
            return "statistical"
        
        # Quote content
        if '"' in chunk_content or "'" in chunk_content:
            return "quote"
        
        # Question content
        if '?' in chunk_content:
            return "question"
        
        # Narrative content
        return "narrative"


# Service instance getters following VMP patterns
_streaming_csv_processor: Optional[StreamingCSVProcessor] = None
_batch_pdf_processor: Optional[BatchPDFProcessor] = None
_efficient_embedding_generator: Optional[EfficientEmbeddingGenerator] = None
_intelligent_chunking_strategy: Optional[IntelligentChunkingStrategy] = None

def get_streaming_csv_processor() -> StreamingCSVProcessor:
    """Get streaming CSV processor service singleton."""
    global _streaming_csv_processor
    if _streaming_csv_processor is None:
        _streaming_csv_processor = StreamingCSVProcessor()
    return _streaming_csv_processor

def get_batch_pdf_processor() -> BatchPDFProcessor:
    """Get batch PDF processor service singleton."""
    global _batch_pdf_processor
    if _batch_pdf_processor is None:
        _batch_pdf_processor = BatchPDFProcessor()
    return _batch_pdf_processor

def get_efficient_embedding_generator() -> EfficientEmbeddingGenerator:
    """Get efficient embedding generator service singleton."""
    global _efficient_embedding_generator
    if _efficient_embedding_generator is None:
        _efficient_embedding_generator = EfficientEmbeddingGenerator()
    return _efficient_embedding_generator

def get_intelligent_chunking_strategy() -> IntelligentChunkingStrategy:
    """Get intelligent chunking strategy service singleton."""
    global _intelligent_chunking_strategy
    if _intelligent_chunking_strategy is None:
        _intelligent_chunking_strategy = IntelligentChunkingStrategy()
    return _intelligent_chunking_strategy