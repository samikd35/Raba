// Chat Message Interface
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  isError?: boolean;
  metadata?: any;
}

// Chat Response Interface
export interface ChatResponse {
  id?: string;
  content?: string;
  answer?: string;
  success: boolean;
  error?: string;
  chat_session_id?: string;
  metadata?: any;
  sources?: Array<{
    type: string;
    filename?: string;
    source_type?: string;
    section_count?: number;
    chunk_count?: number;
    insight_count?: number;
    includes?: any;
  }>;
  context_used?: {
    research_chunks?: number;
    report_chunks?: number;
    critique_chunks?: number;
    thread_id?: string;
  };
  thread_id?: string;
  assistant_message?: {
    id: string;
    content: string;
    created_at: string;
    metadata?: any;
  };
  user_message?: {
    id: string;
    content: string;
    created_at: string;
  };
  conversation_history?: Array<{
    role: string;
    content: string;
  }>;
  timestamp?: string;
  message?: string;
}

// New Types for Threaded Chat
export interface ChatThread {
  id: string;
  project_id: string;
  title: string;
  status: string;
  created_at: string;
  updated_at: string;
  last_message_at: string | null;
  message_count: number | null;
  org_owner_access: boolean;
}

export interface ChatThreadResponse {
  threads: ChatThread[];
  total_count: number;
  has_more: boolean;
}

export interface ProjectChatDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  projectId: string; // Required for project chat
  organizationId?: string; // Optional, can be derived or passed
}

// Keeping original props for backward compatibility if needed, 
// but we might transition away from them or make them optional
export interface ChatDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  projectId: string | null;
  organizationId?: string; // Added for the new implementation
  title?: string;
  apiEndpoint?: string;
  placeholder?: string;
  emptyStateTitle?: string;
  emptyStateDescription?: string;
  suggestedQuestions?: string[];
  selectedPersona?: string | null;
}

// Chat Markdown Renderer Props Interface
export interface ChatMarkdownRendererProps {
  content: string;
}
