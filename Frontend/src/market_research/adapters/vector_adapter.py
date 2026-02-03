"""
Vector Adapter for Data Analysis Agent

Provides vector operations following VMP service patterns.
"""

import logging
import numpy as np
from typing import List, Dict, Any, Optional
from src.vpm.adapters.vector_adapter import YubaVectorAdapter
from src.mint.api.services.ai.embedding_service import get_embedding_service

logger = logging.getLogger(__name__)


class AnalysisAgentVectorAdapter(YubaVectorAdapter):
    """
    Vector adapter for Data Analysis Agent operations.
    
    Inherits from VMP's YubaVectorAdapter to maintain consistency
    with existing VMP service patterns.
    """
    
    def __init__(self):
        """Initialize using the same pattern as VMP services"""
        super().__init__()
        self.embedding_service = get_embedding_service()
    
    async def get_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to generate embedding for
            
        Returns:
            Embedding vector as list of floats
        """
        try:
            embeddings = await self.embedding_service.generate_embeddings([text])
            return embeddings[0] if embeddings else []
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return []
    
    async def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score between 0 and 1
        """
        try:
            if not embedding1 or not embedding2:
                return 0.0
            
            # Convert to numpy arrays
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            # Calculate cosine similarity
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            return float(similarity)
            
        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            return 0.0
    
    async def store_research_chunks(
        self, 
        project_id: str, 
        chunks: List[Dict[str, Any]]
    ) -> bool:
        """
        Store research document chunks with embeddings using the EXACT same method as market research service.
        
        Args:
            project_id: The project ID (used as doc_id)
            chunks: List of chunks with content, embeddings, and metadata
            
        Returns:
            True if successful, False otherwise
        """
        try:
            from src.mint.api.services.storage.chunk_storage_service import store_chunks
            from src.mint.api.report.report_models import ReportChunkWithEmbedding
            
            # Format chunks using the EXACT Pydantic model that market research uses
            formatted_chunks = []
            for chunk in chunks:
                try:
                    # Create ReportChunkWithEmbedding object (same as market research service line 1974)
                    chunk_obj = ReportChunkWithEmbedding(
                        chunk_index=chunk.get('index', chunk.get('chunk_index', 0)),
                        content=chunk['content'],
                        embedding=chunk['embedding'],
                        metadata={
                            'project_id': project_id,
                            **chunk.get('metadata', {})
                        }
                    )
                    formatted_chunks.append(chunk_obj)
                except Exception as e:
                    logger.warning(f"Failed to format chunk {chunk.get('index', 0)}: {e}")
                    continue
            
            logger.info(f"Storing {len(formatted_chunks)} chunks for project {project_id}")
            
            # Store using the same service as market research (line 2025)
            success = await store_chunks(project_id, formatted_chunks)
            
            if success:
                logger.info(f"✅ Successfully stored {len(formatted_chunks)} chunks")
            else:
                logger.error(f"❌ Failed to store chunks")
            
            return success
            
        except Exception as e:
            logger.error(f"Error storing research chunks: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    async def search_relevant_chunks(
        self, 
        project_id: str, 
        query_embedding: List[float], 
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant research chunks using semantic similarity.
        
        Args:
            project_id: The project ID
            query_embedding: The query embedding vector
            top_k: Number of top results to return
            
        Returns:
            List of relevant chunks with similarity scores
        """
        try:
            # Use existing vector search with project-specific filtering
            results = await self.similarity_search(
                query_embedding=query_embedding,
                top_k=top_k,
                filter_metadata={'project_id': project_id, 'source_type': 'research_document'}
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching relevant chunks: {e}")
            return []
    
    async def search_research_chunks(
        self,
        project_id: str,
        query: str,
        source_type: Optional[str] = None,
        max_results: int = 10,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Search research chunks using text query with vector similarity.
        
        Args:
            project_id: The project ID
            query: Text query to search for
            source_type: Filter by source type ('pdf', 'csv', 'analysis_report', or None for all)
            max_results: Maximum number of results to return
            similarity_threshold: Minimum similarity score (0-1)
            
        Returns:
            List of relevant chunks with content and metadata
        """
        try:
            from src.mint.api.system.core.supabase_client import get_service_role_client
            
            # Generate embedding for the query
            query_embedding = await self.get_embedding(query)
            
            if not query_embedding:
                logger.error(f"Failed to generate embedding for query: {query}")
                return []
            
            logger.info(f"Generated embedding with {len(query_embedding)} dimensions")
            
            # Use Supabase RPC for vector similarity search
            supabase = get_service_role_client()
            
            # Build metadata filter
            metadata_filter = {"project_id": project_id}
            if source_type:
                metadata_filter["source_type"] = source_type
            
            # Perform vector similarity search using Supabase function
            result = supabase.client.rpc(
                'match_chunks',
                {
                    'query_embedding': query_embedding,
                    'match_threshold': similarity_threshold,
                    'match_count': max_results,
                    'filter_metadata': metadata_filter
                }
            ).execute()
            
            # Format results
            filtered_results = []
            for chunk in result.data or []:
                filtered_results.append({
                    'content': chunk.get('content', ''),
                    'similarity': chunk.get('similarity', 0),
                    'source_type': chunk.get('metadata', {}).get('source_type', 'unknown'),
                    'source_metadata': chunk.get('metadata', {}),
                    'chunk_index': chunk.get('metadata', {}).get('chunk_index', 0)
                })
            
            logger.info(f"Found {len(filtered_results)} chunks above threshold {similarity_threshold}")
            return filtered_results
            
        except Exception as e:
            logger.error(f"Error searching research chunks: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise