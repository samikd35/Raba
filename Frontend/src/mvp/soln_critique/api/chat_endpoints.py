"""
Chat API Endpoints for Solution Critique

Provides conversational interface for querying solution critique reports.
"""

import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..services.critique_chat_service import SolutionCritiqueChatService
from ..services.critique_report_chunking_service import CritiqueReportChunkingService
from src.mint.api.auth_v2.utils import get_current_user
from src.mvp.adapters.database_adapter import MVPDatabaseAdapter

logger = logging.getLogger(__name__)

# Create chat router
chat_router = APIRouter(
    prefix="/api/v2/mvp/projects",
    tags=["MVP - Value Proposition"]
)


# ========== Request/Response Models ==========

class ChatMessage(BaseModel):
    """Single chat message."""
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Chat request model."""
    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="User's question or message"
    )
    conversation_history: Optional[List[ChatMessage]] = Field(
        default=None,
        description="Previous conversation messages for context"
    )


class ChatSource(BaseModel):
    """Source information for chat response."""
    type: str = Field(..., description="Source type (solution_critique)")
    section_count: Optional[int] = Field(None, description="Number of sections used")
    chunk_count: Optional[int] = Field(None, description="Number of chunks used")
    includes: Optional[List[str]] = Field(None, description="Included section types")


class ChatContextUsed(BaseModel):
    """Information about context used in response."""
    critique_chunks: int = Field(..., description="Number of critique chunks used")


class ChatResponse(BaseModel):
    """Chat response model."""
    success: bool = Field(..., description="Whether the request was successful")
    answer: str = Field(..., description="AI-generated answer to the user's question")
    sources: List[ChatSource] = Field(..., description="Sources used to generate the answer")
    context_used: ChatContextUsed = Field(..., description="Context statistics")
    conversation_history: List[ChatMessage] = Field(..., description="Updated conversation history")
    timestamp: str = Field(..., description="Response timestamp")
    error: Optional[str] = Field(None, description="Error code if request failed")
    message: Optional[str] = Field(None, description="Error message if request failed")


class PrepareReportRequest(BaseModel):
    """Request to prepare critique report for chat."""
    force_refresh: bool = Field(
        default=False,
        description="Force re-chunking even if critique chunks already exist"
    )


class PrepareReportResponse(BaseModel):
    """Response for report preparation."""
    success: bool = Field(..., description="Whether preparation was successful")
    message: str = Field(..., description="Status message")
    chunk_count: Optional[int] = Field(None, description="Number of chunks created")
    project_id: str = Field(..., description="Project ID")
    error: Optional[str] = Field(None, description="Error code if failed")


class ClearConversationResponse(BaseModel):
    """Response for clearing conversation."""
    success: bool = Field(..., description="Whether clearing was successful")
    message: str = Field(..., description="Status message")
    project_id: str = Field(..., description="Project ID")


class ChatStatusResponse(BaseModel):
    """Response for chat status check."""
    project_id: str
    chat_ready: bool
    status: dict
    available_sources: dict
    next_steps: List[str]


# ========== Dependency Injection ==========

def get_chat_service() -> SolutionCritiqueChatService:
    """Get chat service instance."""
    return SolutionCritiqueChatService()


def get_chunking_service() -> CritiqueReportChunkingService:
    """Get chunking service instance."""
    return CritiqueReportChunkingService()


def get_db_adapter() -> MVPDatabaseAdapter:
    """Get database adapter instance."""
    return MVPDatabaseAdapter(use_service_role=True)


# ========== Endpoints ==========

@chat_router.post(
    "/{project_id}/solution-critique/chat/prepare",
    response_model=PrepareReportResponse,
    summary="Prepare Critique Report for Chat",
    description="Chunk and embed the solution critique report to enable chat functionality"
)
async def prepare_critique_for_chat(
    project_id: str,
    request_body: PrepareReportRequest,
    chunking_service: CritiqueReportChunkingService = Depends(get_chunking_service),
    db_adapter: MVPDatabaseAdapter = Depends(get_db_adapter),
    current_user: dict = Depends(get_current_user)
):
    """
    Prepare the solution critique report for chat by chunking and embedding it.
    
    This endpoint should be called after critique generation completes to enable
    chat functionality. It chunks the report and stores embeddings in the vector database.
    
    **Note**: This usually happens automatically after critique generation,
    but can be called manually if auto-preparation fails.
    
    **Requirements**: Solution critique must be generated and completed first
    """
    try:
        # Defensive: Strip whitespace from path parameter
        project_id = project_id.strip()
        
        tenant_id = current_user.get("tenant_id")
        
        logger.info(f"📊 PREPARE CHAT: Starting for project {project_id}")
        
        # Check if critique exists and is completed
        project_data = db_adapter.get_project(project_id, tenant_id)
        if not project_data:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "project_not_found",
                    "message": f"Project {project_id} not found"
                }
            )
        
        critique_data = project_data.get('soln_critique_data')
        if not critique_data:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "critique_not_found",
                    "message": "No solution critique found. Please generate a critique first."
                }
            )
        
        if critique_data.get('status') != 'completed':
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "critique_not_complete",
                    "message": f"Critique status is '{critique_data.get('status')}', not completed. Wait for completion."
                }
            )
        
        # Chunk and embed the report
        result = await chunking_service.chunk_and_embed_report(
            project_id=project_id,
            tenant_id=tenant_id
        )
        
        if result["success"]:
            logger.info(f"✅ PREPARE CHAT: Successfully prepared with {result['chunk_count']} chunks")
            return PrepareReportResponse(
                success=True,
                message=result["message"],
                chunk_count=result["chunk_count"],
                project_id=project_id
            )
        else:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": result.get("error", "preparation_error"),
                    "message": result.get("message", "Failed to prepare critique for chat")
                }
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ PREPARE CHAT: Error: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "preparation_error",
                "message": f"Failed to prepare critique for chat: {str(e)}"
            }
        )


@chat_router.post(
    "/{project_id}/solution-critique/chat/message",
    response_model=ChatResponse,
    summary="Send Chat Message",
    description="Send a message and get an AI-generated response based on solution critique"
)
async def send_chat_message(
    project_id: str,
    request_body: ChatRequest,
    chat_service: SolutionCritiqueChatService = Depends(get_chat_service),
    db_adapter: MVPDatabaseAdapter = Depends(get_db_adapter),
    current_user: dict = Depends(get_current_user)
):
    """
    Send a chat message and receive an AI-generated response.
    
    The response is grounded in the solution critique report:
    - Executive summary with overall viability assessment
    - Critiques across 5 dimensions (Market, Operational, Business Model, Competitive, Technical)
    - Prioritized actions and recommendations
    - Research sources (web, BMC, VPC, VPS)
    
    The system maintains conversation history for follow-up questions.
    
    **Requirements**: Solution critique must be generated and completed first
    """
    try:
        # Defensive: Strip whitespace from path parameter
        project_id = project_id.strip()
        
        tenant_id = current_user.get("tenant_id")
        
        logger.info(f"💬 CHAT MESSAGE: Processing for project {project_id}")
        logger.info(f"💬 CHAT MESSAGE: User message: {request_body.message[:100]}...")
        
        # Check if project and critique exist
        project_data = db_adapter.get_project(project_id, tenant_id)
        if not project_data:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "project_not_found",
                    "message": f"Project {project_id} not found"
                }
            )
        
        # Convert Pydantic models to dicts for service
        conversation_history = None
        if request_body.conversation_history:
            conversation_history = [
                {"role": msg.role, "content": msg.content}
                for msg in request_body.conversation_history
            ]
        
        # Process chat message
        result = await chat_service.chat(
            project_id=project_id,
            tenant_id=tenant_id,
            user_message=request_body.message,
            conversation_history=conversation_history
        )
        
        if result["success"]:
            logger.info(f"✅ CHAT MESSAGE: Generated response with {len(result['sources'])} sources")
            
            # Convert sources to response models
            sources = [ChatSource(**source) for source in result["sources"]]
            
            # Convert conversation history to response models
            history = []
            for msg in result["conversation_history"]:
                if isinstance(msg, dict) and "role" in msg and "content" in msg:
                    history.append(ChatMessage(role=msg["role"], content=msg["content"]))
            
            # Convert context used to response model
            context_used = ChatContextUsed(**result["context_used"])
            
            return ChatResponse(
                success=True,
                answer=result["answer"],
                sources=sources,
                context_used=context_used,
                conversation_history=history,
                timestamp=result["timestamp"]
            )
        else:
            # Return error response
            error_history = []
            if conversation_history:
                for msg in conversation_history:
                    if isinstance(msg, dict) and "role" in msg and "content" in msg:
                        error_history.append(ChatMessage(role=msg["role"], content=msg["content"]))
            
            return ChatResponse(
                success=False,
                answer="I apologize, but I couldn't process your question.",
                sources=[],
                context_used=ChatContextUsed(critique_chunks=0),
                conversation_history=error_history,
                timestamp=datetime.utcnow().isoformat(),
                error=result.get("error"),
                message=result.get("message")
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ CHAT MESSAGE: Error: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "chat_error",
                "message": f"Failed to process chat message: {str(e)}"
            }
        )


@chat_router.post(
    "/{project_id}/solution-critique/chat/clear",
    response_model=ClearConversationResponse,
    summary="Clear Conversation History",
    description="Clear the conversation history for a project"
)
async def clear_conversation_history(
    project_id: str,
    chat_service: SolutionCritiqueChatService = Depends(get_chat_service),
    db_adapter: MVPDatabaseAdapter = Depends(get_db_adapter),
    current_user: dict = Depends(get_current_user)
):
    """
    Clear the conversation history for a project.
    
    This allows starting a fresh conversation without previous context.
    """
    try:
        # Defensive: Strip whitespace from path parameter
        project_id = project_id.strip()
        
        tenant_id = current_user.get("tenant_id")
        
        logger.info(f"🗑️ CLEAR CONVERSATION: For project {project_id}")
        
        # Check if project exists
        project_data = db_adapter.get_project(project_id, tenant_id)
        if not project_data:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "project_not_found",
                    "message": f"Project {project_id} not found"
                }
            )
        
        # Clear conversation
        result = await chat_service.clear_conversation(
            project_id=project_id,
            tenant_id=tenant_id
        )
        
        if result["success"]:
            logger.info(f"✅ CLEAR CONVERSATION: Successfully cleared for project {project_id}")
            return ClearConversationResponse(
                success=True,
                message=result["message"],
                project_id=project_id
            )
        else:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": result.get("error", "clear_error"),
                    "message": result.get("message", "Failed to clear conversation")
                }
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ CLEAR CONVERSATION: Error: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "clear_error",
                "message": f"Failed to clear conversation: {str(e)}"
            }
        )


@chat_router.get(
    "/{project_id}/solution-critique/chat/status",
    response_model=ChatStatusResponse,
    summary="Get Chat Status",
    description="Check if chat is ready for a project"
)
async def get_chat_status(
    project_id: str,
    db_adapter: MVPDatabaseAdapter = Depends(get_db_adapter),
    current_user: dict = Depends(get_current_user)
):
    """
    Get chat readiness status for a project.
    
    Returns information about:
    - Whether critique is generated
    - Whether critique is completed
    - Whether report is prepared for chat (chunks exist)
    - Number of available chunks
    """
    try:
        # Defensive: Strip whitespace from path parameter
        project_id = project_id.strip()
        
        tenant_id = current_user.get("tenant_id")
        
        logger.info(f"📊 CHAT STATUS: Checking for project {project_id}")
        
        # Get project data
        project_data = db_adapter.get_project(project_id, tenant_id)
        if not project_data:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "project_not_found",
                    "message": f"Project {project_id} not found"
                }
            )
        
        # Check critique status
        critique_data = project_data.get('soln_critique_data')
        has_critique = bool(critique_data)
        critique_complete = critique_data.get('status') == 'completed' if critique_data else False
        
        # Check if chunks exist
        from src.mint.api.services.storage.chunk_storage_service import get_chunk_storage_service
        chunk_service = get_chunk_storage_service()
        all_chunks = await chunk_service.get_chunks_by_report_id(project_id)
        
        critique_chunks = [
            chunk for chunk in all_chunks
            if chunk.get('metadata', {}).get('source_type') == 'solution_critique'
        ]
        
        report_prepared = len(critique_chunks) > 0
        
        # Determine chat readiness
        chat_ready = has_critique and critique_complete and report_prepared
        
        # Build next steps
        next_steps = []
        if not has_critique:
            next_steps.append("Generate solution critique (POST /solution-critique/generate)")
        elif not critique_complete:
            next_steps.append(f"Wait for critique to complete (current status: {critique_data.get('status')})")
        elif not report_prepared:
            next_steps.append("Prepare report for chat (POST /solution-critique/chat/prepare)")
        else:
            next_steps.append("Chat is ready! Start asking questions.")
        
        return ChatStatusResponse(
            project_id=project_id,
            chat_ready=chat_ready,
            status={
                "critique_generated": has_critique,
                "critique_complete": critique_complete,
                "report_prepared": report_prepared
            },
            available_sources={
                "critique_chunks": len(critique_chunks),
                "all_chunks": len(all_chunks)
            },
            next_steps=next_steps
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ CHAT STATUS: Error: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "status_error",
                "message": f"Failed to get chat status: {str(e)}"
            }
        )
