"""
Chunking and Embedding Engine for Data Analysis Agent

Handles text chunking and embedding generation for semantic processing
following VMP service patterns and integrating with existing embedding services.
"""

import logging
import re
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
try:
    import tiktoken
except ImportError:  # pragma: no cover - optional dependency in test environments
    tiktoken = None

# Import existing embedding service - with fallback for testing
try:
    from src.mint.api.services.ai.embedding_service import get_embedding_service
except ImportError:
    # Fallback for testing environment
    def get_embedding_service():
        class MockEmbeddingService:
            async def generate_embeddings(self, texts):
                return [[0.1, 0.2, 0.3] for _ in texts]
        return MockEmbeddingService()

# Import the existing database adapter from market_research
from ..adapters.database_adapter import (
    AnalysisAgentDatabaseAdapter,
    sanitize_chunk_for_storage,
)

from ..utils.error_handling import (
    DocumentProcessingError, AIServiceError, TokenLimitError,
    handle_document_processing_errors, handle_ai_service_errors,
    retry_with_exponential_backoff, monitor_performance,
    error_monitor, ErrorCategory, ErrorSeverity, resource_monitor
)

# Import AI token monitoring service
import asyncio
from monitor.tokens.service import get_monitoring_service
from monitor.tokens.models import AIUsageContext


logger = logging.getLogger(__name__)


