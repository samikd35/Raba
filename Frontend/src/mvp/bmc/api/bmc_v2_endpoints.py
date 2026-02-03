"""
BMC v2 API Endpoints (Separate router for Swagger ordering)

These endpoints are in a separate file to ensure they appear after
VPS v2 endpoints in Swagger UI.
"""

from fastapi import APIRouter, Depends, HTTPException
import logging
import time

from src.mint.api.auth_v2.utils import get_current_user
from src.mint.api.credit.service import CreditService

from src.mvp.api.models import (
    BMCGenerationRequest,
    BMCResponse,
    BMCBlockUpdateRequest,
    BMCItemAddRequest,
    BMCItemAddResponse,
    BMCItemDeleteRequest,
    BMCItemDeleteResponse,
    ErrorResponse
)
from src.mvp.bmc.services.bmc_service import BMCService

router = APIRouter(prefix="/api/v2/mvp", tags=["MVP - Value Proposition"])
logger = logging.getLogger(__name__)

credit_service = CreditService()


# ==================== BMC V2 ENDPOINTS ====================

@router.post(
    "/projects/{project_id}/bmc/v2/generate",
    response_model=BMCResponse,
    responses={
        402: {"model": ErrorResponse, "description": "Insufficient credits"},
        404: {"model": ErrorResponse, "description": "Project not found"},
        400: {"model": ErrorResponse, "description": "BMC v1, VPS v2, or Solution Critique not found"}
    }
)
async def generate_bmc_v2(
    project_id: str,
    request: BMCGenerationRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Generate Business Model Canvas v2 (critique-driven refinement with VPS v2 alignment).
    
    **Prerequisites**:
    - BMC v1 must exist
    - VPS v2 must exist (for Value Propositions alignment)
    - Solution Critique must be completed
    
    **Process**:
    - Uses RAG to retrieve relevant critique chunks dynamically (top 20 chunks)
    - AI analyzes critique feedback against BMC v1, block by block
    - Ensures Value Propositions block aligns with refined VPS v2
    - Decides refinement scope per block: no_changes, partial, or full
    - Generates refined BMC v2 with reasons and evidence for each change
    - Tracks critique sources and how concerns were addressed
    
    **Cost**: 1 credit (bypassed for super admins)
    
    **Returns**: 
    - Refined BMC v2 (same 9-block structure as v1)
    - Refinement metadata (decision, rationale, per-block change tracking)
    - VPS v2 alignment confirmation
    - Critique sources used with citations
    """
    start_time = time.time()
    
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        plan_type = current_user["tenant_type"]
        user_roles = current_user.get("roles", [])
        
        logger.info(f"BMC v2 generation request from user {user_id} for project {project_id}")
        
        # Check if super admin
        is_super_admin = len(user_roles) > 0 and user_roles[0] == "super_admin"
        
        # Credit check - resolve feature name to UUID
        from src.mint.api.features.dependencies import resolve_feature_id
        feature_id = await resolve_feature_id("Business Model Canvas v2")
        if not is_super_admin:
            has_credits = credit_service.has_sufficient_credits_for_feature(
                tenant_id=tenant_id,
                feature_id=feature_id,
                plan_type=plan_type
            )
            if not has_credits:
                raise HTTPException(
                    status_code=402,
                    detail="Insufficient credits for BMC v2 generation"
                )
        else:
            logger.info(f"✅ Super admin {user_id} bypassing credit check for BMC v2 generation")
        
        # Initialize service
        bmc_service = BMCService()
        
        # Generate BMC v2
        result = await bmc_service.generate_bmc_v2(
            project_id=project_id,
            tenant_id=tenant_id,
            user_id=user_id,
            creativity_level=request.creativity_level
        )
        
        # Get project name
        from src.mvp.adapters.database_adapter import get_mvp_database_adapter
        mvp_adapter = get_mvp_database_adapter()
        project = mvp_adapter.get_project(project_id, tenant_id)
        project_name = project.get("name") if project else None
        
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
                    reason="BMC v2 generation",
                    project_id=project_id,
                    metadata={
                        "generation_time": time.time() - start_time,
                        "blocks_changed": result["bmc_v2"]["refinement_metadata"]["blocks_changed"]
                    }
                )
                logger.info(f"✅ Consumed 1 credit for BMC v2 generation")
            except Exception as credit_error:
                logger.error(f"Credit consumption failed: {credit_error}")
        
        logger.info(f"BMC v2 generated successfully for project {project_id} in {time.time() - start_time:.2f}s")
        
        return BMCResponse(
            success=True,
            project_id=project_id,
            project_name=project_name,
            bmc=result["bmc_v2"],
            message=result['message']
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error generating BMC v2: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error generating BMC v2: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate BMC v2: {str(e)}"
        )


@router.get(
    "/projects/{project_id}/bmc/v2",
    response_model=BMCResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Project or BMC v2 not found"}
    }
)
async def get_bmc_v2(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get BMC v2 for a project.
    
    **Returns**: BMC v2 data with refinement metadata, or null if not generated yet
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        
        from src.mvp.adapters.database_adapter import get_mvp_database_adapter
        mvp_adapter = get_mvp_database_adapter()
        
        # Get project data (for name)
        project = mvp_adapter.get_project(project_id, tenant_id)
        project_name = project.get("name") if project else None
        
        # Get BMC v2 data
        bmc_v2 = mvp_adapter.get_bmc_v2(project_id, tenant_id)
        
        if bmc_v2:
            return BMCResponse(
                success=True,
                project_id=project_id,
                project_name=project_name,
                bmc=bmc_v2,
                message="BMC v2 retrieved successfully"
            )
        else:
            return BMCResponse(
                success=True,
                project_id=project_id,
                project_name=project_name,
                bmc=None,
                message="BMC v2 not found. Generate it first."
            )
        
    except Exception as e:
        logger.error(f"Error retrieving BMC v2: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve BMC v2: {str(e)}"
        )


@router.put(
    "/projects/{project_id}/bmc/v2/blocks/{block_name}",
    response_model=BMCResponse,
    responses={
        404: {"model": ErrorResponse, "description": "BMC v2 or block not found"},
        400: {"model": ErrorResponse, "description": "Invalid block name or data"}
    }
)
async def update_bmc_v2_block(
    project_id: str,
    block_name: str,
    request: BMCBlockUpdateRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Update a specific BMC v2 block (manual user edits).
    
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
    
    **Returns**: Updated complete BMC v2
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        
        from src.mvp.adapters.database_adapter import get_mvp_database_adapter
        
        bmc_service = BMCService()
        mvp_adapter = get_mvp_database_adapter()
        
        # Check if BMC v2 exists
        bmc_v2 = mvp_adapter.get_bmc_v2(project_id, tenant_id)
        if not bmc_v2:
            raise HTTPException(
                status_code=404,
                detail="BMC v2 not found. Generate BMC v2 first."
            )
        
        result = await bmc_service.update_bmc_v2_block(
            project_id=project_id,
            tenant_id=tenant_id,
            user_id=user_id,
            block_name=block_name,
            block_data=request.block_data
        )
        
        # Get project name
        project = mvp_adapter.get_project(project_id, tenant_id)
        project_name = project.get("name") if project else None
        
        return BMCResponse(
            success=True,
            project_id=project_id,
            project_name=project_name,
            bmc=result["bmc"],
            updated_block=block_name,
            message=f"BMC v2 block {block_name} updated successfully"
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating BMC v2 block: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating BMC v2 block: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update BMC v2 block: {str(e)}"
        )


@router.post(
    "/projects/{project_id}/bmc/v2/items/add",
    response_model=BMCItemAddResponse,
    responses={
        404: {"model": ErrorResponse, "description": "BMC v2 not found"},
        400: {"model": ErrorResponse, "description": "Invalid block name or data"}
    }
)
async def add_bmc_v2_item(
    project_id: str,
    request: BMCItemAddRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Add a new item to a BMC v2 block with AI-enhanced description.
    
    Similar to persona AI enrichment, this endpoint:
    1. Takes user's label and description
    2. Queries PV report and actionable insights for relevant context
    3. Uses AI to enhance the description with evidence from the data
    4. Adds the enriched item to the specified BMC v2 block
    
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
    - Updated complete BMC v2
    - Flag indicating if AI enhancement was applied
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        
        from src.mvp.adapters.database_adapter import get_mvp_database_adapter
        
        bmc_service = BMCService()
        mvp_adapter = get_mvp_database_adapter()
        
        # Check if BMC v2 exists
        bmc_v2 = mvp_adapter.get_bmc_v2(project_id, tenant_id)
        if not bmc_v2:
            raise HTTPException(
                status_code=404,
                detail="BMC v2 not found. Generate BMC v2 first before adding items."
            )
        
        # Use the same service method but for BMC v2
        result = await bmc_service.add_bmc_v2_item_with_enhancement(
            project_id=project_id,
            tenant_id=tenant_id,
            user_id=user_id,
            block_name=request.block_name,
            label=request.label,
            description=request.description
        )
        
        # Get project name
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
        logger.error(f"Validation error adding BMC v2 item: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error adding BMC v2 item: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to add BMC v2 item: {str(e)}"
        )


@router.delete(
    "/projects/{project_id}/bmc/v2/items/delete",
    response_model=BMCItemDeleteResponse,
    responses={
        404: {"model": ErrorResponse, "description": "BMC v2 or item not found"},
        400: {"model": ErrorResponse, "description": "Invalid block name or item ID"}
    }
)
async def delete_bmc_v2_item(
    project_id: str,
    request: BMCItemDeleteRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete an item from a BMC v2 block by its ID.
    
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
    - Updated complete BMC v2
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        
        from src.mvp.adapters.database_adapter import get_mvp_database_adapter
        
        bmc_service = BMCService()
        mvp_adapter = get_mvp_database_adapter()
        
        # Check if BMC v2 exists
        bmc_v2 = mvp_adapter.get_bmc_v2(project_id, tenant_id)
        if not bmc_v2:
            raise HTTPException(
                status_code=404,
                detail="BMC v2 not found. Generate BMC v2 first."
            )
        
        # Delete the item
        result = bmc_service.delete_bmc_v2_item(
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
        logger.error(f"Validation error deleting BMC v2 item: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error deleting BMC v2 item: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete BMC v2 item: {str(e)}"
        )
