"""
FastAPI Endpoints for Project Chat Feature

Endpoints:
- Thread lifecycle: create, list, read, delete
- Messaging: post message (triggers workflow), list messages
- Debug: read thread memory, export transcript
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.mint.api.auth_v2.utils import get_current_user

from ..models import (
    CreateThreadRequest,
    PostMessageRequest,
    ListThreadsParams,
    ListMessagesParams,
    ThreadResponse,
    ThreadListResponse,
    MessageResponse,
    AssistantMessageResponse,
    MessageListResponse,
    ThreadMemoryResponse,
    ThreadStatus,
    MessageRole,
    Citation,
    ToolTrace,
)
from ..adapters.database_adapter import get_chat_database_adapter
from ..workflow import run_chat_workflow
from ..services.project_rag_service import get_project_rag_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mav", tags=["Project Chat"])


# ============================================================================
# THREAD ENDPOINTS
# ============================================================================

@router.post(
    "/projects/{project_id}/threads",
    response_model=ThreadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new chat thread",
    description="Create a new chat thread for a VMP project."
)
async def create_thread(
    project_id: str,
    request: CreateThreadRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new chat thread for the specified project.
    
    - **project_id**: VMP project ID
    - **title**: Optional thread title
    """
    user_id = current_user.get("user_id")
    tenant_id = current_user.get("tenant_id")
    
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant ID required"
        )
    
    db_adapter = get_chat_database_adapter()
    
    # Verify project access
    if not await db_adapter.verify_project_access(project_id, tenant_id, user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or access denied"
        )
    
    # Create thread
    thread = await db_adapter.create_thread(
        project_id=project_id,
        tenant_id=tenant_id,
        user_id=user_id,
        title=request.title,
        metadata=request.metadata
    )
    
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create thread"
        )
    
    logger.info(f"✅ Created thread {thread.id} for project {project_id}")
    
    return ThreadResponse(
        id=thread.id,
        project_id=thread.project_id,
        title=thread.title,
        status=thread.status,
        created_at=thread.created_at,
        updated_at=thread.updated_at,
        last_message_at=thread.last_message_at
    )


@router.get(
    "/projects/{project_id}/threads",
    response_model=ThreadListResponse,
    summary="List chat threads",
    description="List all chat threads for a VMP project."
)
async def list_threads(
    project_id: str,
    status_filter: Optional[ThreadStatus] = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user)
):
    """
    List chat threads for the specified project.
    
    - **project_id**: VMP project ID
    - **status**: Filter by thread status
    - **limit**: Max threads to return (1-100)
    - **offset**: Pagination offset
    """
    tenant_id = current_user.get("tenant_id")
    
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant ID required"
        )
    
    db_adapter = get_chat_database_adapter()
    
    threads, total_count = await db_adapter.list_threads(
        project_id=project_id,
        tenant_id=tenant_id,
        status=status_filter,
        limit=limit,
        offset=offset
    )
    
    return ThreadListResponse(
        threads=[
            ThreadResponse(
                id=t.id,
                project_id=t.project_id,
                title=t.title,
                status=t.status,
                created_at=t.created_at,
                updated_at=t.updated_at,
                last_message_at=t.last_message_at
            )
            for t in threads
        ],
        total_count=total_count,
        has_more=offset + len(threads) < total_count
    )


