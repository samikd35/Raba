"""
Simple Tenant Management API Endpoints

Basic tenant endpoints for testing and demonstration without complex auth dependencies.
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status

from ..auth_v2.utils import (
    get_current_user,
    get_global_admin_or_tenant_admin,
    get_global_admin_or_tenant_member,
    get_super_admin_or_tenant_owner,
)
from .models import (
    TenantCreate,
    TenantDelete,
    TenantListResponse,
    TenantResponse,
    TenantUpdate,
)
from .service import TenantService

logger = logging.getLogger(__name__)

# Create router for simple tenant endpoints
router = APIRouter(prefix="/api/v1/tenant", tags=["tenant"])

# =============================================
# SIMPLE TENANT ENDPOINTS (NO AUTH FOR TESTING)
# =============================================


@router.post("/", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant_simple(
    tenant_data: TenantCreate, current_user: dict = Depends(get_current_user)
):
    """
    Create a new tenant (Individual, Team, or Organization) - SIMPLE VERSION FOR TESTING.

    The specified user becomes the owner of the created tenant.
    """
    try:
        logger.info(f"Creating tenant: {tenant_data.name}")

        # Use the new registered user ID
        user_id = current_user["user_id"]
        service = TenantService(use_service_role=True)
        result = await service.create_tenant(tenant_data, user_id)

        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=result.message
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating tenant: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while creating tenant",
        )


@router.get("/", response_model=TenantListResponse)
async def list_tenants_simple(
    current_user: dict = Depends(get_current_user),
):
    """
    List all tenants that the specified user belongs to - SIMPLE VERSION FOR TESTING.
    """
    try:
        user_id = current_user["user_id"]
        logger.info(f"Listing tenants for user: {user_id}")

        service = TenantService()
        result = await service.list_user_tenants(user_id)

        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=result.message
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing user tenants: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while listing tenants",
        )


@router.get("/{tenant_id}/members")
async def get_tenant_member_simple(
    tenant_id: str,
    page: str,
    page_size: str,
    current_user: str = Depends(get_global_admin_or_tenant_member),
):
    """
    User must be a member of the tenant to access its details.
    """
    try:
        user_id = current_user["user_id"]
        logger.info(f"Getting tenant {tenant_id} members")

        page_num = int(page) if page.isdigit() else 1
        page_size = int(page_size) if page_size.isdigit() else 20

        service = TenantService(use_service_role=False)
        result = await service.list_tenant_members(
            tenant_id, user_id, page_num, page_size
        )

        if not result.success:
            if "not found" in result.message.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail=result.message
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail=result.message
                )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting tenant {tenant_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while getting tenant",
        )


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant_simple(
    tenant_id: str, current_user: str = Depends(get_global_admin_or_tenant_member)
):
    """
    Get tenant details by ID - SIMPLE VERSION FOR TESTING.

    User must be a member of the tenant to access its details.
    """
    try:
        user_id = current_user["user_id"]
        logger.info(f"Getting tenant {tenant_id} for user {user_id}")

        service = TenantService(use_service_role=False)
        result = await service.get_tenant(tenant_id, user_id)

        if not result.success:
            if "Access denied" in result.message:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail=result.message
                )
            elif "not found" in result.message.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail=result.message
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail=result.message
                )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting tenant {tenant_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while getting tenant",
        )


# =============================================
# HEALTH CHECK ENDPOINT
# =============================================


@router.get("/health", response_model=Dict[str, str])
async def tenant_health_check():
    """
    Health check endpoint for tenant service.
    """
    return {
        "status": "healthy",
        "service": "tenant-management",
        "message": "Tenant service is operational",
    }


@router.get("/test-endpoints", response_model=Dict[str, str])
async def test_endpoints():
    """
    Test endpoint to verify new endpoints are working.
    """
    return {
        "status": "success",
        "message": "New endpoints are working!",
        "available_endpoints": [
            "POST /api/v1/tenant/actionable-insights",
            "POST /api/v1/tenant/vector-storage/documents",
            "POST /api/v1/tenant/problem-validation-reports",
        ],
    }


# =============================================
# ACTIONABLE INSIGHTS ENDPOINTS
# =============================================


@router.post("/actionable-insights", response_model=Dict[str, Any])
async def create_actionable_insights(insight_data: Dict[str, Any]):
    """
    Create actionable insights for the tenant.
    """
    try:
        import os
        import sys

        sys.path.append(os.path.dirname(os.path.abspath(__file__)))

        import uuid
        from datetime import datetime

        from src.mint.api.system.core.supabase_client import get_supabase_client

        # Get service role client
        supabase = get_supabase_client(use_service_role=True)
        client = supabase.client

        # Use the new registered user ID
        user_id = "d1562108-0c12-4c9d-ab10-0f5f76c00685"

        # Create actionable insight
        insight_record = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "title": insight_data.get(
                "title", "Digital Banking Strategy for Rural Nigeria"
            ),
            "executive_summary": insight_data.get(
                "executive_summary",
                "Comprehensive strategy for expanding digital banking to rural Nigeria",
            ),
            "key_recommendations": insight_data.get(
                "key_recommendations",
                [
                    "Mobile-first approach with USSD banking",
                    "Agent banking networks in underserved communities",
                    "Financial literacy programs",
                    "Partnership with telecom companies",
                ],
            ),
            "implementation_roadmap": insight_data.get(
                "implementation_roadmap",
                {
                    "phase_1": "Infrastructure setup (6 months)",
                    "phase_2": "Product development (6 months)",
                    "phase_3": "Full deployment (6 months)",
                },
            ),
            "expected_impact": insight_data.get(
                "expected_impact",
                {
                    "financial_inclusion": "50% increase in rural banking access",
                    "cost_reduction": "30% reduction in transaction costs",
                    "user_adoption": "25% improvement in financial literacy",
                },
            ),
            "risk_assessment": insight_data.get(
                "risk_assessment",
                {
                    "technical_risks": "Low - proven technology",
                    "regulatory_risks": "Medium - requires CBN approval",
                    "market_risks": "Low - high demand exists",
                },
            ),
            "success_metrics": insight_data.get(
                "success_metrics",
                [
                    "Number of rural users with digital banking access",
                    "Transaction volume growth",
                    "Customer satisfaction scores",
                ],
            ),
            "industry": insight_data.get("industry", "fintech"),
            "geography": insight_data.get("geography", "Nigeria"),
            "target_audience": insight_data.get("target_audience", "rural_communities"),
            "priority": insight_data.get("priority", "high"),
            "status": insight_data.get("status", "draft"),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        result = client.table("actionable_insights").insert(insight_record).execute()

        return {
            "success": True,
            "message": "Actionable insight created successfully",
            "data": result.data[0] if result.data else None,
        }

    except Exception as e:
        logger.error(f"Error creating actionable insight: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create actionable insight: {str(e)}",
        )


@router.post("/vector-storage/documents", response_model=Dict[str, Any])
async def create_document_with_chunks(document_data: Dict[str, Any]):
    """
    Create document and chunks for vector storage.
    """
    try:
        import os
        import sys

        sys.path.append(os.path.dirname(os.path.abspath(__file__)))

        import uuid
        from datetime import datetime

        from src.mint.api.system.core.supabase_client import get_supabase_client

        # Get service role client
        supabase = get_supabase_client(use_service_role=True)
        client = supabase.client

        # Use the new registered user ID
        user_id = "d1562108-0c12-4c9d-ab10-0f5f76c00685"

        # Create document
        doc_record = {
            "id": str(uuid.uuid4()),
            "tenant_id": document_data.get(
                "tenant_id", "cfe1a6dd-1a8a-4f33-9051-15aecbcc3751"
            ),
            "project_id": None,
            "source_type": document_data.get("source_type", "actionable_insights"),
            "title": document_data.get(
                "title", "Digital Banking Strategy for Rural Nigeria"
            ),
            "content": document_data.get(
                "content",
                """
            EXECUTIVE SUMMARY:
            This actionable insight provides a comprehensive strategy for expanding digital financial services to rural Nigeria, addressing the critical gap in financial inclusion that affects over 40 million people.

            KEY RECOMMENDATIONS:
            1. Infrastructure Development:
               - Partner with telecom companies to expand 4G coverage to rural areas
               - Implement USSD-based financial services for basic phones
               - Establish agent banking networks in underserved communities

            2. Product Innovation:
               - Develop offline-capable mobile banking applications
               - Create simplified user interfaces for low-literacy users
               - Implement voice-based banking for accessibility

            3. Financial Literacy:
               - Launch community-based financial education programs
               - Partner with local organizations for trust-building
               - Create culturally relevant educational content

            4. Regulatory Support:
               - Work with CBN to streamline licensing for rural agents
               - Advocate for reduced transaction fees for rural services
               - Establish consumer protection frameworks

            IMPLEMENTATION TIMELINE:
            - Phase 1 (Months 1-6): Infrastructure and agent network setup
            - Phase 2 (Months 7-12): Product development and testing
            - Phase 3 (Months 13-18): Full deployment and scaling

            SUCCESS METRICS:
            - 50% increase in rural digital financial service adoption
            - 30% reduction in transaction costs for rural users
            - 25% improvement in financial literacy scores

            RISK MITIGATION:
            - Partner with established local organizations
            - Implement robust security measures
            - Create contingency plans for infrastructure failures
            """,
            ),
            "storage_path": None,
            "sha256": str(uuid.uuid4())[:12],
            "created_by": user_id,
            "metadata": document_data.get(
                "metadata",
                {
                    "industry": "fintech",
                    "geography": "Nigeria",
                    "target_audience": "rural_communities",
                    "priority": "high",
                    "estimated_impact": "high",
                    "implementation_difficulty": "medium",
                    "cost_estimate": "medium",
                    "timeline": "18_months",
                },
            ),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        result = client.table("documents").insert(doc_record).execute()
        document_id = result.data[0]["id"]

        # Create chunks for the document
        content = doc_record["content"]
        chunk_size = 1000
        chunks_created = []

        for i in range(0, len(content), chunk_size):
            chunk_content = content[i : i + chunk_size]
            chunk_record = {
                "id": str(uuid.uuid4()),
                "doc_id": document_id,
                "chunk_index": i // chunk_size,
                "content": chunk_content,
                "token_count": len(chunk_content.split()),
                "embedding": None,  # Will be generated by embedding service
                "metadata": {
                    "chunk_type": "text",
                    "source": "actionable_insights",
                    "industry": "fintech",
                    "geography": "Nigeria",
                },
                "created_at": datetime.utcnow().isoformat(),
            }

            chunk_result = client.table("chunks").insert(chunk_record).execute()
            chunks_created.append(chunk_result.data[0])

        return {
            "success": True,
            "message": f"Document and {len(chunks_created)} chunks created successfully",
            "data": {"document": result.data[0], "chunks": chunks_created},
        }

    except Exception as e:
        logger.error(f"Error creating document and chunks: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create document and chunks: {str(e)}",
        )


@router.post("/problem-validation-reports", response_model=Dict[str, Any])
async def create_problem_validation_report(report_data: Dict[str, Any]):
    """
    Create problem validation report.
    """
    try:
        import os
        import sys

        sys.path.append(os.path.dirname(os.path.abspath(__file__)))

        import uuid
        from datetime import datetime

        from src.mint.api.system.core.supabase_client import get_supabase_client

        # Get service role client
        supabase = get_supabase_client(use_service_role=True)
        client = supabase.client

        # Use the new registered user ID
        user_id = "d1562108-0c12-4c9d-ab10-0f5f76c00685"

        # Create problem validation report
        pv_report = {
            "id": str(uuid.uuid4()),
            "session_id": str(uuid.uuid4()),
            "user_id": user_id,
            "title": report_data.get(
                "title", "E-commerce Logistics Validation Report - Ghana"
            ),
            "executive_summary": report_data.get(
                "executive_summary",
                "Validation of e-commerce logistics challenges in Ghana",
            ),
            "problem_statement": report_data.get(
                "problem_statement",
                "High delivery costs and long delivery times prevent e-commerce growth in Ghana",
            ),
            "market_analysis": report_data.get(
                "market_analysis",
                "Ghana's e-commerce market growing at 25% annually with $2.3B logistics market",
            ),
            "competitive_analysis": report_data.get(
                "competitive_analysis",
                "Limited real-time tracking, poor infrastructure, manual processes",
            ),
            "customer_validation": report_data.get(
                "customer_validation",
                "85% of businesses interested in improved logistics solutions",
            ),
            "technical_feasibility": report_data.get(
                "technical_feasibility", "High - proven technology available"
            ),
            "business_model": report_data.get(
                "business_model", "Subscription-based with tiered pricing"
            ),
            "recommendations": report_data.get(
                "recommendations",
                [
                    "Implement real-time tracking systems",
                    "Establish regional distribution centers",
                    "Partner with existing transport networks",
                ],
            ),
            "report_type": report_data.get("report_type", "market_validation"),
            "industry": report_data.get("industry", "ecommerce"),
            "geography": report_data.get("geography", "Ghana"),
            "target_audience": report_data.get(
                "target_audience", "ecommerce_businesses"
            ),
            "market_size_estimate": report_data.get(
                "market_size_estimate", {"value": 2300000000, "currency": "USD"}
            ),
            "customer_segments": report_data.get(
                "customer_segments",
                ["small_businesses", "medium_enterprises", "large_corporations"],
            ),
            "competitive_landscape": report_data.get(
                "competitive_landscape",
                ["local_providers", "international_couriers", "postal_services"],
            ),
            "risk_assessment": report_data.get(
                "risk_assessment",
                {
                    "market_risk": "low",
                    "technical_risk": "low",
                    "regulatory_risk": "medium",
                },
            ),
            "status": report_data.get("status", "completed"),
            "completion_percentage": report_data.get("completion_percentage", 100),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "completed_at": datetime.utcnow().isoformat(),
        }

        result = client.table("problem_validation_reports").insert(pv_report).execute()

        return {
            "success": True,
            "message": "Problem validation report created successfully",
            "data": result.data[0] if result.data else None,
        }

    except Exception as e:
        logger.error(f"Error creating problem validation report: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create problem validation report: {str(e)}",
        )


@router.delete("/{tenant_id}")
async def delete_tenant(
    tenant_id: str,
    current_user: dict = Depends(get_super_admin_or_tenant_owner),
):
    """
    Delete a tenant if the current user is its owner or if user is super admin.
    
    Super admins can delete any tenant.
    Regular users can only delete tenants they own.
    
    This will cascade delete all related data:
    - Tenant memberships
    - Tenant invitations  
    - Organization-team mappings
    - Team-user mappings
    - Projects (both regular and VMP)
    - Credit lots
    """
    # Determine if user is super admin
    user_roles = current_user.get("roles", [])
    is_super_admin = len(user_roles) > 0 and user_roles[0] == "super_admin"
    
    # Super admins use service role, regular users use their own permissions
    service = TenantService(use_service_role=is_super_admin)

    deleted = await service.delete_tenant(
        tenant_id=tenant_id, user_id=current_user["user_id"]
    )
    if not deleted:
        raise HTTPException(status_code=500, detail="Failed to delete tenant")

    return {"success": True, "message": "Tenant deleted successfully"}


@router.put("/{tenant_id}")
async def update_tenant(
    tenant_id: str,
    update_data: TenantUpdate,
    current_user: dict = Depends(get_global_admin_or_tenant_admin),
):
    """
    Update a tenant if the current user is its owner.
    """
    service = TenantService(use_service_role=True)

    updated = service.update_tenant(
        tenant_id=tenant_id, user_id=current_user["user_id"], update_data=update_data
    )
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to delete tenant")

    return {"success": True, "message": "Tenant deleted successfully"}


@router.delete("/{tenant_id}/member")
async def update_tenant(
    tenant_id: str,
    delete_data: TenantDelete,
    current_user: dict = Depends(get_super_admin_or_tenant_owner),
):
    """
    Update a tenant if the current user is its owner.
    """
    service = TenantService(use_service_role=True)

    deleted = service.remove_tenant_member(
        tenant_id=tenant_id, user_id=delete_data.member_id
    )
    if not deleted:
        raise HTTPException(status_code=500, detail="Failed to remove member")

    return {"success": True, "message": "Tenant deleted successfully"}
