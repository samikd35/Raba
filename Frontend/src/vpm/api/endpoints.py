"""
VPM API Endpoints - Fixed Version with Multi-Persona Support
"""

import uuid
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# Import auth and core services
from src.mint.api.auth_v2.utils import get_current_user
from src.mint.api.credit.service import (
    CreditService,
    InsufficientCreditsError,
    InvalidConsumptionRequest,
)

# Import cache decorators and invalidation service
from src.mint.api.cache.decorators import cached_query
from src.mint.api.cache.invalidation_service import (
    get_invalidation_service,
    WriteOperation,
)

from ..models.field_prep import (
    FieldPrepAssumptionsRequest,
    FieldPrepAssumptionsResponse,
    FieldPrepExportRequest,
    FieldPrepExportResponse,
    FieldPrepHypothesisRequest,
    FieldPrepHypothesisResponse,
    FieldPrepProgressResponse,
    FieldPrepQuestionnairesRequest,
    FieldPrepQuestionnairesResponse,
    FieldPrepStage,
    CustomerProfileEditRequest,
    CustomerProfileEditResponse,
    PersonaEditRequest,
    PersonaEditResponse,
    PersonaAddRequest,
    PersonaAddResponse,
    PersonaDeleteRequest,
    PersonaDeleteResponse,
    HypothesisEditRequest,
    HypothesisEditResponse,
    AssumptionsEditRequest,
    AssumptionsEditResponse,
    QuestionnairesEditRequest,
    QuestionnairesEditResponse,
)
from ..services.field_prep_service import get_yuba_field_prep_service

# Import our integration service
from ..services.integrated_vmp_service import get_integrated_vmp_service

router = APIRouter(prefix="/api/v2/vmp", tags=["VPM"])

logger = logging.getLogger(__name__)

credit_service = CreditService()

# Helper function to get tenant ID from user ID


# Request Models
class CustomerProfileGenerationRequest(BaseModel):
    """Request for Customer Profile generation (Step 1)"""

    creativity_level: float = Field(
        0.7, ge=0.0, le=1.0, description="AI creativity level"
    )
    include_context_summary: bool = Field(
        True, description="Include context summary in response"
    )


class VPCImageRequest(BaseModel):
    """Request to save VPC image URL"""

    vpc_image_url: str = Field(..., description="URL or path to the VPC image")


class CreateProjectRequest(BaseModel):
    """Request to create a new VMP project"""

    name: str = Field(..., min_length=1, max_length=100, description="Project name")
    pv_report_id: str = Field(
        ..., description="ID of the Problem Validation report to base this project on"
    )


class UpdateProjectRequest(BaseModel):
    """Request to update VMP project details - accepts either direct or wrapped format"""

    name: Optional[str] = Field(
        None, min_length=1, max_length=100, description="Project name (direct format)"
    )
    description: Optional[str] = Field(
        None, max_length=500, description="Project description (direct format)"
    )
    data: Optional[Dict[str, Any]] = Field(
        None, description="Wrapped format with data.name and data.description"
    )

    def get_update_fields(self) -> Dict[str, str]:
        """Extract update fields from either format"""
        update_fields = {}

        # Try direct format first
        if self.name is not None:
            update_fields["name"] = self.name
        if self.description is not None:
            update_fields["description"] = self.description

        # Try wrapped format if no direct fields
        if not update_fields and self.data is not None:
            if "name" in self.data and self.data["name"]:
                update_fields["name"] = self.data["name"]
            if "description" in self.data and self.data["description"]:
                update_fields["description"] = self.data["description"]

        return update_fields


class MoveProjectRequest(BaseModel):
    """Request to move a VMP project to another tenant workspace"""

    target_tenant_id: str = Field(
        ..., description="Target tenant ID to move the project into"
    )


class ProblemStatementUpdateRequest(BaseModel):
    """Request to update refined problem statement - accepts either direct or wrapped format"""

    problem_statement: Optional[str] = Field(
        None,
        min_length=1,
        max_length=1000,
        description="Refined problem statement (direct format)",
    )
    data: Optional[Dict[str, Any]] = Field(
        None, description="Wrapped format with data.problem_statement"
    )

    def get_problem_statement(self) -> str:
        """Extract problem statement from either format"""
        # Try direct format first
        if self.problem_statement is not None:
            return self.problem_statement

        # Try wrapped format
        if self.data is not None and "problem_statement" in self.data:
            return self.data["problem_statement"]

        # If neither format provided
        raise ValueError(
            "Must provide either 'problem_statement' or 'data.problem_statement'"
        )


class CustomerProfileSelectionRequest(BaseModel):
    """Request for Customer Profile selections (Step 1 completion)"""

    # Support both single and multi-persona selection formats
    selected_jtbd_ids: Optional[List[str]] = Field(
        None, description="Selected Jobs-to-be-Done IDs (legacy single persona)"
    )
    selected_pain_ids: Optional[List[str]] = Field(
        None, description="Selected Pain IDs (legacy single persona)"
    )
    selected_gain_ids: Optional[List[str]] = Field(
        None, description="Selected Gain IDs (legacy single persona)"
    )

    # Multi-persona selection format
    persona_selections: Optional[Dict[str, Dict[str, List[str]]]] = Field(
        None,
        description="Persona-specific selections: {'P1': {'jtbd': [...], 'pain': [...], 'gain': [...]}, 'P2': {...}}",
    )


class ValueMapGenerationRequest(BaseModel):
    """Request for Value Map generation (Step 2)"""

    creativity_level: float = Field(
        0.7, ge=0.0, le=1.0, description="AI creativity level"
    )
    include_context_summary: bool = Field(
        True, description="Include context summary in response"
    )


class ValueMapSelectionRequest(BaseModel):
    """Request for Value Map selections (Step 2 completion)"""

    selected_product_service_ids: List[str] = Field(
        ..., description="Selected Products/Services IDs (max 3)"
    )
    selected_pain_reliever_ids: List[str] = Field(
        ..., description="Selected Pain Reliever IDs (max 3)"
    )
    selected_gain_creator_ids: List[str] = Field(
        ..., description="Selected Gain Creator IDs (max 3)"
    )


class VPCCompositionRequest(BaseModel):
    """Request for final VPC composition (Step 3)"""

    include_visual: bool = Field(True, description="Include visual VPC canvas")
    export_format: str = Field("json", description="Export format (json, png, pdf)")
    include_context_summary: bool = Field(True, description="Include context summary")


class VPCv2GenerationRequest(BaseModel):
    """Request for VPC v2 generation (customer profile or value map)"""

    creativity_level: float = Field(
        0.7, ge=0.0, le=1.0, description="AI creativity level"
    )
    include_context_summary: bool = Field(
        True, description="Include context summary in response"
    )


# ==================== REPORT DISCOVERY ENDPOINTS ====================


@router.get("/reports")
async def browse_pv_reports(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(35, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(
        None, description="Search query for report titles/descriptions"
    ),
    status_filter: Optional[str] = Query(None, description="Filter by report status"),
    current_user: dict = Depends(get_current_user),
):
    """Browse available Problem Validation reports for VMP project creation."""
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        if not tenant_id:
            raise HTTPException(status_code=400, detail="User tenant not found")

        service = get_integrated_vmp_service()
        result = await service.browse_pv_reports(
            tenant_id=tenant_id,
            user_id=user_id,
            page=page,
            page_size=page_size,
            search=search,
        )

        if result["success"]:
            return {
                "success": True,
                "data": {
                    "reports": result["reports"],
                    "total_count": result["total_count"],
                    "page": page,
                    "page_size": page_size,
                    "has_next": result.get("has_next", False),
                },
                "message": f"Found {len(result['reports'])} reports",
            }
        else:
            raise HTTPException(status_code=400, detail=result["error"])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch reports: {str(e)}"
        )


@router.get("/reports/{report_id}")
async def get_report_detail(
    report_id: str, current_user: dict = Depends(get_current_user)
):
    """Get detailed information about a specific PV report."""
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        if not tenant_id:
            raise HTTPException(status_code=400, detail="User tenant not found")

        service = get_integrated_vmp_service()
        result = await service.get_report_detail(report_id, tenant_id, user_id)

        if result["success"]:
            return {
                "success": True,
                "data": result["report"],
                "message": "Report details retrieved successfully",
            }
        else:
            raise HTTPException(status_code=404, detail=result["error"])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch report details: {str(e)}"
        )


# ==================== PROJECT MANAGEMENT ENDPOINTS ====================


@router.post("/projects")
async def create_vmp_project(
    project_request: CreateProjectRequest,
    current_user: dict = Depends(get_current_user),
):
    """Create a new VMP project from a Problem Validation report."""
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        if not tenant_id:
            raise HTTPException(status_code=400, detail="User tenant not found")

        service = get_integrated_vmp_service()
        project_data = {
            "name": project_request.name,
            "pv_report_id": project_request.pv_report_id,
            "tenant_id": tenant_id,
        }

        result = await service.create_vmp_project(project_data, user_id)

        if result["success"]:
            # Invalidate VMP project list caches after successful creation (Requirement 5.5)
            invalidation_service = get_invalidation_service()
            if invalidation_service:
                await invalidation_service.on_write(
                    table_name="vmp_projects",
                    operation=WriteOperation.CREATE,
                    record_id=result["project"]["id"],
                    tenant_id=tenant_id,
                    user_id=user_id,
                    background=True,
                )

            return {
                "success": True,
                "data": {
                    "project": result["project"],
                    "next_step": f"/api/v2/vmp/projects/{result['project']['id']}/identify-personas",
                },
                "message": result["message"],
            }
        else:
            if "credits" in result["error"].lower():
                raise HTTPException(status_code=402, detail=result["error"])
            else:
                raise HTTPException(status_code=400, detail=result["error"])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create project: {str(e)}"
        )


@router.get("/projects")
@cached_query(
    "vmp_projects_list", ttl=180, user_specific=True
)  # 3-minute TTL, bypass with X-Skip-Cache header
async def get_user_projects(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(35, ge=1, le=100, description="Items per page"),
    status_filter: Optional[str] = Query(None, description="Filter by project status"),
    search: Optional[str] = Query(
        None, description="Search query for project names/descriptions"
    ),
    current_user: dict = Depends(get_current_user),
):
    """Get user's VMP projects with pagination and filtering."""
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        if not tenant_id:
            raise HTTPException(status_code=400, detail="User tenant not found")

        service = get_integrated_vmp_service()
        result = await service.get_user_projects(
            tenant_id=tenant_id,
            user_id=user_id,
            page=page,
            page_size=page_size,
            status_filter=status_filter,
            search=search,
        )

        if result["success"]:
            return {
                "success": True,
                "data": {
                    "projects": result["projects"],
                    "total_count": result["total_count"],
                    "page": page,
                    "page_size": page_size,
                    "has_next": result.get("has_next", False),
                },
                "message": f"Found {len(result['projects'])} projects",
            }
        else:
            raise HTTPException(status_code=400, detail=result["error"])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch projects: {str(e)}"
        )


@router.get("/projects/completed/value-maps")
@cached_query(
    "vmp_completed_value_maps", ttl=300, user_specific=True
)  # 5-minute TTL (Requirement 5.3)
async def get_value_map_completed_projects(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(35, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(
        None, description="Search query for project names/descriptions"
    ),
    include_metadata: bool = Query(
        True, description="Include value map metadata (persona statuses, timestamps)"
    ),
    current_user: dict = Depends(get_current_user),
):
    """
    Get VMP projects that have completed Value Map selections (Module 2 final step).

    **These projects are READY FOR MODULE 3 (VPS v1 generation).**

    This endpoint returns only projects where:
    - At least 1 persona exists
    - ALL personas have value_map_selections in vpc_v2_data
    - Each value_map_selections has 3+ items in:
      - products_services
      - pain_relievers
      - gain_creators

    Use case: Show projects ready for Value Proposition Statement generation in Module 3.

    Response includes:
    - All standard project fields
    - Value map metadata (if include_metadata=True):
      - Personas count
      - Persona completion statuses
      - Value map completion timestamp
      - Module 3 readiness flag
      - VPS v1 generation status

    Next step after getting these projects:
    - Call `POST /api/v2/mvp/projects/{project_id}/vps/v1/generate` to generate VPS v1
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        if not tenant_id:
            raise HTTPException(status_code=400, detail="User tenant not found")

        service = get_integrated_vmp_service()
        result = await service.get_value_map_completed_projects(
            tenant_id=tenant_id,
            user_id=user_id,
            page=page,
            page_size=page_size,
            search=search,
            include_metadata=include_metadata,
        )

        if result["success"]:
            return {
                "success": True,
                "data": {
                    "projects": result["projects"],
                    "total_count": result["total_count"],
                    "page": page,
                    "page_size": page_size,
                    "has_next": result.get("has_next", False),
                    "filter_applied": "value_maps_completed",
                },
                "message": f"Found {len(result['projects'])} projects ready for VPS v1 generation (Module 3)",
            }
        else:
            raise HTTPException(status_code=400, detail=result["error"])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch value-map-completed projects: {str(e)}",
        )


@router.get("/projects/completed/questionnaires")
@cached_query(
    "vmp_completed_questionnaires", ttl=300, user_specific=True
)  # 5-minute TTL (Requirement 5.2)
async def get_questionnaire_completed_projects(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(35, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(
        None, description="Search query for project names/descriptions"
    ),
    include_metadata: bool = Query(
        True, description="Include questionnaire metadata (counts, timestamps)"
    ),
    current_user: dict = Depends(get_current_user),
):
    """
    Get VMP projects that have completed the questionnaire generation step.

    This endpoint returns only projects where:
    - field_prep_data.stage = 'questionnaires_completed'
    - field_prep_data.questionnaires array exists and is not empty

    Note: We filter by stage only (not current_step) because current_step can be
    overwritten by other workflow steps like customer_profile selections.

    These projects are ready for field research execution.

    Response includes:
    - All standard project fields
    - Questionnaire metadata (if include_metadata=True):
      - Total question count
      - Questions per persona breakdown
      - Generation timestamp
      - Assumptions count
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        if not tenant_id:
            raise HTTPException(status_code=400, detail="User tenant not found")

        service = get_integrated_vmp_service()
        result = await service.get_questionnaire_completed_projects(
            tenant_id=tenant_id,
            user_id=user_id,
            page=page,
            page_size=page_size,
            search=search,
            include_metadata=include_metadata,
        )

        if result["success"]:
            return {
                "success": True,
                "data": {
                    "projects": result["projects"],
                    "total_count": result["total_count"],
                    "page": page,
                    "page_size": page_size,
                    "has_next": result.get("has_next", False),
                    "filter_applied": "questionnaires_completed",
                },
                "message": f"Found {len(result['projects'])} projects with completed questionnaires",
            }
        else:
            raise HTTPException(status_code=400, detail=result["error"])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch questionnaire-completed projects: {str(e)}",
        )


