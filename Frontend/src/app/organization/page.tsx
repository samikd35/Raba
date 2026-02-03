"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { organizationService } from '@/lib/api/organizationService';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useAuthStore } from '@/stores/authStore';
import { toast } from "react-hot-toast";
import {
  ArrowLeft,
  RefreshCw,
  Building2,
  Users,
  CreditCard,
  Mail,
  MapPin,
  Globe,
  Phone,
  Calendar,
  UserPlus,
  TrendingUp,
  Activity,
  Shield,
  MoreVertical,
  Settings
} from 'lucide-react';
import { OrganizationMetricsCard } from '@/components/admin/OrganizationMetricsCard';
import { InvitationAnalyticsPanel } from '@/components/admin/InvitationAnalyticsPanel';
import { OrganizationMetrics as StoreOrganizationMetrics } from '@/stores/organizationStore';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';

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
  created_at: string;
  updated_at: string;
  status: 'active' | 'suspended' | 'frozen';
  total_credits?: number;
  used_credits?: number;
  current_monthly_usage?: number;
}

interface OrganizationMetrics {
  invitations: {
    sent: number;
    accepted: number;
  };
  membership: {
    total: number;
    team_members: number;
    individual_members: number;
  };
  credits: {
    total: number;
    used: number;
    remaining: number;
    monthly_limit: number;
  };
}

