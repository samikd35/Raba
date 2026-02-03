'use client';

import React from 'react';
import { Loader2 } from 'lucide-react';
import type { ProcessingStepProps } from '../types';

export const ProcessingStep: React.FC<ProcessingStepProps> = ({ message }) => {
  // Determine if we're Generating Product Requirements or questions based on message
  const isGeneratingPRD = message?.toLowerCase().includes('product requirements') || 
                          message?.toLowerCase().includes('submitting answers');
  
  return (
    <div className="py-12">
      <div className="flex flex-col items-center justify-center space-y-4">
        <div className="relative">
          <div className="w-20 h-20 rounded-full bg-brand-100 dark:bg-brand-900/40 flex items-center justify-center">
            <Loader2 className="h-10 w-10 text-brand-500 animate-spin" />
          </div>
          {/* Pulsing ring effect */}
          <div className="absolute inset-0 rounded-full border-2 border-brand-300 dark:border-brand-700 animate-ping opacity-20" />
        </div>
        <div className="text-center space-y-2">
          <h3 className="text-lg font-semibold text-brand-500 dark:text-gray-300">
            {isGeneratingPRD ? 'Generating Product Requirements' : 'Generating Questions'}
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400 max-w-md">
            {message || 'Please wait while we analyze your project and generate clarifying questions...'}
          </p>
        </div>

        {/* Progress steps */}
        <div className="mt-6 space-y-2 text-xs text-gray-500 dark:text-gray-400">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            <span>Validating project artifacts</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-brand-500 animate-pulse" />
            <span>Performing template routing</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-gray-300 dark:bg-gray-600" />
            <span>Generating clarifying questions</span>
          </div>
        </div>
      </div>
    </div>
  );
};
