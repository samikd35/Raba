/**
 * TypeScript interfaces for GeneratePRDModal components
 */

// API Request Types
export interface AMRGRunRequest {
  research_mode: 'auto' | 'manual';
  force_regenerate: boolean;
}

// API Response Types
export interface TopTemplate {
  code: string;
  name: string;
  confidence: number;
  rationale: string;
}

export interface CoarseRouting {
  top_templates: TopTemplate[];
  confidence_threshold_met: boolean;
  routing_rationale: string;
}

export interface AMRGQuestion {
  q_index: number;
  question_text: string;
  category: string;
  purpose: string;
}

export interface AMRGRunResponse {
  success: boolean;
  run_id: string;
  status: string;
  message: string;
  coarse_routing: CoarseRouting;
  questions: AMRGQuestion[];
  estimated_completion_seconds: number;
}

// Missing Artifacts Error Response
export interface ArtifactDetail {
  artifact_name: string;
  description: string;
  how_to_generate: string;
}

export interface MissingArtifactsError {
  success: false;
  error_code: 'MISSING_REQUIRED_ARTIFACTS';
  message: string;
  missing_artifacts: string[];
  artifact_details: ArtifactDetail[];
}

// Modal Step Types
export type GeneratePRDStep = 
  | 'initial' 
  | 'processing' 
  | 'questions'
  | 'generating-prd'
  | 'missing-artifacts' 
  | 'error';

// Component Props
export interface GeneratePRDModalProps {
  isOpen: boolean;
  onClose: () => void;
  projectId: string;
  onPRDGenerated?: () => void;
}

export interface InitialStepProps {
  onStartGeneration: () => void;
  isSubmitting: boolean;
}

export interface ProcessingStepProps {
  message: string;
}

export interface QuestionsStepProps {
  questions: AMRGQuestion[];
  answers: Record<number, string>;
  answerErrors: Record<number, string>;
  isSubmitting: boolean;
  onAnswerChange: (qIndex: number, value: string) => void;
  runId: string;
  coarseRouting?: CoarseRouting;
}

export interface MissingArtifactsStepProps {
  artifactDetails: ArtifactDetail[];
  onClose: () => void;
}

export interface ErrorStepProps {
  error: string;
  onRetry: () => void;
  onClose: () => void;
}

export interface ModalFooterProps {
  step: GeneratePRDStep;
  isSubmitting: boolean;
  hasAllRequiredAnswers: boolean;
  onClose: () => void;
  onStartGeneration: () => void;
  onSubmitAnswers: () => void;
}