class ChunkingAndEmbeddingEngine:
    """
    Engine for chunking text content and generating embeddings for semantic search.
    
    Integrates with existing Yuba embedding services and follows VMP patterns
    for consistent data processing and storage.
    """
    
    # Default chunking parameters
    DEFAULT_CHUNK_SIZE = 1000  # characters
    DEFAULT_CHUNK_OVERLAP = 200  # characters
    MIN_CHUNK_SIZE = 100  # minimum viable chunk size
    MAX_CHUNK_SIZE = 2000  # maximum chunk size
    
    def __init__(self, db_adapter: Optional[AnalysisAgentDatabaseAdapter] = None):
        """
        Initialize the chunking and embedding engine.
        
        Args:
            db_adapter: Optional database adapter for storage operations
        """
        self.db_adapter = db_adapter or AnalysisAgentDatabaseAdapter(use_service_role=True)
        self.embedding_service = get_embedding_service()
        
        # Initialize tokenizer lazily to avoid memory spikes during startup
        self.tokenizer = None
        self._tokenizer_initialized = False
    
    @handle_document_processing_errors
    @monitor_performance("content_chunking")
    async def chunk_content(
        self, 
        content: str, 
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
        content_type: str = "text"
    ) -> List[Dict[str, Any]]:
        """
        Chunk text content into semantic segments with comprehensive error handling.
        
        Args:
            content: Text content to chunk
            chunk_size: Target size for each chunk (in characters)
            chunk_overlap: Overlap between consecutive chunks
            content_type: Type of content being chunked
            
        Returns:
            List of chunk dictionaries with content and metadata
            
        Raises:
            DocumentProcessingError: If chunking fails
        """
        operation_data = resource_monitor.start_operation(
            f"chunk_content_{content_type}",
            {"content_length": len(content), "chunk_size": chunk_size}
        )
        
        try:
            if not content or not content.strip():
                raise DocumentProcessingError(
                    "Content is empty or contains only whitespace",
                    error_code="EMPTY_CONTENT"
                )
            
            # Validate content size
            if len(content) > 10_000_000:  # 10MB text limit
                raise DocumentProcessingError(
                    f"Content too large for chunking: {len(content)} characters. Maximum: 10,000,000",
                    error_code="CONTENT_TOO_LARGE"
                )
            
            # Validate parameters
            original_chunk_size = chunk_size
            chunk_size = max(self.MIN_CHUNK_SIZE, min(chunk_size, self.MAX_CHUNK_SIZE))
            chunk_overlap = min(chunk_overlap, chunk_size // 2)  # Overlap can't be more than half
            
            if original_chunk_size != chunk_size:
                logger.warning(f"Chunk size adjusted from {original_chunk_size} to {chunk_size}")
            
            # Clean and normalize content
            try:
                cleaned_content = self._clean_content(content)
            except Exception as e:
                raise DocumentProcessingError(
                    f"Failed to clean content: {str(e)}",
                    error_code="CONTENT_CLEANING_ERROR"
                )
            
            # Choose chunking strategy based on content type
            try:
                logger.info(f"📄 CHUNKING: Processing {content_type} content ({len(cleaned_content)} chars)")
                if content_type == "pdf":
                    chunks = await self._chunk_pdf_content(cleaned_content, chunk_size, chunk_overlap)
                elif content_type == "csv":
                    chunks = await self._chunk_csv_content(cleaned_content, chunk_size, chunk_overlap)
                else:
                    chunks = await self._chunk_generic_content(cleaned_content, chunk_size, chunk_overlap)
            except Exception as e:
                logger.error(f"❌ CHUNKING FAILED: {e}")
                raise DocumentProcessingError(
                    f"Failed to chunk {content_type} content: {str(e)}",
                    error_code=f"CHUNKING_{content_type.upper()}_ERROR"
                )
            
            # Add metadata to chunks
            processed_chunks = []
            for i, chunk_text in enumerate(chunks):
                try:
                    if len(chunk_text.strip()) >= self.MIN_CHUNK_SIZE:
                        chunk_data = {
                            "index": i,
                            "content": chunk_text.strip(),
                            "character_count": len(chunk_text.strip()),
                            "word_count": len(chunk_text.strip().split()),
                            "token_count": self._count_tokens(chunk_text),
                            "content_type": content_type,
                            "chunk_hash": self._generate_chunk_hash(chunk_text),
                            "created_at": datetime.utcnow().isoformat()
                        }
                        processed_chunks.append(chunk_data)
                except Exception as e:
                    logger.warning(f"Failed to process chunk {i}: {e}")
                    continue
            
            if not processed_chunks:
                raise DocumentProcessingError(
                    "No valid chunks were created from the content",
                    error_code="NO_VALID_CHUNKS"
                )
            
            logger.info(f"Successfully chunked content into {len(processed_chunks)} chunks")
            
            # Record success
            error_monitor.record_error(
                Exception(f"Successfully chunked {content_type} content into {len(processed_chunks)} chunks"),
                ErrorCategory.DOCUMENT_PROCESSING,
                ErrorSeverity.LOW,
                {"content_type": content_type, "chunk_count": len(processed_chunks)}
            )
            
            return processed_chunks
            
        except DocumentProcessingError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error chunking content: {e}")
            raise DocumentProcessingError(
                f"Unexpected error during content chunking: {str(e)}",
                error_code="CHUNKING_UNEXPECTED_ERROR"
            )
        finally:
            resource_monitor.end_operation(operation_data)
    
    @handle_ai_service_errors
    @monitor_performance("embedding_generation")
    @retry_with_exponential_backoff(max_retries=3, base_delay=2.0, exceptions=(AIServiceError, TokenLimitError))
    async def generate_embeddings(
        self, 
        chunks: List[Dict[str, Any]],
        monitoring_context: Optional[AIUsageContext] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate embeddings for chunks using existing embedding service with comprehensive error handling.
        
        Args:
            chunks: List of chunk dictionaries
            monitoring_context: Optional AI usage monitoring context for token tracking
            
        Returns:
            List of chunks with embeddings added
            
        Raises:
            AIServiceError: If embedding generation fails
            TokenLimitError: If token limits are exceeded
        """
        operation_data = resource_monitor.start_operation(
            "generate_embeddings",
            {"chunk_count": len(chunks)}
        )
        
        # Record start time for monitoring
        started_at = datetime.utcnow()
        
        try:
            if not chunks:
                return []
            
            # Check for reasonable chunk count
            if len(chunks) > 1000:
                logger.warning(f"Large number of chunks for embedding: {len(chunks)}. This may take a while.")
            
            # Extract text content for embedding generation
            texts = []
            valid_chunk_indices = []
            
            for i, chunk in enumerate(chunks):
                content = chunk.get("content", "").strip()
                if content:
                    # Check token count if available
                    token_count = chunk.get("token_count", 0)
                    if token_count > 8000:  # OpenAI embedding limit
                        logger.warning(f"Chunk {i} has {token_count} tokens, may exceed embedding limits")
                        # Truncate content if too long
                        content = content[:6000]  # Conservative truncation
                    
                    texts.append(content)
                    valid_chunk_indices.append(i)
                else:
                    logger.warning(f"Chunk {i} has empty content, skipping embedding generation")
            
            if not texts:
                raise AIServiceError(
                    "No valid text content found for embedding generation",
                    error_code="NO_VALID_TEXT"
                )
            
            logger.info(f"Generating embeddings for {len(texts)} valid chunks")
            
            # Generate embeddings using existing service with error handling
            try:
                embeddings = await self.embedding_service.generate_embeddings(texts)
                    
            except Exception as e:
                error_msg = str(e).lower()
                if "token" in error_msg and ("limit" in error_msg or "exceeded" in error_msg):
                    raise TokenLimitError(
                        f"Token limit exceeded during embedding generation: {str(e)}",
                        error_code="EMBEDDING_TOKEN_LIMIT"
                    )
                elif "rate" in error_msg and "limit" in error_msg:
                    raise AIServiceError(
                        f"Rate limit exceeded during embedding generation: {str(e)}",
                        error_code="EMBEDDING_RATE_LIMIT",
                        retry_after=60
                    )
                else:
                    raise AIServiceError(
                        f"AI service error during embedding generation: {str(e)}",
                        error_code="EMBEDDING_SERVICE_ERROR"
                    )
            
            if not embeddings:
                raise AIServiceError(
                    "Embedding service returned no results",
                    error_code="EMPTY_EMBEDDING_RESPONSE"
                )
            
            # Add embeddings to chunks
            chunks_with_embeddings = []
            successful_embeddings = 0
            
            for i, chunk in enumerate(chunks):
                chunk_copy = chunk.copy()
                
                # Check if this chunk had valid content
                if i in valid_chunk_indices:
                    embedding_index = valid_chunk_indices.index(i)
                    
                    if (embedding_index < len(embeddings) and 
                        embeddings[embedding_index] is not None and
                        isinstance(embeddings[embedding_index], (list, tuple)) and
                        len(embeddings[embedding_index]) > 0):
                        
                        chunk_copy["embedding"] = embeddings[embedding_index]
                        chunk_copy["embedding_dimension"] = len(embeddings[embedding_index])
                        chunk_copy["has_embedding"] = True
                        successful_embeddings += 1
                    else:
                        chunk_copy["embedding"] = None
                        chunk_copy["embedding_dimension"] = 0
                        chunk_copy["has_embedding"] = False
                        logger.warning(f"Failed to generate embedding for chunk {i}")
                else:
                    # Chunk had no valid content
                    chunk_copy["embedding"] = None
                    chunk_copy["embedding_dimension"] = 0
                    chunk_copy["has_embedding"] = False
                
                chunks_with_embeddings.append(chunk_copy)
            
            # Check if we got reasonable success rate
            success_rate = successful_embeddings / len(chunks) if chunks else 0
            if success_rate < 0.5:  # Less than 50% success
                logger.error(f"Low embedding success rate: {successful_embeddings}/{len(chunks)} ({success_rate:.1%})")
                error_monitor.record_error(
                    Exception(f"Low embedding success rate: {success_rate:.1%}"),
                    ErrorCategory.AI_SERVICE,
                    ErrorSeverity.HIGH,
                    {"success_rate": success_rate, "successful": successful_embeddings, "total": len(chunks)}
                )
            
            logger.info(f"Successfully generated {successful_embeddings}/{len(chunks)} embeddings ({success_rate:.1%})")
            
            # Record AI usage for embedding generation (fire-and-forget)
            if monitoring_context:
                try:
                    finished_at = datetime.utcnow()
                    monitoring_service = get_monitoring_service()
                    # Estimate embedding tokens (roughly 1 token per 4 chars)
                    total_chars = sum(len(t) for t in texts)
                    estimated_tokens = total_chars // 4
                    asyncio.create_task(
                        monitoring_service.record_ai_usage(
                            context=monitoring_context,
                            provider="azure_openai",
                            model_name="text-embedding-3-small",
                            operation_type="embedding",
                            started_at=started_at,
                            finished_at=finished_at,
                            status="success",
                            embedding_tokens=estimated_tokens,
                            input_chars=total_chars,
                            extra_metadata={
                                "chunk_count": len(chunks),
                                "successful_embeddings": successful_embeddings
                            }
                        )
                    )
                except Exception as monitor_error:
                    logger.warning(f"Failed to record embedding monitoring: {monitor_error}")
            
            return chunks_with_embeddings
            
        except (AIServiceError, TokenLimitError):
            # Record error in monitoring
            if monitoring_context:
                try:
                    finished_at = datetime.utcnow()
                    monitoring_service = get_monitoring_service()
                    asyncio.create_task(
                        monitoring_service.record_ai_usage(
                            context=monitoring_context,
                            provider="azure_openai",
                            model_name="text-embedding-3-small",
                            operation_type="embedding",
                            started_at=started_at,
                            finished_at=finished_at,
                            status="error",
                            error_type="embedding_error"
                        )
                    )
                except Exception as monitor_error:
                    logger.warning(f"Failed to record embedding error monitoring: {monitor_error}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error generating embeddings: {e}")
            raise AIServiceError(
                f"Unexpected error during embedding generation: {str(e)}",
                error_code="EMBEDDING_UNEXPECTED_ERROR"
            )
        finally:
            resource_monitor.end_operation(operation_data)
    
    async def store_chunks_in_project(
        self, 
        project_id: str, 
        tenant_id: str,
        chunks: List[Dict[str, Any]],
        document_type: str = "research_document"
    ) -> bool:
        """
        Store chunks with embeddings in vmp_projects.research_documents_data.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID
            chunks: List of chunks with embeddings
            document_type: Type of document being stored
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get existing research document payload
            research_data = await self.db_adapter.get_research_documents_data(project_id, tenant_id)
            if research_data is None:
                research_data = {}

            # Sanitize chunks before persisting to avoid massive payloads
            sanitized_chunks = []
            total_tokens = 0
            for chunk in chunks:
                if not isinstance(chunk, dict):
                    continue

                sanitized_chunk = sanitize_chunk_for_storage(chunk)

                token_count = sanitized_chunk.get("token_count")
                if isinstance(token_count, int):
                    total_tokens += token_count

                sanitized_chunks.append(sanitized_chunk)

            doc_payload = research_data.get(document_type, {}) if isinstance(research_data.get(document_type), dict) else {}
            doc_payload.update({
                "chunks": sanitized_chunks,
                "chunk_count": len(sanitized_chunks),
                "chunks_with_embeddings": sum(1 for chunk in sanitized_chunks if chunk.get("has_embedding")),
                "total_tokens": total_tokens,
                "updated_at": datetime.utcnow().isoformat(),
            })
            research_data[document_type] = doc_payload

            # Update project with new research data
            success = await self.db_adapter.update_research_documents_data(
                project_id, tenant_id, research_data
            )
            
            if success:
                logger.info(f"Successfully stored {len(chunks)} chunks for project {project_id}")
            else:
                logger.error(f"Failed to store chunks for project {project_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error storing chunks in project: {e}")
            return False
    
    def _clean_content(self, content: str) -> str:
        """
        Clean and normalize content for chunking.
        
        Args:
            content: Raw content to clean
            
        Returns:
            Cleaned content
        """
        # Remove excessive whitespace
        content = re.sub(r'\s+', ' ', content)
        
        # Remove control characters but keep newlines
        content = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', content)
        
        # Normalize line endings
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        
        return content.strip()
    
    async def _chunk_generic_content(
        self, 
        content: str, 
        chunk_size: int, 
        chunk_overlap: int
    ) -> List[str]:
        """
        Chunk generic text content using sliding window approach.
        
        Args:
            content: Content to chunk
            chunk_size: Target chunk size
            chunk_overlap: Overlap between chunks
            
        Returns:
            List of chunk strings
        """
        chunks: List[str] = []
        start = 0
        content_length = len(content)

        while start < content_length:
            # Calculate tentative end position
            end = start + chunk_size

            # Ensure we don't move past the content length
            if end >= content_length:
                end = content_length
            else:
                # Try to break at a sentence boundary for cleaner chunks
                sentence_end = self._find_sentence_boundary(content, end, start + chunk_size // 2)
                if sentence_end > start:
                    end = sentence_end

            # Guard against malformed ranges
            if end <= start:
                end = min(start + self.MIN_CHUNK_SIZE, content_length)

            chunk = content[start:end]
            if chunk.strip():
                chunks.append(chunk)

            if end >= content_length:
                break

            # Move start position with overlap while guaranteeing forward progress
            next_start = end - chunk_overlap
            if next_start <= start:
                next_start = end
            start = next_start

        return chunks
    
    async def _chunk_pdf_content(
        self, 
        content: str, 
        chunk_size: int, 
        chunk_overlap: int
    ) -> List[str]:
        """
        Chunk PDF content with page-aware splitting.
        
        Args:
            content: PDF content with page markers
            chunk_size: Target chunk size
            chunk_overlap: Overlap between chunks
            
        Returns:
            List of chunk strings
        """
        # Split by page markers first
        page_pattern = r'--- Page \d+ ---'
        pages = re.split(page_pattern, content)
        
        chunks = []
        for page_content in pages:
            if page_content.strip():
                # Chunk each page individually
                page_chunks = await self._chunk_generic_content(
                    page_content.strip(), chunk_size, chunk_overlap
                )
                chunks.extend(page_chunks)
        
        return chunks
    
    async def _chunk_csv_content(
        self, 
        content: str, 
        chunk_size: int, 
        chunk_overlap: int
    ) -> List[str]:
        """
        Chunk CSV content with response-aware splitting.
        
        Args:
            content: CSV content with response markers
            chunk_size: Target chunk size
            chunk_overlap: Overlap between chunks
            
        Returns:
            List of chunk strings
        """
        # Split by response markers
        response_pattern = r'--- Response \d+ ---'
        responses = re.split(response_pattern, content)
        
        chunks = []
        current_chunk = ""
        
        for response in responses:
            response = response.strip()
            if not response:
                continue
            
            # If adding this response would exceed chunk size, finalize current chunk
            if current_chunk and len(current_chunk + response) > chunk_size:
                chunks.append(current_chunk.strip())
                current_chunk = response
            else:
                current_chunk += "\n\n" + response if current_chunk else response
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _find_sentence_boundary(self, content: str, preferred_end: int, min_end: int) -> int:
        """
        Find a good sentence boundary for chunking.
        
        Args:
            content: Content to search in
            preferred_end: Preferred end position
            min_end: Minimum acceptable end position
            
        Returns:
            Best end position found
        """
        # Look for sentence endings near the preferred position
        sentence_endings = ['.', '!', '?', '\n\n']
        
        # Search backwards from preferred_end
        for i in range(preferred_end, min_end - 1, -1):
            if i < len(content) and content[i] in sentence_endings:
                # Make sure we're not breaking in the middle of a number or abbreviation
                if content[i] == '.' and i > 0 and content[i-1].isdigit():
                    continue
                return i + 1
        
        # If no good boundary found, use preferred_end
        return preferred_end
    
    def _init_tokenizer_if_needed(self):
        """Initialize tokenizer lazily to avoid memory spikes during startup."""
        if not self._tokenizer_initialized:
            try:
                self.tokenizer = tiktoken.get_encoding("cl100k_base")  # GPT-4 tokenizer
                logger.info("✅ SUCCESS: Tokenizer initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize tokenizer, using fallback: {e}")
                self.tokenizer = None
            finally:
                self._tokenizer_initialized = True
    
    def _count_tokens(self, text: str) -> int:
        """
        Count tokens in text using tiktoken with lazy initialization.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Number of tokens
        """
        # Use simple word-based estimation to avoid tiktoken memory issues
        # This is safer and faster for chunking purposes
        return int(len(text.split()) * 1.3)  # Approximate token count
        
        # Commented out tiktoken usage to prevent memory issues:
        # self._init_tokenizer_if_needed()
        # if not self.tokenizer:
        #     return int(len(text.split()) * 1.3)
        # try:
        #     return len(self.tokenizer.encode(text))
        # except Exception:
        #     return int(len(text.split()) * 1.3)
    
    def _generate_chunk_hash(self, content: str) -> str:
        """
        Generate a hash for chunk content for deduplication.
        
        Args:
            content: Chunk content
            
        Returns:
            SHA-256 hash of content
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]


# Service instance getter following VMP patterns
_chunking_engine: Optional[ChunkingAndEmbeddingEngine] = None

def get_chunking_engine() -> ChunkingAndEmbeddingEngine:
    """Get chunking and embedding engine singleton."""
    global _chunking_engine
    if _chunking_engine is None:
        _chunking_engine = ChunkingAndEmbeddingEngine()
    return _chunking_engine
