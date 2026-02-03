'use client';

import React, { useCallback } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useProjectBootstrap } from './useProjectBootstrap';
import { 
  InputStep, 
  ProcessingStep, 
  QuestionsStep, 
  ProcessingContextStep, 
  ContextReadyStep 
} from './steps';
import { ModalFooter } from './ModalFooter';
import { CancelConfirmDialog } from './CancelConfirmDialog';
import type { CreateProjectModalProps } from './types';

/**
 * Modal for creating a new project with bootstrap workflow
 */
export const CreateProjectModal: React.FC<CreateProjectModalProps> = ({ 
  isOpen, 
  onClose, 
  onProjectCreated 
}) => {
  const {
    // State
    step,
    projectName,
    ideaText,
    pdfFiles,
    isSubmitting,
    processingMessage,
    questions,
    answers,
    answerErrors,
    error,
    showCancelConfirm,
    enhancedContext,
    editableContext,
    isFormValid,
    
    // Setters
    setProjectName,
    setIdeaText,
    setShowCancelConfirm,
    
    // Handlers
    handleFileChange,
    handleRemoveFile,
    handleAnswerChange,
    handleSubmit,
    handleSubmitAnswers,
    handleConfirmContext,
    resetState,
    
    // Context update handlers
    updateEditableContext,
    updateNestedEditableContext,
    updateArrayItem,
    updateCostDriver,
    
    // Utility functions
    getPriorityColor,
    getCategoryDisplay,
  } = useProjectBootstrap(onClose, onProjectCreated);

  /**
   * Handle modal close request
   */
  const handleCloseRequest = useCallback(() => {
    const hasProgress = projectName.trim() || ideaText.trim() || pdfFiles.length > 0 || 
                       questions.length > 0 || Object.keys(answers).length > 0;
    
    if (hasProgress) {
      setShowCancelConfirm(true);
    } else {
      resetState();
      onClose();
    }
  }, [projectName, ideaText, pdfFiles, questions, answers, setShowCancelConfirm, resetState, onClose]);

  /**
   * Confirm cancel and close modal
   */
  const handleConfirmCancel = useCallback(() => {
    setShowCancelConfirm(false);
    resetState();
    onClose();
  }, [setShowCancelConfirm, resetState, onClose]);

  /**
   * Cancel the cancel confirmation
   */
  const handleCancelConfirmation = useCallback(() => {
    setShowCancelConfirm(false);
  }, [setShowCancelConfirm]);

  /**
   * Get modal title based on step
   */
  const getModalTitle = () => {
    switch (step) {
      case 'input':
        return 'Create New Project';
      case 'processing':
        return 'Creating Project';
      case 'questions':
        return 'Clarifying Questions';
      case 'processing-context':
        return 'Processing Context';
      case 'context-ready':
        return 'Review Project Details';
      default:
        return 'Create New Project';
    }
  };

  return (
    <>
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
            {step === 'input' && (
              <InputStep
                projectName={projectName}
                ideaText={ideaText}
                pdfFiles={pdfFiles}
                isSubmitting={isSubmitting}
                error={error}
                onProjectNameChange={setProjectName}
                onIdeaTextChange={setIdeaText}
                onFileChange={handleFileChange}
                onRemoveFile={handleRemoveFile}
              />
            )}

            {step === 'processing' && (
              <ProcessingStep processingMessage={processingMessage} />
            )}

            {step === 'questions' && (
              <QuestionsStep
                questions={questions}
                answers={answers}
                answerErrors={answerErrors}
                isSubmitting={isSubmitting}
                onAnswerChange={handleAnswerChange}
                getPriorityColor={getPriorityColor}
                getCategoryDisplay={getCategoryDisplay}
              />
            )}

            {step === 'processing-context' && (
              <ProcessingContextStep
                processingMessage={processingMessage}
                error={error}
              />
            )}

            {step === 'context-ready' && editableContext && (
              <ContextReadyStep
                editableContext={editableContext}
                enhancedContext={enhancedContext}
                error={error}
                updateEditableContext={updateEditableContext}
                updateNestedEditableContext={updateNestedEditableContext}
                updateArrayItem={updateArrayItem}
                updateCostDriver={updateCostDriver}
              />
            )}
          </div>

          {/* Footer */}
          <ModalFooter
            step={step}
            isFormValid={isFormValid}
            isSubmitting={isSubmitting}
            onClose={handleCloseRequest}
            onSubmit={handleSubmit}
            onSubmitAnswers={handleSubmitAnswers}
            onConfirmContext={handleConfirmContext}
          />
        </DialogContent>
      </Dialog>

      {/* Cancel Confirmation Dialog */}
      <CancelConfirmDialog
        isOpen={showCancelConfirm}
        onOpenChange={setShowCancelConfirm}
        onConfirmCancel={handleConfirmCancel}
        onContinueWorking={handleCancelConfirmation}
      />
    </>
  );
};
