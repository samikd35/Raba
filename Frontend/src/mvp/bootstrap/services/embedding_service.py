"""
Bootstrap Embedding Service

Handles chunking, embedding, and vector storage for bootstrap context generation.
Uses existing Yuba vector infrastructure.
"""

import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Chunking configuration
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 200


class BootstrapEmbeddingService:
    """
    Service for chunking, embedding, and storing bootstrap content.
    
    Follows patterns from src/vpm/adapters/vector_adapter.py and
    src/mint/api/services/ai/vector_search_service.py
    """
    
    def __init__(self):
        """Initialize embedding service with Yuba's existing infrastructure."""
        self._init_services()
        logger.info("Bootstrap Embedding Service initialized")
    
    def _init_services(self):
        """Initialize required services."""
        try:
            from src.mint.api.services.ai.embedding_service import get_embedding_service
            self.embedding_service = get_embedding_service()
        except ImportError:
            logger.warning("Embedding service not available, using fallback")
            self.embedding_service = None
        
        try:
            from src.mint.api.system.core.supabase_client import get_service_role_client
            self.supabase = get_service_role_client()
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            self.supabase = None
    
    def chunk_content(
        self,
        content: str,
        source_type: str,
        metadata: Optional[Dict[str, Any]] = None,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP
    ) -> List[Dict[str, Any]]:
        """
        Split content into chunks for embedding.
        
        Args:
            content: Text content to chunk
            source_type: Type of source (e.g., 'bootstrap_idea_text', 'bootstrap_pdf_extract')
            metadata: Additional metadata to attach to chunks
            chunk_size: Maximum characters per chunk
            chunk_overlap: Overlap between chunks
            
        Returns:
            List of chunk dictionaries
        """
        if not content or not content.strip():
            return []
        
        chunks = []
        text = content.strip()
        
        # Simple sentence-aware chunking
        sentences = self._split_into_sentences(text)
        current_chunk = ""
        chunk_index = 0
        
        for sentence in sentences:
            # If adding this sentence exceeds chunk_size, save current chunk
            if len(current_chunk) + len(sentence) > chunk_size and current_chunk:
                chunks.append(self._create_chunk(
                    content=current_chunk.strip(),
                    source_type=source_type,
                    chunk_index=chunk_index,
                    metadata=metadata
                ))
                chunk_index += 1
                
                # Start new chunk with overlap
                overlap_text = current_chunk[-chunk_overlap:] if len(current_chunk) > chunk_overlap else current_chunk
                current_chunk = overlap_text + " " + sentence
            else:
                current_chunk += " " + sentence if current_chunk else sentence
        
        # Don't forget the last chunk
        if current_chunk.strip():
            chunks.append(self._create_chunk(
                content=current_chunk.strip(),
                source_type=source_type,
                chunk_index=chunk_index,
                metadata=metadata
            ))
        
        logger.info(f"Created {len(chunks)} chunks from {len(text)} chars of {source_type}")
        return chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        import re
        # Simple sentence splitting
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _create_chunk(
        self,
        content: str,
        source_type: str,
        chunk_index: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a chunk dictionary."""
        chunk_metadata = {
            "source_type": source_type,
            "chunk_index": chunk_index,
            "char_count": len(content),
            "created_at": datetime.utcnow().isoformat()
        }
        
        if metadata:
            chunk_metadata.update(metadata)
        
        return {
            "id": str(uuid.uuid4()),
            "content": content,
            "metadata": chunk_metadata
        }
    
    async def embed_chunks(
        self,
        chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate embeddings for chunks.
        
        Args:
            chunks: List of chunk dictionaries
            
        Returns:
            Chunks with 'embedding' field added
        """
        if not chunks:
            return []
        
        if not self.embedding_service:
            logger.warning("Embedding service not available, skipping embeddings")
            return chunks
        
        try:
            # Extract content for embedding
            contents = [chunk["content"] for chunk in chunks]
            
            # Generate embeddings
            embeddings = await self.embedding_service.generate_embeddings(contents)
            
            # Add embeddings to chunks
            for i, chunk in enumerate(chunks):
                if i < len(embeddings) and embeddings[i]:
                    chunk["embedding"] = embeddings[i]
                else:
                    chunk["embedding"] = None
            
            embedded_count = sum(1 for c in chunks if c.get("embedding"))
            logger.info(f"✅ Generated embeddings for {embedded_count}/{len(chunks)} chunks")
            return chunks
            
        except Exception as e:
            logger.error(f"❌ Error generating embeddings: {e}")
            # Return chunks without embeddings rather than failing
            return chunks
    
    async def store_chunks(
        self,
        project_id: str,
        tenant_id: str,
        chunks: List[Dict[str, Any]],
        user_id: Optional[str] = None
    ) -> bool:
        """
        Store chunks in the database with embeddings.
        
        Args:
            project_id: Project ID to associate chunks with
            tenant_id: Tenant ID for security
            chunks: List of chunk dictionaries with embeddings
            user_id: User ID for created_by field
            
        Returns:
            True if successful
        """
        if not chunks:
            return True
        
        if not self.supabase:
            logger.error("Supabase client not available")
            return False
        
        try:
            # First, create a document entry for this project's bootstrap content
            doc_id = str(uuid.uuid4())
            doc_data = {
                "id": doc_id,
                "tenant_id": tenant_id,
                "title": f"Bootstrap Content - {project_id}",
                "source_type": "vpc_artifact",  # Use allowed source_type (bootstrap content feeds VPS/BMC)
                "document_type": "bootstrap_intake",  # Store actual type in document_type field
                "metadata": {
                    "project_id": project_id,
                    "chunk_count": len(chunks),
                    "bootstrap": True
                },
                "created_at": datetime.utcnow().isoformat(),
                "created_by": user_id  # Required NOT NULL field
            }
            
            self.supabase.client.table("documents").insert(doc_data).execute()
            
            # Prepare chunks for insertion
            chunk_records = []
            for i, chunk in enumerate(chunks):
                record = {
                    "id": chunk["id"],
                    "doc_id": doc_id,
                    "content": chunk["content"],
                    "chunk_index": i,  # Use sequential index to avoid unique constraint violation
                    "metadata": chunk["metadata"],
                    "created_at": datetime.utcnow().isoformat()
                }
                
                # Add embedding if available (as JSON string for storage)
                if chunk.get("embedding"):
                    import json
                    record["embedding"] = json.dumps(chunk["embedding"])
                
                chunk_records.append(record)
            
            # Insert chunks in batches
            batch_size = 50
            for i in range(0, len(chunk_records), batch_size):
                batch = chunk_records[i:i + batch_size]
                self.supabase.client.table("chunks").insert(batch).execute()
            
            logger.info(f"✅ Stored {len(chunks)} chunks for project {project_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error storing chunks: {e}")
            return False
    
    async def retrieve(
        self,
        project_id: str,
        tenant_id: str,
        query: str,
        top_k: int = 10,
        source_filters: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant chunks using semantic search.
        
        Args:
            project_id: Project ID
            tenant_id: Tenant ID
            query: Search query
            top_k: Number of results to return
            source_filters: Optional list of source_type values to filter by
            
        Returns:
            List of relevant chunks with similarity scores
        """
        if not self.embedding_service or not self.supabase:
            logger.warning("Services not available for retrieval")
            return []
        
        try:
            # Generate query embedding
            query_embeddings = await self.embedding_service.generate_embeddings([query])
            if not query_embeddings or not query_embeddings[0]:
                logger.warning("Failed to generate query embedding")
                return []
            
            query_embedding = query_embeddings[0]
            
            # Get document IDs for this project
            docs_response = self.supabase.client.table("documents").select(
                "id"
            ).eq("metadata->>project_id", project_id).execute()
            
            if not docs_response.data:
                logger.info(f"No documents found for project {project_id}")
                return []
            
            doc_ids = [doc["id"] for doc in docs_response.data]
            
            # Get all chunks for these documents
            chunks_response = self.supabase.client.table("chunks").select(
                "id, content, metadata, embedding"
            ).in_("doc_id", doc_ids).execute()
            
            if not chunks_response.data:
                return []
            
            # Calculate similarity scores
            import numpy as np
            import json
            
            scored_chunks = []
            for chunk in chunks_response.data:
                # Apply source filter if specified
                if source_filters:
                    chunk_source = chunk.get("metadata", {}).get("source_type", "")
                    if chunk_source not in source_filters:
                        continue
                
                # Parse embedding
                raw_embedding = chunk.get("embedding")
                if not raw_embedding:
                    continue
                
                if isinstance(raw_embedding, str):
                    try:
                        chunk_embedding = json.loads(raw_embedding)
                    except:
                        continue
                else:
                    chunk_embedding = raw_embedding
                
                # Calculate cosine similarity
                try:
                    similarity = np.dot(query_embedding, chunk_embedding) / (
                        np.linalg.norm(query_embedding) * np.linalg.norm(chunk_embedding)
                    )
                    
                    scored_chunks.append({
                        "id": chunk["id"],
                        "content": chunk["content"],
                        "metadata": chunk.get("metadata", {}),
                        "similarity": float(similarity)
                    })
                except Exception as e:
                    logger.warning(f"Error calculating similarity: {e}")
                    continue
            
            # Sort by similarity and return top_k
            scored_chunks.sort(key=lambda x: x["similarity"], reverse=True)
            results = scored_chunks[:top_k]
            
            logger.info(f"Retrieved {len(results)} chunks for query")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error retrieving chunks: {e}")
            return []
    
    async def process_bootstrap_input(
        self,
        project_id: str,
        tenant_id: str,
        idea_text: Optional[str] = None,
        pdf_extracts: Optional[List[Dict[str, Any]]] = None,
        qa_answers: Optional[List[Dict[str, Any]]] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process all bootstrap input: chunk, embed, and store.
        
        Args:
            project_id: Project ID
            tenant_id: Tenant ID
            idea_text: Optional raw idea text
            pdf_extracts: Optional list of PDF extraction results
            qa_answers: Optional list of Q&A answers
            user_id: User ID for created_by field
            
        Returns:
            Processing result with chunk count
        """
        all_chunks = []
        
        # Process idea text
        if idea_text:
            chunks = self.chunk_content(
                content=idea_text,
                source_type="bootstrap_idea_text",
                metadata={"project_id": project_id}
            )
            all_chunks.extend(chunks)
        
        # Process PDF extracts
        if pdf_extracts:
            for i, extract in enumerate(pdf_extracts):
                if extract.get("success") and extract.get("text"):
                    chunks = self.chunk_content(
                        content=extract["text"],
                        source_type="bootstrap_pdf_extract",
                        metadata={
                            "project_id": project_id,
                            "file_key": extract.get("file_key", f"file_{i}"),
                            "extractor": extract.get("extractor", "unknown")
                        }
                    )
                    all_chunks.extend(chunks)
        
        # Process Q&A answers
        if qa_answers:
            for answer in qa_answers:
                # Create a chunk from each answer with question context
                question_id = answer.get("question_id", "unknown")
                answer_text = answer.get("answer", "")
                
                if answer_text:
                    chunks = self.chunk_content(
                        content=answer_text,
                        source_type="bootstrap_qa_answer",
                        metadata={
                            "project_id": project_id,
                            "question_id": question_id
                        }
                    )
                    all_chunks.extend(chunks)
        
        if not all_chunks:
            return {"success": True, "chunk_count": 0, "message": "No content to process"}
        
        # Generate embeddings
        embedded_chunks = await self.embed_chunks(all_chunks)
        
        # Store chunks
        stored = await self.store_chunks(project_id, tenant_id, embedded_chunks, user_id)
        
        return {
            "success": stored,
            "chunk_count": len(embedded_chunks),
            "message": f"Processed {len(embedded_chunks)} chunks"
        }


def get_bootstrap_embedding_service() -> BootstrapEmbeddingService:
    """Factory function for BootstrapEmbeddingService."""
    return BootstrapEmbeddingService()
