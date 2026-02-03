"""
Validation Controller - Request Validation and Business Rules
============================================================

This controller handles all validation logic including:
1. Request data validation
2. Business rule validation
3. Credit validation
4. User permission validation

Separated from endpoints to ensure clean separation of concerns.
"""

import logging
from typing import Dict, Any, Optional
from fastapi import HTTPException

from ..models.workflow_models import WorkflowRequest, WorkflowStatus
# Credit system removed
# from ..api.credit_service import CreditService

logger = logging.getLogger(__name__)


class ValidationController:
    """Handles all validation logic for workflow operations."""
    
    def __init__(self):
        # Credit system removed
        pass
    
    async def validate_workflow_request(
        self, 
        request: WorkflowRequest, 
        user_id: str
    ) -> Dict[str, Any]:
        """
        Validate a workflow request including business rules.
        
        Args:
            request: The workflow request to validate
            user_id: The authenticated user ID
            
        Returns:
            Dict containing validation results and credit status
            
        Raises:
            HTTPException: If validation fails
        """
        try:
            # 1. User ID comes from authenticated JWT token (not request body)
            # No need to validate since request.user_id no longer exists
            
            # 2. Validate query quality
            self._validate_query_quality(request.query)
            
            # 3. Credit system removed - skip credit checks
            logger.info(f"Credit validation bypassed for user {user_id} (credit system removed)")
            
            # 4. Validate session limits (if any)
            await self._validate_session_limits(user_id)
            
            logger.info(f"Workflow request validated successfully for user {user_id}")
            
            return {
                "valid": True,
                "user_id": user_id,
                "query": request.query
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Validation error: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "validation_error",
                    "message": "Request validation failed"
                }
            )
    
    def _validate_query_quality(self, query: str) -> None:
        """Validate that the query meets quality standards."""
        if not query or not query.strip():
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "invalid_query",
                    "message": "Query cannot be empty"
                }
            )
        
        # Check minimum length
        if len(query.strip()) < 10:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "query_too_short",
                    "message": "Query must be at least 10 characters long"
                }
            )
        
        # Check for meaningful content
        words = query.strip().split()
        if len(words) < 3:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "query_too_simple",
                    "message": "Query must contain at least 3 words"
                }
            )
    
    async def _validate_session_limits(self, user_id: str) -> None:
        """Validate that user hasn't exceeded session limits."""
        # This could check for concurrent sessions, daily limits, etc.
        # For now, we'll just log the check
        logger.debug(f"Validating session limits for user {user_id}")
        # TODO: Implement actual session limit validation
        pass
    
    async def validate_session_access(
        self, 
        session_id: str, 
        user_id: str
    ) -> Dict[str, Any]:
        """
        Validate that user has access to a specific session.
        
        Args:
            session_id: The session ID to validate access for
            user_id: The authenticated user ID
            
        Returns:
            Dict containing validation results
            
        Raises:
            HTTPException: If access is denied
        """
        try:
            # TODO: Implement actual session ownership validation
            # This should check if the session belongs to the user
            logger.debug(f"Validating session access: session={session_id}, user={user_id}")
            
            return {
                "valid": True,
                "session_id": session_id,
                "user_id": user_id
            }
            
        except Exception as e:
            logger.error(f"Session access validation error: {str(e)}")
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "access_denied",
                    "message": "Access denied to this session"
                }
            )











