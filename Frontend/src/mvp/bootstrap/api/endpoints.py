"""
Bootstrap API Endpoints

FastAPI endpoints for Module 3 Bootstrap Route.
Handles project creation, question retrieval, answer submission,
context retrieval, and context confirmation.
"""

import logging
import uuid
from typing import List, Optional, Union
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, Query
from pydantic import BaseModel, Field

from src.mint.api.auth_v2.utils import get_current_user

from src.mvp.bootstrap.models.state_models import (
    ContextStatus,
    ClarifyingQuestion,
    ClarifyingAnswer,
    BootstrapProjectResponse,
    QuestionsResponse,
    AnswersSubmittedResponse,
    EnhancedContextResponse,
    ContextConfirmedResponse,
    ErrorResponse,
    EnhancedContext
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/mvp/bootstrap",
    tags=["Module 3 Bootstrap"]
)


# ==================== REQUEST MODELS ====================

class SubmitAnswersRequest(BaseModel):
    """Request to submit clarifying question answers."""
    answers: List[ClarifyingAnswer]


class ConfirmContextRequest(BaseModel):
    """Request to confirm enhanced context."""
    confirmed_context: dict = Field(..., description="The confirmed (possibly edited) context")


# ==================== HELPER FUNCTIONS ====================

def _is_super_admin(current_user: dict) -> bool:
    """Check if user is super admin."""
    user_roles = current_user.get("roles", [])
    return len(user_roles) > 0 and user_roles[0] == "super_admin"


async def _run_initial_workflow(
    project_id: str,
    tenant_id: str,
    user_id: str,
    idea_text: Optional[str],
    file_keys: List[str],
    is_super_admin: bool,
    plan_type: str
):
    """Background task to run initial bootstrap workflow."""
    try:
        from src.mvp.bootstrap.workflow.bootstrap_graph import get_bootstrap_workflow
        
        workflow = get_bootstrap_workflow()
        await workflow.start_run(
            project_id=project_id,
            tenant_id=tenant_id,
            user_id=user_id,
            idea_text=idea_text,
            file_keys=file_keys,
            is_super_admin=is_super_admin,
            plan_type=plan_type
        )
    except Exception as e:
        logger.error(f"Background workflow error for {project_id}: {e}")
        # Update status to failed
        from src.mvp.bootstrap.adapters.database_adapter import get_bootstrap_database_adapter
        db_adapter = get_bootstrap_database_adapter()
        db_adapter.update_context_status(project_id, tenant_id, "failed", str(e))


async def _run_resume_workflow(
    project_id: str,
    tenant_id: str,
    answers: List[dict],
    is_super_admin: bool,
    plan_type: str
):
    """Background task to resume bootstrap workflow after answers."""
    try:
        from src.mvp.bootstrap.workflow.bootstrap_graph import get_bootstrap_workflow
        
        workflow = get_bootstrap_workflow()
        await workflow.resume_with_answers(
            project_id=project_id,
            tenant_id=tenant_id,
            answers=answers,
            is_super_admin=is_super_admin,
            plan_type=plan_type
        )
    except Exception as e:
        logger.error(f"Background workflow resume error for {project_id}: {e}")
        from src.mvp.bootstrap.adapters.database_adapter import get_bootstrap_database_adapter
        db_adapter = get_bootstrap_database_adapter()
        db_adapter.update_context_status(project_id, tenant_id, "failed", str(e))


# ==================== ENDPOINTS ====================