@router.get("/projects/completed/vps-v2")
@cached_query(
    "vmp_completed_vps_v2", ttl=300, user_specific=True
)  # 5-minute TTL (Requirement 5.4)
async def get_vps_v2_completed_projects(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(35, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(
        None, description="Search query for project names/descriptions"
    ),
    include_metadata: bool = Query(
        True, description="Include VPS v2 metadata (counts, timestamps)"
    ),
    current_user: dict = Depends(get_current_user),
):
    """
    Get VMP projects that have completed VPS v2 generation (Module 3 refinement).

    **These projects are READY FOR AMRG (MVP Requirements Generator).**

    This endpoint returns only projects where:
    - mvp_data.vps_v2 exists and is not empty
    - Project has completed Module 3 refinement workflow

    Use case: Show projects ready for PRD generation in AMRG module.

    Response includes:
    - All standard project fields
    - VPS v2 metadata (if include_metadata=True):
      - VPS v2 count (per persona)
      - VPS version
      - VPS generation timestamp
      - BMC v2 existence flag
      - Solution Critique existence flag
      - AMRG readiness flag (all 5 artifacts present)
      - Module 3 completion status

    Next step after getting these projects:
    - Call `POST /api/v2/mvp/projects/{project_id}/amrg/runs` to start PRD generation
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        if not tenant_id:
            raise HTTPException(status_code=400, detail="User tenant not found")

        service = get_integrated_vmp_service()
        result = await service.get_vps_v2_completed_projects(
            tenant_id=tenant_id,
            user_id=user_id,
            page=page,
            page_size=page_size,
            search=search,
            include_metadata=include_metadata,
        )

        if result["success"]:
            return {
                "success": True,
                "data": {
                    "projects": result["projects"],
                    "total_count": result["total_count"],
                    "page": page,
                    "page_size": page_size,
                    "has_next": result.get("has_next", False),
                    "filter_applied": "vps_v2_completed",
                },
                "message": f"Found {len(result['projects'])} projects with completed VPS v2 (AMRG ready)",
            }
        else:
            raise HTTPException(status_code=400, detail=result["error"])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch VPS v2 completed projects: {str(e)}",
        )


@router.get("/sidebar-status")
@cached_query(
    "vmp_sidebar_status", ttl=120, user_specific=True
)  # 2-minute TTL, auto-invalidated on project updates
async def get_sidebar_unlock_status(
    request: Request, current_user: dict = Depends(get_current_user)
):
    """
    📊 SIDEBAR STATUS: Get unified workflow completion status for sidebar unlock logic.

    This endpoint returns the completion status of ALL workflow stages across all projects
    for the current tenant. Used to determine which sidebar menu items should be unlocked.

    **Workflow Stages (in order):**
    1. project_created - Project exists
    2. persona_created - At least one persona defined
    3. customer_profile_v1_completed - VPC v1 customer profile done
    4. hypothesis_completed - Hypotheses generated
    5. assumptions_completed - Assumptions generated
    6. questionnaires_completed - Questionnaires generated
    7. market_research_completed - Market research analysis done
    8. customer_profile_v2_completed - VPC v2 customer profile done
    9. value_map_completed - Value map selections saved
    10. vps_v1_completed - VPS v1 generated
    11. bmc_v1_completed - BMC v1 generated
    12. solution_critique_completed - Solution critique done
    13. vps_v2_completed - VPS v2 generated (refinement)
    14. bmc_v2_completed - BMC v2 generated (refinement)
    15. mvp_requirements_completed - MVP requirements (PRD) generated

    **Response:**
    - `has_projects`: True if tenant has any VMP projects
    - `[stage_name]`: True if ANY project has completed that stage
    - `max_level`: Highest completed level across all projects (1-15)

    **Caching:**
    - TTL: 2 minutes (auto-refresh)
    - Auto-invalidated on project updates
    - Use `X-Skip-Cache: true` header to bypass cache

    **Use Case:**
    Frontend sidebar uses this to show/hide or enable/disable menu items
    based on workflow progression.
    """
    try:
        tenant_id = current_user["tenant_id"]
        if not tenant_id:
            raise HTTPException(status_code=400, detail="User tenant not found")

        from ..services.workflow_status_service import get_workflow_status_service

        workflow_service = get_workflow_status_service()

        unlock_status = workflow_service.get_sidebar_unlock_status(tenant_id=tenant_id)

        return {"success": True, "data": unlock_status}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch sidebar status: {str(e)}"
        )


@router.get("/projects/{project_id}/workflow-status")
async def get_project_workflow_status(
    project_id: str, current_user: dict = Depends(get_current_user)
):
    """
    📊 PROJECT WORKFLOW STATUS: Get workflow completion status for a specific project.

    Returns detailed workflow status for a single project, including:
    - Completion flags for each stage
    - Timestamps for when each stage was completed
    - Max completed level
    - Last updated timestamp

    **Use Case:**
    Show progress indicators on project detail pages.
    """
    try:
        tenant_id = current_user["tenant_id"]
        if not tenant_id:
            raise HTTPException(status_code=400, detail="User tenant not found")

        from ..services.workflow_status_service import get_workflow_status_service

        workflow_service = get_workflow_status_service()

        status = workflow_service.get_workflow_status(
            project_id=project_id, tenant_id=tenant_id
        )

        if status is None:
            raise HTTPException(status_code=404, detail="Project not found")

        return {
            "success": True,
            "data": {"project_id": project_id, "workflow_status": status},
            "message": "Project workflow status retrieved",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch project workflow status: {str(e)}"
        )


@router.get("/projects/latest")
@cached_query(
    "vmp_latest_projects", ttl=120, user_specific=True
)  # 2-minute TTL, bypass with X-Skip-Cache header
async def get_latest_projects(
    request: Request,
    limit: int = Query(
        6, ge=1, le=10, description="Number of projects to return (max 10)"
    ),
    current_user: dict = Depends(get_current_user),
):
    """
    🚀 FAST: Get the latest VMP projects ordered by most recently updated.

    **Optimized for dashboard/quick access:**
    - Minimal data returned (no heavy JSONB fields)
    - Single direct query with LIMIT
    - Cached for 2 minutes
    - No pagination overhead

    Use case: Dashboard widgets, recent projects list, quick navigation.

    Response includes per project:
    - id, name, problem_statement
    - status, current_step
    - created_at, updated_at
    - personas_count
    """
    try:
        tenant_id = current_user["tenant_id"]
        if not tenant_id:
            raise HTTPException(status_code=400, detail="User tenant not found")

        service = get_integrated_vmp_service()
        result = await service.get_latest_projects(tenant_id=tenant_id, limit=limit)

        if result["success"]:
            return {
                "success": True,
                "data": {
                    "projects": result["projects"],
                    "count": result["count"],
                    "limit": limit,
                },
                "message": f"Fetched {result['count']} latest projects",
            }
        else:
            raise HTTPException(status_code=400, detail=result["error"])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch latest projects: {str(e)}"
        )


@router.get("/projects/{project_id}")
async def get_project_detail(
    project_id: str, current_user: dict = Depends(get_current_user)
):
    """Get detailed information about a specific VMP project."""
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        if not tenant_id:
            raise HTTPException(status_code=400, detail="User tenant not found")

        service = get_integrated_vmp_service()
        result = await service.get_project_detail(project_id, tenant_id, user_id)

        if result["success"]:
            return {
                "success": True,
                "data": result["project"],
                "message": "Project details retrieved successfully",
            }
        else:
            raise HTTPException(status_code=404, detail=result["error"])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch project details: {str(e)}"
        )


@router.get("/projects/{project_id}/problem-statement")
async def get_project_problem_statement(
    project_id: str, current_user: dict = Depends(get_current_user)
):
    """
    Get the refined problem statement for a VMP project.

    The problem statement is automatically extracted from the PV report's executive summary
    during project creation and represents the validated problem that the VPM workflow addresses.
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        if not tenant_id:
            raise HTTPException(status_code=400, detail="User tenant not found")

        # Get database adapter
        from ..adapters.database_adapter import get_yuba_database_adapter

        db_adapter = get_yuba_database_adapter()

        # Get project to verify access
        project = await db_adapter.get_vmp_project(project_id, tenant_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Get problem statement
        problem_statement = await db_adapter.get_refined_problem_statement(project_id)

        if not problem_statement:
            raise HTTPException(
                status_code=404,
                detail="Problem statement not available for this project",
            )

        return {
            "success": True,
            "data": {
                "project_id": project_id,
                "problem_statement": problem_statement,
                "source": "executive_summary",
                "extraction_method": "first_sentences",
            },
            "message": "Problem statement retrieved successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch problem statement: {str(e)}"
        )


@router.put("/projects/{project_id}/problem-statement")
async def update_project_problem_statement(
    project_id: str,
    update_request: ProblemStatementUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Update the refined problem statement for a VMP project.

    Allows users to manually refine or edit the automatically extracted problem statement.

    Accepts either format:
    1. Direct: {"problem_statement": "..."}
    2. Wrapped: {"data": {"problem_statement": "..."}} (same as GET response)
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        if not tenant_id:
            raise HTTPException(status_code=400, detail="User tenant not found")

        # Extract problem statement from either format
        try:
            problem_statement = update_request.get_problem_statement()
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

        # Validate problem statement
        if not problem_statement or not problem_statement.strip():
            raise HTTPException(
                status_code=422, detail="Problem statement cannot be empty"
            )

        if len(problem_statement) > 1000:
            raise HTTPException(
                status_code=422,
                detail="Problem statement must be less than 1000 characters",
            )

        # Get database adapter
        from ..adapters.database_adapter import get_yuba_database_adapter

        db_adapter = get_yuba_database_adapter()

        # Verify project exists and user has access
        project = await db_adapter.get_vmp_project(project_id, tenant_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        if project.get("user_id") != user_id:
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to update this project",
            )

        # Save updated problem statement
        success = await db_adapter.save_refined_problem_statement(
            project_id=project_id,
            problem_statement=problem_statement.strip(),
            user_id=user_id,
        )

        if not success:
            raise HTTPException(
                status_code=500, detail="Failed to update problem statement"
            )

        return {
            "success": True,
            "data": {
                "project_id": project_id,
                "problem_statement": problem_statement.strip(),
                "updated_at": datetime.utcnow().isoformat(),
            },
            "message": "Problem statement updated successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to update problem statement: {str(e)}"
        )


@router.put("/projects/{project_id}")
async def update_project_details(
    project_id: str,
    update_request: UpdateProjectRequest,
    current_user: dict = Depends(get_current_user),
):
    """Update VMP project details (name and/or description).

    Accepts either format:
    1. Direct: {"name": "...", "description": "..."}
    2. Wrapped: {"data": {"name": "...", "description": "..."}} (same as GET response)

    Partial updates supported - only provide fields you want to change.
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        if not tenant_id:
            raise HTTPException(status_code=400, detail="User tenant not found")

        # Extract update fields from either format
        update_data = update_request.get_update_fields()

        # Check if at least one field is provided
        if not update_data:
            raise HTTPException(
                status_code=422,
                detail="At least one field (name or description) must be provided",
            )

        service = get_integrated_vmp_service()

        # Get current project to verify ownership
        project_result = await service.get_project_detail(
            project_id, tenant_id, user_id
        )
        if not project_result["success"]:
            raise HTTPException(status_code=404, detail="Project not found")

        # Verify user owns the project
        project = project_result["project"]
        if project.get("user_id") != user_id:
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to update this project",
            )

        # Update project in database
        update_data["updated_at"] = "now()"

        # CRITICAL FIX: Removed user_id filter to enable team collaboration
        response = (
            service.db_adapter.supabase.client.table("vmp_projects")
            .update(update_data)
            .eq("id", project_id)
            .execute()
        )

        if response.data:
            # Invalidate VMP project list caches after successful update (Requirement 5.5)
            invalidation_service = get_invalidation_service()
            if invalidation_service:
                await invalidation_service.on_write(
                    table_name="vmp_projects",
                    operation=WriteOperation.UPDATE,
                    record_id=project_id,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    background=True,
                )

            # Get updated project
            updated_result = await service.get_project_detail(
                project_id, tenant_id, user_id
            )

            return {
                "success": True,
                "data": updated_result["project"],
                "message": "Project details updated successfully",
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to update project")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to update project: {str(e)}"
        )


@router.post("/projects/{project_id}/move")
async def move_project(
    project_id: str,
    move_request: MoveProjectRequest,
    current_user: dict = Depends(get_current_user),
):
    """Move a VMP project to another tenant workspace.

    This updates only the project's tenant_id (Option 1).
    Related documents, reports, and chunks are not moved.
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user.get("tenant_id")
        if not tenant_id:
            raise HTTPException(status_code=400, detail="User tenant not found")

        target_tenant_id = move_request.target_tenant_id
        if target_tenant_id == tenant_id:
            raise HTTPException(
                status_code=400,
                detail="Target tenant must be different from current tenant",
            )

        logger.info(
            "[MOVE_PROJECT] user_id=%s project_id=%s from_tenant=%s to_tenant=%s",
            user_id,
            project_id,
            tenant_id,
            target_tenant_id,
        )

        service = get_integrated_vmp_service()
        project_result = await service.get_project_detail(
            project_id, tenant_id, user_id
        )
        if not project_result.get("success"):
            raise HTTPException(status_code=404, detail="Project not found")

        project = project_result["project"]
        if project.get("user_id") != user_id:
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to move this project",
            )

        logger.info(
            "[MOVE_PROJECT] project_owner=%s current_tenant=%s",
            project.get("user_id"),
            project.get("tenant_id"),
        )

        from src.mint.api.system.core.supabase_client import get_service_role_client

        supabase = get_service_role_client()
        target_membership = (
            supabase.client.table("tenant_memberships")
            .select("id")
            .eq("tenant_id", target_tenant_id)
            .eq("user_id", user_id)
            .eq("is_active", True)
            .limit(1)
            .execute()
        )

        if not target_membership.data:
            raise HTTPException(
                status_code=403,
                detail="You are not a member of the target workspace",
            )

        logger.info(
            "[MOVE_PROJECT] target membership verified user_id=%s tenant_id=%s",
            user_id,
            target_tenant_id,
        )

        desired_name = project.get("name")
        resolved_name = desired_name
        if desired_name:
            name_conflict = (
                supabase.client.table("vmp_projects")
                .select("id")
                .eq("tenant_id", target_tenant_id)
                .eq("name", desired_name)
                .limit(1)
                .execute()
            )
            if name_conflict.data:
                logger.info(
                    "[MOVE_PROJECT] name conflict detected name=%s target_tenant=%s",
                    desired_name,
                    target_tenant_id,
                )
                suffix_index = 1
                while True:
                    suffix = (
                        " (moved)" if suffix_index == 1 else f" (moved {suffix_index})"
                    )
                    candidate_name = f"{desired_name}{suffix}"
                    candidate_conflict = (
                        supabase.client.table("vmp_projects")
                        .select("id")
                        .eq("tenant_id", target_tenant_id)
                        .eq("name", candidate_name)
                        .limit(1)
                        .execute()
                    )
                    if not candidate_conflict.data:
                        resolved_name = candidate_name
                        logger.info(
                            "[MOVE_PROJECT] resolved name conflict: %s",
                            resolved_name,
                        )
                        break
                    suffix_index += 1

        target_org_response = (
            supabase.client.table("org_individuals")
            .select("organization_id")
            .eq("individual_tenant_id", target_tenant_id)
            .limit(1)
            .execute()
        )
        if not target_org_response.data:
            target_org_response = (
                supabase.client.table("org_teams")
                .select("organization_id")
                .eq("team_id", target_tenant_id)
                .limit(1)
                .execute()
            )
        if target_org_response.data:
            organization_id = target_org_response.data[0].get("organization_id")
            if organization_id:
                try:
                    audit_payload = {
                        "organization_id": organization_id,
                        "accessed_by_user_id": user_id,
                        "target_user_id": project.get("user_id"),
                        "project_id": project_id,
                        "access_type": "edit",
                        "metadata": {
                            "action": "move",
                            "from_tenant_id": tenant_id,
                            "to_tenant_id": target_tenant_id,
                        },
                    }
                    logger.info(
                        "[MOVE_PROJECT] audit insert org_id=%s payload=%s",
                        organization_id,
                        audit_payload,
                    )
                    audit_response = (
                        supabase.client.table("project_access_logs")
                        .insert(audit_payload)
                        .execute()
                    )
                    logger.info(
                        "[MOVE_PROJECT] audit insert result data=%s error=%s",
                        audit_response.data,
                        getattr(audit_response, "error", None),
                    )
                except Exception as audit_error:
                    logger.error(
                        "[MOVE_PROJECT] audit insert failed: %s",
                        audit_error,
                        exc_info=True,
                    )
            else:
                logger.warning(
                    "[MOVE_PROJECT] target org lookup missing organization_id for tenant=%s",
                    target_tenant_id,
                )
        else:
            logger.info(
                "[MOVE_PROJECT] no org mapping found for tenant=%s",
                target_tenant_id,
            )

        try:
            update_payload = {
                "tenant_id": target_tenant_id,
                "updated_at": datetime.utcnow().isoformat(),
            }
            if resolved_name and resolved_name != desired_name:
                update_payload["name"] = resolved_name

            update_result = (
                supabase.client.table("vmp_projects")
                .update(update_payload)
                .eq("id", project_id)
                .execute()
            )

            logger.info(
                "[MOVE_PROJECT] update result data=%s error=%s",
                update_result.data,
                getattr(update_result, "error", None),
            )
            logger.info(
                "[MOVE_PROJECT] update result status=%s response=%s",
                getattr(update_result, "status_code", None),
                update_result,
            )
        except Exception as update_error:
            logger.error(
                "[MOVE_PROJECT] update failed: %s",
                update_error,
                exc_info=True,
            )
            logger.error(
                "[MOVE_PROJECT] update error details code=%s message=%s hint=%s details=%s",
                getattr(update_error, "code", None),
                getattr(update_error, "message", None),
                getattr(update_error, "hint", None),
                getattr(update_error, "details", None),
            )
            raise HTTPException(
                status_code=500,
                detail="Failed to move project (update error)",
            )

        if not update_result.data:
            raise HTTPException(status_code=500, detail="Failed to move project")

        invalidation_service = get_invalidation_service()
        if invalidation_service:
            await invalidation_service.on_write(
                table_name="vmp_projects",
                operation=WriteOperation.UPDATE,
                record_id=project_id,
                tenant_id=tenant_id,
                user_id=user_id,
                background=True,
            )
            await invalidation_service.on_write(
                table_name="vmp_projects",
                operation=WriteOperation.UPDATE,
                record_id=project_id,
                tenant_id=target_tenant_id,
                user_id=user_id,
                background=True,
            )
            await invalidation_service.invalidate_project_caches(project_id, tenant_id)
            await invalidation_service.invalidate_project_caches(
                project_id, target_tenant_id
            )

        updated_project_result = await service.get_project_detail(
            project_id, target_tenant_id, user_id
        )

        return {
            "success": True,
            "data": updated_project_result.get("project"),
            "message": "Project moved successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to move project: {str(e)}")


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: str, current_user: dict = Depends(get_current_user)
):
    """Delete a VMP project and all associated data.

    This is a permanent operation and cannot be undone.
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        if not tenant_id:
            raise HTTPException(status_code=400, detail="User tenant not found")

        service = get_integrated_vmp_service()

        # Verify project exists and user has access
        project_result = await service.get_project_detail(
            project_id, tenant_id, user_id
        )
        if not project_result["success"]:
            raise HTTPException(status_code=404, detail="Project not found")

        # Verify user owns the project
        project = project_result["project"]
        if project.get("user_id") != user_id:
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to delete this project",
            )

        # Delete the project
        # CRITICAL FIX: Removed user_id filter to enable team collaboration
        response = (
            service.db_adapter.supabase.client.table("vmp_projects")
            .delete()
            .eq("id", project_id)
            .execute()
        )

        if response.data:
            # Invalidate VMP project list caches after successful deletion (Requirement 5.5)
            invalidation_service = get_invalidation_service()
            if invalidation_service:
                await invalidation_service.on_write(
                    table_name="vmp_projects",
                    operation=WriteOperation.DELETE,
                    record_id=project_id,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    background=True,
                )
                # Also invalidate all project-specific caches
                await invalidation_service.invalidate_project_caches(
                    project_id=project_id, tenant_id=tenant_id
                )

            return {
                "success": True,
                "data": {"project_id": project_id, "deleted": True},
                "message": "Project deleted successfully",
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to delete project")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete project: {str(e)}"
        )


# ==================== PERSONA IDENTIFICATION (PHASE 2) ====================


@router.post("/projects/{project_id}/identify-personas")
async def identify_personas(
    project_id: str, current_user: dict = Depends(get_current_user)
):
    """Identify personas for a VMP project using RAG analysis."""
    try:
        # Get tenant_id from user_id
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        plan_type = current_user.get("tenant_type", "individual")
        if not tenant_id:
            raise HTTPException(status_code=400, detail="User tenant not found")

        # Credit check - resolve feature name to UUID
        from src.mint.api.features.dependencies import resolve_feature_id

        feature_id = await resolve_feature_id("Persona Identification")
        user_roles = current_user.get("roles", [])
        is_super_admin = len(user_roles) > 0 and user_roles[0] == "super_admin"

        if not is_super_admin and not credit_service.has_sufficient_credits_for_feature(
            tenant_id=tenant_id,
            feature_id=feature_id,
            plan_type=plan_type,
        ):
            raise HTTPException(
                status_code=402,
                detail={
                    "code": "insufficient_credits",
                    "message": "You do not have enough credits for this feature.",
                },
            )

        service = get_integrated_vmp_service()
        result = await service.identify_personas(project_id, tenant_id, user_id)

        if result["success"]:
            # Consume credits after successful generation
            if not is_super_admin:
                try:
                    request_id = str(uuid.uuid4())
                    credit_service.consume_feature(
                        tenant_id=tenant_id,
                        user_id=user_id,
                        feature_id=feature_id,
                        plan_type=plan_type,
                        request_id=request_id,
                        reason="persona_identification",
                        project_id=project_id,
                        metadata={"total_personas": len(result.get("personas", []))},
                    )
                except Exception as credit_error:
                    print(f"⚠️ Credit consumption failed (non-blocking): {credit_error}")

            return {
                "success": True,
                "data": {
                    "project_id": project_id,
                    "personas": result["personas"],
                    "total_personas": result.get(
                        "total_personas", len(result.get("personas", []))
                    ),
                    "analysis_summary": result.get("analysis_summary", ""),
                    "requires_multiple_vpcs": result.get(
                        "requires_multiple_vpcs", False
                    ),
                    "personas_saved": result.get("personas_saved", False),
                },
                "message": f"Successfully identified {len(result.get('personas', []))} persona(s)",
                "next_step": f"/api/v2/vmp/projects/{project_id}/vpc/step1/generate-customer-profile",
            }
        else:
            raise HTTPException(status_code=400, detail=result["error"])

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/personas")
async def get_project_personas(
    project_id: str, current_user: dict = Depends(get_current_user)
):
    """Get previously identified personas for a VMP project."""
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        if not tenant_id:
            raise HTTPException(status_code=400, detail="User tenant not found")

        service = get_integrated_vmp_service()
        result = await service.get_project_personas(project_id, tenant_id)

        if result["success"]:
            return {
                "success": True,
                "data": result["data"],
                "message": f"Retrieved {result['data']['total_personas']} persona(s)",
            }
        else:
            raise HTTPException(status_code=404, detail=result["error"])

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/projects/{project_id}/personas", response_model=PersonaEditResponse)
async def edit_project_personas(
    project_id: str,
    edit_request: PersonaEditRequest,
    current_user: dict = Depends(get_current_user),
):
    """Edit personas for a VMP project.

    Accepts either format:
    1. Direct: {"personas": [...]}
    2. Wrapped: {"data": {"personas": [...]}} (same as GET response)
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        if not tenant_id:
            raise HTTPException(status_code=400, detail="User tenant not found")

        # Extract personas from either format
        try:
            personas = edit_request.get_personas()
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

        service = get_integrated_vmp_service()

        # Update personas in database
        success = await service.db_adapter.save_project_personas(project_id, personas)

        if success:
            # Retrieve updated personas
            result = await service.get_project_personas(project_id, tenant_id)

            return PersonaEditResponse(
                success=True,
                data=result["data"],
                message=f"Successfully updated {len(personas)} persona(s)",
            )
        else:
            raise HTTPException(status_code=400, detail="Failed to update personas")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to edit personas: {str(e)}"
        )


