import React from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { AlertCircle, ArrowLeft, RefreshCw } from 'lucide-react';

interface CohortErrorStateProps {
    error: string | null;
    onRetry: () => void;
}

export const CohortErrorState = ({ error, onRetry }: CohortErrorStateProps) => {
    const router = useRouter();
    return (
        <div className="flex flex-col items-center justify-center py-20 bg-gray-50 dark:bg-gray-900 rounded-xl border-2 border-dashed border-gray-200 dark:border-gray-800">
            <AlertCircle className="h-12 w-12 text-red-500 mb-4" />
            <h2 className="text-xl font-semibold mb-2">Error Loading Cohort</h2>
            <p className="text-gray-500 mb-6">{error || 'Cohort could not be found'}</p>
            <div className="flex gap-3">
                <Button variant="outline" onClick={() => router.back()}>
                    <ArrowLeft className="h-4 w-4 mr-2" /> Go Back
                </Button>
                <Button onClick={onRetry}>
                    <RefreshCw className="h-4 w-4 mr-2" /> Retry
                </Button>
            </div>
        </div>
    );
};
