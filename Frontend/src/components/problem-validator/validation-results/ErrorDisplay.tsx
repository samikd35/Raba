"use client";

import React from "react";
import { Button } from "@/components/ui/button";
import { AlertTriangle, RefreshCw } from "lucide-react";

interface ErrorDisplayProps {
    error: string;
    onRetry?: () => void;
}

export const ErrorDisplay = React.memo(({
    error,
    onRetry
}: ErrorDisplayProps) => (
    <div className="min-h-screen flex items-center justify-center">
        <div className="text-center max-w-md">
            <AlertTriangle className="h-12 w-12 text-red-500 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                Unable to Load Results
            </h2>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
                {error}
            </p>
            <div className="flex gap-3 justify-center">
                <Button onClick={() => window.location.reload()} variant="outline">
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Retry
                </Button>
                <Button onClick={() => window.history.back()}>
                    Go Back
                </Button>
            </div>
        </div>
    </div>
));

ErrorDisplay.displayName = 'ErrorDisplay';
