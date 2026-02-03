"use client";

import React from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useAuthStore } from '@/stores/authStore';
import { Card, CardContent } from '@/components/ui/card';
import { AlertCircle } from 'lucide-react';
import MemberProjectsList from '@/components/organization/MemberProjectsList';

export default function CohortProjectsPage() {
  const router = useRouter();
  const params = useParams();
  const { user } = useAuthStore();

  const organizationId = user?.tenant_id;
  const cohortId = params.id as string;

  if (!organizationId) {
    return (
      <div className="container mx-auto p-2 space-y-6">
        <Card>
          <CardContent className="py-12">
            <div className="text-center">
              <div className="w-16 h-16 bg-amber-100 dark:bg-amber-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
                <AlertCircle className="w-8 h-8 text-amber-600 dark:text-amber-400" />
              </div>
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                Organization Not Found
              </h3>
              <p className="text-gray-500 dark:text-gray-400 mb-6 max-w-md mx-auto">
                Please select a valid organization to view cohort projects.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!cohortId) {
    return (
      <div className="container mx-auto p-2 space-y-6">
        <Card>
          <CardContent className="py-12">
            <div className="text-center">
              <div className="w-16 h-16 bg-amber-100 dark:bg-amber-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
                <AlertCircle className="w-8 h-8 text-amber-600 dark:text-amber-400" />
              </div>
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                Cohort Not Found
              </h3>
              <p className="text-gray-500 dark:text-gray-400 mb-6 max-w-md mx-auto">
                Please select a valid cohort to view its projects.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-2 space-y-6">
      <MemberProjectsList organizationId={organizationId} cohortId={cohortId} />
    </div>
  );
}