@router.post("/projects/{project_id}/personas/add", response_model=PersonaAddResponse)
async def add_user_persona(
    project_id: str,
    add_request: PersonaAddRequest,
    current_user: dict = Depends(get_current_user),
):
    """Add a new user-created persona to a VMP project with AI enrichment.

    The system will:
    1. Take user's persona name and description
    2. Query PV report and actionable insights (same as AI persona generation)
    3. Find relevant evidence from the data
    4. Enhance the description with insights from the data
    5. Generate problem_relationship automatically
    6. Create a fully enriched persona

    Rules:
    - Maximum 2 personas per project (system + user generated combined)
    - User provides: name, description (optional: problem_relationship, is_primary_payer)
    - System enriches with evidence and enhanced description
    - Automatically triggers multi-persona VPC workflow if adding 2nd persona
    - New persona will be used in all downstream workflows (hypotheses, assumptions, questionnaires)
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        if not tenant_id:
            raise HTTPException(status_code=400, detail="User tenant not found")

        service = get_integrated_vmp_service()

        # Get existing personas
        result = await service.get_project_personas(project_id, tenant_id)

        if not result["success"]:
            raise HTTPException(
                status_code=404, detail="Project not found or no personas exist"
            )

        existing_personas = result["data"].get("personas", [])

        # CRITICAL: Enforce maximum 2 personas limit
        if len(existing_personas) >= 2:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "max_personas_reached",
                    "message": "Maximum 2 personas allowed per project. Please delete an existing persona first.",
                    "current_count": len(existing_personas),
                },
            )

        # Generate unique ID for new persona
        new_persona_id = f"P{len(existing_personas) + 1}"

        print(
            f"🔍 DEBUG: [ADD_PERSONA] Starting AI enrichment for persona '{add_request.name}'"
        )

        # AI ENRICHMENT: Query PV report and actionable insights
        try:
            # Use dual context search to find relevant information about this persona
            context_query = f"{add_request.name} {add_request.description} customer stakeholder user problem pain"

            print(f"🔍 DEBUG: [ADD_PERSONA] Context query: {context_query}")

            context = await service.vector_adapter.dual_context_search(
                project_id=project_id,
                query=context_query,
                max_results_per_store=10,  # Get relevant context
            )

            print(
                f"🔍 DEBUG: [ADD_PERSONA] Retrieved context - PV: {len(context.get('pv_report_context', []))} items, Insights: {len(context.get('actionable_insights_context', []))}"
            )

            # Extract evidence from context
            evidence_items = []

            # Helper function to clean evidence quotes
            def clean_quote(text: str, max_length: int = 400) -> str:
                """Clean and format evidence quotes by removing HTML tags and truncating properly."""
                import re

                # Remove HTML tags
                text = re.sub(r"<[^>]+>", "", text)

                # Remove chunk IDs and markers
                text = re.sub(r"chunk-\d+", "", text)
                text = re.sub(r'class="report-chunk"', "", text)

                # Remove markdown headers at the start (##, ###, etc.)
                text = re.sub(r"^#+\s+", "", text.strip())

                # Clean up extra whitespace
                text = " ".join(text.split())

                # Truncate to max length, breaking at sentence if possible
                if len(text) > max_length:
                    # Try to break at last sentence within limit
                    truncated = text[:max_length]
                    last_period = truncated.rfind(".")
                    last_question = truncated.rfind("?")
                    last_exclamation = truncated.rfind("!")

                    # Find the last sentence ending
                    last_sentence_end = max(
                        last_period, last_question, last_exclamation
                    )

                    if (
                        last_sentence_end > max_length * 0.7
                    ):  # If we can keep at least 70% of text
                        text = truncated[: last_sentence_end + 1]
                    else:
                        # Break at last space
                        last_space = truncated.rfind(" ")
                        if last_space > 0:
                            text = truncated[:last_space] + "..."
                        else:
                            text = truncated + "..."

                return text.strip()

            # Get evidence from PV report context
            for item in context.get("pv_report_context", [])[:2]:  # Top 2 from report
                raw_content = item.get("content", "")
                cleaned_quote = clean_quote(raw_content, max_length=400)

                # Only add if we have meaningful content after cleaning
                if len(cleaned_quote) > 50:  # Minimum 50 chars for meaningful evidence
                    evidence_items.append(
                        {
                            "source": "report",
                            "quote": cleaned_quote,
                            "relevance_score": item.get("score", 0.8),
                        }
                    )

            # Get evidence from actionable insights
            for item in context.get("actionable_insights_context", [])[
                :1
            ]:  # Top 1 from insights
                raw_content = item.get("content", "")
                cleaned_quote = clean_quote(raw_content, max_length=400)

                # Only add if we have meaningful content after cleaning
                if len(cleaned_quote) > 50:
                    evidence_items.append(
                        {
                            "source": "insights",
                            "quote": cleaned_quote,
                            "relevance_score": item.get("score", 0.8),
                        }
                    )

            print(
                f"🔍 DEBUG: [ADD_PERSONA] Extracted {len(evidence_items)} evidence items"
            )

            # Use AI to enhance description and generate problem_relationship
            from VPM.core.ai_service import AIService

            ai_service = AIService()

            # Prepare context for AI
            context_text = "\n\n".join(
                [
                    f"Evidence {i + 1} ({ev['source']}): {ev['quote']}"
                    for i, ev in enumerate(evidence_items)
                ]
            )

            enhancement_prompt = f"""Based on the user's persona concept and evidence from the PV report and insights, enhance the persona description and generate a problem relationship.

User's Persona Name: {add_request.name}
User's Description: {add_request.description}

Evidence from PV Report and Insights:
{context_text}

Task:
1. Enhance the description to be more specific and data-driven (keep it 50-300 characters)
2. Generate a clear problem_relationship explaining how this persona relates to the problem (50-200 characters)
3. Ensure the enhanced content is grounded in the evidence provided

