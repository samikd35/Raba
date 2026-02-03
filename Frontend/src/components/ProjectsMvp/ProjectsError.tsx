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
 * Error state component for projects
 */
export const ProjectsError = React.memo(({ 
  error, 
  onRetry, 
  onGoToCustomerUnderstanding,
  onStartValidationProject 
}: ProjectsErrorProps) => (
  <motion.div
    initial={{ opacity: 0, scale: 0.95 }}
    animate={{ opacity: 1, scale: 1 }}
    className="flex flex-col items-center justify-center py-16 px-4"
  >
    <Card className="bg-red-50 dark:bg-gray-900 border border-red-200 dark:border-red-800/50 max-w-xl w-full shadow-lg">
      <CardContent className="pt-6 text-center">
        <div className="bg-red-100 dark:bg-red-900/30 rounded-full p-4 w-20 h-20 mx-auto mb-4 flex items-center justify-center">
          <AlertCircle className="h-10 w-10 text-red-600 dark:text-red-400" />
        </div>
        <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
          Oops! Something went wrong
        </h3>
        <p className="text-gray-600 dark:text-gray-400 mb-6">
          {error}
        </p>
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Button
            onClick={onRetry}
            variant="default"
            className="bg-red-600 hover:bg-red-700 dark:bg-red-700 dark:hover:bg-red-600"
          >
            <RefreshCw className="mr-2 h-4 w-4" />
            Try Again
          </Button>
          <Button
            onClick={onGoToCustomerUnderstanding}
            variant="outline"
            className="border-brand-500 text-brand-600 hover:bg-brand-50 dark:border-brand-600 dark:text-brand-400 dark:hover:bg-brand-900/20"
          >
            <Target className="mr-2 h-4 w-4" />
            Customer Understanding
          </Button>
          <Button
            onClick={onStartValidationProject}
            variant="outline"
            className="border-purple-500 text-purple-600 hover:bg-purple-50 dark:border-purple-600 dark:text-purple-400 dark:hover:bg-purple-900/20"
          >
            <PlayCircle className="mr-2 h-4 w-4" />
            Start New Project
          </Button>
        </div>
      </CardContent>
    </Card>
  </motion.div>
));

ProjectsError.displayName = 'ProjectsError';
