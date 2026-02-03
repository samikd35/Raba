import React, { useState, useCallback } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import {
    Calendar, Clock, Loader2, CheckCircle2, XCircle
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Card } from "@/components/ui/card";
import { Cohort } from '@/components/organization/cohorts/types';

interface MemberProjectsCohortCardProps {
    cohort: Cohort;
    index: number;
}

export const MemberProjectsCohortCard = React.memo(({ cohort, index }: MemberProjectsCohortCardProps) => {
    const [isNavigating, setIsNavigating] = useState(false);

    const formatDate = useCallback((dateString: string) => {
        try {
            return new Intl.DateTimeFormat('en-US', {
                month: 'short',
                day: 'numeric',
                year: 'numeric'
            }).format(new Date(dateString));
        } catch {
            return 'N/A';
        }
    }, []);

    return (
        <motion.div
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: Math.min(index * 0.04, 0.4) }}
        >
            <Link
                href={`/organization/member-projects/cohorts/${cohort.id}`}
                onClick={() => setIsNavigating(true)}
                className="block h-full"
            >
                <Card
                    className="h-full bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 hover:shadow-md transition-all duration-200 cursor-pointer overflow-hidden relative group"
                    style={{ borderColor: cohort.color }}
                >
                    <div className="px-4 space-y-2">
                        <div className="flex items-start justify-between mt-4">
                            <div className="flex-1 min-w-0 pr-4">
                                <div className="flex items-center gap-2 mb-2">
                                    <div
                                        className="w-3 h-3 rounded-full shrink-0"
                                        style={{ backgroundColor: cohort.color || '#9ca3af' }}
                                        aria-label={`Color: ${cohort.color}`}
                                    />
                                    <h3 className="text-lg font-semibold text-brand-500 dark:text-gray-100 truncate group-hover:text-brand-600 transition-colors">
                                        {cohort.name}
                                    </h3>
                                </div>
                                <p className="text-sm text-gray-500 dark:text-gray-400 line-clamp-2 min-h-[2.5rem]">
                                    {cohort.description || 'No description provided'}
                                </p>
                            </div>
                            <Badge
                                variant="outline"
                                className={`${cohort.is_active
                                    ? 'bg-green-50 text-green-700 border-green-200 dark:bg-green-900/20 dark:text-green-400 dark:border-green-800'
                                    : 'bg-gray-50 text-gray-700 border-gray-200 dark:bg-gray-900/20 dark:text-gray-400 dark:border-gray-700'
                                    }`}
                            >
                                {cohort.is_active ? (
                                    <CheckCircle2 className="w-3 h-3 mr-1" />
                                ) : (
                                    <XCircle className="w-3 h-3 mr-1" />
                                )}
                                {cohort.is_active ? 'Active' : 'Inactive'}
                            </Badge>
                        </div>

                        <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400 pt-4 pb-4 border-t border-gray-100 dark:border-gray-800">
                            <div className="flex items-center gap-1.5">
                                <Calendar className="h-3.5 w-3.5" />
                                <span>Created {formatDate(cohort.created_at)}</span>
                            </div>
                            <div className="flex items-center gap-1.5 ml-auto">
                                <Clock className="h-3.5 w-3.5" />
                                <span>Updated {formatDate(cohort.updated_at)}</span>
                            </div>
                        </div>
                    </div>

                    {isNavigating && (
                        <div className="absolute inset-0 bg-white/80 dark:bg-gray-900/80 backdrop-blur-sm flex items-center justify-center z-10">
                            <div className="flex flex-col items-center gap-2">
                                <Loader2 className="h-6 w-6 animate-spin text-brand-500" />
                                <span className="text-xs text-gray-600 dark:text-gray-400 font-medium">Opening projects...</span>
                            </div>
                        </div>
                    )}
                </Card>
            </Link>
        </motion.div>
    );
});

MemberProjectsCohortCard.displayName = 'MemberProjectsCohortCard';
