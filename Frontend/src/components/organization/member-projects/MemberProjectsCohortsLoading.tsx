import React from 'react';
import { Skeleton } from '@/components/ui/skeleton';
import { Card } from '@/components/ui/card';

export function MemberProjectsCohortsLoading() {
    return (
        <div className="space-y-4">
            {/* Filters skeleton */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 bg-brand-25 dark:bg-brand-900/10 p-4 rounded-lg border border-brand-50 dark:border-brand-800">
                <Skeleton className="h-10 w-full sm:max-w-xs" />
                <div className="flex items-center gap-2 w-full sm:w-auto">
                    <Skeleton className="h-10 w-full sm:w-40" />
                    <Skeleton className="h-10 w-10" />
                    <Skeleton className="h-10 w-10" />
                </div>
            </div>

            {/* Count skeleton */}
            <Skeleton className="h-5 w-48" />

            {/* Cards grid skeleton */}
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                {[...Array(6)].map((_, i) => (
                    <Card key={i} className="p-4 space-y-4">
                        <div className="flex items-start justify-between">
                            <div className="flex-1 space-y-2">
                                <div className="flex items-center gap-2">
                                    <Skeleton className="h-3 w-3 rounded-full" />
                                    <Skeleton className="h-5 w-32" />
                                </div>
                                <Skeleton className="h-4 w-full" />
                                <Skeleton className="h-4 w-3/4" />
                            </div>
                            <Skeleton className="h-6 w-16" />
                        </div>
                        <div className="flex items-center justify-between pt-4 border-t border-gray-100 dark:border-gray-800">
                            <Skeleton className="h-4 w-28" />
                            <Skeleton className="h-4 w-28" />
                        </div>
                    </Card>
                ))}
            </div>
        </div>
    );
}
