"""
Passage Embedder Node

Node 5 in the Problem Generator agent graph.
Generates embeddings for extracted passages using OpenAI text-embedding-3-small.
"""

import logging
import asyncio
from typing import Dict, Any, List
from datetime import datetime

from langsmith.run_helpers import traceable
from src.mint.agents.agent_config import get_agent_config
from src.pgen.services.embedding_service import EmbeddingService

from ..graph_state import ProblemGraphState

logger = logging.getLogger(__name__)


@traceable(name="passage_embedder_node")
async def passage_embedder_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Node 5: Passage Embedder
    
    Generates embeddings for extracted passages using OpenAI text-embedding-3-small.
    
    Args:
        state: Current workflow state with extracted passages
        
    Returns:
        Updated workflow state with embedded passages
    """
    logger.info("Starting passage embedding")
    start_time = datetime.now()
    
    try:
        # Update status
        state["current_node"] = "passage_embedder"
        
        # Get configuration
        agent_config = get_agent_config(state, "problem_generator")
        embedding_config = agent_config.get("embedding", {})
        
        # Get extracted passages
        passages = state.get("passages", [])
        if not passages:
            logger.warning("No passages found for embedding")
            state["embedded_passages"] = []
            return state
        
        logger.info(f"Generating embeddings for {len(passages)} passages")
        
        # =============================================
        # PREPARE TEXTS FOR EMBEDDING
        # =============================================
        
        # Prepare texts and metadata
        embedding_items = []
        
        for i, passage in enumerate(passages):
            text = passage.get("text", "").strip()
            if not text:
                continue
            
            # Create embedding text (combine text with context for better embeddings)
            context = passage.get("context", "")
            location = passage.get("location", "")
            industry = passage.get("industry", "")
            
            # Build enriched text for embedding
            embedding_text = text
            
            if context:
                embedding_text += f" Context: {context}"
            if location:
                embedding_text += f" Location: {location}"
            if industry:
                embedding_text += f" Industry: {industry}"
            
            embedding_items.append({
                "index": i,
                "text": embedding_text,
                "original_passage": passage
            })
        
        if not embedding_items:
            logger.warning("No valid texts found for embedding")
            state["embedded_passages"] = []
            return state
        
        logger.info(f"Prepared {len(embedding_items)} texts for embedding")
        
        # =============================================
        # GENERATE EMBEDDINGS
        # =============================================
        
        # Extract monitoring context from state
        monitoring_user_id = state.get("user_id")
        monitoring_tenant_id = state.get("tenant_id")
        monitoring_project_id = state.get("project_id")
        
        async def generate_all_embeddings():
            """Generate embeddings for all texts using EmbeddingService."""
            
            # Initialize embedding service with monitoring context
            embedding_service = EmbeddingService(
                user_id=monitoring_user_id,
                tenant_id=monitoring_tenant_id,
                project_id=monitoring_project_id
            )
            
            # Process texts individually for now (can be optimized later)
            all_embeddings = []
            
            for idx, item in enumerate(embedding_items):
                try:
                    logger.debug(f"Processing embedding {idx + 1}/{len(embedding_items)}")
                    
                    # Generate embedding for the text
                    embedding_result = await embedding_service.generate_embedding(item["text"])
                    
                    if embedding_result:
                        # Create embedded passage with metadata
                        embedded_passage = {
                            **item,  # Include all original passage data
                            "embedding": embedding_result.embedding,
                            "embedding_model": embedding_result.model_name,
                            "embedding_dimensions": embedding_result.dimensions,
                            "embedded_at": datetime.now().isoformat()
                        }
                        all_embeddings.append(embedded_passage)
                    else:
                        logger.warning(f"Failed to generate embedding for passage {idx + 1}")
                        all_embeddings.append(None)
                    
                    # Small delay to avoid rate limits
                    if idx < len(embedding_items) - 1:
                        await asyncio.sleep(0.05)
                        
                except Exception as e:
                    logger.error(f"Embedding generation failed for passage {idx + 1}: {str(e)}")
                    all_embeddings.append(None)
            
            return all_embeddings
        
        # Generate embeddings
        embeddings = await generate_all_embeddings()
        
        # =============================================
        # PROCESS EMBEDDING RESULTS
        # =============================================
        
        embedded_passages = []
        embedding_stats = {
            "total_passages": len(passages),
            "successful_embeddings": 0,
            "failed_embeddings": 0,
            "embedding_dimension": 0
        }
        
        for embedding in embeddings:
            if embedding is None:
                embedding_stats["failed_embeddings"] += 1
                continue
            
            # Validate embedding
            if not embedding.get("embedding") or not isinstance(embedding["embedding"], list):
                logger.warning(f"Invalid embedding for passage")
                embedding_stats["failed_embeddings"] += 1
                continue
            
            # Store embedding dimension (from first successful embedding)
            if embedding_stats["embedding_dimension"] == 0:
                embedding_stats["embedding_dimension"] = embedding["embedding_dimensions"]
            
            embedded_passages.append(embedding)
            embedding_stats["successful_embeddings"] += 1
        
        # =============================================
        # STORE RESULTS
        # =============================================
        
        state["embedded_passages"] = embedded_passages
        state["embedding_stats"] = embedding_stats
        
        # Add processing metrics
        total_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        embedding_metrics = {
            "passages_processed": len(passages),
            "embeddings_generated": embedding_stats["successful_embeddings"],
            "success_rate": embedding_stats["successful_embeddings"] / max(len(passages), 1),
            "embedding_dimension": embedding_stats["embedding_dimension"],
            "processing_time_ms": total_time,
            "avg_time_per_embedding": total_time / max(embedding_stats["successful_embeddings"], 1)
        }
        
        if "processing_metrics" not in state:
            state["processing_metrics"] = {}
        state["processing_metrics"]["passage_embedder"] = embedding_metrics
        
        logger.info(f"Passage embedding completed successfully")
        logger.info(f"Generated {embedding_stats['successful_embeddings']}/{len(passages)} embeddings")
        logger.info(f"Embedding dimension: {embedding_stats['embedding_dimension']}")
        
        return state
        
    except Exception as e:
        error_msg = f"Passage embedding failed: {str(e)}"
        logger.error(error_msg)
        state["error"] = error_msg
        state["status"] = "failed"
        return state
