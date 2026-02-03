"""
API endpoints for Feature Video Seen tracking.

Provides:
- GET /api/v1/feature-videos/seen - Get all seen feature IDs for current user
- POST /api/v1/feature-videos/seen - Mark a feature video as seen
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from ..auth_v2.utils import get_current_user
from .models import (
    MarkFeatureVideoSeenRequest,
    MarkFeatureVideoSeenResponse,
    SeenFeatureVideosResponse,
)
from .service import get_feature_video_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/feature-videos",
    tags=["Feature Videos"],
)


@router.get(
    "/seen",
    response_model=SeenFeatureVideosResponse,
    summary="Get all seen feature videos",
    description="Returns a list of all feature IDs for which the current user has seen the help video.",
)
async def get_seen_feature_videos(
    current_user: dict = Depends(get_current_user),
) -> SeenFeatureVideosResponse:
    """
    Get all feature video IDs that the authenticated user has seen.
    
    This endpoint is designed to be called once on app load to populate
    the frontend's seen features cache.
    """
    user_id = current_user.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID not found in token",
        )
    
    try:
        service = get_feature_video_service()
        seen_features = await service.get_seen_features(user_id)
        
        return SeenFeatureVideosResponse(seen=seen_features)
        
    except Exception as e:
        logger.error(f"Failed to get seen features: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve seen feature videos",
        )


@router.post(
    "/seen",
    response_model=MarkFeatureVideoSeenResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark a feature video as seen",
    description="Records that the current user has seen a specific feature's help video. Idempotent - safe to call multiple times.",
)
async def mark_feature_video_seen(
    request: MarkFeatureVideoSeenRequest,
    current_user: dict = Depends(get_current_user),
) -> MarkFeatureVideoSeenResponse:
    """
    Mark a feature video as seen for the authenticated user.
    
    This should be called when:
    - A video starts autoplaying on first visit
    - A user clicks the help icon to replay a video
    
    The operation is idempotent - calling it multiple times for the same
    feature will not create duplicate records.
    """
    user_id = current_user.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID not found in token",
        )
    
    # Validate feature_id format (basic validation)
    feature_id = request.feature_id.strip().lower()
    if not feature_id or len(feature_id) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid feature_id format",
        )
    
    try:
        service = get_feature_video_service()
        success, created = await service.mark_feature_seen(
            user_id=user_id,
            feature_id=feature_id,
            source=request.source,
        )
        
        return MarkFeatureVideoSeenResponse(
            ok=success,
            feature_id=feature_id,
            created=created,
        )
        
    except Exception as e:
        logger.error(f"Failed to mark feature seen: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark feature video as seen",
        )
