#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MINT API Idea Refinement Router

Complete idea refinement endpoints with history, analytics, and session management.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from src.mint.api.auth_v2.utils import get_current_user
from src.mint.api.credit.service import (CreditService,
                                         InsufficientCreditsError,
                                         InvalidConsumptionRequest)
from src.mint.api.cache.core import AdminCache
from src.prefine.history_service import ProblemRefinerHistoryService
from src.prefine.models import \
    IdeaRefinementRequest as PrefineIdeaRefinementRequest
from src.prefine.models import ResearchedStatusUpdate
from src.prefine.service import IdeaRefinementService

from .ai.config import get_api_key

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(tags=["idea-refinement"])

# Initialize services
idea_refinement_service = IdeaRefinementService()
history_service = ProblemRefinerHistoryService()
credit_service = CreditService()

# Initialize cache with 5-minute TTL for history endpoint
cache_service = AdminCache(default_ttl=300, max_size=500)


# =============================================
# REQUEST/RESPONSE MODELS
# =============================================


class IdeaRefinementRequest(BaseModel):
    """Request model for idea refinement."""

    original_idea: str = Field(..., min_length=10, description="The raw idea to refine")
    refinement_type: str = Field(
        default="problem_statement", description="Type of refinement"
    )
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class IdeaRefinementResponse(BaseModel):
    """Response model for idea refinement."""

    success: bool
    session_id: str
    problem_statements: List[Dict[str, Any]]
    parsed_context: Dict[str, str]
    processing_time: float


class HistoryResponse(BaseModel):
    """Response model for refinement history."""

    success: bool
    history: List[Dict[str, Any]]
    total_count: int
    user_id: str
    pagination: Dict[str, Any]


class SessionDetailsResponse(BaseModel):
    """Response model for session details."""

    success: bool
    session: Dict[str, Any]
    session_id: str


class AnalyticsResponse(BaseModel):
    """Response model for user analytics."""

    success: bool
    analytics: Dict[str, Any]
    user_id: str
    generated_at: str


class SearchResponse(BaseModel):
    """Response model for search results."""

    success: bool
    results: List[Dict[str, Any]]
    total_count: int
    query: str
    user_id: str
    search_metadata: Dict[str, Any]


# =============================================
# CORE REFINEMENT ENDPOINTS
# =============================================


