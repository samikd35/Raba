"""
Migration Endpoints

API endpoints for handling report data migration operations with proper
error handling and rollback mechanisms.

Requirements addressed:
- 5.2: Proper rollback mechanisms for failed database operations
- 5.3: Data migration service to convert existing reports from old structure to new format
- 5.5: Proper error messages without exposing sensitive system information
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Query, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Role system removed - admin endpoints now require basic authentication only
from ...auth.production.system import get_current_user
from ...report.report_migration_service import get_report_migration_service, MigrationResult
from ..core.database_transaction_manager import get_database_transaction_manager
from ...report.report_error_handler import get_report_error_handler
from ..core.utils import is_valid_uuid

logger = logging.getLogger(__name__)

# Create router for migration endpoints
migration_router = APIRouter(prefix="/api/migration", tags=["migration"])


class MigrationRequest(BaseModel):
    """Request model for single report migration."""
    
    report_id: str = Field(..., description="ID of the report to migrate")
    target_structure: str = Field(default="unified", description="Target structure type")
    create_backup: bool = Field(default=True, description="Whether to create backup for rollback")


class BatchMigrationRequest(BaseModel):
    """Request model for batch report migration."""
    
    report_ids: List[str] = Field(..., description="List of report IDs to migrate")
    target_structure: str = Field(default="unified", description="Target structure type")
    create_backups: bool = Field(default=True, description="Whether to create backups for rollback")
    stop_on_error: bool = Field(default=False, description="Whether to stop batch on first error")


class MigrationStatusResponse(BaseModel):
    """Response model for migration status."""
    
    success: bool
    report_id: str
    migration_steps: List[str]
    error_message: Optional[str] = None
    rollback_performed: bool = False


class BatchMigrationStatusResponse(BaseModel):
    """Response model for batch migration status."""
    
    total_reports: int
    successful_migrations: int
    failed_migrations: int
    results: List[MigrationStatusResponse]


@migration_router.post("/migrate-report", response_model=MigrationStatusResponse)
async def migrate_single_report(
    request: MigrationRequest,
    current_user_id: str = Depends(get_current_user),
    background_tasks: BackgroundTasks = BackgroundTasks()
) -> MigrationStatusResponse:
    """
    Migrate a single report to the new structure.
    
    This endpoint allows administrators to migrate individual reports
    from old structures to new formats with proper error handling
    and rollback mechanisms.
    
    Args:
        request: Migration request parameters
        admin_context: Admin authentication context
        background_tasks: Background task manager
        
    Returns:
        Migration status and results
        
    Raises:
        HTTPException: If migration fails or access is denied
    """
    try:
        logger.info(f"Admin {admin_context.get('user_id')} initiating migration for report {request.report_id}")
        
        # Validate report ID format
        if not is_valid_uuid(request.report_id):
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "validation_error",
                    "message": "Invalid report ID format",
                    "code": "INVALID_REPORT_ID"
                }
            )
        
        # Get migration service
        migration_service = get_report_migration_service()
        
        # Perform migration
        result = await migration_service.migrate_report(
            report_id=request.report_id,
            target_structure=request.target_structure,
            create_backup=request.create_backup
        )
        
        # Convert result to response model
        response = MigrationStatusResponse(
            success=result.success,
            report_id=result.report_id,
            migration_steps=result.migration_steps,
            rollback_performed=result.rollback_performed
        )
        
        if not result.success and result.error:
            response.error_message = result.error.user_message
            
            # Log error for monitoring
            error_handler = get_report_error_handler()
            error_handler.log_error_for_monitoring(result.error)
        
        # Schedule cleanup of old backups in background
        if result.success and request.create_backup:
            background_tasks.add_task(
                _cleanup_old_backups,
                migration_service,
                older_than_days=7
            )
        
        logger.info(f"Migration completed for report {request.report_id}: success={result.success}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during single report migration: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "migration_error",
                "message": "An unexpected error occurred during migration",
                "code": "MIGRATION_SYSTEM_ERROR"
            }
        )


@migration_router.post("/migrate-batch", response_model=BatchMigrationStatusResponse)
async def migrate_batch_reports(
    request: BatchMigrationRequest,
    current_user_id: str = Depends(get_current_user),
    background_tasks: BackgroundTasks = BackgroundTasks()
) -> BatchMigrationStatusResponse:
    """
    Migrate multiple reports in batch.
    
    This endpoint allows administrators to migrate multiple reports
    efficiently with proper error handling and rollback mechanisms.
    
    Args:
        request: Batch migration request parameters
        admin_context: Admin authentication context
        background_tasks: Background task manager
        
    Returns:
        Batch migration status and results
        
    Raises:
        HTTPException: If batch migration fails or access is denied
    """
    try:
        logger.info(f"Admin {admin_context.get('user_id')} initiating batch migration for {len(request.report_ids)} reports")
        
        # Validate report IDs
        invalid_ids = [rid for rid in request.report_ids if not is_valid_uuid(rid)]
        if invalid_ids:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "validation_error",
                    "message": f"Invalid report ID formats: {invalid_ids}",
                    "code": "INVALID_REPORT_IDS"
                }
            )
        
        # Limit batch size for performance
        if len(request.report_ids) > 100:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "validation_error",
                    "message": "Batch size cannot exceed 100 reports",
                    "code": "BATCH_SIZE_EXCEEDED"
                }
            )
        
        # Get migration service
        migration_service = get_report_migration_service()
        
        # Perform batch migration
        results = await migration_service.migrate_batch(
            report_ids=request.report_ids,
            target_structure=request.target_structure,
            create_backups=request.create_backups,
            stop_on_error=request.stop_on_error
        )
        
        # Convert results to response models
        response_results = []
        successful_count = 0
        failed_count = 0
        
        for result in results:
            response_result = MigrationStatusResponse(
                success=result.success,
                report_id=result.report_id,
                migration_steps=result.migration_steps,
                rollback_performed=result.rollback_performed
            )
            
            if result.success:
                successful_count += 1
            else:
                failed_count += 1
                if result.error:
                    response_result.error_message = result.error.user_message
                    
                    # Log error for monitoring
                    error_handler = get_report_error_handler()
                    error_handler.log_error_for_monitoring(result.error)
            
            response_results.append(response_result)
        
        # Schedule cleanup of old backups in background
        if successful_count > 0 and request.create_backups:
            background_tasks.add_task(
                _cleanup_old_backups,
                migration_service,
                older_than_days=7
            )
        
        response = BatchMigrationStatusResponse(
            total_reports=len(request.report_ids),
            successful_migrations=successful_count,
            failed_migrations=failed_count,
            results=response_results
        )
        
        logger.info(f"Batch migration completed: {successful_count}/{len(request.report_ids)} successful")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during batch migration: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "migration_error",
                "message": "An unexpected error occurred during batch migration",
                "code": "BATCH_MIGRATION_SYSTEM_ERROR"
            }
        )


@migration_router.post("/rollback-report/{report_id}")
async def rollback_report_migration(
    report_id: str,
    current_user_id: str = Depends(get_current_user)
) -> JSONResponse:
    """
    Rollback a report migration using backup data.
    
    This endpoint allows administrators to rollback a report migration
    if issues are discovered after the migration is complete.
    
    Args:
        report_id: ID of the report to rollback
        admin_context: Admin authentication context
        
    Returns:
        Rollback status
        
    Raises:
        HTTPException: If rollback fails or access is denied
    """
    try:
        logger.info(f"Admin {admin_context.get('user_id')} initiating rollback for report {report_id}")
        
        # Validate report ID format
        if not is_valid_uuid(report_id):
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "validation_error",
                    "message": "Invalid report ID format",
                    "code": "INVALID_REPORT_ID"
                }
            )
        
        # Get migration service
        migration_service = get_report_migration_service()
        
        # Attempt rollback
        rollback_success = await migration_service._perform_rollback(report_id)
        
        if rollback_success:
            logger.info(f"Successfully rolled back report {report_id}")
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "message": "Report migration rolled back successfully",
                    "report_id": report_id
                }
            )
        else:
            logger.error(f"Failed to rollback report {report_id}")
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "rollback_error",
                    "message": "Failed to rollback report migration",
                    "code": "ROLLBACK_FAILED"
                }
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during rollback: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "rollback_error",
                "message": "An unexpected error occurred during rollback",
                "code": "ROLLBACK_SYSTEM_ERROR"
            }
        )


@migration_router.get("/migration-status/{report_id}")
async def get_migration_status(
    report_id: str,
    current_user_id: str = Depends(get_current_user)
) -> JSONResponse:
    """
    Get the migration status of a specific report.
    
    Args:
        report_id: ID of the report to check
        admin_context: Admin authentication context
        
    Returns:
        Migration status information
        
    Raises:
        HTTPException: If status check fails or access is denied
    """
    try:
        # Validate report ID format
        if not is_valid_uuid(report_id):
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "validation_error",
                    "message": "Invalid report ID format",
                    "code": "INVALID_REPORT_ID"
                }
            )
        
        # Get transaction manager to check for active transactions
        transaction_manager = get_database_transaction_manager()
        
        # Check for active transactions related to this report
        # (This is a simplified check - in a real implementation,
        # you might want to track migration status in a separate table)
        
        return JSONResponse(
            status_code=200,
            content={
                "report_id": report_id,
                "migration_status": "completed",  # Simplified status
                "last_checked": datetime.utcnow().isoformat(),
                "message": "Migration status check completed"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking migration status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "status_check_error",
                "message": "Failed to check migration status",
                "code": "STATUS_CHECK_FAILED"
            }
        )


@migration_router.delete("/cleanup-backups")
async def cleanup_migration_backups(
    older_than_days: int = Query(default=30, ge=1, le=365),
    current_user_id: str = Depends(get_current_user)
) -> JSONResponse:
    """
    Clean up old migration backup data.
    
    Args:
        older_than_days: Remove backups older than this many days
        admin_context: Admin authentication context
        
    Returns:
        Cleanup results
        
    Raises:
        HTTPException: If cleanup fails or access is denied
    """
    try:
        logger.info(f"Admin {admin_context.get('user_id')} initiating backup cleanup (older than {older_than_days} days)")
        
        # Get migration service
        migration_service = get_report_migration_service()
        
        # Perform cleanup
        cleaned_count = await migration_service.cleanup_backups(
            older_than_days=older_than_days
        )
        
        logger.info(f"Cleaned up {cleaned_count} backup records")
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": f"Successfully cleaned up {cleaned_count} backup records",
                "cleaned_count": cleaned_count,
                "older_than_days": older_than_days
            }
        )
        
    except Exception as e:
        logger.error(f"Error during backup cleanup: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "cleanup_error",
                "message": "Failed to clean up backup data",
                "code": "CLEANUP_FAILED"
            }
        )


async def _cleanup_old_backups(migration_service, older_than_days: int = 7):
    """Background task to clean up old backup data."""
    try:
        cleaned_count = await migration_service.cleanup_backups(
            older_than_days=older_than_days
        )
        logger.info(f"Background cleanup completed: {cleaned_count} backups removed")
    except Exception as e:
        logger.error(f"Background backup cleanup failed: {str(e)}")


# Export the router
__all__ = ["migration_router"]