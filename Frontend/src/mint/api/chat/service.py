#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Report Chat Service for MINT.

This module provides functionality for chatting with reports using RAG (Retrieval-Augmented Generation).

MIGRATED TO RESPONSES API (Dec 2025):
- Uses centralized OpenAIProvider.generate_responses() for gpt-5-mini
- Leverages reasoning.effort and text.verbosity for grounded output
"""

import asyncio
import json
import logging
import uuid
import os
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

import httpx
import numpy as np
from pydantic import BaseModel, Field
from langgraph.checkpoint.memory import MemorySaver

from ..ai.config import (
    ModelProvider, 
    ModelType, 
    ModelUseCase,
    get_api_key, 
    get_model_name,
    get_client_config,
    get_provider_with_fallback
)
from ..ai.providers import OpenAIProvider, LLMConfig

from ..system.core.supabase_client import get_supabase_client
from ..report.report_models import ReportChunk, ReportChunkWithEmbedding
from ..services.ai.embedding_service import get_embedding_service
from ..services.ai.vector_search_service import search_chunks_with_fallback, get_vector_search_service
from ..system.middleware.id_consistency_middleware import ensure_report_id_consistency, log_id_flow, IDConsistencyError
from .models import (
    ChatMessage, ChatMessageType, ChatQuery, ChatResponse, ChatValidationResult,
    ChatSearchResult, ChatWebSearchResult, ChatContext, ChatConfig,
    DEFAULT_SIMILARITY_THRESHOLD, DEFAULT_MAX_CHUNKS
)
from .utils import (
    generate_message_id, generate_session_id, validate_message_content,
    format_search_results, format_web_search_results, create_performance_metrics,
    log_chat_operation, format_chat_context
)

# Import AI token monitoring service
from monitor.tokens.service import get_monitoring_service
from monitor.tokens.models import AIUsageContext


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import shared Azure OpenAI semaphore
from ..system.core.azure_semaphore import azure_openai_semaphore

# Constants
DEFAULT_SIMILARITY_THRESHOLD = 0.2
DEFAULT_MAX_CHUNKS = 5


async def resolve_report_identifier(report_identifier: str, user_token: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Resolve a report identifier to the actual report data.
    
    The identifier can be either:
    - The actual report ID (uuid)
    - The session_id (which is used in frontend URLs)
    
    Args:
        report_identifier: Either report ID or session_id
        user_token: Optional JWT token for user authentication
        
    Returns:
        Dict containing report data if found, None otherwise
    """
    # Enhanced ID consistency logging
    logger.info(f"ID RESOLUTION: Input identifier: {report_identifier} (type: {type(report_identifier).__name__})")
    logger.info(f"Resolving report identifier: {report_identifier}")
    
    try:
        from ..system.core.supabase_client import get_service_role_client
        service_client = get_service_role_client()
        
        # First, try to find by ID (direct match)
        logger.info(f"Trying to find report by ID: {report_identifier}")
        report_result = service_client.client.table("documents").select("id, created_by, metadata, title").eq("id", report_identifier).eq("source_type", "pv_report").execute()
        
        if report_result.data and len(report_result.data) > 0:
            report = report_result.data[0]
            # Map documents table fields to expected format
            mapped_report = {
                'id': report['id'],
                'user_id': report['created_by'],  # Map created_by to user_id
                'session_id': report.get('metadata', {}).get('session_id', report['id']),
                'title': report['title']
            }
            logger.info(f"Found report by ID: {mapped_report['id']}, user_id={mapped_report['user_id']}, session_id={mapped_report['session_id']}")
            return mapped_report
        
        # If not found by ID, try to find by session_id (stored as ID in documents table)
        logger.info(f"Report not found by ID, session_id lookup not needed since session_id is stored as ID in documents table")
        return None
        
        logger.warning(f"Report not found with identifier: {report_identifier}")
        return None
        
    except Exception as e:
        logger.error(f"Error resolving report identifier {report_identifier}: {str(e)}")
        return None