@router.post("/refine", response_model=IdeaRefinementResponse)
async def refine_idea(
    request: IdeaRefinementRequest,
    current_user: dict = Depends(get_current_user),
    api_key: str = Depends(get_api_key),
):
    """Refine an idea using advanced AI enhancement - returns multiple problem statements."""
    try:
        # Hardcoded feature for idea refinement
        from src.mint.api.features.dependencies import resolve_feature_id
        feature_id = await resolve_feature_id("PRefiner")
        
        current_user_id = current_user["user_id"]
        logger.info(f"Idea refinement requested for: {request.original_idea[:100]}...")
        logger.info(f"Authenticated user_id: {current_user_id}")
        logger.info(f"Request context: {request.context}")

        # Use authenticated user_id (this is the correct user_id)
        user_id = current_user_id
        tenant_id = current_user["tenant_id"]
        plan_type = current_user["tenant_type"]

        logger.info(f"Using user_id: {user_id}")

        # -------- Pre-check: ensure sufficient credits for this feature --------
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
                    "message": "You don't have enough credits for this feature.",
                },
            )

        # Create prefine request format
        prefine_request = PrefineIdeaRefinementRequest(
            raw_idea=request.original_idea, user_id=user_id
        )

        # Process refinement through service (pass tenant_id for monitoring)
        result = await idea_refinement_service.refine_idea_complete(
            raw_idea=prefine_request.raw_idea, 
            user_id=prefine_request.user_id,
            tenant_id=tenant_id
        )

        if result:
            # Results are already stored by the service, no need to store again
            logger.info("Refinement result already stored by service")

            # -------- Deduct credits at the finish of the route (idempotent) --------
            # Prefer the service's session_id as the idempotency key; fallback to a UUID.
            request_id = getattr(result, "session_id", None) or str(uuid.uuid4())

            # Super admins bypass credit consumption
            if not is_super_admin:
                try:
                    credit_service.consume_feature(
                        tenant_id=tenant_id,
                        user_id=user_id,
                        feature_id=feature_id,
                        plan_type=plan_type,
                        request_id=request_id,  # unique (tenant_id, request_id) prevents double-charge on retries
                        reason="idea_refinement",
                        project_id=None,
                        workflow_id=None,
                        metadata={
                            "session_id": getattr(result, "session_id", None),
                            "source": "idea_refinement",
                            "context": request.context,
                            "idea_preview": request.original_idea[:200],
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
            # try:
            #     if prefine_request.user_id:
            #         await history_service.store_refinement_result(
            #             user_id=prefine_request.user_id,
            #             original_idea=prefine_request.raw_idea,
            #             refined_idea=str(result.problem_statements),
            #             refinement_type="idea_refinement",
            #             context={"parsed_context": result.parsed_context.dict()},
            #             metadata={"processing_time": result.processing_time_seconds}
            #         )
            #         logger.info("Refinement result stored in history")
            # except Exception as e:
            #     logger.warning(f"Failed to store refinement in history: {e}")

            # Format the response to match the UI expectations
            problem_statements = []
            if hasattr(result, "problem_statements") and result.problem_statements:
                for stmt in result.problem_statements.problem_statements:
                    problem_statements.append(
                        {
                            "stakeholder": stmt.stakeholder,
                            "statement": stmt.statement,
                            "assumptions": stmt.assumptions,
                        }
                    )

            return IdeaRefinementResponse(
                success=True,
                session_id=result.session_id,
                problem_statements=problem_statements,
                parsed_context={
                    "persona": result.parsed_context.persona,
                    "industry": result.parsed_context.industry,
                    "geography": result.parsed_context.geography,
                    "delivery_mode": result.parsed_context.delivery_mode,
                },
                processing_time=result.processing_time_seconds,
            )
        else:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "refinement_failed",
                    "message": "Idea refinement failed",
                    "suggestions": [],
                },
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refining idea: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "refinement_error",
                "message": "Failed to process idea refinement",
                "details": str(e),
            },
        )


@router.get("/health")
async def idea_refinement_health():
    """Health check for idea refinement service."""
    try:
        # Check service health
        health_status = await idea_refinement_service.health_check()

        return {
            "status": "healthy" if health_status.get("healthy") else "unhealthy",
            "service": "idea_refinement",
            "timestamp": datetime.now().isoformat(),
            "details": health_status,
        }

    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "service": "idea_refinement",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
        }


# =============================================
# HISTORY MANAGEMENT ENDPOINTS
# =============================================


@router.get("/history", response_model=HistoryResponse)
async def get_refinement_history(
    limit: int = Query(10, ge=1, le=100, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    current_user: dict = Depends(get_current_user),
):
    """
    Get refinement history for the authenticated user.
    
    PERFORMANCE OPTIMIZED:
    - Backend caching with 5-minute TTL
    - Selective column fetching (excludes large JSONB fields)
    - Combined count query (single database round-trip)
    
    Note: user_id is extracted from the authenticated user's JWT token.
    No need to pass user_id as a query parameter.
    """
    try:
        # Extract user_id from authenticated user's token - no need for query param
        user_id = current_user["user_id"]
        logger.info(f"Refinement history requested for authenticated user: {user_id}")

        # Create cache key based on all query parameters
        cache_key = f"refiner_history:{user_id}:{limit}:{offset}:{status_filter or 'none'}"
        
        # Try to get from cache first
        cached_result = cache_service.get(cache_key)
        if cached_result:
            logger.debug(f"Returning cached refinement history for user {user_id}")
            return HistoryResponse(
                success=True,
                history=cached_result["history"],
                total_count=cached_result["total_count"],
                user_id=user_id,
                pagination=cached_result["pagination"],
            )

        # Get history from service (optimized query)
        history_data, total_count = history_service.get_user_history(
            user_id=user_id, limit=limit, offset=offset, status_filter=status_filter
        )

        # Build response data
        response_data = {
            "history": history_data,
            "total_count": total_count,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "has_more": (offset + limit) < total_count,
            },
        }
        
        # Cache the result for 5 minutes
        cache_service.set(cache_key, response_data, ttl_seconds=300)
        
        logger.info(f"Retrieved {len(history_data)} refinement sessions for user {user_id}")

        return HistoryResponse(
            success=True,
            history=history_data,
            total_count=total_count,
            user_id=user_id,
            pagination=response_data["pagination"],
        )

    except Exception as e:
        logger.error(f"Error getting refinement history for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "history_retrieval_failed",
                "message": "Failed to get refinement history",
                "details": str(e),
            },
        )


