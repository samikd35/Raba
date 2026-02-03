"use client";

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { userMonitoringService, UserSummary, OnboardingMetrics, ActivationMetrics, RetentionMetrics } from '@/lib/api/userMonitoringService';
import { useAuthStore } from '@/stores/authStore';
import { toast } from 'sonner';
import { 
  Users, 
  TrendingUp, 
  Activity, 
  UserCheck, 
  UserX, 
  Search,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';

export default function UserMonitoringPage() {
  const router = useRouter();
  const { user, isAuthenticated, token } = useAuthStore();
  
  // State for users list
  const [users, setUsers] = useState<UserSummary[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalUsers, setTotalUsers] = useState(0);
  const [hasNextPage, setHasNextPage] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  
  // State for metrics
  const [onboardingMetrics, setOnboardingMetrics] = useState<OnboardingMetrics | null>(null);
  const [activationMetrics, setActivationMetrics] = useState<ActivationMetrics | null>(null);
  const [retentionMetrics, setRetentionMetrics] = useState<RetentionMetrics | null>(null);
  
  // Loading states
  const [loadingUsers, setLoadingUsers] = useState(true);
  const [loadingMetrics, setLoadingMetrics] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Check if user is authenticated
    if (!isAuthenticated || !token) {
      console.log('User not authenticated, redirecting to login');
      router.push('/signin');
      return;
    }
    
    // Check if user has super_admin role
    if (!user?.roles?.includes('super_admin')) {
      console.log('User does not have super_admin role');
      router.push('/unauthorized');
      return;
    }
    
    fetchAllData();
  }, [isAuthenticated, token, user, router, currentPage, searchTerm]);

  const fetchAllData = async () => {
    await Promise.all([
      fetchUsers(),
      fetchMetrics()
    ]);
  };

  const fetchUsers = async () => {
    try {
      setLoadingUsers(true);
      const response = await userMonitoringService.fetchUsers({
        page: currentPage,
        page_size: 20,
        search: searchTerm || undefined
      });
      
      setUsers(response.users);
      setTotalUsers(response.total_count);
      setHasNextPage(response.has_next);
    } catch (err: any) {
      console.error('Failed to fetch users', err);
      if (err?.message?.includes('401') || err?.message?.includes('403')) {
        toast.error('Authentication failed. Please log in again.');
        router.push('/signin');
      } else {
        setError(err?.message || 'Failed to fetch users');
        toast.error(err?.message || 'Failed to fetch users');
      }
    } finally {
      setLoadingUsers(false);
    }
  };

  const fetchMetrics = async () => {
    try {
      setLoadingMetrics(true);
      const [onboarding, activation, retention] = await Promise.all([
        userMonitoringService.getOnboardingMetrics(),
        userMonitoringService.getActivationMetrics(),
        userMonitoringService.getRetentionMetrics({ window_days: 30 })
      ]);
      
      setOnboardingMetrics(onboarding);
      setActivationMetrics(activation);
      setRetentionMetrics(retention);
    } catch (err: any) {
      console.error('Failed to fetch metrics', err);
      toast.error('Failed to fetch metrics');
    } finally {
      setLoadingMetrics(false);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setCurrentPage(1); // Reset to first page on new search
    fetchUsers();
  };

  const formatPercentage = (value: number) => {
    return `${(value * 100).toFixed(1)}%`;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  if (loadingUsers && loadingMetrics) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            User Monitoring
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            Track user onboarding, activation, and retention metrics
          </p>
        </div>
      </div>

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Total Users */}
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400">Total Users</h3>
            <Users className="w-5 h-5 text-gray-400" />
          </div>
          <div className="text-2xl font-bold text-gray-900 dark:text-white">{totalUsers}</div>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">All registered users</p>
        </div>

        {/* Onboarding Conversion */}
        {onboardingMetrics && (
          <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400">Onboarding</h3>
              <TrendingUp className="w-5 h-5 text-gray-400" />
            </div>
            <div className="text-2xl font-bold text-gray-900 dark:text-white">
              {formatPercentage(onboardingMetrics.conversion_to_first_project)}
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              {onboardingMetrics.users_with_first_project} / {onboardingMetrics.total_signups} created project
            </p>
          </div>
        )}

        {/* Activation Rate */}
        {activationMetrics && (
          <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400">Activation</h3>
              <UserCheck className="w-5 h-5 text-gray-400" />
            </div>
            <div className="text-2xl font-bold text-gray-900 dark:text-white">
              {formatPercentage(activationMetrics.activation_rate)}
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              {activationMetrics.activated_users} / {activationMetrics.total_signups} activated
            </p>
          </div>
        )}

        {/* Retention */}
        {retentionMetrics && (
          <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400">Active Users</h3>
              <Activity className="w-5 h-5 text-gray-400" />
            </div>
            <div className="text-2xl font-bold text-gray-900 dark:text-white">
              {retentionMetrics.power_users + retentionMetrics.healthy_users}
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              {retentionMetrics.power_users} power, {retentionMetrics.healthy_users} healthy
            </p>
          </div>
        )}
      </div>

      {/* Detailed Metrics */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Onboarding Funnel */}
        {onboardingMetrics && (
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Onboarding Funnel</h2>
            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-600 dark:text-gray-400">Sign-ups</span>
                  <span className="font-medium text-gray-900 dark:text-white">{onboardingMetrics.total_signups}</span>
                </div>
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                  <div className="bg-brand-500 h-2 rounded-full" style={{ width: '100%' }}></div>
                </div>
              </div>
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-600 dark:text-gray-400">First Project</span>
                  <span className="font-medium text-gray-900 dark:text-white">
                    {onboardingMetrics.users_with_first_project} ({formatPercentage(onboardingMetrics.conversion_to_first_project)})
                  </span>
                </div>
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                  <div 
                    className="bg-brand-500 h-2 rounded-full" 
                    style={{ width: formatPercentage(onboardingMetrics.conversion_to_first_project) }}
                  ></div>
                </div>
              </div>
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-600 dark:text-gray-400">First Report</span>
                  <span className="font-medium text-gray-900 dark:text-white">
                    {onboardingMetrics.users_with_first_report} ({formatPercentage(onboardingMetrics.conversion_to_first_report)})
                  </span>
                </div>
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                  <div 
                    className="bg-brand-500 h-2 rounded-full" 
                    style={{ width: formatPercentage(onboardingMetrics.conversion_to_first_report) }}
                  ></div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Activation Details */}
        {activationMetrics && (
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Activation Metrics</h2>
            <div className="space-y-4">
              <div className="flex items-center justify-between p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
                <div className="flex items-center space-x-3">
                  <UserCheck className="w-5 h-5 text-green-600 dark:text-green-400" />
                  <span className="text-sm font-medium text-gray-900 dark:text-white">Activated Users</span>
                </div>
                <span className="text-lg font-bold text-green-600 dark:text-green-400">
                  {activationMetrics.activated_users}
                </span>
              </div>
              <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                <div className="flex items-center space-x-3">
                  <UserX className="w-5 h-5 text-gray-600 dark:text-gray-400" />
                  <span className="text-sm font-medium text-gray-900 dark:text-white">Not Activated</span>
                </div>
                <span className="text-lg font-bold text-gray-600 dark:text-gray-400">
                  {activationMetrics.total_signups - activationMetrics.activated_users}
                </span>
              </div>
              <div className="pt-3 border-t border-gray-200 dark:border-gray-700">
                <div className="text-center">
                  <div className="text-3xl font-bold text-brand-500">
                    {formatPercentage(activationMetrics.activation_rate)}
                  </div>
                  <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">Activation Rate</div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* User Segments */}
        {retentionMetrics && (
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">User Segments (30 days)</h2>
            <div className="space-y-4">
              <div className="flex items-center justify-between p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
                <div>
                  <div className="text-sm font-medium text-gray-900 dark:text-white">Power Users</div>
                  <div className="text-xs text-gray-600 dark:text-gray-400">10+ active days</div>
                </div>
                <span className="text-lg font-bold text-purple-600 dark:text-purple-400">
                  {retentionMetrics.power_users}
                </span>
              </div>
              <div className="flex items-center justify-between p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                <div>
                  <div className="text-sm font-medium text-gray-900 dark:text-white">Healthy Users</div>
                  <div className="text-xs text-gray-600 dark:text-gray-400">Active in window</div>
                </div>
                <span className="text-lg font-bold text-blue-600 dark:text-blue-400">
                  {retentionMetrics.healthy_users}
                </span>
              </div>
              <div className="flex items-center justify-between p-3 bg-red-50 dark:bg-red-900/20 rounded-lg">
                <div>
                  <div className="text-sm font-medium text-gray-900 dark:text-white">Churn Risk</div>
                  <div className="text-xs text-gray-600 dark:text-gray-400">No recent activity</div>
                </div>
                <span className="text-lg font-bold text-red-600 dark:text-red-400">
                  {retentionMetrics.churn_risk_users}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Users List */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">All Users</h2>
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                {totalUsers} total users
              </p>
            </div>
            <form onSubmit={handleSearch} className="flex items-center space-x-2">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder="Search by email or name..."
                  className="pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
                />
              </div>
              <button
                type="submit"
                className="px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white rounded-lg"
              >
                Search
              </button>
            </form>
          </div>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
                <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">Email</th>
                <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">Name</th>
                <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">Location</th>
                <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">Role</th>
                <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">Created</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id} className="border-b border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700">
                  <td className="py-3 px-4 text-gray-900 dark:text-white">{user.email}</td>
                  <td className="py-3 px-4 text-gray-600 dark:text-gray-400">{user.full_name || '-'}</td>
                  <td className="py-3 px-4 text-gray-600 dark:text-gray-400">{user.location || '-'}</td>
                  <td className="py-3 px-4">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      user.role === 'super_admin' 
                        ? 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200'
                        : user.role === 'admin'
                        ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
                        : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200'
                    }`}>
                      {user.role}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-gray-600 dark:text-gray-400">{formatDate(user.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="p-4 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between">
          <div className="text-sm text-gray-600 dark:text-gray-400">
            Page {currentPage} • {totalUsers} total users
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="p-2 rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              onClick={() => setCurrentPage(p => p + 1)}
              disabled={!hasNextPage}
              className="p-2 rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
