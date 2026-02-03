'use client';

import React from 'react';
import { Loader2 } from 'lucide-react';

interface ProcessingStepProps {
  processingMessage: string;
}

export const ProcessingStep: React.FC<ProcessingStepProps> = ({ processingMessage }) => {
  return (
    <div className="py-12">
      <div className="flex flex-col items-center justify-center space-y-4">
        <div className="relative">
          <div className="w-20 h-20 rounded-full bg-brand-100 dark:bg-brand-900/40 flex items-center justify-center">
            <Loader2 className="h-10 w-10 text-brand-500 animate-spin" />
          </div>
        </div>
        <div className="text-center space-y-2">
          <h3 className="text-lg font-semibold text-brand-500 dark:text-gray-300">
            Analyzing Your Content
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400 max-w-md">
            {processingMessage}
          </p>
        </div>
      </div>
    </div>
  );
};
