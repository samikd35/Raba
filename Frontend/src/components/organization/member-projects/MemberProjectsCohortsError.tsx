import React from 'react';
import { Button } from '@/components/ui/button';
import { AlertCircle, RefreshCw } from 'lucide-react';
import { Card } from '@/components/ui/card';

interface MemberProjectsCohortsErrorProps {
    error: string;
    onRetry: () => void;
}

export function MemberProjectsCohortsError({ error, onRetry }: MemberProjectsCohortsErrorProps) {
    return (
        <Card className="p-0 pb-6 overflow-hidden">
            <div className="bg-brand-25 dark:bg-brand-900/10 border-b border-brand-50 dark:border-brand-800 rounded-t-xl px-6 py-4">
                <h2 className="text-lg font-semibold text-brand-500 dark:text-white flex items-center gap-2">
                    <AlertCircle className="w-5 h-5 text-red-500" />
                    Error Loading Cohorts
                </h2>
            </div>
            <div className="py-16 text-center">
                <div className="w-16 h-16 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
                    <AlertCircle className="w-8 h-8 text-red-600 dark:text-red-400" />
                </div>
                <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                    Failed to Load Cohorts
                </h3>
                <p className="text-gray-500 dark:text-gray-400 mb-6 max-w-md mx-auto">
                    {error}
                </p>
                <Button onClick={onRetry} className="flex items-center space-x-2 bg-brand-500 hover:bg-brand-600 text-white">
                    <RefreshCw className="w-4 h-4" />
                    <span>Try Again</span>
                </Button>
            </div>
        </Card>
    );
}
