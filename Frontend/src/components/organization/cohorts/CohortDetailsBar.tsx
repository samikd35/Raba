import React from 'react';
import { Card, CardContent } from "@/components/ui/card";
import { Calendar, Clock, Hash } from 'lucide-react';
import { Cohort } from './types';

const formatDate = (dateString: string) => {
    try {
        return new Intl.DateTimeFormat('en-US', {
            dateStyle: 'long',
            timeStyle: 'short'
        }).format(new Date(dateString));
    } catch {
        return 'N/A';
    }
};

export const CohortDetailsBar = ({ cohort }: { cohort: Cohort }) => {
    return (
        <Card className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 shadow-none">
            <CardContent className="px-4">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div className="flex items-start gap-3">
                        <div className="mt-0.5 p-1.5 bg-brand-50 dark:bg-brand-500/10 rounded-md shrink-0">
                            <Hash className="h-4 w-4 text-brand-500" />
                        </div>
                        <div className="space-y-0.5">
                            <p className="text-xs font-medium text-gray-500 uppercase">About</p>
                            <p className="text-sm font-medium text-brand-500 line-clamp-2" title={cohort.description}>
                                {cohort.description || 'No description provided'}
                            </p>
                        </div>
                    </div>

                    <div className="flex items-start gap-3">
                        <div className="mt-0.5 p-1.5 bg-brand-50 dark:bg-brand-500/10 rounded-md shrink-0">
                            <Calendar className="h-4 w-4 text-brand-500" />
                        </div>
                        <div className="space-y-0.5">
                            <p className="text-xs font-medium text-gray-500 uppercase">Created At</p>
                            <p className="text-sm font-medium text-brand-500">{formatDate(cohort.created_at)}</p>
                        </div>
                    </div>

                    <div className="flex items-start gap-3">
                        <div className="mt-0.5 p-1.5 bg-brand-50 dark:bg-brand-500/10 rounded-md shrink-0">
                            <Clock className="h-4 w-4 text-brand-500" />
                        </div>
                        <div className="space-y-0.5">
                            <p className="text-xs font-medium text-gray-500 uppercase">Last Updated</p>
                            <p className="text-sm font-medium text-brand-500">{formatDate(cohort.updated_at)}</p>
                        </div>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
};