Return ONLY a JSON object with this structure:
{{
  "enhanced_description": "Enhanced description here",
  "problem_relationship": "How this persona relates to the problem"
}}"""

            messages = [
                {
                    "role": "system",
                    "content": "You are an expert at persona analysis. Enhance persona descriptions based on evidence from market research data.",
                },
                {"role": "user", "content": enhancement_prompt},
            ]

            print(f"🔍 DEBUG: [ADD_PERSONA] Calling AI for enhancement")

            enhancement_schema = {
                "type": "object",
                "properties": {
                    "enhanced_description": {
                        "type": "string",
                        "minLength": 50,
                        "maxLength": 500,
                    },
                    "problem_relationship": {
                        "type": "string",
                        "minLength": 50,
                        "maxLength": 300,
                    },
                },
                "required": ["enhanced_description", "problem_relationship"],
            }

            # Create monitoring context for AI usage tracking
            monitoring_context = None
            try:
                from monitor.tokens.models import AIUsageContext

                monitoring_context = AIUsageContext(
                    user_id=user_id,
                    tenant_id=tenant_id,
                    project_id=project_id,
                    feature_id="vpm_persona_enhancement",
                    workflow_name="vpm_persona_workflow",
                    step_name="enhance_persona",
                    environment="prod",
                )
            except ImportError:
                pass

            ai_response = ai_service.chat_json(
                messages, enhancement_schema, monitoring_context=monitoring_context
            )

            enhanced_description = ai_response.get(
                "enhanced_description", add_request.description
            )
            problem_relationship = ai_response.get(
                "problem_relationship", add_request.problem_relationship
            )

            print(f"✅ DEBUG: [ADD_PERSONA] AI enhancement complete")
            print(
                f"🔍 DEBUG: [ADD_PERSONA] Enhanced description: {enhanced_description[:100]}..."
            )
            print(
                f"🔍 DEBUG: [ADD_PERSONA] Problem relationship: {problem_relationship[:100]}..."
            )

        except Exception as e:
            print(f"⚠️ WARNING: [ADD_PERSONA] AI enrichment failed: {str(e)}")
            # Fallback to user-provided values
            enhanced_description = add_request.description
            problem_relationship = add_request.problem_relationship
            evidence_items = [
                {
                    "source": "user_input",
                    "quote": "User-created persona based on domain knowledge",
                    "relevance_score": 1.0,
                }
            ]

        # Create new persona with enriched data
        new_persona = {
            "id": new_persona_id,
            "name": add_request.name,
            "description": enhanced_description,
            "problem_relationship": problem_relationship,
            "evidence": evidence_items,
            "is_primary_payer": add_request.is_primary_payer,
            "created_by": "user",  # Mark as user-created
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "ai_enriched": True,  # Flag to indicate AI enrichment was applied
        }

        # Add to existing personas
        updated_personas = existing_personas + [new_persona]

        # Save updated personas
        success = await service.db_adapter.save_project_personas(
            project_id, updated_personas
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to save new persona")

        # Check if we now need multiple VPCs
        requires_multiple_vpcs = len(updated_personas) > 1

        # If adding 2nd persona, update VPC data structure for multi-persona support
        if requires_multiple_vpcs:
            project_data = await service.db_adapter.get_vmp_project(
                project_id, tenant_id
            )
            if project_data:
                vpc_data = project_data.get("vpc_data", {})

                # Initialize multi-persona VPC structure if not exists
                if "vpcs" not in vpc_data:
                    vpc_data["vpcs"] = {}

                    # Migrate existing single persona data if exists
                    if "customer_profile" in vpc_data:
                        vpc_data["vpcs"][existing_personas[0]["id"]] = {
                            "persona_id": existing_personas[0]["id"],
                            "persona_name": existing_personas[0]["name"],
                            "customer_profile": vpc_data.pop("customer_profile"),
                            "status": "completed",
                            "created_at": datetime.utcnow().isoformat(),
                        }

                # Initialize new persona VPC slot
                vpc_data["vpcs"][new_persona_id] = {
                    "persona_id": new_persona_id,
                    "persona_name": new_persona["name"],
                    "customer_profile": None,
                    "value_map": None,
                    "status": "pending",
                    "created_at": datetime.utcnow().isoformat(),
                }

                # Update project with new VPC structure
                from src.mint.api.system.core.supabase_client import (
                    get_service_role_client,
                )

                supabase = get_service_role_client()
                supabase.client.table("vmp_projects").update(
                    {"vpc_data": vpc_data, "updated_at": datetime.utcnow().isoformat()}
                ).eq("id", project_id).execute()

        # Retrieve updated personas
        updated_result = await service.get_project_personas(project_id, tenant_id)

        return PersonaAddResponse(
            success=True,
            data=updated_result["data"],
            message=f"Successfully added persona '{new_persona['name']}'. Total personas: {len(updated_personas)}",
            total_personas=len(updated_personas),
            requires_multiple_vpcs=requires_multiple_vpcs,
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ ERROR: [ADD_PERSONA] {str(e)}")
        import traceback

        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to add persona: {str(e)}")


@router.delete(
    "/projects/{project_id}/personas/{persona_id}", response_model=PersonaDeleteResponse
)
async def delete_persona(
    project_id: str, persona_id: str, current_user: dict = Depends(get_current_user)
):
    """Delete a persona from a VMP project.

    Rules:
    - Cannot delete if only 1 persona remains (minimum 1 required)
    - Deleting 2nd persona reverts to single-persona workflow
    - WARNING: Deleting a persona will remove associated customer profiles, hypotheses, assumptions, and questionnaires
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        if not tenant_id:
            raise HTTPException(status_code=400, detail="User tenant not found")

        service = get_integrated_vmp_service()

        # Get existing personas
        result = await service.get_project_personas(project_id, tenant_id)

        if not result["success"]:
            raise HTTPException(
                status_code=404, detail="Project not found or no personas exist"
            )

        existing_personas = result["data"].get("personas", [])

        # CRITICAL: Enforce minimum 1 persona
        if len(existing_personas) <= 1:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "min_personas_required",
                    "message": "Cannot delete the last persona. At least 1 persona is required.",
                    "current_count": len(existing_personas),
                },
            )

        # Find persona to delete
        persona_to_delete = None
        remaining_personas = []

        for persona in existing_personas:
            if persona["id"] == persona_id:
                persona_to_delete = persona
            else:
                remaining_personas.append(persona)

        if not persona_to_delete:
            raise HTTPException(
                status_code=404, detail=f"Persona with ID '{persona_id}' not found"
            )

        # Save remaining personas
        success = await service.db_adapter.save_project_personas(
            project_id, remaining_personas
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete persona")

        # Clean up associated data
        project_data = await service.db_adapter.get_vmp_project(project_id, tenant_id)
        if project_data:
            vpc_data = project_data.get("vpc_data", {})
            field_prep_data = project_data.get("field_prep_data", {})

            # Remove persona from VPC data
            if "vpcs" in vpc_data and persona_id in vpc_data["vpcs"]:
                del vpc_data["vpcs"][persona_id]

                # If only 1 persona left, revert to single-persona structure
                if len(remaining_personas) == 1:
                    remaining_persona_id = remaining_personas[0]["id"]
                    if remaining_persona_id in vpc_data["vpcs"]:
                        # Move data back to root level
                        vpc_data["customer_profile"] = vpc_data["vpcs"][
                            remaining_persona_id
                        ].get("customer_profile")
                        vpc_data["value_map"] = vpc_data["vpcs"][
                            remaining_persona_id
                        ].get("value_map")
                        del vpc_data["vpcs"]

            # Remove persona from field prep data
            if "hypotheses" in field_prep_data:
                field_prep_data["hypotheses"] = [
                    h
                    for h in field_prep_data["hypotheses"]
                    if h.get("persona_id") != persona_id
                ]

            if "assumptions" in field_prep_data:
                field_prep_data["assumptions"] = [
                    a
                    for a in field_prep_data["assumptions"]
                    if a.get("persona_id") != persona_id
                ]

            if "questionnaires" in field_prep_data:
                field_prep_data["questionnaires"] = [
                    q
                    for q in field_prep_data["questionnaires"]
                    if q.get("persona_id") != persona_id
                ]

            # Update project
            from src.mint.api.system.core.supabase_client import get_service_role_client

            supabase = get_service_role_client()
            supabase.client.table("vmp_projects").update(
                {
                    "vpc_data": vpc_data,
                    "field_prep_data": field_prep_data,
                    "updated_at": datetime.utcnow().isoformat(),
                }
            ).eq("id", project_id).execute()

        requires_multiple_vpcs = len(remaining_personas) > 1

        # Retrieve updated personas
        updated_result = await service.get_project_personas(project_id, tenant_id)

        return PersonaDeleteResponse(
            success=True,
            data=updated_result["data"],
            message=f"Successfully deleted persona '{persona_to_delete['name']}'. Remaining personas: {len(remaining_personas)}",
            total_personas=len(remaining_personas),
            requires_multiple_vpcs=requires_multiple_vpcs,
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ ERROR: [DELETE_PERSONA] {str(e)}")
        import traceback

        print(traceback.format_exc())
        raise HTTPException(
            status_code=500, detail=f"Failed to delete persona: {str(e)}"
        )


@router.post("/projects/{project_id}/vpc/step1/generate-customer-profile")
async def generate_customer_profile(
    project_id: str,
    generation_request: CustomerProfileGenerationRequest,
    current_user: dict = Depends(get_current_user),
):
    """Generate customer profile candidates (JTBD, Pains, Gains) for Step 1."""
    try:
        # Hardcoded feature for customer profile generation
        from src.mint.api.features.dependencies import resolve_feature_id

        feature_id = await resolve_feature_id("customer_profile_generator")

        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        plan_type = current_user["tenant_type"]

        # ---- Pre-check: ensure sufficient credits for this feature ----
        # Super admins bypass credit checks
        user_roles = current_user.get("roles", [])
        is_super_admin = len(user_roles) > 0 and user_roles[0] == "super_admin"

        if not is_super_admin and not credit_service.has_sufficient_credits_for_feature(
            tenant_id=tenant_id,
            feature_id=feature_id,
            plan_type=plan_type,
        ):
            raise HTTPException(
                status_code=402,
                detail={
                    "code": "insufficient_credits",
                    "message": "You do not have enough credits for this feature.",
                },
            )

        service = get_integrated_vmp_service()

        result = await service.generate_vpc_with_dual_context(
            project_id=project_id,
            generation_request={
                "generation_type": "customer_profile",
                "creativity_level": generation_request.creativity_level,
                "query": "customer problems pain points jobs to be done gains needs frustrations desires Ethiopian shoes footwear local manufacturing",
            },
            user_id=user_id,
        )

        if result["success"]:
            # ---- Deduct credits at the finish of the route (idempotent) ----
            # Prefer a session ID from generation metadata; fallback to a UUID.
            request_id = (
                result.get("vpc_data", {})
                .get("generation_metadata", {})
                .get("session_id")
                or result.get("session_id")
                or str(uuid.uuid4())
            )

            # Super admins bypass credit consumption
            if not is_super_admin:
                try:
                    credit_service.consume_feature(
                        tenant_id=tenant_id,
                        user_id=user_id,
                        feature_id=feature_id,
                        plan_type=plan_type,
                        request_id=request_id,  # unique (tenant_id, request_id) prevents double-charge on retries
                        reason="vpc_step1_generate_customer_profile",
                        project_id=project_id,
                        workflow_id=None,
                        metadata={
                            "generation_type": "customer_profile",
                            "source": "vpc_step1",
                            "creativity_level": generation_request.creativity_level,
                            "context_summary": result.get("context_summary", {}),
                        },
                    )
                except InsufficientCreditsError:
                    # Balance may have been consumed concurrently after pre-check
                    raise HTTPException(
                        status_code=402,
                        detail={
                            "code": "insufficient_credits",
                            "message": "Not enough credits to complete this request.",
                        },
                    )
                except InvalidConsumptionRequest as e:
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "code": "invalid_consumption_request",
                            "message": str(e),
                        },
                    )

            return {
                "success": True,
                "data": {
                    "customer_profile_candidates": result["vpc_data"],
                    "generation_metadata": result.get("vpc_data", {}).get(
                        "generation_metadata", {}
                    ),
                    "context_summary": result.get("context_summary", {}),
                },
                "message": "Customer profile candidates generated successfully. Please select 3 items from each category (JTBD, Pains, Gains).",
                "next_step": f"/api/v2/vmp/projects/{project_id}/vpc/step1/select-customer-profile",
            }
        else:
            raise HTTPException(status_code=400, detail=result["error"])

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/vpc/step1/customer-profile-candidates")
async def get_customer_profile_candidates(
    project_id: str, current_user: dict = Depends(get_current_user)
):
    """Get previously generated customer profile candidates (before selection)."""
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        if not tenant_id:
            raise HTTPException(status_code=400, detail="User tenant not found")

        service = get_integrated_vmp_service()

        # Get the latest customer profile artifacts
        artifacts = await service.db_adapter.get_latest_vpc_artifacts(
            project_id, "customer_profile"
        )

        if artifacts:
            # Parse the content if it's a string
            content = artifacts.get("content", {})
            if isinstance(content, str):
                import json

                try:
                    content = json.loads(content)
                except json.JSONDecodeError:
                    content = {}

            # Extract customer profile candidates
            customer_profile_candidates = content.get("customer_profile_candidates", {})
            customer_profile_data = customer_profile_candidates.get(
                "customer_profile", {}
            )

            # Enrich with persona_name based on persona_id using project personas
            try:
                personas = await service.db_adapter.get_project_personas(project_id)
                persona_name_map = {p.get("id"): p.get("name") for p in personas or []}
                for key in ["jobs_to_be_done", "pains", "gains"]:
                    items = customer_profile_data.get(key, [])
                    for item in items:
                        persona_id = item.get("persona_id")
                        if (
                            persona_id
                            and "persona_name" not in item
                            and persona_id in persona_name_map
                        ):
                            item["persona_name"] = persona_name_map[persona_id]
            except Exception:
                # Fail silently if persona enrichment fails; core payload must still work
                pass

            return {
                "success": True,
                "data": {
                    "project_id": project_id,
                    "customer_profile_candidates": customer_profile_data,
                    "generation_metadata": content.get("generation_metadata", {}),
                    "generated_at": artifacts.get("created_at"),
                },
                "message": "Customer profile candidates retrieved successfully",
            }
        else:
            raise HTTPException(
                status_code=404,
                detail="No customer profile candidates found. Please generate them first.",
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{project_id}/vpc/step1/select-customer-profile")
async def select_customer_profile(
    project_id: str,
    selection_request: CustomerProfileSelectionRequest,
    current_user: dict = Depends(get_current_user),
):
    """Save customer profile selections (supports both single and multi-persona formats)."""
    try:
        user_id = current_user["user_id"]
        service = get_integrated_vmp_service()

        # Determine if this is single or multi-persona selection
        if selection_request.persona_selections:
            # Multi-persona format
            print("🔍 DEBUG: [API] Multi-persona selection detected")

            # Validate persona selections
            for persona_id, selections in selection_request.persona_selections.items():
                if len(selections.get("jtbd", [])) != 3:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Exactly 3 Jobs-to-be-Done must be selected for {persona_id}",
                    )
                if len(selections.get("pain", [])) != 3:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Exactly 3 Pains must be selected for {persona_id}",
                    )
                if len(selections.get("gain", [])) != 3:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Exactly 3 Gains must be selected for {persona_id}",
                    )

            # Save multi-persona selections
            result = await service.save_multi_persona_customer_profile_selections(
                project_id=project_id,
                persona_selections=selection_request.persona_selections,
                user_id=user_id,
            )

        else:
            # Legacy single persona format
            print("🔍 DEBUG: [API] Single persona selection detected")

            # Validate selection counts
            if (
                not selection_request.selected_jtbd_ids
                or len(selection_request.selected_jtbd_ids) != 3
            ):
                raise HTTPException(
                    status_code=400, detail="Exactly 3 Jobs-to-be-Done must be selected"
                )
            if (
                not selection_request.selected_pain_ids
                or len(selection_request.selected_pain_ids) != 3
            ):
                raise HTTPException(
                    status_code=400, detail="Exactly 3 Pains must be selected"
                )
            if (
                not selection_request.selected_gain_ids
                or len(selection_request.selected_gain_ids) != 3
            ):
                raise HTTPException(
                    status_code=400, detail="Exactly 3 Gains must be selected"
                )

            # Save single persona selections
            result = await service.save_customer_profile_selections(
                project_id=project_id,
                selections={
                    "jtbd": selection_request.selected_jtbd_ids,
                    "pain": selection_request.selected_pain_ids,
                    "gain": selection_request.selected_gain_ids,
                },
                user_id=user_id,
            )

        if result["success"]:
            return {
                "success": True,
                "data": result.get(
                    "data",
                    {
                        "project_id": project_id,
                        "step_completed": 1,
                        "selections_saved": True,
                    },
                ),
                "message": "Customer profile selections saved successfully",
                "next_step": f"/api/v2/vmp/projects/{project_id}/field-prep/hypothesis",
            }
        else:
            raise HTTPException(status_code=400, detail=result["error"])

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/vpc/step1/customer-profile-selections")
async def get_customer_profile_selections(
    project_id: str, current_user: dict = Depends(get_current_user)
):
    """Get previously selected customer profile items."""
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        if not tenant_id:
            raise HTTPException(status_code=400, detail="User tenant not found")

        print(
            f"🔍 DEBUG: [GET_CP_SELECTIONS] Getting selections for project_id={project_id}, user_id={user_id}"
        )

        # Get project data with selections
        service = get_integrated_vmp_service()
        project_data = await service.db_adapter.get_project_with_selections(
            project_id, user_id
        )

        if not project_data:
            print(f"❌ DEBUG: [GET_CP_SELECTIONS] No project data found")
            raise HTTPException(status_code=404, detail="Project not found")

        print(
            f"🔍 DEBUG: [GET_CP_SELECTIONS] Project data keys: {list(project_data.keys())}"
        )

        vpc_data = project_data.get("vpc_data", {})
        print(f"🔍 DEBUG: [GET_CP_SELECTIONS] VPC data keys: {list(vpc_data.keys())}")

        # FIXED: Handle both single and multi-persona formats
        customer_profile = vpc_data.get("customer_profile", {})
        vpcs = vpc_data.get("vpcs", {})

        print(
            f"🔍 DEBUG: [GET_CP_SELECTIONS] Customer profile keys: {list(customer_profile.keys())}"
        )
        print(f"🔍 DEBUG: [GET_CP_SELECTIONS] VPCs keys: {list(vpcs.keys())}")
        print(
            f"🔍 DEBUG: [GET_CP_SELECTIONS] Customer profile content: {customer_profile}"
        )

        # Check if we have multi-persona format (vpcs) or single persona format (customer_profile)
        if vpcs:
            # Multi-persona format - combine all personas' customer profiles
            combined_profile = {"jobs_to_be_done": [], "pains": [], "gains": []}
            for persona_id, vpc in vpcs.items():
                persona_profile = vpc.get("customer_profile", {})
                if persona_profile:
                    combined_profile["jobs_to_be_done"].extend(
                        persona_profile.get("jobs_to_be_done", [])
                    )
                    combined_profile["pains"].extend(persona_profile.get("pains", []))
                    combined_profile["gains"].extend(persona_profile.get("gains", []))

            # Enrich selections with persona_name based on persona_id
            try:
                personas = await service.db_adapter.get_project_personas(project_id)
                persona_name_map = {p.get("id"): p.get("name") for p in personas or []}
                for key in ["jobs_to_be_done", "pains", "gains"]:
                    items = combined_profile.get(key, [])
                    for item in items:
                        persona_id = item.get("persona_id")
                        if (
                            persona_id
                            and "persona_name" not in item
                            and persona_id in persona_name_map
                        ):
                            item["persona_name"] = persona_name_map[persona_id]
            except Exception:
                # Fail silently if persona enrichment fails; core payload must still work
                pass

            print(
                f"🔍 DEBUG: [GET_CP_SELECTIONS] Combined profile: JTBD={len(combined_profile['jobs_to_be_done'])}, Pains={len(combined_profile['pains'])}, Gains={len(combined_profile['gains'])}"
            )

            if any(len(v) > 0 for v in combined_profile.values()):
                return {
                    "success": True,
                    "data": {
                        "project_id": project_id,
                        "customer_profile_selections": combined_profile,
                        "vpcs_data": vpcs,  # Include original VPCs data for reference
                        "format": "multi_persona",
                        "total_jtbd": len(combined_profile.get("jobs_to_be_done", [])),
                        "total_pains": len(combined_profile.get("pains", [])),
                        "total_gains": len(combined_profile.get("gains", [])),
                    },
                    "message": "Customer profile selections retrieved successfully (multi-persona format)",
                }
        elif customer_profile:
            # Enrich single-persona selections with persona_name where persona_id is present
            try:
                personas = await service.db_adapter.get_project_personas(project_id)
                persona_name_map = {p.get("id"): p.get("name") for p in personas or []}
                for key in ["jobs_to_be_done", "pains", "gains"]:
                    items = customer_profile.get(key, [])
                    for item in items:
                        persona_id = item.get("persona_id")
                        if (
                            persona_id
                            and "persona_name" not in item
                            and persona_id in persona_name_map
                        ):
                            item["persona_name"] = persona_name_map[persona_id]
            except Exception:
                # Fail silently if persona enrichment fails; core payload must still work
                pass
            return {
                "success": True,
                "data": {
                    "project_id": project_id,
                    "customer_profile_selections": customer_profile,
                    "total_jtbd": len(customer_profile.get("jobs_to_be_done", [])),
                    "total_pains": len(customer_profile.get("pains", [])),
                    "total_gains": len(customer_profile.get("gains", [])),
                },
                "message": "Customer profile selections retrieved successfully",
            }
        else:
            print(f"❌ DEBUG: [GET_CP_SELECTIONS] Customer profile is empty or missing")
            raise HTTPException(
                status_code=404,
                detail="No customer profile selections found. Please make selections first.",
            )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ ERROR: [GET_CP_SELECTIONS] Exception: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/vpc/template-data")
async def get_vpc_template_data(
    project_id: str, current_user: dict = Depends(get_current_user)
):
    """Get VPC template mapping data - labels and metadata only for frontend visualization.

    Returns a simplified structure with only the information needed to render the VPC template:
    - Labels for each item (no descriptions or evidence)
    - Position metadata for template mapping
    - Template configuration
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        if not tenant_id:
            raise HTTPException(status_code=400, detail="User tenant not found")

        # Get project data with selections
        service = get_integrated_vmp_service()
        project_data = await service.db_adapter.get_project_with_selections(
            project_id, user_id
        )

        if not project_data:
            raise HTTPException(status_code=404, detail="Project not found")

        vpc_data = project_data.get("vpc_data", {})

        # Handle both single-persona and multi-persona structures
        vpcs = vpc_data.get("vpcs", {})

        if vpcs:
            # Multi-persona structure: Combine customer profiles from all personas
            print(
                f"🔍 DEBUG: [TEMPLATE_DATA] Multi-persona structure detected with {len(vpcs)} personas"
            )
            combined_customer_profile = {
                "jobs_to_be_done": [],
                "pains": [],
                "gains": [],
            }

            for persona_id, vpc_info in vpcs.items():
                persona_customer_profile = vpc_info.get("customer_profile", {})
                if persona_customer_profile:
                    print(
                        f"🔍 DEBUG: [TEMPLATE_DATA] Found customer profile for {persona_id}"
                    )
                    combined_customer_profile["jobs_to_be_done"].extend(
                        persona_customer_profile.get("jobs_to_be_done", [])
                    )
                    combined_customer_profile["pains"].extend(
                        persona_customer_profile.get("pains", [])
                    )
                    combined_customer_profile["gains"].extend(
                        persona_customer_profile.get("gains", [])
                    )

            customer_profile = combined_customer_profile
            print(
                f"🔍 DEBUG: [TEMPLATE_DATA] Combined profile: JTBD={len(customer_profile['jobs_to_be_done'])}, Pains={len(customer_profile['pains'])}, Gains={len(customer_profile['gains'])}"
            )
        else:
            # Single-persona structure: Direct customer_profile
            customer_profile = vpc_data.get("customer_profile", {})
            print(f"🔍 DEBUG: [TEMPLATE_DATA] Single-persona structure")

        if not customer_profile or not any(
            [
                customer_profile.get("jobs_to_be_done"),
                customer_profile.get("pains"),
                customer_profile.get("gains"),
            ]
        ):
            raise HTTPException(
                status_code=404,
                detail="No customer profile found. Please complete customer profile selection first.",
            )

        # Enrich customer profile with persona_name (same as customer-profile-selections endpoint)
        try:
            personas = await service.db_adapter.get_project_personas(project_id)
            persona_name_map = {p.get("id"): p.get("name") for p in personas or []}
            for key in ["jobs_to_be_done", "pains", "gains"]:
                items = customer_profile.get(key, [])
                for item in items:
                    persona_id = item.get("persona_id")
                    if (
                        persona_id
                        and "persona_name" not in item
                        and persona_id in persona_name_map
                    ):
                        item["persona_name"] = persona_name_map[persona_id]
        except Exception:
            # Fail silently if persona enrichment fails; core payload must still work
            pass

        # Extract only labels and IDs for template mapping
        def extract_labels(items):
            """Extract only label and position data for template rendering"""
            return [
                {
                    "id": item.get("id"),
                    "label": item.get("label"),
                    "position": item.get(
                        "position", idx + 1
                    ),  # Default to sequential if not set
                    "persona_id": item.get("persona_id"),  # For multi-persona support
                    "persona_name": item.get(
                        "persona_name"
                    ),  # Include persona_name for display
                }
                for idx, item in enumerate(items)
            ]

        # Build template data structure
        template_data = {
            "template_id": "standard_vpc_v1",
            "layout": "square_circle",
            "customer_profile": {
                "jobs": {
                    "section_name": "Customer Jobs",
                    "items": extract_labels(
                        customer_profile.get("jobs_to_be_done", [])
                    ),
                    "max_items": 3,
                    "position": "top",
                },
                "pains": {
                    "section_name": "Pains",
                    "items": extract_labels(customer_profile.get("pains", [])),
                    "max_items": 3,
                    "position": "bottom-left",
                },
                "gains": {
                    "section_name": "Gains",
                    "items": extract_labels(customer_profile.get("gains", [])),
                    "max_items": 3,
                    "position": "bottom-right",
                },
            },
            "value_map": {
                "status": "pending",
                "message": "Value map will be generated after market research",
            },
        }

        return {
            "success": True,
            "data": {
                "project_id": project_id,
                "template_data": template_data,
                "vpc_image_url": project_data.get(
                    "vpc_image_url"
                ),  # Will be None until image is saved
                "last_updated": project_data.get("updated_at"),
            },
            "message": "VPC template data retrieved successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ ERROR: [GET_VPC_TEMPLATE_DATA] Exception: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{project_id}/vpc/save-image")
async def save_vpc_image(
    project_id: str,
    image_request: VPCImageRequest,
    current_user: dict = Depends(get_current_user),
):
    """Save VPC image URL/path to project.

    The frontend generates the VPC visualization and saves the image,
    then calls this endpoint to store the image URL in the database.
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        if not tenant_id:
            raise HTTPException(status_code=400, detail="User tenant not found")

        service = get_integrated_vmp_service()

        # Update project with image URL
        from src.mint.api.system.core.supabase_client import get_service_role_client

        supabase = get_service_role_client()

        # Verify project exists and user has access
        project_result = (
            supabase.client.table("vmp_projects")
            .select("id, user_id")
            .eq("id", project_id)
            .eq("tenant_id", tenant_id)
            .execute()
        )

        if not project_result.data:
            raise HTTPException(status_code=404, detail="Project not found")

        # Verify ownership
        if project_result.data[0]["user_id"] != user_id:
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to update this project",
            )

        # Update the vpc_image_url column
        update_result = (
            supabase.client.table("vmp_projects")
            .update(
                {
                    "vpc_image_url": image_request.vpc_image_url,
                    "updated_at": datetime.utcnow().isoformat(),
                }
            )
            .eq("id", project_id)
            .execute()
        )

        if not update_result.data:
            raise HTTPException(status_code=500, detail="Failed to save VPC image URL")

        return {
            "success": True,
            "data": {
                "project_id": project_id,
                "vpc_image_url": image_request.vpc_image_url,
                "updated_at": update_result.data[0].get("updated_at"),
            },
            "message": "VPC image URL saved successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ ERROR: [SAVE_VPC_IMAGE] Exception: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/vpc/image")
