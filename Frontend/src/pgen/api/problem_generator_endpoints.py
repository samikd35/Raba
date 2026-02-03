"""
Problem Generator API Endpoints

This module provides FastAPI endpoints for the Problem Generator feature,
following the existing patterns and authentication from the main MINT API.
"""

import uuid
import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional
from time import time
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator

# Import NEW production authentication system
from src.mint.api.auth_v2.utils import get_current_user
from src.mint.api.system.core.supabase_client import get_supabase_client
from src.mint.api.credit.service import CreditService, InsufficientCreditsError, InvalidConsumptionRequest

# Performance optimization imports
try:
    from ..utils.performance_optimizer import (
        get_cache_manager,
        get_request_optimizer,
        performance_monitor
    )
    PERFORMANCE_ENABLED = True
except ImportError:
    PERFORMANCE_ENABLED = False
    logging.warning("Performance optimizer not available")

# Database-first job status tracking (replaces in-memory store)
from ..services.job_status_service import get_job_status_service, JobStatus

# Enhanced logging
from ..utils.logging_config import get_contextual_logger, performance_logger

# Authentication and database utilities
from ..utils.auth_utils import AuthenticatedUser, log_auth_event
from ..utils.database_utils import (
    DatabaseValidator, 
    execute_with_retry, 
    validate_database_connection,
    database_transaction,
    DatabaseOperation
)

# Task management imports removed - using job_status table instead


# Import Problem Generator components
from ..models.problem_models import (
    ProblemGenerationRequest,
    ProblemStatementResponse,
    ProblemStatementSummary
)
from ..services.problem_database_service import ProblemDatabaseService, SearchFilters

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/pgen", tags=["🔒 Problem Generator"])

credit_service = CreditService()

# =============================================
# REQUEST/RESPONSE MODELS
# =============================================

class ProblemGenerationJobRequest(BaseModel):
    """Request model for starting problem generation job."""
    parameters: ProblemGenerationRequest = Field(..., description="Problem generation parameters")
    
    @validator('parameters')
    def validate_parameters(cls, v):
        if not v or not isinstance(v, ProblemGenerationRequest):
            raise ValueError("parameters must be a non-empty ProblemGenerationRequest")
        return v

class ProblemGenerationJobResponse(BaseModel):
    """Response model for problem generation job."""
    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Job status: pending, processing, completed, failed")
    user_id: str = Field(..., description="User identifier")
    created_at: datetime = Field(..., description="Job creation timestamp")
    message: str = Field(..., description="Status message")
    problems: Optional[List[ProblemStatementResponse]] = Field(None, description="Generated problem statements (if completed)")
    problems_count: int = Field(0, description="Number of problems generated")
    processing_time_ms: Optional[int] = Field(None, description="Total processing time in milliseconds")

class ProblemSearchResponse(BaseModel):
    """Response model for problem search."""
    problems: List[ProblemStatementSummary] = Field(..., description="Found problem statements")
    total: int = Field(..., description="Total number of matching problems")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_prev: bool = Field(..., description="Whether there are previous pages")

class AnalyticsResponse(BaseModel):
    """Response model for user analytics."""
    user_id: str
    total_problems_generated: int
    total_sessions: int
    success_rate: float
    average_generation_time_ms: float
    average_satisfaction_rating: float

# =============================================
# HELPER FUNCTIONS
# =============================================

# Removed validate_user_token as authentication is now handled by get_current_user

def get_problem_database_service() -> ProblemDatabaseService:
    """Get Problem Database Service instance."""
    return ProblemDatabaseService(use_service_role=True)

# =============================================
# PROBLEM GENERATION ENDPOINTS
# =============================================

@router.get("/health")
async def health_check():
    """Health check endpoint for Problem Generator service."""
    try:
        # Basic health checks
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "problem-generator",
            "version": "2.0.0"
        }
        
        # Check database connectivity
        try:
            validate_database_connection()
            health_status["database"] = "connected"
        except Exception as e:
            health_status["database"] = f"error: {str(e)}"
            health_status["status"] = "degraded"
        
        # Task management system removed - using job_status table for simpler job tracking
        health_status["job_tracking"] = "job_status_table"
        
        # Check cache if available
        if PERFORMANCE_ENABLED:
            try:
                cache_manager = get_cache_manager()
                health_status["cache"] = "available"
            except Exception as e:
                health_status["cache"] = f"error: {str(e)}"
        else:
            health_status["cache"] = "disabled"
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
        )

# @router.post("/test/generate-simple", response_model=ProblemGenerationJobResponse)
# async def generate_problems_simple(
#     job_request: ProblemGenerationJobRequest,
#     current_user_id: str = Depends(get_current_user)
# ):
#     """
#     Simple problem generation endpoint that provides immediate results for testing.
    
#     This bypasses the complex 12-node workflow and provides sample problems
#     based on the user's parameters.
#     """
    
#     try:
#         # Generate a job ID
#         job_id = str(uuid.uuid4())
        
#         # Create sample problems based on parameters
#         sample_problems = create_sample_problems(job_request.parameters)
        
#         return ProblemGenerationJobResponse(
#             job_id=job_id,
#             status="completed",
#             user_id=current_user_id,
#             created_at=datetime.utcnow(),
#             message=f"Successfully generated {len(sample_problems)} sample problems"
#         )
        
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Simple generation failed: {str(e)}"
#         )



