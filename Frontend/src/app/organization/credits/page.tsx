"use client";

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { organizationService } from '@/lib/api/organizationService';
import { 
  CreditRequestService, 
  CreditRequest, 
  CreditRequestListResponse 
} from '@/lib/api/creditRequestService';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useAuthStore } from '@/stores/authStore';
import { toast } from "react-hot-toast";
import { 
  CreditCard, 
  TrendingUp, 
  TrendingDown, 
  Calendar, 
  DollarSign, 
  AlertCircle, 
  Plus, 
  Pause, 
  Play, 
  ArrowLeft,
  RefreshCw,
  Download,
  BarChart3,
  Zap,
  Clock,
  Shield,
  X,
  CheckCircle,
  XCircle,
  Eye,
  MoreVertical,
  Send,
  Users
} from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

interface CreditLot {
  id: string;
  credit_amount: number;
  original_amount: number;
  source: string;
  valid_from: string;
  expires_at: string | null;
  is_active: boolean;
  created_at: string;
  metadata?: any;
}

interface CreditMetrics {
  total: number;
  used: number;
  remaining: number;
  monthly_limit: number | null;
}

interface OrganizationMetrics {
  credits: CreditMetrics;
}

export default function OrganizationCreditsPage() {
  const router = useRouter();
     const { user, isAuthenticated,token } = useAuthStore();
     const currentWorkspaceTenantId = user?.tenant_id;
  
  // Get organization ID from current workspace
  const organizationId = currentWorkspaceTenantId;
  
  const [creditLots, setCreditLots] = useState<CreditLot[]>([]);
  const [metrics, setMetrics] = useState<CreditMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);
  const [activeTab, setActiveTab] = useState<'overview' | 'lots' | 'requests'>('overview');
  
  // Credit Request State
  const [creditRequests, setCreditRequests] = useState<CreditRequest[]>([]);
  const [pendingRequestsCount, setPendingRequestsCount] = useState(0);
  const [showRequestModal, setShowRequestModal] = useState(false);
  const [showReviewModal, setShowReviewModal] = useState(false);
  const [selectedRequest, setSelectedRequest] = useState<CreditRequest | null>(null);
  const [requestFormData, setRequestFormData] = useState({
    requested_amount: '',
    reason: '',
    urgency: 'normal' as 'normal' | 'high' | 'urgent',
  });
  const [isSubmittingRequest, setIsSubmittingRequest] = useState(false);
  const [reviewFormData, setReviewFormData] = useState({
    status: 'approved' as 'approved' | 'rejected',
    review_notes: '',
  });

  const fetchCreditsData = useCallback(async () => {
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
        console.log('🏢 Fetching credits data for organization ID:', organizationId);
      }
      
      // Fetch organization metrics for credit summary
      const metricsData = await organizationService.getOrganizationMetrics(organizationId);
      setMetrics(metricsData.credits || null);

      // Fetch credit lots
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/organization/${organizationId}/lots/issued`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch credit lots: ${response.status}`);
      }

      const lotsData = await response.json();
      setCreditLots(lotsData.lots || []);
      
      if (process.env.NODE_ENV === 'development') {
        console.log('✅ Credits data loaded successfully');
      }
      
      // Fetch credit requests for the organization
      try {
        const requestsData = await CreditRequestService.getOrganizationCreditRequests(organizationId);
        setCreditRequests(requestsData.requests || []);
        setPendingRequestsCount(requestsData.pending_count || 0);
        
        if (process.env.NODE_ENV === 'development') {
          console.log('✅ Credit requests loaded:', requestsData.total_count);
        }
      } catch (reqError) {
        // Don't fail the whole page if credit requests fail to load
        console.warn('Failed to load credit requests:', reqError);
        setCreditRequests([]);
        setPendingRequestsCount(0);
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load credits data';
      
      if (process.env.NODE_ENV === 'development') {
        console.error('❌ Error fetching credits data:', error);
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
      toast.error('Failed to load credits data');
      
      // Auto-retry logic for network errors
      if (retryCount < 3 && (errorMessage.includes('Network') || errorMessage.includes('fetch'))) {
        const retryDelay = Math.pow(2, retryCount) * 1000; // Exponential backoff
        setTimeout(() => {
          setRetryCount(prev => prev + 1);
          fetchCreditsData();
        }, retryDelay);
      }
    } finally {
      setLoading(false);
    }
  }, [organizationId, isAuthenticated, token, retryCount, router]);

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

    fetchCreditsData();
  }, [isAuthenticated, organizationId, fetchCreditsData, router]);

  // Statistics
  const stats = useMemo(() => {
    if (!metrics) return null;

    const usagePercentage = metrics.total > 0 ? (metrics.used / metrics.total) * 100 : 0;
    const monthlyLimitUsage = metrics.monthly_limit ? (metrics.used / metrics.monthly_limit) * 100 : 0;
    const activeLots = creditLots.filter(lot => lot.is_active).length;
    const totalLotsValue = creditLots.reduce((sum, lot) => sum + lot.credit_amount, 0);
    const expiringSoon = creditLots.filter(lot => {
      if (!lot.expires_at) return false;
      const expiryDate = new Date(lot.expires_at);
      const today = new Date();
      const daysUntilExpiry = Math.ceil((expiryDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
      return daysUntilExpiry <= 30 && daysUntilExpiry > 0;
    }).length;

    return {
      usagePercentage,
      monthlyLimitUsage,
      activeLots,
      totalLotsValue,
      expiringSoon,
    };
  }, [metrics, creditLots]);

  const handleBack = useCallback(() => {
    router.push('/organization');
  }, [router]);

  const handleRefresh = useCallback(() => {
    fetchCreditsData();
    toast.success('Credits data refreshed');
  }, [fetchCreditsData]);

  const handleRetry = useCallback(() => {
    setRetryCount(0);
    fetchCreditsData();
  }, [fetchCreditsData]);

  const handleBackToWorkspaces = useCallback(() => {
    router.push('/choose-workspace');
  }, [router]);

  const handleSuspendLot = useCallback(async (lotId: string, lotName: string) => {
    if (!confirm(`Are you sure you want to suspend credit lot ${lotName}? This will prevent any further usage of these credits.`)) {
      return;
    }

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/organization/${organizationId}/lots/${lotId}/suspend`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to suspend credit lot: ${response.status}`);
      }

      toast.success('Credit lot suspended successfully');
      fetchCreditsData(); // Refresh data
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to suspend credit lot';
      if (process.env.NODE_ENV === 'development') {
        console.error('Error suspending credit lot:', error);
      }
      toast.error(errorMessage);
    }
  }, [organizationId, token, fetchCreditsData]);

  const handleFreezeLot = useCallback(async (lotId: string, lotName: string) => {
    if (!confirm(`Are you sure you want to freeze credit lot ${lotName}? This will temporarily disable these credits.`)) {
      return;
    }

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/organization/${organizationId}/lots/${lotId}/freeze`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to freeze credit lot: ${response.status}`);
      }

      toast.success('Credit lot frozen successfully');
      fetchCreditsData(); // Refresh data
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to freeze credit lot';
      if (process.env.NODE_ENV === 'development') {
        console.error('Error freezing credit lot:', error);
      }
      toast.error(errorMessage);
    }
  }, [organizationId, token, fetchCreditsData]);

  const handleActivateLot = useCallback(async (lotId: string, lotName: string) => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/organization/${organizationId}/lots/${lotId}/activate`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to activate credit lot: ${response.status}`);
      }

      toast.success('Credit lot activated successfully');
      fetchCreditsData(); // Refresh data
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to activate credit lot';
      if (process.env.NODE_ENV === 'development') {
        console.error('Error activating credit lot:', error);
      }
      toast.error(errorMessage);
    }
  }, [organizationId, token, fetchCreditsData]);

  // Request Credits from Yuba (for grant organizations)
  const handleRequestCreditsFromYuba = useCallback(async () => {
    if (!organizationId) {
      toast.error('Organization ID not available');
      return;
    }

    const amount = parseInt(requestFormData.requested_amount);
    if (!amount || amount <= 0) {
      toast.error('Please enter a valid credit amount');
      return;
    }

    if (!requestFormData.reason || requestFormData.reason.length < 10) {
      toast.error('Please provide a reason (at least 10 characters)');
      return;
    }

    setIsSubmittingRequest(true);
    try {
      const result = await CreditRequestService.requestCreditsFromYuba(organizationId, {
        requested_amount: amount,
        reason: requestFormData.reason,
        urgency: requestFormData.urgency,
      });

      toast.success(result.message || 'Credit request submitted to Yuba');
      setShowRequestModal(false);
      setRequestFormData({ requested_amount: '', reason: '', urgency: 'normal' });
      fetchCreditsData(); // Refresh data
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to submit credit request';
      toast.error(errorMessage);
    } finally {
      setIsSubmittingRequest(false);
    }
  }, [organizationId, requestFormData, fetchCreditsData]);

  // Review Credit Request (approve/reject)
  const handleReviewCreditRequest = useCallback(async () => {
    if (!organizationId || !selectedRequest) {
      toast.error('Missing required information');
      return;
    }

    if (reviewFormData.status === 'rejected' && !reviewFormData.review_notes.trim()) {
      toast.error('Please provide a reason for rejection');
      return;
    }

    setIsSubmittingRequest(true);
    try {
      await CreditRequestService.updateCreditRequestStatus(
        organizationId,
        selectedRequest.id,
        {
          status: reviewFormData.status,
          review_notes: reviewFormData.review_notes.trim() || undefined,
        }
      );

      toast.success(`Credit request ${reviewFormData.status}`);
      setShowReviewModal(false);
      setSelectedRequest(null);
      setReviewFormData({ status: 'approved', review_notes: '' });
      fetchCreditsData(); // Refresh data
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to review credit request';
      toast.error(errorMessage);
    } finally {
      setIsSubmittingRequest(false);
    }
  }, [organizationId, selectedRequest, reviewFormData, fetchCreditsData]);

  // Open review modal
  const handleOpenReviewModal = useCallback((request: CreditRequest) => {
    setSelectedRequest(request);
    setReviewFormData({ status: 'approved', review_notes: '' });
    setShowReviewModal(true);
  }, []);

  // Get status badge color
  const getRequestStatusColor = useCallback((status: string) => {
    switch (status) {
      case 'pending':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200';
      case 'approved':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
      case 'rejected':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
      case 'fulfilled':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200';
    }
  }, []);

  const getSourceColor = useCallback((source: string) => {
    switch (source.toLowerCase()) {
      case 'grant':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
      case 'purchase':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200';
      case 'transfer':
        return 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200';
      case 'invitation':
        return 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200';
      case 'bonus':
        return 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900 dark:text-cyan-200';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200';
    }
  }, []);

  const getSourceIcon = useCallback((source: string) => {
    switch (source.toLowerCase()) {
      case 'grant':
        return <Shield className="w-4 h-4" />;
      case 'purchase':
        return <DollarSign className="w-4 h-4" />;
      case 'transfer':
        return <RefreshCw className="w-4 h-4" />;
      case 'invitation':
        return <Zap className="w-4 h-4" />;
      case 'bonus':
        return <TrendingUp className="w-4 h-4" />;
      default:
        return <CreditCard className="w-4 h-4" />;
    }
  }, []);

  const getStatusColor = useCallback((isActive: boolean) => {
    return isActive 
      ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
      : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
  }, []);

  const getUsageColor = useCallback((percentage: number) => {
    if (percentage >= 90) return 'bg-red-500';
    if (percentage >= 75) return 'bg-yellow-500';
    return 'bg-blue-500';
  }, []);

  const formatDate = useCallback((dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  }, []);

  const getDaysUntilExpiry = useCallback((expiresAt: string | null) => {
    if (!expiresAt) return null;
    const expiryDate = new Date(expiresAt);
    const today = new Date();
    const diffTime = expiryDate.getTime() - today.getTime();
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  }, []);

  const getExpiryColor = useCallback((days: number | null) => {
    if (days === null) return 'text-gray-500';
    if (days <= 0) return 'text-red-600';
    if (days <= 7) return 'text-red-500';
    if (days <= 30) return 'text-yellow-500';
    return 'text-green-500';
  }, []);

  // Loading State
  if (loading) {
    return (
      <div className="space-y-6">
        {/* Header Skeleton */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Skeleton className="h-10 w-10 rounded-md" />
            <div className="space-y-2">
              <Skeleton className="h-8 w-64" />
              <Skeleton className="h-4 w-96" />
            </div>
          </div>
          <div className="flex space-x-3">
            <Skeleton className="h-10 w-24" />
            <Skeleton className="h-10 w-40" />
          </div>
        </div>

        {/* Stats Skeleton */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>

        {/* Progress Skeleton */}
        <Skeleton className="h-32 w-full" />

        {/* Tabs Skeleton */}
        <div className="space-y-4">
          <div className="flex space-x-4 border-b">
            <Skeleton className="h-10 w-32" />
            <Skeleton className="h-10 w-32" />
          </div>
          <Skeleton className="h-64 w-full" />
        </div>
      </div>
    );
  }

  // Error State
  if (error) {
    return (
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center space-x-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={handleBack}
          >
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
              Credits & Billing
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mt-1">
              Manage organization credit allocation and usage
            </p>
          </div>
        </div>

        {/* Error Card */}
        <Card className="border-red-200 dark:border-red-800">
          <CardContent className="pt-6">
            <div className="flex items-start space-x-4">
              <AlertCircle className="w-6 h-6 text-red-500 mt-0.5" />
              <div className="flex-1">
                <h3 className="font-semibold text-red-800 dark:text-red-200">
                  Unable to Load Credits Data
                </h3>
                <p className="text-red-700 dark:text-red-300 mt-1">
                  {error}
                </p>
                <div className="flex space-x-3 mt-4">
                  <Button onClick={handleRetry} className="flex items-center space-x-2">
                    <RefreshCw className="w-4 h-4" />
                    <span>Try Again</span>
                  </Button>
                  <Button variant="outline" onClick={handleBackToWorkspaces}>
                    Back to Workspaces
                  </Button>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
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
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
              Credits & Billing
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mt-1">
              Manage organization credit allocation and usage
            </p>
          </div>
        </div>
        <div className="flex space-x-3">
          <Button 
            variant="outline" 
            onClick={handleRefresh}
            className="flex items-center space-x-2"
          >
            <RefreshCw className="w-4 h-4" />
            <span>Refresh</span>
          </Button>
          <Button 
            onClick={() => setShowRequestModal(true)}
            className="flex items-center space-x-2"
          >
            <Plus className="w-4 h-4" />
            <span>Request Credits from Yuba</span>
          </Button>
        </div>
      </div>

      {/* Credit Summary */}
      {metrics && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center space-x-3">
                <div className="w-12 h-12 bg-blue-100 dark:bg-blue-900 rounded-lg flex items-center justify-center">
                  <CreditCard className="w-6 h-6 text-blue-600 dark:text-blue-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {metrics.total.toLocaleString()}
                  </p>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Total Credits</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center space-x-3">
                <div className="w-12 h-12 bg-red-100 dark:bg-red-900 rounded-lg flex items-center justify-center">
                  <TrendingUp className="w-6 h-6 text-red-600 dark:text-red-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {metrics.used.toLocaleString()}
                  </p>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Credits Used</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center space-x-3">
                <div className="w-12 h-12 bg-green-100 dark:bg-green-900 rounded-lg flex items-center justify-center">
                  <TrendingDown className="w-6 h-6 text-green-600 dark:text-green-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {metrics.remaining.toLocaleString()}
                  </p>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Remaining</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center space-x-3">
                <div className="w-12 h-12 bg-purple-100 dark:bg-purple-900 rounded-lg flex items-center justify-center">
                  <Calendar className="w-6 h-6 text-purple-600 dark:text-purple-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {metrics.monthly_limit ? metrics.monthly_limit.toLocaleString() : '∞'}
                  </p>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Monthly Limit</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Credit Usage Progress */}
      {metrics && metrics.total > 0 && stats && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <BarChart3 className="w-5 h-5" />
                <span>Credit Usage</span>
              </CardTitle>
              <CardDescription>Current credit consumption across the organization</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600 dark:text-gray-400">Used: {metrics.used.toLocaleString()}</span>
                  <span className="text-gray-600 dark:text-gray-400">Remaining: {metrics.remaining.toLocaleString()}</span>
                </div>
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3">
                  <div 
                    className={`h-3 rounded-full transition-all duration-500 ${getUsageColor(stats.usagePercentage)}`}
                    style={{ width: `${stats.usagePercentage}%` }}
                  ></div>
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {Math.round(stats.usagePercentage)}% of total credits used
                </p>
              </div>
              
              {metrics.monthly_limit && (
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600 dark:text-gray-400">Monthly Limit Usage</span>
                    <span className="text-gray-600 dark:text-gray-400">{Math.round(stats.monthlyLimitUsage)}%</span>
                  </div>
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                    <div 
                      className={`h-2 rounded-full transition-all duration-500 ${getUsageColor(stats.monthlyLimitUsage)}`}
                      style={{ width: `${stats.monthlyLimitUsage}%` }}
                    ></div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Quick Stats */}
          <Card>
            <CardHeader>
              <CardTitle>Credit Overview</CardTitle>
              <CardDescription>Credit allocation summary</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-gray-600 dark:text-gray-400">Active Credit Lots</span>
                <span className="font-semibold">{stats.activeLots}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-600 dark:text-gray-400">Total Lots Value</span>
                <span className="font-semibold">{stats.totalLotsValue.toLocaleString()}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-600 dark:text-gray-400">Lots Expiring Soon</span>
                <span className="font-semibold">{stats.expiringSoon}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-600 dark:text-gray-400">Daily Usage Rate</span>
                <span className="font-semibold">~{Math.round(metrics.used / 30)}/day</span>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tab Navigation */}
      <div className="flex space-x-1 border-b border-gray-200 dark:border-gray-700">
        <button
          onClick={() => setActiveTab('overview')}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'overview'
              ? 'border-blue-500 text-blue-600 dark:text-blue-400'
              : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
          }`}
        >
          Overview
        </button>
        <button
          onClick={() => setActiveTab('lots')}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'lots'
              ? 'border-blue-500 text-blue-600 dark:text-blue-400'
              : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
          }`}
        >
          Credit Lots ({creditLots.length})
        </button>
        <button
          onClick={() => setActiveTab('requests')}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors flex items-center space-x-2 ${
            activeTab === 'requests'
              ? 'border-blue-500 text-blue-600 dark:text-blue-400'
              : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
          }`}
        >
          <span>Credit Requests</span>
          {pendingRequestsCount > 0 && (
            <Badge className="bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200">
              {pendingRequestsCount}
            </Badge>
          )}
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === 'requests' ? (
        // Credit Requests Tab
        <Card>
          <CardHeader className="pb-4">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <CardTitle className="flex items-center space-x-2 text-xl">
                <Users className="w-5 h-5" />
                <span>Member Credit Requests</span>
              </CardTitle>
              {pendingRequestsCount > 0 && (
                <Badge className="bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200">
                  {pendingRequestsCount} Pending
                </Badge>
              )}
            </div>
            <CardDescription>
              Review and manage credit requests from team members and individuals
            </CardDescription>
          </CardHeader>
          <CardContent>
            {creditRequests.length === 0 ? (
              <div className="text-center py-12">
                <div className="w-16 h-16 bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Clock className="w-8 h-8 text-gray-400" />
                </div>
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                  No credit requests yet
                </h3>
                <p className="text-gray-500 dark:text-gray-400 max-w-md mx-auto">
                  When team members or individuals request additional credits, they will appear here for your review.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {/* Pending Requests First */}
                {creditRequests.filter(r => r.status === 'pending').length > 0 && (
                  <div className="space-y-3">
                    <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Pending Requests</h3>
                    {creditRequests.filter(r => r.status === 'pending').map((request) => (
                      <div
                        key={request.id}
                        className="border border-yellow-200 dark:border-yellow-800 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg p-4"
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="flex items-center space-x-3 mb-2">
                              <h4 className="font-medium text-gray-900 dark:text-white">
                                {request.user_name || request.user_email || 'Unknown User'}
                              </h4>
                              <Badge className="bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                                {request.requested_amount.toLocaleString()} credits
                              </Badge>
                              {request.team_name && (
                                <Badge variant="outline">
                                  Team: {request.team_name}
                                </Badge>
                              )}
                            </div>
                            <div className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
                              {request.reason && (
                                <p><span className="font-medium">Reason:</span> {request.reason}</p>
                              )}
                              <p className="text-xs text-gray-500">
                                Submitted: {formatDate(request.created_at)}
                              </p>
                            </div>
                          </div>
                          <Button
                            onClick={() => handleOpenReviewModal(request)}
                            className="ml-4"
                          >
                            <Eye className="w-4 h-4 mr-2" />
                            Review
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Completed Requests */}
                {creditRequests.filter(r => r.status !== 'pending').length > 0 && (
                  <div className="space-y-3 mt-6">
                    <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Request History</h3>
                    <div className="overflow-x-auto">
                      <table className="w-full">
                        <thead>
                          <tr className="border-b border-gray-200 dark:border-gray-700">
                            <th className="text-left py-3 px-4 text-sm font-medium text-gray-700 dark:text-gray-300">Requester</th>
                            <th className="text-left py-3 px-4 text-sm font-medium text-gray-700 dark:text-gray-300">Amount</th>
                            <th className="text-left py-3 px-4 text-sm font-medium text-gray-700 dark:text-gray-300">Status</th>
                            <th className="text-left py-3 px-4 text-sm font-medium text-gray-700 dark:text-gray-300">Date</th>
                            <th className="text-left py-3 px-4 text-sm font-medium text-gray-700 dark:text-gray-300">Notes</th>
                          </tr>
                        </thead>
                        <tbody>
                          {creditRequests.filter(r => r.status !== 'pending').map((request) => (
                            <tr key={request.id} className="border-b border-gray-100 dark:border-gray-800">
                              <td className="py-3 px-4">
                                <div>
                                  <p className="font-medium text-gray-900 dark:text-white">
                                    {request.user_name || request.user_email || 'Unknown'}
                                  </p>
                                  {request.team_name && (
                                    <p className="text-xs text-gray-500">{request.team_name}</p>
                                  )}
                                </div>
                              </td>
                              <td className="py-3 px-4 font-medium">
                                {request.requested_amount.toLocaleString()}
                              </td>
                              <td className="py-3 px-4">
                                <Badge className={getRequestStatusColor(request.status)}>
                                  {request.status}
                                </Badge>
                              </td>
                              <td className="py-3 px-4 text-sm text-gray-600 dark:text-gray-400">
                                {formatDate(request.created_at)}
                              </td>
                              <td className="py-3 px-4 text-sm text-gray-600 dark:text-gray-400 max-w-xs truncate">
                                {request.review_notes || '—'}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      ) : (
        // Credit Lots Tab (existing content)
        <Card>
          <CardHeader className="pb-4">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <CardTitle className="flex items-center space-x-2 text-xl">
                <DollarSign className="w-5 h-5" />
                <span>Credit Lots</span>
              </CardTitle>
              <div className="flex items-center space-x-4 text-sm text-gray-500 dark:text-gray-400">
                <span>Active: {stats?.activeLots}</span>
                <span>•</span>
                <span>Total Value: {stats?.totalLotsValue.toLocaleString()}</span>
              </div>
            </div>
            <CardDescription>
              Individual credit allocations and their status
            </CardDescription>
          </CardHeader>
        <CardContent>
          {activeTab === 'overview' ? (
            // Overview Tab - Summary of credit lots
            <div className="space-y-6">
              {/* Active Lots Summary */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {creditLots.filter(lot => lot.is_active).slice(0, 6).map((lot) => {
                  const daysUntilExpiry = getDaysUntilExpiry(lot.expires_at);
                  
                  return (
                    <Card key={lot.id} className="hover:shadow-md transition-shadow">
                      <CardContent className="p-4">
                        <div className="flex items-start justify-between mb-3">
                          <div className="flex items-center space-x-2">
                            {getSourceIcon(lot.source)}
                            <Badge className={getSourceColor(lot.source)}>
                              {lot.source}
                            </Badge>
                          </div>
                          <Badge className={getStatusColor(lot.is_active)}>
                            {lot.is_active ? 'Active' : 'Inactive'}
                          </Badge>
                        </div>
                        
                        <div className="space-y-2">
                          <div className="flex justify-between items-center">
                            <span className="text-sm text-gray-600 dark:text-gray-400">Amount</span>
                            <span className="font-bold text-lg">{lot.credit_amount.toLocaleString()}</span>
                          </div>
                          
                          {lot.expires_at && (
                            <div className="flex justify-between items-center">
                              <span className="text-sm text-gray-600 dark:text-gray-400">Expires</span>
                              <span className={`text-sm font-medium ${getExpiryColor(daysUntilExpiry)}`}>
                                {daysUntilExpiry && daysUntilExpiry > 0 ? `${daysUntilExpiry}d` : 'Expired'}
                              </span>
                            </div>
                          )}
                          
                          <div className="flex justify-between items-center">
                            <span className="text-sm text-gray-600 dark:text-gray-400">Created</span>
                            <span className="text-sm">{formatDate(lot.created_at)}</span>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>

              {creditLots.length === 0 && (
                <div className="text-center py-12">
                  <div className="w-16 h-16 bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-4">
                    <AlertCircle className="w-8 h-8 text-gray-400" />
                  </div>
                  <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                    No credit lots found
                  </h3>
                  <p className="text-gray-500 dark:text-gray-400 mb-6 max-w-md mx-auto">
                    This organization doesn't have any credit allocations yet.
                  </p>
                  <Button className="flex items-center space-x-2">
                    <Plus className="w-4 h-4" />
                    <span>Request Credits</span>
                  </Button>
                </div>
              )}
            </div>
          ) : (
            // All Lots Tab - Detailed table view
            <div className="space-y-4">
              {creditLots.length === 0 ? (
                <div className="text-center py-12">
                  <div className="w-16 h-16 bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-4">
                    <AlertCircle className="w-8 h-8 text-gray-400" />
                  </div>
                  <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                    No credit lots found
                  </h3>
                  <p className="text-gray-500 dark:text-gray-400 mb-6 max-w-md mx-auto">
                    This organization doesn't have any credit allocations yet.
                  </p>
                  <Button className="flex items-center space-x-2">
                    <Plus className="w-4 h-4" />
                    <span>Request Credits</span>
                  </Button>
                </div>
              ) : (
                <>
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead>
                        <tr className="border-b border-gray-200 dark:border-gray-700">
                          <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">Source</th>
                          <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">Amount</th>
                          <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">Status</th>
                          <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">Valid From</th>
                          <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">Expires</th>
                          <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {creditLots.map((lot) => {
                          const daysUntilExpiry = getDaysUntilExpiry(lot.expires_at);
                          
                          return (
                            <tr key={lot.id} className="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50">
                              <td className="py-4 px-4">
                                <div className="flex items-center space-x-2">
                                  {getSourceIcon(lot.source)}
                                  <Badge className={getSourceColor(lot.source)}>
                                    {lot.source}
                                  </Badge>
                                </div>
                              </td>
                              <td className="py-4 px-4">
                                <div>
                                  <p className="font-medium text-gray-900 dark:text-white">
                                    {lot.credit_amount.toLocaleString()}
                                  </p>
                                  {lot.original_amount !== lot.credit_amount && (
                                    <p className="text-xs text-gray-500 dark:text-gray-400">
                                      Originally: {lot.original_amount.toLocaleString()}
                                    </p>
                                  )}
                                </div>
                              </td>
                              <td className="py-4 px-4">
                                <Badge className={getStatusColor(lot.is_active)}>
                                  {lot.is_active ? 'Active' : 'Inactive'}
                                </Badge>
                              </td>
                              <td className="py-4 px-4">
                                <p className="text-sm text-gray-900 dark:text-white">
                                  {formatDate(lot.valid_from)}
                                </p>
                              </td>
                              <td className="py-4 px-4">
                                <div className="flex items-center space-x-2">
                                  <p className="text-sm text-gray-900 dark:text-white">
                                    {lot.expires_at ? formatDate(lot.expires_at) : 'Never'}
                                  </p>
                                  {daysUntilExpiry !== null && daysUntilExpiry <= 30 && (
                                    <Badge variant="outline" className={getExpiryColor(daysUntilExpiry)}>
                                      {daysUntilExpiry > 0 ? `${daysUntilExpiry}d` : 'Expired'}
                                    </Badge>
                                  )}
                                </div>
                              </td>
                              <td className="py-4 px-4">
                                <DropdownMenu>
                                  <DropdownMenuTrigger asChild>
                                    <Button variant="ghost" size="sm">
                                      <MoreVertical className="w-4 h-4" />
                                    </Button>
                                  </DropdownMenuTrigger>
                                  <DropdownMenuContent align="end">
                                    {lot.is_active ? (
                                      <>
                                        <DropdownMenuItem onClick={() => handleSuspendLot(lot.id, `#${lot.id}`)}>
                                          <Pause className="w-4 h-4 mr-2" />
                                          Suspend
                                        </DropdownMenuItem>
                                        <DropdownMenuItem onClick={() => handleFreezeLot(lot.id, `#${lot.id}`)}>
                                          <Clock className="w-4 h-4 mr-2" />
                                          Freeze
                                        </DropdownMenuItem>
                                      </>
                                    ) : (
                                      <DropdownMenuItem onClick={() => handleActivateLot(lot.id, `#${lot.id}`)}>
                                        <Play className="w-4 h-4 mr-2" />
                                        Activate
                                      </DropdownMenuItem>
                                    )}
                                    <DropdownMenuItem>
                                      <Download className="w-4 h-4 mr-2" />
                                      Export Details
                                    </DropdownMenuItem>
                                  </DropdownMenuContent>
                                </DropdownMenu>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>

                  {/* Summary Footer */}
                  <div className="flex justify-between items-center pt-4 border-t border-gray-200 dark:border-gray-700">
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      Showing {creditLots.length} credit lots
                    </p>
                    <div className="flex items-center space-x-4 text-sm text-gray-500 dark:text-gray-400">
                      <span>Active: {stats?.activeLots}</span>
                      <span>•</span>
                      <span>Total Value: {stats?.totalLotsValue.toLocaleString()}</span>
                    </div>
                  </div>
                </>
              )}
            </div>
          )}
        </CardContent>
      </Card>
      )}

      {/* Request Credits from Yuba Modal */}
      {showRequestModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-md mx-4">
            {/* Header */}
            <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white flex items-center space-x-2">
                <Send className="w-5 h-5" />
                <span>Request Credits from Yuba</span>
              </h2>
              <button
                onClick={() => setShowRequestModal(false)}
                disabled={isSubmittingRequest}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 disabled:opacity-50"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Form */}
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Credits Requested <span className="text-red-500">*</span>
                </label>
                <input
                  type="number"
                  min="1"
                  value={requestFormData.requested_amount}
                  onChange={(e) => setRequestFormData(prev => ({ ...prev, requested_amount: e.target.value }))}
                  placeholder="Enter amount (e.g., 5000)"
                  disabled={isSubmittingRequest}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Reason <span className="text-red-500">*</span>
                </label>
                <textarea
                  value={requestFormData.reason}
                  onChange={(e) => setRequestFormData(prev => ({ ...prev, reason: e.target.value }))}
                  placeholder="Explain why you need additional credits (minimum 10 characters)..."
                  rows={4}
                  maxLength={2000}
                  disabled={isSubmittingRequest}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 resize-none"
                />
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  {requestFormData.reason.length}/2000 characters
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Urgency
                </label>
                <select
                  value={requestFormData.urgency}
                  onChange={(e) => setRequestFormData(prev => ({ ...prev, urgency: e.target.value as 'normal' | 'high' | 'urgent' }))}
                  disabled={isSubmittingRequest}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50"
                >
                  <option value="normal">Normal</option>
                  <option value="high">High</option>
                  <option value="urgent">Urgent</option>
                </select>
              </div>

              {/* Info Alert */}
              <div className="flex items-start space-x-2 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                <AlertCircle className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-blue-800 dark:text-blue-200">
                  Your request will be sent to Yuba (info@yubanow.com) for review. This feature is only available for grant organizations.
                </p>
              </div>

              {/* Actions */}
              <div className="flex justify-end space-x-3 pt-4">
                <Button
                  variant="outline"
                  onClick={() => setShowRequestModal(false)}
                  disabled={isSubmittingRequest}
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleRequestCreditsFromYuba}
                  disabled={isSubmittingRequest || !requestFormData.requested_amount || requestFormData.reason.length < 10}
                >
                  {isSubmittingRequest ? (
                    <>
                      <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                      Submitting...
                    </>
                  ) : (
                    <>
                      <Send className="w-4 h-4 mr-2" />
                      Submit Request
                    </>
                  )}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Review Credit Request Modal */}
      {showReviewModal && selectedRequest && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-lg mx-4">
            {/* Header */}
            <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                Review Credit Request
              </h2>
              <button
                onClick={() => { setShowReviewModal(false); setSelectedRequest(null); }}
                disabled={isSubmittingRequest}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 disabled:opacity-50"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Request Details */}
            <div className="p-6 bg-gray-50 dark:bg-gray-900/50 border-b border-gray-200 dark:border-gray-700">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-gray-500 dark:text-gray-400">Requester</p>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    {selectedRequest.user_name || selectedRequest.user_email || 'Unknown'}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 dark:text-gray-400">Amount Requested</p>
                  <p className="text-lg font-semibold text-blue-600 dark:text-blue-400">
                    {selectedRequest.requested_amount.toLocaleString()}
                  </p>
                </div>
                {selectedRequest.team_name && (
                  <div>
                    <p className="text-xs text-gray-500 dark:text-gray-400">Team</p>
                    <p className="text-sm font-medium text-gray-900 dark:text-white">
                      {selectedRequest.team_name}
                    </p>
                  </div>
                )}
                <div>
                  <p className="text-xs text-gray-500 dark:text-gray-400">Submitted</p>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    {formatDate(selectedRequest.created_at)}
                  </p>
                </div>
              </div>
              {selectedRequest.reason && (
                <div className="mt-4">
                  <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Reason</p>
                  <p className="text-sm text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 p-3 rounded-lg border border-gray-200 dark:border-gray-700">
                    {selectedRequest.reason}
                  </p>
                </div>
              )}
            </div>

            {/* Review Form */}
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                  Decision <span className="text-red-500">*</span>
                </label>
                <div className="grid grid-cols-2 gap-4">
                  <button
                    type="button"
                    onClick={() => setReviewFormData(prev => ({ ...prev, status: 'approved' }))}
                    disabled={isSubmittingRequest}
                    className={`p-4 border-2 rounded-lg transition-all ${
                      reviewFormData.status === 'approved'
                        ? 'border-green-500 bg-green-50 dark:bg-green-900/20'
                        : 'border-gray-300 dark:border-gray-600 hover:border-green-300'
                    } disabled:opacity-50`}
                  >
                    <CheckCircle className={`w-6 h-6 mx-auto mb-2 ${
                      reviewFormData.status === 'approved' ? 'text-green-600' : 'text-gray-400'
                    }`} />
                    <p className={`text-sm font-medium ${
                      reviewFormData.status === 'approved'
                        ? 'text-green-700 dark:text-green-300'
                        : 'text-gray-700 dark:text-gray-300'
                    }`}>
                      Approve
                    </p>
                  </button>
                  <button
                    type="button"
                    onClick={() => setReviewFormData(prev => ({ ...prev, status: 'rejected' }))}
                    disabled={isSubmittingRequest}
                    className={`p-4 border-2 rounded-lg transition-all ${
                      reviewFormData.status === 'rejected'
                        ? 'border-red-500 bg-red-50 dark:bg-red-900/20'
                        : 'border-gray-300 dark:border-gray-600 hover:border-red-300'
                    } disabled:opacity-50`}
                  >
                    <XCircle className={`w-6 h-6 mx-auto mb-2 ${
                      reviewFormData.status === 'rejected' ? 'text-red-600' : 'text-gray-400'
                    }`} />
                    <p className={`text-sm font-medium ${
                      reviewFormData.status === 'rejected'
                        ? 'text-red-700 dark:text-red-300'
                        : 'text-gray-700 dark:text-gray-300'
                    }`}>
                      Reject
                    </p>
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Review Notes {reviewFormData.status === 'rejected' && <span className="text-red-500">*</span>}
                </label>
                <textarea
                  value={reviewFormData.review_notes}
                  onChange={(e) => setReviewFormData(prev => ({ ...prev, review_notes: e.target.value }))}
                  placeholder={
                    reviewFormData.status === 'approved'
                      ? 'Add any notes about this approval (optional)...'
                      : 'Explain why this request is being rejected...'
                  }
                  rows={3}
                  maxLength={500}
                  disabled={isSubmittingRequest}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 resize-none"
                />
              </div>

              {/* Actions */}
              <div className="flex justify-end space-x-3 pt-4">
                <Button
                  variant="outline"
                  onClick={() => { setShowReviewModal(false); setSelectedRequest(null); }}
                  disabled={isSubmittingRequest}
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleReviewCreditRequest}
                  disabled={isSubmittingRequest || (reviewFormData.status === 'rejected' && !reviewFormData.review_notes.trim())}
                  className={reviewFormData.status === 'approved' ? 'bg-green-600 hover:bg-green-700' : 'bg-red-600 hover:bg-red-700'}
                >
                  {isSubmittingRequest ? (
                    <>
                      <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                      Processing...
                    </>
                  ) : (
                    <>
                      {reviewFormData.status === 'approved' ? (
                        <>
                          <CheckCircle className="w-4 h-4 mr-2" />
                          Approve Request
                        </>
                      ) : (
                        <>
                          <XCircle className="w-4 h-4 mr-2" />
                          Reject Request
                        </>
                      )}
                    </>
                  )}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}