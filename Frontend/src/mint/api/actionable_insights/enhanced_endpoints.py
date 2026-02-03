#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Enhanced Actionable Insights API Endpoints with Vector Storage.

This module provides REST API endpoints for generating and retrieving
actionable insights with vector embeddings for semantic search.
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel, Field

from .enhanced_service import (
    get_enhanced_actionable_insights_service,
    EnhancedInsightGenerationRequest,
    EnhancedInsightsListResponse
)
from ..auth.core import get_current_user

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/insights", tags=["💡 Enhanced Actionable Insights"])

# =============================================
# REQUEST/RESPONSE MODELS
# =============================================

class InsightSearchRequest(BaseModel):
    """Request model for searching insights by similarity."""
    query: str = Field(..., min_length=3, max_length=500, description="Search query for semantic similarity")
    report_id: Optional[str] = Field(None, description="Filter by specific report ID")
    category_filter: Optional[str] = Field(None, description="Filter by insight category")
    priority_filter: Optional[str] = Field(None, description="Filter by priority level")
    match_threshold: float = Field(0.7, ge=0.0, le=1.0, description="Similarity threshold (0.0-1.0)")
    match_count: int = Field(10, ge=1, le=50, description="Maximum number of results to return")

class InsightStatusUpdateRequest(BaseModel):
    """Request model for updating insight status."""
    status: str = Field(..., description="New status for the insight")
    reviewed_by: Optional[str] = Field(None, description="User ID of the reviewer")

# =============================================
# ENHANCED ENDPOINTS
# =============================================

@router.get("/debug/enhanced")
async def debug_enhanced_insights():
    """Debug endpoint to test enhanced actionable insights router."""
    logger.info("🧪 DEBUG: Enhanced actionable insights router test endpoint hit!")
    return {
        "status": "success", 
        "message": "Enhanced actionable insights router is working with vector storage",
        "timestamp": datetime.now().isoformat(),
        "features": ["vector_search", "semantic_similarity", "enhanced_metadata"]
    }

