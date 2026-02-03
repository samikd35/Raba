import React from 'react';
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { motion } from 'framer-motion';

/**
 * Loading skeleton for projects grid
 */
export const ProjectsAmrgLoading = React.memo(() => (
    <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="space-y-6"
    >
        {/* Filters Skeleton */}
        <div className="flex flex-col md:flex-row gap-4 items-center justify-between mb-8">
            <div className="w-full md:w-96">
                <Skeleton className="h-10 w-full rounded-lg" />
            </div>
            <div className="flex gap-2 w-full md:w-auto">
                <Skeleton className="h-10 w-32 rounded-lg" />
                <Skeleton className="h-10 w-32 rounded-lg" />
                <Skeleton className="h-10 w-10 rounded-lg" />
            </div>
        </div>

        {/* Results Count Skeleton */}
        <div className="flex items-center justify-between mb-2">
            <Skeleton className="h-4 w-48" />
        </div>

        {/* Projects Grid Skeleton */}
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
            {[...Array(6)].map((_, i) => (
                <Card key={i} className="h-full border-gray-100 dark:border-gray-800 dark:bg-gray-900/50">
                    <CardHeader className="pb-4">
                        <div className="flex items-start justify-between">
                            <div className="flex-1 space-y-2">
                                <Skeleton className="h-6 w-3/4 rounded-md" />
                                <Skeleton className="h-4 w-1/2 rounded-md" />
                            </div>
                            <Skeleton className="h-6 w-20 rounded-full" />
                        </div>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="space-y-2">
                            <Skeleton className="h-3 w-full rounded-md" />
                            <Skeleton className="h-3 w-5/6 rounded-md" />
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <Skeleton className="h-16 rounded-xl bg-gray-50 dark:bg-gray-800/50" />
                            <Skeleton className="h-16 rounded-xl bg-gray-50 dark:bg-gray-800/50" />
                            <Skeleton className="h-16 rounded-xl bg-gray-50 dark:bg-gray-800/50" />
                            <Skeleton className="h-16 rounded-xl bg-gray-50 dark:bg-gray-800/50" />
                        </div>
                        <Skeleton className="h-10 w-full rounded-xl" />
                    </CardContent>
                </Card>
            ))}
        </div>
    </motion.div>
));

ProjectsAmrgLoading.displayName = 'ProjectsAmrgLoading';
