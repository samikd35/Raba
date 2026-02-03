"""
Chat API Endpoints for Market Research Analysis

Provides conversational interface for querying research data and analysis reports.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel, Field

from ..services.chat_service import MarketResearchChatService
from ..services.report_chunking_service import ReportChunkingService
from ..services.market_research_analysis_service import EnterpriseMarketResearchService
from src.mint.api.auth_v2.utils import get_current_user

logger = logging.getLogger(__name__)

# Create chat router
chat_router = APIRouter(prefix="/chat", tags=["market-research-chat"])


# ========== Request/Response Models ==========

class ChatMessage(BaseModel):
    """Single chat message."""
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Chat request model."""
    message: str = Field(..., min_length=1, max_length=2000, description="User's question or message")
    persona_id: Optional[str] = Field(
        default=None,
        description="Persona ID for multi-persona projects (required if project has multiple personas)"
    )
    conversation_history: Optional[List[ChatMessage]] = Field(
        default=None,
        description="Previous conversation messages for context"
    )


class ChatSource(BaseModel):
    """Source information for chat response."""
    type: str = Field(..., description="Source type (research_document, analysis_report, etc.)")
    filename: Optional[str] = Field(None, description="Source filename if applicable")
    source_type: Optional[str] = Field(None, description="Document source type (pdf, csv)")
    section_count: Optional[int] = Field(None, description="Number of sections used")
    chunk_count: Optional[int] = Field(None, description="Number of chunks used")
    insight_count: Optional[int] = Field(None, description="Number of insights used")
    includes: Optional[List[str]] = Field(None, description="Included metadata types")


class ChatContextUsed(BaseModel):
    """Information about context used in response."""
    research_chunks: int = Field(..., description="Number of uploaded research document chunks used")
    report_chunks: int = Field(..., description="Number of analysis report chunks used")


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
    """Request to prepare report for chat."""
    force_refresh: bool = Field(
        default=False,
        description="Force re-chunking even if report chunks already exist"
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


# ========== Dependency Injection ==========

def get_chat_service() -> MarketResearchChatService:
    """Get chat service instance."""
    return MarketResearchChatService()


def get_report_chunking_service() -> ReportChunkingService:
    """Get report chunking service instance."""
    return ReportChunkingService()


def get_analysis_service() -> EnterpriseMarketResearchService:
    """Get analysis service instance."""
    return EnterpriseMarketResearchService()


# ========== Endpoints ==========

@chat_router.post(
    "/projects/{project_id}/prepare-report",
    response_model=PrepareReportResponse,
    summary="Prepare Report for Chat",
    description="Chunk and embed the analysis report to enable chat functionality"
)
async def prepare_report_for_chat(
    project_id: str,
    request_body: PrepareReportRequest,
    persona_id: Optional[str] = Query(None, description="Persona ID for multi-persona projects (required if project has multiple personas)"),
    analysis_service: EnterpriseMarketResearchService = Depends(get_analysis_service),
    chunking_service: ReportChunkingService = Depends(get_report_chunking_service),
    current_user: dict = Depends(get_current_user)
):
    """
    Prepare the analysis report for chat by chunking and embedding it.
    
    For multi-persona projects, you MUST specify persona_id to prepare that persona's report.
    
    This endpoint should be called after analysis is complete to enable
    chat functionality. It chunks the report and stores embeddings in
    the vector database.
    
    **Requirements**: Analysis must be completed first
    """
    try:
        persona_tag = f" for persona '{persona_id}'" if persona_id else ""
        logger.info(f"📊 PREPARE REPORT: Starting for project {project_id}{persona_tag}")
        
        # Get project context
        project_context = await analysis_service._get_project_context(project_id)
        if not project_context:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "project_not_found",
                    "message": f"VMP project {project_id} not found"
                }
            )
        
        tenant_id = project_context.get("tenant_id")
        
        # MULTI-PERSONA VALIDATION: Check if persona_id is required and valid
        from src.vpm.adapters.database_adapter import get_yuba_database_adapter
        vpm_db_adapter = get_yuba_database_adapter()
        project_personas = await vpm_db_adapter.get_project_personas(project_id)
        
        logger.info(f"📋 PREPARE REPORT PERSONA CHECK: Project has {len(project_personas)} persona(s), requested persona: {persona_id}")
        
        # If project has multiple personas, persona_id is required
        if len(project_personas) > 1:
            if not persona_id:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "error": "persona_id_required",
                        "message": f"This project has {len(project_personas)} personas. You must specify which persona's report to prepare.",
                        "available_personas": [{"id": p.get("id"), "name": p.get("name")} for p in project_personas]
                    }
                )
            
            # Validate persona_id exists in project
            valid_persona_ids = [p.get("id") for p in project_personas]
            if persona_id not in valid_persona_ids:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "error": "invalid_persona_id",
                        "message": f"Persona ID '{persona_id}' not found in project.",
                        "available_personas": [{"id": p.get("id"), "name": p.get("name")} for p in project_personas]
                    }
                )
            
            logger.info(f"✅ PREPARE REPORT PERSONA VALIDATION: Using persona '{persona_id}'")
        
        # If project has single persona, use it automatically
        elif len(project_personas) == 1:
            if not persona_id:
                persona_id = project_personas[0].get("id")
                logger.info(f"🔄 AUTO-ASSIGN: Single persona project, using persona '{persona_id}'")
            elif persona_id != project_personas[0].get("id"):
                raise HTTPException(
                    status_code=422,
                    detail={
                        "error": "invalid_persona_id",
                        "message": f"Persona ID '{persona_id}' does not match project's persona '{project_personas[0].get('id')}'.",
                        "available_personas": [{"id": project_personas[0].get("id"), "name": project_personas[0].get("name")}]
                    }
                )
        
        # Check if analysis is complete
        analysis_data = project_context.get("analysis_data", {})
        if not analysis_data or analysis_data.get("stage") != "analysis_completed":
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "analysis_not_complete",
                    "message": "Analysis must be completed before preparing report for chat"
                }
            )
        
        # Chunk and embed the report with persona_id
        result = await chunking_service.chunk_and_embed_report(
            project_id=project_id,
            tenant_id=tenant_id,
            persona_id=persona_id
        )
        
        if result["success"]:
            logger.info(f"✅ PREPARE REPORT: Successfully prepared report with {result['chunk_count']} chunks")
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
                    "message": result.get("message", "Failed to prepare report")
                }
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ PREPARE REPORT: Error: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "preparation_error",
                "message": f"Failed to prepare report for chat: {str(e)}"
            }
        )