@router.post("/generate", response_model=ProblemGenerationJobResponse)
@performance_monitor("generate_problems") if PERFORMANCE_ENABLED else lambda f: f
async def generate_problems(
    job_request: ProblemGenerationJobRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """
    Start a new problem generation job.
    
    This endpoint initiates the problem generation process using the specified parameters.
    The generation runs in the background and can be monitored via the status endpoint.
    Includes caching for identical parameter sets to improve performance.
    """
    start_time = time()
    
    try:
        # Hardcoded feature for problem generation
        from src.mint.api.features.dependencies import resolve_feature_id
        feature_id = await resolve_feature_id("problem_generator")
        
        # Standardized user validation - no fallbacks
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        # Map your plan type; adjust if you store it differently.
        plan_type = current_user["tenant_type"]

        authenticated_user = AuthenticatedUser(user_id)
        
        # Validate database connection before proceeding
        validate_database_connection()
        
        # Log authentication event
        log_auth_event(user_id, "problem_generation_request", "job", None, True)

        # Super admins bypass credit checks
        user_roles = current_user.get("roles", [])
        is_super_admin = len(user_roles) > 0 and user_roles[0] == "super_admin"
        
        if not is_super_admin:
            has_credit = credit_service.has_sufficient_credits_for_feature(
                tenant_id=tenant_id,
                feature_id=feature_id,
                plan_type=plan_type
            )
            if not has_credit:
                raise HTTPException(
                    status_code=402,
                    detail={"code": "insufficient_credits",
                            "message": "You do not have enough credits for this feature."}
                )
        else:
            logger.info(f"Super admin {user_id} bypassing credit check for feature {feature_id}")
        
        # Credit system removed - problem generation now runs without credit checks
        logger.info(f"Problem generation starting for user {user_id} (credit system disabled)")
        
        # Check cache for identical parameters (if enabled)
        cached_result = None
        if PERFORMANCE_ENABLED:
            cache_manager = get_cache_manager()
            cached_result = cache_manager.get_cached_problem_results(
                job_request.parameters.dict()
            )
            
            if cached_result:
                logger.info(f"Cache hit for user {user_id} - returning cached results")
                
                # Create a job with immediate completion using database tracking
                job_id = str(uuid.uuid4())
                
                # Use transaction for atomic operations
                with database_transaction() as tx:
                    # Create job record
                    tx.add_operation(DatabaseOperation(
                        table="job_status",
                        operation="insert",
                        data={
                            "job_id": job_id,
                            "user_id": user_id,
                            "status": JobStatus.COMPLETED,
                            "progress": 100,
                            "message": "Results retrieved from cache",
                            "job_type": "problem_generation",
                            "created_at": datetime.utcnow().isoformat(),
                            "completed_at": datetime.utcnow().isoformat()
                        }
                    ))

                # ---- Deduct credits at the finish of the route (idempotent by request_id=job_id) ----
                # Super admins bypass credit consumption
                if not is_super_admin:
                    try:
                        credit_service.consume_feature(
                            tenant_id=tenant_id,
                            user_id=user_id,
                            feature_id=feature_id,
                            plan_type=plan_type,
                            request_id=job_id,  # idempotency key across retries
                            reason="problem_generation_cached",
                            project_id=None,
                            workflow_id=None,
                            metadata={
                            "job_id": job_id,
                            "source": "problem_generation",
                            "parameters": job_request.parameters.dict()
                        },
                    )
                    except InsufficientCreditsError:
                        # Race where another request consumed credits before deduction here
                        raise HTTPException(
                            status_code=402,
                            detail={"code": "insufficient_credits",
                                    "message": "Not enough credits to complete this request."}
                        )
                    except InvalidConsumptionRequest as e:
                        raise HTTPException(
                            status_code=400,
                            detail={"code": "invalid_consumption_request", "message": str(e)}
                        )
                
                log_auth_event(user_id, "problem_generation_cached", "job", job_id, True)
                
                return ProblemGenerationJobResponse(
                    job_id=job_id,
                    status="completed",
                    user_id=user_id,
                    created_at=datetime.utcnow(),
                    message="Results retrieved from cache"
                )
        
        # Generate unique job ID (this will also be our session ID)
        job_id = str(uuid.uuid4())
        session_id = uuid.UUID(job_id)
        
        # Validate request parameters - check for actual required fields
        validated_params = DatabaseValidator.validate_json_data(
            job_request.parameters.dict(), 
            ["industry", "geography", "background", "product_type", "target_customer", "impact_focus"]
        )
        
        # Create generation session and job status atomically - no fallbacks
        with database_transaction() as tx:
            # Create generation session
            session_data = {
                "session_id": str(session_id),
                "user_id": user_id,
                "session_name": f"Generation {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
                "parameters": validated_params,
                "status": "running",
                "created_at": datetime.utcnow().isoformat(),
                "started_at": datetime.utcnow().isoformat()
            }
            
            tx.add_operation(DatabaseOperation(
                table="problem_generation_sessions",
                operation="insert",
                data=session_data
            ))
            
            # Create job status record
            job_data = {
                "job_id": job_id,
                "user_id": user_id,
                "status": JobStatus.PROCESSING,
                "progress": 5,
                "message": "Job queued for processing",
                "job_type": "problem_generation",
                "created_at": datetime.utcnow().isoformat(),
                "started_at": datetime.utcnow().isoformat()
            }
            
            tx.add_operation(DatabaseOperation(
                table="job_status",
                operation="insert",
                data=job_data
            ))
        
        logger.info(f"Successfully created problem generation job {job_id} for user {user_id}")
        log_auth_event(user_id, "problem_generation_started", "job", job_id, True)
        
        # Start background job using simple job_status tracking
        task = asyncio.create_task(
            run_problem_generation_job(
                job_id=job_id,
                user_id=user_id,
                tenant_id=tenant_id,
                parameters=job_request.parameters
            )
        )

        # ---- Deduct credits at the finish of the route (after scheduling), idempotent on job_id ----
        # Super admins bypass credit consumption
        if not is_super_admin:
            try:
                credit_service.consume_feature(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    feature_id=feature_id,
                    plan_type=plan_type,
                    request_id=job_id,  # ensures retries don't double-charge
                    reason="problem_generation_start",
                    project_id=None,
                    workflow_id=None,
                    metadata={
                        "job_id": job_id,
                        "source": "problem_generation",
                        "parameters": job_request.parameters.dict()
                    },
                )
            except InsufficientCreditsError:
                # This can occur if another concurrent request drained the balance
                # after our pre-check but before deduction. Mark the job as failed and return 402.
                with database_transaction() as tx:
                    tx.add_operation(DatabaseOperation(
                        table="job_status",
                        operation="update",
                        data={
                            "status": JobStatus.FAILED,
                            "progress": 100,
                            "message": "Insufficient credits at deduction step",
                            "completed_at": datetime.utcnow().isoformat()
                        },
                        where={"job_id": job_id}
                    ))
                raise HTTPException(
                    status_code=402,
                    detail={"code": "insufficient_credits",
                            "message": "Not enough credits to complete this request."}
                )
            except InvalidConsumptionRequest as e:
                with database_transaction() as tx:
                    tx.add_operation(DatabaseOperation(
                        table="job_status",
                        operation="update",
                        data={
                            "status": JobStatus.FAILED,
                            "progress": 100,
                            "message": f"Credit consumption error: {str(e)}",
                            "completed_at": datetime.utcnow().isoformat()
                        },
                        where={"job_id": job_id}
                    ))
                raise HTTPException(
                    status_code=400,
                detail={"code": "invalid_consumption_request", "message": str(e)}
            )
        
        logger.info(f"Started problem generation job {job_id}")
        
        return ProblemGenerationJobResponse(
            job_id=job_id,
            status="pending",
            user_id=user_id,
            created_at=datetime.utcnow(),
            message="Problem generation job started successfully",
            problems=None,
            problems_count=0
        )
        
    except HTTPException:
        # Re-raise authentication and validation errors
        raise
    except Exception as e:
        logger.error(f"Error starting problem generation job: {str(e)}")
        # Log the failure event if we have a user_id
        if 'user_id' in locals():
            log_auth_event(user_id, "problem_generation_error", "job", None, False, str(e))
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "generation_failed",
                "message": "Failed to start problem generation job"
            }
        )

