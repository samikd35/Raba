#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Report Validation Service for MINT.

This module provides comprehensive report validation functionality for chat endpoints,
ensuring proper report ID validation, ownership verification, and clear error messaging.
"""

import logging
import uuid
from typing import Dict, Any, Optional, Tuple
from enum import Enum

from ..system.core.supabase_client import get_supabase_client, get_service_role_client
from ..cache.enhanced import get_cache_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ReportValidationError(Exception):
    """Base exception for report validation errors."""
    pass


class ReportNotFoundError(ReportValidationError):
    """Raised when a report cannot be found."""
    pass


class ReportAccessDeniedError(ReportValidationError):
    """Raised when user doesn't have access to a report."""
    pass


class ReportValidationResult:
    """Result of report validation."""
    
    def __init__(
        self,
        success: bool,
        report_data: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        user_message: Optional[str] = None
    ):
        self.success = success
        self.report_data = report_data
        self.error_code = error_code
        self.error_message = error_message
        self.user_message = user_message
    
    @property
    def report_id(self) -> Optional[str]:
        """Get the validated report ID."""
        return self.report_data.get("id") if self.report_data else None
    
    @property
    def user_id(self) -> Optional[str]:
        """Get the report owner's user ID."""
        return self.report_data.get("user_id") if self.report_data else None


