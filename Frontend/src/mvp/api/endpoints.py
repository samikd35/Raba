"""
MVP Module API Endpoints

FastAPI routes for VPS generation and management.
Includes credit system integration with super admin bypass.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any
import logging
import time

from src.mint.api.auth_v2.utils import get_current_user
from src.mint.api.credit.service import CreditService

from .models import (
    VPSGenerationRequest,
    VPSUpdateRequest,
    VPSEditRequest,
    VPSResponse,
    VPSDetailResponse,
    ProjectVersionsResponse,
    ErrorResponse,
    BMCGenerationRequest,
    BMCBlockUpdateRequest,
    BMCBlockRegenerateRequest,
    BMCResponse,
    BMCItemAddRequest,
    BMCItemAddResponse,
    BMCItemDeleteRequest,
    BMCItemDeleteResponse
)
# Note: VPSV2GenerationRequest moved to vps_v2_endpoints.py
from ..services.vps_service import get_vps_service

router = APIRouter(prefix="/api/v2/mvp", tags=["MVP - Value Proposition"])
logger = logging.getLogger(__name__)

credit_service = CreditService()


# ==================== VPS V1 ENDPOINTS ====================

@router.post(
    "/projects/{project_id}/vps/v1/generate",
    response_model=VPSResponse,
    responses={
        402: {"model": ErrorResponse, "description": "Insufficient credits"},
        404: {"model": ErrorResponse, "description": "Project not found"},
        400: {"model": ErrorResponse, "description": "Invalid request or prerequisites not met"}
    }
)
async def generate_vps_v1(
    project_id: str,
    request: VPSGenerationRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Generate Value Proposition Statement v1.
    
    **Prerequisites**:
    - Completed VPC 2.0 (customer profile + value map)
    - Identified personas (1-2 personas)
    - PV report with market evidence
    
    **Cost**: 1 credit (bypassed for super admins)
    
    **Returns**: Generated VPS with primary statement, extended statement, and 3 key differentiators
    """
    try:
        user_id = current_user["user_id"]  # Fixed: auth returns "user_id" not "id"
        tenant_id = current_user["tenant_id"]
        plan_type = current_user.get("tenant_type", "individual")
        user_roles = current_user.get("roles", [])
        
        logger.info(f"VPS v1 generation request from user {user_id} for project {project_id}")
        
        # Check if super admin
        is_super_admin = len(user_roles) > 0 and user_roles[0] == "super_admin"
        
        # Credit check - resolve feature name to UUID
        from src.mint.api.features.dependencies import resolve_feature_id
        feature_id = await resolve_feature_id("Value Proposition Statement v1")
        if not is_super_admin:
            has_credits = credit_service.has_sufficient_credits_for_feature(
                tenant_id=tenant_id,
                feature_id=feature_id,
                plan_type=plan_type
            )
            if not has_credits:
                logger.warning(f"Insufficient credits for user {user_id}, tenant {tenant_id}")
                raise HTTPException(
                    status_code=402,
                    detail="Insufficient credits for VPS generation. Please purchase more credits."
                )
        else:
            logger.info(f"✅ Super admin {user_id} bypassing credit check for VPS generation")
        
        # Initialize service
        vps_service = get_vps_service()
        
        # Generate VPS
        result = await vps_service.generate_vps_v1(
            project_id=project_id,
            tenant_id=tenant_id,
            user_id=user_id,
            creativity_level=request.creativity_level
        )
        
        # Consume credits (bypass for super admins)
        if not is_super_admin and not result.get('already_existed', False):
            try:
                import uuid
                credit_service.consume_feature(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    feature_id=feature_id,
                    plan_type=plan_type,
                    request_id=str(uuid.uuid4()),
                    reason="VPS v1 generation",
                    project_id=project_id
                )
                logger.info(f"✅ Consumed 1 credit for VPS v1 generation")
            except Exception as e:
                logger.error(f"❌ Failed to consume credits: {e}")
                # Don't fail the request if credit consumption fails
        
        return VPSResponse(
            success=True,
            data=result,
            message=result['message']
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error generating VPS v1: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate VPS: {str(e)}"
        )