@router.get(
    "/threads/{thread_id}",
    response_model=ThreadResponse,
    summary="Get thread details",
    description="Get details of a specific chat thread."
)
async def get_thread(
    thread_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get details of a specific chat thread.
    
    - **thread_id**: Chat thread ID
    """
    tenant_id = current_user.get("tenant_id")
    
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant ID required"
        )
    
    db_adapter = get_chat_database_adapter()
    
    thread = await db_adapter.get_thread(thread_id, tenant_id)
    
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found"
        )
    
    # Get message count
    message_count = await db_adapter.get_message_count(thread_id)
    
    return ThreadResponse(
        id=thread.id,
        project_id=thread.project_id,
        title=thread.title,
        status=thread.status,
        created_at=thread.created_at,
        updated_at=thread.updated_at,
        last_message_at=thread.last_message_at,
        message_count=message_count
    )


@router.delete(
    "/threads/{thread_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete/archive a thread",
    description="Archive or soft-delete a chat thread."
)
async def delete_thread(
    thread_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Archive (soft-delete) a chat thread.
    
    - **thread_id**: Chat thread ID
    """
    tenant_id = current_user.get("tenant_id")
    
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant ID required"
        )
    
    db_adapter = get_chat_database_adapter()
    
    # Verify thread exists
    thread = await db_adapter.get_thread(thread_id, tenant_id)
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found"
        )
    
    # Soft delete (set status to deleted)
    success = await db_adapter.update_thread_status(
        thread_id=thread_id,
        tenant_id=tenant_id,
        status=ThreadStatus.DELETED
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete thread"
        )
    
    logger.info(f"✅ Deleted thread {thread_id}")


# ============================================================================
# MESSAGE ENDPOINTS
# ============================================================================

@router.post(
    "/threads/{thread_id}/messages",
    response_model=AssistantMessageResponse,
    summary="Post a message",
    description="Post a user message and get the assistant's response."
)
async def post_message(
    thread_id: str,
    request: PostMessageRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Post a user message to a thread and get the assistant's response.
    
    This triggers the full chat workflow:
    1. Load thread context
    2. Route intent
    3. Retrieve project evidence (RAG)
    4. Grade evidence sufficiency
    5. Web search if needed
    6. Compose answer with citations
    7. Update thread memory
    8. Persist messages
    
    - **thread_id**: Chat thread ID
    - **content**: User message content
    """
    user_id = current_user.get("user_id")
    tenant_id = current_user.get("tenant_id")
    
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant ID required"
        )
    
    db_adapter = get_chat_database_adapter()
    
    # Verify thread exists and get project_id
    thread = await db_adapter.get_thread(thread_id, tenant_id)
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found"
        )
    
    if thread.status != ThreadStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot post to archived or deleted thread"
        )
    
    logger.info(f"📨 Received message for thread {thread_id}: {request.content[:50]}...")
    
    try:
        # Run the chat workflow
        final_state = await run_chat_workflow(
            project_id=thread.project_id,
            thread_id=thread_id,
            user_id=user_id,
            tenant_id=tenant_id,
            user_message=request.content
        )
        
        # Check for errors
        if final_state.get("error"):
            logger.error(f"Workflow error at {final_state.get('error_stage')}: {final_state.get('error')}")
        
        # Get the messages we just created
        messages, _, _ = await db_adapter.get_messages(
            thread_id=thread_id,
            tenant_id=tenant_id,
            limit=2,
            order="desc"
        )
        
        # Find user and assistant messages
        user_msg = None
        assistant_msg = None
        for msg in messages:
            if msg.role == MessageRole.USER and user_msg is None:
                user_msg = msg
            elif msg.role == MessageRole.ASSISTANT and assistant_msg is None:
                assistant_msg = msg
        
        if not user_msg or not assistant_msg:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve messages"
            )
        
        return AssistantMessageResponse(
            user_message=MessageResponse(
                id=user_msg.id,
                thread_id=user_msg.thread_id,
                role=user_msg.role,
                content=user_msg.content,
                citations=[],
                created_at=user_msg.created_at,
                metadata=user_msg.metadata
            ),
            assistant_message=MessageResponse(
                id=assistant_msg.id,
                thread_id=assistant_msg.thread_id,
                role=assistant_msg.role,
                content=assistant_msg.content,
                citations=assistant_msg.citations,
                created_at=assistant_msg.created_at,
                metadata=assistant_msg.metadata
            ),
            thread_id=thread_id,
            citations=final_state.get("citations", []),
            follow_ups=final_state.get("follow_ups", []),
            tool_trace=ToolTrace(**final_state.get("tool_trace", {})) if final_state.get("tool_trace") else None
        )
        
    except Exception as e:
        logger.error(f"❌ Error processing message: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing message: {str(e)}"
        )


@router.get(
    "/threads/{thread_id}/messages",
    response_model=MessageListResponse,
    summary="Get message history",
    description="Get paginated message history for a thread."
)
async def get_messages(
    thread_id: str,
    limit: int = Query(50, ge=1, le=200),
    cursor: Optional[str] = Query(None),
    order: str = Query("desc", regex="^(asc|desc)$"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get message history for a thread with cursor-based pagination.
    
    - **thread_id**: Chat thread ID
    - **limit**: Max messages to return (1-200)
    - **cursor**: Message ID to start from (for pagination)
    - **order**: Sort order ('asc' or 'desc')
    """
    tenant_id = current_user.get("tenant_id")
    
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant ID required"
        )
    
    db_adapter = get_chat_database_adapter()
    
    messages, next_cursor, has_more = await db_adapter.get_messages(
        thread_id=thread_id,
        tenant_id=tenant_id,
        limit=limit,
        cursor=cursor,
        order=order
    )
    
    return MessageListResponse(
        messages=[
            MessageResponse(
                id=m.id,
                thread_id=m.thread_id,
                role=m.role,
                content=m.content,
                citations=m.citations if isinstance(m.citations, list) else [],
                created_at=m.created_at,
                metadata=m.metadata
            )
            for m in messages
        ],
        has_more=has_more,
        next_cursor=next_cursor
    )


