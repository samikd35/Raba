import React from 'react';
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export const CohortDetailLoading = () => (
    <div className="space-y-6">
        <div className="flex items-center gap-4">
            <Skeleton className="h-10 w-24" />
            <Skeleton className="h-10 flex-1" />
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-6">
                <Card>
                    <CardHeader>
                        <Skeleton className="h-8 w-1/3 mb-2" />
                        <Skeleton className="h-4 w-full" />
                        <Skeleton className="h-4 w-5/6" />
                    </CardHeader>
                </Card>
                <Card>
                    <CardHeader>
                        <Skeleton className="h-6 w-1/4" />
                    </CardHeader>
                    <CardContent className="space-y-4">
                        {[1, 2, 3].map(i => <Skeleton key={i} className="h-12 w-full" />)}
                    </CardContent>
                </Card>
            </div>
            <div className="space-y-6">
                <Card>
                    <CardHeader>
                        <Skeleton className="h-6 w-1/2" />
                    </CardHeader>
                    <CardContent className="space-y-4">
                        {[1, 2, 3, 4].map(i => <Skeleton key={i} className="h-4 w-full" />)}
                    </CardContent>
                </Card>
            </div>
        </div>
    </div>
);
