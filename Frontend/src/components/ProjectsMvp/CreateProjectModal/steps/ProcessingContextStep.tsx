'use client';

import React from 'react';
import { Loader2 } from 'lucide-react';

interface ProcessingContextStepProps {
  processingMessage: string;
  error: string | null;
}

export const ProcessingContextStep: React.FC<ProcessingContextStepProps> = ({
  processingMessage,
  error,
}) => {
  return (
    <div className="py-8 flex flex-col items-center justify-center min-h-[300px]">
      <div className="relative mb-6">
        <div className="w-16 h-16 rounded-full bg-brand-100 dark:bg-brand-900/40 flex items-center justify-center">
          <Loader2 className="h-8 w-8 text-brand-500 animate-spin" />
        </div>
      </div>
      <h3 className="text-lg font-semibold text-brand-500 dark:text-gray-100 mb-2">
        Generating Enhanced Context
      </h3>
      <p className="text-sm text-gray-600 dark:text-gray-400 text-center max-w-md mb-4">
        {processingMessage || 'AI is analyzing your inputs and conducting research...'}
      </p>
      <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-500">
        <div className="w-2 h-2 rounded-full bg-brand-500 animate-pulse" />
        <span>This may take a few minutes</span>
      </div>
      {error && (
        <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
          <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
        </div>
      )}
    </div>
  );
};