@router.get("/history/{session_id}", response_model=SessionDetailsResponse)
async def get_refinement_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Get details for a specific refinement session.
    
    Note: user_id is extracted from the authenticated user's JWT token.
    The service layer ensures the session belongs to the authenticated user.
    """
    try:
        # Extract user_id from authenticated user's token
        user_id = current_user["user_id"]
        logger.info(f"Refinement session {session_id} details requested by user: {user_id}")

        # Get session details from service (service verifies ownership)
        session_details = history_service.get_session_details(
            session_id=session_id, user_id=user_id
        )

        if not session_details:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "session_not_found",
                    "message": f"Refinement session {session_id} not found",
                },
            )

        return SessionDetailsResponse(
            success=True, session=session_details, session_id=session_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting refinement session {session_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "session_retrieval_failed",
                "message": "Failed to get refinement session details",
                "details": str(e),
            },
        )


@router.post("/history/{result_id}/researched")
async def mark_as_researched(
    result_id: str,
    update: ResearchedStatusUpdate,
    current_user: dict = Depends(get_current_user),
):
    """
    Mark a refinement result as researched.
    
    Note: user_id is extracted from the authenticated user's JWT token.
    """
    try:
        # Extract user_id from authenticated user's token
        user_id = current_user["user_id"]
        logger.info(f"Marking refinement result {result_id} as researched for user {user_id}")

        # Update status through service
        success = history_service.mark_result_researched(
            result_id=result_id, user_id=user_id
        )

        if success:
            return {
                "success": True,
                "message": "Researched status updated successfully",
                "result_id": result_id,
                "researched": update.researched,
                "updated_at": datetime.now().isoformat(),
            }
        else:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "result_not_found",
                    "message": f"Refinement result {result_id} not found",
                },
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating researched status for {result_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "status_update_failed",
                "message": "Failed to update researched status",
                "details": str(e),
            },
        )


# =============================================
# ANALYTICS ENDPOINTS
# =============================================


@router.get("/analytics", response_model=AnalyticsResponse)
async def get_user_analytics(
    current_user: dict = Depends(get_current_user),
):
    """
    Get analytics for the authenticated user's refinement activity.
    
    Note: user_id is extracted from the authenticated user's JWT token.
    """
    try:
        # Extract user_id from authenticated user's token
        user_id = current_user["user_id"]
        logger.info(f"Analytics requested for authenticated user: {user_id}")

        # Get analytics from service
        analytics = history_service.get_analytics_summary(user_id)

        return AnalyticsResponse(
            success=True,
            analytics=analytics,
            user_id=user_id,
            generated_at=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error(f"Error getting analytics for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "analytics_failed",
                "message": "Failed to get user analytics",
                "details": str(e),
            },
        )


# =============================================
# SEARCH ENDPOINTS
# =============================================


@router.get("/search", response_model=SearchResponse)
async def search_refinements(
    query: str = Query(..., min_length=3, description="Search query"),
    limit: int = Query(10, ge=1, le=50, description="Number of results to return"),
    current_user: dict = Depends(get_current_user),
):
    """
    Search through authenticated user's refinement history.
    
    Note: user_id is extracted from the authenticated user's JWT token.
    """
    try:
        # Extract user_id from authenticated user's token
        user_id = current_user["user_id"]
        logger.info(f"Search requested for authenticated user {user_id} with query: {query}")

        # Search through service
        search_results = history_service.search_sessions_by_idea(
            user_id=user_id, search_query=query, limit=limit
        )

        return SearchResponse(
            success=True,
            results=search_results,
            total_count=len(search_results),
            query=query,
            user_id=user_id,
            search_metadata={"searched_at": datetime.now().isoformat()},
        )

    except Exception as e:
        logger.error(f"Error searching refinements for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "search_failed",
                "message": "Failed to search refinements",
                "details": str(e),
            },
        )