@router.get(
    "/projects/{project_id}/vps/v1",
    response_model=VPSDetailResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Project or VPS not found"}
    }
)
async def get_vps_v1(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get VPS v1 for a project.
    
    **Returns**: VPS v1 data if exists, or null if not generated yet
    """
    try:
        user_id = current_user["user_id"]  # Fixed: auth returns "user_id" not "id"
        tenant_id = current_user["tenant_id"]
        
        vps_service = get_vps_service()
        
        # Get VPS data
        vps_data = await vps_service.get_vps_v1(
            project_id=project_id,
            tenant_id=tenant_id,
            user_id=user_id
        )
        
        # Get current version
        current_version = vps_service.get_current_version(project_id, tenant_id)
        
        if vps_data:
            return VPSDetailResponse(
                success=True,
                vps_data=vps_data,
                project_id=project_id,
                current_version=current_version,
                message="VPS v1 retrieved successfully"
            )
        else:
            return VPSDetailResponse(
                success=True,
                vps_data=None,
                project_id=project_id,
                current_version=current_version,
                message="VPS v1 not found. Generate it first."
            )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error retrieving VPS v1: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve VPS: {str(e)}"
        )


@router.put(
    "/projects/{project_id}/vps/v1",
    response_model=VPSResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Project or VPS not found"},
        400: {"model": ErrorResponse, "description": "Invalid update data"},
        422: {"model": ErrorResponse, "description": "Validation error"}
    }
)
async def update_vps_v1(
    project_id: str,
    request: VPSEditRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Update VPS v1 for a project (multi-persona support).
    
    **Accepts EITHER:**
    1. Full GET response: `{"success": true, "vps_data": [...], ...}`
    2. Wrapped format: `{"vps_data": [{persona1_vps}, {persona2_vps}]}`
    
    **Copy-paste friendly**: You can copy the entire GET response, modify it, and send it back.
    
    **Returns**: Updated VPS v1 data array
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
        
        success = mvp_adapter.save_vps_v1(
            project_id=project_id,
            tenant_id=tenant_id,
            vps_data=vps_data,
            user_id=user_id
        )
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to save VPS v1 to database"
            )
        
        # Get updated data
        updated_vps = mvp_adapter.get_vps_v1(project_id, tenant_id)
        
        logger.info(f"✅ Successfully updated {len(vps_data)} VPS v1 for project {project_id}")
        
        return VPSResponse(
            success=True,
            data={"vps_v1": updated_vps, "project_id": project_id, "vps_count": len(vps_data)},
            message=f"VPS v1 updated successfully ({len(vps_data)} persona(s))"
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating VPS v1: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update VPS: {str(e)}"
        )

# (VPS v2 should appear after Solution Critique in the API documentation)


# ==================== VERSION INFO ENDPOINT ====================

@router.get(
    "/projects/{project_id}/versions",
    response_model=ProjectVersionsResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Project not found"}
    }
)
async def get_project_versions(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get version information for all MVP components in a project.
    
    **Returns**: Current versions of VPS, BMC, and other MVP components
    """
    try:
        tenant_id = current_user["tenant_id"]
        
        from ..adapters.database_adapter import get_mvp_database_adapter
        mvp_adapter = get_mvp_database_adapter()
        
        versions = mvp_adapter.get_current_versions(project_id, tenant_id)
        
        return ProjectVersionsResponse(
            success=True,
            project_id=project_id,
            versions=versions,
            message="Version information retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"Error retrieving project versions: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve versions: {str(e)}"
        )


# ==================== BMC ENDPOINTS ====================

@router.post(
    "/projects/{project_id}/bmc/generate",
    response_model=BMCResponse,
    responses={
        402: {"model": ErrorResponse, "description": "Insufficient credits"},
        404: {"model": ErrorResponse, "description": "Project not found"},
        400: {"model": ErrorResponse, "description": "Invalid request or prerequisites not met"}
    }
)
async def generate_bmc(
    project_id: str,
    request: BMCGenerationRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Generate complete Business Model Canvas (all 9 blocks) in single API request.
    
    **Process**:
    - Runs in background (~45-60 seconds)
    - Generates all 9 blocks sequentially
    - Each block builds upon previous blocks
    - Progressive saving after each block
    - Returns complete BMC when done
    
    **Prerequisites**:
    - VPS v1 must be generated
    - VPC 2.0 must be completed
    - Personas must be identified
    - Context completeness > 0.5
    
    **Returns**: Complete 9-block BMC with evidence and generation metadata
    
    **Item Counts** (based on Netflix & Vuba Vuba examples):
    - Customer Segments: 1-3 items
    - Value Propositions: 2-6 items
    - Channels: 3-6 items
    - Customer Relationships: 2-6 items
    - Revenue Streams: 2-5 items
    - Key Resources: 3-6 items
    - Key Activities: 3-7 items
    - Key Partnerships: 3-9 items
    - Cost Structure: 4-9 categories
    """
    start_time = time.time()
    
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        plan_type = current_user["tenant_type"]
        
        # Super admin detection
        user_roles = current_user.get("roles", [])
        is_super_admin = len(user_roles) > 0 and user_roles[0] == "super_admin"
        
        logger.info(f"BMC generation request for project {project_id} by user {user_id}")
        
        # Credit check - resolve feature name to UUID
        from src.mint.api.features.dependencies import resolve_feature_id
        feature_id = await resolve_feature_id("Business Model Canvas v1")
        if not is_super_admin:
            if not credit_service.has_sufficient_credits_for_feature(
                tenant_id=tenant_id,
                feature_id=feature_id,
                plan_type=plan_type
            ):
                raise HTTPException(
                    status_code=402,
                    detail="Insufficient credits for BMC generation"
                )
        
        # Generate BMC
        from ..bmc.services.bmc_service import BMCService
        from ..adapters.database_adapter import get_mvp_database_adapter
        
        bmc_service = BMCService()
        
        result = await bmc_service.generate_bmc(
            project_id=project_id,
            tenant_id=tenant_id,
            user_id=user_id,
            creativity_level=request.creativity_level
        )
        
        # Get project name
        mvp_adapter = get_mvp_database_adapter()
        project = mvp_adapter.get_project(project_id, tenant_id)
        project_name = project.get("name") if project else None
        
        # Consume credits (skip for super admins)
        if not is_super_admin:
            try:
                import uuid
                credit_service.consume_feature(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    feature_id=feature_id,
                    plan_type=plan_type,
                    request_id=str(uuid.uuid4()),
                    reason="BMC v1 generation",
                    project_id=project_id,
                    metadata={
                        "generation_time": time.time() - start_time,
                        "blocks_generated": 9
                    }
                )
            except Exception as credit_error:
                logger.error(f"Credit consumption failed: {credit_error}")
                # Don't fail the request if credit consumption fails
        
        logger.info(f"BMC generated successfully for project {project_id} in {time.time() - start_time:.2f}s")
        
        return BMCResponse(
            success=True,
            project_id=project_id,
            project_name=project_name,
            bmc=result["bmc"],
            message="BMC generated successfully"
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error generating BMC: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error generating BMC: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate BMC: {str(e)}"
        )


@router.get(
    "/projects/{project_id}/bmc",
    response_model=BMCResponse,
    responses={
        404: {"model": ErrorResponse, "description": "BMC not found"}
    }
)
async def get_bmc(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get existing Business Model Canvas for a project.
    
    **Returns**: Complete BMC if exists, 404 if not generated yet
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        
        from ..bmc.services.bmc_service import BMCService
        from ..adapters.database_adapter import get_mvp_database_adapter
        
        bmc_service = BMCService()
        
        result = await bmc_service.get_bmc(
            project_id=project_id,
            tenant_id=tenant_id,
            user_id=user_id
        )
        
        if not result or not result.get("bmc"):
            raise HTTPException(
                status_code=404,
                detail="BMC not found. Generate it first."
            )
        
        # Get project name
        mvp_adapter = get_mvp_database_adapter()
        project = mvp_adapter.get_project(project_id, tenant_id)
        project_name = project.get("name") if project else None
        
        return BMCResponse(
            success=True,
            project_id=project_id,
            project_name=project_name,
            bmc=result["bmc"],
            message="BMC retrieved successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving BMC: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve BMC: {str(e)}"
        )


@router.put(
    "/projects/{project_id}/bmc/blocks/{block_name}",
    response_model=BMCResponse,
    responses={
        404: {"model": ErrorResponse, "description": "BMC or block not found"},
        400: {"model": ErrorResponse, "description": "Invalid block name or data"}
    }
)
async def update_bmc_block(
    project_id: str,
    block_name: str,
    request: BMCBlockUpdateRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Update a specific BMC block (manual user edits).
    
    **Valid block names**:
    - customer_segments
    - value_propositions
    - channels
    - customer_relationships
    - revenue_streams
    - key_resources
    - key_activities
    - key_partnerships
    - cost_structure
    
    **Returns**: Updated complete BMC
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        
        from ..bmc.services.bmc_service import BMCService
        from ..adapters.database_adapter import get_mvp_database_adapter
        
        bmc_service = BMCService()
        
        result = await bmc_service.update_bmc_block(
            project_id=project_id,
            tenant_id=tenant_id,
            user_id=user_id,
            block_name=block_name,
            block_data=request.block_data
        )
        
        # Get project name
        mvp_adapter = get_mvp_database_adapter()
        project = mvp_adapter.get_project(project_id, tenant_id)
        project_name = project.get("name") if project else None
        
        return BMCResponse(
            success=True,
            project_id=project_id,
            project_name=project_name,
            bmc=result["bmc"],
            updated_block=block_name,
            message=f"Block {block_name} updated successfully"
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating BMC block: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating BMC block: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update BMC block: {str(e)}"
        )


@router.post(
    "/projects/{project_id}/bmc/blocks/{block_name}/regenerate",
    response_model=BMCResponse,
    responses={
        404: {"model": ErrorResponse, "description": "BMC not found"},
        400: {"model": ErrorResponse, "description": "Invalid block name"}
    }
)
async def regenerate_bmc_block(
    project_id: str,
    block_name: str,
    request: BMCBlockRegenerateRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Regenerate a specific BMC block using AI.
    
    Uses current context + all previous blocks to regenerate the specified block.
    Useful when:
    - User wants different options
    - Context has changed (new research)
    - User wants to try different creativity level
    
    **Valid block names**:
    - customer_segments
    - value_propositions
    - channels
    - customer_relationships
    - revenue_streams
    - key_resources
    - key_activities
    - key_partnerships
    - cost_structure
    
    **Returns**: Updated complete BMC with regenerated block
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        
        from ..bmc.services.bmc_service import BMCService
        from ..adapters.database_adapter import get_mvp_database_adapter
        
        bmc_service = BMCService()
        
        result = await bmc_service.regenerate_bmc_block(
            project_id=project_id,
            tenant_id=tenant_id,
            user_id=user_id,
            block_name=block_name,
            creativity_level=request.creativity_level
        )
        
        # Get project name
        mvp_adapter = get_mvp_database_adapter()
        project = mvp_adapter.get_project(project_id, tenant_id)
        project_name = project.get("name") if project else None
        
        return BMCResponse(
            success=True,
            project_id=project_id,
            project_name=project_name,
            bmc=result["bmc"],
            regenerated_block=block_name,
            message=f"Block {block_name} regenerated successfully"
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error regenerating BMC block: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error regenerating BMC block: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to regenerate BMC block: {str(e)}"
        )


@router.post(
    "/projects/{project_id}/bmc/items/add",
    response_model=BMCItemAddResponse,
    responses={
        404: {"model": ErrorResponse, "description": "BMC not found"},
        400: {"model": ErrorResponse, "description": "Invalid block name or data"}
    }
)
async def add_bmc_item(
    project_id: str,
    request: BMCItemAddRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Add a new item to a BMC block with AI-enhanced description.
    
    Similar to persona AI enrichment, this endpoint:
    1. Takes user's label and description
    2. Queries PV report and actionable insights for relevant context
    3. Uses AI to enhance the description with evidence from the data
    4. Adds the enriched item to the specified BMC block
    
    **Valid block names**:
    - customer_segments
    - value_propositions
    - channels
    - customer_relationships
    - revenue_streams
    - key_resources
    - key_activities
    - key_partnerships
    - cost_structure
    
    **Returns**: 
    - The newly added item with AI-enhanced description
    - Updated complete BMC
    - Flag indicating if AI enhancement was applied
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        
        from ..bmc.services.bmc_service import BMCService
        from ..adapters.database_adapter import get_mvp_database_adapter
        
        bmc_service = BMCService()
        
        result = await bmc_service.add_bmc_item_with_enhancement(
            project_id=project_id,
            tenant_id=tenant_id,
            user_id=user_id,
            block_name=request.block_name,
            label=request.label,
            description=request.description
        )
        
        # Get project name
        mvp_adapter = get_mvp_database_adapter()
        project = mvp_adapter.get_project(project_id, tenant_id)
        project_name = project.get("name") if project else None
        
        return BMCItemAddResponse(
            success=True,
            project_id=project_id,
            project_name=project_name,
            block_name=result["block_name"],
            added_item=result["added_item"],
            ai_enhanced=result["ai_enhanced"],
            bmc=result["bmc"],
            message=result["message"]
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error adding BMC item: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error adding BMC item: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to add BMC item: {str(e)}"
        )


@router.delete(
    "/projects/{project_id}/bmc/items/delete",
    response_model=BMCItemDeleteResponse,
    responses={
        404: {"model": ErrorResponse, "description": "BMC or item not found"},
        400: {"model": ErrorResponse, "description": "Invalid block name or item ID"}
    }
)
async def delete_bmc_item(
    project_id: str,
    request: BMCItemDeleteRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete an item from a BMC v1 block by its ID.
    
    **Valid block names**:
    - customer_segments
    - value_propositions
    - channels
    - customer_relationships
    - revenue_streams
    - key_resources
    - key_activities
    - key_partnerships
    - cost_structure
    
    **Returns**: 
    - The deleted item ID
    - Updated complete BMC
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        
        from src.mvp.adapters.database_adapter import get_mvp_database_adapter
        from src.mvp.bmc.services.bmc_service import BMCService
        
        bmc_service = BMCService()
        mvp_adapter = get_mvp_database_adapter()
        
        # Check if BMC exists
        bmc = mvp_adapter.get_bmc(project_id, tenant_id)
        if not bmc:
            raise HTTPException(
                status_code=404,
                detail="BMC not found. Generate BMC first."
            )
        
        # Delete the item
        result = bmc_service.delete_bmc_item(
            project_id=project_id,
            tenant_id=tenant_id,
            user_id=user_id,
            block_name=request.block_name,
            item_id=request.item_id
        )
        
        # Get project name
        project = mvp_adapter.get_project(project_id, tenant_id)
        project_name = project.get("name") if project else None
        
        return BMCItemDeleteResponse(
            success=True,
            project_id=project_id,
            project_name=project_name,
            block_name=result["block_name"],
            deleted_item_id=result["deleted_item_id"],
            bmc=result["bmc"],
            message=result["message"]
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error deleting BMC item: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error deleting BMC item: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete BMC item: {str(e)}"
        )
