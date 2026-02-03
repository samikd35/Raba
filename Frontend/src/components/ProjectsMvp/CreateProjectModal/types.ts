/**
 * TypeScript interfaces for CreateProjectModal components
 */

export interface Question {
  id: string;
  priority: string;
  category: string;
  question: string;
  context: string | null;
  required: boolean;
}

export interface BootstrapResponse {
  success: boolean;
  project_id: string;
  project_name: string;
  context_status: string;
  message: string;
}

export interface QuestionsResponse {
  success: boolean;
  project_id: string;
  context_status: string;
  questions: Question[];
  message: string;
}

export interface StatusResponse {
  success: boolean;
  project_id: string;
  project_name: string;
  context_mode: string;
  context_status: string;
  context_version: number;
  created_at: string;
  updated_at: string;
}

export interface ResearchSource {
  n: number;
  url: string;
  title: string;
  snippet: string;
  publisher: string;
  captured_at: string;
}

export interface EnhancedContextDraft {
  IdeaSummary: string;
  CustomerSegments: string[];
  Problem: {
    who: string;
    what: string;
    where: string;
    why_now: string;
  };
  SolutionOverview: string;
  Differentiation: string[];
  BusinessModelSeeds: {
    cost_drivers?: string[];
    revenue_model?: string;
    pricing_hypothesis?: string;
  };
  AlternativesAndCompetition: {
    direct_competitors?: string[];
    indirect_alternatives?: string[];
    differentiation_summary?: string;
  };
  ConstraintsAndRisks: string[];
  Research: {
    sources?: ResearchSource[];
    summary?: string;
    market_context?: string;
    adoption_factors?: string;
    problem_validation?: string;
    solution_landscape?: string;
  };
}

export interface EnhancedContext {
  version: number;
  draft: EnhancedContextDraft;
  confirmed: EnhancedContextDraft | null;
  metadata: {
    context_mode: string;
    invariants: {
      customer_segment: string;
      geography: string;
      core_problem: string;
      core_solution_type: string;
    };
    created_at: string;
    updated_at: string;
  };
}

export interface EnhancedContextResponse {
  success: boolean;
  project_id: string;
  context_status: string;
  enhanced_context: EnhancedContext;
  message: string;
}

export type ModalStep = 'input' | 'processing' | 'questions' | 'processing-context' | 'context-ready';

export interface EditableContext {
  ideaSummary: string;
  customerSegments: string[];
  problem: { who: string; what: string; where: string; why_now: string };
  solutionOverview: string;
  differentiation: string[];
  businessModelSeeds: { revenue_model: string; pricing_hypothesis: string; cost_drivers: string[] };
  constraintsAndRisks: string[];
}

export interface CreateProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
  onProjectCreated?: () => void;
}
