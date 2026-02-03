"use client";

import React from 'react';
import { Lightbulb, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";

interface EmptyStateProps {
  onGoBack: () => void;
  onGenerate: () => void;
}

/**
 * Empty State Component - No critique data found
 */
export const EmptyState: React.FC<EmptyStateProps> = ({ onGoBack, onGenerate }) => {
  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-8 dark:border-gray-800 dark:bg-white/[0.03]">
      <div className="flex flex-col items-center justify-center py-12 space-y-4">
        <Lightbulb className="w-12 h-12 text-brand-500" />
        <div className="text-center">
          <p className="text-lg font-medium text-gray-600 dark:text-gray-300">No Solution Critique Found</p>
          <p className="text-sm text-muted-foreground">Generate a critique to get AI-powered insights on your solution</p>
        </div>
        <div className="flex gap-3 mt-4">
          <Button onClick={onGoBack} variant="outline">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Go Back
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

export default EmptyState;
