import React from 'react';
import { motion } from 'framer-motion';
import { Card, CardContent } from "@/components/ui/card";
import { Button } from '@/components/ui/button';
import { AlertCircle, RefreshCw } from 'lucide-react';

interface CohortsErrorProps {
    error: string;
    onRetry: () => void;
}

export const CohortsError = React.memo(({ error, onRetry }: CohortsErrorProps) => (
    <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="flex flex-col items-center justify-center py-16 px-4"
    >
        <Card className="bg-red-50 dark:bg-red-900/30 border-red-200 dark:border-red-700 max-w-md w-full">
            <CardContent className="pt-6 text-center">
                <AlertCircle className="h-16 w-16 text-red-500 dark:text-red-400 mx-auto mb-4" />
                <h3 className="text-xl font-semibold text-red-900 dark:text-red-100 mb-2">
                    Unable to Load Cohorts
                </h3>
                <p className="text-red-700 dark:text-red-300 mb-6">
                    {error}
                </p>
                <Button onClick={onRetry} variant="destructive">
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Try Again
                </Button>
            </CardContent>
        </Card>
    </motion.div>
));

CohortsError.displayName = 'CohortsError';