@router.get("/status/{job_id}", response_model=ProblemGenerationJobResponse)
async def get_generation_status(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get the status of a problem generation job.
    
    Returns the current status, progress, and results (if completed) of the generation job.
    """
    # Standardized user validation
    user_id = current_user["user_id"]
    
    # Validate job_id format
    job_uuid = DatabaseValidator.validate_uuid(job_id, "job_id")
    
    logger.info(f"Status check for job {job_uuid} by user {user_id}")
    log_auth_event(user_id, "job_status_check", "job", job_uuid, True)

    # Check if there are any active background tasks for this job
    if hasattr(generate_problems, '_background_tasks'):
        active_tasks = len(generate_problems._background_tasks)
        logger.info(f"Active background tasks: {active_tasks}")
        for task in generate_problems._background_tasks:
            if not task.done():
                logger.info(f"Task {task} is still running")
            else:
                logger.info(f"Task {task} is done with result: {task.result() if not task.exception() else task.exception()}")

    try:
        # Get job status from database - no fallbacks
        job_status_service = get_job_status_service()
        job_status = job_status_service.get_job_status(job_uuid, user_id)
        
        if not job_status:
            # Check if it exists as a completed session
            client = get_supabase_client(use_service_role=True)
            session_result = client.client.table("problem_generation_sessions")\
                .select("*")\
                .eq("session_id", job_uuid)\
                .eq("user_id", user_id)\
                .execute()
            
            if not session_result.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "code": "job_not_found",
                        "message": f"Job {job_uuid} not found or access denied"
                    }
                )
            
            # Convert session data to job status format
            session_data = session_result.data[0]
            job_status = {
                "job_id": job_uuid,
                "user_id": user_id,
                "status": session_data.get("status", "unknown"),
                "progress": 100 if session_data.get("status") == "completed" else 0,
                "message": f"Session {session_data.get('status', 'unknown')}",
                "created_at": session_data.get("created_at"),
                "completed_at": session_data.get("completed_at"),
                "problems_generated": session_data.get("problems_generated", 0),
                "results": session_data.get("generation_results", [])
            }
        
        # If job is completed, get results from database
        results = None
        if job_status["status"] == "completed":
            # Get results directly from problem_statements table by session_id
            db_service = get_problem_database_service()
            problems_result = execute_with_retry(
                lambda: db_service.client.client.table("problem_statements")
                .select("*")
                .eq("session_id", job_uuid)
                .eq("user_id", user_id)
                .execute()
            )
            
            if problems_result.data:
                # Convert to response objects
                from ..models.problem_models import ProblemStatementResponse
                processed_results = []
                
                for problem_data in problems_result.data:
                    try:
                        # Ensure required fields exist
                        problem_data.setdefault('validation_feedback', None)
                        problem_data.setdefault('bookmark_count', 0)
                        problem_data.setdefault('view_count', 0)
                        problem_data.setdefault('like_count', 0)
                        problem_data.setdefault('quality_score', None)
                        problem_data.setdefault('validation_status', 'pending')
                        problem_data.setdefault('generation_parameters', {})
                        problem_data.setdefault('generation_model', 'gpt-4')
                        problem_data.setdefault('supporting_sources', [])
                        
                        if 'created_at' in problem_data:
                            problem_data['generation_timestamp'] = problem_data['created_at']
                        if 'updated_at' not in problem_data:
                            problem_data['updated_at'] = problem_data.get('created_at')
                        
                        problem_response = ProblemStatementResponse(**problem_data)
                        processed_results.append(problem_response)
                        
                    except Exception as e:
                        logger.warning(f"Failed to process problem {problem_data.get('id', 'unknown')}: {e}")
                        continue
                
                results = processed_results
                logger.info(f"Retrieved {len(results)} problems for job {job_uuid}")
        
        return ProblemGenerationJobResponse(
            job_id=job_uuid,
            status=job_status["status"],
            user_id=user_id,
            created_at=datetime.fromisoformat(job_status["created_at"]) if job_status.get("created_at") else datetime.utcnow(),
            message=job_status.get("message", ""),
            problems=results if results else None,
            problems_count=len(results) if results else 0,
            processing_time_ms=job_status.get("processing_time_ms")
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions (like 404 for job not found)
        raise
    except Exception as e:
        logger.error(f"Error getting job status {job_uuid}: {str(e)}")
        log_auth_event(user_id, "job_status_error", "job", job_uuid, False, str(e))
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "status_check_failed",
                "message": "Failed to retrieve job status"
            }
        )

@router.post("/cancel/{job_id}")
async def cancel_generation_job(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Cancel a running problem generation job.
    
    Stops the background task and marks the job as cancelled.
    """
    # Standardized user validation
    user_id = current_user["user_id"]
    job_uuid = DatabaseValidator.validate_uuid(job_id, "job_id")
    
    logger = get_contextual_logger("cancel_job", f"job_{job_uuid}")
    
    try:
        # Check if job exists and belongs to user
        job_status_service = get_job_status_service()
        job_info = job_status_service.get_job_status(job_uuid, user_id)
        
        if not job_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "job_not_found",
                    "message": f"Job {job_uuid} not found or access denied"
                }
            )
        
        # Verify job can be cancelled
        if job_info.get("status") in ["completed", "failed", "cancelled"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "job_not_cancellable",
                    "message": f"Job is already {job_info.get('status')} and cannot be cancelled"
                }
            )
        
        # Update job status to cancelled
        success = job_status_service.update_job_status(
            job_id=job_uuid,
            status=JobStatus.CANCELLED,
            message="Job cancelled by user request"
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "code": "cancellation_failed",
                    "message": "Failed to cancel job"
                }
            )
        
        # Log the cancellation event
        log_auth_event(user_id, "job_cancelled", "job", job_uuid, True)
        
        return JSONResponse({
            "job_id": job_uuid,
            "status": "cancelled",
            "message": "Job cancelled successfully",
            "cancelled_at": datetime.utcnow().isoformat()
            })
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error cancelling job {job_uuid}: {str(e)}")
        log_auth_event(user_id, "job_cancel_error", "job", job_uuid, False, str(e))
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "cancellation_error",
                "message": "Failed to cancel job"
            }
        )


# =============================================
@router.get("/problems", response_model=ProblemSearchResponse)
async def search_problems(
    query: Optional[str] = Query(None, description="Search query"),
    category: Optional[str] = Query(None, description="Problem category filter"),
    severity: Optional[str] = Query(None, description="Severity level filter"),
    problem_type: Optional[str] = Query(None, description="Problem type filter"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: dict = Depends(get_current_user)
):
    """
    Search for problem statements.
    
    Supports text search, filtering by categories, and pagination.
    """
    try:
        # User ID now comes from the token via dependency
        user_id = current_user["user_id"]  # get_current_user returns the user ID directly
        
        db_service = get_problem_database_service()
        
        # Build search filters
        filters = SearchFilters()
        if category:
            try:
                from ..models.problem_models import ProblemCategory
                filters.category = ProblemCategory(category)
            except ValueError:
                valid_categories = [cat.value for cat in ProblemCategory]
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid category: {category}. Must be one of: {', '.join(valid_categories)}"
                )
        
        # Calculate offset for pagination
        offset = (page - 1) * page_size
        
        # Perform search
        if user_id:
            problems, total = db_service.list_user_problems(
                user_id=uuid.UUID(user_id),
                limit=page_size,
                offset=offset,
                filters=filters
            )
        else:
            # For public search, we would need a different method
            # For now, return empty results for unauthenticated users
            problems, total = [], 0
        
        return ProblemSearchResponse(
            problems=problems,
            total=total,
            page=page,
            page_size=page_size,
            has_next=offset + page_size < total,
            has_prev=page > 1
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching problems: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search problems"
        )

@router.get("/problems/{problem_id}", response_model=ProblemStatementResponse)
async def get_problem(
    problem_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get a specific problem statement by ID.
    
    Returns the complete problem statement with all details.
    """
    try:
        # Validate UUID format
        try:
            problem_uuid = uuid.UUID(problem_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid problem ID format"
            )
        
        # User ID now comes from the token via dependency
        user_id = current_user["user_id"]  # get_current_user returns the user ID directly
        
        db_service = get_problem_database_service()
        problem = db_service.get_problem_statement(
            problem_id=problem_uuid,
            user_id=uuid.UUID(user_id)
        )
        
        if not problem:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Problem statement not found"
            )
        
        return problem
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting problem {problem_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get problem statement"
        )

# =============================================
# ANALYTICS ENDPOINTS
# =============================================

@router.get("/analytics", response_model=AnalyticsResponse)
async def get_user_analytics(
    current_user: dict = Depends(get_current_user)
):
    """
    Get analytics summary for the authenticated user.
    
    Returns generation statistics, success rates, and usage patterns.
    """
    try:
        # Get user ID from current_user
        user_id = current_user["user_id"]  # get_current_user returns the user ID directly
        user_uuid = uuid.UUID(user_id)

        logger.info(f"Analytics request for user {user_id}")
        
        db_service = ProblemDatabaseService(use_service_role=True)
        
        # Get analytics summary from database
        analytics_data = db_service.get_analytics_summary(user_id=user_uuid)
        
        return {
            "user_id": user_id,
            "total_problems_generated": analytics_data.get("total_problems_generated", 0),
            "total_sessions": analytics_data.get("total_sessions", 0),
            "success_rate": analytics_data.get("success_rate", 0.0),
            "average_generation_time_ms": analytics_data.get("average_generation_time_ms", 0.0),
            "average_satisfaction_rating": analytics_data.get("average_satisfaction_rating", 0.0)
        }
        
    except Exception as e:
        logger.error(f"Error getting analytics for user {user_id}: {str(e)}")
        # Return default analytics on error
        return {
            "user_id": user_id,
            "total_problems_generated": 0,
            "total_sessions": 0,
            "success_rate": 0.0,
            "average_generation_time_ms": 0.0,
            "average_satisfaction_rating": 0.0
        }

# =============================================
# INTERACTION ENDPOINTS (BOOKMARKS, LIKES)
# =============================================

@router.post("/problems/{problem_id}/bookmark")
async def bookmark_problem(
    problem_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Bookmark a problem statement.
    """
    try:
        # Validate problem_id and user_id
        problem_uuid = uuid.UUID(problem_id)
        user_id = current_user["user_id"]  # get_current_user returns the user ID directly
        user_uuid = uuid.UUID(user_id)
        
        logger.info(f"Bookmark request - user_id: {user_id}, problem_id: {problem_id}")
        
        db_service = ProblemDatabaseService(use_service_role=True)
        
        # Check if bookmark already exists
        existing_bookmark = db_service.get_bookmark(
            user_id=user_uuid,
            problem_id=problem_uuid
        )
        
        if existing_bookmark:
            return {"message": "Problem already bookmarked", "bookmark_id": str(existing_bookmark["id"])}
        
        # Create new bookmark
        bookmark = db_service.create_bookmark(
            user_id=user_uuid,
            problem_id=problem_uuid
        )
        
        if not bookmark:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create bookmark"
            )
        
        return {"message": "Problem bookmarked successfully", "bookmark_id": str(bookmark["id"])}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error bookmarking problem {problem_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to bookmark problem"
        )

