"use client";

import React, { useState, useEffect } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import { organizationService } from '@/lib/api/organizationService';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { MemberInviteForm } from '@/components/admin/MemberInviteForm';
import { useAuthStore } from '@/stores/authStore';
import { toast } from 'react-hot-toast';
import { ArrowLeft, Info, Users, Crown, CreditCard } from 'lucide-react';
import { useSetCurrentOrganization, useSetOrganizationMetrics } from '@/stores/organizationStore';

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
  status: 'active' | 'suspended' | 'frozen';
  // Backend API fields
  total_credits?: number;
  used_credits?: number;
  current_monthly_usage?: number; // Legacy field for backward compatibility
}

export default function InviteMembersPage() {
  const router = useRouter();
  const params = useParams();
  const organizationId = params.id as string;
  const { isAuthenticated } = useAuthStore();
  const setCurrentOrganization = useSetCurrentOrganization();
  const setOrganizationMetrics = useSetOrganizationMetrics();

  const [organization, setOrganization] = useState<Organization | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // if (!isAuthenticated) {
    //   router.push('/signin?redirect=/admin/organizations/' + organizationId + '/invite-members');
    //   return;
    // }

    if (organizationId) {
      fetchOrganizationData();
    }
  }, [organizationId, isAuthenticated]);

  const fetchOrganizationData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch organization details
      // Try the new organization-specific endpoint first, fallback to list endpoint
      let org;
      try {
        if (typeof organizationService.getOrganizationById === 'function') {
          org = await organizationService.getOrganizationById(organizationId);
        } else {
          // Fallback to the list endpoint and find the organization
          const organizations = await organizationService.fetchOrganizations();
          org = organizations.find((o: any) => o.id === organizationId) || null;
        }
      } catch (error) {
        // If the new endpoint fails, try the fallback
        console.warn('getOrganizationById failed, trying fallback:', error);
        const organizations = await organizationService.fetchOrganizations();
        org = organizations.find((o: any) => o.id === organizationId) || null;
      }

      if (!org) {
        throw new Error('Organization not found');
      }

      setOrganization(org);
      setCurrentOrganization(org);

      // Fetch organization metrics
      const metrics = await organizationService.getOrganizationMetrics(organizationId);

      // FIXED: Calculate credit metrics using correct backend field names
      const creditMetrics = {
        total: org?.total_credits || org?.monthly_credit_limit || 0,
        used: org?.used_credits || org?.current_monthly_usage || 0,
        remaining: (org?.total_credits || org?.monthly_credit_limit || 0) - (org?.used_credits || org?.current_monthly_usage || 0),
        monthly_limit: org?.total_credits || org?.monthly_credit_limit || 0,
      };

      // Combine metrics
      const fullMetrics = {
        ...metrics,
        credits: creditMetrics,
      };

      setOrganizationMetrics(fullMetrics);
    } catch (err: any) {
      console.error('Error fetching organization data:', err);
      setError(err.message || 'Failed to fetch organization data');
      toast.error(err.message || 'Failed to fetch organization data');
    } finally {
      setLoading(false);
    }
  };

  const handleBack = () => {
    router.push(`/admin/organizations/${organizationId}`);
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-500"></div>
      </div>
    );
  }

  if (error || !organization) {
    return (
      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6">
        <div className="text-red-800 dark:text-red-200">
          <h3 className="font-medium">Error loading organization</h3>
          <p className="mt-1 text-sm">{error || 'Organization not found'}</p>
          <button
            onClick={handleBack}
            className="mt-3 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 text-sm"
          >
            Back to Organization
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Enhanced Header */}
      <div className="bg-gradient-to-r from-brand-50 to-indigo-50 dark:from-brand-950/30 dark:to-indigo-950/30 -mx-6 -mt-6 px-6 py-6 mb-6 border-b border-brand-100 dark:border-brand-900/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button
              variant="outline"
              size="icon"
              onClick={handleBack}
              className="bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              <ArrowLeft className="w-4 h-4" />
            </Button>
            <div>
              <div className="flex items-center gap-3 mb-1">
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                  Invite Members
                </h1>
                <Badge className={
                  organization.type === 'prepay_org'
                    ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                    : 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
                }>
                  {organization.type === 'prepay_org' ? 'Prepayment' : 'Grant'}
                </Badge>
              </div>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Add individual members and team leaders to <span className="font-medium text-gray-900 dark:text-white">{organization.name}</span>
              </p>
            </div>
          </div>

          {/* Credits Info */}
          {organization.type === 'grant_org' && organization.monthly_credit_limit && (
            <div className="flex items-center gap-3 bg-white dark:bg-gray-800 rounded-lg px-4 py-2 border border-brand-200 dark:border-brand-800">
              <CreditCard className="w-5 h-5 text-brand-500" />
              <div className="text-right">
                <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Monthly Limit</p>
                <p className="text-lg font-bold text-brand-600 dark:text-brand-400">{organization.monthly_credit_limit.toLocaleString()}</p>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Form */}
        <div className="lg:col-span-2">
          <MemberInviteForm organizationId={organizationId} />
        </div>

        {/* Info Panel */}
        <div className="space-y-6">
          {/* Member Types Info */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Info className="w-5 h-5" />
                <span>Member Types</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <div className="flex items-center space-x-2">
                  <Users className="w-4 h-4 text-brand-500" />
                  <span className="text-sm font-medium">Individual Members</span>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Regular members who can use credits for their own work. Choose from 150, 200, or 250 credit packages.
                </p>
              </div>

              <div className="space-y-2">
                <div className="flex items-center space-x-2">
                  <Crown className="w-4 h-4 text-yellow-500" />
                  <span className="text-sm font-medium">Team Leaders</span>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Leaders who can create teams and manage credit pools. Choose from packages ranging from 200 to 800 credits.
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Credit Packages Info */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <CreditCard className="w-5 h-5" />
                <span>Credit Packages</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <p className="text-sm font-medium mb-2">Individual Members</p>
                <div className="space-y-1">
                  <Badge variant="outline" className="justify-center">100 credits</Badge>
                  <Badge variant="outline" className="justify-center">200 credits</Badge>
                  <Badge variant="outline" className="justify-center">300 credits</Badge>
                  <Badge variant="outline" className="justify-center">400 credits</Badge>
                  <Badge variant="outline" className="justify-center">500 credits</Badge>
                  <Badge variant="outline" className="justify-center">600 credits</Badge>
                  <Badge variant="outline" className="justify-center">700 credits</Badge>
                  <Badge variant="outline" className="justify-center">800 credits</Badge>
                </div>
              </div>
              <div>
                <p className="text-sm font-medium mb-2">Team Leaders</p>
                <div className="grid grid-cols-2 gap-1">
                  <Badge variant="outline" className="justify-center">200 credits</Badge>
                  <Badge variant="outline" className="justify-center">300 credits</Badge>
                  <Badge variant="outline" className="justify-center">400 credits</Badge>
                  <Badge variant="outline" className="justify-center">500 credits</Badge>
                  <Badge variant="outline" className="justify-center">600 credits</Badge>
                  <Badge variant="outline" className="justify-center">700 credits</Badge>
                  <Badge variant="outline" className="justify-center">800 credits</Badge>
                </div>
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
                  <p className="text-sm font-medium">Invitations Sent</p>
                  <p className="text-xs text-gray-600 dark:text-gray-400">
                    Email invitations sent to all members
                  </p>
                </div>
              </div>

              <div className="flex items-start space-x-3">
                <div className="w-6 h-6 rounded-full bg-brand-500 text-white text-xs flex items-center justify-center font-medium">
                  2
                </div>
                <div>
                  <p className="text-sm font-medium">Account Setup</p>
                  <p className="text-xs text-gray-600 dark:text-gray-400">
                    Members create accounts and join
                  </p>
                </div>
              </div>

              <div className="flex items-start space-x-3">
                <div className="w-6 h-6 rounded-full bg-brand-500 text-white text-xs flex items-center justify-center font-medium">
                  3
                </div>
                <div>
                  <p className="text-sm font-medium">Credits Allocated</p>
                  <p className="text-xs text-gray-600 dark:text-gray-400">
                    Credits automatically allocated upon joining
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
