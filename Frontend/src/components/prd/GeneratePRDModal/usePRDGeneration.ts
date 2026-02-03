'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { useAuthStore } from '@/stores/authStore';
import { toast } from 'react-hot-toast';
import type {
  GeneratePRDStep,
  AMRGQuestion,
  AMRGRunResponse,
  ArtifactDetail,
  CoarseRouting,
  MissingArtifactsError,
} from './types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '';

interface UsePRDGenerationProps {
  projectId: string;
  onClose: () => void;
  onPRDGenerated?: () => void;
}

export function usePRDGeneration({ projectId, onClose, onPRDGenerated }: UsePRDGenerationProps) {
  const { token } = useAuthStore();
  const abortControllerRef = useRef<AbortController | null>(null);

  // State
  const [step, setStep] = useState<GeneratePRDStep>('initial');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [processingMessage, setProcessingMessage] = useState('');
  const [error, setError] = useState<string | null>(null);

  // AMRG Run State
  const [runId, setRunId] = useState<string | null>(null);
  const [questions, setQuestions] = useState<AMRGQuestion[]>([]);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [answerErrors, setAnswerErrors] = useState<Record<number, string>>({});
  const [coarseRouting, setCoarseRouting] = useState<CoarseRouting | null>(null);

  // Missing Artifacts State
  const [artifactDetails, setArtifactDetails] = useState<ArtifactDetail[]>([]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  /**
   * Reset all state to initial values
   */
  const resetState = useCallback(() => {
    setStep('initial');
    setIsSubmitting(false);
    setProcessingMessage('');
    setError(null);
    setRunId(null);
    setQuestions([]);
    setAnswers({});
    setAnswerErrors({});
    setCoarseRouting(null);
    setArtifactDetails([]);
  }, []);

  /**
   * Start AMRG run to generate clarifying questions
   */
  const startGeneration = useCallback(async () => {
    if (!token || !projectId) {
      setError('Authentication required. Please sign in.');
      setStep('error');
      return;
    }

    // Cancel any ongoing request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    try {
      setIsSubmitting(true);
      setStep('processing');
      setProcessingMessage('Validating project artifacts and generating questions...');
      setError(null);

      const response = await fetch(
        `${API_BASE_URL}/mvp/projects/${projectId}/amrg/runs`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            research_mode: 'auto',
            force_regenerate: true,
          }),
          signal: abortControllerRef.current.signal,
        }
      );

      const data = await response.json();

      if (response.ok && data.success) {
        // Success - questions generated
        const runResponse = data as AMRGRunResponse;
        
        // Check if questions were actually generated
        if (!runResponse.questions || runResponse.questions.length === 0) {
          setError(runResponse.message || 'No questions were generated. Please try again.');
          setStep('error');
          toast.error('Failed to generate questions');
          return;
        }
        
        setRunId(runResponse.run_id);
        setQuestions(runResponse.questions);
        setCoarseRouting(runResponse.coarse_routing);
        setStep('questions');
        
        if (process.env.NODE_ENV === 'development') {
          console.log('AMRG run started successfully:', runResponse);
        }

        toast.success(`Generated ${runResponse.questions.length} clarifying questions!`);
      } else if (response.status === 400) {
        // Check for missing artifacts error
        const errorData = data.detail as MissingArtifactsError;
        
        if (errorData?.error_code === 'MISSING_REQUIRED_ARTIFACTS') {
          setArtifactDetails(errorData.artifact_details || []);
          setStep('missing-artifacts');
          toast.error('Missing required artifacts for PRD generation');
        } else {
          setError(errorData?.message || 'Bad request. Please try again.');
          setStep('error');
        }
      } else if (response.status === 402) {
        setError('Insufficient credits. Please upgrade your plan or purchase more credits.');
        setStep('error');
      } else if (response.status === 404) {
        setError('Project not found. Please verify the project exists.');
        setStep('error');
      } else {
        setError(data.detail?.message || data.message || 'Failed to generate questions');
        setStep('error');
      }
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        return;
      }

      const errorMessage = err instanceof Error ? err.message : 'Network error occurred';
      setError(errorMessage);
      setStep('error');

      if (process.env.NODE_ENV === 'development') {
        console.error('AMRG run failed:', err);
      }
    } finally {
      setIsSubmitting(false);
    }
  }, [token, projectId]);

  /**
   * Handle answer change for a question
   */
  const handleAnswerChange = useCallback((qIndex: number, value: string) => {
    setAnswers(prev => ({
      ...prev,
      [qIndex]: value,
    }));

    // Clear error for this question
    setAnswerErrors(prev => {
      const newErrors = { ...prev };
      delete newErrors[qIndex];
      return newErrors;
    });
  }, []);

  /**
   * Validate all required answers are provided
   */
  const validateAnswers = useCallback((): boolean => {
    const errors: Record<number, string> = {};
    let isValid = true;

    questions.forEach((question) => {
      const answer = answers[question.q_index]?.trim();
      if (!answer) {
        errors[question.q_index] = 'This question requires an answer';
        isValid = false;
      } else if (answer.length < 10) {
        errors[question.q_index] = 'Please provide a more detailed answer (at least 10 characters)';
        isValid = false;
      }
    });

    setAnswerErrors(errors);
    return isValid;
  }, [questions, answers]);

  /**
   * Check if all required answers have been provided
   */
  const hasAllRequiredAnswers = useCallback((): boolean => {
    return questions.every((question) => {
      const answer = answers[question.q_index]?.trim();
      return answer && answer.length >= 10;
    });
  }, [questions, answers]);

  /**
   * Submit answers to continue PRD generation
   */
  const submitAnswers = useCallback(async () => {
    if (!validateAnswers()) {
      toast.error('Please answer all questions before continuing');
      return;
    }

    if (!runId) {
      setError('No active generation run. Please start again.');
      setStep('error');
      return;
    }

    if (!token || !projectId) {
      setError('Authentication required. Please sign in.');
      setStep('error');
      return;
    }

    // Cancel any ongoing request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    try {
      setIsSubmitting(true);
      setStep('generating-prd');
      setProcessingMessage('Submitting answers and generating your Product Requirements Document...');
      setError(null);

      // Format answers for API
      const formattedAnswers = Object.entries(answers).map(([qIndex, answerText]) => ({
        q_index: parseInt(qIndex),
        answer_text: answerText.trim(),
      }));

      if (process.env.NODE_ENV === 'development') {
        console.log('Submitting answers:', {
          run_id: runId,
          project_id: projectId,
          answers: formattedAnswers,
        });
      }

      const response = await fetch(
        `${API_BASE_URL}/mvp/amrg/runs/${runId}/answers?project_id=${projectId}`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            answers: formattedAnswers,
          }),
          signal: abortControllerRef.current.signal,
        }
      );

      const data = await response.json();

      if (response.ok && data.success) {
        // PRD generated successfully
        if (process.env.NODE_ENV === 'development') {
          console.log('PRD generated successfully:', data);
        }

        toast.success('PRD generated successfully!');
        
        // Close modal and trigger refresh
        onClose();
        if (onPRDGenerated) {
          onPRDGenerated();
        }
      } else if (response.status === 400) {
        const errorMessage = data.detail?.message || data.message || 'Invalid answers or run state';
        setError(errorMessage);
        setStep('error');
        toast.error(errorMessage);
      } else if (response.status === 404) {
        setError('Generation run not found. Please start again.');
        setStep('error');
        toast.error('Generation run not found');
      } else {
        const errorMessage = data.detail?.message || data.message || 'Failed to Generate PR';
        setError(errorMessage);
        setStep('error');
        toast.error(errorMessage);
      }
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        return;
      }

      const errorMessage = err instanceof Error ? err.message : 'Network error occurred';
      setError(errorMessage);
      setStep('error');
      toast.error('Failed to submit answers. Please try again.');

      if (process.env.NODE_ENV === 'development') {
        console.error('Answer submission failed:', err);
      }
    } finally {
      setIsSubmitting(false);
    }
  }, [runId, answers, validateAnswers, token, projectId, onClose, onPRDGenerated]);

  /**
   * Retry generation after error
   */
  const retryGeneration = useCallback(() => {
    setError(null);
    setStep('initial');
  }, []);

  return {
    // State
    step,
    isSubmitting,
    processingMessage,
    error,
    runId,
    questions,
    answers,
    answerErrors,
    coarseRouting,
    artifactDetails,

    // Actions
    startGeneration,
    handleAnswerChange,
    submitAnswers,
    retryGeneration,
    resetState,
    hasAllRequiredAnswers: hasAllRequiredAnswers(),
  };
}
