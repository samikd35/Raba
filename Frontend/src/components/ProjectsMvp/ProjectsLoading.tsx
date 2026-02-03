import React from 'react';
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

/**
 * Loading skeleton for projects grid
 */
export const ProjectsLoading = React.memo(() => (
  <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
    {[...Array(6)].map((_, i) => (
      <Card key={i} className="h-full border-gray-200 dark:border-gray-700 dark:bg-gray-900">
        <CardHeader className="pb-4">
          <div className="flex items-start justify-between">
            <div className="flex-1 space-y-2">
              <Skeleton className="h-6 w-3/4 bg-gray-300 dark:bg-gray-700" />
              <Skeleton className="h-4 w-1/2 bg-gray-200 dark:bg-gray-800" />
            </div>
            <Skeleton className="h-6 w-20 rounded-full bg-gray-200 dark:bg-gray-800" />
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Skeleton className="h-4 w-full bg-gray-200 dark:bg-gray-800" />
            <Skeleton className="h-4 w-5/6 bg-gray-200 dark:bg-gray-800" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Skeleton className="h-20 rounded-lg bg-gray-200 dark:bg-gray-800" />
            <Skeleton className="h-20 rounded-lg bg-gray-200 dark:bg-gray-800" />
            <Skeleton className="h-20 rounded-lg bg-gray-200 dark:bg-gray-800" />
            <Skeleton className="h-20 rounded-lg bg-gray-200 dark:bg-gray-800" />
          </div>
          <Skeleton className="h-10 w-full rounded-lg bg-gray-200 dark:bg-gray-800" />
        </CardContent>
      </Card>
    ))}
  </div>
));

ProjectsLoading.displayName = 'ProjectsLoading';
