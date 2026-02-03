"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { organizationService } from '@/lib/api/organizationService';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { MemberInviteForm } from '@/components/admin/MemberInviteForm';
import { useAuthStore } from '@/stores/authStore';
import { toast } from "react-hot-toast";
import {
  ArrowLeft,
  Info,
  Users,
  Crown,
  CreditCard,
  RefreshCw,
  AlertCircle,
  Building,
  Shield,
  Zap,
  CheckCircle2
} from 'lucide-react';
import { useSetCurrentOrganization, useSetOrganizationMetrics } from '@/stores/organizationStore';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';

interface Organization {
  id: string;
  name: string;
  description?: string;
  website?: string;
  industry?: string;
  size?: string;
  country: string;
  city: string;
  contact_email: string;
  phone_number: string;
  type?: 'prepay_org' | 'grant_org';
  monthly_credit_limit?: number;
  status?: 'active' | 'suspended' | 'frozen'; // Made optional
  total_credits?: number;
  used_credits?: number;
  current_monthly_usage?: number;
}

export default function InviteMembersPage() {
  const router = useRouter();
  const params = useParams();
  const { user, isAuthenticated } = useAuthStore();
  const currentWorkspaceTenantId = user?.tenant_id;
  const setCurrentOrganization = useSetCurrentOrganization();
  const setOrganizationMetrics = useSetOrganizationMetrics();

  const organizationId = currentWorkspaceTenantId || params.id as string;

  const [organization, setOrganization] = useState<Organization | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);

  const fetchOrganizationData = useCallback(async () => {
    if (!organizationId) {
      setError('No organization ID available. Please select a workspace.');
      setLoading(false);
      return;
    }

    if (!isAuthenticated) {
      setError('Authentication required. Please sign in.');
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);

      if (process.env.NODE_ENV === 'development') {
        console.log('🏢 Fetching organization data for invite-members page, ID:', organizationId);
      }

      const org = await organizationService.getOrganizationById(organizationId);

      if (!org) {
        throw new Error('Organization not found. Please check if you have access to this organization.');
      }

      setOrganization(org);
      setCurrentOrganization(org);

      // Fetch organization metrics
      try {
        const metrics = await organizationService.getOrganizationMetrics(organizationId);

        const creditMetrics = {
          total: org?.total_credits || org?.monthly_credit_limit || 0,
          used: org?.used_credits || org?.current_monthly_usage || 0,
          remaining: (org?.total_credits || org?.monthly_credit_limit || 0) - (org?.used_credits || org?.current_monthly_usage || 0),
          monthly_limit: org?.total_credits || org?.monthly_credit_limit || 0,
        };

        const fullMetrics = {
          ...metrics,
          credits: creditMetrics,
        };

        setOrganizationMetrics(fullMetrics);
      } catch (metricsError) {
        if (process.env.NODE_ENV === 'development') {
          console.warn('Failed to fetch organization metrics:', metricsError);
        }
      }

      if (process.env.NODE_ENV === 'development') {
        console.log('✅ Organization data loaded successfully for invite-members');
      }

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load organization data';

      if (process.env.NODE_ENV === 'development') {
        console.error('❌ Error fetching organization data for invite-members:', error);
      }

      if (errorMessage.includes('401') || errorMessage.includes('Unauthorized')) {
        setError('Authentication expired. Please sign in again.');
        toast.error('Session expired. Please sign in again.');
        setTimeout(() => router.push('/signin'), 2000);
        return;
      }

      if (errorMessage.includes('403') || errorMessage.includes('Forbidden')) {
        setError('Access denied. You may not have permission to view this organization.');
        toast.error('Access denied to organization data.');
        return;
      }

      if (errorMessage.includes('404') || errorMessage.includes('Not Found')) {
        setError('Organization not found. It may have been deleted or you may not have access.');
        toast.error('Organization not found.');
        return;
      }

      setError(errorMessage);
      toast.error('Failed to load organization data');

      if (retryCount < 3 && (errorMessage.includes('Network') || errorMessage.includes('fetch'))) {
        const retryDelay = Math.pow(2, retryCount) * 1000;
        setTimeout(() => {
          setRetryCount(prev => prev + 1);
          fetchOrganizationData();
        }, retryDelay);
      }
    } finally {
      setLoading(false);
    }
  }, [organizationId, isAuthenticated, retryCount, router, setCurrentOrganization, setOrganizationMetrics]);

  useEffect(() => {
    if (!isAuthenticated) {
      if (process.env.NODE_ENV === 'development') {
        console.log('🔒 User not authenticated, redirecting to signin');
      }
      router.push('/signin');
      return;
    }

    if (!organizationId) {
      if (process.env.NODE_ENV === 'development') {
        console.log('🏢 No organization ID available, redirecting to workspace selection');
      }
      router.push('/choose-workspace');
      return;
    }

    fetchOrganizationData();
  }, [isAuthenticated, organizationId, fetchOrganizationData, router]);

  const handleBack = useCallback(() => {
    router.push('/organization');
  }, [router]);

  const handleRetry = useCallback(() => {
    setRetryCount(0);
    fetchOrganizationData();
  }, [fetchOrganizationData]);

  const handleRefresh = useCallback(() => {
    fetchOrganizationData();
    toast.success('Organization data refreshed');
  }, [fetchOrganizationData]);

  const handleBackToWorkspaces = useCallback(() => {
    router.push('/choose-workspace');
  }, [router]);

  // Safe status formatter with fallback
  const getOrganizationStatus = useCallback(() => {
    if (!organization?.status) return 'Unknown';
    return organization.status.charAt(0).toUpperCase() + organization.status.slice(1);
  }, [organization?.status]);

  // Safe status badge variant
  const getStatusBadgeVariant = useCallback(() => {
    if (!organization?.status) return 'secondary';
    return organization.status === 'active' ? 'default' : 'secondary';
  }, [organization?.status]);

  // Safe status badge styles
  const getStatusBadgeStyles = useCallback(() => {
    if (!organization?.status) {
      return 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-300';
    }

    return organization.status === 'active'
      ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300'
      : 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300';
  }, [organization?.status]);

  // Enhanced Loading State
  if (loading) {
    return (
      <div className="space-y-8 animate-pulse">
        {/* Enhanced Header Skeleton */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Skeleton className="h-10 w-10 rounded-lg" />
            <div className="space-y-2">
              <Skeleton className="h-8 w-64 rounded-md" />
              <Skeleton className="h-4 w-96 rounded-md" />
            </div>
          </div>
          <Skeleton className="h-10 w-32 rounded-lg" />
        </div>

        {/* Organization Card Skeleton */}
        <div className="grid gap-6">
          <Skeleton className="h-24 w-full rounded-xl" />

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Main Form Skeleton */}
            <div className="lg:col-span-2 space-y-6">
              <Skeleton className="h-12 w-full rounded-lg" />
              <div className="space-y-4">
                <Skeleton className="h-20 w-full rounded-lg" />
                <Skeleton className="h-20 w-full rounded-lg" />
                <Skeleton className="h-12 w-full rounded-lg" />
              </div>
            </div>

            {/* Info Panel Skeleton */}
            <div className="space-y-6">
              {[1, 2, 3].map((item) => (
                <div key={item} className="space-y-4">
                  <Skeleton className="h-6 w-32 rounded-md" />
                  <Skeleton className="h-32 w-full rounded-lg" />
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Enhanced Error State
  if (error || !organization) {
    return (
      <div className="space-y-8">
        {/* Header */}
        <div className="flex items-center space-x-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={handleBack}
            className="rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              Invite Members
            </h1>
            <p className="text-gray-600 dark:text-gray-400">
              Invite members to your organization
            </p>
          </div>
        </div>

        {/* Enhanced Error Alert */}
        <Alert variant="destructive" className="border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-950/20">
          <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400" />
          <AlertDescription className="text-red-800 dark:text-red-200">
            <div className="flex flex-col space-y-3">
              <div>
                <h4 className="font-semibold text-lg mb-1">Unable to Load Organization</h4>
                <p>{error || 'Organization not found'}</p>
              </div>
              <div className="flex space-x-3 pt-2">
                <Button
                  onClick={handleRetry}
                  className="flex items-center space-x-2 bg-red-600 hover:bg-red-700 text-white"
                >
                  <RefreshCw className="w-4 h-4" />
                  <span>Try Again</span>
                </Button>
                <Button
                  variant="outline"
                  onClick={handleBackToWorkspaces}
                  className="border-red-200 text-red-700 hover:bg-red-100 dark:border-red-800 dark:text-red-300 dark:hover:bg-red-900/30"
                >
                  Back to Workspaces
                </Button>
              </div>
            </div>
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="space-y-4 px-2">
      {/* Enhanced Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center space-x-4">
          <div>
            <h1 className="text-2xl font-bold text-brand-500 dark:text-white">
              Invite Members
            </h1>
            <p className="text-gray-600 dark:text-gray-400">
              Grow your team by inviting members to your organization
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            onClick={handleBack}
            className="flex items-center gap-2 rounded-lg border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors group"
          >
            <ArrowLeft className="w-4 h-4 group-hover:-translate-x-0.5 transition-transform" />
            <span>Back</span>
          </Button>
          <Button
            variant="outline"
            onClick={handleRefresh}
            className="flex items-center bg-brand-25 dark:bg-brand-800 gap-2 rounded-lg border-brand-200 dark:border-brand-700 hover:bg-brand-50 dark:hover:bg-brand-800 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            <span>Refresh</span>
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Main Form */}
        <div className="lg:col-span-2">


          <MemberInviteForm
            organizationId={organizationId}
            organizationName={organization.name}
          />
        </div>

        {/* Enhanced Info Panel */}
        <div className="space-y-6">
          {/* Member Types Info */}
          <Card className="border-gray-200 dark:border-gray-800">
            <CardHeader>
              <CardTitle className="flex items-center space-x-2 text-lg">
                <Info className="w-5 h-5 text-brand-500" />
                <span>Member Types</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-3 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
                <div className="flex items-center space-x-2">
                  <Users className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                  <span className="text-sm font-semibold text-blue-900 dark:text-blue-100">Individual Members</span>
                </div>
                <p className="text-sm text-blue-700 dark:text-blue-300">
                  Regular members who can use credits for their own work. Perfect for individual contributors.
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {[100, 200, 300, 400, 500, 600, 700, 800].map((credits) => (
                    <Badge key={credits} variant="secondary" className="text-xs bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300">
                      {credits} credits
                    </Badge>
                  ))}
                </div>
              </div>

              <div className="space-y-3 p-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800">
                <div className="flex items-center space-x-2">
                  <Crown className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                  <span className="text-sm font-semibold text-amber-900 dark:text-amber-100">Team Leaders</span>
                </div>
                <p className="text-sm text-amber-700 dark:text-amber-300">
                  Leaders who can create teams, manage members, and distribute credits. Ideal for project managers.
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {[200, 300, 400, 500, 600, 700, 800].map((credits) => (
                    <Badge key={credits} variant="secondary" className="text-xs bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300">
                      {credits} credits
                    </Badge>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>


          {/* Invitation Process */}
          <Card className="border-gray-200 dark:border-gray-800">
            <CardHeader>
              <CardTitle className="text-lg">Invitation Process</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {[
                { step: 1, title: "Invitations Sent", description: "Email invitations with secure links are sent immediately" },
                { step: 2, title: "Account Setup", description: "Members create accounts and join your organization" },
                { step: 3, title: "Credits Allocated", description: "Credits are automatically available upon joining" }
              ].map((item) => (
                <div key={item.step} className="flex items-start space-x-3 group">
                  <div className="w-6 h-6 rounded-full bg-brand-500 text-white text-xs flex items-center justify-center font-medium flex-shrink-0 mt-0.5 group-hover:scale-110 transition-transform">
                    {item.step}
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-900 dark:text-white group-hover:text-brand-600 dark:group-hover:text-brand-400 transition-colors">
                      {item.title}
                    </p>
                    <p className="text-xs text-gray-600 dark:text-gray-400 mt-0.5">
                      {item.description}
                    </p>
                  </div>
                </div>
              ))}

              <div className="pt-3 border-t border-gray-200 dark:border-gray-700">
                <p className="text-xs text-gray-500 dark:text-gray-400 italic">
                  Invitations expire after 7 days. You can resend invitations anytime.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}