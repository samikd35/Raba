"""
Embedding service for Problem Generator feature.

This module provides text embedding functionality for vector similarity search
using OpenAI's text-embedding-3-small model or other embedding providers.
"""

import logging
import hashlib
import json
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import asyncio
from functools import lru_cache
from datetime import datetime

from src.mint.providers.factory import get_provider
from src.mint.api.ai.providers import LLMProvider
from ..models.problem_models import ProblemStatementCreate, ProblemStatementResponse

# Import monitoring service
from monitor.tokens.service import get_monitoring_service
from monitor.tokens.models import AIUsageContext

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingResult:
    """Result of an embedding operation."""
    embedding: List[float]
    model_name: str  # Renamed from 'model' to avoid conflicts
    dimensions: int
    token_count: Optional[int] = None


class EmbeddingService:
    """Service for generating text embeddings for problem statements."""
    
    def __init__(
        self, 
        model_name: str = "text-embedding-3-small",
        user_id: str = None,
        tenant_id: str = None,
        project_id: str = None
    ):
        """
        Initialize the embedding service.
        
        Args:
            model_name: Name of the embedding model to use
            user_id: User ID for AI monitoring
            tenant_id: Tenant ID for AI monitoring
            project_id: Project ID for AI monitoring
        """
        self.model_name = model_name
        self.dimensions = 1536 if "3-small" in model_name else 768  # text-embedding-3-small uses 1536 dimensions
        self._provider = None
        self._embedding_cache = {}  # Simple in-memory cache
        # Monitoring context
        self._user_id = user_id
        self._tenant_id = tenant_id
        self._project_id = project_id
    
    @property
    def provider(self) -> LLMProvider:
        """Get the LLM provider instance."""
        if self._provider is None:
            self._provider = get_provider("llm", "openai")
        return self._provider
    
    def _create_cache_key(self, text: str, model: str) -> str:
        """
        Create a cache key for the embedding.
        
        Args:
            text: Input text
            model: Model name
            
        Returns:
            Cache key string
        """
        content = f"{text}:{model}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _prepare_problem_text(self, problem: ProblemStatementCreate) -> str:
        """
        Prepare problem statement text for embedding.
        
        Args:
            problem: Problem statement data
            
        Returns:
            Formatted text for embedding
        """
        # Combine key fields into a comprehensive text representation
        text_parts = [
            f"Title: {problem.title}",
            f"Description: {problem.description}",
            f"Category: {problem.category.value}",
            f"Severity: {problem.severity_level.value}",
            f"Type: {problem.problem_type.value}",
            f"Time Horizon: {problem.time_horizon.value}",
            f"Complexity: {problem.complexity_level.value}"
        ]
        
        # Add geography if specified
        if problem.target_geography:
            text_parts.append(f"Geography: {', '.join(problem.target_geography)}")
        
        # Add impact focus if specified
        if problem.impact_focus:
            text_parts.append(f"Impact Focus: {', '.join(problem.impact_focus)}")
        
        # Add root causes if available
        if problem.root_causes:
            text_parts.append(f"Root Causes: {'; '.join(problem.root_causes)}")
        
        # Add potential effects if available
        if problem.potential_effects:
            text_parts.append(f"Effects: {'; '.join(problem.potential_effects)}")
        
        # Add stakeholders if available
        if problem.stakeholders:
            text_parts.append(f"Stakeholders: {', '.join(problem.stakeholders)}")
        
        return "\n".join(text_parts)
    
    def _prepare_response_text(self, problem: ProblemStatementResponse) -> str:
        """
        Prepare problem statement response text for embedding.
        
        Args:
            problem: Problem statement response data
            
        Returns:
            Formatted text for embedding
        """
        # Convert response to create format for consistency
        problem_create = ProblemStatementCreate(
            title=problem.title,
            description=problem.description,
            category=problem.category,
            severity_level=problem.severity_level,
            target_geography=problem.target_geography,
            impact_focus=problem.impact_focus,
            affected_population_size=problem.affected_population_size,
            problem_type=problem.problem_type,
            time_horizon=problem.time_horizon,
            complexity_level=problem.complexity_level,
            root_causes=problem.root_causes,
            potential_effects=problem.potential_effects,
            stakeholders=problem.stakeholders,
            success_metrics=problem.success_metrics,
            generation_parameters=problem.generation_parameters,
            generation_model=problem.generation_model
        )
        
        return self._prepare_problem_text(problem_create)
    
    async def generate_embedding(self, text: str) -> Optional[EmbeddingResult]:
        """
        Generate embedding for the given text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding result or None if failed
        """
        try:
            # Check cache first
            cache_key = self._create_cache_key(text, self.model_name)
            if cache_key in self._embedding_cache:
                logger.debug(f"Using cached embedding for text (length: {len(text)})")
                return self._embedding_cache[cache_key]
            
            # Truncate text if too long (OpenAI has token limits)
            if len(text) > 8000:  # Conservative limit
                text = text[:8000] + "..."
                logger.warning(f"Truncated text to 8000 characters for embedding")
            
            # Generate embedding using the provider
            # Note: This is a simplified approach - in practice, you'd use the provider's embedding method
            logger.info(f"Generating embedding for text (length: {len(text)}) using {self.model_name}")
            
            # Use the real embedding service from mint.api
            from src.mint.api.services.ai.embedding_service import get_embedding_service
            
            # Get the real embedding service
            real_embedding_service = get_embedding_service()
            
            # Generate embedding using the real service with monitoring
            embedding_start_time = datetime.now()
            
            try:
                embeddings = await real_embedding_service.generate_embeddings([text])
                embedding_end_time = datetime.now()
                
                # Fire-and-forget monitoring
                monitoring = get_monitoring_service()
                monitor_context = AIUsageContext(
                    user_id=self._user_id if hasattr(self, '_user_id') else None,
                    tenant_id=self._tenant_id if hasattr(self, '_tenant_id') else None,
                    team_id=None,
                    project_id=self._project_id if hasattr(self, '_project_id') else None,
                    feature_id="pgen_embedding_generation",
                    workflow_name="problem_generator_workflow",
                    step_name="embedding_service",
                    environment="prod"
                )
                
                # Estimate tokens (rough approximation: 1 token ≈ 4 characters)
                estimated_tokens = len(text) // 4
                
                asyncio.create_task(
                    monitoring.record_ai_usage(
                        context=monitor_context,
                        provider="openai",
                        model_name=self.model_name,
                        operation_type="embedding",
                        started_at=embedding_start_time,
                        finished_at=embedding_end_time,
                        status="success",
                        embedding_tokens=estimated_tokens,
                        input_chars=len(text)
                    )
                )
                
            except Exception as e:
                embedding_end_time = datetime.now()
                
                # Record error
                monitoring = get_monitoring_service()
                monitor_context = AIUsageContext(
                    user_id=self._user_id if hasattr(self, '_user_id') else None,
                    tenant_id=self._tenant_id if hasattr(self, '_tenant_id') else None,
                    team_id=None,
                    project_id=self._project_id if hasattr(self, '_project_id') else None,
                    feature_id="pgen_embedding_generation",
                    workflow_name="problem_generator_workflow",
                    step_name="embedding_service",
                    environment="prod"
                )
                
                asyncio.create_task(
                    monitoring.record_ai_usage(
                        context=monitor_context,
                        provider="openai",
                        model_name=self.model_name,
                        operation_type="embedding",
                        started_at=embedding_start_time,
                        finished_at=embedding_end_time,
                        status="error",
                        error_type=type(e).__name__,
                        input_chars=len(text)
                    )
                )
                
                raise
            
            if not embeddings or embeddings[0] is None:
                logger.error(f"Failed to generate embedding for text (length: {len(text)})")
                return None
            
            embedding_vector = embeddings[0]
            
            result = EmbeddingResult(
                embedding=embedding_vector,
                model_name=self.model_name,
                dimensions=len(embedding_vector),
                token_count=len(text.split())  # Rough token estimate
            )
            
            # Cache the result
            self._embedding_cache[cache_key] = result
            
            logger.info(f"Generated embedding with {result.dimensions} dimensions")
            return result
            
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            return None
    
    async def embed_problem_statement(
        self, 
        problem: ProblemStatementCreate
    ) -> Optional[EmbeddingResult]:
        """
        Generate embedding for a problem statement.
        
        Args:
            problem: Problem statement data
            
        Returns:
            Embedding result or None if failed
        """
        try:
            text = self._prepare_problem_text(problem)
            logger.debug(f"Prepared problem text for embedding: {text[:200]}...")
            
            return await self.generate_embedding(text)
            
        except Exception as e:
            logger.error(f"Error embedding problem statement: {str(e)}")
            return None
    
    async def embed_problem_response(
        self, 
        problem: ProblemStatementResponse
    ) -> Optional[EmbeddingResult]:
        """
        Generate embedding for a problem statement response.
        
        Args:
            problem: Problem statement response data
            
        Returns:
            Embedding result or None if failed
        """
        try:
            text = self._prepare_response_text(problem)
            logger.debug(f"Prepared problem response text for embedding: {text[:200]}...")
            
            return await self.generate_embedding(text)
            
        except Exception as e:
            logger.error(f"Error embedding problem response: {str(e)}")
            return None
    
    async def embed_search_query(self, query: str) -> Optional[EmbeddingResult]:
        """
        Generate embedding for a search query.
        
        Args:
            query: Search query text
            
        Returns:
            Embedding result or None if failed
        """
        try:
            # Enhance the query with context for better matching
            enhanced_query = f"Problem statement search: {query}"
            
            return await self.generate_embedding(enhanced_query)
            
        except Exception as e:
            logger.error(f"Error embedding search query: {str(e)}")
            return None
    
    def calculate_similarity(
        self, 
        embedding1: List[float], 
        embedding2: List[float]
    ) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Similarity score between 0 and 1
        """
        try:
            if len(embedding1) != len(embedding2):
                logger.error(f"Embedding dimension mismatch: {len(embedding1)} vs {len(embedding2)}")
                return 0.0
            
            # Calculate cosine similarity
            dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
            magnitude1 = sum(a * a for a in embedding1) ** 0.5
            magnitude2 = sum(b * b for b in embedding2) ** 0.5
            
            if magnitude1 == 0 or magnitude2 == 0:
                return 0.0
            
            similarity = dot_product / (magnitude1 * magnitude2)
            
            # Convert to 0-1 range (cosine similarity is -1 to 1)
            normalized_similarity = (similarity + 1) / 2
            
            return max(0.0, min(1.0, normalized_similarity))
            
        except Exception as e:
            logger.error(f"Error calculating similarity: {str(e)}")
            return 0.0
    
    async def batch_embed_problems(
        self, 
        problems: List[ProblemStatementCreate]
    ) -> List[Optional[EmbeddingResult]]:
        """
        Generate embeddings for multiple problem statements in batch.
        
        Args:
            problems: List of problem statements
            
        Returns:
            List of embedding results (same order as input)
        """
        try:
            logger.info(f"Generating embeddings for {len(problems)} problems")
            
            # Process embeddings concurrently
            tasks = [self.embed_problem_statement(problem) for problem in problems]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle exceptions in results
            embeddings = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Error embedding problem {i}: {str(result)}")
                    embeddings.append(None)
                else:
                    embeddings.append(result)
            
            successful_embeddings = sum(1 for e in embeddings if e is not None)
            logger.info(f"Successfully generated {successful_embeddings}/{len(problems)} embeddings")
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Error in batch embedding: {str(e)}")
            return [None] * len(problems)
    
    def clear_cache(self) -> None:
        """Clear the embedding cache."""
        self._embedding_cache.clear()
        logger.info("Embedding cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get embedding cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        return {
            "cache_size": len(self._embedding_cache),
            "model_name": self.model_name,
            "dimensions": self.dimensions
        }


# Global embedding service instance
_embedding_service = None

def get_embedding_service() -> EmbeddingService:
    """
    Get the global embedding service instance.
    
    Returns:
        EmbeddingService instance
    """
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