async def get_vpc_image(
    project_id: str, current_user: dict = Depends(get_current_user)
):
    """Get VPC image URL for a project.

    Returns the saved VPC image URL if it exists.
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        if not tenant_id:
            raise HTTPException(status_code=400, detail="User tenant not found")

        from src.mint.api.system.core.supabase_client import get_service_role_client

        supabase = get_service_role_client()

        # Get project with image URL
        project_result = (
            supabase.client.table("vmp_projects")
            .select("id, vpc_image_url, updated_at")
            .eq("id", project_id)
            .eq("tenant_id", tenant_id)
            .execute()
        )

        if not project_result.data:
            raise HTTPException(status_code=404, detail="Project not found")

        project = project_result.data[0]
        vpc_image_url = project.get("vpc_image_url")

        if not vpc_image_url:
            return {
                "success": True,
                "data": {
                    "project_id": project_id,
                    "vpc_image_url": None,
                    "image_exists": False,
                },
                "message": "No VPC image has been saved yet",
            }

        return {
            "success": True,
            "data": {
                "project_id": project_id,
                "vpc_image_url": vpc_image_url,
                "image_exists": True,
                "last_updated": project.get("updated_at"),
            },
            "message": "VPC image URL retrieved successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ ERROR: [GET_VPC_IMAGE] Exception: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/projects/{project_id}/vpc/step1/customer-profile-selections",
    response_model=CustomerProfileEditResponse,
)
async def edit_customer_profile_selections(
    project_id: str,
    edit_request: CustomerProfileEditRequest,
    current_user: dict = Depends(get_current_user),
):
    """Edit customer profile selections.

    Accepts either format:
    1. Direct: {"customer_profile_selections": {"jobs_to_be_done": [...], "pains": [...], "gains": [...]}}
    2. Wrapped: {"data": {"customer_profile_selections": {...}}} (same as GET response)
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        if not tenant_id:
            raise HTTPException(status_code=400, detail="User tenant not found")

        # Extract customer profile from either format
        try:
            customer_profile = edit_request.get_customer_profile()
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

        print(
            f"🔍 DEBUG: [EDIT_CP] Updating customer profile for project_id={project_id}"
        )
        print(f"🔍 DEBUG: [EDIT_CP] Profile keys: {list(customer_profile.keys())}")

        service = get_integrated_vmp_service()

        # Update customer profile in database
        # Get current project data
        project_data = await service.db_adapter.get_project_with_selections(
            project_id, user_id
        )

        if not project_data:
            raise HTTPException(status_code=404, detail="Project not found")

        # Update vpc_data with new customer profile
        vpc_data = project_data.get("vpc_data", {})

        # FIXED: Handle both single and multi-persona structures
        vpcs = vpc_data.get("vpcs", {})

        if vpcs:
            # Multi-persona structure: Distribute items back to personas based on persona_id
            print(
                f"🔍 DEBUG: [EDIT_CP] Multi-persona structure detected with {len(vpcs)} personas"
            )

            # Group items by persona_id
            persona_items = {}
            for category in ["jobs_to_be_done", "pains", "gains"]:
                items = customer_profile.get(category, [])
                for item in items:
                    persona_id = item.get(
                        "persona_id", "P1"
                    )  # Default to P1 if missing
                    if persona_id not in persona_items:
                        persona_items[persona_id] = {
                            "jobs_to_be_done": [],
                            "pains": [],
                            "gains": [],
                        }
                    persona_items[persona_id][category].append(item)

            # Update each persona's customer profile
            for persona_id, items in persona_items.items():
                if persona_id in vpcs:
                    vpcs[persona_id]["customer_profile"] = items
                    print(
                        f"✅ DEBUG: [EDIT_CP] Updated {persona_id}: JTBD={len(items['jobs_to_be_done'])}, Pains={len(items['pains'])}, Gains={len(items['gains'])}"
                    )
                else:
                    print(
                        f"⚠️ WARNING: [EDIT_CP] Persona {persona_id} not found in VPCs structure"
                    )

            vpc_data["vpcs"] = vpcs
        else:
            # Single-persona structure: Direct update
            print(f"🔍 DEBUG: [EDIT_CP] Single-persona structure")
            vpc_data["customer_profile"] = customer_profile

        # Save updated vpc_data
        result = (
            service.db_adapter.supabase.client.table("vmp_projects")
            .update({"vpc_data": vpc_data, "updated_at": "now()"})
            .eq("id", project_id)
            .execute()
        )

        if result.data:
            # Retrieve updated customer profile
            updated_project = await service.db_adapter.get_project_with_selections(
                project_id, user_id
            )
            updated_vpc_data = updated_project.get("vpc_data", {})

            # FIXED: Handle both structures when returning
            updated_vpcs = updated_vpc_data.get("vpcs", {})
            if updated_vpcs:
                # Multi-persona: Combine profiles
                updated_profile = {"jobs_to_be_done": [], "pains": [], "gains": []}
                for persona_id, vpc in updated_vpcs.items():
                    persona_profile = vpc.get("customer_profile", {})
                    if persona_profile:
                        updated_profile["jobs_to_be_done"].extend(
                            persona_profile.get("jobs_to_be_done", [])
                        )
                        updated_profile["pains"].extend(
                            persona_profile.get("pains", [])
                        )
                        updated_profile["gains"].extend(
                            persona_profile.get("gains", [])
                        )
            else:
                # Single-persona: Direct access
                updated_profile = updated_vpc_data.get("customer_profile", {})

            return CustomerProfileEditResponse(
                success=True,
                data={
                    "project_id": project_id,
                    "customer_profile_selections": updated_profile,
                    "total_jtbd": len(updated_profile.get("jobs_to_be_done", [])),
                    "total_pains": len(updated_profile.get("pains", [])),
                    "total_gains": len(updated_profile.get("gains", [])),
                },
                message=f"Successfully updated customer profile selections",
            )
        else:
            raise HTTPException(
                status_code=400, detail="Failed to update customer profile"
            )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ ERROR: [EDIT_CP] Exception: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to edit customer profile: {str(e)}"
        )


# ==================== REPORT DISCOVERY ENDPOINTS ====================


@router.get("/reports")
async def browse_pv_reports(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(35, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(
        None, description="Search query for report titles/descriptions"
    ),
    status_filter: Optional[str] = Query(None, description="Filter by report status"),
    current_user: dict = Depends(get_current_user),
):
    """Browse available Problem Validation reports for VMP project creation."""
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        if not tenant_id:
            raise HTTPException(status_code=400, detail="User tenant not found")

        service = get_integrated_vmp_service()
        result = await service.browse_pv_reports(
            tenant_id=tenant_id,
            user_id=user_id,
            page=page,
            page_size=page_size,
            search=search,
        )

        if result["success"]:
            return {
                "success": True,
                "data": {
                    "reports": result["reports"],
                    "total_count": result["total_count"],
                    "page": page,
                    "page_size": page_size,
                    "has_next": result.get("has_next", False),
                },
                "message": f"Found {len(result['reports'])} reports",
            }
        else:
            raise HTTPException(status_code=400, detail=result["error"])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch reports: {str(e)}"
        )


@router.post("/projects")
async def create_vmp_project(
    project_request: CreateProjectRequest,
    current_user: dict = Depends(get_current_user),
):
    """Create a new VMP project from a Problem Validation report."""
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        if not tenant_id:
            raise HTTPException(status_code=400, detail="User tenant not found")

        service = get_integrated_vmp_service()
        project_data = {
            "name": project_request.name,
            "pv_report_id": project_request.pv_report_id,
            "tenant_id": tenant_id,
        }

        result = await service.create_vmp_project(project_data, user_id)

        if result["success"]:
            return {
                "success": True,
                "data": {
                    "project": result["project"],
                    "next_step": f"/api/v2/vmp/projects/{result['project']['id']}/identify-personas",
                },
                "message": result["message"],
            }
        else:
            if "credits" in result["error"].lower():
                raise HTTPException(status_code=402, detail=result["error"])
            else:
                raise HTTPException(status_code=400, detail=result["error"])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create project: {str(e)}"
        )


# COMMENTED OUT - VALUE MAP GENERATION REMOVED FROM WORKFLOW
# @router.post("/projects/{project_id}/vpc/step2/generate-value-map")
# async def generate_value_map(
#     project_id: str,
#     generation_request: ValueMapGenerationRequest,
#     user_id: str = Depends(get_current_user)
# ):
#     """Generate Value Map candidates (Products/Services, Pain Relievers, Gain Creators)."""
#     try:
#         tenant_id = await get_user_tenant_id(user_id)
#         if not tenant_id:
#             raise HTTPException(status_code=400, detail="User tenant not found")
#
#         service = get_integrated_vmp_service()
#         context = await service.get_dual_vector_context(project_id, tenant_id)
#         if not context['success']:
#             raise HTTPException(status_code=400, detail=context['error'])
#
#         result = await service.generate_value_map_with_dual_context(
#             project_id=project_id,
#             context=context['context'],
#             generation_request=generation_request.dict(),
#             user_id=user_id
#         )
#
#         if result['success']:
#             return {
#                 "success": True,
#                 "data": {
#                     "project_id": project_id,
#                     "step": 2,
#                     "value_map_candidates": result['value_map_candidates'],
#                     "context_summary": result.get('context_summary', {})
#                 },
#                 "message": "Value map candidates generated successfully. Please select 3 items from each category.",
#                 "next_step": f"/api/v2/vmp/projects/{project_id}/vpc/step2/select-value-map"
#             }
#         else:
#             if "credits" in result['error'].lower():
#                 raise HTTPException(status_code=402, detail=result['error'])
#             else:
#                 raise HTTPException(status_code=400, detail=result['error'])
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to generate value map: {str(e)}")

# COMMENTED OUT - VALUE MAP SELECTION REMOVED FROM WORKFLOW
# @router.post("/projects/{project_id}/vpc/step2/select-value-map")
# async def select_value_map(
#     project_id: str,
#     selection_request: ValueMapSelectionRequest,
#     user_id: str = Depends(get_current_user)
# ):
#     """Save Value Map selections (Step 2 completion)."""
#     try:
#         service = get_integrated_vmp_service()
#         selections = {
#             'selected_product_service_ids': selection_request.selected_product_service_ids,
#             'selected_pain_reliever_ids': selection_request.selected_pain_reliever_ids,
#             'selected_gain_creator_ids': selection_request.selected_gain_creator_ids
#         }
#
#         result = await service.save_value_map_selections(project_id, selections, user_id)
#
#         if result['success']:
#             return {
#                 "success": True,
#                 "data": result.get('data', {
#                     "project_id": project_id,
#                     "step_completed": 2,
#                     "selections_saved": True
#                 }),
#                 "message": "Value map selections saved successfully. Ready for final VPC composition.",
#                 "next_step": f"/api/v2/vmp/projects/{project_id}/vpc/step3/compose-final-vpc"
#             }
#         else:
#             raise HTTPException(status_code=400, detail=result['error'])
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to save value map selections: {str(e)}")

# COMMENTED OUT - VPC COMPOSITION REMOVED FROM WORKFLOW (MOVED TO POST-RESEARCH)
# @router.post("/projects/{project_id}/vpc/step3/compose-final-vpc")
# async def compose_final_vpc(
#     project_id: str,
#     composition_request: VPCCompositionRequest,
#     user_id: str = Depends(get_current_user)
# ):
#     """Compose the final Value Proposition Canvas (Step 3 - Final)."""
#     try:
#         service = get_integrated_vmp_service()
#         result = await service.compose_final_vpc(
#             project_id=project_id,
#             composition_options=composition_request.dict(),
#             user_id=user_id
#         )
#
#         if result['success']:
#             return {
#                 "success": True,
#                 "data": {
#                     "project_id": project_id,
#                     "vpc_canvas": result['vpc_canvas'],
#                     "visual_canvas": result.get('visual_canvas'),
#                     "export_formats": result.get('export_formats', []),
#                     "context_summary": result.get('context_summary', {}),
#                     "completion_stats": result.get('completion_stats', {})
#                 },
#                 "message": result['message'],
#                 "next_step": f"/api/v2/vmp/projects/{project_id}/field-prep/hypothesis"
#             }
#         else:
#             raise HTTPException(status_code=400, detail=result['error'])
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to compose final VPC: {str(e)}")


@router.post(
    "/projects/{project_id}/field-prep/hypothesis",
    response_model=FieldPrepHypothesisResponse,
)
async def generate_field_prep_hypothesis(
    project_id: str,
    request: FieldPrepHypothesisRequest,
    current_user: dict = Depends(get_current_user),
):
    """Generate market hypothesis for field research preparation."""
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        plan_type = current_user.get("tenant_type", "individual")
        if not tenant_id:
            raise HTTPException(status_code=400, detail="User tenant not found")

        # Credit check - resolve feature name to UUID
        from src.mint.api.features.dependencies import resolve_feature_id

        feature_id = await resolve_feature_id("Hypothesis Generator")
        user_roles = current_user.get("roles", [])
        is_super_admin = len(user_roles) > 0 and user_roles[0] == "super_admin"

        if not is_super_admin and not credit_service.has_sufficient_credits_for_feature(
            tenant_id=tenant_id,
            feature_id=feature_id,
            plan_type=plan_type,
        ):
            raise HTTPException(
                status_code=402,
                detail={
                    "code": "insufficient_credits",
                    "message": "You do not have enough credits for this feature.",
                },
            )

        # Get integrated services with adapters
        vmp_service = get_integrated_vmp_service()
        service = get_yuba_field_prep_service(
            vmp_service.auth_adapter,
            vmp_service.db_adapter,
            vmp_service.vector_adapter,
            vmp_service.credit_adapter,
        )
        result = await service.generate_hypothesis(
            project_id=project_id,
            user_id=user_id,
            creativity_level=request.creativity_level,
            tenant_id=tenant_id,
        )

        if result["success"]:
            # Consume credits after successful generation
            if not is_super_admin:
                try:
                    request_id = str(uuid.uuid4())
                    credit_service.consume_feature(
                        tenant_id=tenant_id,
                        user_id=user_id,
                        feature_id=feature_id,
                        plan_type=plan_type,
                        request_id=request_id,
                        reason="field_prep_hypothesis_generation",
                        project_id=project_id,
                        metadata={"personas_count": result.get("personas_count", 0)},
                    )
                except Exception as credit_error:
                    print(f"⚠️ Credit consumption failed (non-blocking): {credit_error}")

            return FieldPrepHypothesisResponse(
                project_id=project_id,
                hypothesis=result["hypotheses"],  # List of hypotheses (one per persona)
                stage=FieldPrepStage.HYPOTHESIS,
                context_summary=result.get("context_summary", {}),
                total_hypotheses=result.get(
                    "total_hypotheses", len(result["hypotheses"])
                ),
                personas_count=result.get("personas_count", 0),
            )
        else:
            if "credits" in result["error"].lower():
                raise HTTPException(status_code=402, detail=result["error"])
            else:
                raise HTTPException(status_code=400, detail=result["error"])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate hypothesis: {str(e)}"
        )


