"""
Vector Storage API Endpoints

REST API endpoints for vector storage and RAG operations supporting module context preservation.
"""

import logging
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends, Query, status
from fastapi.responses import JSONResponse

from .service import VectorStorageService
from .models import (
    DocumentCreate, DocumentUpdate, DocumentResponse, DocumentListResponse,
    ProblemValidationReportCreate, ProblemValidationReportUpdate, ProblemValidationReportResponse,
    ActionableInsightCreate, ActionableInsightUpdate, ActionableInsightResponse,
    VectorSearchRequest, VectorSearchResponse,
    SourceType
)

logger = logging.getLogger(__name__)

# Create router for vector storage endpoints
router = APIRouter(prefix="/api/v1/vector", tags=["vector-storage"])

# =============================================
# DOCUMENT ENDPOINTS
# =============================================

@router.post("/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    document_data: DocumentCreate,
    current_user_id: str = "test-user-123"  # Hardcoded for testing
):
    """
    Create a new document for vector storage.
    
    Supports all module types: problem_explorer, pv_report, actionable_insights, vp_map, mvp_spec, mv_analysis.
    """
    try:
        logger.info(f"Creating document: {document_data.title} (type: {document_data.source_type})")
        
        service = VectorStorageService(use_service_role=True)
        result = await service.create_document(document_data)
        
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.message
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while creating document"
        )

@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    tenant_id: Optional[str] = Query(None, description="Filter by tenant ID"),
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    source_type: Optional[SourceType] = Query(None, description="Filter by source type"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user_id: str = "test-user-123"  # Hardcoded for testing
):
    """
    List documents with filtering and pagination.
    
    Supports filtering by tenant, project, and source type.
    """
    try:
        logger.info(f"Listing documents for user {current_user_id}")
        
        service = VectorStorageService(use_service_role=False)
        result = await service.list_documents(
            user_id=current_user_id,
            tenant_id=tenant_id,
            project_id=project_id,
            source_type=source_type,
            page=page,
            page_size=page_size
        )
        
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.message
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while listing documents"
        )

@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    current_user_id: str = "test-user-123"  # Hardcoded for testing
):
    """
    Get document details by ID.
    
    User must have access to the document's tenant.
    """
    try:
        logger.info(f"Getting document {document_id} for user {current_user_id}")
        
        service = VectorStorageService(use_service_role=False)
        result = await service.get_document(document_id, current_user_id)
        
        if not result.success:
            if "not found" in result.message.lower() or "access denied" in result.message.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=result.message
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=result.message
                )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document {document_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while getting document"
        )

# =============================================
# PROBLEM VALIDATION REPORT ENDPOINTS
# =============================================

@router.post("/reports/problem-validation", response_model=ProblemValidationReportResponse, status_code=status.HTTP_201_CREATED)
async def create_problem_validation_report(
    report_data: ProblemValidationReportCreate,
    current_user_id: str = "test-user-123"  # Hardcoded for testing
):
    """
    Create a problem validation report with vector embeddings.
    
    This stores the report output from the Problem Validation module for context in later modules.
    """
    try:
        logger.info(f"Creating problem validation report: {report_data.title}")
        
        service = VectorStorageService(use_service_role=True)
        result = await service.create_problem_validation_report(report_data)
        
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.message
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating problem validation report: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while creating report"
        )

@router.put("/reports/problem-validation/{report_id}/embeddings")
async def update_problem_validation_report_embeddings(
    report_id: str,
    embeddings_data: Dict[str, List[float]],
    current_user_id: str = "test-user-123"  # Hardcoded for testing
):
    """
    Update vector embeddings for a problem validation report.
    
    Accepts embeddings for: full_content, problem_statement, market_analysis, recommendations.
    """
    try:
        logger.info(f"Updating embeddings for problem validation report {report_id}")
        
        service = VectorStorageService(use_service_role=True)
        
        # Extract embeddings
        full_content_embedding = embeddings_data.get("full_content")
        if not full_content_embedding:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="full_content embedding is required"
            )
        
        success = await service.update_problem_validation_report_embeddings(
            report_id=report_id,
            full_content_embedding=full_content_embedding,
            problem_statement_embedding=embeddings_data.get("problem_statement"),
            market_analysis_embedding=embeddings_data.get("market_analysis"),
            recommendations_embedding=embeddings_data.get("recommendations")
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update embeddings"
            )
        
        return {"success": True, "message": "Embeddings updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating report embeddings: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while updating embeddings"
        )

# =============================================
# ACTIONABLE INSIGHTS ENDPOINTS
# =============================================

