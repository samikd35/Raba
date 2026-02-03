"use client";

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { organizationService } from '@/lib/api/organizationService';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useAuthStore } from '@/stores/authStore';
import { toast } from "react-hot-toast";
import { CreditCard, TrendingUp, TrendingDown, Calendar, DollarSign, AlertCircle, Plus, Pause, Play } from 'lucide-react';

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
  const params = useParams();
  const organizationId = params.id as string;
  const { isAuthenticated } = useAuthStore();
  
  const [creditLots, setCreditLots] = useState<CreditLot[]>([]);
  const [metrics, setMetrics] = useState<CreditMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // if (!isAuthenticated) {
    //   router.push('/signin?redirect=/admin/organizations/' + organizationId + '/credits');
    //   return;
    // }
    
    if (organizationId) {
      fetchCreditsData();
    }
  }, [organizationId, isAuthenticated]);

  const fetchCreditsData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Fetch organization metrics for credit summary
      const metricsData = await organizationService.getOrganizationMetrics(organizationId);
      setMetrics(metricsData.credits || null);

      // Fetch credit lots
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/organization/${organizationId}/lots/issued`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${useAuthStore.getState().token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch credit lots: ${response.status}`);
      }

      const lotsData = await response.json();
      setCreditLots(lotsData.lots || []);
    } catch (err: any) {
      console.error('Error fetching credits data:', err);
      setError(err.message || 'Failed to fetch credits data');
      toast.error(err.message || 'Failed to fetch credits data');
    } finally {
      setLoading(false);
    }
  };

  const handleBack = () => {
    router.push(`/admin/organizations/${organizationId}`);
  };

  const handleRefresh = () => {
    fetchCreditsData();
  };

  const handleSuspendLot = async (lotId: string) => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/organization/${organizationId}/lots/${lotId}/suspend`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${useAuthStore.getState().token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to suspend credit lot: ${response.status}`);
      }

      toast.success('Credit lot suspended successfully');
      fetchCreditsData(); // Refresh data
    } catch (err: any) {
      toast.error(err.message || 'Failed to suspend credit lot');
    }
  };

  const handleFreezeLot = async (lotId: string) => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/organization/${organizationId}/lots/${lotId}/freeze`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${useAuthStore.getState().token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to freeze credit lot: ${response.status}`);
      }

      toast.success('Credit lot frozen successfully');
      fetchCreditsData(); // Refresh data
    } catch (err: any) {
      toast.error(err.message || 'Failed to freeze credit lot');
    }
  };

  const getSourceColor = (source: string) => {
    switch (source.toLowerCase()) {
      case 'grant':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
      case 'purchase':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200';
      case 'transfer':
        return 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200';
      case 'invitation':
        return 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200';
    }
  };

  const getStatusColor = (isActive: boolean) => {
    return isActive 
      ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
      : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
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
          <h3 className="font-medium">Error loading credits</h3>
          <p className="mt-1 text-sm">{error}</p>
          <div className="flex space-x-3 mt-3">
            <button
              onClick={handleBack}
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 text-sm"
            >
              Back to Organization
            </button>
            <button
              onClick={fetchCreditsData}
              className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 text-sm"
            >
              Retry
            </button>
          </div>
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
              Credits & Billing
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mt-1">
              Manage organization credit allocation and usage
            </p>
          </div>
        </div>
        <div className="flex space-x-3">
          <Button onClick={handleRefresh}>
            <span className="text-lg mr-2">🔄</span>
            Refresh
          </Button>
          <Button>
            <Plus className="w-4 h-4 mr-2" />
            Allocate Credits
          </Button>
        </div>
      </div>

      {/* Credit Summary */}
      {metrics && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center space-x-2">
                <CreditCard className="w-5 h-5 text-blue-500" />
                <div>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {metrics.total}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">Total Credits</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center space-x-2">
                <TrendingUp className="w-5 h-5 text-red-500" />
                <div>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {metrics.used}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">Credits Used</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center space-x-2">
                <TrendingDown className="w-5 h-5 text-green-500" />
                <div>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {metrics.remaining}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">Remaining</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center space-x-2">
                <Calendar className="w-5 h-5 text-purple-500" />
                <div>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {metrics.monthly_limit || 'Unlimited'}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">Monthly Limit</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Credit Usage Progress */}
      {metrics && metrics.total > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Credit Usage</CardTitle>
            <CardDescription>Current credit consumption across the organization</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>Used: {metrics.used}</span>
                <span>Remaining: {metrics.remaining}</span>
              </div>
              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3">
                <div 
                  className="bg-blue-500 h-3 rounded-full transition-all duration-300" 
                  style={{ width: `${(metrics.used / metrics.total) * 100}%` }}
                ></div>
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {Math.round((metrics.used / metrics.total) * 100)}% of total credits used
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Credit Lots */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <DollarSign className="w-5 h-5" />
            <span>Credit Lots</span>
          </CardTitle>
          <CardDescription>
            Individual credit allocations and their status
          </CardDescription>
        </CardHeader>
        <CardContent>
          {creditLots.length === 0 ? (
            <div className="text-center py-12">
              <AlertCircle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                No credit lots found
              </h3>
              <p className="text-gray-500 dark:text-gray-400 mb-4">
                This organization doesn't have any credit allocations yet.
              </p>
              <Button>
                <Plus className="w-4 h-4 mr-2" />
                Request Credits
              </Button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200 dark:border-gray-700">
                    <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">Amount</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">Source</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">Status</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">Valid From</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">Expires</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {creditLots.map((lot) => (
                    <tr key={lot.id} className="border-b border-gray-100 dark:border-gray-800">
                      <td className="py-4 px-4">
                        <div>
                          <p className="font-medium text-gray-900 dark:text-white">
                            {lot.credit_amount}
                          </p>
                          {lot.original_amount !== lot.credit_amount && (
                            <p className="text-xs text-gray-500 dark:text-gray-400">
                              Originally: {lot.original_amount}
                            </p>
                          )}
                        </div>
                      </td>
                      <td className="py-4 px-4">
                        <Badge className={getSourceColor(lot.source)}>
                          {lot.source}
                        </Badge>
                      </td>
                      <td className="py-4 px-4">
                        <Badge className={getStatusColor(lot.is_active)}>
                          {lot.is_active ? 'Active' : 'Inactive'}
                        </Badge>
                      </td>
                      <td className="py-4 px-4">
                        <p className="text-sm text-gray-900 dark:text-white">
                          {new Date(lot.valid_from).toLocaleDateString()}
                        </p>
                      </td>
                      <td className="py-4 px-4">
                        <p className="text-sm text-gray-900 dark:text-white">
                          {lot.expires_at ? new Date(lot.expires_at).toLocaleDateString() : 'Never'}
                        </p>
                      </td>
                      <td className="py-4 px-4">
                        <div className="flex space-x-2">
                          {lot.is_active ? (
                            <>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => handleSuspendLot(lot.id)}
                              >
                                <Pause className="w-3 h-3 mr-1" />
                                Suspend
                              </Button>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => handleFreezeLot(lot.id)}
                              >
                                Freeze
                              </Button>
                            </>
                          ) : (
                            <Button
                              variant="outline"
                              size="sm"
                              disabled
                            >
                              <Play className="w-3 h-3 mr-1" />
                              Activate
                            </Button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
