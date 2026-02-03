"""
Data Models for Project Chat Feature

Contains Pydantic models for:
- LangGraph state schema
- Thread and message entities
- Thread memory structures
- Evidence and citations
- API request/response models
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, TypedDict, Union

from pydantic import BaseModel, Field


# ============================================================================
# ENUMS
# ============================================================================

class ThreadStatus(str, Enum):
    """Status of a chat thread."""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class MessageRole(str, Enum):
    """Role of a message in the thread."""
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    SYSTEM = "system"


class ChatIntent(str, Enum):
    """Intent classification for routing."""
    PROJECT_ONLY = "PROJECT_ONLY"
    PROJECT_PLUS_WEB = "PROJECT_PLUS_WEB"
    WEB_ONLY = "WEB_ONLY"
    META = "META"


class EvidenceGrade(str, Enum):
    """Grade of evidence sufficiency."""
    SUFFICIENT = "SUFFICIENT"
    PARTIAL = "PARTIAL"
    INSUFFICIENT = "INSUFFICIENT"


# ============================================================================
# EVIDENCE MODELS
# ============================================================================

class ProjectEvidence(BaseModel):
    """Evidence retrieved from project artifacts via RAG."""
    chunk_id: str = Field(..., description="Database ID of the chunk")
    content: str = Field(..., description="Text content of the chunk")
    artifact_type: str = Field(..., description="Type of artifact (e.g., vmp_hypothesis)")
    section: Optional[str] = Field(None, description="Section within artifact")
    chunk_index: int = Field(..., description="Index of chunk within artifact")
    score: float = Field(..., description="Similarity score (0-1)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class WebEvidence(BaseModel):
    """Evidence extracted from web search results."""
    claim: str = Field(..., description="The factual claim extracted")
    snippet: str = Field(..., description="Supporting text snippet")
    url: str = Field(..., description="Source URL")
    title: str = Field(..., description="Page title")
    domain: str = Field(..., description="Source domain")
    published_at: Optional[str] = Field(None, description="Publication date if available")
    fetched_at: str = Field(..., description="When the page was fetched (ISO timestamp)")


# ============================================================================
# CITATION MODELS
# ============================================================================

class InternalCitation(BaseModel):
    """Citation for project artifact evidence."""
    type: Literal["internal"] = "internal"
    ref_id: str = Field(..., description="Reference ID (e.g., P1, P2)")
    artifact_type: str = Field(..., description="Type of artifact")
    chunk_id: str = Field(..., description="Database chunk ID")
    version: Optional[int] = Field(None, description="Artifact version for auditability")
    snippet: Optional[str] = Field(None, description="Evidence snippet (truncated)")
    score: float = Field(..., description="Relevance score")


class ExternalCitation(BaseModel):
    """Citation for web evidence."""
    type: Literal["external"] = "external"
    ref_id: str = Field(..., description="Reference ID (e.g., W1, W2)")
    url: str = Field(..., description="Source URL")
    title: str = Field(..., description="Page title")
    domain: str = Field(..., description="Source domain")
    snippet: Optional[str] = Field(None, description="Evidence snippet")
    fetched_at: str = Field(..., description="Fetch timestamp (ISO)")
    published_at: Optional[str] = Field(None, description="Publication date if known")


# Union type for citations
Citation = Union[InternalCitation, ExternalCitation]


# ============================================================================
# THREAD MEMORY MODELS
# ============================================================================

class ThreadMemory(BaseModel):
    """Thread memory for continuity without replaying full history."""
    running_summary: Optional[str] = Field(
        None, 
        description="Compact summary of the thread so far (5-10 lines)"
    )
    pinned_facts: List[str] = Field(
        default_factory=list,
        description="User-validated stable facts/preferences/decisions"
    )
    open_loops: List[str] = Field(
        default_factory=list,
        description="Unanswered questions, pending decisions, requested follow-ups"
    )
    last_context_refs: Dict[str, Any] = Field(
        default_factory=dict,
        description="Last used project chunks and web sources for traceability"
    )


class MemoryPatch(BaseModel):
    """Patch to update thread memory after a turn."""
    new_summary: Optional[str] = Field(None, description="Updated running summary")
    pinned_facts_add: List[str] = Field(default_factory=list, description="Facts to add")
    pinned_facts_remove: List[str] = Field(default_factory=list, description="Facts to remove")
    open_loops_add: List[str] = Field(default_factory=list, description="Open loops to add")
    open_loops_remove: List[str] = Field(default_factory=list, description="Open loops resolved")


# ============================================================================
# TOOL TRACE MODEL (for audit/debug)
# ============================================================================

class ToolTrace(BaseModel):
    """Audit trace of tools/retrievals used for a response."""
    intent: Optional[str] = Field(None, description="Classified intent")
    rewritten_query: Optional[str] = Field(None, description="Query after rewrite")
    retrieval_chunk_ids: List[str] = Field(default_factory=list, description="Retrieved chunk IDs")
    retrieval_scores: List[float] = Field(default_factory=list, description="Retrieval scores")
    evidence_grade: Optional[str] = Field(None, description="Evidence sufficiency grade")
    web_queries: List[str] = Field(default_factory=list, description="Web search queries executed")
    web_urls_fetched: List[str] = Field(default_factory=list, description="URLs fetched")
    llm_calls: int = Field(0, description="Number of LLM calls made")
    total_tokens: Optional[int] = Field(None, description="Total tokens used")
    latency_ms: Optional[int] = Field(None, description="Total latency in milliseconds")


# ============================================================================
# LANGGRAPH STATE SCHEMA
# ============================================================================

class ChatState(TypedDict, total=False):
    """
    LangGraph state schema for the chat workflow.
    
    This TypedDict carries all data across nodes in the workflow.
    Fields are optional (total=False) to allow incremental population.
    """
    # Identifiers
    project_id: str
    thread_id: str
    user_id: str
    tenant_id: str
    
    # Input
    user_message: str
    
    # Thread Context (loaded from DB)
    messages_window: List[Dict[str, str]]  # Last N messages [{role, content}]
    thread_summary: str
    pinned_facts: List[str]
    open_loops: List[str]
    
    # Intent Routing
    intent: str  # ChatIntent value
    needs_clarification: bool
    clarifying_questions: List[str]
    
    # Query Processing
    rewritten_query: str
    query_filters: Dict[str, Any]  # Optional artifact type filters
    
    # Project Evidence (from RAG)
    project_evidence: List[Dict[str, Any]]  # ProjectEvidence as dicts
    evidence_grade: str  # EvidenceGrade value
    missing_info: List[str]  # What's missing if evidence is insufficient
    
    # Web Evidence (if needed)
    web_plan_queries: List[str]
    web_plan_what_to_extract: List[str]
    web_evidence: List[Dict[str, Any]]  # WebEvidence as dicts
    
    # Response Generation
    answer_text: str
    citations: List[Dict[str, Any]]  # Citation objects as dicts
    follow_ups: List[str]  # Suggested follow-up questions
    
    # Memory Update
    memory_patch: Dict[str, Any]  # MemoryPatch as dict
    
    # Audit/Debug
    tool_trace: Dict[str, Any]  # ToolTrace as dict
    
    # Error Handling
    error: Optional[str]
    error_stage: Optional[str]


# ============================================================================
# DATABASE ENTITY MODELS
# ============================================================================

class ChatThread(BaseModel):
    """Chat thread entity from database."""
    id: str
    project_id: str
    tenant_id: str
    user_id: str
    title: Optional[str] = None
    status: ThreadStatus = ThreadStatus.ACTIVE
    created_at: datetime
    updated_at: datetime
    last_message_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChatMessage(BaseModel):
    """Chat message entity from database."""
    id: str
    thread_id: str
    role: MessageRole
    content: str
    citations: List[Citation] = Field(default_factory=list)
    tool_trace: Optional[ToolTrace] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ChatThreadMemoryRecord(BaseModel):
    """Thread memory record from database."""
    id: str
    thread_id: str
    running_summary: Optional[str] = None
    pinned_facts: List[str] = Field(default_factory=list)
    open_loops: List[str] = Field(default_factory=list)
    last_context_refs: Dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime


# ============================================================================
# API REQUEST MODELS
# ============================================================================

class CreateThreadRequest(BaseModel):
    """Request to create a new chat thread."""
    title: Optional[str] = Field(None, max_length=200, description="Optional thread title")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Optional metadata")


class PostMessageRequest(BaseModel):
    """Request to post a user message and get assistant response."""
    content: str = Field(..., min_length=1, max_length=10000, description="User message content")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Optional metadata")


class ListThreadsParams(BaseModel):
    """Query parameters for listing threads."""
    status: Optional[ThreadStatus] = Field(None, description="Filter by status")
    limit: int = Field(20, ge=1, le=100, description="Max threads to return")
    offset: int = Field(0, ge=0, description="Offset for pagination")


class ListMessagesParams(BaseModel):
    """Query parameters for listing messages."""
    limit: int = Field(50, ge=1, le=200, description="Max messages to return")
    cursor: Optional[str] = Field(None, description="Cursor for pagination (message ID)")
    order: Literal["asc", "desc"] = Field("desc", description="Sort order by created_at")


# ============================================================================
# API RESPONSE MODELS
# ============================================================================

class ThreadResponse(BaseModel):
    """Response containing thread data."""
    id: str
    project_id: str
    title: Optional[str]
    status: ThreadStatus
    created_at: datetime
    updated_at: datetime
    last_message_at: Optional[datetime]
    message_count: Optional[int] = None


class ThreadListResponse(BaseModel):
    """Response containing list of threads."""
    threads: List[ThreadResponse]
    total_count: int
    has_more: bool


class MessageResponse(BaseModel):
    """Response containing message data."""
    id: str
    thread_id: str
    role: MessageRole
    content: str
    citations: List[Citation] = Field(default_factory=list)
    created_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AssistantMessageResponse(BaseModel):
    """Response after posting a user message - includes assistant reply."""
    user_message: MessageResponse
    assistant_message: MessageResponse
    thread_id: str
    citations: List[Citation] = Field(default_factory=list)
    follow_ups: List[str] = Field(default_factory=list)
    tool_trace: Optional[ToolTrace] = None


class MessageListResponse(BaseModel):
    """Response containing list of messages."""
    messages: List[MessageResponse]
    has_more: bool
    next_cursor: Optional[str] = None


class ThreadMemoryResponse(BaseModel):
    """Response containing thread memory state (debug endpoint)."""
    thread_id: str
    running_summary: Optional[str]
    pinned_facts: List[str]
    open_loops: List[str]
    last_context_refs: Dict[str, Any]
    updated_at: datetime


# ============================================================================
# CONFIGURATION MODELS
# ============================================================================

class ChatConfig(BaseModel):
    """Configuration for chat behavior."""
    messages_window_size: int = Field(5, description="Recent messages to include in context")
    max_project_chunks: int = Field(10, description="Top-K chunks to retrieve")
    similarity_threshold: float = Field(0.3, description="Minimum relevance score")
    max_web_queries: int = Field(6, description="Maximum web search queries")
    max_web_results_per_query: int = Field(5, description="Results per web search")
    memory_update_frequency: int = Field(1, description="Update memory every N turns")
    max_summary_length: int = Field(500, description="Max chars for running summary")
    max_pinned_facts: int = Field(10, description="Maximum pinned facts to keep")
    max_open_loops: int = Field(5, description="Maximum open loops to track")
    answer_max_tokens: int = Field(2000, description="Max tokens for answer generation")
    temperature: float = Field(0.2, description="LLM temperature for answers")


# Default configuration
DEFAULT_CHAT_CONFIG = ChatConfig()
