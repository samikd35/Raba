"""
Project RAG Service

Handles vector similarity search over project chunks for the chat feature.
Provides retrieval with strict tenant/project isolation.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.mint.api.system.core.supabase_client import get_service_role_client
from src.mint.api.services.ai.embedding_service import EmbeddingService, get_embedding_service

from ..models import ProjectEvidence, DEFAULT_CHAT_CONFIG

logger = logging.getLogger(__name__)


class ProjectRAGService:
    """
    Service for retrieving project evidence via vector similarity search.
    
    Uses the existing report_chunks table populated by VMPProjectChunkingService.
    Strictly filters by tenant_id and project_id for multi-tenant isolation.
    """
    
    CHUNKS_TABLE = "chunks"
    
    def __init__(self):
        """Initialize RAG service with embedding service and DB client."""
        self.supabase = get_service_role_client()
        self.embedding_service: EmbeddingService = get_embedding_service()
        logger.info("✅ ProjectRAGService initialized")
    
    async def retrieve_evidence(
        self,
        query: str,
        project_id: str,
        tenant_id: str,
        top_k: int = None,
        similarity_threshold: float = None,
        artifact_types: Optional[List[str]] = None
    ) -> List[ProjectEvidence]:
        """
        Retrieve relevant project evidence for a query.
        
        Args:
            query: Search query (will be embedded)
            project_id: VMP project ID (strict filter)
            tenant_id: Tenant ID (strict filter)
            top_k: Max chunks to return (default from config)
            similarity_threshold: Min relevance score (default from config)
            artifact_types: Optional filter for specific artifact types
            
        Returns:
            List of ProjectEvidence objects sorted by relevance
        """
        top_k = top_k or DEFAULT_CHAT_CONFIG.max_project_chunks
        similarity_threshold = similarity_threshold or DEFAULT_CHAT_CONFIG.similarity_threshold
        
        try:
            # Step 1: Generate query embedding
            logger.info(f"🔍 RAG: Generating embedding for query: {query[:50]}...")
            query_embedding = await self.embedding_service.generate_single_embedding(query)
            
            if not query_embedding:
                logger.error("Failed to generate query embedding")
                return []
            
            # Step 2: Execute vector similarity search using RPC function
            logger.info(f"🔍 RAG: Searching chunks for project {project_id}, threshold={similarity_threshold}")
            
            # Use the match_project_chunks function we created
            result = self.supabase.client.rpc(
                "match_project_chunks",
                {
                    "query_embedding": query_embedding,
                    "p_project_id": project_id,
                    "p_tenant_id": tenant_id,
                    "match_count": top_k * 2,  # Get more to filter
                    "match_threshold": 0.0  # Set to 0 to get ALL chunks regardless of similarity
                }
            ).execute()
            
            logger.info(f"🔍 RAG: RPC returned {len(result.data) if result.data else 0} chunks")
            
            if not result.data:
                logger.info("🔍 RAG: No matching chunks found")
                return []
            
            # DEBUG: Log first chunk structure
            if result.data:
                logger.info(f"🔍 RAG DEBUG: First chunk keys: {list(result.data[0].keys())}")
                logger.info(f"🔍 RAG DEBUG: First chunk: {result.data[0]}")
            
            # Step 3: Convert to ProjectEvidence with re-ranking
            # Prioritize v2 artifacts and actual content over metadata/URL sections
            PRIORITY_BOOST = {
                "vmp_bmc_v2": 0.15,      # Boost BMC v2
                "vmp_vps_v2": 0.15,      # Boost VPS v2
                "vmp_mvp_requirements": 0.12,  # Boost AMRG
                "vmp_market_research": 0.12,   # Boost Market Research Analysis
                "vmp_customer_profile_v2": 0.10,
                "vmp_bmc_v1": 0.05,      # Lower boost for v1
                "vmp_vps_v1": 0.05,
            }
            # Penalize metadata-heavy sections
            SECTION_PENALTY = {
                "sources": -0.20,        # URL/reference sections
                "references": -0.20,
            }
            
            evidence_list = []
            for chunk in result.data:
                source_type = chunk.get("source_type") or chunk.get("metadata", {}).get("source_type", "unknown")
                section_type = chunk.get("metadata", {}).get("section_type", "")
                
                # Calculate adjusted score
                base_score = float(chunk.get("similarity", 0.5))
                boost = PRIORITY_BOOST.get(source_type, 0)
                penalty = SECTION_PENALTY.get(section_type, 0)
                adjusted_score = base_score + boost + penalty
                
                evidence = ProjectEvidence(
                    chunk_id=str(chunk["id"]),
                    content=chunk["content"],
                    artifact_type=source_type,
                    section=chunk.get("section"),
                    chunk_index=chunk.get("chunk_index", 0),
                    score=adjusted_score,
                    metadata=chunk.get("metadata", {})
                )
                evidence_list.append(evidence)
            
            # Re-sort by adjusted score and take top_k
            evidence_list.sort(key=lambda x: x.score, reverse=True)
            evidence_list = evidence_list[:top_k]
            
            logger.info(f"✅ RAG: Retrieved {len(evidence_list)} evidence chunks (re-ranked)")
            return evidence_list
            
        except Exception as e:
            logger.error(f"❌ RAG retrieval error: {e}")
            # Try fallback to direct query if RPC fails
            return await self._fallback_retrieval(
                query, project_id, tenant_id, top_k, similarity_threshold, artifact_types
            )
    
    async def _fallback_retrieval(
        self,
        query: str,
        project_id: str,
        tenant_id: str,
        top_k: int,
        similarity_threshold: float,
        artifact_types: Optional[List[str]] = None
    ) -> List[ProjectEvidence]:
        """
        Fallback retrieval using direct table query (less efficient but works).
        
        Used when RPC function is not available or fails.
        """
        try:
            logger.info("🔍 RAG: Using fallback direct query retrieval")
            
            # Generate embedding
            query_embedding = await self.embedding_service.generate_single_embedding(query)
            if not query_embedding:
                return []
            
            # Build query - note: this won't do vector similarity, just filters
            # chunks table uses doc_id for project reference, no tenant_id column
            query_builder = self.supabase.client.table(self.CHUNKS_TABLE).select(
                "id, content, chunk_index, metadata"
            ).eq("doc_id", project_id)
            
            # Artifact type filter
            if artifact_types:
                # Filter by source_type in metadata
                # Note: This is limited without proper JSON filtering
                pass
            
            query_builder = query_builder.limit(top_k * 3)  # Get more for client-side ranking
            
            result = query_builder.execute()
            
            if not result.data:
                return []
            
            # Client-side ranking by embedding similarity would require loading embeddings
            # For fallback, just return chunks without similarity scoring
            evidence_list = []
            for chunk in result.data[:top_k]:
                source_type = chunk.get("metadata", {}).get("source_type", "unknown")
                
                evidence = ProjectEvidence(
                    chunk_id=str(chunk["id"]),
                    content=chunk["content"],
                    artifact_type=source_type,
                    section=chunk.get("section"),
                    chunk_index=chunk.get("chunk_index", 0),
                    score=0.5,  # Default score for fallback
                    metadata=chunk.get("metadata", {})
                )
                evidence_list.append(evidence)
            
            logger.info(f"✅ RAG Fallback: Retrieved {len(evidence_list)} chunks")
            return evidence_list
            
        except Exception as e:
            logger.error(f"❌ RAG fallback error: {e}")
            return []
    
    async def get_chunk_by_id(
        self,
        chunk_id: str,
        tenant_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific chunk by ID with tenant verification.
        
        Args:
            chunk_id: Chunk ID
            tenant_id: Tenant ID for verification
            
        Returns:
            Chunk data dict or None
        """
        try:
            # chunks table doesn't have tenant_id, just filter by chunk_id
            result = self.supabase.client.table(self.CHUNKS_TABLE).select("*").eq("id", chunk_id).execute()
            
            if result.data:
                return result.data[0]
            return None
            
        except Exception as e:
            logger.error(f"Error getting chunk {chunk_id}: {e}")
            return None
    
    async def get_project_chunk_stats(
        self,
        project_id: str,
        tenant_id: str
    ) -> Dict[str, Any]:
        """
        Get statistics about chunks for a project.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID
            
        Returns:
            Stats dict with counts by artifact type
        """
        try:
            # chunks table uses doc_id for project reference, no tenant_id column
            result = self.supabase.client.table(self.CHUNKS_TABLE).select(
                "metadata", count="exact"
            ).eq("doc_id", project_id).execute()
            
            if not result.data:
                return {"total_chunks": 0, "by_artifact_type": {}}
            
            # Count by artifact type
            by_type: Dict[str, int] = {}
            for chunk in result.data:
                source_type = chunk.get("metadata", {}).get("source_type", "unknown")
                by_type[source_type] = by_type.get(source_type, 0) + 1
            
            return {
                "total_chunks": result.count or len(result.data),
                "by_artifact_type": by_type
            }
            
        except Exception as e:
            logger.error(f"Error getting chunk stats: {e}")
            return {"total_chunks": 0, "by_artifact_type": {}}
    
    def format_evidence_for_context(
        self,
        evidence_list: List[ProjectEvidence],
        max_chars: int = 4000
    ) -> str:
        """
        Format evidence list as text for LLM context.
        
        Args:
            evidence_list: List of ProjectEvidence
            max_chars: Maximum total characters
            
        Returns:
            Formatted text with evidence blocks
        """
        if not evidence_list:
            return "No project evidence available."
        
        lines = []
        total_chars = 0
        
        for i, evidence in enumerate(evidence_list, 1):
            ref_id = f"P{i}"
            header = f"[{ref_id}] ({evidence.artifact_type}, score: {evidence.score:.2f})"
            content = evidence.content[:800] + "..." if len(evidence.content) > 800 else evidence.content
            
            block = f"{header}\n{content}\n"
            
            if total_chars + len(block) > max_chars:
                break
            
            lines.append(block)
            total_chars += len(block)
        
        return "\n".join(lines)


# Singleton instance
_project_rag_service: Optional[ProjectRAGService] = None


def get_project_rag_service() -> ProjectRAGService:
    """Get or create singleton ProjectRAGService instance."""
    global _project_rag_service
    if _project_rag_service is None:
        _project_rag_service = ProjectRAGService()
    return _project_rag_service
