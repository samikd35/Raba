"""
Report History API Endpoints

This module provides FastAPI endpoints for report history management,
including retrieval, pinning, deletion, and restoration operations.

Enhanced with proper authentication handling, user context validation,
and ownership verification as per auth-connection-fixes requirements.
"""

import logging
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, HTTPException, Depends, Query, Request
from pydantic import BaseModel, Field

from .report_history_service import ReportHistoryService
from .report_search_service import ReportSearchService
from .report_usage_analytics_service import ReportUsageAnalyticsService
from .report_analytics_visualization_service import ReportAnalyticsVisualizationService
from ..cache.core import AdminCache
from ..system.middleware.rate_limiter import RateLimiter
from ..auth_v2.utils import get_current_user, get_admin_user
# HTTPBearer removed - using production auth system
from ..system.core.utils import is_valid_uuid

logger = logging.getLogger(__name__)


# validate_user_context function removed - using get_current_user directly

# Create router
router = APIRouter(prefix="/api/reports", tags=["report-history"])

# Test endpoint for debugging
@router.get("/debug-history")
async def debug_history(current_user: dict = Depends(get_current_user)):
    """Debug endpoint to check reports in database."""
    try:
        from ..system.core.supabase_client import get_service_role_client
        client = get_service_role_client()
        
        # Get all PV reports to see what's in the database (bypassing RLS)
        response = client.client.table("documents").select("id, tenant_id, created_by, title, created_at, source_type").eq("source_type", "pv_report").limit(10).execute()
        
        # Also check tenant memberships for the user
        user_id = current_user["user_id"]
        tenant_response = client.client.table("tenant_memberships").select("tenant_id, role").eq("user_id", user_id).execute()
        
        return {
            "success": True,
            "total_reports": len(response.data),
            "reports": response.data,
            "user_tenants": tenant_response.data
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# Pydantic models for request/response
class ReportHistoryFilters(BaseModel):
    """Filters for report history queries"""
    date_range: Optional[Dict[str, str]] = None
    categories: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    only_pinned: Optional[bool] = False
    report_types: Optional[List[str]] = None
    search: Optional[str] = None


class ReportHistoryRequest(BaseModel):
    """Request model for report history"""
    filters: Optional[ReportHistoryFilters] = None
    sort_by: str = Field(default="created_at", description="Field to sort by")
    sort_order: str = Field(default="desc", description="Sort order (asc/desc)")
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")


class PinReportRequest(BaseModel):
    """Request model for pinning/unpinning reports"""
    is_pinned: bool = Field(description="Whether to pin or unpin the report")


class DeleteReportRequest(BaseModel):
    """Request model for deleting reports"""
    permanent: bool = Field(default=False, description="Whether to permanently delete")


class UpdateReportMetadataRequest(BaseModel):
    """Request model for updating report metadata"""
    title: Optional[str] = Field(None, description="New report title")
    summary: Optional[str] = Field(None, description="New report summary")
    tags: Optional[List[str]] = Field(None, description="New report tags")
    category: Optional[str] = Field(None, description="New report category")
    is_archived: Optional[bool] = Field(None, description="Archive status")


class ReportHistoryResponse(BaseModel):
    """Response model for report history"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
    error: Optional[str] = None


# Initialize services
history_service = ReportHistoryService()
search_service = ReportSearchService()
analytics_service = ReportUsageAnalyticsService()
visualization_service = ReportAnalyticsVisualizationService()
cache_service = AdminCache(default_ttl=300, max_size=1000)
rate_limiter = RateLimiter()

# Authentication setup - using production auth system

# Remove the complex wrapper - use get_current_user directly like other working endpoints

# Rate limiting dependency
def search_rate_limit(current_user: dict = Depends(get_current_user)):
    """Rate limiting dependency for search endpoints."""
    user_id = current_user["user_id"]
    is_limited, retry_after = rate_limiter.is_rate_limited(f"search:{user_id}")
    if is_limited:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)}
        )
    return None


@router.get("/history", response_model=ReportHistoryResponse)
async def get_report_history(
    filters: Optional[str] = Query(None, description="JSON string of filters"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: dict = Depends(get_current_user),
    request: Request = None
):
    """
    Get user's report history with filtering, sorting, and pagination.
    
    Enhanced with proper user authentication and ownership verification.
    
    Args:
        filters: Optional JSON string of filters to apply
        sort_by: Field to sort by (default: created_at)
        sort_order: Sort order - 'asc' or 'desc' (default: desc)
        page: Page number (1-based)
        page_size: Number of items per page
        current_user: Current authenticated user
        
    Returns:
        ReportHistoryResponse with reports and pagination info
    """
    try:
        # 🔐 AUTH DEBUG: User ID comes directly from get_current_user
        user_id = current_user["user_id"]
        logger.info(f"🔐 AUTH DEBUG - User ID from get_current_user: {user_id}")
        
        # Extract user token for RLS enforcement
        user_token = None
        if request and request.headers.get("Authorization"):
            auth_header = request.headers.get("Authorization")
            logger.info(f"🔐 AUTH DEBUG - Authorization header present: {auth_header[:50]}...")
            scheme, token = auth_header.split()
            if scheme.lower() == "bearer":
                user_token = token
                logger.info(f"🔐 AUTH DEBUG - Extracted user token for RLS enforcement for user {user_id}")
        else:
            logger.warning(f"🔐 AUTH DEBUG - No Authorization header found for user {user_id}")
        
        logger.info(f"Retrieving report history for user {user_id} with filters: {filters}")
            
        # Create cache key
        cache_key = f"report_history:{user_id}:{filters}:{sort_by}:{sort_order}:{page}:{page_size}"
        
        # Try to get from cache first
        cached_result = cache_service.get(cache_key)
        if cached_result:
            logger.debug(f"Returning cached report history for user {user_id}")
            return ReportHistoryResponse(
                success=True,
                data=cached_result,
                message=f"Retrieved {len(cached_result['reports'])} reports (cached)"
            )
            
        # Parse filters if provided
        parsed_filters = None
        if filters:
            try:
                import json
                parsed_filters = json.loads(filters)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid filters JSON format")
                
        # Get report history with user token for RLS enforcement
        result = await history_service.get_report_history(
            user_id=user_id,
            filters=parsed_filters,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size,
            user_token=user_token
        )
        
        # Cache the result for 5 minutes
        cache_service.set(cache_key, result, ttl_seconds=300)
        
        return ReportHistoryResponse(
            success=True,
            data=result,
            message=f"Retrieved {len(result['reports'])} reports"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting report history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/history", response_model=ReportHistoryResponse)
async def get_report_history_post(
    request: ReportHistoryRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Get user's report history with filtering, sorting, and pagination (POST version).
    
    Args:
        request: Report history request with filters and pagination
        current_user: Current authenticated user
        
    Returns:
        ReportHistoryResponse with reports and pagination info
    """
    try:
        # User ID comes directly from get_current_user
        user_id = current_user["user_id"]
        
        logger.info(f"POST request for report history from user {user_id}")
            
        # Convert filters to dict
        filters_dict = None
        if request.filters:
            filters_dict = request.filters.dict(exclude_none=True)
            
        # Get report history with proper user context
        result = history_service.get_report_history(
            user_id=user_id,
            filters=filters_dict,
            sort_by=request.sort_by,
            sort_order=request.sort_order,
            page=request.page,
            page_size=request.page_size
        )
        
        return ReportHistoryResponse(
            success=True,
            data=result,
            message=f"Retrieved {len(result['reports'])} reports"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting report history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.put("/{report_id}/pin", response_model=ReportHistoryResponse)
async def toggle_pin_report(
    report_id: str,
    request: PinReportRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Pin or unpin a report.
    
    Args:
        report_id: ID of the report to pin/unpin
        request: Pin request with is_pinned flag
        current_user: Current authenticated user
        
    Returns:
        ReportHistoryResponse with updated report data
    """
    try:
        # User ID comes directly from get_current_user
        user_id = current_user["user_id"]
        
        if not is_valid_uuid(report_id):
            raise HTTPException(status_code=400, detail="Invalid report ID format")
        
        logger.info(f"User {user_id} toggling pin status for report {report_id} to {request.is_pinned}")
            
        # Toggle pin status with ownership verification
        result = history_service.toggle_pinned_report(
            user_id=user_id,
            report_id=report_id,
            is_pinned=request.is_pinned
        )
        
        # Invalidate relevant caches
        cache_service.clear_pattern(f"report_history:{user_id}:*")
        
        return ReportHistoryResponse(
            success=True,
            data=result,
            message=result["message"]
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error toggling pin for report {report_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/{report_id}", response_model=ReportHistoryResponse)
async def delete_report(
    report_id: str,
    request: DeleteReportRequest,
    current_user: dict = Depends(get_current_user),
    http_request: Request = None
):
    """
    Delete a report (soft delete by default, permanent if specified).
    
    Args:
        report_id: ID of the report to delete
        request: Delete request with permanent flag
        current_user: Current authenticated user
        http_request: HTTP request object for token extraction
        
    Returns:
        ReportHistoryResponse with deletion result
    """
    try:
        # User ID comes directly from get_current_user
        user_id = current_user["user_id"]
        
        if not is_valid_uuid(report_id):
            raise HTTPException(status_code=400, detail="Invalid report ID format")
        
        # Extract user token for RLS enforcement
        user_token = None
        if http_request:
            auth_header = http_request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                user_token = auth_header[7:]  # Remove "Bearer " prefix
                logger.info(f"Extracted user token for RLS enforcement when deleting report {report_id}")
        
        logger.info(f"User {user_id} deleting report {report_id} (permanent: {request.permanent})")
            
        # Delete report with ownership verification
        result = history_service.delete_report(
            user_id=user_id,
            report_id=report_id,
            permanent=request.permanent,
            user_token=user_token
        )
        
        # Invalidate relevant caches
        cache_service.clear_pattern(f"report_history:{user_id}:*")
        cache_service.clear_pattern(f"report_search:{user_id}:*")
        
        return ReportHistoryResponse(
            success=True,
            data=result,
            message=result["message"]
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting report {report_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/{report_id}/restore", response_model=ReportHistoryResponse)
async def restore_report(
    report_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Restore a soft-deleted report.
    
    Args:
        report_id: ID of the report to restore
        current_user: Current authenticated user
        
    Returns:
        ReportHistoryResponse with restored report data
    """
    try:
        # User ID comes directly from get_current_user
        user_id = current_user["user_id"]
        
        if not is_valid_uuid(report_id):
            raise HTTPException(status_code=400, detail="Invalid report ID format")
        
        logger.info(f"User {user_id} restoring report {report_id}")
            
        # Restore report with ownership verification
        result = history_service.restore_report(
            user_id=user_id,
            report_id=report_id
        )
        
        # Invalidate relevant caches
        cache_service.clear_pattern(f"report_history:{user_id}:*")
        
        return ReportHistoryResponse(
            success=True,
            data=result,
            message=result["message"]
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error restoring report {report_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/trash", response_model=ReportHistoryResponse)
async def get_deleted_reports(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get soft-deleted reports for a user (trash/recycle bin).
    
    Args:
        page: Page number (1-based)
        page_size: Number of items per page
        current_user: Current authenticated user
        
    Returns:
        ReportHistoryResponse with deleted reports and pagination info
    """
    try:
        # User ID comes directly from get_current_user
        user_id = current_user["user_id"]
        
        logger.info(f"User {user_id} retrieving deleted reports (page {page})")
            
        # Get deleted reports with proper user context
        result = history_service.get_deleted_reports(
            user_id=user_id,
            page=page,
            page_size=page_size
        )
        
        return ReportHistoryResponse(
            success=True,
            data=result,
            message=f"Retrieved {len(result['reports'])} deleted reports"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting deleted reports: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.put("/{report_id}/metadata", response_model=ReportHistoryResponse)
async def update_report_metadata(
    report_id: str,
    request: UpdateReportMetadataRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Update report metadata (title, summary, tags, category, archive status).
    
    Args:
        report_id: ID of the report to update
        request: Metadata update request
        current_user: Current authenticated user
        
    Returns:
        ReportHistoryResponse with updated report data
    """
    try:
        # User ID comes directly from get_current_user
        user_id = current_user["user_id"]
        
        if not is_valid_uuid(report_id):
            raise HTTPException(status_code=400, detail="Invalid report ID format")
        
        logger.info(f"User {user_id} updating metadata for report {report_id}")
            
        # Build update data from request
        update_data = {}
        if request.title is not None:
            update_data["title"] = request.title.strip()
        if request.summary is not None:
            update_data["summary"] = request.summary.strip()
        if request.tags is not None:
            update_data["tags"] = request.tags
        if request.category is not None:
            update_data["category"] = request.category.strip()
        if request.is_archived is not None:
            update_data["is_archived"] = request.is_archived
            
        if not update_data:
            raise HTTPException(status_code=400, detail="No metadata fields provided for update")
            
        # Update report metadata with ownership verification
        result = history_service.update_report_metadata(
            user_id=user_id,
            report_id=report_id,
            update_data=update_data
        )
        
        # Invalidate relevant caches
        cache_service.clear_pattern(f"report_history:{user_id}:*")
        cache_service.clear_pattern(f"report_search:{user_id}:*")
        
        return ReportHistoryResponse(
            success=True,
            data=result,
            message="Report metadata updated successfully"
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating metadata for report {report_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/{report_id}/view", response_model=ReportHistoryResponse)
async def update_view_count(
    report_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Update the view count and last viewed timestamp for a report.
    
    Args:
        report_id: ID of the report that was viewed
        current_user: Current authenticated user
        
    Returns:
        ReportHistoryResponse with updated report data
    """
    try:
        # User ID comes directly from get_current_user
        user_id = current_user["user_id"]
        
        if not is_valid_uuid(report_id):
            raise HTTPException(status_code=400, detail="Invalid report ID format")
        
        logger.debug(f"User {user_id} updating view count for report {report_id}")
            
        # Update view count with ownership verification
        result = history_service.update_view_count(
            user_id=user_id,
            report_id=report_id
        )
        
        return ReportHistoryResponse(
            success=True,
            data=result,
            message="View count updated successfully"
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating view count for report {report_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/search", response_model=ReportHistoryResponse)
async def search_reports(
    q: str = Query(..., description="Search query"),
    filters: Optional[str] = Query(None, description="JSON string of additional filters"),
    sort_by: str = Query("relevance", description="Field to sort by (relevance, created_at, title, etc.)"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: dict = Depends(get_current_user),
    request: Request = None,
    _: None = Depends(search_rate_limit)
):
    """
    Search reports using full-text search with advanced operators.
    
    Args:
        q: Search query string
        filters: Optional JSON string of additional filters
        sort_by: Field to sort by (relevance, created_at, title, etc.)
        sort_order: Sort order - 'asc' or 'desc'
        page: Page number (1-based)
        page_size: Number of items per page
        current_user: Current authenticated user
        
    Returns:
        ReportHistoryResponse with search results and metadata
    """
    try:
        # User ID comes directly from get_current_user
        user_id = current_user["user_id"]
        
        logger.info(f"User {user_id} searching reports with query: {q}")
            
        # Create cache key for search results
        cache_key = f"report_search:{user_id}:{q}:{filters}:{sort_by}:{sort_order}:{page}:{page_size}"
        
        # Try to get from cache first (shorter TTL for search results)
        cached_result = cache_service.get(cache_key)
        if cached_result:
            logger.debug(f"Returning cached search results for user {user_id}")
            return ReportHistoryResponse(
                success=True,
                data=cached_result,
                message=f"Found {len(cached_result['reports'])} results (cached)"
            )
            
        # Parse additional filters if provided
        parsed_filters = None
        if filters:
            try:
                import json
                parsed_filters = json.loads(filters)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid filters JSON format")
                
        # Perform search
        result = await search_service.search_reports(
            user_id=user_id,
            query=q,
            filters=parsed_filters,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size
        )
        
        # Cache the result for 2 minutes (shorter than history cache)
        cache_service.set(cache_key, result, ttl_seconds=120)
        
        return ReportHistoryResponse(
            success=True,
            data=result,
            message=f"Found {len(result['reports'])} results"
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error searching reports: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/search/suggestions", response_model=ReportHistoryResponse)
async def get_search_suggestions(
    q: str = Query(..., description="Partial search query"),
    limit: int = Query(10, ge=1, le=20, description="Maximum number of suggestions"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get search term suggestions based on user's report history.
    
    Args:
        q: Partial search query
        limit: Maximum number of suggestions
        current_user: Current authenticated user
        
    Returns:
        ReportHistoryResponse with search suggestions
    """
    try:
        # User ID comes directly from get_current_user
        user_id = current_user["user_id"]
        
        logger.debug(f"User {user_id} requesting search suggestions for: {q}")
            
        # Get search suggestions with proper user context
        suggestions = search_service.suggest_search_terms(
            user_id=user_id,
            partial_query=q,
            limit=limit
        )
        
        return ReportHistoryResponse(
            success=True,
            data={"suggestions": suggestions},
            message=f"Generated {len(suggestions)} suggestions"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting search suggestions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/analytics", response_model=ReportHistoryResponse)
async def get_report_analytics(
    time_range: str = Query("month", description="Time range (week, month, quarter, year)"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get report analytics and usage insights for the user.
    
    Args:
        time_range: Time range for analytics (week, month, quarter, year)
        current_user: Current authenticated user
        
    Returns:
        ReportHistoryResponse with analytics data
    """
    try:
        # User ID comes directly from get_current_user
        user_id = current_user["user_id"]
        
        logger.info(f"User {user_id} requesting analytics for time range: {time_range}")
            
        # Create cache key for analytics
        cache_key = f"report_analytics:{user_id}:{time_range}"
        
        # Try to get from cache first (longer TTL for analytics)
        cached_result = cache_service.get(cache_key)
        if cached_result:
            logger.debug(f"Returning cached analytics for user {user_id}")
            return ReportHistoryResponse(
                success=True,
                data=cached_result,
                message="Analytics data retrieved (cached)"
            )
            
        # Generate usage insights
        insights = await analytics_service.generate_usage_insights(user_id)
        
        # Get visualization data
        viz_data = await visualization_service.get_analytics_visualization_data(
            user_id=user_id,
            time_range=time_range
        )
        
        result = {
            "insights": insights.dict(),
            "visualizations": viz_data
        }
        
        # Cache the result for 15 minutes
        cache_service.set(cache_key, result, ttl_seconds=900)
        
        return ReportHistoryResponse(
            success=True,
            data=result,
            message="Analytics data retrieved"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting report analytics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/analytics/creation-frequency", response_model=ReportHistoryResponse)
async def get_creation_frequency(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get report creation frequency data.
    
    Args:
        days: Number of days to analyze
        current_user: Current authenticated user
        
    Returns:
        ReportHistoryResponse with creation frequency data
    """
    try:
        # User ID comes directly from get_current_user
        user_id = current_user["user_id"]
        
        logger.debug(f"User {user_id} requesting creation frequency for {days} days")
            
        # Create cache key
        cache_key = f"creation_frequency:{user_id}:{days}"
        
        # Try to get from cache first
        cached_result = cache_service.get(cache_key)
        if cached_result:
            return ReportHistoryResponse(
                success=True,
                data={"frequency_data": cached_result},
                message="Creation frequency data retrieved (cached)"
            )
            
        # Get creation frequency data
        frequency_data = await analytics_service.get_creation_frequency(user_id, days)
        
        result = [item.dict() for item in frequency_data]
        
        # Cache the result for 10 minutes
        cache_service.set(cache_key, result, ttl_seconds=600)
        
        return ReportHistoryResponse(
            success=True,
            data={"frequency_data": result},
            message="Creation frequency data retrieved"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting creation frequency: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/analytics/topics", response_model=ReportHistoryResponse)
async def get_topic_analysis(
    limit: int = Query(10, ge=1, le=50, description="Maximum number of topics"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get topic analysis from user's reports.
    
    Args:
        limit: Maximum number of topics to return
        current_user: Current authenticated user
        
    Returns:
        ReportHistoryResponse with topic analysis data
    """
    try:
        # User ID comes directly from get_current_user
        user_id = current_user["user_id"]
        
        logger.debug(f"User {user_id} requesting topic analysis (limit: {limit})")
            
        # Create cache key
        cache_key = f"topic_analysis:{user_id}:{limit}"
        
        # Try to get from cache first
        cached_result = cache_service.get(cache_key)
        if cached_result:
            return ReportHistoryResponse(
                success=True,
                data={"topics": cached_result},
                message="Topic analysis retrieved (cached)"
            )
            
        # Get topic analysis
        topics = await analytics_service.analyze_topics(user_id, limit)
        
        result = [item.dict() for item in topics]
        
        # Cache the result for 10 minutes
        cache_service.set(cache_key, result, ttl_seconds=600)
        
        return ReportHistoryResponse(
            success=True,
            data={"topics": result},
            message="Topic analysis retrieved"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting topic analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/analytics/industries", response_model=ReportHistoryResponse)
async def get_industry_analysis(
    limit: int = Query(10, ge=1, le=50, description="Maximum number of industries"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get industry analysis from user's reports.
    
    Args:
        limit: Maximum number of industries to return
        current_user: Current authenticated user
        
    Returns:
        ReportHistoryResponse with industry analysis data
    """
    try:
        # User ID comes directly from get_current_user
        user_id = current_user["user_id"]
        
        logger.debug(f"User {user_id} requesting industry analysis (limit: {limit})")
            
        # Create cache key
        cache_key = f"industry_analysis:{user_id}:{limit}"
        
        # Try to get from cache first
        cached_result = cache_service.get(cache_key)
        if cached_result:
            return ReportHistoryResponse(
                success=True,
                data={"industries": cached_result},
                message="Industry analysis retrieved (cached)"
            )
            
        # Get industry analysis
        industries = await analytics_service.analyze_industries(user_id, limit)
        
        result = [item.dict() for item in industries]
        
        # Cache the result for 10 minutes
        cache_service.set(cache_key, result, ttl_seconds=600)
        
        return ReportHistoryResponse(
            success=True,
            data={"industries": result},
            message="Industry analysis retrieved"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting industry analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/retention/apply", response_model=ReportHistoryResponse)
async def apply_retention_policy(
    retention_days: int = Query(90, ge=1, le=365, description="Retention period in days"),
    current_user: dict = Depends(get_admin_user)
):
    """
    Apply retention policy to permanently delete old reports.
    This endpoint is typically used by admin users or scheduled tasks.
    
    Args:
        retention_days: Number of days to retain reports (default: 90)
        current_user: Current authenticated user
        
    Returns:
        ReportHistoryResponse with retention policy results
    """
    try:
        # Apply retention policy
        result = history_service.apply_retention_policy(retention_days=retention_days)
        
        return ReportHistoryResponse(
            success=True,
            data=result,
            message=result["message"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error applying retention policy: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{report_id}", response_model=ReportHistoryResponse)
async def get_report_by_id(
    report_id: str,
    current_user: dict = Depends(get_current_user),
    request: Request = None
) -> ReportHistoryResponse:
    """
    Get a specific report by ID or session_id for display purposes.
    
    This endpoint returns clean report content suitable for display in the 
    MarketValidationReportPage, not the raw metadata from the database.
    
    Args:
        report_id: The ID or session_id of the report to retrieve
        current_user: Authentication context from get_current_user
        request: FastAPI request object
        
    Returns:
        ReportHistoryResponse: Response containing clean report data for display
    """
    try:
        user_id = current_user["user_id"]
        
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        # Extract user token for RLS enforcement
        user_token = None
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            user_token = auth_header[7:]  # Remove "Bearer " prefix
            logger.info(f"Extracted user token for RLS enforcement when retrieving report {report_id} for user {user_id}")
        
        logger.info(f"Retrieving report {report_id} for display by user {user_id}")
        
        # First, check if this is a session_id and get the actual report_id
        actual_report_id = report_id
        
        # Try to find the report by ID first, then by session_id if not found
        from ..system.core.supabase_client import get_service_role_client
        service_client = get_service_role_client()
        
        # Check if it's a direct report_id in documents table
        report_response = service_client.client.table("documents").select("id, created_by, metadata").eq("id", report_id).eq("source_type", "pv_report").execute()
        
        if not report_response.data:
            # Not found by report_id, try session_id (stored in metadata or as id)
            logger.info(f"Report not found by ID, trying session_id: {report_id}")
            session_response = service_client.client.table("documents").select("id, created_by, metadata").eq("source_type", "pv_report").execute()
            
            # Look for matching session_id in the results
            matching_report = None
            for doc in session_response.data:
                metadata = doc.get("metadata", {})
                if metadata.get("session_id") == report_id:
                    matching_report = doc
                    break
            
            if matching_report:
                session_response.data = [matching_report]
            
            if session_response.data:
                # Found by session_id, use the actual report_id
                actual_report_id = session_response.data[0]["id"]
                # Verify ownership
                if session_response.data[0]["created_by"] != user_id:
                    raise HTTPException(status_code=403, detail="Access denied - you can only view your own reports")
                logger.info(f"Found report by session_id: {report_id} -> report_id: {actual_report_id}")
            else:
                raise HTTPException(status_code=404, detail="Report not found")
        else:
            # Verify ownership for direct report_id access
            if report_response.data[0]["created_by"] != user_id:
                raise HTTPException(status_code=403, detail="Access denied - you can only view your own reports")
        
        # Use ReportRetrievalService to get properly formatted report content
        from .report_retrieval_service import ReportRetrievalService
        
        retrieval_service = ReportRetrievalService()
        
        try:
            # Get the properly formatted report using the retrieval service
            clean_report = await retrieval_service.get_report_for_display(
                report_id=actual_report_id,
                user_id=user_id,
                user_token=user_token
            )
            
            if not clean_report:
                raise HTTPException(status_code=404, detail="Report not found")
                
        except ValueError as e:
            if "not found" in str(e).lower():
                raise HTTPException(status_code=404, detail="Report not found")
            elif "access denied" in str(e).lower():
                raise HTTPException(status_code=403, detail="Access denied")
            else:
                raise HTTPException(status_code=400, detail=str(e))
        
        if not clean_report.get("content"):
            raise HTTPException(status_code=404, detail="Report content not found")
        
        # Get actionable insights for this report
        insights_data = None
        try:
            from ..actionable_insights import get_actionable_insights_service
            insights_service = get_actionable_insights_service()
            existing_insights = await insights_service._get_existing_insights(actual_report_id, user_id)
            
            if existing_insights:
                insights_data = {
                    "insights": [
                        {
                            "id": insight.id,
                            "insight_type": insight.insight_type,
                            "title": insight.title,
                            "content": insight.content,
                            "confidence_score": insight.confidence_score,
                            "supporting_chunks": insight.supporting_chunks,
                            "user_context": insight.user_context,
                            "generation_metadata": insight.generation_metadata
                        }
                        for insight in existing_insights
                    ],
                    "total_insights": len(existing_insights),
                    "status": "available"
                }
                logger.info(f"Retrieved {len(existing_insights)} actionable insights for report {actual_report_id}")
            else:
                # Check if insights are being generated (stored in documents metadata)
                from ..system.core.supabase_client import get_service_role_client
                service_client = get_service_role_client()
                report_result = service_client.client.table("documents").select("metadata").eq("id", actual_report_id).eq("source_type", "pv_report").single().execute()
                
                insights_status = "not_generated"
                if report_result.data and report_result.data.get("metadata"):
                    metadata = report_result.data.get("metadata", {})
                    insights_status = metadata.get("insights_status", "not_generated")
                
                insights_data = {
                    "insights": [],
                    "total_insights": 0,
                    "status": insights_status
                }
                logger.info(f"No insights found for report {actual_report_id}, status: {insights_status}")
                
        except Exception as insights_error:
            logger.error(f"Error retrieving insights for report {actual_report_id}: {str(insights_error)}")
            insights_data = {
                "insights": [],
                "total_insights": 0,
                "status": "error",
                "error_message": str(insights_error)
            }

        # Ensure report_id is included in the response for frontend consistency
        # This enables the frontend to use report_id for chat functionality
        response_data = {
            **clean_report,
            "report_id": actual_report_id,  # Always include the resolved report_id
            "job_id": report_id,  # Keep original ID for backward compatibility
            "actionable_insights": insights_data  # Include insights data
        }
        
        logger.info(f"Returning report data with report_id: {actual_report_id} and insights data for frontend consistency")
        
        return ReportHistoryResponse(
            success=True,
            data=response_data,
            message="Report retrieved successfully for display"
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        # Handle validation errors from the retrieval service
        if "not found" in str(e).lower() or "access denied" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error retrieving report {report_id} for display: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