@chat_router.post(
    "/projects/{project_id}/message",
    response_model=ChatResponse,
    summary="Send Chat Message",
    description="Send a message and get an AI-generated response based on research data"
)
async def send_chat_message(
    project_id: str,
    request_body: ChatRequest,
    analysis_service: EnterpriseMarketResearchService = Depends(get_analysis_service),
    chat_service: MarketResearchChatService = Depends(get_chat_service),
    current_user: dict = Depends(get_current_user)
):
    """
    Send a chat message and receive an AI-generated response.
    
    The response is grounded in:
    - Uploaded research documents (PDFs and CSVs) for the specified persona
    - Generated analysis report for the specified persona
    - PV report chunks
    - Actionable insights
    - Project metadata (personas, hypotheses, assumptions)
    
    For multi-persona projects, you MUST specify persona_id to chat with that persona's data.
    
    The system maintains conversation history for follow-up questions.
    
    **Requirements**: Documents must be uploaded and analysis completed
    """
    try:
        logger.info(f"💬 CHAT MESSAGE: Processing for project {project_id}")
        logger.info(f"💬 CHAT MESSAGE: User message: {request_body.message[:100]}...")
        
        # Get project context
        project_context = await analysis_service._get_project_context(project_id)
        if not project_context:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "project_not_found",
                    "message": f"VMP project {project_id} not found"
                }
            )
        
        tenant_id = project_context.get("tenant_id")
        user_id = project_context.get("user_id") or current_user.get("user_id")
        
        # MULTI-PERSONA VALIDATION: Check if persona_id is required and valid
        from src.vpm.adapters.database_adapter import get_yuba_database_adapter
        vpm_db_adapter = get_yuba_database_adapter()
        project_personas = await vpm_db_adapter.get_project_personas(project_id)
        
        persona_id = request_body.persona_id
        logger.info(f"📋 CHAT PERSONA CHECK: Project has {len(project_personas)} persona(s), requested persona: {persona_id}")
        
        # If project has multiple personas, persona_id is required
        if len(project_personas) > 1:
            if not persona_id:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "error": "persona_id_required",
                        "message": f"This project has {len(project_personas)} personas. You must specify which persona to chat with.",
                        "available_personas": [{"id": p.get("id"), "name": p.get("name")} for p in project_personas]
                    }
                )
            
            # Validate persona_id exists in project
            valid_persona_ids = [p.get("id") for p in project_personas]
            if persona_id not in valid_persona_ids:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "error": "invalid_persona_id",
                        "message": f"Persona ID '{persona_id}' not found in project.",
                        "available_personas": [{"id": p.get("id"), "name": p.get("name")} for p in project_personas]
                    }
                )
            
            logger.info(f"✅ CHAT PERSONA VALIDATION: Using persona '{persona_id}' for chat")
        
        # If project has single persona, use it automatically
        elif len(project_personas) == 1:
            if not persona_id:
                persona_id = project_personas[0].get("id")
                logger.info(f"🔄 AUTO-ASSIGN: Single persona project, using persona '{persona_id}' for chat")
            elif persona_id != project_personas[0].get("id"):
                raise HTTPException(
                    status_code=422,
                    detail={
                        "error": "invalid_persona_id",
                        "message": f"Persona ID '{persona_id}' does not match project's persona '{project_personas[0].get('id')}'.",
                        "available_personas": [{"id": project_personas[0].get("id"), "name": project_personas[0].get("name")}]
                    }
                )
        
        # If no personas exist yet, this is an error
        else:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "no_personas_found",
                    "message": "Project must have at least one persona before using chat. Please complete persona identification first."
                }
            )
        
        # Convert Pydantic models to dicts for service
        conversation_history = None
        if request_body.conversation_history:
            conversation_history = [
                {"role": msg.role, "content": msg.content}
                for msg in request_body.conversation_history
            ]
        
        # Process chat message with persona_id and user_id for monitoring
        result = await chat_service.chat(
            project_id=project_id,
            tenant_id=tenant_id,
            user_message=request_body.message,
            conversation_history=conversation_history,
            persona_id=persona_id,
            user_id=user_id
        )
        
        if result["success"]:
            logger.info(f"✅ CHAT MESSAGE: Generated response with {len(result['sources'])} sources")
            
            # Convert sources to response models
            sources = [ChatSource(**source) for source in result["sources"]]
            
            # Convert conversation history to response models
            # Debug: Check what we're getting
            logger.info(f"🔍 DEBUG: conversation_history type: {type(result['conversation_history'])}")
            logger.info(f"🔍 DEBUG: conversation_history length: {len(result['conversation_history'])}")
            if len(result['conversation_history']) > 0:
                logger.info(f"🔍 DEBUG: First item: {result['conversation_history'][0]}")
                logger.info(f"🔍 DEBUG: First item type: {type(result['conversation_history'][0])}")
                logger.info(f"🔍 DEBUG: First item keys: {result['conversation_history'][0].keys() if isinstance(result['conversation_history'][0], dict) else 'Not a dict'}")
            
            history = []
            for i, msg in enumerate(result["conversation_history"]):
                logger.info(f"🔍 DEBUG: Processing message {i}: type={type(msg)}, is_dict={isinstance(msg, dict)}")
                if isinstance(msg, dict):
                    logger.info(f"🔍 DEBUG: Message {i} keys: {msg.keys()}")
                    logger.info(f"🔍 DEBUG: Message {i} role: {msg.get('role')}, content type: {type(msg.get('content'))}")
                    
                    if "role" in msg and "content" in msg and isinstance(msg["content"], str):
                        history.append(ChatMessage(role=msg["role"], content=msg["content"]))
                    else:
                        logger.error(f"❌ Invalid message format at index {i}: role={msg.get('role')}, content_type={type(msg.get('content'))}, content={str(msg.get('content'))[:100]}")
                        raise ValueError(f"Invalid message format in conversation history at index {i}")
                else:
                    logger.error(f"❌ Message {i} is not a dict: {type(msg)}")
                    raise ValueError(f"Message at index {i} is not a dictionary")
            
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
            # Convert conversation history to ChatMessage models
            error_history = []
            if conversation_history:
                for msg in conversation_history:
                    if isinstance(msg, dict) and "role" in msg and "content" in msg:
                        error_history.append(ChatMessage(role=msg["role"], content=msg["content"]))
            
            return ChatResponse(
                success=False,
                answer="I apologize, but I couldn't process your question.",
                sources=[],
                context_used=ChatContextUsed(
                    research_chunks=0,
                    report_chunks=0
                ),
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
    "/projects/{project_id}/clear",
    response_model=ClearConversationResponse,
    summary="Clear Conversation History",
    description="Clear the conversation history for a project and persona (if multi-persona)"
)
async def clear_conversation_history(
    project_id: str,
    persona_id: Optional[str] = Query(None, description="Persona ID for multi-persona projects"),
    analysis_service: EnterpriseMarketResearchService = Depends(get_analysis_service),
    chat_service: MarketResearchChatService = Depends(get_chat_service),
    current_user: dict = Depends(get_current_user)
):
    """
    Clear the conversation history for a project and persona.
    
    For multi-persona projects, specify persona_id to clear that persona's chat history.
    
    This allows starting a fresh conversation without previous context.
    """
    try:
        persona_tag = f" for persona '{persona_id}'" if persona_id else ""
        logger.info(f"🗑️ CLEAR CONVERSATION: For project {project_id}{persona_tag}")
        
        # Get project context
        project_context = await analysis_service._get_project_context(project_id)
        if not project_context:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "project_not_found",
                    "message": f"VMP project {project_id} not found"
                }
            )
        
        tenant_id = project_context.get("tenant_id")
        
        # Clear conversation with persona_id
        result = await chat_service.clear_conversation(
            project_id=project_id,
            tenant_id=tenant_id,
            persona_id=persona_id
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
    "/projects/{project_id}/status",
    summary="Get Chat Status",
    description="Check if chat is ready for a project"
)
async def get_chat_status(
    project_id: str,
    analysis_service: EnterpriseMarketResearchService = Depends(get_analysis_service),
    current_user: dict = Depends(get_current_user)
):
    """
    Get chat readiness status for a project.
    
    Returns information about:
    - Whether documents are uploaded
    - Whether analysis is complete
    - Whether report is prepared for chat
    - Number of available sources
    """
    try:
        logger.info(f"📊 CHAT STATUS: Checking for project {project_id}")
        
        # Get project context
        project_context = await analysis_service._get_project_context(project_id)
        if not project_context:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "project_not_found",
                    "message": f"VMP project {project_id} not found"
                }
            )
        
        # Check documents
        research_data = project_context.get("research_documents_data", {})
        has_documents = bool(research_data)
        
        # Count document sources
        document_count = 0
        if research_data:
            for key, value in research_data.items():
                if key not in ["documents_manifest", "statistics_registry"] and isinstance(value, dict):
                    document_count += 1
        
        # Check analysis status
        analysis_data = project_context.get("analysis_data", {})
        analysis_complete = analysis_data.get("stage") == "analysis_completed"
        
        # Check if report is prepared (has structured report)
        report_prepared = bool(analysis_data.get("structured_report"))
        
        # Get assumption count
        assumption_count = len(analysis_data.get("assumption_analyses", []))
        
        # Check personas
        personas = project_context.get("personas", [])
        persona_count = len(personas)
        
        # Check hypotheses and assumptions
        field_prep_data = project_context.get("field_prep_data", {})
        hypothesis_count = len(field_prep_data.get("hypotheses", []))
        assumption_field_count = len(field_prep_data.get("assumptions", []))
        
        # Determine chat readiness
        chat_ready = has_documents and analysis_complete and report_prepared
        
        return {
            "project_id": project_id,
            "chat_ready": chat_ready,
            "status": {
                "documents_uploaded": has_documents,
                "analysis_complete": analysis_complete,
                "report_prepared": report_prepared
            },
            "available_sources": {
                "research_documents": document_count,
                "analysis_assumptions": assumption_count,
                "personas": persona_count,
                "hypotheses": hypothesis_count,
                "field_assumptions": assumption_field_count
            },
            "next_steps": _get_next_steps(has_documents, analysis_complete, report_prepared)
        }
        
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


def _get_next_steps(
    has_documents: bool,
    analysis_complete: bool,
    report_prepared: bool
) -> List[str]:
    """Get next steps for enabling chat."""
    steps = []
    
    if not has_documents:
        steps.append("Upload research documents (PDFs and/or CSVs)")
    
    if has_documents and not analysis_complete:
        steps.append("Execute market research analysis")
    
    if analysis_complete and not report_prepared:
        steps.append("Prepare report for chat (call /chat/projects/{project_id}/prepare-report)")
    
    if not steps:
        steps.append("Chat is ready! Start asking questions.")
    
    return steps