class ChatMessage(BaseModel):
    """Schema for a chat message."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    report_id: str
    user_id: Optional[str] = None  # Allow None for service role usage
    role: str  # 'user', 'assistant', or 'system'
    content: str
    created_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = {}
    
    def to_json(self) -> Dict[str, Any]:
        """Convert the message to a JSON-compatible dictionary.
        
        Returns:
            Dict[str, Any]: JSON-compatible dictionary
        """
        return {
            "id": self.id,
            "report_id": self.report_id,
            "user_id": self.user_id,
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata
        }
    
    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "ChatMessage":
        """Create a ChatMessage from a JSON-compatible dictionary.
        
        Args:
            data: JSON-compatible dictionary
            
        Returns:
            ChatMessage: Created message
        """
        # Convert string timestamp to datetime if needed
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        else:
            created_at = data.get("created_at", datetime.now())
            
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            report_id=data.get("report_id"),
            user_id=data.get("user_id"),
            role=data.get("role"),
            content=data.get("content"),
            created_at=created_at,
            metadata=data.get("metadata", {})
        )


class ReportChatService:
    """Service for chatting with reports using RAG with Azure OpenAI support and conversation memory."""

    def __init__(self, api_key: Optional[str] = None, provider: Optional[ModelProvider] = None, user_token: Optional[str] = None):
        """Initialize the report chat service with Azure OpenAI support and memory.
        
        Args:
            api_key: Optional API key override
            provider: Optional provider override (defaults to Azure OpenAI with OpenAI fallback)
            user_token: JWT token for user authentication (enables RLS)
        """
        self.user_token = user_token
        
        # Initialize memory saver for conversation memory
        self.memory = MemorySaver()
        self.chat_sessions = {}  # Track active chat sessions
        
        # Use centralized configuration to get the best provider and model for chat completion
        self.provider, self.chat_model, self.client_config = get_client_config(
            ModelUseCase.CHAT_COMPLETION, 
            provider
        )
        
        # Override API key if provided
        if api_key:
            self.client_config["api_key"] = api_key
        
        # Store API key as attribute for compatibility
        self.api_key = self.client_config["api_key"]
        
        # Use user-authenticated client if token provided, otherwise fall back to service role
        if user_token:
            logger.info("Initializing chat service with user authentication (RLS enabled)")
            self.supabase = get_supabase_client(use_service_role=False)  # Use RLS-enabled client
        else:
            logger.info("Initializing chat service with service role (RLS bypassed)")
            self.supabase = get_supabase_client(use_service_role=True)  # Fallback to service role
        
        # Initialize the appropriate client (same pattern as EmbeddingService which works)
        if self.provider == ModelProvider.AZURE_OPENAI:
            logger.info(f"Initializing Azure OpenAI chat service: {self.chat_model}")
            logger.info(f"Using base_url: {self.client_config.get('base_url')}")
            logger.info(f"API key present: {bool(self.client_config.get('api_key'))}")
            from openai import AsyncOpenAI
            import os
            api_version = self.client_config.get("api_version") or os.environ.get("AZURE_OPENAI_API_VERSION", "2025-04-01-preview")
            self.client = AsyncOpenAI(
                api_key=self.client_config["api_key"],
                base_url=self.client_config["base_url"],
                timeout=120.0,  # 120 second timeout
                default_query={"api-version": api_version}
            )
        elif self.provider == ModelProvider.OPENAI:
            logger.info(f"Initializing OpenAI chat service with model: {self.chat_model}")
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(
                api_key=self.client_config["api_key"],
                timeout=120.0
            )
        else:
            raise ValueError(f"Provider {self.provider} not supported for chat")
        
        logger.info(f"ReportChatService initialized with provider: {self.provider}, model/deployment: {self.chat_model}")
        
        # Initialize centralized OpenAIProvider for Responses API (gpt-5-mini)
        provider_config = LLMConfig(
            provider_type="llm",
            provider_name="openai",
            api_key_env_var="AZURE_OPENAI_API_KEY" if self.provider == ModelProvider.AZURE_OPENAI else "OPENAI_API_KEY",
            model_name=self.chat_model,
            temperature=0.2,
            max_tokens=4096,
            api_key=self.client_config.get("api_key"),
            azure_endpoint=self.client_config.get("azure_endpoint"),
            api_version=self.client_config.get("api_version"),
            base_url=self.client_config.get("base_url")
        )
        self.llm_provider = OpenAIProvider(provider_config)
    
    def create_chat_session(self, report_id: str, user_id: str) -> str:
        """Create a new chat session with memory for a report.
        
        Args:
            report_id: ID of the report
            user_id: ID of the user
            
        Returns:
            str: Chat session ID
        """
        chat_session_id = f"{report_id}_{user_id}_{str(uuid.uuid4())[:8]}"
        
        # Initialize memory for this session
        self.chat_sessions[chat_session_id] = {
            "report_id": report_id,
            "user_id": user_id,
            "created_at": datetime.now(),
            "message_history": []
        }
        
        logger.info(f"Created new chat session: {chat_session_id} for report {report_id}")
        return chat_session_id
    
    def get_or_create_chat_session(self, report_id: str, user_id: str, chat_session_id: Optional[str] = None) -> str:
        """Get or create a chat session ID for conversation memory.
        
        IMPORTANT: For backend-managed memory, we use a deterministic session ID
        based on report_id and user_id. This ensures all messages for the same
        report/user combination are in the same conversation.
        
        Args:
            report_id: ID of the report
            user_id: ID of the user
            chat_session_id: Optional existing chat session ID (ignored for backend memory)
            
        Returns:
            str: Chat session ID (deterministic: report_id_user_id)
        """
        # Use deterministic session ID: report_id + user_id
        # This ensures all messages for this report/user are in one conversation
        session_id = f"{report_id}_{user_id}"
        logger.info(f"Using deterministic chat session: {session_id} for report {report_id}")
        
        return session_id
    
    def clear_chat_session(self, chat_session_id: str) -> bool:
        """Clear a chat session and its memory.
        
        Args:
            chat_session_id: ID of the chat session to clear
            
        Returns:
            bool: True if session was cleared, False if not found
        """
        if chat_session_id in self.chat_sessions:
            del self.chat_sessions[chat_session_id]
            logger.info(f"Cleared chat session: {chat_session_id}")
            return True
        return False
    
    def get_conversation_memory(self, chat_session_id: str) -> List[Dict[str, Any]]:
        """Get conversation memory for a chat session.
        
        Args:
            chat_session_id: ID of the chat session
            
        Returns:
            List[Dict[str, Any]]: List of messages in conversation memory
        """
        if chat_session_id in self.chat_sessions:
            return self.chat_sessions[chat_session_id]["message_history"]
        return []
    
    def add_to_conversation_memory(self, chat_session_id: str, role: str, content: str, metadata: Dict[str, Any] = None):
        """Add a message to conversation memory.
        
        Args:
            chat_session_id: ID of the chat session
            role: Role of the message sender ('user', 'assistant', or 'system')
            content: Content of the message
            metadata: Optional metadata about the message
        """
        if chat_session_id in self.chat_sessions:
            message = {
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {}
            }
            self.chat_sessions[chat_session_id]["message_history"].append(message)
            
            # Keep only last 20 messages to prevent memory bloat
            if len(self.chat_sessions[chat_session_id]["message_history"]) > 20:
                self.chat_sessions[chat_session_id]["message_history"] = \
                    self.chat_sessions[chat_session_id]["message_history"][-20:]
    
    async def store_message(
        self, 
        report_id: str, 
        user_id: str, 
        role: str, 
        content: str,
        metadata: Dict[str, Any] = None
    ) -> Optional[str]:
        """Store a chat message in the database.
        
        Args:
            report_id: ID of the report (can be actual ID or session_id)
            user_id: ID of the user
            role: Role of the message sender ('user', 'assistant', or 'system')
            content: Content of the message
            metadata: Optional metadata about the message
            
        Returns:
            str: ID of the stored message, or None if storage failed
        """
        logger.info(f"Storing {role} message for report identifier {report_id}")
        
        # First, resolve the report identifier to get the actual report data
        report_data = await resolve_report_identifier(report_id, self.user_token)
        if not report_data:
            logger.error(f"Cannot store message: report not found with identifier {report_id}")
            return None
        
        # Use the actual report ID for storage
        actual_report_id = report_data['id']
        logger.info(f"Resolved report identifier {report_id} to actual ID {actual_report_id}")
        
        try:
            # Create a ChatMessage object
            message = ChatMessage(
                id=str(uuid.uuid4()),
                report_id=actual_report_id,
                user_id=user_id,
                role=role,
                content=content,
                created_at=datetime.now(),
                metadata=metadata or {}
            )
            
            # Add tracking metadata
            if not message.metadata.get("tracking"):
                message.metadata["tracking"] = {}
            
            message.metadata["tracking"].update({
                "timestamp": datetime.now().isoformat(),
                "client_info": {
                    "service": "report_chat_service"
                }
            })
            
            # Convert to JSON-compatible dictionary
            data = message.to_json()
            
            # Validate JSON format compliance
            try:
                # Ensure the data can be serialized to JSON
                json_str = json.dumps(data)
                # And deserialized back
                json.loads(json_str)
            except (TypeError, ValueError) as e:
                logger.error(f"JSON format compliance error: {e}")
                # Try to fix the data by removing problematic fields
                for key in list(data["metadata"].keys()):
                    try:
                        json.dumps(data["metadata"][key])
                    except (TypeError, ValueError):
                        logger.warning(f"Removing non-JSON-compliant metadata field: {key}")
                        data["metadata"][key] = str(data["metadata"][key])
            
            # Insert into database with flexible authentication
            try:
                # Strategy: Try user authentication first, fall back to service role for legacy reports
                client = None
                
                # We already have report_data from the resolver, so we can use it directly
                logger.info(f"Report found for chat: ID={actual_report_id}, user_id={report_data.get('user_id', 'NULL')}")
                
                # Use service role client with user_id filtering for security
                # This avoids JWT authentication issues while maintaining data isolation
                logger.info("Using service role for database access with user_id filtering")
                from ..system.core.supabase_client import get_service_role_client
                service_client = get_service_role_client()
                client = service_client
                logger.info(f"Report accessible with service role: user_id={report_data.get('user_id', 'NULL')}")
                
                # Store chat message in documents table following actionable insights pattern
                # Get tenant_id from the parent report
                parent_report = client.client.table("documents").select("tenant_id, title").eq("id", actual_report_id).eq("source_type", "pv_report").execute()
                
                if not parent_report.data:
                    logger.error(f"Parent report {actual_report_id} not found for chat message storage")
                    return None
                
                tenant_id = parent_report.data[0]["tenant_id"]
                
                # Create chat message document
                chat_document = {
                    "tenant_id": tenant_id,
                    "source_document_id": actual_report_id,  # Link to parent report
                    "source_type": "actionable_insights",  # Use existing allowed type
                    "document_type": "chat_message",  # Distinguish from actual insights
                    "title": f"Chat Message - {data['role']}",
                    "content": {
                        "role": data["role"],
                        "content": data["content"],
                        "report_id": data["report_id"],
                        "user_id": data["user_id"],
                        "chat_session_id": data.get("chat_session_id"),
                        "metadata": data.get("metadata", {})
                    },
                    "created_by": data["user_id"],
                    "metadata": {
                        "message_type": "chat",
                        "chat_session_id": data.get("chat_session_id"),
                        "report_id": data["report_id"]
                    }
                }
                
                logger.info(f"💾 DEBUG: Storing message with source_document_id={actual_report_id}, document_type=chat_message")
                
                result = client.client.table("documents").insert(chat_document).execute()
                
                if not result.data or len(result.data) == 0:
                    logger.error(f"Failed to insert chat message: {result}")
                    return None
                    
            except Exception as e:
                logger.error(f"Error storing message: {e}")
                
                # Check if it's a foreign key constraint error
                if "foreign key constraint" in str(e).lower():
                    logger.error(f"Foreign key constraint violation - report {report_id} may not exist or be accessible")
                    logger.error("This suggests an RLS policy or database consistency issue")
                
                return None
            
            logger.info(f"Stored message with ID: {message.id}")
            return message.id
        
        except Exception as e:
            logger.error(f"Error storing message: {e}")
            return None
    
    async def get_chat_history(
        self, 
        report_id: str, 
        limit: int = 20, 
        offset: int = 0,
        sort_by: str = "created_at",
        sort_order: str = "asc",
        role_filter: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        search_query: Optional[str] = None,
        include_metadata: bool = True,
        page: Optional[int] = None,
        user_token: str = None
    ) -> List[ChatMessage]:
        """Get chat history for a report with pagination, sorting, and filtering.
        
        Args:
            report_id: ID of the report (can be actual ID or session_id)
            limit: Maximum number of messages to return
            offset: Offset for pagination
            sort_by: Field to sort by (created_at, role)
            sort_order: Sort order (asc, desc)
            role_filter: Filter by role (user, assistant, system)
            date_from: Filter by date from (ISO format)
            date_to: Filter by date to (ISO format)
            search_query: Search for text in content
            include_metadata: Whether to include metadata in the results
            page: Page number (1-based, overrides offset if provided)
            user_token: User token for RLS enforcement
            
        Returns:
            List[ChatMessage]: List of chat messages
        """
        logger.info(f"Getting chat history for report identifier {report_id}")
        
        # First, resolve the report identifier to get the actual report data
        report_data = await resolve_report_identifier(report_id, user_token)
        if not report_data:
            logger.error(f"Cannot get chat history: report not found with identifier {report_id}")
            return []
        
        # Use the actual report ID for querying
        actual_report_id = report_data['id']
        logger.info(f"Resolved report identifier {report_id} to actual ID {actual_report_id}")
        
        try:
            # Calculate offset from page if provided
            if page is not None and page > 0:
                offset = (page - 1) * limit
            
            # Start building the query
            select_fields = "*" if include_metadata else "id,report_id,user_id,role,content,created_at"
            
            # CRITICAL: Always use service role client for chat history retrieval to bypass RLS
            # Security is maintained by filtering on source_document_id (report access already validated)
            logger.info(f"Retrieving chat history for report {actual_report_id} using service role")
            
            # Get service role client to bypass RLS policies
            from ..system.core.supabase_client import get_service_role_client
            service_client = get_service_role_client()
            
            # DEBUG: Check what documents exist for this report
            debug_query = service_client.client.table("documents").select("id, document_type, source_type, source_document_id, metadata").eq("source_document_id", actual_report_id).limit(20)
            debug_result = debug_query.execute()
            logger.info(f"📚 DEBUG: Found {len(debug_result.data) if debug_result.data else 0} total documents with source_document_id={actual_report_id}")
            if debug_result.data:
                for doc in debug_result.data[:5]:  # Show first 5
                    msg_type = doc.get('metadata', {}).get('message_type') if doc.get('metadata') else None
                    logger.info(f"📚 DEBUG: Document - id={doc.get('id')}, document_type={doc.get('document_type')}, source_type={doc.get('source_type')}, metadata.message_type={msg_type}")
            
            # CRITICAL FIX: Filter by metadata.message_type='chat' instead of document_type
            # because document_type is not being stored in the database
            query = service_client.client.table("documents").select("id, content, created_at, created_by, metadata").eq("source_document_id", actual_report_id).eq("source_type", "actionable_insights").contains("metadata", {"message_type": "chat"})
            
            # Apply role filter if provided (role is now in content JSONB)
            if role_filter:
                query = query.eq("content->>role", role_filter)
            
            # Apply date filters if provided
            if date_from:
                query = query.gte("created_at", date_from)
            if date_to:
                query = query.lte("created_at", date_to)
            
            # Apply text search if provided
            if search_query:
                query = query.ilike("content", f"%{search_query}%")
            
            # Apply sorting
            valid_sort_fields = ["created_at", "role"]
            if sort_by not in valid_sort_fields:
                sort_by = "created_at"  # Default sort field
            
            is_desc = sort_order.lower() == "desc"
            query = query.order(sort_by, desc=is_desc)
            
            # Apply pagination
            query = query.range(offset, offset + limit - 1)
            
            # Execute the query
            result = query.execute()
            
            if hasattr(result, "error") and result.error:
                logger.error(f"Error getting chat history: {result.error}")
                return []
            
            # Convert to ChatMessage objects
            messages = []
            for item in result.data:
                try:
                    # Transform documents table structure to ChatMessage format
                    content_data = item.get("content", {})
                    transformed_data = {
                        "id": item.get("id"),
                        "report_id": content_data.get("report_id"),
                        "user_id": content_data.get("user_id") or item.get("created_by"),
                        "role": content_data.get("role"),
                        "content": content_data.get("content"),
                        "created_at": item.get("created_at"),
                        "metadata": content_data.get("metadata", {})
                    }
                    message = ChatMessage.from_json(transformed_data)
                    messages.append(message)
                except Exception as e:
                    logger.error(f"Error parsing message: {e}")
                    logger.error(f"Item data: {item}")
            
            return messages
        
        except Exception as e:
            logger.error(f"Error getting chat history: {e}")
            return []
            
    async def get_chat_history_by_page(
        self,
        report_id: str,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "asc",
        role_filter: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        search_query: Optional[str] = None,
        include_metadata: bool = True,
        user_token: str = None
    ) -> Dict[str, Any]:
        """Get paginated chat history for a report with additional pagination metadata.
        
        Args:
            report_id: ID of the report (can be actual ID or session_id)
            page: Page number (1-based)
            page_size: Number of messages per page
            sort_by: Field to sort by (created_at, role)
            sort_order: Sort order (asc, desc)
            role_filter: Filter by role (user, assistant, system)
            date_from: Filter by date from (ISO format)
            date_to: Filter by date to (ISO format)
            search_query: Search for text in content
            include_metadata: Whether to include metadata in the results
            
        Returns:
            Dict[str, Any]: Dictionary with messages and pagination metadata
        """
        # Get messages for the current page
        messages = await self.get_chat_history(
            report_id=report_id,
            limit=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
            role_filter=role_filter,
            date_from=date_from,
            date_to=date_to,
            search_query=search_query,
            include_metadata=include_metadata,
            page=page,
            user_token=user_token
        )
        
        # Get the total number of pages
        total_pages = await self.get_total_pages(
            report_id=report_id,
            page_size=page_size,
            role_filter=role_filter,
            date_from=date_from,
            date_to=date_to,
            search_query=search_query,
            user_token=user_token
        )
        
        # Get the total count of messages
        total_count = await self.get_chat_history_count(
            report_id=report_id,
            role_filter=role_filter,
            date_from=date_from,
            date_to=date_to,
            search_query=search_query,
            user_token=user_token
        )
        
        # Convert ChatMessage objects to dictionaries for API response
        messages_json = [message.to_json() for message in messages]
        
        # Return the messages and pagination metadata
        return {
            "messages": messages_json,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "total_count": total_count,
                "has_previous": page > 1,
                "has_next": page < total_pages
            }
        }
            
    async def get_chat_history_count(
        self,
        report_id: str,
        role_filter: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        search_query: Optional[str] = None,
        user_token: str = None
    ) -> int:
        """Get the total count of chat messages for a report with filtering.
        
        Args:
            report_id: ID of the report (can be actual ID or session_id)
            role_filter: Filter by role (user, assistant, system)
            date_from: Filter by date from (ISO format)
            date_to: Filter by date to (ISO format)
            search_query: Search for text in content
            
        Returns:
            int: Total count of messages
        """
        logger.info(f"Getting chat history count for report identifier {report_id}")
        
        # First, resolve the report identifier to get the actual report data
        report_data = await resolve_report_identifier(report_id, user_token)
        if not report_data:
            logger.error(f"Cannot get chat history count: report not found with identifier {report_id}")
            return 0
        
        # Use the actual report ID for querying
        actual_report_id = report_data['id']
        logger.info(f"Resolved report identifier {report_id} to actual ID {actual_report_id}")
        
        try:
            # Start building the query
            # Use user token for RLS enforcement if provided, otherwise fallback to service role key
            if user_token:
                logger.info(f"Using user token for RLS enforcement when counting chat history for report {actual_report_id}")
                # Create a client with the user's JWT token for RLS enforcement
                from supabase import create_client, Client
                import os
                
                supabase_url = os.environ.get("SUPABASE_URL")
                # We still need the anon key for initialization, but auth will use the JWT
                supabase_anon_key = os.environ.get("SUPABASE_ANON_KEY")
                
                # Create client with user's JWT token
                supabase_client = create_client(supabase_url, supabase_anon_key)
                supabase_client.auth.set_session(user_token)
                query = supabase_client.table("documents").select("id", count="exact").eq("source_document_id", actual_report_id).eq("document_type", "chat_message")
            else:
                # Fallback to service role key (with warning)
                logger.warning(f"No user token provided when counting chat history for report {actual_report_id}. Falling back to service role key.")
                query = self.supabase.client.table("documents").select("id", count="exact").eq("source_document_id", actual_report_id).eq("document_type", "chat_message")
            
            # Apply role filter if provided (role is now in content JSONB)
            if role_filter:
                query = query.eq("content->>role", role_filter)
            
            # Apply date filters if provided
            if date_from:
                query = query.gte("created_at", date_from)
            if date_to:
                query = query.lte("created_at", date_to)
            
            # Apply text search if provided
            if search_query:
                query = query.ilike("content", f"%{search_query}%")
            
            # Execute the query
            result = query.execute()
            
            if hasattr(result, "error") and result.error:
                logger.error(f"Error getting chat history count: {result.error}")
                return 0
            
            # Get the count from the result
            count = result.count if hasattr(result, "count") else 0
            return count
        
        except Exception as e:
            logger.error(f"Error getting chat history count: {e}")
            return 0
            
    async def get_total_pages(
        self,
        report_id: str,
        page_size: int = 20,
        role_filter: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        search_query: Optional[str] = None,
        user_token: str = None
    ) -> int:
        """Get the total number of pages for pagination.
        
        Args:
            report_id: ID of the report
            page_size: Number of messages per page
            role_filter: Filter by role (user, assistant, system)
            date_from: Filter by date from (ISO format)
            date_to: Filter by date to (ISO format)
            search_query: Search for text in content
            
        Returns:
            int: Total number of pages
        """
        # Get the total count of messages
        count = await self.get_chat_history_count(
            report_id=report_id,
            role_filter=role_filter,
            date_from=date_from,
            date_to=date_to,
            search_query=search_query,
            user_token=user_token
        )
        
        # Calculate the number of pages
        if count == 0 or page_size <= 0:
            return 1
        
        return (count + page_size - 1) // page_size
    
    async def generate_embedding(
        self, 
        text: str,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        report_id: Optional[str] = None
    ) -> Optional[List[float]]:
        """Generate embedding for a text.
        
        Args:
            text: Text to generate embedding for
            user_id: Optional user ID for monitoring
            tenant_id: Optional tenant ID for monitoring
            report_id: Optional report ID for monitoring
            
        Returns:
            List[float]: Embedding vector, or None if generation failed
        """
        logger.info("Generating embedding for query")
        
        if not self.api_key:
            raise ValueError("API key is required for generating embeddings")
        
        try:
            # Get the embedding service with centralized configuration
            embedding_service = get_embedding_service()
            
            # Create monitoring context for query embedding
            monitoring_context = None
            if user_id or tenant_id or report_id:
                monitoring_context = AIUsageContext(
                    user_id=user_id,
                    tenant_id=tenant_id,
                    project_id=report_id,
                    feature_id="pv_report_chat",
                    workflow_name="pv_report_workflow",
                    step_name="query_embedding",
                    environment="prod"
                )
            
            # Generate embedding using the embedding service
            embeddings = await embedding_service.generate_embeddings([text], monitoring_context)
            
            # Return the first (and only) embedding
            return embeddings[0] if embeddings and embeddings[0] is not None else None
        
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None
    
    async def retrieve_relevant_chunks(
        self, 
        report_id: str, 
        query: str,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        max_chunks: int = DEFAULT_MAX_CHUNKS
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant chunks using enhanced RAG with dual context retrieval.
        
        This method implements sophisticated RAG by retrieving chunks from:
        1. The primary PV report chunks
        2. Associated actionable insights chunks
        3. Using vector similarity search with fallback to keyword search
        
        Args:
            report_id: ID of the report (can be actual ID or session_id)
            query: Query to search for
            similarity_threshold: Minimum similarity score to include a chunk
            max_chunks: Maximum number of chunks to return
            
        Returns:
            List[Dict[str, Any]]: List of relevant chunks with enhanced context
        """
        logger.info(f"🔍 RAG: Retrieving relevant chunks for report identifier {report_id}")
        
        # First, resolve the report identifier to get the actual report data
        report_data = await resolve_report_identifier(report_id, self.user_token)
        if not report_data:
            logger.error(f"Cannot retrieve chunks: report not found with identifier {report_id}")
            return []
        
        # Use the actual report ID for querying
        actual_report_id = report_data['id']
        logger.info(f"🎯 RAG: Resolved report identifier {report_id} to actual ID {actual_report_id}")
        
        try:
            # ENHANCED RAG: Dual Context Retrieval
            all_chunks = []
            
            # 1. Retrieve chunks from the primary PV report
            logger.info(f"📊 RAG: Retrieving PV report chunks for {actual_report_id}")
            pv_chunks = await self._retrieve_document_chunks(
                actual_report_id, 
                query, 
                "pv_report",
                similarity_threshold, 
                max_chunks // 2  # Reserve half for PV report
            )
            
            # Add source context to PV chunks
            for chunk in pv_chunks:
                chunk["source_context"] = "pv_report"
                chunk["context_label"] = "Problem Validation Report"
            
            all_chunks.extend(pv_chunks)
            logger.info(f"✅ RAG: Retrieved {len(pv_chunks)} PV report chunks")
            
            # 2. Retrieve chunks from associated actionable insights
            logger.info(f"💡 RAG: Retrieving actionable insights chunks for {actual_report_id}")
            insights_chunks = await self._retrieve_actionable_insights_chunks(
                actual_report_id,
                query,
                similarity_threshold,
                max_chunks // 2  # Reserve half for insights
            )
            
            # Add source context to insights chunks
            for chunk in insights_chunks:
                chunk["source_context"] = "actionable_insights"
                chunk["context_label"] = "Actionable Insights"
            
            all_chunks.extend(insights_chunks)
            logger.info(f"✅ RAG: Retrieved {len(insights_chunks)} actionable insights chunks")
            
            # 3. Re-rank all chunks by similarity and limit to max_chunks
            all_chunks.sort(key=lambda x: x.get("similarity", 0), reverse=True)
            final_chunks = all_chunks[:max_chunks]
            
            logger.info(f"🚀 RAG: Final context includes {len(final_chunks)} chunks from dual sources")
            logger.info(f"📈 RAG: Context breakdown - PV: {len([c for c in final_chunks if c.get('source_context') == 'pv_report'])}, Insights: {len([c for c in final_chunks if c.get('source_context') == 'actionable_insights'])}")
            
            return final_chunks
            
        except Exception as e:
            logger.error(f"❌ RAG: Error in dual context retrieval: {e}")
            # Fallback to basic retrieval if enhanced RAG fails
            return await self._fallback_chunk_retrieval(actual_report_id, query, similarity_threshold, max_chunks)
    
    async def _retrieve_document_chunks(
        self,
        document_id: str,
        query: str,
        source_type: str,
        similarity_threshold: float,
        max_chunks: int
    ) -> List[Dict[str, Any]]:
        """Retrieve chunks from a specific document using vector search."""
        try:
            # Use the enhanced vector search service
            search_results = await search_chunks_with_fallback(
                report_id=document_id,
                query=query,
                similarity_threshold=similarity_threshold,
                max_chunks=max_chunks
            )
            
            # Convert ChunkSearchResult objects to dictionaries
            chunks = []
            for result in search_results:
                chunks.append({
                    "id": result.id,
                    "doc_id": document_id,
                    "chunk_index": result.chunk_index,
                    "content": result.content,
                    "metadata": result.metadata,
                    "similarity": result.similarity
                })
            
            return chunks
        
        except Exception as e:
            logger.error(f"Error retrieving chunks with fallback: {e}")
            
            # Last resort fallback: try direct database query without embeddings
            try:
                logger.info("Attempting last resort fallback with direct database query")
                
                # Extract keywords from query (simple approach)
                stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "with", "by", "about"}
                keywords = [word.lower() for word in query.split() if word.lower() not in stop_words]
                
                if not keywords:
                    return []
                
                # Use simple LIKE query for each keyword
                query_conditions = []
                for keyword in keywords[:3]:  # Limit to first 3 keywords
                    if len(keyword) > 2:  # Only use keywords with more than 2 characters
                        query_conditions.append(f"content ILIKE '%{keyword}%'")
                
                if not query_conditions:
                    return []
                
                # Build the query
                query_str = " OR ".join(query_conditions)
                
                # Execute the query using new chunks table schema
                result = self.supabase.client.table("chunks") \
                    .select("id, doc_id, chunk_index, content, metadata") \
                    .eq("doc_id", report_id) \
                    .filter(query_str) \
                    .limit(max_chunks) \
                    .execute()
                
                if hasattr(result, "error") and result.error:
                    logger.error(f"Error in last resort fallback: {result.error}")
                    return []
                
                # Add a placeholder similarity score
                for item in result.data:
                    item["similarity"] = 0.5  # Default similarity for keyword matches
                
                return result.data
                
            except Exception as fallback_error:
                logger.error(f"Last resort fallback also failed: {fallback_error}")
                return []
    
    async def _retrieve_actionable_insights_chunks(
        self,
        pv_report_id: str,
        query: str,
        similarity_threshold: float,
        max_chunks: int
    ) -> List[Dict[str, Any]]:
        """Retrieve chunks from actionable insights associated with a PV report."""
        try:
            # Find actionable insights documents linked to this PV report
            insights_query = self.supabase.client.table("documents") \
                .select("id") \
                .eq("source_type", "actionable_insights") \
                .contains("metadata", {"pv_report_id": pv_report_id})
            
            insights_response = insights_query.execute()
            
            if not insights_response.data:
                logger.info(f"💡 RAG: No actionable insights found for PV report {pv_report_id}")
                return []
            
            # Retrieve chunks from all associated insights documents
            all_insights_chunks = []
            
            for insight_doc in insights_response.data:
                insight_id = insight_doc["id"]
                logger.info(f"🔍 RAG: Searching chunks in actionable insights document {insight_id}")
                
                # Get chunks for this insights document
                insight_chunks = await self._retrieve_document_chunks(
                    insight_id,
                    query,
                    "actionable_insights",
                    similarity_threshold,
                    max_chunks  # Will be limited later
                )
                
                all_insights_chunks.extend(insight_chunks)
            
            # Sort by similarity and limit
            all_insights_chunks.sort(key=lambda x: x.get("similarity", 0), reverse=True)
            return all_insights_chunks[:max_chunks]
            
        except Exception as e:
            logger.error(f"❌ RAG: Error retrieving actionable insights chunks: {e}")
            return []
    
    async def _fallback_chunk_retrieval(
        self,
        report_id: str,
        query: str,
        similarity_threshold: float,
        max_chunks: int
    ) -> List[Dict[str, Any]]:
        """Fallback chunk retrieval using basic vector search."""
        try:
            logger.info(f"🔄 RAG: Using fallback chunk retrieval for {report_id}")
            
            # Use the basic search_chunks_with_fallback function
            search_results = await search_chunks_with_fallback(
                report_id=report_id,
                query=query,
                similarity_threshold=similarity_threshold,
                max_chunks=max_chunks
            )
            
            # Convert to dictionaries
            chunks = []
            for result in search_results:
                chunks.append({
                    "id": result.id,
                    "doc_id": report_id,
                    "chunk_index": result.chunk_index,
                    "content": result.content,
                    "metadata": result.metadata,
                    "similarity": result.similarity,
                    "source_context": "pv_report",
                    "context_label": "Problem Validation Report"
                })
            
            logger.info(f"🔄 RAG: Fallback retrieved {len(chunks)} chunks")
            return chunks
            
        except Exception as e:
            logger.error(f"❌ RAG: Fallback chunk retrieval failed: {e}")
            return []
    
    def format_context(self, chunks: List[Dict[str, Any]]) -> str:
        """Format chunks as enhanced context for the LLM with source attribution.
        
        Args:
            chunks: List of chunks with source context information
            
        Returns:
            str: Formatted context with source labels
        """
        if not chunks:
            return ""
        
        # Sort chunks by similarity score (highest first)
        sorted_chunks = sorted(chunks, key=lambda x: x.get("similarity", 0), reverse=True)
        
        # Group chunks by source context
        pv_chunks = [c for c in sorted_chunks if c.get("source_context") == "pv_report"]
        insights_chunks = [c for c in sorted_chunks if c.get("source_context") == "actionable_insights"]
        
        context_parts = ["ENHANCED RAG CONTEXT:"]
        citation_index = 1
        
        # Add PV report chunks first
        if pv_chunks:
            context_parts.append("\n📊 PROBLEM VALIDATION REPORT CONTEXT:")
            for chunk in pv_chunks:
                chunk_text = chunk.get("content", "").strip()
                similarity = chunk.get("similarity", 0)
                context_parts.append(f"[{citation_index}] (Similarity: {similarity:.3f}) {chunk_text}")
                citation_index += 1
        
        # Add actionable insights chunks
        if insights_chunks:
            context_parts.append("\n💡 ACTIONABLE INSIGHTS CONTEXT:")
            for chunk in insights_chunks:
                chunk_text = chunk.get("content", "").strip()
                similarity = chunk.get("similarity", 0)
                context_parts.append(f"[{citation_index}] (Similarity: {similarity:.3f}) {chunk_text}")
                citation_index += 1
        
        # Add context summary
        context_parts.append(f"\n📈 CONTEXT SUMMARY: {len(pv_chunks)} PV report chunks, {len(insights_chunks)} actionable insights chunks")
        
        return "\n\n".join(context_parts)
    
    def format_memory_context(self, memory_messages: List[Dict[str, Any]]) -> str:
        """Format conversation memory as context for the LLM.
        
        Args:
            memory_messages: List of memory messages
            
        Returns:
            str: Formatted memory context
        """
        if not memory_messages:
            return ""
        
        # Format conversation memory
        context_parts = ["CONVERSATION HISTORY:"]
        
        for message in memory_messages:
            role = message.get("role", "")
            content = message.get("content", "").strip()
            
            # Skip empty messages
            if not content:
                continue
                
            # Format based on role
            if role == "user":
                context_parts.append(f"User: {content}")
            elif role == "assistant":
                context_parts.append(f"Assistant: {content}")
            elif role == "system":
                context_parts.append(f"System: {content}")
        
        return "\n\n".join(context_parts)
    
    async def generate_response(
        self, 
        query: str, 
        context: str,
        web_search_enabled: bool = False,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        report_id: Optional[str] = None
    ) -> Optional[str]:
        """Generate a response using the LLM.
        
        Args:
            query: User query
            context: Context from retrieved chunks (includes conversation history)
            web_search_enabled: Whether to enable web search
            conversation_history: Optional conversation history for additional context
            user_id: Optional user ID for monitoring
            tenant_id: Optional tenant ID for monitoring
            report_id: Optional report ID for monitoring
            
        Returns:
            str: Generated response, or None if generation failed
        """
        logger.info("Generating response with OpenAI LLM")
        
        if not self.api_key:
            raise ValueError("API key is required for generating responses")
        
        # Construct enhanced system prompt for dual context RAG
        system_prompt = """
        You are an advanced AI assistant specialized in analyzing market validation reports and actionable insights using enhanced RAG (Retrieval-Augmented Generation).
        
        ENHANCED CONTEXT UNDERSTANDING:
        - You have access to DUAL CONTEXT from both Problem Validation Reports and Actionable Insights
        - Problem Validation Report context (📊) contains original research findings and market analysis
        - Actionable Insights context (💡) contains AI-generated strategic recommendations and implementation guidance
        
        CITATION REQUIREMENTS:
        - Always cite sources using [1], [2], etc. corresponding to the chunk numbers
        - Distinguish between PV report findings and actionable insights in your citations
        - Every piece of information must have proper attribution
        
        RESPONSE STRATEGY:
        - Synthesize information from both contexts to provide comprehensive answers
        - When discussing findings, cite PV report chunks
        - When discussing recommendations or next steps, prioritize actionable insights chunks
        - If information spans both contexts, acknowledge both sources
        
        CONVERSATION CONTINUITY:
        - Use conversation history to understand follow-up questions and maintain context
        - Reference previous exchanges when relevant
        
        LIMITATIONS:
        - If information is not available in either context, clearly state: "I don't have enough information to answer that question."
        - Don't make assumptions beyond what's provided in the context
        
        Format your response in clear, structured markdown with proper citations.
        """
        
        if web_search_enabled:
            system_prompt += "\nYou may also use web search to supplement your answers if needed."
        
        try:
            # Create messages for the chat completion
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"}
            ]
            
            # Call the OpenAI API with retry logic and concurrency control
            max_retries = 3
            base_delay = 1
            
            # Build kwargs - gpt-5-mini/o1/o3 models only support max_completion_tokens
            # They do NOT support: temperature, top_p, max_tokens
            model_name_lower = self.chat_model.lower()
            if "gpt-5" in model_name_lower or "o1" in model_name_lower or "o3" in model_name_lower:
                api_kwargs = {
                    "model": self.chat_model,
                    "messages": messages,
                    "max_completion_tokens": 4096  # Larger budget for detailed responses
                }
            else:
                api_kwargs = {
                    "model": self.chat_model,
                    "messages": messages,
                    "temperature": 0.2,
                    "max_tokens": 4096
                }
            
            # Prepare monitoring context
            monitoring_context = None
            if user_id or tenant_id or report_id:
                monitoring_context = AIUsageContext(
                    user_id=user_id,
                    tenant_id=tenant_id,
                    project_id=report_id,
                    feature_id="pv_report_chat",
                    workflow_name="pv_report_workflow",
                    step_name="chat_response_generation",
                    environment="prod"
                )
            
            chat_started_at = datetime.now()
            
            for attempt in range(max_retries):
                try:
                    # Use shared semaphore to limit concurrent Azure OpenAI requests
                    async with azure_openai_semaphore:
                        # Use centralized Responses API for gpt-5-mini
                        response = await self.llm_provider.generate_responses(messages)
                    break  # Success, exit retry loop
                    
                except Exception as e:
                    error_str = str(e)
                    # Check for rate limit (429) - retry with backoff
                    if "429" in error_str and attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)  # Exponential backoff
                        logger.warning(f"Rate limit hit (429), retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(delay)
                        continue
                    # Check for auth/permission error (401/403) - log and fail
                    elif "401" in error_str or "403" in error_str or "PermissionDenied" in error_str:
                        logger.error(f"Azure OpenAI permission/auth error: {error_str[:200]}")
                        logger.error("Check AZURE_OPENAI_API_KEY and deployment configuration")
                        raise e
                    else:
                        # Final attempt failed or other error
                        if attempt < max_retries - 1:
                            delay = base_delay * (2 ** attempt)
                            logger.warning(f"Request failed, retrying in {delay}s (attempt {attempt + 1}/{max_retries}): {error_str[:100]}")
                            await asyncio.sleep(delay)
                            continue
                        raise e
            
            # Extract the response text from LLMResponse object
            response_text = response.content
            
            if not response_text:
                raise ValueError("No response text in LLM result")
            
            # Record successful AI usage
            if monitoring_context:
                chat_finished_at = datetime.now()
                usage = response.usage
                try:
                    monitoring_service = get_monitoring_service()
                    asyncio.create_task(
                        monitoring_service.record_ai_usage(
                            context=monitoring_context,
                            provider="azure_openai" if self.provider == ModelProvider.AZURE_OPENAI else "openai",
                            model_name=self.chat_model,
                            operation_type="responses_api",
                            started_at=chat_started_at,
                            finished_at=chat_finished_at,
                            status="success",
                            prompt_tokens=usage.get('prompt_tokens') if usage else None,
                            completion_tokens=usage.get('completion_tokens') if usage else None,
                            total_tokens=usage.get('total_tokens') if usage else None,
                            extra_metadata={"step": "pv_report_chat"}
                        )
                    )
                except Exception as monitor_error:
                    logger.warning(f"Failed to record chat AI usage: {monitor_error}")
            
            return response_text
        
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            
            # Record error AI usage
            if monitoring_context:
                chat_finished_at = datetime.now()
                try:
                    monitoring_service = get_monitoring_service()
                    asyncio.create_task(
                        monitoring_service.record_ai_usage(
                            context=monitoring_context,
                            provider="azure_openai" if self.provider == ModelProvider.AZURE_OPENAI else "openai",
                            model_name=self.chat_model,
                            operation_type="responses_api",
                            started_at=chat_started_at,
                            finished_at=chat_finished_at,
                            status="error",
                            error_type=type(e).__name__,
                            extra_metadata={"step": "pv_report_chat", "error": str(e)[:200]}
                        )
                    )
                except Exception as monitor_error:
                    logger.warning(f"Failed to record chat AI usage error: {monitor_error}")
            
            return None
    
    def _update_conversation_history(
        self,
        conversation_history: List[Dict[str, str]],
        user_message: str,
        assistant_response: str
    ) -> List[Dict[str, str]]:
        """Update conversation history with new messages.
        
        Args:
            conversation_history: Current conversation history
            user_message: New user message
            assistant_response: New assistant response
            
        Returns:
            Updated conversation history with new exchange
        """
        # Add new messages
        updated_history = conversation_history + [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": assistant_response}
        ]
        
        # Keep only recent messages to manage context size (last 20 messages = 10 exchanges)
        max_history_messages = 20
        if len(updated_history) > max_history_messages:
            updated_history = updated_history[-max_history_messages:]
        
        logger.info(f"Updated conversation history: {len(updated_history)} messages (kept last {max_history_messages})")
        
        return updated_history
    
    async def delete_message(self, message_id: str) -> bool:
        """Delete a chat message from the database.
        
        Args:
            message_id: ID of the message to delete
            
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        logger.info(f"Deleting message with ID: {message_id}")
        
        try:
            # Delete from database
            result = self.supabase.client.table("documents").delete().eq("id", message_id).eq("document_type", "chat_message").execute()
            
            if hasattr(result, "error") and result.error:
                logger.error(f"Error deleting message: {result.error}")
                return False
            
            return True
        
        except Exception as e:
            logger.error(f"Error deleting message: {e}")
            return False
            
    async def get_latest_messages(
        self,
        report_id: str,
        limit: int = 20,
        include_metadata: bool = True
    ) -> List[ChatMessage]:
        """Get the latest messages for a report.
        
        Args:
            report_id: ID of the report
            limit: Maximum number of messages to return
            include_metadata: Whether to include metadata in the results
            
        Returns:
            List[ChatMessage]: List of latest chat messages
        """
        logger.info(f"Getting latest messages for report {report_id}")
        
        return await self.get_chat_history(
            report_id=report_id,
            limit=limit,
            sort_by="created_at",
            sort_order="desc",
            include_metadata=include_metadata
        )
        
    async def search_messages(
        self,
        report_id: str,
        search_query: str,
        limit: int = 20,
        offset: int = 0,
        include_metadata: bool = True
    ) -> List[ChatMessage]:
        """Search for messages in a report.
        
        Args:
            report_id: ID of the report
            search_query: Text to search for
            limit: Maximum number of messages to return
            offset: Offset for pagination
            include_metadata: Whether to include metadata in the results
            
        Returns:
            List[ChatMessage]: List of matching chat messages
        """
        logger.info(f"Searching messages for report {report_id}")
        
        return await self.get_chat_history(
            report_id=report_id,
            limit=limit,
            offset=offset,
            search_query=search_query,
            include_metadata=include_metadata
        )
    
    async def process_query(
        self, 
        report_id: str, 
        user_id: str, 
        query: str,
        web_search_enabled: bool = False,
        chat_session_id: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """Process a user query and generate a response.
        With fallback mechanisms for handling failures.
        
        Args:
            report_id: ID of the report (can be actual ID or session_id)
            user_id: ID of the user
            query: User query
            web_search_enabled: Whether to enable web search
            chat_session_id: Optional chat session ID for conversation memory
            conversation_history: Optional previous conversation messages for context
            
        Returns:
            Dict[str, Any]: Response data
        """
        logger.info(f"🚀🚀🚀 NEW CODE: Processing query for report {report_id} with BACKEND MEMORY")
        logger.info(f"Conversation history from frontend: {len(conversation_history) if conversation_history else 0} messages")
        
        try:
            # Get or create chat session for conversation memory
            chat_session_id = self.get_or_create_chat_session(report_id, user_id, chat_session_id)
            logger.info(f"Using chat session: {chat_session_id}")
            
            # BACKEND MEMORY: Load conversation history from database
            # Get last 10 messages (5 exchanges) for context
            # IMPORTANT: Load BEFORE storing current message to get previous conversation
            logger.info(f"📚 MEMORY: Loading conversation history from database for report {report_id}")
            logger.info(f"📚 MEMORY: Query parameters - limit=10, sort_order=desc, user_token={'present' if self.user_token else 'None'}")
            
            db_messages = await self.get_chat_history(
                report_id=report_id,
                limit=10,  # Last 10 messages (5 user + 5 assistant)
                sort_order="desc",  # Get most recent first
                user_token=self.user_token
            )
            
            logger.info(f"📚 MEMORY: get_chat_history returned {len(db_messages)} ChatMessage objects")
            logger.info(f"📚 MEMORY: Message types: {[type(msg).__name__ for msg in db_messages]}")
            
            # Reverse to get chronological order (oldest first)
            db_messages.reverse()
            
            # Convert ChatMessage objects to dict format for conversation history
            conversation_history = []
            for msg in db_messages:
                logger.info(f"📚 MEMORY: Converting message - role={msg.role}, content_length={len(msg.content)}")
                conversation_history.append({
                    "role": msg.role,
                    "content": msg.content
                })
            
            logger.info(f"📚 MEMORY: Loaded {len(conversation_history)} messages from database")
            if conversation_history:
                logger.info(f"📚 MEMORY: Oldest message: {conversation_history[0]['role']}: {conversation_history[0]['content'][:50]}...")
                logger.info(f"📚 MEMORY: Latest message: {conversation_history[-1]['role']}: {conversation_history[-1]['content'][:50]}...")
            else:
                logger.warning(f"📚 MEMORY: No previous messages found in database for report {report_id}")
            
            # Store user message
            user_message_id = await self.store_message(
                report_id=report_id,
                user_id=user_id,
                role="user",
                content=query
            )
            
            # Add user query to conversation memory
            self.add_to_conversation_memory(chat_session_id, "user", query)
            
            if not user_message_id:
                return {
                    "success": False,
                    "error": "Failed to store user message"
                }
            
            # Retrieve relevant chunks with fallback
            chunks = await self.retrieve_relevant_chunks(report_id, query)
            
            if not chunks:
                # Store system message about no chunks found
                await self.store_message(
                    report_id=report_id,
                    user_id=user_id,
                    role="system",
                    content="No relevant chunks found for query",
                    metadata={"query": query}
                )
                
                # Generate a fallback response when no chunks are found
                fallback_response = (
                    "I couldn't find any relevant information in your report to answer this question. "
                    "Could you try rephrasing your question or asking about a different topic covered in the report?"
                )
                
                # Store fallback assistant message
                fallback_message_id = await self.store_message(
                    report_id=report_id,
                    user_id=user_id,
                    role="assistant",
                    content=fallback_response,
                    metadata={
                        "fallback": True,
                        "reason": "no_chunks_found",
                        "query": query
                    }
                )
                
                # Update conversation history for no chunks fallback
                updated_history = self._update_conversation_history(
                    conversation_history=conversation_history,
                    user_message=query,
                    assistant_response=fallback_response
                )
                
                return {
                    "success": True,  # Return success to avoid error display
                    "message_id": fallback_message_id,
                    "response": fallback_response,
                    "chunks": [],
                    "fallback": True,
                    "conversation_history": updated_history
                }
            
            # Format context from chunks
            chunks_context = self.format_context(chunks)
            
            # Build conversation history context from provided history
            history_context = ""
            if conversation_history:
                logger.info(f"Building context from {len(conversation_history)} conversation messages")
                recent_history = conversation_history[-10:]  # Keep last 10 messages
                history_parts = []
                for msg in recent_history:
                    role = msg.get("role", "")
                    content = msg.get("content", "").strip()
                    if content:
                        if role == "user":
                            history_parts.append(f"User: {content}")
                        elif role == "assistant":
                            history_parts.append(f"Assistant: {content}")
                
                if history_parts:
                    history_context = "\n\n=== CONVERSATION HISTORY ===\n" + "\n\n".join(history_parts)
                    logger.info(f"Built conversation history context: {len(history_context)} characters")
            
            # Try to generate response with LLM
            try:
                # Combine chunks context with conversation history
                combined_context = f"{chunks_context}\n\n{history_context}".strip()
                logger.info(f"Total context length: {len(combined_context)} characters")
                response = await self.generate_response(
                    query, combined_context, web_search_enabled, conversation_history,
                    user_id=user_id, report_id=report_id
                )
                
                if not response:
                    raise ValueError("Empty response from LLM")
                    
                is_fallback = False
                
            except Exception as llm_error:
                # LLM failed, generate a simple fallback response
                logger.error(f"LLM failed, using fallback response: {llm_error}")
                
                # Create a simple response that references the chunks
                response = (
                    "I'm having trouble generating a detailed response right now. "
                    "However, I found some relevant information in your report that might help:\n\n"
                )
                
                # Add excerpts from the top chunks
                for i, chunk in enumerate(chunks[:3]):  # Use up to 3 chunks
                    chunk_text = chunk.get("content", "").strip()
                    # Truncate long chunks
                    if len(chunk_text) > 200:
                        chunk_text = chunk_text[:200] + "..."
                    response += f"[{i+1}] {chunk_text}\n\n"
                
                response += (
                    "Please check these sections of your report for more information. "
                    "If you have more specific questions about these sections, feel free to ask."
                )
                
                is_fallback = True
            
            # Store assistant message
            metadata = {
                "chunks": [chunk.get("id") for chunk in chunks],
                "web_search_enabled": web_search_enabled,
                "chat_session_id": chat_session_id
            }
            
            if is_fallback:
                metadata["fallback"] = True
                metadata["reason"] = "llm_error"
            
            assistant_message_id = await self.store_message(
                report_id=report_id,
                user_id=user_id,
                role="assistant",
                content=response,
                metadata=metadata
            )
            
            # Add assistant response to conversation memory
            self.add_to_conversation_memory(chat_session_id, "assistant", response)
            
            # Update conversation history with new exchange
            updated_history = self._update_conversation_history(
                conversation_history=conversation_history,
                user_message=query,
                assistant_response=response
            )
            
            logger.info(f"Updated conversation history: {len(updated_history)} total messages")
            
            # Invalidate chat history cache for this report
            try:
                from .cache_service import invalidate_by_tag
                invalidate_by_tag("chat_history")
            except ImportError:
                logger.warning("Cache service not available, could not invalidate cache")
            
            if not assistant_message_id:
                return {
                    "success": False,
                    "error": "Failed to store assistant message"
                }
            
            return {
                "success": True,
                "message_id": assistant_message_id,
                "response": response,
                "chunks": chunks,
                "fallback": is_fallback,
                "chat_session_id": chat_session_id,
                "conversation_history": updated_history
            }
        
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            
            # Ultimate fallback - if everything else fails
            try:
                # Generate a generic fallback response
                fallback_response = (
                    "I'm sorry, but I encountered an error while processing your question. "
                    "This could be due to temporary system issues. "
                    "Please try asking your question again, or try a different question about your report."
                )
                
                # Store fallback assistant message
                fallback_message_id = await self.store_message(
                    report_id=report_id,
                    user_id=user_id,
                    role="assistant",
                    content=fallback_response,
                    metadata={
                        "fallback": True,
                        "reason": "system_error",
                        "error": str(e)
                    }
                )
                
                # Update conversation history for ultimate fallback
                updated_history = self._update_conversation_history(
                    conversation_history=conversation_history,
                    user_message=query,
                    assistant_response=fallback_response
                )
                
                return {
                    "success": True,  # Return success to avoid error display
                    "message_id": fallback_message_id,
                    "response": fallback_response,
                    "chunks": [],
                    "fallback": True,
                    "conversation_history": updated_history
                }
                
            except Exception as fallback_error:
                logger.error(f"Even fallback failed: {fallback_error}")
                return {
                    "success": False,
                    "error": "System error occurred. Please try again later.",
                    "conversation_history": conversation_history  # Return original history on complete failure
                }
            


# Singleton instance
_report_chat_service = None


def get_report_chat_service(api_key: Optional[str] = None, user_token: Optional[str] = None) -> ReportChatService:
    """Get an instance of the report chat service.
    
    Args:
        api_key: Optional API key override (normally not needed - uses Azure config)
        user_token: Optional JWT token for user authentication (enables RLS)
        
    Returns:
        ReportChatService: The report chat service
    """
    # DON'T override API key - let ReportChatService use get_client_config() 
    # which returns the correct Azure OpenAI API key
    
    # Create a new instance with user token (don't use singleton for user-specific instances)
    if user_token:
        logger.info("Creating user-authenticated report chat service")
        return ReportChatService(api_key=api_key, user_token=user_token)
    
    # Use singleton for service-role instances
    global _report_chat_service
    if _report_chat_service is None:
        logger.info("Initializing report chat service")
        _report_chat_service = ReportChatService(api_key=api_key)
    return _report_chat_service


async def process_query(report_id: str, user_id: str, query: str, web_search_enabled: bool = False, chat_session_id: Optional[str] = None, conversation_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
    """Process a user query and generate a response.
    
    Args:
        report_id: ID of the report
        user_id: ID of the user
        query: User query
        web_search_enabled: Whether to enable web search
        chat_session_id: Optional chat session ID for conversation memory
        conversation_history: Optional conversation history (ignored - loaded from database)
        
    Returns:
        Dict[str, Any]: Response data
    """
    service = get_report_chat_service()
    return await service.process_query(report_id, user_id, query, web_search_enabled, chat_session_id, conversation_history)