"""
Vector Storage Service

Business logic for vector storage and RAG operations supporting module context preservation.
"""

import logging
import hashlib
import json
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
import uuid

from ..system.core.supabase_client import get_supabase_client
from .models import (
    Document, DocumentCreate, DocumentUpdate, DocumentResponse, DocumentListResponse,
    Chunk, ChunkCreate, ChunkUpdate,
    ProblemValidationReport, ProblemValidationReportCreate, ProblemValidationReportUpdate,
    ProblemValidationReportResponse,
    ActionableInsight, ActionableInsightCreate, ActionableInsightUpdate, ActionableInsightResponse,
    VectorSearchRequest, VectorSearchResponse, VectorSearchResult,
    SourceType
)

logger = logging.getLogger(__name__)

class VectorStorageService:
    """Service for vector storage and RAG operations"""
    
    def __init__(self, use_service_role: bool = True):
        """Initialize vector storage service with Supabase client"""
        self.supabase = get_supabase_client(use_service_role=use_service_role)
        self.use_service_role = use_service_role
    
    # =============================================
    # DOCUMENT OPERATIONS
    # =============================================
    
    async def create_document(self, document_data: DocumentCreate) -> DocumentResponse:
        """Create a new document for vector storage"""
        try:
            logger.info(f"Creating document: {document_data.title} (type: {document_data.source_type})")
            
            # Generate content hash if content is provided
            sha256_hash = None
            if document_data.content:
                sha256_hash = hashlib.sha256(document_data.content.encode()).hexdigest()
            
            # Create document record
            document_result = self.supabase.table("documents").insert({
                "tenant_id": str(document_data.tenant_id),
                "project_id": str(document_data.project_id) if document_data.project_id else None,
                "source_type": document_data.source_type,
                "title": document_data.title,
                "content": document_data.content,
                "storage_path": document_data.storage_path,
                "sha256": sha256_hash,
                "created_by": str(document_data.created_by),
                "metadata": document_data.metadata
            }).execute()
            
            if not document_result.data:
                raise Exception("Failed to create document")
            
            document = Document(**document_result.data[0])
            
            return DocumentResponse(
                success=True,
                message="Document created successfully",
                data=document
            )
            
        except Exception as e:
            logger.error(f"Error creating document: {str(e)}")
            return DocumentResponse(
                success=False,
                message=f"Failed to create document: {str(e)}",
                data=None
            )
    
    async def get_document(self, document_id: str, user_id: str) -> DocumentResponse:
        """Get document by ID with access control"""
        try:
            # Get document with tenant access check
            document_result = self.supabase.table("documents").select(
                "*, tenant_memberships!inner(user_id)"
            ).eq("id", document_id).eq("tenant_memberships.user_id", user_id).eq(
                "tenant_memberships.is_active", True
            ).execute()
            
            if not document_result.data:
                return DocumentResponse(
                    success=False,
                    message="Document not found or access denied",
                    data=None
                )
            
            document = Document(**document_result.data[0])
            
            return DocumentResponse(
                success=True,
                message="Document retrieved successfully",
                data=document
            )
            
        except Exception as e:
            logger.error(f"Error getting document {document_id}: {str(e)}")
            return DocumentResponse(
                success=False,
                message=f"Failed to get document: {str(e)}",
                data=None
            )
    
    async def list_documents(
        self, 
        user_id: str, 
        tenant_id: Optional[str] = None,
        project_id: Optional[str] = None,
        source_type: Optional[SourceType] = None,
        page: int = 1, 
        page_size: int = 20
    ) -> DocumentListResponse:
        """List documents with filtering and pagination"""
        try:
            # Build query
            query = self.supabase.table("documents").select(
                "*, tenant_memberships!inner(user_id)"
            ).eq("tenant_memberships.user_id", user_id).eq("tenant_memberships.is_active", True)
            
            # Apply filters
            if tenant_id:
                query = query.eq("tenant_id", tenant_id)
            if project_id:
                query = query.eq("project_id", project_id)
            if source_type:
                query = query.eq("source_type", source_type)
            
            # Apply pagination
            offset = (page - 1) * page_size
            documents_result = query.range(offset, offset + page_size - 1).execute()
            
            # Get total count
            count_query = self.supabase.table("documents").select(
                "id", count="exact"
            ).eq("tenant_memberships.user_id", user_id).eq("tenant_memberships.is_active", True)
            
            if tenant_id:
                count_query = count_query.eq("tenant_id", tenant_id)
            if project_id:
                count_query = count_query.eq("project_id", project_id)
            if source_type:
                count_query = count_query.eq("source_type", source_type)
            
            count_result = count_query.execute()
            total = count_result.count if count_result.count else 0
            
            documents = [Document(**doc) for doc in documents_result.data]
            
            return DocumentListResponse(
                success=True,
                message="Documents retrieved successfully",
                data=documents,
                total=total,
                page=page,
                page_size=page_size
            )
            
        except Exception as e:
            logger.error(f"Error listing documents: {str(e)}")
            return DocumentListResponse(
                success=False,
                message=f"Failed to list documents: {str(e)}",
                data=[],
                total=0,
                page=page,
                page_size=page_size
            )
    
    # =============================================
    # CHUNK OPERATIONS
    # =============================================
    
    async def create_chunk(self, chunk_data: ChunkCreate) -> bool:
        """Create a chunk with vector embedding"""
        try:
            # Create chunk record
            chunk_result = self.supabase.table("chunks").insert({
                "doc_id": str(chunk_data.doc_id),
                "chunk_index": chunk_data.chunk_index,
                "content": chunk_data.content,
                "token_count": chunk_data.token_count,
                "embedding": chunk_data.embedding,
                "metadata": chunk_data.metadata
            }).execute()
            
            return bool(chunk_result.data)
            
        except Exception as e:
            logger.error(f"Error creating chunk: {str(e)}")
            return False
    
    async def create_chunks_for_document(
        self, 
        document_id: str, 
        chunks_data: List[Dict[str, Any]]
    ) -> int:
        """Create multiple chunks for a document"""
        try:
            chunks_to_insert = []
            
            for i, chunk_data in enumerate(chunks_data):
                chunks_to_insert.append({
                    "doc_id": document_id,
                    "chunk_index": i,
                    "content": chunk_data["content"],
                    "token_count": chunk_data.get("token_count"),
                    "embedding": chunk_data.get("embedding"),
                    "metadata": chunk_data.get("metadata", {})
                })
            
            # Batch insert chunks
            chunks_result = self.supabase.table("chunks").insert(chunks_to_insert).execute()
            
            return len(chunks_result.data) if chunks_result.data else 0
            
        except Exception as e:
            logger.error(f"Error creating chunks for document {document_id}: {str(e)}")
            return 0
    
    # =============================================
    # PROBLEM VALIDATION REPORT OPERATIONS
    # =============================================
    
    async def create_problem_validation_report(
        self, 
        report_data: ProblemValidationReportCreate
    ) -> ProblemValidationReportResponse:
        """Create a problem validation report with vector embeddings"""
        try:
            logger.info(f"Creating problem validation report: {report_data.title}")
            
            # Create report record
            report_result = self.supabase.table("problem_validation_reports").insert({
                "session_id": str(report_data.session_id),
                "user_id": str(report_data.user_id),
                "title": report_data.title,
                "executive_summary": report_data.executive_summary,
                "problem_statement": report_data.problem_statement,
                "market_analysis": report_data.market_analysis,
                "competitive_analysis": report_data.competitive_analysis,
                "customer_validation": report_data.customer_validation,
                "technical_feasibility": report_data.technical_feasibility,
                "business_model": report_data.business_model,
                "recommendations": report_data.recommendations,
                "report_type": report_data.report_type,
                "industry": report_data.industry,
                "geography": report_data.geography,
                "target_audience": report_data.target_audience,
                "market_size_estimate": report_data.market_size_estimate,
                "customer_segments": report_data.customer_segments,
                "competitive_landscape": report_data.competitive_landscape,
                "risk_assessment": report_data.risk_assessment,
                "status": "draft"
            }).execute()
            
            if not report_result.data:
                raise Exception("Failed to create problem validation report")
            
            report = ProblemValidationReport(**report_result.data[0])
            
            return ProblemValidationReportResponse(
                success=True,
                message="Problem validation report created successfully",
                data=report
            )
            
        except Exception as e:
            logger.error(f"Error creating problem validation report: {str(e)}")
            return ProblemValidationReportResponse(
                success=False,
                message=f"Failed to create report: {str(e)}",
                data=None
            )
    
    async def update_problem_validation_report_embeddings(
        self,
        report_id: str,
        full_content_embedding: List[float],
        problem_statement_embedding: Optional[List[float]] = None,
        market_analysis_embedding: Optional[List[float]] = None,
        recommendations_embedding: Optional[List[float]] = None
    ) -> bool:
        """Update vector embeddings for a problem validation report"""
        try:
            update_data = {
                "full_content_vector": full_content_embedding
            }
            
            if problem_statement_embedding:
                update_data["problem_statement_vector"] = problem_statement_embedding
            if market_analysis_embedding:
                update_data["market_analysis_vector"] = market_analysis_embedding
            if recommendations_embedding:
                update_data["recommendations_vector"] = recommendations_embedding
            
            result = self.supabase.table("problem_validation_reports").update(update_data).eq(
                "id", report_id
            ).execute()
            
            return bool(result.data)
            
        except Exception as e:
            logger.error(f"Error updating report embeddings: {str(e)}")
            return False
    
    # =============================================
    # ACTIONABLE INSIGHTS OPERATIONS
    # =============================================
    
    async def create_actionable_insight(
        self, 
        insight_data: ActionableInsightCreate
    ) -> ActionableInsightResponse:
        """Create an actionable insight with vector embedding"""
        try:
            logger.info(f"Creating actionable insight: {insight_data.title}")
            
            # Create insight record
            insight_result = self.supabase.table("actionable_insights").insert({
                "report_id": str(insight_data.report_id),
                "user_id": str(insight_data.user_id),
                "insight_type": insight_data.insight_type,
                "title": insight_data.title,
                "description": insight_data.description,
                "priority": insight_data.priority,
                "confidence_score": insight_data.confidence_score,
                "supporting_data": insight_data.supporting_data,
                "recommended_actions": insight_data.recommended_actions,
                "impact_assessment": insight_data.impact_assessment,
                "timeline": insight_data.timeline,
                "resources_required": insight_data.resources_required,
                "implementation_steps": insight_data.implementation_steps,
                "success_metrics": insight_data.success_metrics,
                "estimated_effort": insight_data.estimated_effort,
                "estimated_timeline": insight_data.estimated_timeline,
                "tags": insight_data.tags,
                "source_sections": insight_data.source_sections,
                "impact_level": insight_data.impact_level,
                "status": "active"
            }).execute()
            
            if not insight_result.data:
                raise Exception("Failed to create actionable insight")
            
            insight = ActionableInsight(**insight_result.data[0])
            
            return ActionableInsightResponse(
                success=True,
                message="Actionable insight created successfully",
                data=insight
            )
            
        except Exception as e:
            logger.error(f"Error creating actionable insight: {str(e)}")
            return ActionableInsightResponse(
                success=False,
                message=f"Failed to create insight: {str(e)}",
                data=None
            )
    
    async def update_actionable_insight_embedding(
        self,
        insight_id: str,
        content_embedding: List[float]
    ) -> bool:
        """Update vector embedding for an actionable insight"""
        try:
            result = self.supabase.table("actionable_insights").update({
                "content_vector": content_embedding
            }).eq("id", insight_id).execute()
            
            return bool(result.data)
            
        except Exception as e:
            logger.error(f"Error updating insight embedding: {str(e)}")
            return False
    
    # =============================================
    # VECTOR SEARCH OPERATIONS
    # =============================================
    
    async def search_documents(self, search_request: VectorSearchRequest, user_id: str) -> VectorSearchResponse:
        """Search documents using vector similarity"""
        try:
            # For now, we'll do a simple text search since we need embedding generation
            # In production, you'd generate embeddings for the query and use vector search
            
            query = self.supabase.table("documents").select(
                "*, tenant_memberships!inner(user_id)"
            ).eq("tenant_memberships.user_id", user_id).eq("tenant_memberships.is_active", True)
            
            # Apply filters
            if search_request.tenant_id:
                query = query.eq("tenant_id", str(search_request.tenant_id))
            if search_request.project_id:
                query = query.eq("project_id", str(search_request.project_id))
            if search_request.source_types:
                query = query.in_("source_type", search_request.source_types)
            
            # Simple text search (replace with vector search in production)
            # Note: Removed .or_() as Supabase Python client doesn't support it
            # Using ilike on title only - content filtering done in Python if needed
            if search_request.query:
                query = query.ilike("title", f"%{search_request.query}%")
            
            documents_result = query.limit(search_request.match_count).execute()
            
            # Convert to search results
            results = []
            for doc in documents_result.data:
                results.append(VectorSearchResult(
                    id=doc["id"],
                    title=doc["title"],
                    content=doc["content"] or "",
                    source_type=doc["source_type"],
                    similarity=0.8,  # Placeholder similarity score
                    metadata=doc["metadata"]
                ))
            
            return VectorSearchResponse(
                success=True,
                message="Search completed successfully",
                query=search_request.query,
                results=results,
                total_results=len(results)
            )
            
        except Exception as e:
            logger.error(f"Error searching documents: {str(e)}")
            return VectorSearchResponse(
                success=False,
                message=f"Search failed: {str(e)}",
                query=search_request.query,
                results=[],
                total_results=0
            )
    
    async def search_actionable_insights(
        self,
        query_embedding: List[float],
        user_id: str,
        match_threshold: float = 0.7,
        match_count: int = 10,
        category_filter: Optional[str] = None,
        priority_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search actionable insights using vector similarity"""
        try:
            # Use the PostgreSQL function created in the migration
            result = self.supabase.rpc("search_actionable_insights", {
                "query_embedding": query_embedding,
                "user_id_param": user_id,
                "match_threshold": match_threshold,
                "match_count": match_count,
                "category_filter": category_filter,
                "priority_filter": priority_filter
            }).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Error searching actionable insights: {str(e)}")
            return []
    
    async def search_problem_validation_reports(
        self,
        query_embedding: List[float],
        user_id: str,
        match_threshold: float = 0.7,
        match_count: int = 10,
        report_type_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search problem validation reports using vector similarity"""
        try:
            # Use the PostgreSQL function created in the migration
            result = self.supabase.rpc("search_problem_validation_reports", {
                "query_embedding": query_embedding,
                "user_id_param": user_id,
                "match_threshold": match_threshold,
                "match_count": match_count,
                "report_type_filter": report_type_filter
            }).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Error searching problem validation reports: {str(e)}")
            return []
    
    # =============================================
    # MODULE CONTEXT OPERATIONS
    # =============================================
    
    async def store_module_output(
        self,
        tenant_id: str,
        project_id: str,
        user_id: str,
        module_name: str,
        output_data: Dict[str, Any],
        embeddings: Optional[Dict[str, List[float]]] = None
    ) -> bool:
        """Store module output with vector embeddings for context preservation"""
        try:
            # Determine source type based on module
            source_type_mapping = {
                "problem_validation": "pv_report",
                "value_proposition": "vp_map",
                "mvp_development": "mvp_spec",
                "market_validation": "mv_analysis"
            }
            
            source_type = source_type_mapping.get(module_name, "problem_explorer")
            
            # Create document for the module output
            document_data = DocumentCreate(
                tenant_id=uuid.UUID(tenant_id),
                project_id=uuid.UUID(project_id),
                created_by=uuid.UUID(user_id),
                title=f"{module_name.replace('_', ' ').title()} Output",
                content=json.dumps(output_data, indent=2),
                source_type=source_type,
                metadata={
                    "module_name": module_name,
                    "output_type": "module_result",
                    "generated_at": datetime.utcnow().isoformat()
                }
            )
            
            document_response = await self.create_document(document_data)
            
            if not document_response.success or not document_response.data:
                return False
            
            # Create chunks with embeddings if provided
            if embeddings:
                chunks_data = []
                for section, embedding in embeddings.items():
                    if section in output_data:
                        chunks_data.append({
                            "content": str(output_data[section]),
                            "embedding": embedding,
                            "metadata": {"section": section, "module": module_name}
                        })
                
                if chunks_data:
                    chunks_created = await self.create_chunks_for_document(
                        str(document_response.data.id), chunks_data
                    )
                    logger.info(f"Created {chunks_created} chunks for {module_name} output")
            
            return True
            
        except Exception as e:
            logger.error(f"Error storing module output for {module_name}: {str(e)}")
            return False
    
    async def get_module_context(
        self,
        tenant_id: str,
        project_id: str,
        user_id: str,
        current_module: str
    ) -> List[Dict[str, Any]]:
        """Get context from previous modules for the current module"""
        try:
            # Define module order
            module_order = ["problem_validation", "value_proposition", "mvp_development", "market_validation"]
            
            if current_module not in module_order:
                return []
            
            current_index = module_order.index(current_module)
            previous_modules = module_order[:current_index]
            
            if not previous_modules:
                return []
            
            # Get documents from previous modules
            source_types = []
            for module in previous_modules:
                if module == "problem_validation":
                    source_types.append("pv_report")
                elif module == "value_proposition":
                    source_types.append("vp_map")
                elif module == "mvp_development":
                    source_types.append("mvp_spec")
                elif module == "market_validation":
                    source_types.append("mv_analysis")
            
            documents_response = await self.list_documents(
                user_id=user_id,
                tenant_id=tenant_id,
                project_id=project_id,
                page_size=50  # Get more context
            )
            
            if not documents_response.success:
                return []
            
            # Filter and format context
            context = []
            for doc in documents_response.data:
                if doc.source_type in source_types:
                    context.append({
                        "module": doc.metadata.get("module_name", "unknown"),
                        "title": doc.title,
                        "content": doc.content,
                        "source_type": doc.source_type,
                        "created_at": doc.created_at.isoformat(),
                        "metadata": doc.metadata
                    })
            
            return context
            
        except Exception as e:
            logger.error(f"Error getting module context: {str(e)}")
            return []
