"""
Vector Service Adapter for VPM Integration

Bridges VPM vector operations with Yuba's existing vector storage system.
This adapter enables the dual vector store strategy described in VPM documentation.
"""

from typing import List, Dict, Any, Optional

# Import with error handling for graceful degradation
try:
    from src.mint.api.vector_storage.service import VectorStorageService
except ImportError:
    # Fallback if import fails
    class VectorStorageService:
        def __init__(self):
            pass
        async def semantic_search(self, **kwargs):
            return {'results': []}

try:
    from src.mint.api.actionable_insights.service import ActionableInsightsService
except ImportError:
    # Fallback if import fails
    class ActionableInsightsService:
        def __init__(self):
            pass


class YubaVectorAdapter:
    """
    Adapter to integrate VPM vector operations with Yuba's existing vector storage.
    
    This class implements the dual vector store strategy described in VPM documentation:
    - PV Report Vector Store: Raw customer feedback and validation data
    - Actionable Insights Vector Store: Processed insights and strategic recommendations
    """
    
    def __init__(self):
        """Initialize with Yuba's existing vector services"""
        self.vector_service = VectorStorageService()
        self.insights_service = ActionableInsightsService()
    
    async def get_pv_report_context(
        self, 
        report_id: str, 
        query: str, 
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get PV report context using Yuba's vector search with RAG.
        
        This provides raw customer feedback, interview transcripts, and validation data
        using semantic similarity search for the most relevant chunks.
        """
        try:
            # Use Yuba's vector search service for semantic similarity
            from src.mint.api.services.ai.vector_search_service import get_vector_search_service
            from src.mint.api.system.core.supabase_client import get_service_role_client
            
            print(f"🔍 DEBUG: Using vector search for PV report context with query: '{query}'")
            
            # Generate search query if not provided
            if not query.strip():
                query = "customer problems pains jobs to be done gains value proposition"
            
            # Get the vector search service instance
            vector_search_service = get_vector_search_service()
            
            # Try vector search, fallback to basic query if function doesn't exist
            try:
                # Create options with increased max_chunks
                from src.mint.api.services.ai.vector_search_service import VectorSearchOptions
                options = VectorSearchOptions(max_chunks=max_results)
                
                search_results = await vector_search_service.search_chunks(
                    report_id=report_id,
                    query=query,
                    options=options
                )
                
                if not search_results:
                    print(f"🔍 DEBUG: Vector search returned 0 results, using fallback")
                    return await self._fallback_pv_context(report_id, max_results)
                    
            except Exception as e:
                print(f"🔍 DEBUG: Vector search failed ({str(e)[:100]}...), using fallback")
                # Fallback to basic database query
                return await self._fallback_pv_context(report_id, max_results)
            
            print(f"🔍 DEBUG: Vector search returned {len(search_results)} results for PV report")
            
            # Transform to VPM expected format with actual similarity scores
            context_items = []
            for result in search_results:
                context_items.append({
                    'content': result.content,
                    'similarity': result.similarity,  # Actual vector similarity
                    'metadata': result.metadata,
                    'source_type': 'pv_report',
                    'document_id': result.report_id,
                    'chunk_index': result.chunk_index
                })
                print(f"🔍 DEBUG: PV chunk similarity {result.similarity:.3f}: {result.content[:100]}...")
            
            return context_items
            
        except Exception as e:
            print(f"❌ Error in vector search, falling back to basic query: {e}")
            # Fallback to basic query if vector search fails
            return await self._fallback_pv_context(report_id, max_results)
    
    async def _fallback_pv_context(self, report_id: str, max_results: int) -> List[Dict[str, Any]]:
        """Fallback method using basic database query."""
        try:
            from src.mint.api.system.core.supabase_client import get_service_role_client
            supabase = get_service_role_client()
            
            chunks_result = supabase.client.table("chunks").select(
                "*, documents!chunks_doc_id_fkey(id, title, source_type)"
            ).eq("documents.id", report_id).eq("documents.source_type", "pv_report").limit(max_results).execute()
            
            context_items = []
            for chunk in chunks_result.data or []:
                context_items.append({
                    'content': chunk.get('content', ''),
                    'similarity': 0.5,  # Lower similarity for fallback
                    'metadata': chunk.get('metadata', {}),
                    'source_type': 'pv_report',
                    'document_id': chunk.get('doc_id'),
                    'chunk_index': chunk.get('chunk_index', 0)
                })
            
            return context_items
            
        except Exception as e:
            print(f"Error in fallback PV context: {e}")
            return []
    
    async def get_actionable_insights_context(
        self, 
        report_id: str, 
        query: str, 
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get actionable insights context using Yuba's vector search.
        
        This provides processed insights, patterns, and strategic recommendations
        as described in the VPM dual vector store strategy.
        """
        try:
            # Use Yuba's vector search service for semantic similarity
            from src.mint.api.services.ai.vector_search_service import get_vector_search_service
            from src.mint.api.system.core.supabase_client import get_service_role_client
            
            print(f"🔍 DEBUG: Using vector search for actionable insights with query: '{query}'")
            
            # Generate search query if not provided
            if not query.strip():
                query = "insights recommendations patterns strategic opportunities market analysis"
            
            # First, find actionable insights documents linked to this PV report
            supabase = get_service_role_client()
            
            # Debug: Check if any actionable insights exist at all
            all_insights = supabase.client.table("documents").select("id, title, metadata").eq(
                "source_type", "actionable_insights"
            ).execute()
            print(f"🔍 DEBUG: Total actionable insights in system: {len(all_insights.data or [])}")
            
            # Use the correct relationship: source_document_id links actionable insights to PV report
            insights_docs = supabase.client.table("documents").select("id, source_document_id, title").eq(
                "source_type", "actionable_insights"
            ).eq("source_document_id", report_id).execute()
            
            print(f"🔍 DEBUG: Found {len(insights_docs.data or [])} actionable insights linked to PV report {report_id}")
            
            # Debug: Show what we found
            for doc in (insights_docs.data or []):
                print(f"🔍 DEBUG: Actionable insight: {doc['id']} -> {doc.get('title', 'No title')}")
            
            if not insights_docs.data:
                print(f"🔍 DEBUG: No actionable insights found for PV report {report_id}")
                # Print sample metadata to understand the structure
                for insight in (all_insights.data or [])[:3]:
                    print(f"🔍 DEBUG: Sample insight metadata: {insight.get('metadata', {})}")
                return []
            
            context_items = []
            
            # Get the vector search service instance
            vector_search_service = get_vector_search_service()
            
            # Perform vector search on each actionable insights document
            for doc in insights_docs.data:
                try:
                    # Create options with increased max_chunks
                    from src.mint.api.services.ai.vector_search_service import VectorSearchOptions
                    options = VectorSearchOptions(max_chunks=max_results // len(insights_docs.data))
                    
                    search_results = await vector_search_service.search_chunks(
                        report_id=doc["id"],
                        query=query,
                        options=options
                    )
                    
                    for result in search_results:
                        context_items.append({
                            'content': result.content,
                            'similarity': result.similarity,  # Actual vector similarity
                            'metadata': result.metadata,
                            'source_type': 'actionable_insights',
                            'document_id': result.report_id,
                            'insight_type': result.metadata.get('insight_type', 'general'),
                            'confidence_score': result.metadata.get('confidence_score', 0.8)
                        })
                        print(f"🔍 DEBUG: Insights chunk similarity {result.similarity:.3f}: {result.content[:100]}...")
                except Exception as search_error:
                    print(f"❌ Vector search failed for doc {doc['id']}: {search_error}")
            
            print(f"🔍 DEBUG: Vector search returned {len(context_items)} actionable insights results")
            return context_items[:max_results]
            
        except Exception as e:
            print(f"❌ Error in actionable insights vector search: {e}")
            return []
    
    async def dual_context_search(
        self, 
        project_id: str, 
        query: str, 
        max_results_per_store: int = 5
    ) -> Dict[str, Any]:
        """
        Perform dual vector store search as described in VPM documentation.
        
        This is the core method that implements the sophisticated context strategy:
        - Searches both PV report and actionable insights vector stores
        - Combines contexts for richer AI generation
        - Maintains traceability to source data
        """
        try:
            # First, get the PV report ID for this project
            pv_report_id = await self._get_project_pv_report_id(project_id)
            if not pv_report_id:
                return {
                    'pv_report_context': [],
                    'actionable_insights_context': [],
                    'combined_context': [],
                    'context_summary': {
                        'total_items': 0,
                        'pv_items': 0,
                        'insights_items': 0
                    }
                }
            
            # Search both vector stores simultaneously
            pv_context = await self.get_pv_report_context(
                report_id=pv_report_id,
                query=query,
                max_results=max_results_per_store
            )
            
            insights_context = await self.get_actionable_insights_context(
                report_id=pv_report_id,
                query=query,
                max_results=max_results_per_store
            )
            
            # Combine and rank contexts
            combined_context = self._merge_contexts(pv_context, insights_context)
            
            return {
                'pv_report_context': pv_context,
                'actionable_insights_context': insights_context,
                'combined_context': combined_context,
                'context_summary': {
                    'total_items': len(combined_context),
                    'pv_items': len(pv_context),
                    'insights_items': len(insights_context),
                    'query': query,
                    'project_id': project_id,
                    'pv_report_id': pv_report_id
                }
            }
            
        except Exception as e:
            print(f"Error in dual context search: {e}")
            return {
                'pv_report_context': [],
                'actionable_insights_context': [],
                'combined_context': [],
                'context_summary': {'total_items': 0, 'pv_items': 0, 'insights_items': 0}
            }
    
    async def get_project_contexts(self, project_id: str) -> List[Dict[str, Any]]:
        """
        Get all linked contexts for a project.
        
        This retrieves the contexts that were linked during project creation.
        """
        try:
            from src.vpm.adapters.database_adapter import get_yuba_database_adapter
            
            db_adapter = get_yuba_database_adapter()
            
            # Get project contexts from vmp_project_contexts table
            response = db_adapter.supabase.client.table('vmp_project_contexts').select(
                '*, documents!vmp_project_contexts_document_id_fkey(title, source_type)'
            ).eq('project_id', project_id).eq('is_active', True).execute()
            
            contexts = []
            for context in response.data:
                contexts.append({
                    'id': context['id'],
                    'project_id': context['project_id'],
                    'document_id': context['document_id'],
                    'context_type': context['context_type'],
                    'context_data': context['context_data'],
                    'document_title': context.get('documents', {}).get('title', 'Unknown'),
                    'source_type': context.get('documents', {}).get('source_type', 'unknown')
                })
            
            return contexts
            
        except Exception as e:
            print(f"Error getting project contexts: {e}")
            return []
    
    def _merge_contexts(
        self, 
        pv_context: List[Dict[str, Any]], 
        insights_context: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Merge and rank contexts from both vector stores.
        
        This implements intelligent context combination as described in VPM docs.
        """
        # Combine all contexts
        all_contexts = []
        
        # Add PV contexts with source weighting
        for item in pv_context:
            all_contexts.append({
                **item,
                'weighted_similarity': item['similarity'] * 0.6,  # Raw data gets 60% weight
                'context_source': 'pv_report'
            })
        
        # Add insights contexts with source weighting
        for item in insights_context:
            all_contexts.append({
                **item,
                'weighted_similarity': item['similarity'] * 0.8,  # Processed insights get 80% weight
                'context_source': 'actionable_insights'
            })
        
        # Sort by weighted similarity
        all_contexts.sort(key=lambda x: x['weighted_similarity'], reverse=True)
        
        # Return top contexts (limit to prevent token overflow)
        return all_contexts[:15]
    
    async def _get_project_pv_report_id(self, project_id: str) -> Optional[str]:
        """Get the PV report ID associated with a project"""
        try:
            from src.vpm.adapters.database_adapter import get_yuba_database_adapter
            
            db_adapter = get_yuba_database_adapter()
            
            # Get project details
            response = db_adapter.supabase.client.table('vmp_projects').select(
                'pv_report_id'
            ).eq('id', project_id).execute()
            
            if response.data:
                return response.data[0]['pv_report_id']
            
            return None
            
        except Exception as e:
            print(f"Error getting project PV report ID: {e}")
            return None
    
    async def create_embedding_summary(self, contexts: List[Dict[str, Any]]) -> Optional[List[float]]:
        """
        Create aggregated embedding for project contexts.
        
        This can be used for fast similarity search at the project level.
        """
        try:
            # This would use Yuba's existing embedding service
            # For now, return None to not break functionality
            return None
            
        except Exception as e:
            print(f"Error creating embedding summary: {e}")
            return None


# Singleton instance for VPM to use
_vector_adapter_instance = None

def get_yuba_vector_adapter() -> YubaVectorAdapter:
    """Get singleton instance of Yuba vector adapter"""
    global _vector_adapter_instance
    if _vector_adapter_instance is None:
        _vector_adapter_instance = YubaVectorAdapter()
    return _vector_adapter_instance
