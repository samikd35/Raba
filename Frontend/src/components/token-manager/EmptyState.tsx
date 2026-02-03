"use client";

import React from 'react';
import { Inbox } from 'lucide-react';

interface EmptyStateProps {
  title?: string;
  message?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export function EmptyState({
  title = 'No data available',
  message = 'There is no data to display for the selected date range.',
  action,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center min-h-96 text-center">
      <div className="p-4 bg-gray-100 dark:bg-gray-800 rounded-full mb-4">
        <Inbox className="w-12 h-12 text-gray-400 dark:text-gray-600" />
      </div>
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
        {title}
      </h3>
      <p className="text-gray-600 dark:text-gray-400 mb-6 max-w-md">
        {message}
      </p>
      {action && (
        <button
          onClick={action.onClick}
          className="px-4 py-2 bg-brand-500 text-white rounded-md hover:bg-brand-600 transition-colors"
        >
          {action.label}
        </button>
      )}
    </div>
  );
}
