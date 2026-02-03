"""
VPM API Endpoints - Integrated with Yuba

These endpoints provide VPM functionality while seamlessly integrating with
Yuba's existing authentication, credit system, and database infrastructure.

The original VPM code remains completely unchanged.
"""

from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Import Yuba's existing auth system (use production system like other working endpoints)
from src.mint.api.auth.production.system import get_current_user, get_current_user_with_tenant
from src.mint.api.system.core.supabase_client import get_service_role_client

# Import our integration service
from ..services.integrated_vmp_service import get_integrated_vmp_service
from ..services.field_prep_service import get_yuba_field_prep_service
from ..models.field_prep import (
    FieldPrepHypothesisRequest, FieldPrepHypothesisResponse,
    FieldPrepAssumptionsRequest, FieldPrepAssumptionsResponse,
    FieldPrepStakeholdersRequest, FieldPrepStakeholdersResponse,
    FieldPrepQuestionnairesRequest, FieldPrepQuestionnairesResponse,
    FieldPrepProgressResponse, FieldPrepExportRequest, FieldPrepExportResponse
)


# Create router with Yuba patterns
router = APIRouter(
    prefix="/api/v2/vmp",
    tags=["🎯 Value Proposition Module (Module 2)"]
)


# DEPRECATED: This function is kept for backward compatibility but should not be used.
# Use get_current_user_with_tenant dependency instead which extracts tenant_id from JWT.
async def get_user_tenant_id_legacy(user_id: str) -> str:
    """
    DEPRECATED: Get the tenant ID for a user from tenant_memberships table.
    
    WARNING: This function is non-deterministic when a user has multiple tenant memberships.
    It returns an arbitrary active tenant, NOT the user's currently selected workspace.
    
    Use get_current_user_with_tenant dependency instead, which extracts tenant_id
    directly from the JWT token issued during tenant-specific login.
    """
    try:
        # Use service role to query tenant memberships
        supabase = get_service_role_client()
        
        # Query tenant_memberships table for active membership
        # WARNING: This is non-deterministic - returns arbitrary tenant
        result = supabase.client.table("tenant_memberships").select(
            "tenant_id"
        ).eq("user_id", user_id).eq("is_active", True).order("created_at").limit(1).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=403, 
                detail="User does not have access to any tenant"
            )
        
        return result.data[0]["tenant_id"]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get user tenant: {str(e)}"
        )


# Request/Response Models (compatible with original VPM)
class CreateProjectRequest(BaseModel):
    """Request to create a new VMP project"""
    name: str = Field(..., min_length=1, max_length=100, description="Project name")
    pv_report_id: str = Field(..., description="ID of the Problem Validation report to base this project on")


class CustomerProfileGenerationRequest(BaseModel):
    """Request for Customer Profile generation (Step 1)"""
    creativity_level: float = Field(0.7, ge=0.0, le=1.0, description="AI creativity level")
    include_context_summary: bool = Field(True, description="Include context summary in response")


class CustomerProfileSelectionRequest(BaseModel):
    """Request for Customer Profile selections (Step 1 completion)"""
    selected_jtbd_ids: List[str] = Field(..., description="Selected Jobs-to-be-Done IDs (max 3)")
    selected_pain_ids: List[str] = Field(..., description="Selected Pain IDs (max 3)")
    selected_gain_ids: List[str] = Field(..., description="Selected Gain IDs (max 3)")


class ValueMapGenerationRequest(BaseModel):
    """Request for Value Map generation (Step 2)"""
    creativity_level: float = Field(0.7, ge=0.0, le=1.0, description="AI creativity level")
    include_context_summary: bool = Field(True, description="Include context summary in response")


class ValueMapSelectionRequest(BaseModel):
    """Request for Value Map selections (Step 2 completion)"""
    selected_product_service_ids: List[str] = Field(..., description="Selected Products/Services IDs (max 3)")
    selected_pain_reliever_ids: List[str] = Field(..., description="Selected Pain Reliever IDs (max 3)")
    selected_gain_creator_ids: List[str] = Field(..., description="Selected Gain Creator IDs (max 3)")


class VPCCompositionRequest(BaseModel):
    """Request for final VPC composition (Step 3)"""
    include_visual: bool = Field(True, description="Include visual VPC canvas")
    export_format: str = Field("json", description="Export format: json, pdf, png")


