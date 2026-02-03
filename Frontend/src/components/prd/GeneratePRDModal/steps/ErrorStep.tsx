'use client';

import React from 'react';
import { AlertTriangle, RefreshCw, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { ErrorStepProps } from '../types';

export const ErrorStep: React.FC<ErrorStepProps> = ({
  error,
  onRetry,
  onClose,
}) => {
  return (
    <div className="py-8">
      <div className="flex flex-col items-center justify-center space-y-4">
        <div className="w-16 h-16 rounded-full bg-red-100 dark:bg-red-900/40 flex items-center justify-center">
          <AlertTriangle className="h-8 w-8 text-red-500" />
        </div>
        
        <div className="text-center space-y-2">
          <h3 className="text-lg font-semibold text-red-600 dark:text-red-400">
            Generation Failed
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400 max-w-md">
            {error || 'An unexpected error occurred while generating questions.'}
          </p>
        </div>

        <div className="flex items-center gap-3 pt-4">
          <Button
            variant="outline"
            onClick={onClose}
            className="border-gray-300 dark:border-gray-600"
          >
            <X className="h-4 w-4 mr-2" />
            Close
          </Button>
          <Button
            onClick={onRetry}
            className="bg-brand-500 hover:bg-brand-600 text-white"
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Try Again
          </Button>
        </div>
      </div>
    </div>
  );
};