@router.post("/{report_id}/generate-enhanced", response_model=EnhancedInsightsListResponse)
async def generate_enhanced_insights(
    report_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Generate actionable insights with vector storage for semantic search."""
    try:
        # Get user ID from current user
        user_id = current_user.get('id') if isinstance(current_user, dict) else str(current_user)
        
        # Parse request body
        request_body = await request.json()
        force_regenerate = request_body.get("force_regenerate", False)
        include_vector_storage = request_body.get("include_vector_storage", True)
        user_context = request_body.get("user_context", {})
        
        logger.info(f"🎯 ENHANCED GENERATE: Generating insights for report {report_id} by user {user_id}")
        
        # Create enhanced request
        enhanced_request = EnhancedInsightGenerationRequest(
            report_id=report_id,
            user_id=user_id,
            force_regenerate=force_regenerate,
            include_vector_storage=include_vector_storage,
            user_context=user_context
        )
        
        # Get enhanced service
        enhanced_service = get_enhanced_actionable_insights_service()
        
        # Generate insights with vector storage
        result = await enhanced_service.generate_insights_with_vectors(enhanced_request)
        
        logger.info(f"🎯 ENHANCED GENERATE: Generated {result.total_count} insights for report {report_id}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating enhanced insights for report {report_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "enhanced_insights_generation_error",
                "message": "Failed to generate enhanced actionable insights",
                "debug": str(e)
            }
        )

@router.post("/search", response_model=EnhancedInsightsListResponse)
async def search_insights_by_similarity(
    search_request: InsightSearchRequest,
    current_user: dict = Depends(get_current_user)
):
    """Search actionable insights by semantic similarity using vector embeddings."""
    try:
        # Get user ID from current user
        user_id = current_user.get('id') if isinstance(current_user, dict) else str(current_user)
        
        logger.info(f"🔍 VECTOR SEARCH: Searching insights for user {user_id} with query: {search_request.query}")
        
        # Get enhanced service
        enhanced_service = get_enhanced_actionable_insights_service()
        
        # Search insights by similarity
        result = await enhanced_service.search_insights_by_similarity(
            query=search_request.query,
            user_id=user_id,
            report_id=search_request.report_id,
            match_threshold=search_request.match_threshold,
            match_count=search_request.match_count,
            category_filter=search_request.category_filter,
            priority_filter=search_request.priority_filter
        )
        
        logger.info(f"🔍 VECTOR SEARCH: Found {result.total_count} similar insights")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching insights by similarity: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "vector_search_error",
                "message": "Failed to search insights by similarity",
                "debug": str(e)
            }
        )

@router.get("/{report_id}/enhanced", response_model=EnhancedInsightsListResponse)
async def get_enhanced_insights_for_report(
    report_id: str,
    include_vectors: bool = Query(False, description="Include vector search capabilities"),
    current_user: dict = Depends(get_current_user)
):
    """Get all actionable insights for a report with enhanced metadata."""
    try:
        # Get user ID from current user
        user_id = current_user.get('id') if isinstance(current_user, dict) else str(current_user)
        
        logger.info(f"📊 ENHANCED GET: Retrieving insights for report {report_id} by user {user_id}")
        
        # Get enhanced service
        enhanced_service = get_enhanced_actionable_insights_service()
        
        # Get insights for report
        result = await enhanced_service.get_insights_for_report(
            report_id=report_id,
            user_id=user_id,
            include_vectors=include_vectors
        )
        
        logger.info(f"📊 ENHANCED GET: Retrieved {result.total_count} insights for report {report_id}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting enhanced insights for report {report_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "enhanced_insights_retrieval_error",
                "message": "Failed to retrieve enhanced actionable insights",
                "debug": str(e)
            }
        )

@router.put("/{insight_id}/status", response_model=dict)
async def update_insight_status(
    insight_id: str,
    status_request: InsightStatusUpdateRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update the status of an actionable insight."""
    try:
        # Get user ID from current user
        user_id = current_user.get('id') if isinstance(current_user, dict) else str(current_user)
        
        logger.info(f"📝 STATUS UPDATE: Updating insight {insight_id} status to {status_request.status} by user {user_id}")
        
        # Get enhanced service
        enhanced_service = get_enhanced_actionable_insights_service()
        
        # Update insight status
        success = await enhanced_service.update_insight_status(
            insight_id=insight_id,
            user_id=user_id,
            status=status_request.status,
            reviewed_by=status_request.reviewed_by
        )
        
        if success:
            logger.info(f"📝 STATUS UPDATE: Successfully updated insight {insight_id} status")
            return {
                "success": True,
                "message": f"Insight status updated to {status_request.status}",
                "insight_id": insight_id,
                "updated_at": datetime.utcnow().isoformat()
            }
        else:
            logger.error(f"📝 STATUS UPDATE: Failed to update insight {insight_id} status")
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "status_update_failed",
                    "message": "Failed to update insight status"
                }
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating insight status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "status_update_error",
                "message": "Failed to update insight status",
                "debug": str(e)
            }
        )

@router.get("/user/{user_id}/summary")
async def get_user_insights_summary(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a summary of all insights for a user."""
    try:
        # Verify user can access this data
        current_user_id = current_user.get('id') if isinstance(current_user, dict) else str(current_user)
        if current_user_id != user_id:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "access_denied",
                    "message": "You can only access your own insights summary"
                }
            )
        
        logger.info(f"📈 SUMMARY: Getting insights summary for user {user_id}")
        
        # Get enhanced service
        enhanced_service = get_enhanced_actionable_insights_service()
        
        # Get user insights summary
        summary = await enhanced_service.get_user_insights_summary(user_id)
        
        logger.info(f"📈 SUMMARY: Retrieved insights summary for user {user_id}")
        return {
            "success": True,
            "user_id": user_id,
            "summary": summary,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user insights summary: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "summary_retrieval_error",
                "message": "Failed to retrieve user insights summary",
                "debug": str(e)
            }
        )

@router.get("/search/suggestions")
async def get_search_suggestions(
    query: str = Query(..., min_length=2, max_length=100, description="Partial search query"),
    current_user: dict = Depends(get_current_user)
):
    """Get search suggestions based on existing insights."""
    try:
        # Get user ID from current user
        user_id = current_user.get('id') if isinstance(current_user, dict) else str(current_user)
        
        logger.info(f"💡 SUGGESTIONS: Getting search suggestions for user {user_id} with query: {query}")
        
        # This is a placeholder for search suggestions
        # In production, you would implement actual suggestion logic
        suggestions = [
            f"{query} strategy",
            f"{query} implementation",
            f"{query} analysis",
            f"{query} recommendations",
            f"{query} insights"
        ]
        
        return {
            "success": True,
            "query": query,
            "suggestions": suggestions,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting search suggestions: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "suggestions_error",
                "message": "Failed to get search suggestions",
                "debug": str(e)
            }
        )