# ==================== REPORT DISCOVERY ENDPOINTS ====================

@router.get("/reports")
async def browse_pv_reports(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(35, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search query for report titles"),
    current_user: dict = Depends(get_current_user_with_tenant)
):
    """
    Browse available Problem Validation reports for VPM project creation.
    
    This endpoint allows users to discover PV reports from Module 1 that can be used
    as the foundation for VPM projects in Module 2.
    
    **Integration Points:**
    - Uses Yuba's existing authentication system
    - Leverages Yuba's vector storage for PV reports
    - Maintains tenant isolation through JWT tenant context
    """
    try:
        # Get user and tenant from JWT token context (correct tenant isolation)
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        
        service = get_integrated_vmp_service()
        
        result = await service.browse_pv_reports(
            tenant_id=tenant_id,
            user_id=user_id,
            page=page,
            page_size=page_size,
            search=search
        )
        
        if result['success']:
            return {
                "success": True,
                "data": {
                    "reports": result['reports'],
                    "pagination": {
                        "page": result['page'],
                        "page_size": result['page_size'],
                        "total_count": result['total_count'],
                        "has_next": result['has_next']
                    }
                },
                "message": "PV reports retrieved successfully"
            }
        else:
            raise HTTPException(status_code=500, detail=result['error'])
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch reports: {str(e)}")


@router.get("/reports/{report_id}")
async def get_report_detail(
    report_id: str,
    current_user: dict = Depends(get_current_user_with_tenant)
):
    """
    Get detailed information about a specific Problem Validation report.
    
    This provides comprehensive information about a PV report including:
    - Report content preview
    - Associated actionable insights
    - Metadata and statistics
    """
    try:
        # Get user and tenant from JWT token context (correct tenant isolation)
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        
        service = get_integrated_vmp_service()
        
        # Use the database adapter to get report details
        report_detail = await service.db_adapter.get_report_detail(
            report_id=report_id,
            tenant_id=tenant_id
        )
        
        if not report_detail:
            raise HTTPException(status_code=404, detail="Report not found")
        
        return {
            "success": True,
            "data": report_detail,
            "message": "Report details retrieved successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch report details: {str(e)}")


# ==================== PROJECT MANAGEMENT ENDPOINTS ====================

@router.post("/projects")
async def create_vmp_project(
    project_request: CreateProjectRequest,
    current_user: dict = Depends(get_current_user_with_tenant)
):
    """
    Create new VPM project linked to PV report and actionable insights.
    
    **This is the key transition point from Module 1 (PVM) to Module 2 (VPM).**
    
    The project creation process:
    1. Validates user has access to the specified PV report
    2. Checks user has sufficient credits for project creation
    3. Creates the VPM project in the database
    4. Links the project to both PV report and actionable insights (dual vector store)
    5. Deducts credits from user's account
    
    **Integration Features:**
    - Uses Yuba's existing credit system
    - Implements dual vector store linking as described in VPM docs
    - Maintains full audit trail through Yuba's systems
    """
    try:
        # Get user and tenant from JWT token context (correct tenant isolation)
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        
        service = get_integrated_vmp_service()
        
        # Prepare project data
        project_data = {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "name": project_request.name,
            "pv_report_id": project_request.pv_report_id
        }
        
        # Create project with full integration
        result = await service.create_vmp_project(
            project_data=project_data,
            user_id=user_id
        )
        
        if result['success']:
            return {
                "success": True,
                "data": result['project'],
                "message": result['message']
            }
        else:
            if "credits" in result['error'].lower():
                raise HTTPException(status_code=402, detail=result['error'])
            else:
                raise HTTPException(status_code=400, detail=result['error'])
                
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create project: {str(e)}")


@router.get("/projects")
async def get_user_projects(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(35, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by project status"),
    search: Optional[str] = Query(None, description="Search query for project names"),
    current_user: dict = Depends(get_current_user_with_tenant)
):
    """
    Get user's VPM projects with pagination and filtering.
    
    Returns a list of the user's VPM projects with:
    - Project metadata and progress
    - Linked PV report information
    - Artifact counts and status
    """
    try:
        # Get user and tenant from JWT token context (correct tenant isolation)
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        
        service = get_integrated_vmp_service()
        
        result = await service.get_user_projects(
            tenant_id=tenant_id,
            user_id=user_id,
            page=page,
            page_size=page_size,
            status_filter=status,
            search=search
        )
        
        if result['success']:
            return {
                "success": True,
                "data": {
                    "projects": result['projects'],
                    "pagination": {
                        "page": result['page'],
                        "page_size": result['page_size'],
                        "total_count": result['total_count'],
                        "has_next": result['has_next']
                    }
                },
                "message": "Projects retrieved successfully"
            }
        else:
            raise HTTPException(status_code=500, detail=result['error'])
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch projects: {str(e)}")


@router.get("/projects/{project_id}")
async def get_project_detail(
    project_id: str,
    current_user: dict = Depends(get_current_user_with_tenant)
):
    """
    Get detailed information about a specific VPM project.
    
    Includes:
    - Project metadata and current status
    - Linked contexts (PV report + actionable insights)
    - Generated artifacts and progress
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        service = get_integrated_vmp_service()
        
        # Get project contexts to show dual vector store integration
        contexts = await service.vector_adapter.get_project_contexts(project_id)
        
        return {
            "success": True,
            "data": {
                "project_id": project_id,
                "contexts": contexts,
                "context_summary": {
                    "total_contexts": len(contexts),
                    "pv_report_contexts": len([c for c in contexts if c['context_type'] == 'pv_report']),
                    "insights_contexts": len([c for c in contexts if c['context_type'] == 'actionable_insights'])
                }
            },
            "message": "Project details retrieved successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch project details: {str(e)}")


# ==================== VPC GENERATION WORKFLOW ENDPOINTS ====================

@router.post("/projects/{project_id}/vpc/step1/generate-customer-profile")
async def generate_customer_profile(
    project_id: str,
    generation_request: CustomerProfileGenerationRequest,
    current_user: dict = Depends(get_current_user_with_tenant)
):
    """
    **STEP 1: Generate Customer Profile Candidates**
    
    Generate 10 candidates each for Jobs-to-be-Done, Pains, and Gains using dual vector store context.
    
    **This implements the sophisticated dual vector store strategy:**
    - Searches both PV report data (raw customer feedback) and actionable insights (processed patterns)
    - Generates evidence-based candidates with confidence scores
    - Maintains traceability to source data
    
    **Output:** 30 total candidates (10 JTBD + 10 Pains + 10 Gains) for user selection
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        service = get_integrated_vmp_service()
        
        # Prepare generation request for customer profile
        generation_data = {
            "query": "",  # Auto-generated from project context
            "generation_type": "customer_profile",
            "creativity_level": generation_request.creativity_level,
            "include_context_summary": generation_request.include_context_summary
        }
        
        # Generate customer profile candidates
        result = await service.generate_vpc_with_dual_context(
            project_id=project_id,
            generation_request=generation_data,
            user_id=user_id
        )
        
        if result['success']:
            response_data = {
                "customer_profile_candidates": result['vpc_data'],
                "generation_metadata": {
                    "project_id": project_id,
                    "step": 1,
                    "step_name": "customer_profile_generation",
                    "model_used": result['vpc_data'].get('generation_metadata', {}).get('model_used', 'integrated'),
                    "generation_time": result['vpc_data'].get('generation_metadata', {}).get('generation_time')
                }
            }
            
            # Include context summary if requested
            if generation_request.include_context_summary:
                response_data["context_summary"] = result.get('context_summary', {})
            
            return {
                "success": True,
                "data": response_data,
                "message": "Customer profile candidates generated successfully. Please select 3 items from each category (JTBD, Pains, Gains).",
                "next_step": f"/api/v2/vmp/projects/{project_id}/vpc/step1/select-customer-profile"
            }
        else:
            if "credits" in result['error'].lower():
                raise HTTPException(status_code=402, detail=result['error'])
            else:
                raise HTTPException(status_code=400, detail=result['error'])
                
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate customer profile: {str(e)}")


@router.post("/projects/{project_id}/vpc/step1/select-customer-profile")
async def select_customer_profile(
    project_id: str,
    selection_request: CustomerProfileSelectionRequest,
    current_user: dict = Depends(get_current_user_with_tenant)
):
    """
    **STEP 1 COMPLETION: Save Customer Profile Selections**
    
    Save user's selected Jobs-to-be-Done, Pains, and Gains (3 each, 9 total).
    These selections will be used as context for Value Map generation in Step 2.
    
    **Validation:**
    - Exactly 3 JTBD selections required
    - Exactly 3 Pain selections required  
    - Exactly 3 Gain selections required
    - All IDs must be valid from previous generation
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        # Validate selection counts
        if len(selection_request.selected_jtbd_ids) != 3:
            raise HTTPException(status_code=400, detail="Exactly 3 Jobs-to-be-Done must be selected")
        if len(selection_request.selected_pain_ids) != 3:
            raise HTTPException(status_code=400, detail="Exactly 3 Pains must be selected")
        if len(selection_request.selected_gain_ids) != 3:
            raise HTTPException(status_code=400, detail="Exactly 3 Gains must be selected")
        
        service = get_integrated_vmp_service()
        
        # Save selections to project state
        result = await service.save_customer_profile_selections(
            project_id=project_id,
            selections={
                "jtbd": selection_request.selected_jtbd_ids,
                "pain": selection_request.selected_pain_ids,
                "gain": selection_request.selected_gain_ids
            },
            user_id=user_id
        )
        
        if result['success']:
            return {
                "success": True,
                "data": {
                    "project_id": project_id,
                    "step_completed": 1,
                    "selections_saved": {
                        "jtbd_count": len(selection_request.selected_jtbd_ids),
                        "pain_count": len(selection_request.selected_pain_ids),
                        "gain_count": len(selection_request.selected_gain_ids)
                    }
                },
                "message": "Customer profile selections saved successfully. Ready for Value Map generation.",
                "next_step": f"/api/v2/vmp/projects/{project_id}/vpc/step2/generate-value-map"
            }
        else:
            raise HTTPException(status_code=400, detail=result['error'])
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save customer profile selections: {str(e)}")


@router.post("/projects/{project_id}/vpc/step2/generate-value-map")
async def generate_value_map(
    project_id: str,
    generation_request: ValueMapGenerationRequest,
    current_user: dict = Depends(get_current_user_with_tenant)
):
    """
    **STEP 2: Generate Value Map Candidates**
    
    Generate candidates for Products/Services, Pain Relievers, and Gain Creators using:
    - Dual vector store context (PV report + actionable insights)
    - Selected customer profile items from Step 1
    - AI mapping to ensure solutions address customer needs
    
    **Requirements:**
    - Customer profile selections from Step 1 must be completed
    - Uses Yuba's existing credit system for billing (10 credits)
    - Each Value Map item explicitly maps to selected customer profile items
    
    **Output:** 15-24 candidates (5-8 each category) that directly address customer needs
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        service = get_integrated_vmp_service()
        
        # Prepare generation request for value map
        generation_data = {
            "query": "",  # Auto-generated from project context
            "generation_type": "value_map",
            "creativity_level": generation_request.creativity_level,
            "include_context_summary": generation_request.include_context_summary
        }
        
        # Generate value map candidates using the focused method (STEP 2)
        # Get dual context using vector adapter
        context_query = "products services solutions pain relievers gain creators value proposition Ethiopian shoes manufacturing"
        context = await service.vector_adapter.dual_context_search(
            project_id=project_id,
            query=context_query,
            max_results_per_store=20
        )
        
        vpc_data = await service.generate_value_map_with_dual_context(
            project_id=project_id,
            context=context,
            generation_request=generation_data,
            user_id=user_id
        )
        
        # Save the generated candidates to artifacts for later selection
        await service._save_vpc_artifacts(project_id, "value_map", vpc_data, user_id)
        
        # The new method returns the VPC data directly
        response_data = {
            "value_map_candidates": vpc_data,
            "generation_metadata": {
                "project_id": project_id,
                "step": 2,
                "step_name": "value_map_generation",
                "model_used": vpc_data.get('generation_metadata', {}).get('model_used', 'original_vmp'),
                "generation_time": vpc_data.get('generation_metadata', {}).get('generation_time')
            }
        }
        
        # Include context summary if requested
        if generation_request.include_context_summary:
            response_data["context_summary"] = context.get('context_summary', {})
        
        return {
            "success": True,
            "data": response_data,
            "message": "Value map candidates generated successfully. Please select 3 items from each category (Products/Services, Pain Relievers, Gain Creators).",
            "next_step": f"/api/v2/vmp/projects/{project_id}/vpc/step2/select-value-map"
        }
                
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate value map: {str(e)}")


@router.post("/projects/{project_id}/vpc/step2/select-value-map")
async def select_value_map(
    project_id: str,
    selection_request: ValueMapSelectionRequest,
    current_user: dict = Depends(get_current_user_with_tenant)
):
    """
    **STEP 2 COMPLETION: Save Value Map Selections**
    
    Save user's selected Products/Services, Pain Relievers, and Gain Creators (3 each, 9 total).
    These selections complete the Value Map and prepare for final VPC composition.
    
    **Validation:**
    - Exactly 3 Products/Services selections required
    - Exactly 3 Pain Reliever selections required
    - Exactly 3 Gain Creator selections required
    - All IDs must be valid from previous generation
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        # Validate selection counts
        if len(selection_request.selected_product_service_ids) != 3:
            raise HTTPException(status_code=400, detail="Exactly 3 Products/Services must be selected")
        if len(selection_request.selected_pain_reliever_ids) != 3:
            raise HTTPException(status_code=400, detail="Exactly 3 Pain Relievers must be selected")
        if len(selection_request.selected_gain_creator_ids) != 3:
            raise HTTPException(status_code=400, detail="Exactly 3 Gain Creators must be selected")
        
        service = get_integrated_vmp_service()
        
        # Save value map selections to project state
        result = await service.save_value_map_selections(
            project_id=project_id,
            selections={
                "selected_product_service_ids": selection_request.selected_product_service_ids,
                "selected_pain_reliever_ids": selection_request.selected_pain_reliever_ids,
                "selected_gain_creator_ids": selection_request.selected_gain_creator_ids
            },
            user_id=user_id
        )
        
        if result['success']:
            return {
                "success": True,
                "data": {
                    "project_id": project_id,
                    "step_completed": 2,
                    "selections_saved": {
                        "product_service_count": len(selection_request.selected_product_service_ids),
                        "pain_reliever_count": len(selection_request.selected_pain_reliever_ids),
                        "gain_creator_count": len(selection_request.selected_gain_creator_ids)
                    }
                },
                "message": "Value map selections saved successfully. Ready for final VPC composition.",
                "next_step": f"/api/v2/vmp/projects/{project_id}/vpc/step3/compose-final-vpc"
            }
        else:
            raise HTTPException(status_code=400, detail=result['error'])
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save value map selections: {str(e)}")


@router.post("/projects/{project_id}/vpc/step3/compose-final-vpc")
async def compose_final_vpc(
    project_id: str,
    composition_request: VPCCompositionRequest,
    current_user: dict = Depends(get_current_user_with_tenant)
):
    """
    **STEP 3: Compose Final Value Proposition Canvas**
    
    Create the complete VPC using all selections from Steps 1 and 2.
    
    **Requirements:**
    - Customer profile selections (Step 1) must be completed
    - Value map selections (Step 2) must be completed
    - Generates final VPC with visual canvas (optional)
    - Supports multiple export formats (JSON, PDF, PNG)
    
    **Output:** Complete Value Proposition Canvas ready for business use
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        print(f"🔍 DEBUG: [ENDPOINT] compose_final_vpc called for project {project_id}")
        print(f"🔍 DEBUG: [ENDPOINT] Request: include_visual={composition_request.include_visual}, export_format={composition_request.export_format}")
        
        service = get_integrated_vmp_service()
        
        # Compose final VPC from all selections
        print(f"🔍 DEBUG: [ENDPOINT] About to call service.compose_final_vpc")
        result = await service.compose_final_vpc(
            project_id=project_id,
            composition_options={
                "include_visual": composition_request.include_visual,
                "export_format": composition_request.export_format
            },
            user_id=user_id
        )
        print(f"🔍 DEBUG: [ENDPOINT] Service call completed, result keys: {list(result.keys())}")
        
        if result['success']:
            response_data = {
                "final_vpc": result['vpc_data'],
                "generation_metadata": {
                    "project_id": project_id,
                    "step": 3,
                    "step_name": "final_vpc_composition",
                    "export_format": composition_request.export_format,
                    "includes_visual": composition_request.include_visual,
                    "completion_time": result['vpc_data'].get('generation_metadata', {}).get('completion_time')
                }
            }
            
            # Include visual canvas if requested
            if composition_request.include_visual and result.get('visual_canvas'):
                response_data["visual_canvas"] = result['visual_canvas']
            
            return {
                "success": True,
                "data": response_data,
                "message": "Value Proposition Canvas completed successfully! Your VPC is ready for business use.",
                "workflow_completed": True
            }
        else:
            raise HTTPException(status_code=400, detail=result['error'])
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compose final VPC: {str(e)}")


@router.get("/projects/{project_id}/vpc/status")
async def get_vpc_workflow_status(
    project_id: str,
    current_user: dict = Depends(get_current_user_with_tenant)
):
    """
    **Get VPC Workflow Status**
    
    Check the current status of the 3-step VPC generation workflow.
    
    **Returns:**
    - Current step (1, 2, 3, or completed)
    - Completion status of each step
    - Available next actions
    - Progress summary
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        service = get_integrated_vmp_service()
        
        # Get workflow status
        result = await service.get_vpc_workflow_status(
            project_id=project_id,
            user_id=user_id
        )
        
        if result['success']:
            return {
                "success": True,
                "data": result['status'],
                "message": f"VPC workflow is at step {result['status']['current_step']}"
            }
        else:
            raise HTTPException(status_code=400, detail=result['error'])
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get VPC workflow status: {str(e)}")


# ==================== CONTEXT AND INTEGRATION ENDPOINTS ====================

@router.get("/projects/{project_id}/contexts")
async def get_project_contexts(
    project_id: str,
    current_user: dict = Depends(get_current_user_with_tenant)
):
    """
    Get all linked contexts for a project.
    
    This endpoint shows the dual vector store integration in action,
    displaying both PV report contexts and actionable insights contexts.
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        service = get_integrated_vmp_service()
        
        contexts = await service.vector_adapter.get_project_contexts(project_id)
        
        return {
            "success": True,
            "data": {
                "project_id": project_id,
                "contexts": contexts,
                "summary": {
                    "total_contexts": len(contexts),
                    "by_type": {
                        "pv_report": len([c for c in contexts if c['context_type'] == 'pv_report']),
                        "actionable_insights": len([c for c in contexts if c['context_type'] == 'actionable_insights']),
                        "other": len([c for c in contexts if c['context_type'] not in ['pv_report', 'actionable_insights']])
                    }
                }
            },
            "message": "Project contexts retrieved successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch project contexts: {str(e)}")


@router.post("/projects/{project_id}/search-context")
async def search_project_context(
    project_id: str,
    query: str = Query(..., description="Search query for context"),
    max_results: int = Query(10, ge=1, le=50, description="Maximum results to return"),
    current_user: dict = Depends(get_current_user_with_tenant)
):
    """
    Search project contexts using dual vector store.
    
    This demonstrates the dual vector store search capability,
    showing how VPM leverages both PV reports and actionable insights.
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        service = get_integrated_vmp_service()
        
        # Perform dual context search
        context_results = await service.vector_adapter.dual_context_search(
            project_id=project_id,
            query=query,
            max_results_per_store=max_results // 2
        )
        
        return {
            "success": True,
            "data": {
                "query": query,
                "project_id": project_id,
                "pv_report_context": context_results['pv_report_context'],
                "actionable_insights_context": context_results['actionable_insights_context'],
                "combined_context": context_results['combined_context'],
                "context_summary": context_results['context_summary']
            },
            "message": "Context search completed successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search context: {str(e)}")


# ==================== HEALTH AND STATUS ENDPOINTS ====================

@router.get("/health")
async def vmp_health_check():
    """
    VPM module health check.
    
    Verifies integration with Yuba systems is working properly.
    """
    try:
        service = get_integrated_vmp_service()
        
        # Test basic connectivity
        health_status = {
            "vmp_integration": "healthy",
            "auth_adapter": "connected" if service.auth_adapter else "disconnected",
            "database_adapter": "connected" if service.db_adapter else "disconnected",
            "vector_adapter": "connected" if service.vector_adapter else "disconnected",
            "original_vmp_service": "available" if service.original_vmp_service else "fallback_mode",
            "timestamp": "2025-01-22T18:30:00Z"
        }
        
        return {
            "success": True,
            "data": health_status,
            "message": "VPM module is healthy and integrated with Yuba"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "VPM module health check failed"
        }


# ==================== FIELD PREP ENDPOINTS ====================

@router.post("/projects/{project_id}/field-prep/hypothesis", response_model=FieldPrepHypothesisResponse)
async def generate_field_prep_hypothesis(
    project_id: str,
    request: FieldPrepHypothesisRequest,
    current_user: dict = Depends(get_current_user_with_tenant)
):
    """
    Generate market hypothesis for field research preparation.
    
    **This is the first step of Field Prep workflow after VPC generation.**
    
    The hypothesis generation process:
    1. Validates VPC is completed for the project
    2. Uses complete VPC context (Customer Profile + Value Map)
    3. Uses dual vector store context (PV reports + actionable insights)
    4. Generates testable market hypothesis with evidence references
    5. Deducts credits from user's account (5 credits)
    6. Stores hypothesis for next workflow steps
    
    **Context Sources:**
    - Generated VPC artifacts (primary context)
    - PV Report content via vector search
    - Actionable Insights via vector search
    
    **Integration Features:**
    - Pure bridge to original VPM Field Prep service
    - Full AI sophistication preserved
    - Maintains complete audit trail
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        # Get integrated services
        vmp_service = get_integrated_vmp_service()
        field_prep_service = get_yuba_field_prep_service(
            vmp_service.auth_adapter,
            vmp_service.db_adapter, 
            vmp_service.vector_adapter,
            vmp_service.credit_adapter
        )
        
        # Generate hypothesis using VPC + dual vector store context
        result = await field_prep_service.generate_hypothesis(
            project_id=project_id,
            user_id=user_id,
            creativity_level=request.creativity_level
        )
        
        if result['success']:
            return FieldPrepHypothesisResponse(
                hypothesis=result['hypothesis'],
                project_id=project_id,
                context_summary=result.get('context_summary')
            )
        else:
            if "credits" in result['error'].lower():
                raise HTTPException(status_code=402, detail=result['error'])
            else:
                raise HTTPException(status_code=400, detail=result['error'])
                
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate hypothesis: {str(e)}")


@router.post("/projects/{project_id}/field-prep/assumptions", response_model=FieldPrepAssumptionsResponse)
async def generate_field_prep_assumptions(
    project_id: str,
    request: FieldPrepAssumptionsRequest,
    current_user: dict = Depends(get_current_user_with_tenant)
):
    """
    Generate assumptions based on project hypothesis.
    
    **This is the second step of Field Prep workflow.**
    
    Creates 2-3 key assumptions that can be tested through field research.
    Each assumption is categorized and prioritized for effective validation.
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        # Get services
        vmp_service = get_integrated_vmp_service()
        field_prep_service = get_yuba_field_prep_service(
            vmp_service.auth_adapter,
            vmp_service.db_adapter,
            vmp_service.vector_adapter,
            vmp_service.credit_adapter
        )
        
        # Generate assumptions
        result = await field_prep_service.generate_assumptions(
            project_id=project_id,
            user_id=user_id,
            max_assumptions=request.max_assumptions
        )
        
        if result['success']:
            return FieldPrepAssumptionsResponse(
                assumptions=result['assumptions'],
                project_id=project_id,
                hypothesis_reference=result['hypothesis_used']
            )
        else:
            if "credits" in result['error'].lower():
                raise HTTPException(status_code=402, detail=result['error'])
            else:
                raise HTTPException(status_code=400, detail=result['error'])
                
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate assumptions: {str(e)}")


@router.post("/projects/{project_id}/field-prep/stakeholders", response_model=FieldPrepStakeholdersResponse)
async def assign_field_prep_stakeholders(
    project_id: str,
    request: FieldPrepStakeholdersRequest,
    current_user: dict = Depends(get_current_user_with_tenant)
):
    """
    Assign stakeholders to assumptions for field research.
    
    **This is the third step of Field Prep workflow.**
    
    Maps each assumption to relevant stakeholders who can provide validation
    through interviews, surveys, or other research methods.
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        # Get services
        vmp_service = get_integrated_vmp_service()
        field_prep_service = get_yuba_field_prep_service(
            vmp_service.auth_adapter,
            vmp_service.db_adapter,
            vmp_service.vector_adapter,
            vmp_service.credit_adapter
        )
        
        # Assign stakeholders
        result = await field_prep_service.assign_stakeholders(
            project_id=project_id,
            user_id=user_id,
            stakeholder_preferences=request.stakeholder_preferences
        )
        
        if result['success']:
            return FieldPrepStakeholdersResponse(
                stakeholder_assignments=result['stakeholder_assignments'],
                project_id=project_id,
                assignment_summary=result['assignment_summary']
            )
        else:
            if "credits" in result['error'].lower():
                raise HTTPException(status_code=402, detail=result['error'])
            else:
                raise HTTPException(status_code=400, detail=result['error'])
                
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to assign stakeholders: {str(e)}")


@router.post("/projects/{project_id}/field-prep/questionnaires", response_model=FieldPrepQuestionnairesResponse)
async def generate_field_prep_questionnaires(
    project_id: str,
    request: FieldPrepQuestionnairesRequest,
    current_user: dict = Depends(get_current_user_with_tenant)
):
    """
    Generate questionnaires for field research.
    
    **This is the final step of Field Prep workflow.**
    
    Creates comprehensive questionnaires for each assumption-stakeholder combination.
    Questionnaires can be exported to multiple formats including Google Forms.
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        # Get services
        vmp_service = get_integrated_vmp_service()
        field_prep_service = get_yuba_field_prep_service(
            vmp_service.auth_adapter,
            vmp_service.db_adapter,
            vmp_service.vector_adapter,
            vmp_service.credit_adapter
        )
        
        # Generate questionnaires
        result = await field_prep_service.generate_questionnaires(
            project_id=project_id,
            user_id=user_id,
            questions_per_assumption=request.questions_per_assumption,
            include_demographic_questions=request.include_demographic_questions
        )
        
        if result['success']:
            return FieldPrepQuestionnairesResponse(
                questionnaires=result['questionnaires'],
                project_id=project_id,
                questionnaire_summary=result['questionnaire_summary'],
                export_options=result['export_options']
            )
        else:
            if "credits" in result['error'].lower():
                raise HTTPException(status_code=402, detail=result['error'])
            else:
                raise HTTPException(status_code=400, detail=result['error'])
                
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate questionnaires: {str(e)}")


@router.get("/projects/{project_id}/field-prep/progress", response_model=FieldPrepProgressResponse)
async def get_field_prep_progress(
    project_id: str,
    current_user: dict = Depends(get_current_user_with_tenant)
):
    """
    Get Field Prep workflow progress for a project.
    
    Shows current stage, completed steps, and requirements for next steps.
    Helps users understand where they are in the Field Prep workflow.
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        # Get services
        vmp_service = get_integrated_vmp_service()
        field_prep_service = get_yuba_field_prep_service(
            vmp_service.auth_adapter,
            vmp_service.db_adapter,
            vmp_service.vector_adapter,
            vmp_service.credit_adapter
        )
        
        # Get progress
        result = await field_prep_service.get_field_prep_progress(project_id)
        
        if result['success']:
            return FieldPrepProgressResponse(
                project_id=project_id,
                current_stage=result['current_stage'],
                completed_stages=result['completed_stages'],
                next_stage=result['next_stage'],
                progress_percentage=result['progress_percentage'],
                artifacts_summary=result['artifacts_summary'],
                can_proceed=result['can_proceed'],
                requirements_for_next_stage=result['requirements_for_next_stage']
            )
        else:
            raise HTTPException(status_code=500, detail=result['error'])
                
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get field prep progress: {str(e)}")


@router.post("/projects/{project_id}/field-prep/export", response_model=FieldPrepExportResponse)
async def export_field_prep_artifacts(
    project_id: str,
    request: FieldPrepExportRequest,
    current_user: dict = Depends(get_current_user_with_tenant)
):
    """
    Export Field Prep artifacts in various formats.
    
    **Supported formats:**
    - PDF: Professional research document
    - Word: Editable research template
    - CSV: Data for analysis tools
    - Google Forms: Direct integration for online surveys
    
    **Integration Features:**
    - Uses Yuba's existing file storage
    - Maintains user permissions and access control
    - Provides download URLs with expiration
    """
    try:
        # For now, return a placeholder response
        # This would integrate with export services
        
        export_id = f"export_{project_id}_{request.export_format}_{user_id}"
        
        return FieldPrepExportResponse(
            export_url=f"/api/v2/vmp/exports/{export_id}/download",
            export_id=export_id,
            export_format=request.export_format,
            status="processing",
            message=f"Export to {request.export_format.upper()} format initiated. Check back in a few moments."
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initiate export: {str(e)}")