'use client';

import React from 'react';
import { FileText, Sparkles, CheckCircle2 } from 'lucide-react';
import type { InitialStepProps } from '../types';

export const InitialStep: React.FC<InitialStepProps> = ({
  onStartGeneration,
  isSubmitting,
}) => {
  return (
    <div className="py-6 space-y-6">
      {/* Info Banner */}
      <div className="flex items-start gap-3 p-4 bg-brand-50 dark:bg-brand-900/20 rounded-lg border border-brand-200 dark:border-brand-800">
        <FileText className="h-6 w-6 text-brand-500 shrink-0 mt-0.5" />
        <div className="space-y-2">
          <h3 className="font-semibold text-brand-700 dark:text-brand-300">
            No Product Requirements Found for This Project
          </h3>
          <p className="text-sm text-brand-600 dark:text-brand-400">
            A Product Requirement Document (PRD) hasn&apos;t been generated yet. 
            Click the button below to start the generation process.
          </p>
        </div>
      </div>

      {/* What Happens Section */}
      <div className="space-y-4">
        <h4 className="font-medium text-gray-900 dark:text-gray-100">
          What happens when you generate a PRD?
        </h4>
        <div className="space-y-3">
          <div className="flex items-start gap-3">
            <div className="w-6 h-6 rounded-full bg-green-100 dark:bg-green-900/40 flex items-center justify-center shrink-0">
              <CheckCircle2 className="h-4 w-4 text-green-600 dark:text-green-400" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                Artifact Validation
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                We&apos;ll verify your project has all required artifacts (VPS, BMC, Critique)
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3">
            <div className="w-6 h-6 rounded-full bg-blue-100 dark:bg-blue-900/40 flex items-center justify-center shrink-0">
              <Sparkles className="h-4 w-4 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                Smart Template Routing
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                AI analyzes your project to select the most relevant PRD template
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3">
            <div className="w-6 h-6 rounded-full bg-purple-100 dark:bg-purple-900/40 flex items-center justify-center shrink-0">
              <FileText className="h-4 w-4 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                Clarifying Questions
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Answer 3 targeted questions to customize your PRD output
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Estimated Time */}
      <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
        <p className="text-sm text-gray-600 dark:text-gray-400">
          <span className="font-medium">Estimated time:</span> ~2-3 minutes for question generation
        </p>
      </div>
    </div>
  );
};
