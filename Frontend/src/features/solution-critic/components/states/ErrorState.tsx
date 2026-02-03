"use client";

import React from 'react';
import { AlertCircle, ArrowLeft, RefreshCw, Lightbulb } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ErrorStateProps {
  error: string;
  onGoBack: () => void;
  onRetry: () => void;
  onGenerate: () => void;
}

/**
 * Error State Component
 */
export const ErrorState: React.FC<ErrorStateProps> = ({ 
  error, 
  onGoBack, 
  onRetry, 
  onGenerate 
}) => {
  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-8 dark:border-gray-800 dark:bg-white/[0.03]">
      <div className="flex flex-col items-center justify-center py-12 space-y-4">
        <AlertCircle className="w-12 h-12 text-red-500" />
        <div className="text-center">
          <p className="text-lg font-medium text-red-600">{error}</p>
          <p className="text-sm text-muted-foreground">Please try again or generate a new critique</p>
        </div>
        <div className="flex gap-3">
          <Button onClick={onGoBack} variant="outline">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Go Back
          </Button>
          <Button onClick={onRetry} variant="outline">
            <RefreshCw className="w-4 h-4 mr-2" />
            Retry
          </Button>
          <Button onClick={onGenerate} className="bg-brand-600 hover:bg-brand-700">
            <Lightbulb className="w-4 h-4 mr-2" />
            Generate Critique
          </Button>
        </div>
      </div>
    </div>
  );
};

export default ErrorState;