@router.get("/projects/{project_id}/field-prep/hypotheses")
async def get_field_prep_hypotheses(
    project_id: str, current_user: dict = Depends(get_current_user)
):
    """Get previously generated field research hypotheses."""
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        if not tenant_id:
            raise HTTPException(status_code=400, detail="User tenant not found")

        print(
            f"🔍 DEBUG: [GET_HYPOTHESES] Getting hypotheses for project_id={project_id}, tenant_id={tenant_id}, user_id={user_id}"
        )

        # Get project data - FIXED: Use get_project_with_selections like working endpoints
        service = get_integrated_vmp_service()
        project_data = await service.db_adapter.get_project_with_selections(
            project_id, user_id
        )

        print(
            f"🔍 DEBUG: [GET_HYPOTHESES] Project data result: {project_data is not None}"
        )
        if project_data:
            print(
                f"🔍 DEBUG: [GET_HYPOTHESES] Project data keys: {list(project_data.keys())}"
            )
            print(
                f"🔍 DEBUG: [GET_HYPOTHESES] Field prep data: {project_data.get('field_prep_data', {})}"
            )

        if not project_data:
            print(
                f"❌ DEBUG: [GET_HYPOTHESES] No project found for project_id={project_id}, tenant_id={tenant_id}"
            )
            raise HTTPException(status_code=404, detail="Project not found")

        # FIXED: Get field_prep_data from vmp_project_data since we're using get_project_with_selections
        vmp_project_data = project_data.get("vmp_project_data", {})
        field_prep_data = vmp_project_data.get("field_prep_data", {})
        hypotheses = field_prep_data.get("hypotheses", [])

        print(f"🔍 DEBUG: [GET_HYPOTHESES] Found {len(hypotheses)} hypotheses")

        if hypotheses:
            return {
                "success": True,
                "data": {
                    "project_id": project_id,
                    "hypotheses": hypotheses,
                    "total_hypotheses": len(hypotheses),
                    "generated_at": field_prep_data.get("hypotheses_generated_at"),
                    "stage": field_prep_data.get("stage"),
                },
                "message": f"Retrieved {len(hypotheses)} hypothesis(es)",
            }
        else:
            print(f"❌ DEBUG: [GET_HYPOTHESES] No hypotheses found in field_prep_data")
            raise HTTPException(
                status_code=404,
                detail="No hypotheses found. Please generate them first.",
            )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ ERROR: [GET_HYPOTHESES] Exception: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/projects/{project_id}/field-prep/hypotheses",
    response_model=HypothesisEditResponse,
)
async def edit_field_prep_hypotheses(
    project_id: str,
    edit_request: HypothesisEditRequest,
    current_user: dict = Depends(get_current_user),
):
    """Edit field research hypotheses.

    Accepts either format:
    1. Direct: {"hypotheses": [...]}
    2. Wrapped: {"data": {"hypotheses": [...]}} (same as GET response)
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        if not tenant_id:
            raise HTTPException(status_code=400, detail="User tenant not found")

        # Extract hypotheses from either format
        try:
            hypotheses = edit_request.get_hypotheses()
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

        # Get integrated services
        vmp_service = get_integrated_vmp_service()
        service = get_yuba_field_prep_service(
            vmp_service.auth_adapter,
            vmp_service.db_adapter,
            vmp_service.vector_adapter,
            vmp_service.credit_adapter,
        )

        # Update hypotheses in database
        success = await service._save_hypotheses_to_project(
            project_id, hypotheses, user_id
        )

        if success:
            # Retrieve updated hypotheses
            project_data = await vmp_service.db_adapter.get_project_with_selections(
                project_id, user_id
            )
            vmp_project_data = project_data.get("vmp_project_data", {})
            field_prep_data = vmp_project_data.get("field_prep_data", {})
            hypotheses = field_prep_data.get("hypotheses", [])

            return HypothesisEditResponse(
                success=True,
                data={
                    "project_id": project_id,
                    "hypotheses": hypotheses,
                    "total_hypotheses": len(hypotheses),
                    "generated_at": field_prep_data.get("hypotheses_generated_at"),
                    "stage": field_prep_data.get("stage"),
                },
                message=f"Successfully updated {len(hypotheses)} hypothesis(es)",
            )
        else:
            raise HTTPException(status_code=400, detail="Failed to update hypotheses")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to edit hypotheses: {str(e)}"
        )


@router.post(
    "/projects/{project_id}/field-prep/assumptions",
    response_model=FieldPrepAssumptionsResponse,
)
async def generate_field_prep_assumptions(
    project_id: str,
    request: FieldPrepAssumptionsRequest,
    current_user: dict = Depends(get_current_user),
):
    """Generate testable assumptions for field research."""
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        plan_type = current_user.get("tenant_type", "individual")
        if not tenant_id:
            raise HTTPException(status_code=400, detail="User tenant not found")

        # Credit check - resolve feature name to UUID
        from src.mint.api.features.dependencies import resolve_feature_id

        feature_id = await resolve_feature_id("Assumptions Generator")
        user_roles = current_user.get("roles", [])
        is_super_admin = len(user_roles) > 0 and user_roles[0] == "super_admin"

        if not is_super_admin and not credit_service.has_sufficient_credits_for_feature(
            tenant_id=tenant_id,
            feature_id=feature_id,
            plan_type=plan_type,
        ):
            raise HTTPException(
                status_code=402,
                detail={
                    "code": "insufficient_credits",
                    "message": "You do not have enough credits for this feature.",
                },
            )

        # Get integrated services with adapters
        vmp_service = get_integrated_vmp_service()
        service = get_yuba_field_prep_service(
            vmp_service.auth_adapter,
            vmp_service.db_adapter,
            vmp_service.vector_adapter,
            vmp_service.credit_adapter,
        )
        result = await service.generate_assumptions(
            project_id=project_id,
            user_id=user_id,
            max_assumptions=request.max_assumptions,
            tenant_id=tenant_id,
        )

        if result["success"]:
            # Consume credits after successful generation
            if not is_super_admin:
                try:
                    request_id = str(uuid.uuid4())
                    credit_service.consume_feature(
                        tenant_id=tenant_id,
                        user_id=user_id,
                        feature_id=feature_id,
                        plan_type=plan_type,
                        request_id=request_id,
                        reason="field_prep_assumptions_generation",
                        project_id=project_id,
                        metadata={
                            "total_assumptions": result.get("total_assumptions", 0)
                        },
                    )
                except Exception as credit_error:
                    print(f"⚠️ Credit consumption failed (non-blocking): {credit_error}")

            return FieldPrepAssumptionsResponse(
                project_id=project_id,
                assumptions=result["assumptions"],
                stage=FieldPrepStage.ASSUMPTIONS,
                total_assumptions=result.get(
                    "total_assumptions", len(result["assumptions"])
                ),
                hypotheses_count=result.get("hypotheses_count", 0),
                hypotheses_reference=result.get("hypotheses_reference", []),
            )
        else:
            if "credits" in result["error"].lower():
                raise HTTPException(status_code=402, detail=result["error"])
            else:
                raise HTTPException(status_code=400, detail=result["error"])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate assumptions: {str(e)}"
        )


@router.get("/projects/{project_id}/field-prep/assumptions")
async def get_field_prep_assumptions(
    project_id: str, current_user: dict = Depends(get_current_user)
):
    """Get previously generated field research assumptions."""
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        if not tenant_id:
            raise HTTPException(status_code=400, detail="User tenant not found")

        # Get project data - FIXED: Use get_project_with_selections like working endpoints
        service = get_integrated_vmp_service()
        project_data = await service.db_adapter.get_project_with_selections(
            project_id, user_id
        )

        if not project_data:
            raise HTTPException(status_code=404, detail="Project not found")

        # FIXED: Get field_prep_data from vmp_project_data since we're using get_project_with_selections
        vmp_project_data = project_data.get("vmp_project_data", {})
        field_prep_data = vmp_project_data.get("field_prep_data", {})
        assumptions = field_prep_data.get("assumptions", [])
        hypotheses = field_prep_data.get("hypotheses", [])

        if assumptions:
            return {
                "success": True,
                "data": {
                    "project_id": project_id,
                    "assumptions": assumptions,
                    "total_assumptions": len(assumptions),
                    "hypotheses_count": len(hypotheses),
                    "generated_at": field_prep_data.get("assumptions_generated_at"),
                    "stage": field_prep_data.get("stage"),
                },
                "message": f"Retrieved {len(assumptions)} assumption(s)",
            }
        else:
            raise HTTPException(
                status_code=404,
                detail="No assumptions found. Please generate them first.",
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/projects/{project_id}/field-prep/assumptions",
    response_model=AssumptionsEditResponse,
)
async def edit_field_prep_assumptions(
    project_id: str,
    edit_request: AssumptionsEditRequest,
    current_user: dict = Depends(get_current_user),
):
    """Edit field research assumptions.

    Accepts either format:
    1. Direct: {"assumptions": [...]}
    2. Wrapped: {"data": {"assumptions": [...]}} (same as GET response)
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        if not tenant_id:
            raise HTTPException(status_code=400, detail="User tenant not found")

        # Extract assumptions from either format
        try:
            assumptions = edit_request.get_assumptions()
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

        # Get integrated services
        vmp_service = get_integrated_vmp_service()
        service = get_yuba_field_prep_service(
            vmp_service.auth_adapter,
            vmp_service.db_adapter,
            vmp_service.vector_adapter,
            vmp_service.credit_adapter,
        )

        # Update assumptions in database
        success = await service._save_assumptions_to_project(
            project_id, assumptions, user_id
        )

        if success:
            # Retrieve updated assumptions
            project_data = await vmp_service.db_adapter.get_project_with_selections(
                project_id, user_id
            )
            vmp_project_data = project_data.get("vmp_project_data", {})
            field_prep_data = vmp_project_data.get("field_prep_data", {})
            assumptions = field_prep_data.get("assumptions", [])
            hypotheses = field_prep_data.get("hypotheses", [])

            return AssumptionsEditResponse(
                success=True,
                data={
                    "project_id": project_id,
                    "assumptions": assumptions,
                    "total_assumptions": len(assumptions),
                    "hypotheses_count": len(hypotheses),
                    "generated_at": field_prep_data.get("assumptions_generated_at"),
                    "stage": field_prep_data.get("stage"),
                },
                message=f"Successfully updated {len(assumptions)} assumption(s)",
            )
        else:
            raise HTTPException(status_code=400, detail="Failed to update assumptions")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to edit assumptions: {str(e)}"
        )


@router.post(
    "/projects/{project_id}/field-prep/questionnaires",
    response_model=FieldPrepQuestionnairesResponse,
)
async def generate_field_prep_questionnaires(
    project_id: str,
    request: FieldPrepQuestionnairesRequest,
    current_user: dict = Depends(get_current_user),
):
    """Generate targeted questionnaires for field research using identified personas."""
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        plan_type = current_user.get("tenant_type", "individual")
        if not tenant_id:
            raise HTTPException(status_code=400, detail="User tenant not found")

        # Credit check - resolve feature name to UUID
        from src.mint.api.features.dependencies import resolve_feature_id

        feature_id = await resolve_feature_id("Questionnaire Generator")
        user_roles = current_user.get("roles", [])
        is_super_admin = len(user_roles) > 0 and user_roles[0] == "super_admin"

        if not is_super_admin and not credit_service.has_sufficient_credits_for_feature(
            tenant_id=tenant_id,
            feature_id=feature_id,
            plan_type=plan_type,
        ):
            raise HTTPException(
                status_code=402,
                detail={
                    "code": "insufficient_credits",
                    "message": "You do not have enough credits for this feature.",
                },
            )

        # Get integrated services with adapters
        vmp_service = get_integrated_vmp_service()
        service = get_yuba_field_prep_service(
            vmp_service.auth_adapter,
            vmp_service.db_adapter,
            vmp_service.vector_adapter,
            vmp_service.credit_adapter,
        )
        result = await service.generate_questionnaires(
            project_id=project_id,
            user_id=user_id,
            questions_per_assumption=request.questions_per_assumption,
            include_demographic_questions=request.include_demographic_questions,
            tenant_id=tenant_id,
        )

        if result["success"]:
            # Consume credits after successful generation
            if not is_super_admin:
                try:
                    request_id = str(uuid.uuid4())
                    credit_service.consume_feature(
                        tenant_id=tenant_id,
                        user_id=user_id,
                        feature_id=feature_id,
                        plan_type=plan_type,
                        request_id=request_id,
                        reason="field_prep_questionnaires_generation",
                        project_id=project_id,
                        metadata={"total_questions": result.get("total_questions", 0)},
                    )
                except Exception as credit_error:
                    print(f"⚠️ Credit consumption failed (non-blocking): {credit_error}")

            # Invalidate completed questionnaires list cache after successful generation (Requirement 5.7)
            from src.mint.api.cache.entity_cache_service import EntityType

            invalidation_service = get_invalidation_service()
            if invalidation_service:
                await invalidation_service.on_feature_completed(
                    feature_entity=EntityType.QUESTIONNAIRE,
                    project_id=project_id,
                    tenant_id=tenant_id,
                    background=True,
                )

            return FieldPrepQuestionnairesResponse(
                project_id=project_id,
                questionnaires=result["questionnaires"],
                stage=FieldPrepStage.QUESTIONNAIRES,
                total_questions=result.get(
                    "total_questions", len(result["questionnaires"])
                ),
                assumptions_count=result.get("assumptions_count", 0),
                personas_count=result.get("personas_count", 0),
                questions_per_assumption=result.get("questions_per_assumption", 5),
            )
        else:
            if "credits" in result["error"].lower():
                raise HTTPException(status_code=402, detail=result["error"])
            else:
                raise HTTPException(status_code=400, detail=result["error"])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate questionnaires: {str(e)}"
        )


@router.get("/projects/{project_id}/field-prep/questionnaires")
async def get_field_prep_questionnaires(
    project_id: str, current_user: dict = Depends(get_current_user)
):
    """Get previously generated field research questionnaires."""
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        if not tenant_id:
            raise HTTPException(status_code=400, detail="User tenant not found")

        # Get project data - FIXED: Use get_project_with_selections like working endpoints
        service = get_integrated_vmp_service()
        project_data = await service.db_adapter.get_project_with_selections(
            project_id, user_id
        )

        if not project_data:
            raise HTTPException(status_code=404, detail="Project not found")

        # FIXED: Get field_prep_data from vmp_project_data since we're using get_project_with_selections
        vmp_project_data = project_data.get("vmp_project_data", {})
        field_prep_data = vmp_project_data.get("field_prep_data", {})
        questionnaires = field_prep_data.get("questionnaires", [])
        assumptions = field_prep_data.get("assumptions", [])

        if questionnaires:
            # Group questionnaires by persona for better organization
            questionnaires_by_persona = {}
            for question in questionnaires:
                persona_name = question.get("persona_name", "Unknown")
                if persona_name not in questionnaires_by_persona:
                    questionnaires_by_persona[persona_name] = []
                questionnaires_by_persona[persona_name].append(question)

            return {
                "success": True,
                "data": {
                    "project_id": project_id,
                    "questionnaires": questionnaires,
                    "questionnaires_by_persona": questionnaires_by_persona,
                    "total_questions": len(questionnaires),
                    "assumptions_count": len(assumptions),
                    "personas_count": len(questionnaires_by_persona),
                    "generated_at": field_prep_data.get("questionnaires_generated_at"),
                    "stage": field_prep_data.get("stage"),
                },
                "message": f"Retrieved {len(questionnaires)} question(s) for {len(questionnaires_by_persona)} persona(s)",
            }
        else:
            raise HTTPException(
                status_code=404,
                detail="No questionnaires found. Please generate them first.",
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/projects/{project_id}/field-prep/questionnaires",
    response_model=QuestionnairesEditResponse,
)
async def edit_field_prep_questionnaires(
    project_id: str,
    edit_request: QuestionnairesEditRequest,
    current_user: dict = Depends(get_current_user),
):
    """Edit field research questionnaires.

    Accepts either format:
    1. Direct: {"questionnaires": [...]}
    2. Wrapped: {"data": {"questionnaires": [...]}} (same as GET response)
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        if not tenant_id:
            raise HTTPException(status_code=400, detail="User tenant not found")

        # Extract questionnaires from either format
        try:
            questionnaires = edit_request.get_questionnaires()
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

        # Get integrated services
        vmp_service = get_integrated_vmp_service()
        service = get_yuba_field_prep_service(
            vmp_service.auth_adapter,
            vmp_service.db_adapter,
            vmp_service.vector_adapter,
            vmp_service.credit_adapter,
        )

        # Update questionnaires in database
        success = await service._save_questionnaires_to_project(
            project_id, questionnaires, user_id
        )

        if success:
            # Retrieve updated questionnaires
            project_data = await vmp_service.db_adapter.get_project_with_selections(
                project_id, user_id
            )
            vmp_project_data = project_data.get("vmp_project_data", {})
            field_prep_data = vmp_project_data.get("field_prep_data", {})
            questionnaires = field_prep_data.get("questionnaires", [])
            assumptions = field_prep_data.get("assumptions", [])

            # Group questionnaires by persona
            questionnaires_by_persona = {}
            for question in questionnaires:
                persona_name = question.get("persona_name", "Unknown")
                if persona_name not in questionnaires_by_persona:
                    questionnaires_by_persona[persona_name] = []
                questionnaires_by_persona[persona_name].append(question)

            return QuestionnairesEditResponse(
                success=True,
                data={
                    "project_id": project_id,
                    "questionnaires": questionnaires,
                    "questionnaires_by_persona": questionnaires_by_persona,
                    "total_questions": len(questionnaires),
                    "assumptions_count": len(assumptions),
                    "personas_count": len(questionnaires_by_persona),
                    "generated_at": field_prep_data.get("questionnaires_generated_at"),
                    "stage": field_prep_data.get("stage"),
                },
                message=f"Successfully updated {len(questionnaires)} question(s)",
            )
        else:
            raise HTTPException(
                status_code=400, detail="Failed to update questionnaires"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to edit questionnaires: {str(e)}"
        )


@router.get("/health")
async def vmp_health_check():
    """VMP module health check."""
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "vmp_service": "available",
                "field_prep_service": "available",
                "database": "connected",
                "vector_storage": "connected",
            },
            "version": "2.0.0",
        }

        return {
            "success": True,
            "data": health_status,
            "message": "VMP module is healthy and operational",
        }
    except Exception as e:
        return {
            "success": False,
            "data": {
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
            },
            "message": f"VMP module health check failed: {str(e)}",
        }


# ==================== WORKFLOW STATUS ENDPOINTS ====================


@router.get("/projects/{project_id}/vpc/status")
async def get_vpc_workflow_status(
    project_id: str, current_user: dict = Depends(get_current_user)
):
    """Get the current status of the VPC workflow."""
    try:
        user_id = current_user["user_id"]
        service = get_integrated_vmp_service()
        result = await service.get_vpc_workflow_status(project_id, user_id)

        if result["success"]:
            return {
                "success": True,
                "data": result["status"],
                "message": f"Currently on step: {result['status']['current_step']}",
            }
        else:
            raise HTTPException(status_code=404, detail=result["error"])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get workflow status: {str(e)}"
        )


@router.get(
    "/projects/{project_id}/field-prep/progress",
    response_model=FieldPrepProgressResponse,
)
async def get_field_prep_progress(
    project_id: str, current_user: dict = Depends(get_current_user)
):
    """Get field research preparation progress."""
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        if not tenant_id:
            raise HTTPException(status_code=400, detail="User tenant not found")

        # Get integrated services with adapters
        vmp_service = get_integrated_vmp_service()
        service = get_yuba_field_prep_service(
            vmp_service.auth_adapter,
            vmp_service.db_adapter,
            vmp_service.vector_adapter,
            vmp_service.credit_adapter,
        )
        result = await service.get_progress(project_id=project_id, user_id=user_id)

        if result["success"]:
            return FieldPrepProgressResponse(
                success=True,
                project_id=project_id,
                current_step=result["current_step"],
                completed_steps=result["completed_steps"],
                next_action=result["next_action"],
                progress_percentage=result.get("progress_percentage", 0),
            )
        else:
            raise HTTPException(status_code=404, detail=result["error"])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get field prep progress: {str(e)}"
        )


@router.post(
    "/projects/{project_id}/field-prep/export", response_model=FieldPrepExportResponse
)
async def export_field_prep_artifacts(
    project_id: str,
    request: FieldPrepExportRequest,
    current_user: dict = Depends(get_current_user),
):
    """Export field research preparation artifacts."""
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        if not tenant_id:
            raise HTTPException(status_code=400, detail="User tenant not found")

        # Get integrated services with adapters
        vmp_service = get_integrated_vmp_service()
        service = get_yuba_field_prep_service(
            vmp_service.auth_adapter,
            vmp_service.db_adapter,
            vmp_service.vector_adapter,
            vmp_service.credit_adapter,
        )
        result = await service.export_artifacts(
            project_id=project_id, user_id=user_id, export_format=request.export_format
        )

        if result["success"]:
            export_id = f"export_{project_id}_{request.export_format}_{user_id}"

            return FieldPrepExportResponse(
                export_url=f"/api/v2/vmp/exports/{export_id}/download",
                export_id=export_id,
                export_format=request.export_format,
                status="processing",
                message="Export initiated successfully",
            )
        else:
            raise HTTPException(status_code=400, detail=result["error"])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to export artifacts: {str(e)}"
        )


@router.get("/projects/{project_id}/field-prep/questionnaires/download")
async def download_questionnaires(
    project_id: str,
    format: str = Query(
        ..., regex="^(pdf|docx)$", description="Download format: pdf or docx"
    ),
    current_user: dict = Depends(get_current_user),
):
    """
    Download questionnaires in PDF or Word format with Yuba branding.

    Args:
        project_id: Project ID
        format: Download format (pdf or docx)
        current_user: Authenticated user

    Returns:
        StreamingResponse: File download
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]

        if not tenant_id:
            raise HTTPException(status_code=400, detail="User tenant not found")

        # Get integrated services
        vmp_service = get_integrated_vmp_service()
        service = get_yuba_field_prep_service(
            vmp_service.auth_adapter,
            vmp_service.db_adapter,
            vmp_service.vector_adapter,
            vmp_service.credit_adapter,
        )

        # Get questionnaires from database
        result = await service.get_questionnaires(
            project_id=project_id, user_id=user_id, tenant_id=tenant_id
        )

        if not result["success"]:
            raise HTTPException(status_code=404, detail="Questionnaires not found")

        questionnaires = result.get("questionnaires", [])

        if not questionnaires:
            raise HTTPException(
                status_code=404, detail="No questionnaires found for this project"
            )

        # Get project details
        project_result = await vmp_service.get_project_detail(
            project_id, tenant_id, user_id
        )
        if not project_result["success"]:
            raise HTTPException(status_code=404, detail="Project not found")

        project = project_result["project"]
        project_name = project.get("name", "Untitled Project")

        # Import document generator
        from ..services.document_generator import YubaDocumentGenerator

        generator = YubaDocumentGenerator()

        # Generate document based on format
        if format == "pdf":
            buffer = await generator.generate_questionnaires_pdf(
                questionnaires=questionnaires,
                project_name=project_name,
                project_id=project_id,
            )

            return StreamingResponse(
                buffer,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f"attachment; filename=Yuba_Questionnaires_{project_id}.pdf"
                },
            )
        else:  # docx
            buffer = await generator.generate_questionnaires_docx(
                questionnaires=questionnaires,
                project_name=project_name,
                project_id=project_id,
            )

            return StreamingResponse(
                buffer,
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                headers={
                    "Content-Disposition": f"attachment; filename=Yuba_Questionnaires_{project_id}.docx"
                },
            )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error generating questionnaire download: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to generate document: {str(e)}"
        )


