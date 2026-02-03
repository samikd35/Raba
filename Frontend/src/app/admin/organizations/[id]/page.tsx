"use client";

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { organizationService } from '@/lib/api/organizationService';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useAuthStore } from '@/stores/authStore';
import { toast } from "react-hot-toast";
import { OrganizationMetricsCard } from '@/components/admin/OrganizationMetricsCard';
import { InvitationAnalyticsPanel } from '@/components/admin/InvitationAnalyticsPanel';
import { OrganizationMetrics as StoreOrganizationMetrics } from '@/stores/organizationStore';

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
  // Backend API fields
  total_credits?: number;
  used_credits?: number;
  current_monthly_usage?: number; // Legacy field for backward compatibility
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
  const params = useParams();
  const organizationId = params.id as string;
  const { isAuthenticated } = useAuthStore();
  
  const [organization, setOrganization] = useState<Organization | null>(null);
  const [metrics, setMetrics] = useState<OrganizationMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // if (!isAuthenticated) {
    //   router.push('/signin?redirect=/admin/organizations/' + organizationId);
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
      
      // Fetch organization details using the dedicated endpoint
      const org = await organizationService.getOrganizationById(organizationId);
      setOrganization(org);
      
      // Debug: Log the organization data to see what fields are available
      console.log('🔍 Organization Data:', org);
      console.log('🔍 Organization Fields:', {
        contact_email: org?.contact_email,
        phone_number: org?.phone_number,
        city: org?.city,
        country: org?.country,
        website: org?.website,
        industry: org?.industry,
        size: org?.size,
        description: org?.description,
      });
      
      // Fetch organization metrics
      const orgMetrics = await organizationService.getOrganizationMetrics(organizationId);
      
      // Debug: Log the metrics data
      console.log('🔍 Organization Metrics:', orgMetrics);
      console.log('🔍 Credits Data:', orgMetrics.credits);
      
      // Use credit metrics from API response (which should have the correct data)
      const fullMetrics = {
        ...orgMetrics,
        credits: orgMetrics.credits || {
          total: 0,
          used: 0,
          remaining: 0,
          monthly_limit: 0,
        },
      };
      
      setMetrics(fullMetrics);
    } catch (err: any) {
      console.error('Error fetching organization data:', err);
      setError(err.message || 'Failed to fetch organization data');
      toast.error(err.message || 'Failed to fetch organization data');
    } finally {
      setLoading(false);
    }
  };

  const handleBack = () => {
    router.push('/admin/organizations');
  };

  const handleRefresh = () => {
    fetchOrganizationData();
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6">
        <div className="text-red-800 dark:text-red-200">
          <h3 className="font-medium">Error loading organization</h3>
          <p className="mt-1 text-sm">{error}</p>
          <div className="flex space-x-3 mt-3">
            <button
              onClick={handleBack}
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 text-sm"
            >
              Back to Organizations
            </button>
            <button
              onClick={fetchOrganizationData}
              className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 text-sm"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!organization) {
    return (
      <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-6">
        <div className="text-yellow-800 dark:text-yellow-200">
          <h3 className="font-medium">Organization not found</h3>
          <p className="mt-1 text-sm">The organization with ID "{organizationId}" could not be found.</p>
          <button
            onClick={handleBack}
            className="mt-3 px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 text-sm"
          >
            Back to Organizations
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Button 
            variant="ghost" 
            size="icon"
            onClick={handleBack}
          >
            <span className="text-lg">⬅️</span>
          </Button>
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
              {organization.name}
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mt-1">
              Organization details and metrics
            </p>
          </div>
        </div>
        <Button onClick={handleRefresh}>
          <span className="text-lg mr-2">🔄</span>
          Refresh
        </Button>
      </div>

      {/* Organization Info */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <span className="text-lg">🏢</span>
            <span>Organization Information</span>
          </CardTitle>
          <CardDescription>
            Basic information about the organization
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Description Section (if available) */}
          {organization.description && (
            <div>
              <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">Description</h3>
              <p className="text-gray-700 dark:text-gray-300">{organization.description}</p>
            </div>
          )}

          {/* Two Column Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-4">
              <div>
                <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">Organization ID</h3>
                <p className="font-mono text-sm">{organization.id}</p>
              </div>
              <div>
                <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">Name</h3>
                <p className="font-medium">{organization.name}</p>
              </div>
              <div>
                <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">Industry</h3>
                <p className="font-medium">{organization.industry || 'Not specified'}</p>
              </div>
              <div>
                <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">Organization Size</h3>
                <p className="font-medium">
                  {organization.size ? (
                    organization.size === 'startup' ? 'Startup (1-10 employees)' :
                    organization.size === 'small' ? 'Small (11-50 employees)' :
                    organization.size === 'medium' ? 'Medium (51-200 employees)' :
                    organization.size === 'large' ? 'Large (201-1000 employees)' :
                    organization.size === 'enterprise' ? 'Enterprise (1000+ employees)' :
                    organization.size
                  ) : 'Not specified'}
                </p>
              </div>
              <div>
                <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">Contact Email</h3>
                <p className="font-medium">{organization.contact_email || 'Not specified'}</p>
              </div>
              <div>
                <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">Phone Number</h3>
                <p className="font-medium">{organization.phone_number || 'Not specified'}</p>
              </div>
            </div>
            <div className="space-y-4">
              <div>
                <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">Location</h3>
                <p className="font-medium">{organization.city || 'Not specified'}, {organization.country || 'Not specified'}</p>
              </div>
              <div>
                <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">Website</h3>
                {organization.website ? (
                  <a 
                    href={organization.website} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="font-medium text-blue-600 dark:text-blue-400 hover:underline"
                  >
                    {organization.website}
                  </a>
                ) : (
                  <p className="font-medium">Not specified</p>
                )}
              </div>
              <div>
                <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">Type</h3>
                <Badge className={
                  organization.type === 'prepay_org' 
                    ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' 
                    : 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
                }>
                  {organization.type === 'prepay_org' ? 'Prepayment' : 'Grant'}
                </Badge>
              </div>
              <div>
                <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">Status</h3>
                <Badge className={
                  organization.status === 'active' 
                    ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' 
                    : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                }>
                  {organization.status}
                </Badge>
              </div>
              <div>
                <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">Created</h3>
                <p className="font-medium">{new Date(organization.created_at).toLocaleDateString()}</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

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

      {/* Membership Metrics */}
      {metrics && (
        <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <span className="text-lg">👥</span>
                <span>Membership Metrics</span>
              </CardTitle>
              <CardDescription>
                Organization membership statistics
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-gray-600 dark:text-gray-400">Total Members</span>
                <span className="text-xl font-bold">{metrics.membership.total}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-600 dark:text-gray-400">Team Members</span>
                <span className="text-xl font-bold">{metrics.membership.team_members}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-600 dark:text-gray-400">Individual Members</span>
                <span className="text-xl font-bold">{metrics.membership.individual_members}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-600 dark:text-gray-400">Average Team Size</span>
                <span className="text-xl font-bold">
                  {metrics.membership.team_members > 0 
                    ? (metrics.membership.team_members / Math.max(1, metrics.membership.team_members)).toFixed(1)
                    : '0'}
                </span>
              </div>
            </CardContent>
          </Card>
      )}

      {/* Actions */}
      <div className="flex space-x-4">
        <Button onClick={() => router.push(`/admin/organizations/${organizationId}/invite-members`)}>
          <span className="text-lg mr-2">📤</span>
          Invite Members
        </Button>
        <Button variant="outline" onClick={handleRefresh}>
          <span className="text-lg mr-2">🔄</span>
          Refresh Data
        </Button>
      </div>
    </div>
  );
}