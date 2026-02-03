'use client';

import React from 'react';
import { Loader2, Sparkles, ChevronRight, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { ModalFooterProps } from './types';

export const ModalFooter: React.FC<ModalFooterProps> = ({
  step,
  isSubmitting,
  hasAllRequiredAnswers,
  onClose,
  onStartGeneration,
  onSubmitAnswers,
}) => {
  // Don't show footer for error step (has its own buttons)
  if (step === 'error') {
    return null;
  }

  return (
    <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700 shrink-0 bg-white dark:bg-gray-900">
      {/* Cancel Button - show for initial, questions, and missing-artifacts steps */}
      {(step === 'initial' || step === 'questions' || step === 'missing-artifacts') && (
        <Button
          variant="outline"
          onClick={onClose}
          className="border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-800"
          disabled={isSubmitting}
        >
          {step === 'missing-artifacts' ? (
            <>
              <X className="h-4 w-4 mr-2" />
              Close
            </>
          ) : (
            'Cancel'
          )}
        </Button>
      )}

      {/* Initial Step - Generate Button */}
      {step === 'initial' && (
        <Button
          onClick={onStartGeneration}
          disabled={isSubmitting}
          className="bg-brand-500 hover:bg-brand-600 text-white"
        >
          {isSubmitting ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Starting...
            </>
          ) : (
            <>
              <Sparkles className="h-4 w-4 mr-2" />
              Generate PR
            </>
          )}
        </Button>
      )}

      {/* Questions Step - Submit Answers Button */}
      {step === 'questions' && (
        <Button
          onClick={onSubmitAnswers}
          disabled={isSubmitting || !hasAllRequiredAnswers}
          className="bg-brand-500 hover:bg-brand-600 text-white disabled:bg-gray-400 disabled:cursor-not-allowed"
        >
          {isSubmitting ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Submitting...
            </>
          ) : (
            <>
              Submit Answers
              <ChevronRight className="h-4 w-4 ml-1" />
            </>
          )}
        </Button>
      )}
    </div>
  );
};
