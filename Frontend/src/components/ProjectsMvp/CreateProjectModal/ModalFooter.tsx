'use client';

import React from 'react';
import { Loader2, ChevronRight, CheckCircle2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { ModalStep } from './types';

interface ModalFooterProps {
  step: ModalStep;
  isFormValid: boolean;
  isSubmitting: boolean;
  onClose: () => void;
  onSubmit: () => void;
  onSubmitAnswers: () => void;
  onConfirmContext: () => void;
}

export const ModalFooter: React.FC<ModalFooterProps> = ({
  step,
  isFormValid,
  isSubmitting,
  onClose,
  onSubmit,
  onSubmitAnswers,
  onConfirmContext,
}) => {
  return (
    <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700 shrink-0 bg-white dark:bg-gray-900">
      {step !== 'context-ready' && (
        <Button
          variant="outline"
          onClick={onClose}
          className="border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-800"
          disabled={isSubmitting || step === 'processing-context'}
        >
          Cancel
        </Button>
      )}
      
      {step === 'input' && (
        <Button
          onClick={onSubmit}
          disabled={!isFormValid || isSubmitting}
          className="bg-brand-500 hover:bg-brand-600 text-white"
        >
          {isSubmitting ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Creating...
            </>
          ) : (
            'Create Project'
          )}
        </Button>
      )}

      {step === 'questions' && (
        <Button
          className="bg-brand-500 hover:bg-brand-600 text-white"
          onClick={onSubmitAnswers}
          disabled={isSubmitting}
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

      {step === 'context-ready' && (
        <Button
          className="bg-green-500 hover:bg-green-600 text-white"
          onClick={onConfirmContext}
          disabled={isSubmitting}
        >
          {isSubmitting ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Saving...
            </>
          ) : (
            <>
              <CheckCircle2 className="h-4 w-4 mr-2" />
              Save & Finish
            </>
          )}
        </Button>
      )}
    </div>
  );
};
