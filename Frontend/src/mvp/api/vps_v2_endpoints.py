"""
VPS v2 API Endpoints (Separate router for Swagger ordering)

These endpoints are in a separate file to ensure they appear after
Solution Critique endpoints in Swagger UI.
"""

from fastapi import APIRouter, Depends, HTTPException
import logging
import time

from src.mint.api.auth_v2.utils import get_current_user
from src.mint.api.credit.service import CreditService

from .models import (
    VPSV2GenerationRequest,
    VPSEditRequest,
    VPSResponse,
    VPSDetailResponse,
    ErrorResponse
)
from ..services.vps_service import get_vps_service

router = APIRouter(prefix="/api/v2/mvp", tags=["MVP - Value Proposition"])
logger = logging.getLogger(__name__)

credit_service = CreditService()


# ==================== VPS V2 ENDPOINTS ====================

@router.post(
    "/projects/{project_id}/vps/v2/generate",
    response_model=VPSResponse,
    responses={
        402: {"model": ErrorResponse, "description": "Insufficient credits"},
        404: {"model": ErrorResponse, "description": "Project or VPS v1 not found"},
        400: {"model": ErrorResponse, "description": "VPS v1 or Solution Critique not found"}
    }
)
async def generate_vps_v2(
    project_id: str,
    request: VPSV2GenerationRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Generate Value Proposition Statement v2 (critique-driven refinement).
    
    **Prerequisites**:
    - VPS v1 must exist
    - Solution Critique must be completed
    
    **Process**:
    - Uses RAG to retrieve relevant critique chunks dynamically
    - AI analyzes critique feedback against VPS v1
    - Decides refinement scope: no_changes, partial_refinement, or full_refinement
    - Generates refined VPS v2 with reasons and evidence for each change
    - Tracks critique sources and how concerns were addressed
    
    **Cost**: 1 credit (bypassed for super admins)
    
    **Returns**: 
    - Refined VPS v2 (same format as v1)
    - Refinement metadata (decision, rationale, changes tracking)
    - Critique sources used with citations
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        plan_type = current_user.get("tenant_type", "individual")
        user_roles = current_user.get("roles", [])
        
        logger.info(f"VPS v2 generation request from user {user_id} for project {project_id}")
        
        # Check if super admin
        is_super_admin = len(user_roles) > 0 and user_roles[0] == "super_admin"
        
        # Credit check - resolve feature name to UUID
        from src.mint.api.features.dependencies import resolve_feature_id
        feature_id = await resolve_feature_id("Value Proposition Statement v2")
        if not is_super_admin:
            has_credits = credit_service.has_sufficient_credits_for_feature(
                tenant_id=tenant_id,
                feature_id=feature_id,
                plan_type=plan_type
            )
            if not has_credits:
                raise HTTPException(
                    status_code=402,
                    detail="Insufficient credits for VPS v2 generation"
                )
        else:
            logger.info(f"✅ Super admin {user_id} bypassing credit check for VPS v2 generation")
        
        # Initialize service
        vps_service = get_vps_service()
        
        # Generate VPS v2 (RAG automatically retrieves critique chunks)
        result = await vps_service.generate_vps_v2(
            project_id=project_id,
            tenant_id=tenant_id,
            user_id=user_id,
            creativity_level=request.creativity_level
        )
        
        # Consume credits (bypass for super admins)
        if not is_super_admin:
            try:
                import uuid
                credit_service.consume_feature(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    feature_id=feature_id,
                    plan_type=plan_type,
                    request_id=str(uuid.uuid4()),
                    reason="VPS v2 generation",
                    project_id=project_id
                )
                logger.info(f"✅ Consumed 1 credit for VPS v2 generation")
            except Exception as e:
                logger.error(f"❌ Failed to consume credits: {e}")
        
        # Invalidate completed VPS v2 list cache after successful generation (Requirement 5.7)
        from src.mint.api.cache.invalidation_service import get_invalidation_service
        from src.mint.api.cache.entity_cache_service import EntityType
        invalidation_service = get_invalidation_service()
        if invalidation_service:
            await invalidation_service.on_feature_completed(
                feature_entity=EntityType.VPS_V2,
                project_id=project_id,
                tenant_id=tenant_id,
                background=True
            )
        
        return VPSResponse(
            success=True,
            data=result,
            message=result['message']
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating VPS v2: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate VPS v2: {str(e)}"
        )


@router.get(
    "/projects/{project_id}/vps/v2",
    response_model=VPSDetailResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Project or VPS v2 not found"}
    }
)
async def get_vps_v2(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get VPS v2 for a project.
    
    **Returns**: VPS v2 data with refinement metadata, or null if not generated yet
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        
        vps_service = get_vps_service()
        
        # Get VPS v2 data
        from ..adapters.database_adapter import get_mvp_database_adapter
        mvp_adapter = get_mvp_database_adapter()
        
        vps_data = mvp_adapter.get_vps_v2(project_id, tenant_id)
        current_version = vps_service.get_current_version(project_id, tenant_id)
        
        if vps_data:
            return VPSDetailResponse(
                success=True,
                vps_data=vps_data,
                project_id=project_id,
                current_version=current_version,
                message="VPS v2 retrieved successfully"
            )
        else:
            return VPSDetailResponse(
                success=True,
                vps_data=None,
                project_id=project_id,
                current_version=current_version,
                message="VPS v2 not found. Generate it first."
            )
        
    except Exception as e:
        logger.error(f"Error retrieving VPS v2: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve VPS v2: {str(e)}"
        )


@router.put(
    "/projects/{project_id}/vps/v2",
    response_model=VPSResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Project or VPS v2 not found"},
        400: {"model": ErrorResponse, "description": "Invalid update data"},
        422: {"model": ErrorResponse, "description": "Validation error"}
    }
)
async def update_vps_v2(
    project_id: str,
    request: VPSEditRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Update VPS v2 for a project (multi-persona support).
    
    **Accepts EITHER:**
    1. Full GET response: `{"success": true, "vps_data": [...], ...}`
    2. Wrapped format: `{"vps_data": [{persona1_vps}, {persona2_vps}]}`
    
    **Copy-paste friendly**: You can copy the entire GET response, modify it, and send it back.
    
    **Returns**: Updated VPS v2 data array
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        
        # Extract VPS data from request
        try:
            vps_data = request.get_vps_data()
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))
        
        # Validate VPS data
        if not vps_data or len(vps_data) == 0:
            raise HTTPException(
                status_code=400,
                detail="vps_data array cannot be empty. Provide at least one VPS object."
            )
        
        if len(vps_data) > 2:
            raise HTTPException(
                status_code=400,
                detail="vps_data array cannot have more than 2 items (max 2 personas)."
            )
        
        # Validate each VPS has required fields
        for idx, vps in enumerate(vps_data):
            if 'primary_statement' not in vps:
                raise HTTPException(
                    status_code=400,
                    detail=f"VPS at index {idx} missing required field: primary_statement"
                )
            if 'extended_statement' not in vps:
                raise HTTPException(
                    status_code=400,
                    detail=f"VPS at index {idx} missing required field: extended_statement"
                )
            if 'key_differentiators' not in vps:
                raise HTTPException(
                    status_code=400,
                    detail=f"VPS at index {idx} missing required field: key_differentiators"
                )
        
        # Update metadata for each VPS
        from datetime import datetime
        for vps in vps_data:
            if 'generation_metadata' not in vps:
                vps['generation_metadata'] = {}
            vps['generation_metadata']['last_updated_at'] = datetime.utcnow().isoformat()
            vps['generation_metadata']['last_updated_by'] = user_id
        
        # Save to database
        from ..adapters.database_adapter import get_mvp_database_adapter
        mvp_adapter = get_mvp_database_adapter()
        
        success = mvp_adapter.save_vps_v2(
            project_id=project_id,
            tenant_id=tenant_id,
            vps_data=vps_data,
            user_id=user_id
        )
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to save VPS v2 to database"
            )
        
        # Get updated data
        updated_vps = mvp_adapter.get_vps_v2(project_id, tenant_id)
        
        logger.info(f"✅ Successfully updated {len(vps_data)} VPS v2 for project {project_id}")
        
        return VPSResponse(
            success=True,
            data={"vps_v2": updated_vps, "project_id": project_id, "vps_count": len(vps_data)},
            message=f"VPS v2 updated successfully ({len(vps_data)} persona(s))"
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating VPS v2: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update VPS: {str(e)}"
        )
