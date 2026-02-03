"use client";

import React from 'react';
import { Loader2 } from "lucide-react";

/**
 * Loading State Component
 */
export const LoadingState: React.FC = () => {
  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-8 dark:border-gray-800 dark:bg-white/[0.03]">
      <div className="flex flex-col items-center justify-center py-12 space-y-4">
        <Loader2 className="w-12 h-12 text-brand-500 animate-spin" />
        <div className="text-center">
          <p className="text-lg font-medium text-brand-500">Loading Solution Critique...</p>
          <p className="text-sm text-muted-foreground">Please wait while we fetch your critique data</p>
        </div>
      </div>
    </div>
  );
};

export default LoadingState;