@router.post("/insights", response_model=ActionableInsightResponse, status_code=status.HTTP_201_CREATED)
async def create_actionable_insight(
    insight_data: ActionableInsightCreate,
    current_user_id: str = "test-user-123"  # Hardcoded for testing
):
    """
    Create an actionable insight with vector embedding.
    
    Actionable insights are generated from reports and stored for semantic search.
    """
    try:
        logger.info(f"Creating actionable insight: {insight_data.title}")
        
        service = VectorStorageService(use_service_role=True)
        result = await service.create_actionable_insight(insight_data)
        
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.message
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating actionable insight: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while creating insight"
        )

@router.put("/insights/{insight_id}/embedding")
async def update_actionable_insight_embedding(
    insight_id: str,
    embedding_data: Dict[str, List[float]],
    current_user_id: str = "test-user-123"  # Hardcoded for testing
):
    """
    Update vector embedding for an actionable insight.
    
    The embedding is used for semantic search across insights.
    """
    try:
        logger.info(f"Updating embedding for actionable insight {insight_id}")
        
        content_embedding = embedding_data.get("content_embedding")
        if not content_embedding:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="content_embedding is required"
            )
        
        service = VectorStorageService(use_service_role=True)
        success = await service.update_actionable_insight_embedding(insight_id, content_embedding)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update embedding"
            )
        
        return {"success": True, "message": "Embedding updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating insight embedding: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while updating embedding"
        )

# =============================================
# SEARCH ENDPOINTS
# =============================================

@router.post("/search", response_model=VectorSearchResponse)
async def search_documents(
    search_request: VectorSearchRequest,
    current_user_id: str = "test-user-123"  # Hardcoded for testing
):
    """
    Search documents using vector similarity.
    
    Supports filtering by source type, tenant, and project.
    """
    try:
        logger.info(f"Searching documents with query: {search_request.query}")
        
        service = VectorStorageService(use_service_role=False)
        result = await service.search_documents(search_request, current_user_id)
        
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.message
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching documents: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while searching"
        )

@router.post("/search/insights")
async def search_actionable_insights(
    query_embedding: List[float],
    match_threshold: float = Query(0.7, ge=0, le=1, description="Similarity threshold"),
    match_count: int = Query(10, ge=1, le=100, description="Number of matches"),
    category_filter: Optional[str] = Query(None, description="Filter by insight type"),
    priority_filter: Optional[str] = Query(None, description="Filter by priority"),
    current_user_id: str = "test-user-123"  # Hardcoded for testing
):
    """
    Search actionable insights using vector similarity.
    
    Requires pre-computed query embedding (1536 dimensions).
    """
    try:
        logger.info(f"Searching actionable insights for user {current_user_id}")
        
        if len(query_embedding) != 1536:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Query embedding must be 1536 dimensions"
            )
        
        service = VectorStorageService(use_service_role=False)
        results = await service.search_actionable_insights(
            query_embedding=query_embedding,
            user_id=current_user_id,
            match_threshold=match_threshold,
            match_count=match_count,
            category_filter=category_filter,
            priority_filter=priority_filter
        )
        
        return {
            "success": True,
            "message": "Search completed successfully",
            "results": results,
            "total_results": len(results)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching actionable insights: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while searching insights"
        )

@router.post("/search/reports")
async def search_problem_validation_reports(
    query_embedding: List[float],
    match_threshold: float = Query(0.7, ge=0, le=1, description="Similarity threshold"),
    match_count: int = Query(10, ge=1, le=100, description="Number of matches"),
    report_type_filter: Optional[str] = Query(None, description="Filter by report type"),
    current_user_id: str = "test-user-123"  # Hardcoded for testing
):
    """
    Search problem validation reports using vector similarity.
    
    Requires pre-computed query embedding (1536 dimensions).
    """
    try:
        logger.info(f"Searching problem validation reports for user {current_user_id}")
        
        if len(query_embedding) != 1536:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Query embedding must be 1536 dimensions"
            )
        
        service = VectorStorageService(use_service_role=False)
        results = await service.search_problem_validation_reports(
            query_embedding=query_embedding,
            user_id=current_user_id,
            match_threshold=match_threshold,
            match_count=match_count,
            report_type_filter=report_type_filter
        )
        
        return {
            "success": True,
            "message": "Search completed successfully",
            "results": results,
            "total_results": len(results)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching problem validation reports: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while searching reports"
        )

# =============================================
# MODULE CONTEXT ENDPOINTS
# =============================================

