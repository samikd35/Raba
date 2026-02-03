"use client";

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { OrganizationInviteForm } from '@/components/admin/OrganizationInviteForm';
import { toast } from "react-hot-toast";
import { useAuthStore } from '@/stores/authStore';
import { isAdminUser } from '@/lib/adminRouteGuard';
import { ArrowLeft, Info } from 'lucide-react';

export default function InviteOrganizationPage() {
  const router = useRouter();
  const { isAuthenticated } = useAuthStore();
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // if (!isAuthenticated) {
    //   router.push('/signin?redirect=/admin/organizations/invite');
    //   return;
    // }

    if (!isAdminUser()) {
      toast.error('Access denied. You must be an admin to invite organizations.');
      router.push('/admin');
      return;
    }

    setIsLoading(false);
  }, [isAuthenticated, router]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-brand-500"></div>
      </div>
    );
  }

  return (
    <Card className="bg-white dark:bg-gray-800 px-4">
      {/* Header */}
      <div className="flex items-center space-x-2">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => router.back()}
        >
          <ArrowLeft className="w-5 h-5" />
        </Button>
        <div>
          <h1 className="text-2xl font-bold text-brand-500 dark:text-white">
            Invite Organization
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Send an invitation to create a new organization on Yuba
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Main Form */}
        <div className="lg:col-span-2">
          <OrganizationInviteForm />
        </div>

        {/* Info Panel */}
        <div className="space-y-4">
          {/* Organization Types Info */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Info className="w-5 h-5" />
                <span>Organization Types</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <div className="flex items-center space-x-2">
                  <Badge className="bg-green-100 text-green-800">Prepay</Badge>
                  <span className="text-sm font-medium">Prepayment Organization</span>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Organization pays upfront for credits. Credit card required during onboarding.
                </p>
              </div>

              <div className="space-y-2">
                <div className="flex items-center space-x-2">
                  <Badge className="bg-blue-100 text-blue-800">Grant</Badge>
                  <span className="text-sm font-medium">Grant Organization</span>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Organization receives monthly credit allocation. No credit card required.
                </p>
              </div>

              <div className="space-y-2">
                <div className="flex items-center space-x-2">
                  <Badge className="bg-amber-100 text-amber-800">Postpay</Badge>
                  <span className="text-sm font-medium">Postpayment Organization</span>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Organization pays for usage at the end of each billing cycle.
                </p>
              </div>
            </CardContent>
          </Card>

          {/* What Happens Next */}
          <Card>
            <CardHeader>
              <CardTitle>What Happens Next?</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-start space-x-3">
                <div className="w-6 h-6 rounded-full bg-brand-500 text-white text-xs flex items-center justify-center font-medium">
                  1
                </div>
                <div>
                  <p className="text-sm font-medium">Email Sent</p>
                  <p className="text-xs text-gray-600 dark:text-gray-400">
                    Invitation email sent to the admin
                  </p>
                </div>
              </div>

              <div className="flex items-start space-x-3">
                <div className="w-6 h-6 rounded-full bg-brand-500 text-white text-xs flex items-center justify-center font-medium">
                  2
                </div>
                <div>
                  <p className="text-sm font-medium">Account Creation</p>
                  <p className="text-xs text-gray-600 dark:text-gray-400">
                    Admin creates organization account
                  </p>
                </div>
              </div>

              <div className="flex items-start space-x-3">
                <div className="w-6 h-6 rounded-full bg-brand-500 text-white text-xs flex items-center justify-center font-medium">
                  3
                </div>
                <div>
                  <p className="text-sm font-medium">Ready to Use</p>
                  <p className="text-xs text-gray-600 dark:text-gray-400">
                    Organization can start inviting members
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </Card>
  );
}