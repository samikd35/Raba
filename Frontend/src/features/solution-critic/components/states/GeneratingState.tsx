"use client";

import React from 'react';
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";

interface GeneratingStateProps {
  progress: string | null;
  onCancel: () => void;
}

/**
 * Generating State Component
 */
export const GeneratingState: React.FC<GeneratingStateProps> = ({ progress, onCancel }) => {
  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-8 dark:border-gray-800 dark:bg-white/[0.03]">
      <div className="flex flex-col items-center justify-center py-12 space-y-4">
        <Loader2 className="w-12 h-12 text-brand-500 animate-spin" />
        <div className="text-center">
          <p className="text-lg font-medium text-brand-500">Generating Solution Critique...</p>
          <p className="text-sm text-muted-foreground">
            {progress || 'Analyzing your solution and generating insights...'}
          </p>
          <p className="text-xs text-muted-foreground mt-2">This may take up to 2 minutes</p>
        </div>
        <Button 
          onClick={onCancel} 
          variant="outline" 
          size="sm"
          className="mt-4"
        >
          Cancel
        </Button>
      </div>
    </div>
  );
};

export default GeneratingState;