# ============================================================================
# VPC v2 ENDPOINTS (Post-Market Research)
# ============================================================================
# NOTE: The old combined /vpc-v2/generate endpoint has been REMOVED.
# Use the separate phase endpoints instead:
#   - POST /vpc-v2/customer-profile/generate (Phase 1)
#   - POST /vpc-v2/value-map/generate (Phase 2)
# ============================================================================


class VPCv2Response(BaseModel):
    """Response for VPC v2 retrieval"""

    success: bool
    vpc_v2: Optional[Dict[str, Any]] = None
    message: str
    error: Optional[str] = None


class VPCv2UpdateRequest(BaseModel):
    """Request for updating full VPC v2 data (customer profile + value map)"""

    vpc_v2: Optional[Dict[str, Any]] = Field(
        None, description="Updated VPC v2 data (direct format)"
    )
    data: Optional[Dict[str, Any]] = Field(
        None, description="Wrapped format with data.vpc_v2"
    )
    persona_id: Optional[str] = Field(
        None,
        description="Optional persona ID for single-persona update in multi-persona projects",
    )

    def get_vpc_v2(self) -> Dict[str, Any]:
        """Extract VPC v2 data from either format"""
        if self.vpc_v2 is not None:
            return self.vpc_v2
        elif self.data is not None and "vpc_v2" in self.data:
            return self.data["vpc_v2"]
        else:
            raise ValueError("Must provide either 'vpc_v2' or 'data.vpc_v2'")


class VPCv2UpdateResponse(BaseModel):
    """Response for VPC v2 update"""

    success: bool
    vpc_v2: Optional[Dict[str, Any]] = None
    message: str


@router.get("/projects/{project_id}/vpc-v2", response_model=VPCv2Response)
async def get_vpc_v2(project_id: str, current_user: dict = Depends(get_current_user)):
    """
    Retrieve VPC v2 data for a project.
    Automatically returns all personas (single or multiple).

    UNIFIED RESPONSE STRUCTURE:
    vpc_v2 = {P1: {customer_profile: {...}, value_map_candidates: {...}}, P2: {...}}

    This ensures consistent structure for frontend consumption regardless of persona count.

    Args:
        project_id: VMP project ID
        current_user: Authenticated user

    Returns:
        VPCv2Response with VPC v2 data for all personas in unified structure
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]

        if not tenant_id:
            raise HTTPException(status_code=400, detail="User tenant not found")

        # Get integrated services
        vmp_service = get_integrated_vmp_service()

        # Get project data
        project_result = await vmp_service.get_project_detail(
            project_id, tenant_id, user_id
        )

        if not project_result["success"]:
            raise HTTPException(status_code=404, detail="Project not found")

        project = project_result["project"]
        vpc_v2_data = project.get("vpc_v2_data", {})

        if not vpc_v2_data:
            raise HTTPException(
                status_code=404, detail="VPC v2 not found. Generate VPC v2 first."
            )

        personas = project.get("personas", [])

        # NORMALIZE RESPONSE: Ensure unified persona-keyed structure
        # Check if this is legacy flat structure (has customer_profile at root level)
        if vpc_v2_data.get("customer_profile") and not any(
            k.startswith("P") for k in vpc_v2_data.keys()
        ):
            # Legacy flat structure - convert to unified structure for response
            persona_id = personas[0].get("id", "P1") if personas else "P1"
            persona_name = personas[0].get("name") if personas else None

            normalized_vpc_v2 = {
                persona_id: {
                    "customer_profile": vpc_v2_data.get("customer_profile"),
                    "value_map_candidates": vpc_v2_data.get("value_map_candidates"),
                    "value_map_selections": vpc_v2_data.get("value_map_selections"),
                    "status": vpc_v2_data.get("status"),
                    "persona_id": persona_id,
                    "persona_name": persona_name or vpc_v2_data.get("persona_name"),
                    "version": vpc_v2_data.get("version"),
                    "validation_metadata": vpc_v2_data.get("validation_metadata"),
                }
            }
            # Remove None values
            normalized_vpc_v2[persona_id] = {
                k: v for k, v in normalized_vpc_v2[persona_id].items() if v is not None
            }

            print(
                f"🔄 VPC v2 GET: Normalized legacy flat structure to unified structure for persona {persona_id}"
            )
            vpc_v2_data = normalized_vpc_v2

        # Return all personas' VPC v2 data in unified structure
        return VPCv2Response(
            success=True,
            vpc_v2=vpc_v2_data,
            message=f"VPC v2 retrieved successfully for {len(personas)} persona(s)",
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error retrieving VPC v2: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve VPC v2: {str(e)}"
        )


@router.put("/projects/{project_id}/vpc-v2", response_model=VPCv2UpdateResponse)
async def update_vpc_v2(
    project_id: str,
    request: VPCv2UpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Update full VPC v2 data (customer profile + value map + other fields).

    Supports three modes:
    1. Batch update (multi-persona): Send vpc_v2 with P1, P2 keys, omit persona_id
    2. Single-persona update (in multi-persona project): Send single persona data + persona_id
    3. Single-persona project: Send vpc_v2 data, omit persona_id

    Args:
        project_id: VMP project ID
        request: VPC v2 update request with optional persona_id
        current_user: Authenticated user

    Returns:
        VPCv2UpdateResponse with updated VPC v2 data
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]

        if not tenant_id:
            raise HTTPException(status_code=400, detail="User tenant not found")

        # Extract VPC v2 data from request
        try:
            updated_vpc_v2 = request.get_vpc_v2()
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

        # Get integrated services
        vmp_service = get_integrated_vmp_service()

        # Import VPC v2 service
        from ..services.vpc_v2_service import VPCv2Service

        vpc_v2_service = VPCv2Service(
            auth_adapter=vmp_service.auth_adapter,
            db_adapter=vmp_service.db_adapter,
            vector_adapter=vmp_service.vector_adapter,
        )

        # Update VPC v2
        result = await vpc_v2_service.update_vpc_v2(
            project_id=project_id,
            tenant_id=tenant_id,
            persona_id=request.persona_id,
            updated_vpc_v2=updated_vpc_v2,
            user_id=user_id,
        )

        if result["success"]:
            return VPCv2UpdateResponse(
                success=True, vpc_v2=result["vpc_v2"], message=result["message"]
            )
        else:
            raise HTTPException(
                status_code=400, detail=result.get("error", "Failed to update VPC v2")
            )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating VPC v2: {e}")
        import traceback

        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Failed to update VPC v2: {str(e)}"
        )


class VPCComparisonResponse(BaseModel):
    """Response for VPC v1 vs VPC v2 comparison"""

    success: bool
    comparison: Optional[Dict[str, Any]] = None
    message: str


@router.get(
    "/projects/{project_id}/vpc-v2/comparison", response_model=VPCComparisonResponse
)
async def get_vpc_comparison(
    project_id: str, current_user: dict = Depends(get_current_user)
):
    """
    Get side-by-side comparison of VPC v1 vs VPC v2.
    Shows what changed and why with evidence citations.
    Automatically returns comparison for all personas.

    Args:
        project_id: VMP project ID
        current_user: Authenticated user

    Returns:
        VPCComparisonResponse with comparison data for all personas
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]

        if not tenant_id:
            raise HTTPException(status_code=400, detail="User tenant not found")

        # Get integrated services
        vmp_service = get_integrated_vmp_service()

        # Get project data
        project_result = await vmp_service.get_project_detail(
            project_id, tenant_id, user_id
        )

        if not project_result["success"]:
            raise HTTPException(status_code=404, detail="Project not found")

        project = project_result["project"]
        vpc_data = project.get("vpc_data", {})
        vpc_v2_data = project.get("vpc_v2_data", {})

        if not vpc_v2_data:
            raise HTTPException(
                status_code=404, detail="VPC v2 not found. Generate VPC v2 first."
            )

        personas = project.get("personas", [])

        # Get VPC v1 and v2 data for all personas
        if len(personas) > 1:
            # Multi-persona: Return comparison for all personas
            comparisons = {}
            for persona in personas:
                persona_id = persona.get("id")
                vpc_v1_profile = (
                    vpc_data.get("vpcs", {})
                    .get(persona_id, {})
                    .get("customer_profile", {})
                )
                vpc_v2 = vpc_v2_data.get(persona_id, {})
                if vpc_v1_profile and vpc_v2:
                    comparisons[persona_id] = {
                        "vpc_v1": {"customer_profile": vpc_v1_profile},
                        "vpc_v2": vpc_v2,
                    }

            if not comparisons:
                raise HTTPException(
                    status_code=404, detail="No VPC data found for comparison"
                )

            return VPCComparisonResponse(
                success=True,
                comparison=comparisons,
                message=f"VPC comparison retrieved for {len(comparisons)} personas",
            )
        else:
            # Single persona: Get from root
            vpc_v1_profile = vpc_data.get("customer_profile", {})
            vpc_v2 = vpc_v2_data

        if not vpc_v1_profile:
            raise HTTPException(
                status_code=404, detail="VPC v1 customer profile not found"
            )

        # Build comparison
        comparison = {
            "vpc_v1": {"customer_profile": vpc_v1_profile},
            "vpc_v2": {
                "customer_profile": vpc_v2.get("customer_profile", {}),
                "value_map": vpc_v2.get("value_map", {}),
                "validation_metadata": vpc_v2.get("validation_metadata", {}),
            },
            "changes": vpc_v2.get("customer_profile", {}).get("change_log", {}),
            "persona_name": vpc_v2.get("persona_name", "Target Persona"),
        }

        return VPCComparisonResponse(
            success=True,
            comparison=comparison,
            message="VPC comparison retrieved successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error retrieving VPC comparison: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve VPC comparison: {str(e)}"
        )


class ValueMapSelectionsRequest(BaseModel):
    """Request for value map selections (user chooses 3 from 5 candidates)"""

    # Single persona format (backward compatibility)
    persona_id: Optional[str] = Field(
        None, description="Persona ID for single persona selection"
    )
    selected_product_ids: Optional[List[str]] = Field(
        None, min_items=3, max_items=3, description="Selected product/service IDs"
    )
    selected_pain_reliever_ids: Optional[List[str]] = Field(
        None, min_items=3, max_items=3, description="Selected pain reliever IDs"
    )
    selected_gain_creator_ids: Optional[List[str]] = Field(
        None, min_items=3, max_items=3, description="Selected gain creator IDs"
    )

    # Multi-persona batch format (NEW - matches VPC V1 pattern)
    persona_selections: Optional[Dict[str, Dict[str, List[str]]]] = Field(
        None,
        description="Batch selections for multiple personas. Format: {'P1': {'selected_product_ids': [...], 'selected_pain_reliever_ids': [...], 'selected_gain_creator_ids': [...]}, 'P2': {...}}",
    )


class ValueMapSelectionsResponse(BaseModel):
    """Response for value map selections"""

    success: bool
    selections: Optional[Dict[str, Any]] = None
    message: str


@router.post(
    "/projects/{project_id}/vpc-v2/value-map-selections",
    response_model=ValueMapSelectionsResponse,
)
async def save_value_map_selections(
    project_id: str,
    request: ValueMapSelectionsRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Save user's value map selections (3 from each category of 5 candidates).

    Similar to customer profile selection in VPC v1, users are presented with
    5 candidates for each category and must select exactly 3.

    Args:
        project_id: VMP project ID
        request: Value map selections request
        current_user: Authenticated user

    Returns:
        ValueMapSelectionsResponse with saved selections
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]

        if not tenant_id:
            raise HTTPException(status_code=400, detail="User tenant not found")

        # Get integrated services
        vmp_service = get_integrated_vmp_service()

        # Import VPC v2 service
        from ..services.vpc_v2_service import VPCv2Service

        vpc_v2_service = VPCv2Service(
            auth_adapter=vmp_service.auth_adapter,
            db_adapter=vmp_service.db_adapter,
            vector_adapter=vmp_service.vector_adapter,
        )

        # BATCH PROCESSING: Support both single and multi-persona selections
        if request.persona_selections:
            # DEBUG: Show what keys are being sent
            print(
                f"🔍 ENDPOINT DEBUG: persona_selections keys: {list(request.persona_selections.keys())}"
            )
            for key in request.persona_selections.keys():
                print(
                    f"🔍 ENDPOINT DEBUG: persona_selections[{key}] = {request.persona_selections[key]}"
                )

            # Multi-persona batch selections (NEW - matches VPC V1 pattern)
            result = await vpc_v2_service.save_value_map_selections_batch(
                project_id=project_id,
                tenant_id=tenant_id,
                user_id=user_id,
                persona_selections=request.persona_selections,
            )

            if result["success"]:
                # Invalidate completed value maps list cache after successful selection (Requirement 5.7)
                from src.mint.api.cache.entity_cache_service import EntityType

                invalidation_service = get_invalidation_service()
                if invalidation_service:
                    await invalidation_service.on_feature_completed(
                        feature_entity=EntityType.VALUE_MAP,
                        project_id=project_id,
                        tenant_id=tenant_id,
                        background=True,
                    )

                return {
                    "success": True,
                    "value_map_selections": result["value_map_selections"],
                    "personas_processed": result["personas_processed"],
                    "message": result["message"],
                }
            else:
                raise HTTPException(
                    status_code=400,
                    detail=result.get("error", "Failed to save selections"),
                )
        else:
            # Single persona selection (backward compatibility)
            if (
                not request.selected_product_ids
                or not request.selected_pain_reliever_ids
                or not request.selected_gain_creator_ids
            ):
                raise HTTPException(
                    status_code=400,
                    detail="Must provide either persona_selections (batch) or individual selection fields (single persona)",
                )

            result = await vpc_v2_service.save_value_map_selections(
                project_id=project_id,
                tenant_id=tenant_id,
                persona_id=request.persona_id,
                selected_product_ids=request.selected_product_ids,
                selected_pain_reliever_ids=request.selected_pain_reliever_ids,
                selected_gain_creator_ids=request.selected_gain_creator_ids,
            )

            if result["success"]:
                # Invalidate completed value maps list cache after successful selection (Requirement 5.7)
                from src.mint.api.cache.entity_cache_service import EntityType

                invalidation_service = get_invalidation_service()
                if invalidation_service:
                    await invalidation_service.on_feature_completed(
                        feature_entity=EntityType.VALUE_MAP,
                        project_id=project_id,
                        tenant_id=tenant_id,
                        background=True,
                    )

                return ValueMapSelectionsResponse(
                    success=True,
                    selections=result["selections"],
                    message=result["message"],
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail=result.get("error", "Failed to save selections"),
                )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error saving value map selections: {e}")
        import traceback

        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Failed to save value map selections: {str(e)}"
        )


class CustomerProfileUpdateRequest(BaseModel):
    """Request for updating VPC v2 customer profile"""

    customer_profile: Optional[Dict[str, Any]] = Field(
        None, description="Updated customer profile (direct format)"
    )
    data: Optional[Dict[str, Any]] = Field(
        None, description="Wrapped format with data.customer_profile"
    )
    persona_id: Optional[str] = Field(
        None,
        description="Optional persona ID for single-persona update in multi-persona projects",
    )

    def get_customer_profile(self) -> Dict[str, Any]:
        """Extract customer profile from either format"""
        if self.customer_profile is not None:
            return self.customer_profile
        elif self.data is not None and "customer_profile" in self.data:
            return self.data["customer_profile"]
        else:
            raise ValueError(
                "Must provide either 'customer_profile' or 'data.customer_profile'"
            )


class CustomerProfileUpdateResponse(BaseModel):
    """Response for customer profile update"""

    success: bool
    customer_profile: Optional[Dict[str, Any]] = None
    message: str


class ValueMapUpdateRequest(BaseModel):
    """Request for updating VPC v2 value map selections"""

    value_map_selections: Optional[Dict[str, Any]] = Field(
        None, description="Updated value map selections (direct format)"
    )
    data: Optional[Dict[str, Any]] = Field(
        None, description="Wrapped format with data.value_map_selections"
    )
    persona_id: Optional[str] = Field(
        None,
        description="Optional persona ID for single-persona update in multi-persona projects",
    )

    def get_value_map_selections(self) -> Dict[str, Any]:
        """Extract value map selections from either format"""
        if self.value_map_selections is not None:
            return self.value_map_selections
        elif self.data is not None and "value_map_selections" in self.data:
            return self.data["value_map_selections"]
        else:
            raise ValueError(
                "Must provide either 'value_map_selections' or 'data.value_map_selections'"
            )


class ValueMapUpdateResponse(BaseModel):
    """Response for value map update"""

    success: bool
    value_map_selections: Optional[Dict[str, Any]] = None
    message: str