@router.post("/modules/{module_name}/store-output")
async def store_module_output(
    module_name: str,
    output_data: Dict[str, Any],
    tenant_id: str = Query(..., description="Tenant ID"),
    project_id: str = Query(..., description="Project ID"),
    embeddings: Optional[Dict[str, List[float]]] = None,
    current_user_id: str = "test-user-123"  # Hardcoded for testing
):
    """
    Store module output with vector embeddings for context preservation.
    
    Supports modules: problem_validation, value_proposition, mvp_development, market_validation.
    """
    try:
        logger.info(f"Storing output for module {module_name}")
        
        valid_modules = ["problem_validation", "value_proposition", "mvp_development", "market_validation"]
        if module_name not in valid_modules:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid module name. Must be one of: {valid_modules}"
            )
        
        service = VectorStorageService(use_service_role=True)
        success = await service.store_module_output(
            tenant_id=tenant_id,
            project_id=project_id,
            user_id=current_user_id,
            module_name=module_name,
            output_data=output_data,
            embeddings=embeddings
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to store module output"
            )
        
        return {
            "success": True,
            "message": f"Module output for {module_name} stored successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error storing module output: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while storing module output"
        )

@router.get("/modules/{module_name}/context")
async def get_module_context(
    module_name: str,
    tenant_id: str = Query(..., description="Tenant ID"),
    project_id: str = Query(..., description="Project ID"),
    current_user_id: str = "test-user-123"  # Hardcoded for testing
):
    """
    Get context from previous modules for the current module.
    
    Returns outputs from all previous modules in the workflow order.
    """
    try:
        logger.info(f"Getting context for module {module_name}")
        
        valid_modules = ["problem_validation", "value_proposition", "mvp_development", "market_validation"]
        if module_name not in valid_modules:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid module name. Must be one of: {valid_modules}"
            )
        
        service = VectorStorageService(use_service_role=False)
        context = await service.get_module_context(
            tenant_id=tenant_id,
            project_id=project_id,
            user_id=current_user_id,
            current_module=module_name
        )
        
        return {
            "success": True,
            "message": f"Context retrieved for {module_name}",
            "context": context,
            "total_context_items": len(context)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting module context: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while getting context"
        )

# =============================================
# DEMO ENDPOINTS
# =============================================

@router.get("/demo/create-sample-data")
async def create_sample_vector_data():
    """
    Create sample vector storage data for demonstration.
    """
    try:
        service = VectorStorageService(use_service_role=True)
        
        # Sample problem validation report
        from uuid import uuid4
        
        sample_report = ProblemValidationReportCreate(
            session_id=uuid4(),
            user_id=uuid4(),
            title="E-commerce Platform Market Analysis",
            executive_summary="Comprehensive analysis of e-commerce opportunities in emerging markets",
            problem_statement="Small businesses in developing countries lack access to affordable e-commerce platforms",
            market_analysis="The market size is estimated at $2.5B with 15% annual growth",
            recommendations="Develop a low-cost, mobile-first e-commerce solution",
            industry="E-commerce",
            geography="Nigeria",
            target_audience="Small businesses"
        )
        
        report_result = await service.create_problem_validation_report(sample_report)
        
        # Sample actionable insight
        if report_result.success and report_result.data:
            sample_insight = ActionableInsightCreate(
                report_id=report_result.data.id,
                user_id=uuid4(),
                insight_type="opportunity",
                title="Mobile Payment Integration Opportunity",
                description="Integrate with local mobile payment providers to reduce transaction costs",
                priority="high",
                confidence_score=0.85,
                recommended_actions=["Research local payment providers", "Develop API integration"],
                impact_level="high"
            )
            
            insight_result = await service.create_actionable_insight(sample_insight)
        
        return {
            "success": True,
            "message": "Sample vector storage data created successfully",
            "data": {
                "problem_validation_report": report_result.data.dict() if report_result.success else None,
                "actionable_insight": insight_result.data.dict() if 'insight_result' in locals() and insight_result.success else None
            }
        }
        
    except Exception as e:
        logger.error(f"Error creating sample data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create sample data: {str(e)}"
        )

# =============================================
# HEALTH CHECK ENDPOINT
# =============================================

@router.get("/health")
async def vector_storage_health_check():
    """
    Health check endpoint for vector storage service.
    """
    return {
        "status": "healthy",
        "service": "vector-storage",
        "message": "Vector storage and RAG system operational",
        "features": {
            "document_storage": True,
            "vector_embeddings": True,
            "semantic_search": True,
            "module_context": True,
            "rag_support": True
        }
    }
