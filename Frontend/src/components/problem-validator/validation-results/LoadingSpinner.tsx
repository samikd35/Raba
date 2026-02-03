"use client";

import React from "react";

interface LoadingSpinnerProps {
    message?: string;
}

export const LoadingSpinner = React.memo(({
    message = "Loading validation results..."
}: LoadingSpinnerProps) => (
    <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
            <div className="rounded-full h-12 w-12 border-2 border-t-brand-500 border-r-brand-500 border-b-brand-100 border-l-brand-100 mx-auto mb-4 animate-spin" />
            <p className="text-gray-600 dark:text-gray-400">{message}</p>
        </div>
    </div>
));

LoadingSpinner.displayName = 'LoadingSpinner';
