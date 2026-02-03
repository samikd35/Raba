"""
Solution Critique Chat Service

Provides conversational interface for querying solution critique reports
using RAG (Retrieval-Augmented Generation).

Features:
- Vector similarity search for relevant critique chunks
- Conversation memory for follow-up questions
- Grounded responses using only critique data
- Citation tracking for transparency
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.mvp.adapters.database_adapter import MVPDatabaseAdapter
from src.market_research.utils.ai_service_wrapper import get_ai_service_wrapper

logger = logging.getLogger(__name__)


class SolutionCritiqueChatService:
    """
    Chat service for solution critique with RAG and conversation memory.
    
    Retrieves context from solution critique report chunks and generates
    grounded responses using LLM.
    """
    
    def __init__(self):
        """Initialize chat service with required adapters."""
        self.db_adapter = MVPDatabaseAdapter(use_service_role=True)
        self.ai_service = get_ai_service_wrapper()
        
        # Chat configuration
        self.max_context_tokens = 4000  # Leave room for response
        self.max_history_messages = 10  # Last 10 messages
        self.similarity_threshold = 0.7
    
    async def chat(
        self,
        project_id: str,
        tenant_id: str,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Process a chat message and generate a grounded response.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID
            user_message: User's question/message
            conversation_history: Previous conversation messages
            
        Returns:
            Response with answer, sources, and updated conversation
        """
        try:
            logger.info(f"💬 CRITIQUE CHAT: Processing message for project {project_id}")
            logger.info(f"💬 CRITIQUE CHAT: User message: {user_message[:100]}...")
            
            # Initialize conversation history if not provided
            if conversation_history is None:
                conversation_history = []
            
            # Retrieve relevant critique chunks using RAG
            context = await self._retrieve_context(
                project_id=project_id,
                tenant_id=tenant_id,
                query=user_message,
                conversation_history=conversation_history
            )
            
            if not context["has_context"]:
                return {
                    "success": False,
                    "error": "no_context",
                    "message": "No solution critique found for this project. Please generate a critique first."
                }
            
            # Generate response using LLM with retrieved context
            response = await self._generate_response(
                user_message=user_message,
                context=context,
                conversation_history=conversation_history
            )
            
            # Update conversation history
            updated_history = self._update_conversation_history(
                conversation_history=conversation_history,
                user_message=user_message,
                assistant_response=response["answer"]
            )
            
            logger.info(f"✅ CRITIQUE CHAT: Generated response with {len(response['sources'])} sources")
            
            return {
                "success": True,
                "answer": response["answer"],
                "sources": response["sources"],
                "context_used": {
                    "critique_chunks": len(context.get("critique_chunks", []))
                },
                "conversation_history": updated_history,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ CRITIQUE CHAT: Error processing message: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": "chat_error",
                "message": f"Failed to process chat message: {str(e)}"
            }
    
    async def _retrieve_context(
        self,
        project_id: str,
        tenant_id: str,
        query: str,
        conversation_history: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Retrieve relevant critique chunks using vector similarity search.
        
        Returns context from solution critique report chunks.
        """
        try:
            logger.info(f"🔍 CRITIQUE CHAT CONTEXT: Starting retrieval for project {project_id}")
            
            # Get critique report chunks using vector search
            critique_chunks = await self._retrieve_critique_chunks(
                project_id, tenant_id, query, max_chunks=15
            )
            logger.info(f"✅ CRITIQUE CHAT CONTEXT: Retrieved {len(critique_chunks)} critique chunks")
            
            context = {
                "critique_chunks": critique_chunks,
                "has_context": len(critique_chunks) > 0
            }
            
            logger.info(f"✅ CRITIQUE CHAT CONTEXT: Context retrieval complete. Total chunks: {len(critique_chunks)}")
            
            return context
            
        except Exception as e:
            logger.error(f"❌ CRITIQUE CHAT CONTEXT: Error retrieving context: {e}")
            return {
                "critique_chunks": [],
                "has_context": False
            }
    
    async def _retrieve_critique_chunks(
        self,
        project_id: str,
        tenant_id: str,
        query: str,
        max_chunks: int = 15
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant chunks from solution critique using vector search."""
        try:
            from src.mint.api.services.storage.chunk_storage_service import get_chunk_storage_service
            from src.mint.api.services.ai.embedding_service import EmbeddingService
            
            chunk_service = get_chunk_storage_service()
            
            # Load all chunks from chunks table
            all_chunks = await chunk_service.get_chunks_by_report_id(project_id)
            
            if not all_chunks:
                logger.warning(f"No chunks found for project {project_id}")
                return []
            
            # Filter for solution_critique chunks only
            critique_chunks = [
                chunk for chunk in all_chunks
                if chunk.get('metadata', {}).get('source_type') == 'solution_critique'
            ]
            
            logger.info(f"🔍 CRITIQUE FILTER: Found {len(all_chunks)} total chunks, {len(critique_chunks)} solution_critique chunks")
            
            if not critique_chunks:
                logger.warning(f"No solution_critique chunks found for project {project_id}")
                return []
            
            # Generate embedding for the query
            embedding_service = EmbeddingService()
            query_embeddings = await embedding_service.generate_embeddings([query])
            query_embedding = query_embeddings[0] if query_embeddings else None
            
            if not query_embedding:
                logger.error("Failed to generate query embedding")
                return []
            
            # Calculate similarity scores and rank chunks
            import numpy as np
            scored_chunks = []
            
            for chunk_data in critique_chunks:
                # Get chunk embedding
                raw_embedding = chunk_data.get('embedding')
                if raw_embedding and isinstance(raw_embedding, str):
                    try:
                        import json
                        chunk_embedding = json.loads(raw_embedding)
                    except:
                        continue
                elif isinstance(raw_embedding, list):
                    chunk_embedding = raw_embedding
                else:
                    continue
                
                # Calculate cosine similarity
                try:
                    similarity = np.dot(query_embedding, chunk_embedding) / (
                        np.linalg.norm(query_embedding) * np.linalg.norm(chunk_embedding)
                    )
                    
                    scored_chunks.append({
                        'content': chunk_data.get('content', ''),
                        'similarity': float(similarity),
                        'metadata': chunk_data.get('metadata', {})
                    })
                except Exception as e:
                    logger.warning(f"Failed to calculate similarity: {e}")
                    continue
            
            # Sort by similarity and return top chunks
            scored_chunks.sort(key=lambda x: x['similarity'], reverse=True)
            top_chunks = scored_chunks[:max_chunks]
            
            # DEBUG: Log what we're returning
            logger.info(f"🔍 CRITIQUE CHUNKS: Returning {len(top_chunks)} chunks")
            if top_chunks:
                logger.info(f"🔍 TOP CHUNK SIMILARITY: {top_chunks[0]['similarity']:.4f}")
                logger.info(f"🔍 TOP CHUNK SECTION: {top_chunks[0].get('metadata', {}).get('section')}")
                logger.info(f"🔍 TOP CHUNK PREVIEW: {top_chunks[0].get('content', '')[:200]}...")
            
            return top_chunks
            
        except Exception as e:
            logger.error(f"❌ CRITIQUE CHAT: Error retrieving critique chunks: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []
    
    async def _generate_response(
        self,
        user_message: str,
        context: Dict[str, Any],
        conversation_history: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Generate a grounded response using LLM with retrieved context."""
        try:
            # Build context string from critique chunks
            context_parts = []
            sources = []
            
            # Add critique context
            if context["critique_chunks"]:
                logger.info(f"🔍 CONTEXT BUILD: Building context from {len(context['critique_chunks'])} critique chunks")
                
                critique_context = "\n\n".join([
                    f"[Solution Critique - {chunk.get('metadata', {}).get('section', 'Unknown Section')}]\n{chunk['content']}"
                    for chunk in context["critique_chunks"][:15]  # Top 15
                ])
                context_parts.append(f"=== SOLUTION CRITIQUE REPORT ===\n{critique_context}")
                
                logger.info(f"🔍 CONTEXT BUILD: Critique context length: {len(critique_context)} characters")
                
                # Track sources by section
                sections_used = {}
                for chunk in context["critique_chunks"][:15]:
                    metadata = chunk.get("metadata", {})
                    section = metadata.get("section", "unknown")
                    section_type = metadata.get("section_type", "unknown")
                    
                    if section_type not in sections_used:
                        sections_used[section_type] = 0
                    sections_used[section_type] += 1
                
                sources.append({
                    "type": "solution_critique",
                    "section_count": len(sections_used),
                    "chunk_count": len(context["critique_chunks"][:15]),
                    "includes": list(sections_used.keys())
                })
            
            # Combine all context
            full_context = "\n\n" + "="*80 + "\n\n".join(context_parts)
            
            logger.info(f"🔍 CONTEXT BUILD: Full context length: {len(full_context)} characters")
            logger.info(f"🔍 CONTEXT BUILD: Context preview (first 500 chars): {full_context[:500]}...")
            
            # Build conversation history string
            history_text = ""
            if conversation_history:
                recent_history = conversation_history[-self.max_history_messages:]
                history_text = "\n\n=== CONVERSATION HISTORY ===\n" + "\n\n".join([
                    f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}"
                    for msg in recent_history
                ])
            
            # Create system prompt
            system_prompt = """You are a startup advisor helping analyze a solution critique report.

Your role is to answer questions based STRICTLY on the solution critique data provided in the context.

CONTEXT SOURCES:
- Solution critique report with 5 dimensions:
  1. Market Viability
  2. Operational Feasibility
  3. Business Model
  4. Competitive Differentiation
  5. Technical Scalability
- Executive summary with overall assessment
- Prioritized actions and recommendations
- Source citations from web research, BMC, VPC, VPS

CRITICAL RULES:
1. ONLY use information from the solution critique report
2. If the answer is not in the critique, say "I don't have that information in the critique report."
3. Cite critique dimensions when relevant (e.g., "According to the market viability critique...")
4. Reference severity levels (high/medium/low) and specific issues
5. Consider the conversation history for follow-up questions
6. Be conversational but accurate

DO NOT:
- Make up critiques or issues not in the report
- Speculate beyond what's stated
- Use external knowledge
- Provide generic advice not grounded in the critique

When asked about:
- **Risks**: Cite high-severity critiques with evidence
- **Recommendations**: Use the prioritized actions from the report
- **Sources**: Reference the web research and project data cited
- **Viability**: Use the executive summary overall assessment"""

            # Create user prompt
            user_prompt = f"""{history_text}

CONTEXT:
{full_context}

USER QUESTION:
{user_message}

Please provide a helpful, accurate answer based ONLY on the solution critique report provided above."""

            # Generate response using LLM
            logger.info("🤖 CRITIQUE CHAT: Generating LLM response...")
            response = await self.ai_service.generate_analysis_response(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model="gpt-5-mini",  # Azure OpenAI deployment
                max_completion_tokens=16000  # gpt-5-mini needs large token budget
            )
            
            # Extract content from response dict
            response_text = response.get("content", "") if isinstance(response, dict) else str(response)
            
            logger.info(f"✅ CRITIQUE CHAT: Generated response: {len(response_text)} characters")
            
            return {
                "answer": response_text,
                "sources": sources
            }
            
        except Exception as e:
            logger.error(f"❌ CRITIQUE CHAT: Error generating response: {e}")
            return {
                "answer": "I apologize, but I encountered an error while processing your question. Please try again.",
                "sources": []
            }
    
    def _update_conversation_history(
        self,
        conversation_history: List[Dict[str, str]],
        user_message: str,
        assistant_response: str
    ) -> List[Dict[str, str]]:
        """Update conversation history with new messages."""
        # Add new messages
        updated_history = conversation_history + [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": assistant_response}
        ]
        
        # Keep only recent messages to manage context size
        if len(updated_history) > self.max_history_messages * 2:  # *2 for user+assistant pairs
            updated_history = updated_history[-(self.max_history_messages * 2):]
        
        return updated_history
    
    async def clear_conversation(
        self,
        project_id: str,
        tenant_id: str
    ) -> Dict[str, Any]:
        """Clear conversation history for a project."""
        try:
            logger.info(f"🗑️ CRITIQUE CHAT: Clearing conversation history for project {project_id}")
            
            # Conversation history is managed client-side, so just return success
            return {
                "success": True,
                "message": "Conversation history cleared",
                "project_id": project_id
            }
            
        except Exception as e:
            logger.error(f"❌ CRITIQUE CHAT: Error clearing conversation: {e}")
            return {
                "success": False,
                "error": "clear_error",
                "message": f"Failed to clear conversation: {str(e)}"
            }
