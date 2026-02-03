// Chat Message Interface
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  isError?: boolean;
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
  };
  conversation_history?: Array<{
    role: string;
    content: string;
  }>;
  timestamp?: string;
  message?: string;
}

// Chat Drawer Props Interface
export interface ChatDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  projectId: string | null;
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
