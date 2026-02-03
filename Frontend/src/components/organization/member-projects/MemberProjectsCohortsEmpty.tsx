import React from 'react';
import { Card } from '@/components/ui/card';
import { FolderOpen, Users } from 'lucide-react';

export function MemberProjectsCohortsEmpty() {
    return (
        <Card className="p-0 pb-6 overflow-hidden">
            <div className="bg-brand-25 dark:bg-brand-900/10 border-b border-brand-50 dark:border-brand-800 rounded-t-xl px-6 py-4">
                <h2 className="text-lg font-semibold text-brand-500 dark:text-white flex items-center gap-2">
                    <Users className="w-5 h-5" />
                    Select a Cohort
                </h2>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    Choose a cohort to view member projects
                </p>
            </div>
            <div className="py-16 text-center">
                <div className="w-16 h-16 bg-brand-50 dark:bg-brand-900/20 rounded-full flex items-center justify-center mx-auto mb-4">
                    <FolderOpen className="w-8 h-8 text-brand-400" />
                </div>
                <h3 className="text-xl font-semibold text-brand-500 dark:text-white mb-2">
                    No Cohorts Available
                </h3>
                <p className="text-gray-500 dark:text-gray-400 max-w-md mx-auto">
                    There are no cohorts available to view projects from. Cohorts need to be created first before you can view member projects.
                </p>
            </div>
        </Card>
    );
}
