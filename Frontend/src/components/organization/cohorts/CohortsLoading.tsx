import React from 'react';
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export const CohortsLoading = React.memo(() => (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {[...Array(6)].map((_, i) => (
            <Card key={i} className="h-full border-gray-200 dark:border-gray-700">
                <CardHeader className="pb-4">
                    <div className="flex items-start justify-between">
                        <div className="flex-1 space-y-2">
                            <Skeleton className="h-6 w-3/4" />
                            <Skeleton className="h-4 w-1/2" />
                        </div>
                        <Skeleton className="h-6 w-6 rounded-full" />
                    </div>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="flex gap-4">
                        <Skeleton className="h-20 w-1/2 rounded-lg" />
                        <Skeleton className="h-20 w-1/2 rounded-lg" />
                    </div>
                </CardContent>
            </Card>
        ))}
    </div>
));

CohortsLoading.displayName = 'CohortsLoading';