export default function OrganizationDetailPage() {
  const router = useRouter();
  const { user, isAuthenticated } = useAuthStore();
  const currentWorkspaceTenantId = user?.tenant_id;

  const [organization, setOrganization] = useState<Organization | null>(null);
  const [metrics, setMetrics] = useState<OrganizationMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [orgType, setOrgType] = useState<string | null>(null);
  const currentWorkspaceType = user?.tenant_type;
  const [retryCount, setRetryCount] = useState(0);

  // Get organization ID from current workspace
  const organizationId = currentWorkspaceTenantId;

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
        console.log('🏢 Fetching organization data for ID:', organizationId);
      }

      const [org, orgMetrics] = await Promise.all([
        organizationService.getOrganizationById(organizationId),
        organizationService.getOrganizationMetrics(organizationId)
      ]);

      setOrganization(org);

      const fullMetrics = {
        ...orgMetrics,
        credits: orgMetrics.credits || {
          total: 0,
          used: 0,
          remaining: 0,
          monthly_limit: 0
        }
      };

      setMetrics(fullMetrics);

      if (process.env.NODE_ENV === 'development') {
        console.log('✅ Organization data loaded successfully');
      }

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load organization data';

      if (process.env.NODE_ENV === 'development') {
        console.error('❌ Error fetching organization data:', error);
      }

      // Handle specific error cases
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

      // Auto-retry logic for network errors
      if (retryCount < 3 && (errorMessage.includes('Network') || errorMessage.includes('fetch'))) {
        const retryDelay = Math.pow(2, retryCount) * 1000; // Exponential backoff
        setTimeout(() => {
          setRetryCount(prev => prev + 1);
          fetchOrganizationData();
        }, retryDelay);
      }
    } finally {
      setLoading(false);
    }
  }, [organizationId, isAuthenticated, retryCount, router]);

  // Fetch organization type
  const fetchOrgType = useCallback(async () => {
    if (!isAuthenticated || user?.tenant_type !== 'organization') {
      return;
    }

    try {
      const result = await organizationService.getMyOrganizationType();
      if (result.success) {
        setOrgType(result.organization_type);
      }
    } catch (error) {
      if (process.env.NODE_ENV === 'development') {
        console.error('OrganizationDetailPage: Error fetching organization type:', error);
      }
    }
  }, [isAuthenticated, user?.tenant_type]);

  useEffect(() => {
    // Check authentication first
    if (!isAuthenticated) {
      if (process.env.NODE_ENV === 'development') {
        console.log('🔒 User not authenticated, redirecting to signin');
      }
      router.push('/signin');
      return;
    }

    // Check if we have organization ID
    if (!organizationId) {
      if (process.env.NODE_ENV === 'development') {
        console.log('🏢 No organization ID available, redirecting to workspace selection');
      }
      router.push('/choose-workspace');
      return;
    }

    fetchOrganizationData();
    if (user?.tenant_type === 'organization') {
      fetchOrgType();
    }
  }, [isAuthenticated, organizationId, fetchOrganizationData, fetchOrgType, user?.tenant_type, router]);

  const handleRetry = useCallback(() => {
    setRetryCount(0);
    fetchOrganizationData();
  }, [fetchOrganizationData]);

  const handleBackToWorkspaces = useCallback(() => {
    router.push('/choose-workspace');
  }, [router]);

  const handleBack = () => {
    router.push('/admin/organizations');
  };

  const handleRefresh = () => {
    fetchOrganizationData();
    toast.success('Dashboard refreshed');
  };

  const getOrganizationSizeLabel = (size: string) => {
    switch (size) {
      case 'startup': return '1-10 employees';
      case 'small': return '11-50 employees';
      case 'medium': return '51-200 employees';
      case 'large': return '201-1000 employees';
      case 'enterprise': return '1000+ employees';
      default: return 'Not specified';
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  // Loading State
  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50/50 dark:bg-gray-900 p-6">
        <div className="mx-auto space-y-6">
          {/* Header Skeleton */}
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <Skeleton className="h-10 w-10 rounded-lg dark:bg-gray-900" />
              <div className="space-y-2">
                <Skeleton className="h-8 w-64 dark:bg-gray-900" />
                <Skeleton className="h-4 w-48 dark:bg-gray-900" />
              </div>
            </div>
            <Skeleton className="h-10 w-32 dark:bg-gray-900" />
          </div>

          {/* Stats Grid Skeleton */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[...Array(4)].map((_, i) => (
              <Skeleton key={i} className="h-32 rounded-xl dark:bg-gray-900" />
            ))}
          </div>

          {/* Content Grid Skeleton */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-6">
              <Skeleton className="h-64 rounded-xl dark:bg-gray-900" />
              <Skeleton className="h-64 rounded-xl dark:bg-gray-900" />
            </div>
            <div className="space-y-6">
              <Skeleton className="h-48 rounded-xl dark:bg-gray-900" />
              <Skeleton className="h-48 rounded-xl dark:bg-gray-900" />
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Error State
  if (error) {
    return (
      <div className="min-h-screen bg-gray-50/50 dark:bg-gray-900 p-6">
        <div className="mx-auto">
          <div className="flex items-center space-x-4 mb-6">
            <Button
              variant="ghost"
              size="icon"
              onClick={handleBack}
              className="rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
            >
              <ArrowLeft className="w-5 h-5 text-gray-700 dark:text-gray-300" />
            </Button>
            <div>
              <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">
                Organization Dashboard
              </h1>
            </div>
          </div>

          <Card className="border-red-200 dark:border-red-800 bg-white dark:bg-gray-900">
            <CardContent className="pt-6">
              <div className="flex items-start space-x-4">
                <div className="w-12 h-12 bg-red-100 dark:bg-red-950/50 rounded-lg flex items-center justify-center flex-shrink-0 border border-red-200 dark:border-red-800">
                  <Activity className="w-6 h-6 text-red-600 dark:text-red-400" />
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-red-800 dark:text-red-300">
                    Unable to Load Dashboard
                  </h3>
                  <p className="text-red-700 dark:text-red-400 mt-1">
                    {error}
                  </p>
                  <div className="flex space-x-3 mt-4">
                    <Button onClick={handleRetry} className="flex items-center space-x-2 bg-red-600 hover:bg-red-700 dark:bg-red-600 dark:hover:bg-red-700">
                      <RefreshCw className="w-4 h-4" />
                      <span>Try Again</span>
                    </Button>
                    <Button variant="outline" onClick={handleBackToWorkspaces} className="dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-800">
                      Back to Workspaces
                    </Button>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  if (!organization) {
    return (
      <div className="min-h-screen bg-gray-50/50 dark:bg-gray-900 p-6">
        <div className="mx-auto">
          <div className="flex items-center space-x-4 mb-6">
            <Button
              variant="ghost"
              size="icon"
              onClick={handleBack}
              className="rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
            >
              <ArrowLeft className="w-5 h-5 text-gray-700 dark:text-gray-300" />
            </Button>
            <div>
              <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">
                Organization Dashboard
              </h1>
            </div>
          </div>

          <Card className="border-yellow-200 dark:border-yellow-800 bg-white dark:bg-gray-900">
            <CardContent className="pt-6">
              <div className="flex items-start space-x-4">
                <div className="w-12 h-12 bg-yellow-100 dark:bg-yellow-950/50 rounded-lg flex items-center justify-center flex-shrink-0 border border-yellow-200 dark:border-yellow-800">
                  <Building2 className="w-6 h-6 text-yellow-600 dark:text-yellow-400" />
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-yellow-800 dark:text-yellow-300">
                    Organization Not Found
                  </h3>
                  <p className="text-yellow-700 dark:text-yellow-400 mt-1">
                    The organization with ID "{organizationId}" could not be found.
                  </p>
                  <Button onClick={handleBackToWorkspaces} className="mt-4 bg-yellow-600 hover:bg-yellow-700 dark:bg-yellow-600 dark:hover:bg-yellow-700">
                    Back to Workspaces
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50/50 dark:bg-gray-900">
      <div className="mx-auto space-y-4 w-full">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Button
              variant="outline"
              size="icon"
              onClick={handleBack}
              className="rounded-lg hover:bg-white dark:hover:bg-gray-800 transition-colors"
            >
              <ArrowLeft className="w-5 h-5 text-brand-500 dark:text-brand-400" />
            </Button>
            <div>
              <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">
                <span className="text-gray-800 dark:text-gray-300">Welcome to </span>
                <span className="text-brand-500 dark:text-brand-400">{organization.name}</span>

                {(orgType || organization.type) && (
                  <span className="ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-brand-100 text-brand-800 dark:bg-brand-900/50 dark:text-brand-200 border border-brand-200 dark:border-brand-800">
                    {(() => {
                      const type = orgType || organization.type;
                      const labels: Record<string, string> = {
                        'postpay_org': 'Post Pay Organization',
                        'prepay_org': 'Pre Pay Organization',
                        'grant_org': 'Grant Organization',
                      };
                      return labels[type || ''] || type;
                    })()}
                  </span>
                )}
              </h1>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <Button
              variant="outline"
              onClick={handleRefresh}
              className="flex items-center space-x-2 rounded-lg dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-800"
            >
              <RefreshCw className="w-4 h-4" />
              <span>Refresh</span>
            </Button>
            <Button
              onClick={() => router.push(`/organization/invite-members`)}
              className="flex items-center space-x-2 rounded-lg bg-brand-600 hover:bg-brand-700 dark:bg-brand-600 dark:hover:bg-brand-700"
            >
              <UserPlus className="w-4 h-4" />
              <span>Invite Members</span>
            </Button>
          </div>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Total Members */}
          <Card className={cn(
            "group relative overflow-hidden border-border/50 shadow-sm hover:shadow-md transition-all duration-300",

            "hover:border-blue-200 dark:hover:border-blue-800"
          )}>
            <CardContent className="p-4 px-8">
              <div className="flex items-start justify-between h-16">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <Users className="w-4 h-4 text-muted-foreground" />
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                      Total Members
                    </p>
                  </div>
                  <p className="text-3xl font-bold text-brand-500 mt-2">
                    {metrics?.membership.total || 0}
                  </p>
                  <div className="flex items-center gap-1.5 mt-3">
                    <div className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800">
                      <TrendingUp className="w-3 h-3 text-emerald-600 dark:text-emerald-400" />
                      <span className="text-xs font-medium text-emerald-600 dark:text-emerald-400">Active</span>
                    </div>
                  </div>
                </div>
                <div className={cn(
                  "p-3 rounded-xl transition-all duration-300",
                  "bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800",
                  "group-hover:scale-110 group-hover:rotate-3"
                )}>
                  <Users className="w-6 h-6 text-blue-600 dark:text-blue-400" />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Credits Used */}
          <Card className={cn(
            "group relative overflow-hidden border-border/50 shadow-sm hover:shadow-md transition-all duration-300",

            "hover:border-emerald-200 dark:hover:border-emerald-800"
          )}>
            <CardContent className="p-4 px-8">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <CreditCard className="w-4 h-4 text-muted-foreground" />
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                      Credits Used
                    </p>
                  </div>
                  <p className="text-3xl font-bold text-brand-500 mt-2">
                    {metrics?.credits.used.toLocaleString() || 0}
                  </p>
                  <div className="flex items-center gap-1.5 mt-3">
                    <span className="text-xs text-muted-foreground">
                      of <span className="font-semibold text-brand-500">{metrics?.credits.total.toLocaleString() || 0}</span> total
                    </span>
                  </div>
                </div>
                <div className={cn(
                  "p-3 rounded-xl transition-all duration-300",
                  "bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800",
                  "group-hover:scale-110 group-hover:rotate-3"
                )}>
                  <CreditCard className="w-6 h-6 text-emerald-600 dark:text-emerald-400" />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Active Invitations */}
          <Card className={cn(
            "group relative overflow-hidden border-border/50 shadow-sm hover:shadow-md transition-all duration-300",

            "hover:border-purple-200 dark:hover:border-purple-800"
          )}>
            <CardContent className="p-4 px-8">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <Mail className="w-4 h-4 text-muted-foreground" />
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                      Invitations
                    </p>
                  </div>
                  <p className="text-3xl font-bold text-brand-500 mt-2">
                    {metrics?.invitations.sent || 0}
                  </p>
                  <div className="flex items-center gap-1.5 mt-3">
                    <Badge
                      variant="outline"
                      className="bg-emerald-50 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800 text-xs font-semibold"
                    >
                      {metrics?.invitations.accepted || 0} accepted
                    </Badge>
                  </div>
                </div>
                <div className={cn(
                  "p-3 rounded-xl transition-all duration-300",
                  "bg-purple-50 dark:bg-purple-950/30 border border-purple-200 dark:border-purple-800",
                  "group-hover:scale-110 group-hover:rotate-3"
                )}>
                  <Mail className="w-6 h-6 text-purple-600 dark:text-purple-400" />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Organization Status */}
          <Card className={cn(
            "group relative overflow-hidden border-border/50 shadow-sm hover:shadow-md transition-all duration-300",

            organization.status === 'active'
              ? "hover:border-emerald-200 dark:hover:border-emerald-800"
              : "hover:border-red-200 dark:hover:border-red-800"
          )}>
            <CardContent className="p-4 px-8">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <Shield className="w-4 h-4 text-muted-foreground" />
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                      Status
                    </p>
                  </div>
                  <div className="mt-2">
                    <Badge
                      variant="outline"
                      className={cn(
                        "text-sm font-semibold px-3 py-1",
                        organization.status === 'active'
                          ? 'bg-emerald-50 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800'
                          : 'bg-red-50 dark:bg-red-950/30 text-red-700 dark:text-red-300 border-red-200 dark:border-red-800'
                      )}
                    >
                      {organization.status}
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground mt-3 capitalize">
                    {organization.type === 'prepay_org' ? 'Prepayment' : 'Grant'} Organization
                  </p>
                </div>
                <div className={cn(
                  "p-3 rounded-xl transition-all duration-300",
                  organization.status === 'active'
                    ? "bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800"
                    : "bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800",
                  "group-hover:scale-110 group-hover:rotate-3"
                )}>
                  <Shield className={cn(
                    "w-6 h-6",
                    organization.status === 'active'
                      ? "text-emerald-600 dark:text-emerald-400"
                      : "text-red-600 dark:text-red-400"
                  )} />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Metrics */}
          <div className="lg:col-span-2 space-y-6">
            {/* Credit Metrics */}
            {metrics && metrics.credits && (
              <OrganizationMetricsCard
                metrics={metrics as StoreOrganizationMetrics}
                isLoading={loading}
              />
            )}

            {/* Invitation Analytics */}
            {metrics && (
              <InvitationAnalyticsPanel
                invitations={metrics.invitations}
                isLoading={loading}
              />
            )}
          </div>

          {/* Right Column - Info & Actions */}
          <div className="space-y-6">
            {/* Enhanced Organization Info */}
            <Card className="bg-white dark:bg-gray-900 backdrop-blur-sm border border-gray-200 dark:border-gray-800 shadow-sm rounded-2xl overflow-hidden">
              <CardHeader className="border-b border-gray-100 dark:border-gray-800">
                <CardTitle className="flex items-center space-x-3 text-lg text-gray-900 dark:text-white">
                  <div className="w-6 h-6 bg-gradient-to-br from-blue-100 to-blue-200 dark:from-blue-900/50 dark:to-blue-800/50 rounded-xl flex items-center justify-center border border-blue-200 dark:border-blue-700">
                    <Building2 className="w-4 h-4 text-brand-600 dark:text-brand-400" />
                  </div>
                  <span>Organization Details</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4 -mt-4 pt-6">
                {/* Description */}
                {organization.description && (
                  <div className="bg-gray-50 dark:bg-gray-900/50 rounded-xl p-4 border border-gray-100 dark:border-gray-700">
                    <p className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-2">Description</p>
                    <p className="text-sm text-gray-900 dark:text-gray-200 leading-relaxed">
                      {organization.description}
                    </p>
                  </div>
                )}

                <div className="space-y-4">
                  {/* Contact Information */}
                  <div className="space-y-3">
                    <h4 className="font-semibold text-brand-600 dark:text-brand-400 text-md">Contact Information</h4>

                    <div className="flex items-center space-x-3 p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors border border-transparent hover:border-gray-200 dark:hover:border-gray-700">
                      <div className="w-8 h-8 bg-brand-100 dark:bg-gray-900/30 rounded-lg flex items-center justify-center flex-shrink-0 border border-brand-200 dark:border-brand-800">
                        <Globe className="w-4 h-4 text-brand-600 dark:text-brand-400" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-gray-600 dark:text-gray-400">Website</p>
                        {organization.website ? (
                          <a
                            href={organization.website}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-sm text-blue-600 dark:text-blue-400 hover:underline truncate block font-medium"
                          >
                            {organization.website}
                          </a>
                        ) : (
                          <p className="text-sm text-gray-500 dark:text-gray-500">Not specified</p>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center space-x-3 p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors border border-transparent hover:border-gray-200 dark:hover:border-gray-700">
                      <div className="w-8 h-8 bg-green-100 dark:bg-green-900/30 rounded-lg flex items-center justify-center flex-shrink-0 border border-green-200 dark:border-green-800">
                        <Mail className="w-4 h-4 text-green-600 dark:text-green-400" />
                      </div>
                      <div>
                        <p className="text-sm text-gray-600 dark:text-gray-400">Contact Email</p>
                        <p className="text-sm text-gray-900 dark:text-gray-200 font-medium">
                          {organization.contact_email || 'Not specified'}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center space-x-3 p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors border border-transparent hover:border-gray-200 dark:hover:border-gray-700">
                      <div className="w-8 h-8 bg-purple-100 dark:bg-purple-900/30 rounded-lg flex items-center justify-center flex-shrink-0 border border-purple-200 dark:border-purple-800">
                        <Phone className="w-4 h-4 text-purple-600 dark:text-purple-400" />
                      </div>
                      <div>
                        <p className="text-sm text-gray-600 dark:text-gray-400">Phone</p>
                        <p className="text-sm text-gray-900 dark:text-gray-200 font-medium">
                          {organization.phone_number || 'Not specified'}
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Location & Details */}
                  <div className="space-y-3">
                    <h4 className="font-semibold text-brand-600 dark:text-brand-400 text-md">Location & Details</h4>

                    <div className="flex items-center space-x-3 p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors border border-transparent hover:border-gray-200 dark:hover:border-gray-700">
                      <div className="w-8 h-8 bg-orange-100 dark:bg-orange-900/30 rounded-lg flex items-center justify-center flex-shrink-0 border border-orange-200 dark:border-orange-800">
                        <MapPin className="w-4 h-4 text-orange-600 dark:text-orange-400" />
                      </div>
                      <div>
                        <p className="text-sm text-gray-600 dark:text-gray-400">Location</p>
                        <p className="text-sm text-gray-900 dark:text-gray-200 font-medium">
                          {organization.city || 'N/A'}, {organization.country || 'N/A'}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center space-x-3 p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors border border-transparent hover:border-gray-200 dark:hover:border-gray-700">
                      <div className="w-8 h-8 bg-indigo-100 dark:bg-indigo-900/30 rounded-lg flex items-center justify-center flex-shrink-0 border border-indigo-200 dark:border-indigo-800">
                        <Calendar className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
                      </div>
                      <div>
                        <p className="text-sm text-gray-600 dark:text-gray-400">Created</p>
                        <p className="text-sm text-gray-900 dark:text-gray-200 font-medium">
                          {formatDate(organization.created_at)}
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Industry & Size */}
                  <div className="grid grid-cols-2 gap-4 pt-2">
                    <div className="bg-gray-50 dark:bg-gray-900/50 rounded-xl p-4 border border-gray-100 dark:border-gray-700">
                      <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">Industry</p>
                      <Badge variant="secondary" className="bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300 border border-blue-200 dark:border-blue-800 px-3 py-1 rounded-full text-sm">
                        {organization.industry || 'N/A'}
                      </Badge>
                    </div>
                    <div className="bg-gray-50 dark:bg-gray-900/50 rounded-xl p-4 border border-gray-100 dark:border-gray-700">
                      <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">Size</p>
                      <Badge variant="secondary" className="bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-300 border border-green-200 dark:border-green-800 px-3 py-1 rounded-full text-sm">
                        {getOrganizationSizeLabel(organization.size || '')}
                      </Badge>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>


          </div>
        </div>
      </div>
    </div>
  );
}