@router.post("/problems/{problem_id}/like")
async def like_problem(
    problem_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Like a problem statement.
    """
    try:
        # Validate problem_id and user_id
        problem_uuid = uuid.UUID(problem_id)
        user_id = current_user["user_id"]  # get_current_user returns the user ID directly
        user_uuid = uuid.UUID(user_id)
        
        logger.info(f"Like request - user_id: {user_id}, problem_id: {problem_id}")
        
        db_service = ProblemDatabaseService(use_service_role=True)
        
        # Check if like already exists
        existing_like = db_service.get_like(
            user_id=user_uuid,
            problem_id=problem_uuid
        )
        
        if existing_like:
            return {"message": "Problem already liked", "like_id": str(existing_like["id"])}
        
        # Create new like
        like = db_service.create_like(
            user_id=user_uuid,
            problem_id=problem_uuid
        )
        
        if not like:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to like problem"
            )
        
        return {"message": "Problem liked successfully", "like_id": str(like["id"])}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error liking problem {problem_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to like problem"
        )

# =============================================
# BACKGROUND TASK FUNCTIONS
# =============================================

async def run_robust_problem_generation_job(
    job_id: str,
    user_id: str,
    parameters: ProblemGenerationRequest
):
    """
    Robust background task for running problem generation with enhanced error handling.
    
    Uses the robust problem generator with comprehensive timeout management,
    retry logic, and fallback mechanisms.
    """
    # Create contextual logger
    ctx_logger = get_contextual_logger("pgen.api.robust_generation", job_id=job_id, user_id=user_id)
    start_time = time()
    
    try:
        ctx_logger.info(f"Starting robust problem generation job {job_id} for user {user_id}")
        
        # Get job status service for database tracking
        job_status_service = get_job_status_service()
        
        # Update status to processing
        job_status_service.update_job_status(
            job_id=job_id,
            status=JobStatus.PROCESSING,
            progress=10,
            message="Robust generation system initialized"
        )
        
        # Use the same direct approach as the working test endpoint
        from ..agents.problem_generator_graph import ProblemGeneratorGraph
        
        # Convert parameters to dict format (same as test endpoint)
        user_params = {
            "industry": parameters.industry,
            "geography": parameters.geography,
            "background": parameters.background,
            "product_type": parameters.product_type,
            "target_customer": parameters.target_customer or [],
            "impact_focus": parameters.impact_focus or [],
            "num_problems": parameters.num_problems,
            "creativity_level": parameters.creativity_level,
            "custom_constraints": parameters.custom_constraints
        }
        
        # Update progress
        job_status_service.update_job_status(
            job_id=job_id,
            progress=20,
            message="Running 12-node AI workflow"
        )
        
        # Initialize the Problem Generator graph (same as test endpoint)
        graph = ProblemGeneratorGraph()
        
        # Create initial state for the workflow (same as test endpoint)
        initial_state = {
            "params": user_params,
            "user_id": user_id,
            "job_id": job_id
        }
        
        # Run the complete 12-node workflow (same as test endpoint)
        result_state = await graph.graph.ainvoke(initial_state)
        
        # Extract results from the workflow (same as test endpoint)
        final_problems = result_state.get("final", [])
        
        # Debug logging to see what we got from the workflow
        ctx_logger.info(f"Workflow completed for job {job_id}")
        ctx_logger.info(f"Generated {len(final_problems)} problems")
        if final_problems:
            ctx_logger.info(f"First problem keys: {list(final_problems[0].keys())}")
            ctx_logger.info(f"First problem statement field: {final_problems[0].get('statement', 'NOT FOUND')}")
            ctx_logger.info(f"First problem title field: {final_problems[0].get('title', 'NOT FOUND')}")
            ctx_logger.info(f"First problem description field: {final_problems[0].get('description', 'NOT FOUND')}")
        if final_problems:
            ctx_logger.info(f"First problem: {final_problems[0]}")
        
        # Update progress
        job_status_service.update_job_status(
            job_id=job_id,
            progress=80,
            message=f"Processing {len(final_problems)} generated problems"
        )
        
        # Save problems to database if any were generated (same as test endpoint)
        saved_problems = []
        if final_problems:
            from ..services.problem_database_service import ProblemDatabaseService
            db_service = ProblemDatabaseService(use_service_role=True)
            
            for problem in final_problems:
                try:
                    # Convert to database format with proper validation
                    from ..models.problem_models import ProblemStatementCreate
                    
                    # Clean and validate the data
                    # The curator creates two fields:
                    # - "problem_statement": Concise one-sentence version (for title)
                    # - "statement": Detailed explanation (for description)
                    
                    concise_statement = problem.get("problem_statement", "").strip()
                    detailed_statement = problem.get("detailed_explanation", "").strip()
                    
                    ctx_logger.info(f"DEBUG: Raw problem_statement field: '{problem.get('problem_statement', 'FIELD_NOT_FOUND')}'")
                    ctx_logger.info(f"DEBUG: Raw detailed_explanation field: '{problem.get('detailed_explanation', 'FIELD_NOT_FOUND')[:100]}...'")
                    ctx_logger.info(f"Concise statement found: '{concise_statement}' (length: {len(concise_statement)})")
                    ctx_logger.info(f"Detailed statement found: '{detailed_statement[:100]}...' (length: {len(detailed_statement)})")
                    ctx_logger.info(f"DEBUG: Will concise_statement evaluate to True? {bool(concise_statement)}")
                    ctx_logger.info(f"DEBUG: Will detailed_statement evaluate to True? {bool(detailed_statement)}")
                    
                    # STRICT MODE: Only use concise statement for title, no fallbacks
                    if not concise_statement:
                        available_fields = list(problem.keys())
                        raise ValueError(f"MISSING CONCISE STATEMENT: 'problem_statement' field is empty or missing. Available fields: {available_fields}. Raw problem_statement: '{problem.get('problem_statement', 'FIELD_NOT_FOUND')}'")
                    
                    if not detailed_statement:
                        available_fields = list(problem.keys())
                        raise ValueError(f"MISSING DETAILED STATEMENT: 'detailed_explanation' field is empty or missing. Available fields: {available_fields}. Raw detailed_explanation: '{problem.get('detailed_explanation', 'FIELD_NOT_FOUND')}'")
                    
                    # Use ONLY the concise and detailed statements - no fallbacks
                    title = concise_statement
                    description = detailed_statement
                    
                    ctx_logger.info(f"SUCCESS: Using concise statement as title. Title: '{title}' (length: {len(title)})")
                    ctx_logger.info(f"SUCCESS: Using detailed statement as description (length: {len(description)})")
                    
                    # Map category to valid enum values
                    category = problem.get("category", "other").lower()
                    valid_categories = ["technology", "healthcare", "education", "finance", "environment", "social", "business", "other"]
                    if category not in valid_categories:
                        category = "other"
                    
                    # Map problem_type to valid enum values
                    problem_type = problem.get("problem_type", "operational").lower()
                    valid_problem_types = ["operational", "strategic", "technical", "social", "environmental", "regulatory"]
                    if problem_type not in valid_problem_types:
                        problem_type = "social"  # Default for most problems
                    
                    # Ensure impact_focus is a list
                    impact_focus = problem.get("impact_focus", [])
                    if isinstance(impact_focus, str):
                        impact_focus = [impact_focus] if impact_focus.strip() else []
                    
                    # Final validation - no empty titles or descriptions allowed
                    if not title or not description:
                        raise ValueError(f"Empty title or description after processing. Title: '{title}', Description: '{description}', Original problem: {problem}")
                    
                    problem_create = ProblemStatementCreate(
                        title=title,
                        description=description,
                        category=category,
                        severity_level=problem.get("severity_level", "medium"),
                        problem_type=problem_type,
                        time_horizon=problem.get("time_horizon", "medium_term"),
                        complexity_level=problem.get("complexity_level", "moderate"),
                        target_geography=problem.get("target_geography", []),
                        impact_focus=impact_focus,
                        root_causes=problem.get("root_causes", []),
                        potential_effects=problem.get("potential_effects", []),
                        stakeholders=problem.get("stakeholders", []),
                        success_metrics=problem.get("success_metrics", []),
                        session_id=job_id  # Link to the generation session
                    )
                    
                    ctx_logger.info(f"Saving problem to database: {problem_create.title}")
                    
                    saved_problem = db_service.create_problem_statement(
                        user_id=uuid.UUID(user_id),
                        problem_data=problem_create
                    )
                    
                    if saved_problem:
                        saved_problems.append(saved_problem)
                        ctx_logger.info(f"Successfully saved problem: {saved_problem.id if hasattr(saved_problem, 'id') else 'unknown'}")
                    else:
                        ctx_logger.error("Failed to save problem - no result returned from database")
                        
                except Exception as e:
                    ctx_logger.error(f"Failed to save problem to database: {e}")
                    import traceback
                    ctx_logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Create result object
        result = {
            "status": "completed",
            "problems_generated": len(final_problems),
            "problems_saved": len(saved_problems),
            "problems": final_problems
        }
        
        # Check result status
        if result.get("status") == "completed":
            # Update to completed
            job_status_service.update_job_status(
                job_id=job_id,
                status=JobStatus.COMPLETED,
                progress=100,
                message=f"Successfully generated {result.get('problems_generated', 0)} problems"
            )
            ctx_logger.info(f"Robust generation completed successfully for job {job_id}")
        else:
            # Update to failed
            job_status_service.update_job_status(
                job_id=job_id,
                status=JobStatus.FAILED,
                progress=0,
                message=f"Generation failed: {result.get('error', 'Unknown error')}"
            )
            ctx_logger.error(f"Robust generation failed for job {job_id}: {result.get('error')}")
        
    except Exception as e:
        ctx_logger.error(f"Robust generation job {job_id} failed with exception: {str(e)}")
        
        # Update job status to failed
        try:
            job_status_service = get_job_status_service()
            job_status_service.update_job_status(
                job_id=job_id,
                status=JobStatus.FAILED,
                progress=0,
                message=f"Job failed with exception: {str(e)}"
            )
        except Exception as status_error:
            ctx_logger.error(f"Failed to update job status: {str(status_error)}")


async def run_problem_generation_job(
    job_id: str,
    user_id: str,
    tenant_id: str,
    parameters: ProblemGenerationRequest
):
    """
    Background task for running problem generation.
    
    Executes the complete LangGraph workflow and stores results.
    """
    # Create contextual logger
    ctx_logger = get_contextual_logger("pgen.api.generation", job_id=job_id, user_id=user_id)
    start_time = time()
    
    try:
        ctx_logger.info(f"Starting problem generation job {job_id} for user {user_id}")
        
        # Get job status service for database tracking
        job_status_service = get_job_status_service()
        
        # Helper function to check if job was cancelled
        def check_cancellation():
            job_status = job_status_service.get_job_status(job_id, user_id)
            if job_status and job_status.get("status") == "cancelled":
                ctx_logger.info(f"Job {job_id} was cancelled, stopping execution")
                return True
            return False
        
        # Immediate progress update to show task is running
        job_status_service.update_job_status(
            job_id=job_id,
            status=JobStatus.PROCESSING,
            progress=10,
            message="Background task started - importing modules"
        )
        
        # Check for cancellation before proceeding
        if check_cancellation():
            return
        
        # Import the LangGraph workflow with error handling
        try:
            from ..agents.problem_generator_graph import create_problem_generator_graph
            from ..services.problem_database_service import ProblemDatabaseService
            
            # Update progress after successful imports
            job_status_service.update_job_status(
                job_id=job_id,
                progress=15,
                message="Modules imported - initializing workflow"
            )
            
            # Check for cancellation after imports
            if check_cancellation():
                return
                
        except ImportError as import_error:
            raise Exception(f"Failed to import required modules: {str(import_error)}")
        
        # Create the problem generator graph with error handling
        try:
            graph = create_problem_generator_graph()
            
            # Update progress after successful graph creation
            job_status_service.update_job_status(
                job_id=job_id,
                progress=20,
                message="Workflow graph created - preparing execution"
            )
            
            # Check for cancellation before workflow execution
            if check_cancellation():
                return
                
        except Exception as graph_error:
            raise Exception(f"Failed to create workflow graph: {str(graph_error)}")
        
        # Convert ProblemGenerationRequest to dict format expected by the graph
        # Optimized to use only 6 core parameters for improved performance
        user_params = {
            "industry": parameters.industry,
            "geography": parameters.geography,
            "background": parameters.background,
            "product_type": parameters.product_type,
            "target_customer": parameters.target_customer or [],
            "impact_focus": parameters.impact_focus or [],
            "user_id": user_id,
            "tenant_id": tenant_id,  # For AI usage monitoring
            "job_id": job_id,
            "num_problems": parameters.num_problems,
            "creativity_level": parameters.creativity_level,
            "custom_constraints": parameters.custom_constraints
        }
        
        # Update progress
        job_status_service.update_job_status(
            job_id=job_id,
            progress=30,
            message="Executing problem generation workflow"
        )
        
        # Final cancellation check before expensive workflow execution
        if check_cancellation():
            return
        
        ctx_logger.info(f"Executing LangGraph workflow for job {job_id}")
        
        # Execute the workflow
        result = await graph.generate_problems(user_params)
        
        # Check for cancellation after workflow execution
        if check_cancellation():
            return
        
        # Update progress after workflow completion
        job_status_service.update_job_status(
            job_id=job_id,
            progress=70,
            message="Processing and storing results"
        )
        
        # Check if workflow completed successfully
        if result.get("status") == "failed":
            raise Exception(f"Workflow failed: {result.get('error', 'Unknown error')}")
        
        # Get the final problem statements
        final_problems = result.get("final", [])
        
        if not final_problems:
            ctx_logger.warning(f"No problem statements generated for job {job_id}")
        
        # Check for cancellation before database storage
        if check_cancellation():
            return
        
        # Store results in database
        db_service = ProblemDatabaseService(use_service_role=True)
        
        # Verify session exists before creating problems
        session_check = db_service.client.client.table("problem_generation_sessions").select("session_id").eq("session_id", job_id).execute()
        if not session_check.data:
            ctx_logger.error(f"Session {job_id} not found in database when trying to save problems!")
            # Try to create the session again as fallback
            session_data = db_service.create_generation_session(
                user_id=uuid.UUID(user_id),
                session_id=uuid.UUID(job_id),
                parameters=user_params,
                session_name=f"Generation {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
            )
            if not session_data:
                ctx_logger.error(f"Failed to create fallback session {job_id}")
                job_status_service.mark_job_failed(
                    job_id=job_id,
                    error_message="Failed to create session in database"
                )
                return
        else:
            ctx_logger.info(f"Session {job_id} verified in database")
        
        stored_problems = []
        for problem_data in final_problems:
            # Check for cancellation during database operations
            if check_cancellation():
                return
            try:
                # Convert problem statement to database format
                statement_text = problem_data.get("statement", "") if isinstance(problem_data, dict) else str(problem_data)
                
                from ..models.problem_models import ProblemStatementCreate, ProblemCategory, SeverityLevel, ProblemType, TimeHorizon, ComplexityLevel
                
                # Extract the concise statement and detailed explanation
                # Use the properly generated concise problem_statement from curator, not the raw detailed statement
                if isinstance(problem_data, dict):
                    # First try to get the concise problem_statement generated by curator
                    problem_statement = problem_data.get("problem_statement", "")
                    
                    # If no concise statement available, fallback to truncated raw statement
                    if not problem_statement:
                        raw_statement = problem_data.get("statement", statement_text)
                        problem_statement = raw_statement[:350] if len(raw_statement) > 350 else raw_statement
                    
                    detailed_explanation = problem_data.get("detailed_explanation", statement_text)
                else:
                    # Fallback for non-dict data
                    problem_statement = statement_text[:350] if len(statement_text) > 350 else statement_text
                    detailed_explanation = statement_text
                
                # Extract supporting sources
                supporting_sources = []
                
                # Debug: Log the entire problem_data structure
                ctx_logger.info(f"Processing problem_data keys: {list(problem_data.keys()) if isinstance(problem_data, dict) else 'NOT_DICT'}")
                
                if isinstance(problem_data, dict) and "supporting_sources" in problem_data:
                    supporting_sources = problem_data.get("supporting_sources", [])
                    ctx_logger.info(f"Found supporting_sources in problem_data: {len(supporting_sources)} sources")
                    for i, src in enumerate(supporting_sources):
                        ctx_logger.info(f"Source {i}: {src}")
                else:
                    ctx_logger.warning(f"No supporting_sources found in problem_data. Available keys: {list(problem_data.keys()) if isinstance(problem_data, dict) else 'NOT_DICT'}")
                    
                # Also check if sources are in a different field name
                if isinstance(problem_data, dict):
                    for key in ['sources', 'source_list', 'references']:
                        if key in problem_data:
                            ctx_logger.info(f"Found alternative sources field '{key}': {problem_data[key]}")
                            if not supporting_sources:  # Use as fallback if supporting_sources is empty
                                supporting_sources = problem_data[key]
                
                # Create the problem statement with the new structure
                problem_create = ProblemStatementCreate(
                    # Core information
                    title=problem_statement,  # Concise statement
                    description=detailed_explanation,  # Detailed explanation
                    
                    # Contextual information
                    category=ProblemCategory.BUSINESS,  # Default, can be customized based on problem_data
                    target_geography=user_params.get("geography", []),
                    impact_focus=user_params.get("impact_focus", []),
                    
                    # Problem characteristics
                    severity_level=SeverityLevel.MEDIUM,
                    problem_type=ProblemType.OPERATIONAL,
                    time_horizon=TimeHorizon.SHORT_TERM,
                    complexity_level=ComplexityLevel.MODERATE,
                    affected_population_size=None,
                    
                    # Detailed analysis sections
                    root_causes=problem_data.get("root_causes", []) if isinstance(problem_data, dict) else [],
                    potential_effects=problem_data.get("potential_effects", []) if isinstance(problem_data, dict) else [],
                    stakeholders=problem_data.get("stakeholders", []) if isinstance(problem_data, dict) else [],
                    success_metrics=problem_data.get("success_metrics", []) if isinstance(problem_data, dict) else [],
                    
                    # Source information
                    supporting_sources=supporting_sources,
                    
                    # Generation metadata
                    generation_parameters=user_params,
                    generation_model="gpt-4o",
                    quality_score=problem_data.get("relevance_score", 0.7) if isinstance(problem_data, dict) else 0.7,
                    session_id=uuid.UUID(job_id)
                )
                
                # Store in database
                ctx_logger.info(f"Attempting to create problem statement {len(stored_problems) + 1} for session {job_id}")
                stored_problem = db_service.create_problem_statement(
                    user_id=uuid.UUID(user_id),
                    problem_data=problem_create
                )
                
                if stored_problem:
                    ctx_logger.info(f"Successfully created problem statement {stored_problem.id} for session {job_id}")
                    stored_problems.append(stored_problem)
                    
                    # Create generation result linking problem to session
                    try:
                        ctx_logger.info(f"Creating generation result for session {job_id}, problem {stored_problem.id}, rank {len(stored_problems)}")
                        result_record = db_service.create_generation_result(
                            session_id=uuid.UUID(job_id),
                            problem_statement_id=uuid.UUID(str(stored_problem.id)),
                            rank=len(stored_problems),  # Use current position as rank
                            quality_score=problem_data.get("relevance_score", 0.7) if isinstance(problem_data, dict) else 0.7,
                            selected=False  # Default to not selected
                        )
                        
                        if result_record:
                            ctx_logger.info(f"Successfully created generation result {result_record.get('result_id')} for problem {stored_problem.id}")
                        else:
                            ctx_logger.error(f"Failed to create generation result for problem {stored_problem.id} - no data returned")
                            
                    except Exception as result_error:
                        ctx_logger.error(f"Failed to create generation result for problem {stored_problem.id}: {str(result_error)}")
                        # Continue processing other problems even if one fails
                else:
                    ctx_logger.error(f"Failed to create problem statement {len(stored_problems) + 1} - no data returned")
                    continue
                    
            except Exception as e:
                ctx_logger.error(f"Failed to store problem statement: {str(e)}")
                continue
        
        # Store analytics
        try:
            from ..models.problem_models import GenerationAnalyticsCreate
            import json
            
            # Convert user_params to JSON-serializable format
            serializable_params = {}
            for key, value in user_params.items():
                if isinstance(value, uuid.UUID):
                    serializable_params[key] = str(value)
                elif isinstance(value, (list, dict, str, int, float, bool)) or value is None:
                    serializable_params[key] = value
                else:
                    serializable_params[key] = str(value)
            
            analytics_data = GenerationAnalyticsCreate(
                session_id=uuid.UUID(job_id),
                input_parameters=serializable_params,
                problems_generated=len(stored_problems),
                generation_success=len(stored_problems) > 0,
                generation_time_ms=result.get("total_processing_time_ms", 0),
                model_used="gpt-4o",
                average_quality_score=sum(p.quality_score or 0 for p in stored_problems) / len(stored_problems) if stored_problems else 0,
                user_satisfaction_rating=None
            )
            
            db_service.create_generation_analytics(
                user_id=uuid.UUID(user_id),
                analytics_data=analytics_data
            )
            
        except Exception as e:
            ctx_logger.error(f"Failed to store analytics for job {job_id}: {str(e)}")
        
        # Cache successful results for future requests (if enabled)
        if PERFORMANCE_ENABLED and stored_problems:
            try:
                cache_manager = get_cache_manager()
                problem_dicts = [p.dict() for p in stored_problems]
                cache_key = cache_manager.cache_problem_results(
                    parameters.dict(), 
                    problem_dicts
                )
                ctx_logger.info(f"Cached results with key: {cache_key}")
            except Exception as e:
                ctx_logger.warning(f"Failed to cache results: {str(e)}")
        
        # Prepare results for frontend with restructured format
        results = []
        for problem in stored_problems:
            # Extract source information with comprehensive handling
            sources = []
            
            # Debug: Log the supporting_sources field
            ctx_logger.info(f"Problem {problem.id} supporting_sources type: {type(getattr(problem, 'supporting_sources', None))}")
            ctx_logger.info(f"Problem {problem.id} supporting_sources value: {getattr(problem, 'supporting_sources', 'NOT_FOUND')}")
            
            # Get supporting_sources from the problem object
            supporting_sources_data = getattr(problem, 'supporting_sources', None)
            
            if supporting_sources_data:
                ctx_logger.info(f"Found supporting_sources data: {len(supporting_sources_data) if isinstance(supporting_sources_data, (list, tuple)) else 'not_list'}")
                
                # Handle different data types for supporting_sources
                if isinstance(supporting_sources_data, (list, tuple)):
                    for i, source in enumerate(supporting_sources_data):
                        ctx_logger.info(f"Processing source {i}: {source} (type: {type(source)})")
                        
                        # Handle dict sources (most common case)
                        if isinstance(source, dict):
                            source_obj = {
                                "citation_number": source.get("citation_number", i + 1),
                                "source_uuid": source.get("source_uuid", ""),
                                "url": source.get("url", ""),
                                "title": source.get("title", ""),
                                "domain": source.get("domain", ""),
                                "publication_date": source.get("publication_date", ""),
                                "author": source.get("author", ""),
                                "credibility_score": source.get("credibility_score", 5.0),
                                "content_type": source.get("content_type", "article")
                            }
                            sources.append(source_obj)
                            ctx_logger.info(f"Added source {i}: {source_obj['title'][:50]}...")
                            
                        # Handle object sources (if any)
                        elif hasattr(source, '__dict__'):
                            source_obj = {
                                "citation_number": getattr(source, 'citation_number', i + 1),
                                "source_uuid": getattr(source, 'source_uuid', ''),
                                "url": getattr(source, 'url', ''),
                                "title": getattr(source, 'title', ''),
                                "domain": getattr(source, 'domain', ''),
                                "publication_date": getattr(source, 'publication_date', ''),
                                "author": getattr(source, 'author', ''),
                                "credibility_score": getattr(source, 'credibility_score', 5.0),
                                "content_type": getattr(source, 'content_type', 'article')
                            }
                            sources.append(source_obj)
                            ctx_logger.info(f"Added object source {i}: {source_obj['title'][:50]}...")
                            
                        # Handle string sources (fallback)
                        elif isinstance(source, str):
                            try:
                                import json
                                source_dict = json.loads(source)
                                source_obj = {
                                    "citation_number": source_dict.get("citation_number", i + 1),
                                    "source_uuid": source_dict.get("source_uuid", ""),
                                    "url": source_dict.get("url", ""),
                                    "title": source_dict.get("title", ""),
                                    "domain": source_dict.get("domain", ""),
                                    "publication_date": source_dict.get("publication_date", ""),
                                    "author": source_dict.get("author", ""),
                                    "credibility_score": source_dict.get("credibility_score", 5.0),
                                    "content_type": source_dict.get("content_type", "article")
                                }
                                sources.append(source_obj)
                                ctx_logger.info(f"Added JSON string source {i}: {source_obj['title'][:50]}...")
                            except (json.JSONDecodeError, AttributeError):
                                ctx_logger.warning(f"Could not parse string source {i}: {source}")
                        else:
                            ctx_logger.warning(f"Unknown source type {i}: {type(source)} - {source}")
                            
                elif isinstance(supporting_sources_data, str):
                    # Handle case where supporting_sources is a JSON string
                    try:
                        import json
                        sources_list = json.loads(supporting_sources_data)
                        if isinstance(sources_list, list):
                            for i, source in enumerate(sources_list):
                                if isinstance(source, dict):
                                    source_obj = {
                                        "citation_number": source.get("citation_number", i + 1),
                                        "source_uuid": source.get("source_uuid", ""),
                                        "url": source.get("url", ""),
                                        "title": source.get("title", ""),
                                        "domain": source.get("domain", ""),
                                        "publication_date": source.get("publication_date", ""),
                                        "author": source.get("author", ""),
                                        "credibility_score": source.get("credibility_score", 5.0),
                                        "content_type": source.get("content_type", "article")
                                    }
                                    sources.append(source_obj)
                    except json.JSONDecodeError:
                        ctx_logger.warning(f"Could not parse supporting_sources JSON string: {supporting_sources_data}")
                        
            else:
                ctx_logger.warning(f"No supporting_sources found for problem {problem.id}")
                
                # Fallback: Try to get sources from the original problem_data if available
                # This handles cases where sources might be in the workflow result but not stored properly
                for problem_data in final_problems:
                    if isinstance(problem_data, dict) and problem_data.get("problem_statement") == problem.title:
                        fallback_sources = problem_data.get("supporting_sources", [])
                        if fallback_sources:
                            ctx_logger.info(f"Found fallback sources for problem {problem.id}: {len(fallback_sources)}")
                            for i, source in enumerate(fallback_sources):
                                if isinstance(source, dict):
                                    source_obj = {
                                        "citation_number": source.get("citation_number", i + 1),
                                        "source_uuid": source.get("source_uuid", ""),
                                        "url": source.get("url", ""),
                                        "title": source.get("title", ""),
                                        "domain": source.get("domain", ""),
                                        "publication_date": source.get("publication_date", ""),
                                        "author": source.get("author", ""),
                                        "credibility_score": source.get("credibility_score", 5.0),
                                        "content_type": source.get("content_type", "article")
                                    }
                                    sources.append(source_obj)
                        break
            
            # Structure the response according to requirements
            results.append({
                # Core information
                "id": str(problem.id),
                "problem_statement": problem.title,  # Concise statement
                "explanation": problem.description,   # Detailed explanation
                
                # Contextual information
                "industry": problem.category.value if hasattr(problem.category, 'value') else str(problem.category),
                "geography": problem.target_geography,
                "target_demographics": problem.impact_focus,
                
                # Detailed analysis sections
                "root_causes": problem.root_causes,
                "effects": problem.potential_effects,
                "stakeholders": problem.stakeholders,
                "metrics": problem.success_metrics,
                
                # Source information (fixed)
                "sources": sources,
                "supporting_sources": sources,  # Provide both field names for compatibility
                
                # Debug: Log the sources being sent to frontend
                "_debug_sources_count": len(sources),
                
                # Additional metadata
                "severity": problem.severity_level.value if hasattr(problem.severity_level, 'value') else str(problem.severity_level),
                "quality_score": problem.quality_score,
                "created_at": problem.created_at.isoformat() if problem.created_at else None
            })
        
        # Credit system removed - no credit deduction needed
        ctx_logger.info(f"Problem generation completed for user {user_id}, job {job_id} (credit system disabled)")
        
        # Update generation session with completion status
        try:
            session_updates = {
                "status": "completed",
                "problems_generated": len(stored_problems),
                "problems_selected": 0,  # Will be updated when user selects problems
                "completed_at": datetime.utcnow().isoformat()
            }
            
            updated_session = db_service.update_generation_session(
                session_id=uuid.UUID(job_id),
                user_id=uuid.UUID(user_id),
                updates=session_updates
            )
            
            if updated_session:
                ctx_logger.info(f"Successfully updated generation session {job_id} to completed status")
            else:
                ctx_logger.error(f"Failed to update generation session {job_id} - session not found in database")
                
        except Exception as session_error:
            ctx_logger.error(f"Failed to update failed generation session: {str(session_error)}")
        
        # Mark job as completed atomically - only after results are saved
        completion_success = job_status_service.mark_job_completed_with_results(
            job_id=job_id,
            results_count=len(stored_problems)
        )
        
        if not completion_success:
            ctx_logger.error(f"Failed to mark job {job_id} as completed - atomic verification failed")
            # Keep job in processing state rather than marking as failed
            job_status_service.update_job_status(
                job_id=job_id,
                progress=95,
                message=f"Generated {len(stored_problems)} problems, finalizing completion..."
            )
        else:
            ctx_logger.info(f"Successfully marked job {job_id} as completed with {len(stored_problems)} results")
        
        # Calculate total time
        total_time_ms = int((time() - start_time) * 1000)
        
        # Log performance metrics
        performance_logger.log_generation_metrics(
            job_id=job_id,
            user_id=user_id,
            total_time_ms=total_time_ms,
            problems_generated=len(stored_problems),
            parameters=parameters.dict(),
            success=True
        )
        
        ctx_logger.info(f"Problem generation job {job_id} completed successfully")
        ctx_logger.info(f"Generated and stored {len(stored_problems)} problem statements in {total_time_ms}ms")
        
    except Exception as e:
        # Calculate total time for failed job
        total_time_ms = int((time() - start_time) * 1000)
        
        # Log error performance metrics
        performance_logger.log_generation_metrics(
            job_id=job_id,
            user_id=user_id,
            total_time_ms=total_time_ms,
            problems_generated=0,
            parameters=parameters.dict(),
            success=False,
            error=str(e)
        )
        
        ctx_logger.error(f"Problem generation job {job_id} failed: {str(e)}")
        
        # Update generation session with failure status
        try:
            session_updates = {
                "status": "failed",
                "problems_generated": 0,
                "error_message": str(e),
                "completed_at": datetime.utcnow().isoformat()
            }
            
            db_service = ProblemDatabaseService(use_service_role=True)
            db_service.update_generation_session(
                session_id=uuid.UUID(job_id),
                user_id=uuid.UUID(user_id),
                updates=session_updates
            )
        except Exception as session_error:
            ctx_logger.error(f"Failed to update failed generation session: {str(session_error)}")
        
        # Mark job as failed in database
        job_status_service.mark_job_failed(
            job_id=job_id,
            error_message=str(e)
        )
        
        # Store failed analytics
        try:
            db_service = ProblemDatabaseService(use_service_role=True)
            analytics_data = GenerationAnalyticsCreate(
                session_id=uuid.UUID(job_id),
                input_parameters=parameters.dict(),
                problems_generated=0,
                generation_success=False,
                error_occurred=True,
                model_used="gpt-4o",
                user_satisfaction_rating=None,
                generation_time_ms=None,
                average_quality_score=None
            )
            
            db_service.create_generation_analytics(
                user_id=uuid.UUID(user_id),
                analytics_data=analytics_data
            )
            
        except Exception as analytics_error:
            ctx_logger.error(f"Failed to store error analytics: {str(analytics_error)}")
        
        # TODO: Update job status to failed
        raise
        # TODO: Store error details


# =============================================
# GENERATION HISTORY ENDPOINTS
# =============================================

class GenerationSessionResponse(BaseModel):
    """Response model for generation session data."""
    session_id: str
    user_id: str
    session_name: Optional[str] = None
    session_description: Optional[str] = None
    parameters: Dict[str, Any]
    status: str
    problems_generated: Optional[int] = None
    problems_selected: Optional[int] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    results: Optional[List[Dict[str, Any]]] = None

class GenerationHistoryResponse(BaseModel):
    """Response model for generation history listing."""
    sessions: List[GenerationSessionResponse]
    total_count: int
    page: int
    page_size: int
    has_more: bool

class CreateFavoriteRequest(BaseModel):
    """Request model for creating user favorites."""
    favorite_type: str = Field(..., pattern="^(session|problem|result)$")
    target_id: str
    notes: Optional[str] = None
    tags: Optional[List[str]] = None

class FavoriteResponse(BaseModel):
    """Response model for user favorites."""
    id: str
    user_id: str
    favorite_type: str
    session_id: Optional[str] = None
    problem_statement_id: Optional[str] = None
    result_id: Optional[str] = None
    notes: Optional[str] = None
    tags: List[str] = []
    saved_at: datetime

@router.get("/history", response_model=GenerationHistoryResponse)
async def get_generation_history(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: Optional[str] = Query("completed", description="Filter by status (default: completed)"),
    include_running: bool = Query(False, description="Include running sessions in results"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get user's problem generation history.
    
    Returns paginated list of generation sessions with metadata.
    By default, only returns completed sessions. Set include_running=True to include running sessions.
    """
    try:
        # User ID now comes from the token via dependency
        user_id = current_user["user_id"]  # get_current_user returns the user ID directly
        
        db_service = ProblemDatabaseService(use_service_role=True)
        
        # Default to completed sessions only, unless explicitly requesting all or running
        effective_status_filter = status_filter
        if include_running:
            effective_status_filter = None  # No filter - include all statuses
        
        offset = (page - 1) * page_size
        sessions, total_count = db_service.get_user_generation_history(
            user_id=uuid.UUID(user_id),
            limit=page_size,
            offset=offset,
            status_filter=effective_status_filter
        )
        
        # Convert sessions to response format
        session_responses = []
        for session in sessions:
            session_responses.append(GenerationSessionResponse(
                session_id=session["session_id"],
                user_id=session["user_id"],
                session_name=session.get("session_name"),
                session_description=session.get("session_description"),
                parameters=session["parameters"],
                status=session["status"],
                problems_generated=session.get("problems_generated"),
                problems_selected=session.get("problems_selected"),
                created_at=session["created_at"],
                completed_at=session.get("completed_at")
            ))
        
        has_more = offset + len(sessions) < total_count
        
        return GenerationHistoryResponse(
            sessions=session_responses,
            total_count=total_count,
            page=page,
            page_size=page_size,
            has_more=has_more
        )
        
    except Exception as e:
        logger.error(f"Error getting generation history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve generation history: {str(e)}"
        )

@router.get("/history/search")
async def search_problems_by_description(
    parameters: str = Query(..., description="Search query to match against problem descriptions"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results"),
    current_user: dict = Depends(get_current_user)
):
    """
    Search user's problem statements by description content.
    
    Finds problems with descriptions that contain the search query.
    """
    try:
        # User ID now comes from the token via dependency
        user_id = current_user["user_id"]  # get_current_user returns the user ID directly
        logger.info(f"Search request - user_id: {user_id}, type: {type(user_id)}, parameters: {parameters}")
        
        # Validate and convert user_id to UUID
        try:
            user_uuid = uuid.UUID(user_id)
            logger.info(f"Successfully converted user_id to UUID: {user_uuid}")
        except (ValueError, TypeError) as uuid_error:
            logger.error(f"Invalid UUID format for user_id '{user_id}': {uuid_error}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid user ID format: {str(uuid_error)}"
            )
        
        db_service = ProblemDatabaseService(use_service_role=True)
        
        # Search problems by description using parameters as search query
        problems = db_service.search_problems_by_description(
            user_id=user_uuid,
            search_query=parameters,
            limit=limit
        )
        
        return {
            "problems": problems,
            "search_query": parameters,
            "total_found": len(problems)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching problems by description: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search problems: {str(e)}"
        )

@router.get("/history/{session_id}", response_model=GenerationSessionResponse)
async def get_session_details(
    session_id: str,
    include_results: bool = Query(True, description="Include generated problems"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get detailed information about a specific generation session.
    
    Returns session metadata and optionally the generated problems.
    """
    try:
        # User ID now comes from the token via dependency
        user_id = current_user["user_id"]  # get_current_user returns the user ID directly
        
        db_service = ProblemDatabaseService(use_service_role=True)
        
        session_data = db_service.get_session_details(
            session_id=uuid.UUID(session_id),
            user_id=uuid.UUID(user_id),
            include_results=include_results
        )
        
        if not session_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        return GenerationSessionResponse(
            session_id=session_data["session_id"],
            user_id=session_data["user_id"],
            session_name=session_data.get("session_name"),
            session_description=session_data.get("session_description"),
            parameters=session_data["parameters"],
            status=session_data["status"],
            problems_generated=session_data.get("problems_generated"),
            problems_selected=session_data.get("problems_selected"),
            created_at=session_data["created_at"],
            completed_at=session_data.get("completed_at"),
            results=session_data.get("results", [])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session details: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve session details: {str(e)}"
        )

@router.delete("/sessions/{session_id}")
async def delete_generation_session(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a problem generation session and all associated problem statements.
    This action is permanent and cannot be undone.
    """
    try:
        # Validate and get user ID from token
        user_id = current_user["user_id"]  # get_current_user returns the user ID directly
        user_uuid = uuid.UUID(user_id)
        
        logger.info(f"Deleting generation session {session_id} for user {user_id}")
        
        db_service = ProblemDatabaseService(use_service_role=True)
        
        # First, verify the session belongs to the user
        session_uuid = uuid.UUID(session_id)
        session_details = db_service.get_session_details(
            user_id=user_uuid,
            session_id=session_uuid
        )
        
        if not session_details:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found or you don't have permission to delete it"
            )
        
        # Delete all problem statements associated with this session
        problems_deleted = db_service.delete_problems_by_session(
            user_id=user_uuid,
            session_id=session_uuid
        )
        
        # Delete the session record
        session_deleted = db_service.delete_generation_session(
            user_id=user_uuid,
            session_id=session_uuid
        )
        
        if not session_deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        logger.info(f"Successfully deleted session {session_id} with {problems_deleted} problem statements")
        
        return {
            "message": "Session deleted successfully",
            "session_id": session_id,
            "problems_deleted": problems_deleted
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete session: {str(e)}"
        )