# ============================================================================
# DEBUG/ADMIN ENDPOINTS
# ============================================================================

@router.get(
    "/threads/{thread_id}/memory",
    response_model=ThreadMemoryResponse,
    summary="Get thread memory (debug)",
    description="Get the current thread memory state for debugging."
)
async def get_thread_memory(
    thread_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get the current thread memory state.
    
    This is primarily for debugging and admin purposes.
    
    - **thread_id**: Chat thread ID
    """
    tenant_id = current_user.get("tenant_id")
    
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant ID required"
        )
    
    db_adapter = get_chat_database_adapter()
    
    memory_record = await db_adapter.get_thread_memory_record(thread_id, tenant_id)
    
    if not memory_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread memory not found"
        )
    
    return ThreadMemoryResponse(
        thread_id=memory_record.thread_id,
        running_summary=memory_record.running_summary,
        pinned_facts=memory_record.pinned_facts,
        open_loops=memory_record.open_loops,
        last_context_refs=memory_record.last_context_refs,
        updated_at=memory_record.updated_at
    )


@router.get(
    "/projects/completed/mvp-requirements",
    summary="List projects with completed MVP Requirements (AMRG)",
    description="Get projects that have completed the Agentic MVP Requirement Generator and are ready for chat."
)
async def get_mvp_requirements_completed_projects(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search query for project names/descriptions"),
    include_metadata: bool = Query(True, description="Include MVP requirements metadata"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get VMP projects that have completed the Agentic MVP Requirement Generator (AMRG).
    
    **These projects are READY FOR PROJECT CHAT (Module 4).**
    
    This endpoint returns only projects where:
    - mvp_data.mvp_requirements is populated (AMRG completed)
    - Project has embedded chunks in the vector database
    
    Use case: Show projects ready for RAG-based chat in Module 4.
    
    Response includes:
    - All standard project fields
    - MVP requirements metadata (if include_metadata=True):
      - MVP requirements completion status
      - Chunk count and artifact types
      - Chat readiness flag
    
    Next step after getting these projects:
    - Call `POST /api/v1/mav/projects/{project_id}/threads` to create a chat thread
    """
    from src.mint.api.system.core.supabase_client import get_service_role_client
    
    tenant_id = current_user.get("tenant_id")
    user_id = current_user.get("user_id")
    
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant ID required"
        )
    
    try:
        supabase = get_service_role_client()
        
        logger.info(f"🔍 DEBUG: [GET_AMRG_COMPLETED] Fetching AMRG-completed projects for tenant: {tenant_id}")
        logger.info(f"🔍 DEBUG: [GET_AMRG_COMPLETED] Page: {page}, Size: {page_size}, Search: {search}")
        
        # OPTIMIZED QUERY: Fetch columns needed for filtering
        select_clause = '''
            id,
            tenant_id,
            user_id,
            name,
            description,
            refined_problem_statement,
            status,
            created_at,
            updated_at,
            mvp_data,
            context_mode,
            context_status
        '''
        
        # Build query - filter by tenant_id for multi-tenant isolation
        query = supabase.client.table("vmp_projects").select(
            select_clause,
            count="exact"
        ).eq("tenant_id", tenant_id)
        
        # Search filter (optional)
        if search:
            query = query.ilike("name", f"%{search}%")
        
        # Order by most recent
        query = query.order("updated_at", desc=True)
        
        # Fetch projects with reasonable limit for filtering
        max_fetch = page_size * 5
        query = query.range(0, max_fetch - 1)
        
        # Execute query
        response = query.execute()
        
        logger.info(f"🔍 DEBUG: [GET_AMRG_COMPLETED] Query returned {len(response.data)} projects (before filtering)")
        
        # Filter projects that have 'amrg' in mvp_data
        validated_projects = []
        
        for project in response.data:
            project_id = project.get("id")
            mvp_data = project.get("mvp_data", {}) or {}
            
            # Check if 'amrg' exists in mvp_data (AMRG completed)
            amrg_data = mvp_data.get("amrg")
            
            if not amrg_data:
                continue
            
            # Get problem statement with fallback
            problem_statement = project.get("refined_problem_statement") or project.get("description") or ""
            
            # Build project object
            minimal_project = {
                "id": project_id,
                "tenant_id": project.get("tenant_id"),
                "user_id": project.get("user_id"),
                "name": project.get("name"),
                "problem_statement": problem_statement,
                "status": project.get("status"),
                "created_at": project.get("created_at"),
                "updated_at": project.get("updated_at"),
                "amrg_completed": True,
                "amrg_completed_at": project.get("updated_at"),
                "context_mode": project.get("context_mode", "normal")
            }
            
            validated_projects.append(minimal_project)
        
        # Apply pagination to filtered results
        total_count = len(validated_projects)
        offset = (page - 1) * page_size
        start_idx = offset
        end_idx = offset + page_size
        paginated_projects = validated_projects[start_idx:end_idx]
        
        has_next = (page * page_size) < total_count
        
        logger.info(f"✅ DEBUG: [GET_AMRG_COMPLETED] Returning {len(paginated_projects)} projects "
                   f"(page {page} of {total_count} total)")
        
        return {
            "success": True,
            "data": {
                "projects": paginated_projects,
                "total_count": total_count,
                "page": page,
                "page_size": page_size,
                "has_next": has_next,
                "filter_applied": "amrg_completed"
            },
            "message": f"Found {len(paginated_projects)} projects with completed AMRG"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ ERROR: [GET_AMRG_COMPLETED] Failed to fetch projects: {e}")
        import traceback
        logger.error(f"❌ ERROR: [GET_AMRG_COMPLETED] Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch MVP-requirements-completed projects: {str(e)}"
        )


@router.get(
    "/projects/{project_id}/chunk-stats",
    summary="Get project chunk statistics",
    description="Get statistics about embedded chunks for a project."
)
async def get_project_chunk_stats(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get statistics about the embedded chunks for a project.
    
    Useful for verifying that project data has been chunked and embedded.
    
    - **project_id**: VMP project ID
    """
    tenant_id = current_user.get("tenant_id")
    
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant ID required"
        )
    
    rag_service = get_project_rag_service()
    
    stats = await rag_service.get_project_chunk_stats(project_id, tenant_id)
    
    return {
        "project_id": project_id,
        "total_chunks": stats.get("total_chunks", 0),
        "by_artifact_type": stats.get("by_artifact_type", {}),
        "chat_ready": stats.get("total_chunks", 0) > 0
    }
