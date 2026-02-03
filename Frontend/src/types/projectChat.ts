/**
 * Project Chat Types
 * TypeScript interfaces for the MAV (Market Analysis Validator) chat system
 */

// Thread status types
export type ThreadStatus = 'active' | 'archived' | 'deleted';

// Message roles
export type MessageRole = 'user' | 'assistant';

// ============================================
// Citation Types
// ============================================

export interface InternalCitation {
    type: 'internal';
    ref_id: string;
    artifact_type: string;
    chunk_id: string;
    version: number;
    snippet: string;
    score: number;
}

export interface ExternalCitation {
    type: 'external';
    ref_id: string;
    url: string;
    title: string;
    domain: string;
    snippet: string;
    fetched_at: string;
    published_at: string;
}

export type Citation = InternalCitation | ExternalCitation;

// ============================================
// Thread Entity
// ============================================

export interface ChatThread {
    id: string;
    project_id: string;
    title: string;
    status: ThreadStatus;
    created_at: string;
    updated_at: string;
    last_message_at: string | null;
    message_count: number | null;
}

// ============================================
// Message Entity
// ============================================

export interface ChatThreadMessage {
    id: string;
    thread_id: string;
    role: MessageRole;
    content: string;
    citations: Citation[];
    created_at: string;
    metadata: Record<string, unknown>;
}

// ============================================
// API Request Types
// ============================================

export interface CreateThreadRequest {
    title: string;
    metadata?: Record<string, unknown>;
}

export interface PostMessageRequest {
    content: string;
    metadata?: Record<string, unknown>;
}

export interface ListThreadsParams {
    status?: ThreadStatus;
    limit?: number;
    offset?: number;
}

export interface GetMessagesParams {
    limit?: number;
    cursor?: string;
    order?: 'asc' | 'desc';
}

// ============================================
// API Response Types
// ============================================

export interface ThreadListResponse {
    threads: ChatThread[];
    total_count: number;
    has_more: boolean;
}

export interface MessageListResponse {
    messages: ChatThreadMessage[];
    has_more: boolean;
    next_cursor: string | null;
}

export interface ToolTrace {
    intent: string;
    rewritten_query: string;
    retrieval_chunk_ids: string[];
    retrieval_scores: number[];
    evidence_grade: string;
    web_queries: string[];
    web_urls_fetched: string[];
    llm_calls: number;
    total_tokens: number;
    latency_ms: number;
}

export interface PostMessageResponse {
    user_message: ChatThreadMessage;
    assistant_message: ChatThreadMessage;
    thread_id: string;
    citations: Citation[];
    follow_ups: string[];
    tool_trace: ToolTrace;
}

// ============================================
// UI State Types
// ============================================

export type ChatStatus =
    | 'idle'
    | 'loading_threads'
    | 'creating_thread'
    | 'loading_messages'
    | 'ready'
    | 'sending'
    | 'error';

export interface ProjectChatState {
    status: ChatStatus;
    threads: ChatThread[];
    activeThread: ChatThread | null;
    messages: ChatThreadMessage[];
    hasMoreMessages: boolean;
    messageCursor: string | null;
    followUpSuggestions: string[];
    error: string | null;
    isHistoryOpen: boolean;
}

// ============================================
// Action Types for Reducer
// ============================================

export type ProjectChatAction =
    | { type: 'RESET' }
    | { type: 'SET_LOADING'; payload: ChatStatus }
    | { type: 'SET_ERROR'; payload: string }
    | { type: 'CLEAR_ERROR' }
    | { type: 'SET_THREADS'; payload: ChatThread[] }
    | { type: 'ADD_THREAD'; payload: ChatThread }
    | { type: 'SET_ACTIVE_THREAD'; payload: ChatThread }
    | { type: 'REMOVE_THREAD'; payload: string }
    | { type: 'SET_MESSAGES'; payload: { messages: ChatThreadMessage[]; hasMore: boolean; cursor: string | null } }
    | { type: 'PREPEND_MESSAGES'; payload: { messages: ChatThreadMessage[]; hasMore: boolean; cursor: string | null } }
    | { type: 'ADD_MESSAGE'; payload: ChatThreadMessage }
    | { type: 'ADD_ASSISTANT_MESSAGE'; payload: { assistantMessage: ChatThreadMessage; followUps: string[] } }
    | { type: 'ADD_MESSAGES'; payload: { userMessage: ChatThreadMessage; assistantMessage: ChatThreadMessage; followUps: string[] } }
    | { type: 'SET_FOLLOW_UPS'; payload: string[] }
    | { type: 'TOGGLE_HISTORY'; payload?: boolean }
    | { type: 'SET_READY' };
