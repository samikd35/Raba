'use client';

import React, { useCallback, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { usePRDGeneration } from './usePRDGeneration';
import {
  InitialStep,
  ProcessingStep,
  QuestionsStep,
  MissingArtifactsStep,
  ErrorStep,
} from './steps';
import { ModalFooter } from './ModalFooter';
import type { GeneratePRDModalProps } from './types';

/**
 * Modal for Generating Product Requirements with clarifying questions
 */
export const GeneratePRDModal: React.FC<GeneratePRDModalProps> = ({
  isOpen,
  onClose,
  projectId,
  onPRDGenerated,
}) => {
  const {
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
    hasAllRequiredAnswers,
  } = usePRDGeneration({ projectId, onClose, onPRDGenerated });

  // Reset state when modal closes and auto-start when it opens
  useEffect(() => {
    if (!isOpen) {
      resetState();
    } else if (isOpen && step === 'initial') {
      // Automatically start generation when modal opens
      if (process.env.NODE_ENV === 'development') {
        console.log('🚀 Auto-starting PRD generation for project:', projectId);
      }
      
      const timer = setTimeout(() => {
        startGeneration();
      }, 100);
      
      return () => clearTimeout(timer);
    }
  }, [isOpen, step, resetState, startGeneration, projectId]);

  /**
   * Handle modal close request
   */
  const handleCloseRequest = useCallback(() => {
    // Allow closing during initial, error, or missing-artifacts steps
    if (step === 'initial' || step === 'error' || step === 'missing-artifacts') {
      resetState();
      onClose();
      return;
    }

    // For questions step, ask for confirmation if there are answers
    if (step === 'questions') {
      const hasAnswers = Object.values(answers).some(a => a.trim().length > 0);
      if (hasAnswers) {
        // Could add a confirmation dialog here in the future
        // For now, allow closing
        resetState();
        onClose();
      } else {
        resetState();
        onClose();
      }
      return;
    }

    // For processing steps, prevent closing
    if (step === 'processing' || step === 'generating-prd') {
      return;
    }

    resetState();
    onClose();
  }, [step, answers, resetState, onClose]);

  /**
   * Get modal title based on current step
   */
  const getModalTitle = useCallback((): string => {
    switch (step) {
      case 'initial':
        return 'Generate Product Requirements';
      case 'processing':
        return 'Generating Questions';
      case 'questions':
        return 'Clarifying Questions';
      case 'generating-prd':
        return 'Generating Product Requirements';
      case 'missing-artifacts':
        return 'Missing Prerequisites';
      case 'error':
        return 'Generation Error';
      default:
        return 'Generate PR';
    }
  }, [step]);

  return (
    <Dialog open={isOpen} onOpenChange={handleCloseRequest}>
      <DialogContent
        className="w-[75vw] max-w-[75vw] max-h-[90vh] flex flex-col"
        style={{ 
          scrollbarWidth: 'none', 
          msOverflowStyle: 'none',
          width: '75vw',
          maxWidth: '75vw'
        }}
        data-scrollbar-hide
      >
        {/* Header */}
        <DialogHeader className="bg-brand-25 dark:bg-brand-900/10 border-b border-brand-200 dark:border-brand-800 -m-6 mb-0 px-6 py-4 shrink-0">
          <DialogTitle className="text-xl font-bold text-brand-500 dark:text-brand-300">
            {getModalTitle()}
          </DialogTitle>
        </DialogHeader>

        {/* Content */}
        <div className="flex-1 overflow-y-auto py-2 space-y-4">
          {step === 'initial' && (
            <InitialStep
              onStartGeneration={startGeneration}
              isSubmitting={isSubmitting}
            />
          )}

          {step === 'processing' && (
            <ProcessingStep message={processingMessage} />
          )}

          {step === 'questions' && (
            <QuestionsStep
              questions={questions}
              answers={answers}
              answerErrors={answerErrors}
              isSubmitting={isSubmitting}
              onAnswerChange={handleAnswerChange}
              runId={runId || ''}
              coarseRouting={coarseRouting || undefined}
            />
          )}

          {step === 'generating-prd' && (
            <ProcessingStep message={processingMessage} />
          )}

          {step === 'missing-artifacts' && (
            <MissingArtifactsStep
              artifactDetails={artifactDetails}
              onClose={handleCloseRequest}
            />
          )}

          {step === 'error' && (
            <ErrorStep
              error={error || 'Unknown error occurred'}
              onRetry={retryGeneration}
              onClose={handleCloseRequest}
            />
          )}
        </div>

        {/* Footer */}
        <ModalFooter
          step={step}
          isSubmitting={isSubmitting}
          hasAllRequiredAnswers={hasAllRequiredAnswers}
          onClose={handleCloseRequest}
          onStartGeneration={startGeneration}
          onSubmitAnswers={submitAnswers}
        />
      </DialogContent>
    </Dialog>
  );
};
