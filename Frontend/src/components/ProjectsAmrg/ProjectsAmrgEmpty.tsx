import React from 'react';
import { motion } from 'framer-motion';
import { FileText, Target, PlayCircle } from 'lucide-react';
import { Card, CardContent } from "@/components/ui/card";
import { Button } from '@/components/ui/button';

interface ProjectsEmptyProps {
    onGoToCustomerUnderstanding: () => void;
    onStartValidationProject: () => void;
}

/**
 * Simplified Empty state component for projects
 */
export const ProjectsAmrgEmpty = React.memo(({
    onGoToCustomerUnderstanding,
    onStartValidationProject
}: ProjectsEmptyProps) => (
    <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col items-center justify-center py-20 px-4"
    >
        <Card className="max-w-2xl w-full border-gray-100 dark:border-gray-800 shadow-sm">
            <CardContent className="pt-12 pb-10 text-center">
                <div className="bg-brand-50 dark:bg-brand-900/20 rounded-full p-5 w-20 h-20 mx-auto mb-6 flex items-center justify-center">
                    <FileText className="h-10 w-10 text-brand-600" />
                </div>

                <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
                    Start your AMRG Project
                </h3>

                <p className="text-gray-500 dark:text-gray-400 mb-10 max-w-sm mx-auto">
                    You haven't completed any MVP requirements yet. Choose an option below to get started.
                </p>

                <div className="grid sm:grid-cols-2 gap-4 max-w-xl mx-auto">
                    <div className="p-6 rounded-xl border border-gray-100 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-900/50 text-left">
                        <Target className="h-6 w-6 text-brand-600 mb-3" />
                        <h4 className="font-semibold text-gray-900 dark:text-white mb-1 text-sm">Customer Persona</h4>
                        <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">Define your audience and insights.</p>
                        <Button
                            onClick={onGoToCustomerUnderstanding}
                            variant="outline"
                            size="sm"
                            className="w-full text-xs border-brand-200 hover:bg-brand-50 text-brand-700"
                        >
                            Explore
                        </Button>
                    </div>

                    <div className="p-6 rounded-xl border border-gray-100 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-900/50 text-left">
                        <PlayCircle className="h-6 w-6 text-brand-600 mb-3" />
                        <h4 className="font-semibold text-gray-900 dark:text-white mb-1 text-sm">New Validation</h4>
                        <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">Test your assumptions now.</p>
                        <Button
                            onClick={onStartValidationProject}
                            variant="outline"
                            size="sm"
                            className="w-full text-xs border-brand-200 hover:bg-brand-50 text-brand-700"
                        >
                            Start Project
                        </Button>
                    </div>
                </div>
            </CardContent>
        </Card>
    </motion.div>
));

ProjectsAmrgEmpty.displayName = 'ProjectsAmrgEmpty';
