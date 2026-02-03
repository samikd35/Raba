import React from 'react';
import { motion } from 'framer-motion';
import { AlertCircle, RefreshCw, Target, PlayCircle } from 'lucide-react';
import { Card, CardContent } from "@/components/ui/card";
import { Button } from '@/components/ui/button';

interface ProjectsErrorProps {
    error: string;
    onRetry: () => void;
    onGoToCustomerUnderstanding: () => void;
    onStartValidationProject: () => void;
}

/**
 * Simplified Error state component for projects
 */
export const ProjectsAmrgError = React.memo(({
    error,
    onRetry,
    onGoToCustomerUnderstanding,
    onStartValidationProject
}: ProjectsErrorProps) => (
    <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col items-center justify-center py-20 px-4"
    >
        <Card className="max-w-md w-full border-gray-200 dark:border-gray-800 shadow-sm">
            <CardContent className="pt-10 pb-8 text-center">
                <div className="bg-red-50 dark:bg-red-900/20 rounded-full p-4 w-16 h-16 mx-auto mb-6 flex items-center justify-center">
                    <AlertCircle className="h-8 w-8 text-red-500" />
                </div>

                <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                    Failed to load projects
                </h3>

                <p className="text-sm text-gray-500 dark:text-gray-400 mb-8 px-4">
                    {error || "An unexpected error occurred while fetching your data."}
                </p>

                <div className="space-y-3 px-4">
                    <Button
                        onClick={onRetry}
                        className="w-full bg-brand-600 hover:bg-brand-700 text-white"
                    >
                        <RefreshCw className="mr-2 h-4 w-4" />
                        Try Again
                    </Button>

                    <div className="grid grid-cols-2 gap-3">
                        <Button
                            onClick={onGoToCustomerUnderstanding}
                            variant="outline"
                            className="text-xs"
                        >
                            <Target className="mr-2 h-3.5 w-3.5 text-brand-500" />
                            Customers
                        </Button>
                        <Button
                            onClick={onStartValidationProject}
                            variant="outline"
                            className="text-xs"
                        >
                            <PlayCircle className="mr-2 h-3.5 w-3.5 text-brand-500" />
                            New Project
                        </Button>
                    </div>
                </div>
            </CardContent>
        </Card>
    </motion.div>
));

ProjectsAmrgError.displayName = 'ProjectsAmrgError';