@router.put(
    "/projects/{project_id}/vpc-v2/value-map", response_model=ValueMapUpdateResponse
)
async def update_vpc_v2_value_map(
    project_id: str,
    request: ValueMapUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Update VPC v2 value map selections.

    Supports three modes:
    1. Batch update (multi-persona): Send value_map_selections with P1, P2 keys, omit persona_id
    2. Single-persona update (in multi-persona project): Send single persona data + persona_id
    3. Single-persona project: Send value map selections, omit persona_id

    Args:
        project_id: VMP project ID
        request: Value map update request with optional persona_id
        current_user: Authenticated user

    Returns:
        ValueMapUpdateResponse with updated selections
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]

        if not tenant_id:
            raise HTTPException(status_code=400, detail="User tenant not found")

        # Extract value map selections from request
        try:
            updated_selections = request.get_value_map_selections()
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

        # Get integrated services
        vmp_service = get_integrated_vmp_service()

        # Import VPC v2 service
        from ..services.vpc_v2_service import VPCv2Service

        vpc_v2_service = VPCv2Service(
            auth_adapter=vmp_service.auth_adapter,
            db_adapter=vmp_service.db_adapter,
            vector_adapter=vmp_service.vector_adapter,
        )

        # Update value map selections
        result = await vpc_v2_service.update_value_map_selections(
            project_id=project_id,
            tenant_id=tenant_id,
            persona_id=request.persona_id,  # ✅ Now passed from request
            updated_selections=updated_selections,
        )

        if result["success"]:
            return ValueMapUpdateResponse(
                success=True,
                value_map_selections=result["value_map_selections"],
                message=result["message"],
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Failed to update value map"),
            )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating VPC v2 value map: {e}")
        import traceback

        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Failed to update value map: {str(e)}"
        )


# ============================================================================
# VPC v2 SEPARATE ENDPOINTS (Customer Profile & Value Map)
# ============================================================================


class CustomerProfileV2Response(BaseModel):
    """Response for VPC v2 customer profile generation"""

    success: bool
    customer_profile: Optional[Dict[str, Any]] = None
    message: str
    error: Optional[str] = None


class ValueMapV2Response(BaseModel):
    """Response for VPC v2 value map generation"""

    success: bool
    value_map_candidates: Optional[Dict[str, Any]] = None
    message: str
    error: Optional[str] = None


@router.post(
    "/projects/{project_id}/vpc-v2/customer-profile/generate",
    response_model=CustomerProfileV2Response,
)
async def generate_vpc_v2_customer_profile(
    project_id: str,
    request: VPCv2GenerationRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    PHASE 1: Generate VPC v2 customer profile only.

    This is the first step in VPC v2 workflow. It refines the VPC v1 customer profile
    with market research insights, adding research-backed details while preserving
    the original structure with labels, evidence, and confidence scores.

    Args:
        project_id: VMP project ID
        request: VPC v2 generation request with optional persona_id
        current_user: Authenticated user

    Returns:
        CustomerProfileV2Response with refined customer profile
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        plan_type = current_user.get("tenant_type", "individual")

        if not tenant_id:
            raise HTTPException(status_code=400, detail="User tenant not found")

        # Credit check - resolve feature name to UUID
        from src.mint.api.features.dependencies import resolve_feature_id

        feature_id = await resolve_feature_id("Customer Profile v2")
        user_roles = current_user.get("roles", [])
        is_super_admin = len(user_roles) > 0 and user_roles[0] == "super_admin"

        if not is_super_admin and not credit_service.has_sufficient_credits_for_feature(
            tenant_id=tenant_id,
            feature_id=feature_id,
            plan_type=plan_type,
        ):
            raise HTTPException(
                status_code=402,
                detail={
                    "code": "insufficient_credits",
                    "message": "You do not have enough credits for this feature.",
                },
            )

        # Get integrated services
        vmp_service = get_integrated_vmp_service()

        # Import VPC v2 service
        from ..services.vpc_v2_service import VPCv2Service

        vpc_v2_service = VPCv2Service(
            auth_adapter=vmp_service.auth_adapter,
            db_adapter=vmp_service.db_adapter,
            vector_adapter=vmp_service.vector_adapter,
        )

        # AUTOMATIC BATCH PROCESSING: Always generate for all personas
        # Backend automatically detects single vs multi-persona projects
        result = await vpc_v2_service.generate_customer_profile_v2_batch(
            project_id=project_id, tenant_id=tenant_id, user_id=user_id
        )

        if result["success"]:
            # Consume credits after successful generation
            if not is_super_admin:
                try:
                    request_id = str(uuid.uuid4())
                    credit_service.consume_feature(
                        tenant_id=tenant_id,
                        user_id=user_id,
                        feature_id=feature_id,
                        plan_type=plan_type,
                        request_id=request_id,
                        reason="vpc_v2_customer_profile_generation",
                        project_id=project_id,
                        metadata={
                            "personas_processed": result.get("personas_processed", [])
                        },
                    )
                except Exception as credit_error:
                    print(f"⚠️ Credit consumption failed (non-blocking): {credit_error}")

            return {
                "success": True,
                "customer_profiles": result["customer_profiles"],
                "personas_processed": result["personas_processed"],
                "message": result["message"],
            }
        else:
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Customer profile generation failed"),
            )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error generating VPC v2 customer profile: {e}")
        import traceback

        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Failed to generate customer profile: {str(e)}"
        )


@router.get("/projects/{project_id}/vpc-v2/customer-profile")
async def get_vpc_v2_customer_profile(
    project_id: str, current_user: dict = Depends(get_current_user)
):
    """
    Retrieve VPC v2 customer profiles for a project.
    Automatically returns all personas (single or multiple).

    UNIFIED RESPONSE STRUCTURE:
    customer_profiles = {P1: {customer_profile: {...}}, P2: {...}}

    Args:
        project_id: VMP project ID
        current_user: Authenticated user

    Returns:
        Dict with customer profiles for all personas in unified structure
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]

        if not tenant_id:
            raise HTTPException(status_code=400, detail="User tenant not found")

        # Get integrated services
        vmp_service = get_integrated_vmp_service()

        # Get project
        project = await vmp_service.db_adapter.get_vmp_project(project_id, tenant_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        vpc_v2_data = project.get("vpc_v2_data", {})

        if not vpc_v2_data:
            raise HTTPException(
                status_code=404,
                detail="VPC v2 customer profiles not found. Generate them first.",
            )

        personas = project.get("personas", [])

        # UNIFIED STRUCTURE: Always return persona-keyed format
        # Check if this is legacy flat structure
        if vpc_v2_data.get("customer_profile") and not any(
            k.startswith("P") for k in vpc_v2_data.keys()
        ):
            # Legacy flat structure - normalize to unified structure
            persona_id = personas[0].get("id", "P1") if personas else "P1"
            customer_profiles = {persona_id: vpc_v2_data}
            print(
                f"🔄 Customer Profile GET: Normalized legacy flat structure for persona {persona_id}"
            )
        else:
            # Already in unified structure - extract customer profiles
            customer_profiles = {}
            for persona_id, persona_data in vpc_v2_data.items():
                if isinstance(persona_data, dict) and persona_data.get(
                    "customer_profile"
                ):
                    customer_profiles[persona_id] = persona_data

        if not customer_profiles:
            raise HTTPException(
                status_code=404, detail="VPC v2 customer profiles not found"
            )

        return {
            "success": True,
            "customer_profiles": customer_profiles,
            "personas_processed": list(customer_profiles.keys()),
            "message": f"Customer profiles retrieved successfully for {len(customer_profiles)} persona(s)",
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error retrieving VPC v2 customer profile: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve customer profile: {str(e)}"
        )


@router.put(
    "/projects/{project_id}/vpc-v2/customer-profile",
    response_model=CustomerProfileV2Response,
)
async def update_vpc_v2_customer_profile(
    project_id: str,
    request: CustomerProfileUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Update VPC v2 customer profile.

    Supports three modes:
    1. Batch update (multi-persona): Send customer_profile with P1, P2 keys, omit persona_id
    2. Single-persona update (in multi-persona project): Send single persona data + persona_id
    3. Single-persona project: Send customer profile, omit persona_id

    Args:
        project_id: VMP project ID
        request: Customer profile update request with optional persona_id
        current_user: Authenticated user

    Returns:
        CustomerProfileV2Response with updated customer profile
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]

        if not tenant_id:
            raise HTTPException(status_code=400, detail="User tenant not found")

        # Extract customer profile from request (supports both formats)
        try:
            customer_profile = request.get_customer_profile()
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

        # Get integrated services
        vmp_service = get_integrated_vmp_service()

        # Import VPC v2 service
        from ..services.vpc_v2_service import VPCv2Service

        vpc_v2_service = VPCv2Service(
            auth_adapter=vmp_service.auth_adapter,
            db_adapter=vmp_service.db_adapter,
            vector_adapter=vmp_service.vector_adapter,
        )

        # Update customer profile
        result = await vpc_v2_service.update_customer_profile(
            project_id=project_id,
            tenant_id=tenant_id,
            persona_id=request.persona_id,
            updated_profile=customer_profile,
            user_id=user_id,
        )

        if result["success"]:
            return CustomerProfileV2Response(
                success=True,
                customer_profile=result["customer_profile"],
                message=result["message"],
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Failed to update customer profile"),
            )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating VPC v2 customer profile: {e}")
        import traceback

        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Failed to update customer profile: {str(e)}"
        )


@router.post(
    "/projects/{project_id}/vpc-v2/value-map/generate",
    response_model=ValueMapV2Response,
)
async def generate_vpc_v2_value_map(
    project_id: str,
    request: VPCv2GenerationRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    PHASE 2: Generate VPC v2 value map candidates.

    This is the second step in VPC v2 workflow (after customer profile). It generates
    5 value map candidates per category (Products/Services, Pain Relievers, Gain Creators)
    for the user to select from.

    Requires: VPC v2 customer profile must be generated first (Phase 1).

    Args:
        project_id: VMP project ID
        request: VPC v2 generation request with optional persona_id
        current_user: Authenticated user

    Returns:
        ValueMapV2Response with value map candidates
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        plan_type = current_user.get("tenant_type", "individual")

        if not tenant_id:
            raise HTTPException(status_code=400, detail="User tenant not found")

        # Credit check - resolve feature name to UUID
        from src.mint.api.features.dependencies import resolve_feature_id

        feature_id = await resolve_feature_id("Value Map Generator")
        user_roles = current_user.get("roles", [])
        is_super_admin = len(user_roles) > 0 and user_roles[0] == "super_admin"

        if not is_super_admin and not credit_service.has_sufficient_credits_for_feature(
            tenant_id=tenant_id,
            feature_id=feature_id,
            plan_type=plan_type,
        ):
            raise HTTPException(
                status_code=402,
                detail={
                    "code": "insufficient_credits",
                    "message": "You do not have enough credits for this feature.",
                },
            )

        # Get integrated services
        vmp_service = get_integrated_vmp_service()

        # Import VPC v2 service
        from ..services.vpc_v2_service import VPCv2Service

        vpc_v2_service = VPCv2Service(
            auth_adapter=vmp_service.auth_adapter,
            db_adapter=vmp_service.db_adapter,
            vector_adapter=vmp_service.vector_adapter,
        )

        # AUTOMATIC BATCH PROCESSING: Always generate for all personas
        # Backend automatically detects single vs multi-persona projects
        result = await vpc_v2_service.generate_value_map_v2_batch(
            project_id=project_id, tenant_id=tenant_id, user_id=user_id
        )

        if result["success"]:
            # Consume credits after successful generation
            if not is_super_admin:
                try:
                    request_id = str(uuid.uuid4())
                    credit_service.consume_feature(
                        tenant_id=tenant_id,
                        user_id=user_id,
                        feature_id=feature_id,
                        plan_type=plan_type,
                        request_id=request_id,
                        reason="vpc_v2_value_map_generation",
                        project_id=project_id,
                        metadata={
                            "personas_processed": result.get("personas_processed", [])
                        },
                    )
                except Exception as credit_error:
                    print(f"⚠️ Credit consumption failed (non-blocking): {credit_error}")

            return {
                "success": True,
                "value_map_candidates": result["value_map_candidates"],
                "personas_processed": result["personas_processed"],
                "message": result["message"],
            }
        else:
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Value map generation failed"),
            )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error generating VPC v2 value map: {e}")
        import traceback

        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Failed to generate value map: {str(e)}"
        )


@router.get("/projects/{project_id}/vpc-v2/value-map-candidates")
async def get_vpc_v2_value_map_candidates(
    project_id: str, current_user: dict = Depends(get_current_user)
):
    """
    Get previously generated value map candidates (before selection).
    This endpoint ONLY returns candidates, matching VPC V1 pattern.

    UNIFIED RESPONSE STRUCTURE:
    value_map_candidates = {P1: {products_services_candidates: [...], ...}, P2: {...}}

    Args:
        project_id: VMP project ID
        current_user: Authenticated user

    Returns:
        Dict with value map candidates for all personas in unified structure
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]

        if not tenant_id:
            raise HTTPException(status_code=400, detail="User tenant not found")

        # Get integrated services
        vmp_service = get_integrated_vmp_service()

        # Get project
        project = await vmp_service.db_adapter.get_vmp_project(project_id, tenant_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        vpc_v2_data = project.get("vpc_v2_data", {})

        if not vpc_v2_data:
            raise HTTPException(
                status_code=404,
                detail="VPC v2 data not found. Generate customer profiles first.",
            )

        personas = project.get("personas", [])
        value_map_candidates = {}

        # UNIFIED STRUCTURE: Always use persona-keyed format
        # Check if this is legacy flat structure
        if vpc_v2_data.get("value_map_candidates") and not any(
            k.startswith("P") for k in vpc_v2_data.keys()
        ):
            # Legacy flat structure - normalize to unified structure
            persona_id = personas[0].get("id", "P1") if personas else "P1"
            persona_name = personas[0].get("name") if personas else None
            candidates = vpc_v2_data.get("value_map_candidates")
            if persona_name and isinstance(candidates, dict):
                candidates["persona_name"] = persona_name
            value_map_candidates[persona_id] = candidates
            print(
                f"🔄 Value Map Candidates GET: Normalized legacy flat structure for persona {persona_id}"
            )
        else:
            # Already in unified structure - extract candidates
            for persona_id, persona_data in vpc_v2_data.items():
                if not isinstance(persona_data, dict):
                    continue

                # ONLY return candidates, not selections
                if persona_data.get("value_map_candidates"):
                    value_map_candidates[persona_id] = persona_data.get(
                        "value_map_candidates"
                    )

            # Enrich with persona names
            try:
                persona_name_map = {p.get("id"): p.get("name") for p in personas}
                for persona_id in value_map_candidates.keys():
                    if persona_id in persona_name_map and isinstance(
                        value_map_candidates[persona_id], dict
                    ):
                        value_map_candidates[persona_id]["persona_name"] = (
                            persona_name_map[persona_id]
                        )
            except Exception:
                pass

        if not value_map_candidates:
            raise HTTPException(
                status_code=404,
                detail="No value map candidates found. Please generate them first.",
            )

        return {
            "success": True,
            "data": {
                "project_id": project_id,
                "value_map_candidates": value_map_candidates,
                "personas_processed": list(value_map_candidates.keys()),
                "generated_at": vpc_v2_data.get(
                    list(value_map_candidates.keys())[0], {}
                ).get("updated_at")
                if value_map_candidates
                else None,
            },
            "message": f"Value map candidates retrieved successfully for {len(value_map_candidates)} persona(s)",
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error retrieving VPC v2 value map candidates: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve value map candidates: {str(e)}"
        )


@router.get("/projects/{project_id}/vpc-v2/value-map-selections")
async def get_vpc_v2_value_map_selections(
    project_id: str, current_user: dict = Depends(get_current_user)
):
    """
    Get previously selected value map items.
    This endpoint ONLY returns selections, matching VPC V1 pattern.

    UNIFIED RESPONSE STRUCTURE:
    value_map_selections = {P1: {products_services: [...], ...}, P2: {...}}

    Args:
        project_id: VMP project ID
        current_user: Authenticated user

    Returns:
        Dict with value map selections for all personas in unified structure
    """
    try:
        import copy

        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]

        if not tenant_id:
            raise HTTPException(status_code=400, detail="User tenant not found")

        print(
            f"🔍 DEBUG: [GET_VM_SELECTIONS] Getting selections for project_id={project_id}, user_id={user_id}"
        )

        # Get integrated services
        vmp_service = get_integrated_vmp_service()

        # Get project
        project = await vmp_service.db_adapter.get_vmp_project(project_id, tenant_id)
        if not project:
            print(f"❌ DEBUG: [GET_VM_SELECTIONS] No project data found")
            raise HTTPException(status_code=404, detail="Project not found")

        print(
            f"🔍 DEBUG: [GET_VM_SELECTIONS] Project data keys: {list(project.keys())}"
        )

        vpc_v2_data = project.get("vpc_v2_data", {})
        print(
            f"🔍 DEBUG: [GET_VM_SELECTIONS] VPC v2 data keys: {list(vpc_v2_data.keys())}"
        )

        if not vpc_v2_data:
            raise HTTPException(
                status_code=404,
                detail="VPC v2 data not found. Generate customer profiles first.",
            )

        personas = project.get("personas", [])
        value_map_selections = {}

        # UNIFIED STRUCTURE: Always use persona-keyed format
        # Check if this is legacy flat structure
        if vpc_v2_data.get("value_map_selections") and not any(
            k.startswith("P") for k in vpc_v2_data.keys()
        ):
            # Legacy flat structure - normalize to unified structure
            persona_id = personas[0].get("id", "P1") if personas else "P1"
            value_map_selections[persona_id] = copy.deepcopy(
                vpc_v2_data.get("value_map_selections")
            )
            print(
                f"🔄 Value Map Selections GET: Normalized legacy flat structure for persona {persona_id}"
            )
        else:
            # Already in unified structure - extract selections
            for persona_id, persona_data in vpc_v2_data.items():
                if not isinstance(persona_data, dict):
                    continue

                # ONLY return selections, not candidates
                if persona_data.get("value_map_selections"):
                    value_map_selections[persona_id] = copy.deepcopy(
                        persona_data.get("value_map_selections")
                    )

        if not value_map_selections:
            print(f"❌ DEBUG: [GET_VM_SELECTIONS] No selections found")
            raise HTTPException(
                status_code=404,
                detail="No value map selections found. Please select value maps first.",
            )

        print(
            f"🔍 DEBUG: [GET_VM_SELECTIONS] Combined selections: {len(value_map_selections)} personas"
        )

        return {
            "success": True,
            "data": {
                "project_id": project_id,
                "value_map_selections": value_map_selections,
                "personas_processed": list(value_map_selections.keys()),
                "format": "multi_persona" if len(personas) > 1 else "single_persona",
                "selected_at": vpc_v2_data.get(
                    list(value_map_selections.keys())[0], {}
                ).get("updated_at")
                if value_map_selections
                else None,
            },
            "message": f"Value map selections retrieved successfully for {len(value_map_selections)} persona(s)",
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error retrieving VPC v2 value map selections: {e}")
        import traceback

        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve value map selections: {str(e)}"
        )
