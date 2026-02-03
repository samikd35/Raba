export interface MarketValidationData {
  selectedProblemStatement: ProblemStatement;
  problemIndex: number;
  originalIdea: string;
  contextAnalysis?: {
    persona: string;
    industry: string;
    geography: string;
    delivery_mode: string;
  };
  persona: string;
  industry: string;
  geography: string;
  delivery_mode: string;
  sessionId?: string;
  reportId?: string;
  allProblemStatements?: ProblemStatement[];
}

export interface ProblemStatement {
  statement: string;
  assumptions: string[];
}

export interface ClarificationQuestion {
  id: string;
  question: string;
  question_type: "text" | "multiple_choice" | "boolean";
  options?: string[] | null;
  required: boolean;
}

export interface WorkflowResponse {
  session_id: string;
  status: "started" | "waiting_for_clarification" | "processing" | "completed" | "error";
  progress: number;
  message: string;
  clarification_questions: ClarificationQuestion[] | null;
  last_updated: string;
  error: string | null;
  progress_details: string | null;
  estimated_completion: string | null;
}

export interface AnswerPayload {
  answers: Record<string, string>;
}

export interface ReportSection {
  title: string;
  content: string;
  subsections?: ReportSection[];
}

export interface ReportSource {
  number: number;
  source_url: string;
  source_title: string;
}

export interface ReportContent {
  title: string;
  executive_summary: string;
  industry_analysis: string;
  challenges_analysis: string;
  recommendations: string;
  sources: ReportSource[];
  tenant_id: string;
}

export interface ReportResponse {
  session_id: string;
  report_id: string;
  query: string;
  title: string;
  executive_summary: string;
  sections: any[];
  report: ReportContent;
  status: string;
  generated_at: string;
  generation_time_seconds: number | null;
  word_count: number | null;
  quality_score: number | null;
  validation_score?: number;
  insights_available?: boolean;
  insights_generated_at?: string;
  insights_status?: 'pending' | 'processing' | 'completed' | 'failed';
}

export interface EnhancedValidationResultsData {
  sessionId: string;
  reportId?: string;
  report: ReportResponse;
  validationData?: MarketValidationData;
  metadata?: {
    generatedAt: string;
    version: string;
    userId?: string;
    tenant_id?: string;
  };
}

export interface ChatMessage {
  id: string;
  from: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  type?: 'question' | 'answer' | 'system' | 'report';
  questionId?: string;
}

export interface ValidationStore {
  userId: string;
  sessionId: string | null;
  reportId: string | null;
  validationData: MarketValidationData | null;
  currentAnswers: Record<string, string>;
  setUserId: (id: string) => void;
  setSessionId: (id: string) => void;
  setReportId: (id: string) => void;
  setValidationData: (data: MarketValidationData) => void;
  setAnswer: (questionId: string, answer: string) => void;
  clearAnswers: () => void;
  reset: () => void;
}