class ReportValidationService:
    """Service for validating reports and user access."""
    
    def __init__(self, user_token: Optional[str] = None):
        """Initialize the validation service.
        
        Args:
            user_token: Optional JWT token for user authentication
        """
        self.user_token = user_token
        
        # Use user-authenticated client if token provided
        if user_token:
            logger.info("Initializing report validation service with user authentication")
            self.supabase = get_supabase_client(use_service_role=False)
        else:
            logger.info("Initializing report validation service with service role")
            self.supabase = get_supabase_client(use_service_role=True)
        
        # Initialize cache service for performance optimization
        try:
            self.cache_service = get_cache_service()
            logger.debug("Cache service initialized for report validation")
        except Exception as e:
            logger.warning(f"Cache service not available: {e}")
            self.cache_service = None
    
    def _is_valid_uuid(self, value: str) -> bool:
        """Check if a string is a valid UUID.
        
        Args:
            value: String to validate
            
        Returns:
            bool: True if valid UUID, False otherwise
        """
        try:
            uuid.UUID(value)
            return True
        except (ValueError, TypeError):
            return False
    
    async def _find_report_by_id(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Find a report by its ID.
        
        Args:
            report_id: Report ID to search for
            
        Returns:
            Dict containing report data if found, None otherwise
        """
        try:
            # Use service role client for initial lookup to bypass RLS
            service_client = get_service_role_client()
            
            result = service_client.client.table("documents").select(
                "id, created_by, metadata, title, source_type, created_at"
            ).eq("id", report_id).eq("source_type", "pv_report").execute()
            
            if result.data and len(result.data) > 0:
                report = result.data[0]
                # Map documents table fields to expected format
                mapped_report = {
                    'id': report['id'],
                    'user_id': report['created_by'],  # Map created_by to user_id
                    'session_id': report.get('metadata', {}).get('session_id', report['id']),
                    'title': report['title'],
                    'report_type': report.get('metadata', {}).get('report_type', 'pv_report'),
                    'created_at': report['created_at']
                }
                logger.info(f"Found report by ID: {mapped_report['id']}, user_id={mapped_report['user_id']}")
                return mapped_report
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding report by ID {report_id}: {e}")
            return None
    
    async def _find_report_by_session_id(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Find a report by its session ID.
        
        Args:
            session_id: Session ID to search for
            
        Returns:
            Dict containing report data if found, None otherwise
        """
        try:
            # Use service role client for initial lookup to bypass RLS
            service_client = get_service_role_client()
            
            result = service_client.client.table("documents").select(
                "id, created_by, metadata, title, source_type, created_at"
            ).eq("id", session_id).eq("source_type", "pv_report").execute()
            
            if result.data and len(result.data) > 0:
                # Since we're using documents table, session_id is stored as the primary key 'id'
                report = result.data[0]
                # Map documents table fields to expected format
                mapped_report = {
                    'id': report['id'],
                    'user_id': report['created_by'],  # Map created_by to user_id
                    'session_id': report.get('metadata', {}).get('session_id', report['id']),
                    'title': report['title'],
                    'report_type': report.get('metadata', {}).get('report_type', 'pv_report'),
                    'created_at': report['created_at']
                }
                logger.info(f"Found report by session_id: {mapped_report['id']}, user_id={mapped_report['user_id']}")
                return mapped_report
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding report by session_id {session_id}: {e}")
            return None
    
    async def _check_report_chunks_exist(self, report_id: str) -> Tuple[bool, int]:
        """Check if a report has chunks available for chat.
        
        Optimized version with caching and efficient queries.
        
        Args:
            report_id: Report ID to check
            
        Returns:
            Tuple of (has_chunks, chunk_count)
        """
        try:
            # Check cache first if available
            cache_key = f"chunks_exist:{report_id}"
            if hasattr(self, 'cache_service') and self.cache_service:
                cached_result = await self.cache_service.get(cache_key)
                if cached_result:
                    logger.debug(f"Cache hit for chunks check: {report_id}")
                    return cached_result['has_chunks'], cached_result['count']
            
            # Use service role client to check chunks with optimized query
            service_client = get_service_role_client()
            
            # First, do a fast existence check (limit 1 for speed)
            existence_result = service_client.client.table("report_chunks").select(
                "id"
            ).eq("report_id", report_id).limit(1).execute()
            
            has_chunks = len(existence_result.data) > 0
            
            if has_chunks:
                # Only count if chunks exist (avoid expensive count on empty results)
                count_result = service_client.client.table("report_chunks").select(
                    "id", count="exact"
                ).eq("report_id", report_id).execute()
                chunk_count = count_result.count if hasattr(count_result, "count") else len(existence_result.data)
            else:
                chunk_count = 0
            
            # Cache the result for 5 minutes
            if hasattr(self, 'cache_service') and self.cache_service:
                cache_data = {'has_chunks': has_chunks, 'count': chunk_count}
                await self.cache_service.set(cache_key, cache_data, ttl=300)  # 5 minutes
            
            logger.info(f"Report {report_id} has {chunk_count} chunks available (cached for future requests)")
            return has_chunks, chunk_count
            
        except Exception as e:
            logger.error(f"Error checking chunks for report {report_id}: {e}")
            # Return True for chunks to avoid blocking chat (graceful degradation)
            return True, 1
    
    async def _verify_user_ownership(self, report_data: Dict[str, Any], user_id: str) -> bool:
        """Verify that a user owns a report.
        
        Args:
            report_data: Report data dictionary
            user_id: User ID to verify ownership for
            
        Returns:
            bool: True if user owns the report, False otherwise
        """
        report_user_id = report_data.get("user_id")
        
        if not report_user_id:
            logger.warning(f"Report {report_data.get('id')} has no user_id - legacy report")
            # For legacy reports without user_id, we'll allow access but log it
            return True
        
        if report_user_id == user_id:
            logger.info(f"User {user_id} owns report {report_data.get('id')}")
            return True
        
        logger.warning(f"User {user_id} does not own report {report_data.get('id')} (owner: {report_user_id})")
        return False
    
    async def validate_report_for_chat(
        self, 
        report_identifier: str, 
        user_id: str,
        check_chunks: bool = True
    ) -> ReportValidationResult:
        """Validate a report for chat functionality.
        
        This method performs comprehensive validation:
        1. Validates report exists in documents table
        2. Verifies user ownership
        3. Optionally checks if chunks exist for chat
        4. Returns detailed error information
        
        Args:
            report_identifier: Report ID or session ID
            user_id: User ID requesting access
            check_chunks: Whether to check if chunks exist
            
        Returns:
            ReportValidationResult: Validation result with detailed information
        """
        logger.info(f"Validating report {report_identifier} for user {user_id}")
        
        # Step 1: Find the report
        report_data = None
        
        # Try to find by ID first (most common case)
        if self._is_valid_uuid(report_identifier):
            report_data = await self._find_report_by_id(report_identifier)
        
        # If not found by ID, try by session_id
        if not report_data:
            report_data = await self._find_report_by_session_id(report_identifier)
        
        # Step 2: Check if report exists
        if not report_data:
            logger.error(f"Report not found with identifier: {report_identifier}")
            return ReportValidationResult(
                success=False,
                error_code="report_not_found",
                error_message=f"Report not found with identifier: {report_identifier}",
                user_message="The requested report could not be found. It may have been deleted or you may not have access to it."
            )
        
        # Step 3: Verify user ownership
        if not await self._verify_user_ownership(report_data, user_id):
            logger.error(f"User {user_id} does not have access to report {report_data['id']}")
            return ReportValidationResult(
                success=False,
                error_code="access_denied",
                error_message=f"User {user_id} does not have access to report {report_data['id']}",
                user_message="You don't have permission to access this report."
            )
        
        # Step 4: Check if chunks exist (optional)
        if check_chunks:
            has_chunks, chunk_count = await self._check_report_chunks_exist(report_data["id"])
            
            if not has_chunks:
                logger.warning(f"Report {report_data['id']} has no chunks available for chat")
                return ReportValidationResult(
                    success=False,
                    report_data=report_data,
                    error_code="no_chunks_found",
                    error_message=f"Report {report_data['id']} has no chunks available for chat",
                    user_message="This report is not ready for chat yet. It may still be processing, or there may have been an issue during report generation."
                )
        
        # Step 5: Success - report is valid and accessible
        logger.info(f"Report {report_data['id']} validated successfully for user {user_id}")
        return ReportValidationResult(
            success=True,
            report_data=report_data
        )
    
    async def validate_report_exists(self, report_identifier: str) -> ReportValidationResult:
        """Simple validation to check if a report exists.
        
        Args:
            report_identifier: Report ID or session ID
            
        Returns:
            ReportValidationResult: Validation result
        """
        logger.info(f"Checking if report exists: {report_identifier}")
        
        # Find the report
        report_data = None
        
        if self._is_valid_uuid(report_identifier):
            report_data = await self._find_report_by_id(report_identifier)
        
        if not report_data:
            report_data = await self._find_report_by_session_id(report_identifier)
        
        if not report_data:
            return ReportValidationResult(
                success=False,
                error_code="report_not_found",
                error_message=f"Report not found with identifier: {report_identifier}",
                user_message="The requested report could not be found."
            )
        
        return ReportValidationResult(
            success=True,
            report_data=report_data
        )


# Singleton instance
_report_validation_service = None


def get_report_validation_service(user_token: Optional[str] = None) -> ReportValidationService:
    """Get an instance of the report validation service.
    
    Args:
        user_token: Optional JWT token for user authentication
        
    Returns:
        ReportValidationService: The validation service
    """
    # Create a new instance with user token (don't use singleton for user-specific instances)
    if user_token:
        logger.info("Creating user-authenticated report validation service")
        return ReportValidationService(user_token=user_token)
    
    # Use singleton for service-role instances
    global _report_validation_service
    if _report_validation_service is None:
        logger.info("Initializing report validation service")
        _report_validation_service = ReportValidationService()
    return _report_validation_service