@router.post(
    "/projects",
    response_model=BootstrapProjectResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def create_bootstrap_project(
    background_tasks: BackgroundTasks,
    project_name: str = Form(..., description="Name for the new project"),
    idea_text: Optional[str] = Form(None, description="Initial idea description"),
    pdf_files: Union[List[UploadFile], UploadFile, List[str], str, None] = File(default=None, description="PDF files to upload"),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new bootstrap project and start the context generation workflow.
    
    At least one of `idea_text` or `pdf_files` must be provided.
    
    The workflow runs in the background:
    1. Extracts text from PDFs (if provided)
    2. Chunks and embeds all content
    3. Generates clarifying questions
    4. Sets status to 'questions_pending'
    
    Poll `/projects/{project_id}/questions` to retrieve questions.
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        plan_type = current_user.get("tenant_type", "individual")
        is_super_admin = _is_super_admin(current_user)
        
        # Handle idea_text - could be empty string
        if idea_text == "":
            idea_text = None
        
        logger.info(f"🔍 CREATE BOOTSTRAP PROJECT DEBUG:")
        logger.info(f"   - project_name: {project_name}")
        logger.info(f"   - idea_text length: {len(idea_text) if idea_text else 0}")
        logger.info(f"   - pdf_files: {pdf_files}")
        logger.info(f"   - pdf_files type: {type(pdf_files)}")
        
        # Filter valid PDF files from input (handles strings, None, single file, or list)
        valid_pdf_files = []
        if pdf_files:
            # Normalize to list
            files_list = pdf_files if isinstance(pdf_files, list) else [pdf_files]
            logger.info(f"   - files_list: {files_list}")
            for f in files_list:
                logger.info(f"   - Checking file: {f}, type: {type(f)}, is UploadFile: {isinstance(f, UploadFile)}")
                # Check if it's an UploadFile-like object with filename attribute
                if hasattr(f, 'filename') and hasattr(f, 'read'):
                    filename = f.filename
                    logger.info(f"   - filename: {filename}, bool: {bool(filename)}")
                    if filename and filename.strip():
                        valid_pdf_files.append(f)
                        logger.info(f"   - Added valid file: {filename}")
        
        logger.info(f"   - Valid PDF files count: {len(valid_pdf_files)}")
        
        # Validate input - need at least idea_text OR valid files
        if not idea_text and not valid_pdf_files:
            raise HTTPException(
                status_code=400,
                detail="At least one of idea_text or pdf_files is required"
            )
        
        if not project_name or not project_name.strip():
            raise HTTPException(
                status_code=400,
                detail="project_name is required"
            )
        
        # Upload files to storage if provided
        file_keys = []
        bucket_name = "bootstrap-uploads"
        if valid_pdf_files:
            from src.mint.api.system.core.supabase_client import get_service_role_client
            supabase = get_service_role_client()
            
            # Ensure bucket exists before uploading
            try:
                buckets = supabase.client.storage.list_buckets()
                bucket_names = [bucket.name for bucket in buckets]
                if bucket_name not in bucket_names:
                    supabase.client.storage.create_bucket(
                        bucket_name,
                        options={"public": False}  # Private bucket for uploads
                    )
                    logger.info(f"Created storage bucket: {bucket_name}")
            except Exception as bucket_error:
                logger.warning(f"Bucket check/creation: {bucket_error}")
            
            for pdf_file in valid_pdf_files:
                if pdf_file.filename:
                    # Generate unique key
                    file_key = f"{tenant_id}/{uuid.uuid4()}/{pdf_file.filename}"
                    
                    # Read file content
                    content = await pdf_file.read()
                    
                    # Upload to storage
                    try:
                        supabase.client.storage.from_(bucket_name).upload(
                            file_key, content
                        )
                        file_keys.append(file_key)
                        logger.info(f"Uploaded file: {file_key}")
                    except Exception as upload_error:
                        logger.error(f"File upload failed: {upload_error}")
                        # If user provided files but upload failed, and no idea_text, fail early
                        if not idea_text:
                            raise HTTPException(
                                status_code=500,
                                detail=f"File upload failed: {upload_error}. Please try again or provide an idea description instead."
                            )
        
        # Validate that we have at least some input
        if not idea_text and not file_keys:
            raise HTTPException(
                status_code=400,
                detail="At least one of idea description or file upload is required. File upload may have failed - please try again."
            )
        
        # Create project
        from src.mvp.bootstrap.adapters.database_adapter import get_bootstrap_database_adapter
        db_adapter = get_bootstrap_database_adapter()
        
        project = await db_adapter.create_bootstrap_project(
            tenant_id=tenant_id,
            user_id=user_id,
            project_name=project_name.strip(),
            idea_text=idea_text,
            file_keys=file_keys
        )
        
        project_id = project["id"]
        
        # Start workflow in background
        background_tasks.add_task(
            _run_initial_workflow,
            project_id=project_id,
            tenant_id=tenant_id,
            user_id=user_id,
            idea_text=idea_text,
            file_keys=file_keys,
            is_super_admin=is_super_admin,
            plan_type=plan_type
        )
        
        logger.info(f"Created bootstrap project {project_id} for user {user_id}")
        
        return BootstrapProjectResponse(
            success=True,
            project_id=project_id,
            project_name=project_name.strip(),
            context_status=ContextStatus.EMBEDDING.value,
            message="Project created. Workflow started in background."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating bootstrap project: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create project: {str(e)}"
        )


# ==================== LIST PROJECTS ====================

@router.get(
    "/projects",
    responses={
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def list_bootstrap_projects(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search query for project names"),
    current_user: dict = Depends(get_current_user)
):
    """
    List all bootstrap projects for the current user/tenant.
    
    Returns paginated list of bootstrap projects with:
    - Basic project info (id, name, status, timestamps)
    - Workflow progress indicators (has_draft, has_confirmed, questions_count)
    - File upload status
    
    Use `search` parameter to filter by project name.
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        
        from src.mvp.bootstrap.adapters.database_adapter import get_bootstrap_database_adapter
        db_adapter = get_bootstrap_database_adapter()
        
        result = db_adapter.list_bootstrap_projects(
            tenant_id=tenant_id,
            user_id=user_id,
            page=page,
            page_size=page_size,
            search=search
        )
        
        if result["success"]:
            return {
                "success": True,
                "data": {
                    "projects": result["projects"],
                    "total_count": result["total_count"],
                    "page": result["page"],
                    "page_size": result["page_size"],
                    "has_next": result["has_next"]
                },
                "message": f"Found {len(result['projects'])} bootstrap projects"
            }
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to list projects"))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing bootstrap projects: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list projects: {str(e)}"
        )


# ==================== DELETE PROJECT ====================

@router.delete(
    "/projects/{project_id}",
    responses={
        404: {"model": ErrorResponse, "description": "Project not found"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def delete_bootstrap_project(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a bootstrap project and all associated data.
    
    This permanently deletes:
    - The project record
    - All embedded chunks
    - All associated documents
    
    Note: Uploaded files in storage are NOT deleted automatically.
    """
    try:
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        is_super_admin = _is_super_admin(current_user)
        
        from src.mvp.bootstrap.adapters.database_adapter import get_bootstrap_database_adapter
        db_adapter = get_bootstrap_database_adapter()
        
        # Super admins can delete any project, regular users only their own
        owner_check = None if is_super_admin else user_id
        
        result = db_adapter.delete_bootstrap_project(
            project_id=project_id,
            tenant_id=tenant_id,
            user_id=owner_check
        )
        
        if result["success"]:
            return {
                "success": True,
                "message": result["message"]
            }
        else:
            error = result.get("error", "Failed to delete project")
            if "not found" in error.lower():
                raise HTTPException(status_code=404, detail=error)
            elif "permission" in error.lower():
                raise HTTPException(status_code=403, detail=error)
            else:
                raise HTTPException(status_code=500, detail=error)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting bootstrap project {project_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete project: {str(e)}"
        )


@router.get(
    "/projects/{project_id}/questions",
    response_model=QuestionsResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Project not found"},
        409: {"model": ErrorResponse, "description": "Questions not ready yet"}
    }
)
async def get_bootstrap_questions(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get clarifying questions for a bootstrap project.
    
    Returns questions only when `context_status` is 'questions_pending'.
    If status is 'embedding', the workflow is still processing.
    """
    try:
        tenant_id = current_user["tenant_id"]
        
        from src.mvp.bootstrap.adapters.database_adapter import get_bootstrap_database_adapter
        db_adapter = get_bootstrap_database_adapter()
        
        project = db_adapter.get_bootstrap_project(project_id, tenant_id)
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        context_status = project.get("context_status", "not_started")
        
        # Check if questions are ready
        if context_status == ContextStatus.EMBEDDING.value:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "not_ready",
                    "message": "Workflow is still processing. Please try again shortly.",
                    "context_status": context_status
                }
            )
        
        if context_status == ContextStatus.FAILED.value:
            enhanced_context = project.get("enhanced_context", {})
            error = enhanced_context.get("metadata", {}).get("error", "Unknown error")
            raise HTTPException(
                status_code=500,
                detail={
                    "code": "workflow_failed",
                    "message": f"Workflow failed: {error}",
                    "context_status": context_status
                }
            )
        
        # Get questions from enhanced_context
        enhanced_context = project.get("enhanced_context", {})
        questions_data = enhanced_context.get("metadata", {}).get("clarifying_questions", [])
        
        # Convert to response model
        questions = [
            ClarifyingQuestion(
                id=q.get("id", f"q{i}"),
                priority=q.get("priority", "P0"),
                category=q.get("category", "general"),
                question=q.get("question", ""),
                context=q.get("context"),
                required=q.get("required", True)
            )
            for i, q in enumerate(questions_data)
        ]
        
        return QuestionsResponse(
            success=True,
            project_id=project_id,
            context_status=context_status,
            questions=questions,
            message=f"Retrieved {len(questions)} questions"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting questions for {project_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get questions: {str(e)}"
        )


@router.post(
    "/projects/{project_id}/answers",
    response_model=AnswersSubmittedResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Project not found"},
        400: {"model": ErrorResponse, "description": "Invalid answers"}
    }
)
async def submit_bootstrap_answers(
    project_id: str,
    request: SubmitAnswersRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """
    Submit answers to clarifying questions and resume the workflow.
    
    The workflow continues in the background:
    1. Embeds answers
    2. Plans and executes web research
    3. Composes enhanced context
    4. Deducts credits (or sets payment_required)
    5. Sets status to 'context_ready' or 'payment_required'
    
    Poll `/projects/{project_id}/enhanced-context` to retrieve the result.
    """
    try:
        tenant_id = current_user["tenant_id"]
        plan_type = current_user.get("tenant_type", "individual")
        is_super_admin = _is_super_admin(current_user)
        
        from src.mvp.bootstrap.adapters.database_adapter import get_bootstrap_database_adapter
        db_adapter = get_bootstrap_database_adapter()
        
        project = db_adapter.get_bootstrap_project(project_id, tenant_id)
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        context_status = project.get("context_status", "not_started")
        
        # Validate status
        if context_status != ContextStatus.QUESTIONS_PENDING.value:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "invalid_status",
                    "message": f"Cannot submit answers in status '{context_status}'",
                    "context_status": context_status
                }
            )
        
        # Validate answers
        if not request.answers:
            raise HTTPException(
                status_code=400,
                detail="At least one answer is required"
            )
        
        # Convert to dict list
        answers_data = [
            {"question_id": a.question_id, "answer": a.answer}
            for a in request.answers
        ]
        
        # Update status immediately
        db_adapter.update_context_status(
            project_id, tenant_id, ContextStatus.ANSWERS_RECEIVED.value
        )
        
        # Resume workflow in background
        background_tasks.add_task(
            _run_resume_workflow,
            project_id=project_id,
            tenant_id=tenant_id,
            answers=answers_data,
            is_super_admin=is_super_admin,
            plan_type=plan_type
        )
        
        logger.info(f"Submitted {len(answers_data)} answers for project {project_id}")
        
        return AnswersSubmittedResponse(
            success=True,
            project_id=project_id,
            context_status=ContextStatus.ANSWERS_RECEIVED.value,
            message="Answers submitted. Workflow resumed in background."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting answers for {project_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit answers: {str(e)}"
        )


@router.get(
    "/projects/{project_id}/enhanced-context",
    response_model=EnhancedContextResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Project not found"},
        402: {"model": ErrorResponse, "description": "Payment required"},
        409: {"model": ErrorResponse, "description": "Context not ready"}
    }
)
async def get_enhanced_context(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get the enhanced context for a bootstrap project.
    
    Returns context only when `context_status` is 'context_ready' or 'context_confirmed'.
    If status is 'payment_required', credits must be added before access.
    """
    try:
        tenant_id = current_user["tenant_id"]
        
        from src.mvp.bootstrap.adapters.database_adapter import get_bootstrap_database_adapter
        db_adapter = get_bootstrap_database_adapter()
        
        project = db_adapter.get_bootstrap_project(project_id, tenant_id)
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        context_status = project.get("context_status", "not_started")
        
        # Check status
        if context_status == ContextStatus.PAYMENT_REQUIRED.value:
            raise HTTPException(
                status_code=402,
                detail={
                    "code": "payment_required",
                    "message": "Insufficient credits. Please add credits to access the context.",
                    "context_status": context_status
                }
            )
        
        if context_status in [
            ContextStatus.EMBEDDING.value,
            ContextStatus.QUESTIONS_PENDING.value,
            ContextStatus.ANSWERS_RECEIVED.value,
            ContextStatus.RESEARCHING.value
        ]:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "not_ready",
                    "message": f"Context generation in progress (status: {context_status})",
                    "context_status": context_status
                }
            )
        
        if context_status == ContextStatus.FAILED.value:
            enhanced_context = project.get("enhanced_context", {})
            error = enhanced_context.get("metadata", {}).get("error", "Unknown error")
            raise HTTPException(
                status_code=500,
                detail={
                    "code": "workflow_failed",
                    "message": f"Context generation failed: {error}",
                    "context_status": context_status
                }
            )
        
        # Return context
        enhanced_context_data = project.get("enhanced_context", {})
        
        return EnhancedContextResponse(
            success=True,
            project_id=project_id,
            context_status=context_status,
            enhanced_context=enhanced_context_data,
            message="Enhanced context retrieved successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting enhanced context for {project_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get enhanced context: {str(e)}"
        )


@router.put(
    "/projects/{project_id}/enhanced-context/confirm",
    response_model=ContextConfirmedResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Project not found"},
        400: {"model": ErrorResponse, "description": "Invalid request"}
    }
)
async def confirm_enhanced_context(
    project_id: str,
    request: ConfirmContextRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Confirm the enhanced context (with optional user edits).
    
    This sets `context_status` to 'context_confirmed' and stores the
    user-edited context in `enhanced_context.confirmed`.
    
    After confirmation, the project is ready for VPS/BMC generation.
    """
    try:
        tenant_id = current_user["tenant_id"]
        
        from src.mvp.bootstrap.adapters.database_adapter import get_bootstrap_database_adapter
        db_adapter = get_bootstrap_database_adapter()
        
        project = db_adapter.get_bootstrap_project(project_id, tenant_id)
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        context_status = project.get("context_status", "not_started")
        
        # Must be in context_ready or context_confirmed state
        if context_status not in [
            ContextStatus.CONTEXT_READY.value,
            ContextStatus.CONTEXT_CONFIRMED.value
        ]:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "invalid_status",
                    "message": f"Cannot confirm context in status '{context_status}'",
                    "context_status": context_status
                }
            )
        
        # Confirm context
        success = db_adapter.confirm_enhanced_context(
            project_id=project_id,
            tenant_id=tenant_id,
            confirmed_context=request.confirmed_context
        )
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to save confirmed context"
            )
        
        # Get updated version
        updated_project = db_adapter.get_bootstrap_project(project_id, tenant_id)
        new_version = updated_project.get("context_version", 1)
        
        logger.info(f"Confirmed enhanced context v{new_version} for project {project_id}")
        
        return ContextConfirmedResponse(
            success=True,
            project_id=project_id,
            context_status=ContextStatus.CONTEXT_CONFIRMED.value,
            context_version=new_version,
            message="Context confirmed successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error confirming context for {project_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to confirm context: {str(e)}"
        )


@router.get(
    "/projects/{project_id}/status",
    responses={
        404: {"model": ErrorResponse, "description": "Project not found"}
    }
)
async def get_project_status(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get the current status of a bootstrap project.
    
    Useful for polling during workflow execution.
    """
    try:
        tenant_id = current_user["tenant_id"]
        
        from src.mvp.bootstrap.adapters.database_adapter import get_bootstrap_database_adapter
        db_adapter = get_bootstrap_database_adapter()
        
        project = db_adapter.get_bootstrap_project(project_id, tenant_id)
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        return {
            "success": True,
            "project_id": project_id,
            "project_name": project.get("name"),
            "context_mode": project.get("context_mode"),
            "context_status": project.get("context_status"),
            "context_version": project.get("context_version"),
            "created_at": project.get("created_at"),
            "updated_at": project.get("updated_at")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting status for {project_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get project status: {str(e)}"
        )
