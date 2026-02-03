"use client";

import React, { useEffect, useState, useMemo, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { 
  useTeamStore, 
  useCurrentTeam, 
  useTeamMetrics, 
  useTeamLoading,
  useTeamError,
  useFetchTeamDetails,
  useSetTeamMetrics,
  useSetTeamError,
  useSetTeamLoading
} from "@/stores/teamStore";
import { useAuthStore } from "@/stores/authStore";
import { TeamMetrics } from "@/types/team";
import { 
  Users, 
  CreditCard, 
  TrendingUp, 
  Calendar,
  Sparkles,
  ArrowUpRight,
  Clock,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  RefreshCw,
  User,
  Building
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import QuickActions from "@/components/workspace/QuickActions";

// Skeleton loader component
const DashboardSkeleton = () => (
  <div className="space-y-6 max-w-7xl">
    {/* Header Skeleton */}
    <div className="flex items-center gap-3">
      <div className="w-2 h-8 bg-gray-200 dark:bg-gray-700 rounded-full animate-pulse" />
      <div className="space-y-2">
        <div className="h-7 w-64 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
        <div className="h-4 w-48 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
      </div>
    </div>

    {/* Metrics Grid Skeleton */}
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {[...Array(4)].map((_, i) => (
        <div key={i} className="p-6 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl">
          <div className="flex items-start justify-between mb-4">
            <div className="w-10 h-10 bg-gray-200 dark:bg-gray-700 rounded-lg animate-pulse" />
            <div className="w-12 h-4 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
          </div>
          <div className="space-y-2">
            <div className="h-4 w-24 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
            <div className="h-8 w-16 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
            <div className="h-3 w-32 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
          </div>
        </div>
      ))}
    </div>

    {/* Quick Actions Skeleton */}
    <div className="p-6 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl">
      <div className="h-6 w-32 bg-gray-200 dark:bg-gray-700 rounded animate-pulse mb-4" />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-20 bg-gray-100 dark:bg-gray-800 rounded-lg animate-pulse" />
        ))}
      </div>
    </div>

    {/* Team Overview Skeleton */}
    <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="space-y-3">
            <div className="h-4 w-32 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
            <div className="h-6 w-48 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
          </div>
        ))}
      </div>
    </div>
  </div>
);

// Error state component
const ErrorState = ({ error, onRetry }: { error: string; onRetry: () => void }) => (
  <motion.div
    initial={{ opacity: 0, scale: 0.95 }}
    animate={{ opacity: 1, scale: 1 }}
    className="flex flex-col items-center justify-center min-h-[400px] text-center p-6"
  >
    <div className="w-16 h-16 bg-red-100 dark:bg-red-900/20 rounded-full flex items-center justify-center mb-4">
      <AlertTriangle className="w-8 h-8 text-red-500" />
    </div>
    <h3 className="text-lg font-semibold text-brand-500 dark:text-white mb-2">
      Unable to load dashboard
    </h3>
    <p className="text-gray-600 dark:text-gray-400 mb-6 max-w-md">
      {error || "There was a problem loading your team dashboard data."}
    </p>
    <button
      onClick={onRetry}
      className="px-4 py-2 bg-brand-500 text-white rounded-lg hover:bg-brand-600 transition-colors flex items-center gap-2"
    >
      <RefreshCw className="w-4 h-4" />
      Try Again
    </button>
  </motion.div>
);

// Safe error handler utility
const safeErrorHandler = (error: unknown): string => {
  if (error instanceof Error) {
    return error.message;
  }
  if (typeof error === 'string') {
    return error;
  }
  if (error && typeof error === 'object' && 'message' in error) {
    return String((error as any).message);
  }
  return 'An unknown error occurred';
};

// Credits data interfaces
interface CreditLot {
  id: string;
  credit_amount: number;
  valid_from: string;
  expires_at: string;
}

interface CreditsData {
  tenant_id: string;
  lots: CreditLot[];
  tenant_total_active_credits: number;
  user_total_consumed_in_tenant: number;
}

// Custom hook for credits data management
const useCreditsData = (currentTeam: any) => {
  const [creditsData, setCreditsData] = useState<CreditsData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { token, isInitialized, isAuthenticated } = useAuthStore();
  const abortControllerRef = useRef<AbortController | null>(null);
  const isMountedRef = useRef(true);
  const isFetchingRef = useRef(false);
  const lastFetchAtRef = useRef<number>(0);

  const fetchCreditsData = useCallback(async (forceRefresh = false) => {
    // Guard: wait until auth is initialized and user is authenticated and we have a team and token
    if (!isInitialized || !isAuthenticated || !currentTeam?.id || !token) {
      setCreditsData(null);
      // Suppress error during initialization to avoid flashing errors
      setError(null);
      return;
    }

    // Prevent duplicate requests unless forced
    if (isFetchingRef.current && !forceRefresh) {
      return;
    }

    // Throttle: avoid fetching more than once every 10s unless forced
    const now = Date.now();
    if (!forceRefresh && now - lastFetchAtRef.current < 10000) {
      return;
    }

    try {
      setIsLoading(true);
      setError(null);
      isFetchingRef.current = true;

      // Cancel previous request if it exists
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      // Create new AbortController for this request
      abortControllerRef.current = new AbortController();

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/me/credits`,
        {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          signal: abortControllerRef.current.signal,
        }
      );

      if (!response.ok) {
        const errorText = await response.text().catch(() => 'Unknown error');
        
        switch (response.status) {
          case 401:
            throw new Error('Authentication expired. Please sign in again.');
          case 403:
            throw new Error('Access forbidden. Check your permissions.');
          case 404:
            throw new Error('Credits endpoint not found.');
          case 429:
            throw new Error('Too many requests. Please try again later.');
          default:
            throw new Error(`Failed to fetch credits: ${response.status} ${response.statusText}`);
        }
      }

      const contentType = response.headers.get('content-type');
      if (!contentType?.includes('application/json')) {
        throw new Error('Invalid response format from credits API');
      }

      const data: CreditsData = await response.json();
      
      // Enhanced data validation
      if (!data || typeof data !== 'object') {
        throw new Error('Invalid data structure received from API');
      }

      // Validate and normalize the data
      const validatedData: CreditsData = {
        tenant_id: data.tenant_id || currentTeam.id,
        lots: Array.isArray(data.lots) 
          ? data.lots.filter((lot: any) => 
              lot?.id && 
              typeof lot.credit_amount === 'number' &&
              lot.valid_from && 
              lot.expires_at
            )
          : [],
        tenant_total_active_credits: typeof data.tenant_total_active_credits === 'number' 
          ? Math.max(0, data.tenant_total_active_credits) 
          : 0,
        user_total_consumed_in_tenant: typeof data.user_total_consumed_in_tenant === 'number' 
          ? Math.max(0, data.user_total_consumed_in_tenant) 
          : 0,
      };

      // Only update state if component is still mounted
      if (isMountedRef.current) {
        setCreditsData(validatedData);
      }

      if (process.env.NODE_ENV === 'development') {
        console.log('✅ Dashboard credits data fetched successfully:', {
          tenant_id: validatedData.tenant_id,
          total_active: validatedData.tenant_total_active_credits,
          consumed: validatedData.user_total_consumed_in_tenant,
          lots_count: validatedData.lots.length
        });
      }

    } catch (err: any) {
      if (err.name === 'AbortError') {
        return; // Request was cancelled, no need to set error
      }

      // Only update state if component is still mounted
      if (isMountedRef.current) {
        const errorMessage = err.message || 'Failed to fetch credits data';
        setError(errorMessage);
      }
      
      if (process.env.NODE_ENV === 'development') {
        console.error('❌ Dashboard error fetching credits:', err);
      }
    } finally {
      // Only update state if component is still mounted
      if (isMountedRef.current) {
        setIsLoading(false);
      }
      lastFetchAtRef.current = Date.now();
      isFetchingRef.current = false;
    }
  }, [currentTeam?.id, token, isInitialized, isAuthenticated]);

  // Cleanup function
  useEffect(() => {
    isMountedRef.current = true;
    isFetchingRef.current = false;
    
    return () => {
      isMountedRef.current = false;
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  return {
    creditsData,
    isLoading,
    error,
    fetchCreditsData,
  };
};

// Custom hook for dashboard data management
const useDashboardData = () => {
  const currentTeam = useCurrentTeam();
  const teamMetrics = useTeamMetrics();
  const isLoading = useTeamLoading();
  const error = useTeamError();
  const fetchTeamDetails = useFetchTeamDetails();
  const setTeamMetrics = useSetTeamMetrics();
  const setError = useSetTeamError();
  const setIsLoading = useSetTeamLoading();
  const { user, token, isAuthenticated } = useAuthStore();
  
  const teamId = user?.tenant_id;

  console.log('currentTeammmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmm', currentTeam);

  const fetchMetricsData = useCallback(async (): Promise<TeamMetrics | null> => {
    if (!teamId || !token) return null;

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/teams/${teamId}/metrics`,
        {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch metrics: ${response.status}`);
      }

      const metricsData: TeamMetrics = await response.json();
      return metricsData;
    } catch (err) {
      console.error('Error fetching team metrics:', err);
      return null;
    }
  }, [teamId, token]);

  const fetchDashboardData = useCallback(async (showRefresh = false) => {
    if (!teamId || !isAuthenticated) return;

    try {
      if (!showRefresh) {
        setIsLoading(true);
      }
      setError(null);

      // Fetch team details using store method (handles caching)
      // CRITICAL: Always verify cached team matches current tenant_id to prevent
      // showing wrong team data when switching workspaces
      let teamData = currentTeam;
      const teamIdMismatch = currentTeam && currentTeam.id !== teamId;
      
      if (!currentTeam || teamIdMismatch || showRefresh) {
        if (process.env.NODE_ENV === 'development' && teamIdMismatch) {
          console.log('Dashboard: Team ID mismatch detected, fetching correct team', {
            cachedTeamId: currentTeam?.id,
            expectedTeamId: teamId,
          });
        }
        teamData = await fetchTeamDetails(teamId);
      }

      // Only fetch metrics if we have a team
      if (teamData) {
        const metricsData = await fetchMetricsData();
        if (metricsData) {
          setTeamMetrics(metricsData);
        }
      }

    } catch (err) {
      console.error('Dashboard data fetch error:', err);
      const errorMessage = safeErrorHandler(err);
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, [
    teamId,
    isAuthenticated,
    currentTeam,
    fetchTeamDetails,
    fetchMetricsData,
    setTeamMetrics,
    setError,
    setIsLoading
  ]);

  return {
    currentTeam,
    teamMetrics,
    isLoading,
    error,
    fetchDashboardData,
  };
};

export default function TeamWorkspaceDashboard() {
  const router = useRouter();
  const { user } = useAuthStore();
  const [refreshing, setRefreshing] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  
  const {
    currentTeam,
    teamMetrics,
    isLoading,
    error,
    fetchDashboardData
  } = useDashboardData();

  // Add credits data hook
  const { 
    creditsData, 
    isLoading: creditsLoading, 
    error: creditsError, 
    fetchCreditsData 
  } = useCreditsData(currentTeam);

  // Memoized calculations for better performance - now using creditsData
  const creditStats = useMemo(() => {
    // Use creditsData if available, otherwise fallback to currentTeam
    if (creditsData) {
      const total = Math.max(creditsData.tenant_total_active_credits + creditsData.user_total_consumed_in_tenant, 1);
      const remaining = Math.max(creditsData.tenant_total_active_credits, 0);
      const used = Math.max(creditsData.user_total_consumed_in_tenant, 0);
      const percentage = total > 0 ? Math.round((remaining / total) * 100) : 0;
      const usedPercentage = total > 0 ? Math.round((used / total) * 100) : 0;
      
      let status: 'good' | 'medium' | 'low' | 'empty' = 'low';
      let color = 'text-red-500 dark:text-red-400';
      let progressColor = 'bg-red-500';
      
      if (percentage > 60) {
        status = 'good';
        color = 'text-emerald-500 dark:text-emerald-400';
        progressColor = 'bg-emerald-500';
      } else if (percentage > 30) {
        status = 'medium';
        color = 'text-amber-500 dark:text-amber-400';
        progressColor = 'bg-amber-500';
      } else if (percentage > 0) {
        status = 'low';
        color = 'text-red-500 dark:text-red-400';
        progressColor = 'bg-red-500';
      } else {
        status = 'empty';
        color = 'text-gray-400 dark:text-gray-500';
        progressColor = 'bg-gray-400';
      }
      
      return { 
        percentage, 
        usedPercentage, 
        status, 
        color, 
        progressColor,
        total, 
        remaining, 
        used 
      };
    }
    
    // Fallback to currentTeam data
    if (!currentTeam) return { 
      percentage: 0, 
      usedPercentage: 0,
      status: 'empty', 
      color: 'text-gray-400',
      progressColor: 'bg-gray-400',
      total: 0, 
      remaining: 0, 
      used: 0 
    };
    
    const total = currentTeam.credit_pool_total || 0;
    const remaining = currentTeam.credit_pool_remaining || 0;
    const used = currentTeam.credit_pool_used || 0;
    
    if (total === 0) return { 
      percentage: 0, 
      usedPercentage: 0,
      status: 'empty', 
      color: 'text-gray-400',
      progressColor: 'bg-gray-400',
      total, 
      remaining, 
      used 
    };
    
    const percentage = Math.round((remaining / total) * 100);
    const usedPercentage = Math.round((used / total) * 100);
    
    let status: 'good' | 'medium' | 'low' | 'empty' = 'low';
    let color = 'text-red-500 dark:text-red-400';
    let progressColor = 'bg-red-500';
    
    if (percentage > 60) {
      status = 'good';
      color = 'text-emerald-500 dark:text-emerald-400';
      progressColor = 'bg-emerald-500';
    } else if (percentage > 30) {
      status = 'medium';
      color = 'text-amber-500 dark:text-amber-400';
      progressColor = 'bg-amber-500';
    } else if (percentage > 0) {
      status = 'low';
      color = 'text-red-500 dark:text-red-400';
      progressColor = 'bg-red-500';
    } else {
      status = 'empty';
      color = 'text-gray-400 dark:text-gray-500';
      progressColor = 'bg-gray-400';
    }
    
    return { 
      percentage, 
      usedPercentage, 
      status, 
      color, 
      progressColor,
      total, 
      remaining, 
      used 
    };
  }, [creditsData, currentTeam]);

  const formatNumber = useCallback((num: number) => {
    if (num === 0) return '0';
    return new Intl.NumberFormat('en-US', { 
      notation: num > 999 ? 'compact' : 'standard',
      maximumFractionDigits: 1 
    }).format(num);
  }, []);

  const getDaysSinceCreation = useCallback((createdAt: string) => {
    try {
      const created = new Date(createdAt).getTime();
      const now = Date.now();
      return Math.floor((now - created) / (1000 * 60 * 60 * 24));
    } catch {
      return 0;
    }
  }, []);

  const getDaysUntilReset = useCallback((resetDate: string) => {
    try {
      const reset = new Date(resetDate).getTime();
      const now = Date.now();
      const days = Math.ceil((reset - now) / (1000 * 60 * 60 * 24));
      return Math.max(0, days); // Prevent negative days
    } catch {
      return 0;
    }
  }, []);

  // Data fetching effect with error boundary
  useEffect(() => {
    const loadData = async () => {
      try {
        await fetchDashboardData();
        setLocalError(null);
      } catch (err) {
        const errorMessage = safeErrorHandler(err);
        setLocalError(errorMessage);
        console.error('Dashboard data loading failed:', err);
      }
    };

    loadData();
  }, [fetchDashboardData]);

  // Fetch credits when team changes
  useEffect(() => {
    if (!currentTeam?.id) return;

    // Small startup delay to avoid racing with auth initialization
    const t = setTimeout(() => {
      fetchCreditsData();
    }, 300);

    return () => clearTimeout(t);
  }, [currentTeam?.id, fetchCreditsData]);

  // Auto-refresh credits every 60 seconds
  useEffect(() => {
    if (!currentTeam?.id) return;

    const interval = setInterval(() => {
      fetchCreditsData();
    }, 60000);

    return () => clearInterval(interval);
  }, [currentTeam?.id, fetchCreditsData]);

  const handleRetry = useCallback(async () => {
    try {
      setLocalError(null);
      await fetchDashboardData();
      await fetchCreditsData(true);
    } catch (err) {
      const errorMessage = safeErrorHandler(err);
      setLocalError(errorMessage);
    }
  }, [fetchDashboardData, fetchCreditsData]);

  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    try {
      setLocalError(null);
      await fetchDashboardData(true);
      await fetchCreditsData(true);
    } catch (err) {
      const errorMessage = safeErrorHandler(err);
      setLocalError(errorMessage);
    } finally {
      setRefreshing(false);
    }
  }, [fetchDashboardData, fetchCreditsData]);

  // Combine store error and local error
  const displayError = localError || error;

  // Show skeleton during initial load
  if (isLoading && !currentTeam) {
    return <DashboardSkeleton />;
  }

  // Show error state if there's an error and no data
  if (displayError && !currentTeam) {
    return <ErrorState error={displayError} onRetry={handleRetry} />;
  }

  // If no team data but not loading, show empty state
  if (!currentTeam && !isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] text-center p-6">
        <div className="w-16 h-16 bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center mb-4">
          <AlertTriangle className="w-8 h-8 text-gray-400" />
        </div>
        <h3 className="text-lg font-semibold text-brand-500 dark:text-white mb-2">
          No Team Data
        </h3>
        <p className="text-gray-600 dark:text-gray-400 mb-6">
          Unable to load team information. Please try again.
        </p>
        <button
          onClick={handleRetry}
          className="px-4 py-2 bg-brand-500 text-white rounded-lg hover:bg-brand-600 transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4 mx-auto py-2">
      {/* Header with refresh button */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4"
      >
        <div className="flex items-center gap-3">
          <div className="w-2 h-8 bg-brand-500 rounded-full" />
          <div>
            <h1 className="text-2xl font-bold text-gray-500 dark:text-white">
              Welcome back, <span className="text-brand-500 dark:text-brand-300">{user?.full_name?.split(' ')[0] || 'there'}</span> 👋
            </h1>
            <div className="flex items-center gap-2 mt-1">
              <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-brand-50 text-brand-700 border border-brand-200 dark:bg-brand-900/20 dark:text-brand-300 dark:border-brand-800">
                {currentTeam?.name}
              </span>
              {currentTeam?.organization_name && (
                <>
                  <div className="w-1 h-1 rounded-full bg-gray-400 dark:bg-gray-500" />
                  <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-gray-50 text-gray-700 border border-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:border-gray-700">
                    {currentTeam?.organization_name}
                  </span>
                </>
              )}
            </div>
          </div>
        </div>
        
        <button
          onClick={handleRefresh}
          disabled={refreshing || isLoading}
          className="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          {refreshing ? 'Refreshing...' : 'Refresh'}
        </button>
      </motion.div>

      {/* Error Alert */}
      {/* <AnimatePresence>
        {displayError && currentTeam && (
          <motion.div 
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl flex items-start gap-3"
          >
            <AlertTriangle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h3 className="text-sm font-medium text-red-900 dark:text-red-200">
                Partial data loaded
              </h3>
              <p className="text-sm text-red-700 dark:text-red-300 mt-1">
                {displayError} Some features might be unavailable.
              </p>
            </div>
            <button
              onClick={handleRetry}
              className="text-sm text-red-700 dark:text-red-300 hover:text-red-900 dark:hover:text-red-100 font-medium"
            >
              Retry
            </button>
          </motion.div>
        )}
      </AnimatePresence> */}

      {/* Key Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Credit Pool */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="group relative p-6 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl hover:shadow-lg transition-all duration-200"
        >
          <div className="flex items-start justify-between mb-4">
            <div className={`p-2.5 rounded-lg ${
              creditStats.status === 'good' ? 'bg-emerald-50 dark:bg-emerald-900/30' :
              creditStats.status === 'medium' ? 'bg-amber-50 dark:bg-amber-900/30' :
              creditStats.status === 'low' ? 'bg-red-50 dark:bg-red-900/30' :
              'bg-gray-50 dark:bg-gray-800'
            }`}>
              <CreditCard className={`w-5 h-5 ${
                creditStats.status === 'good' ? 'text-emerald-600 dark:text-emerald-400' :
                creditStats.status === 'medium' ? 'text-amber-600 dark:text-amber-400' :
                creditStats.status === 'low' ? 'text-red-600 dark:text-red-400' :
                'text-gray-400'
              }`} />
            </div>
            <div className="text-right">
              {creditsLoading ? (
                <RefreshCw className="w-3 h-3 animate-spin text-gray-400" />
              ) : creditsError ? (
                <div className="flex items-center gap-1 text-xs text-red-500">
                  <AlertTriangle className="w-3 h-3" />
                  <span>Error</span>
                </div>
              ) : (
                <>
                  <div className={`text-xs font-medium ${creditStats.color}`}>
                    {creditStats.percentage}% remaining
                  </div>
                  <div className="w-16 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full mt-2 overflow-hidden">
                    <motion.div 
                      initial={{ width: 0 }}
                      animate={{ width: `${creditStats.percentage}%` }}
                      transition={{ duration: 1, ease: "easeOut" }}
                      className={`h-full ${creditStats.progressColor}`}
                    />
                  </div>
                </>
              )}
            </div>
          </div>
          <div className="space-y-1">
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
              Credits Available
            </p>
            <p className="text-2xl font-bold text-brand-500 dark:text-white">
              {formatNumber(creditStats.remaining)}
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              of {formatNumber(creditStats.total)} total • {creditStats.usedPercentage}% used
            </p>
           
          </div>
        </motion.div>

        {/* Team Members */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="group relative p-6 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl hover:shadow-lg transition-all duration-200"
        >
          <div className="flex items-start justify-between mb-4">
            <div className="p-2.5 bg-blue-50 dark:bg-blue-900/30 rounded-lg">
              <Users className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            </div>
            <CheckCircle2 className="w-4 h-4 text-emerald-500" />
          </div>
          <div className="space-y-1">
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
              Team Members
            </p>
            <p className="text-2xl font-bold text-brand-500 dark:text-white">
              {currentTeam?.member_count || 0}
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Active members in team
            </p>
          </div>
        </motion.div>

        {/* Credits Used */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="group relative p-6 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl hover:shadow-lg transition-all duration-200"
        >
          <div className="flex items-start justify-between mb-4">
            <div className="p-2.5 bg-purple-50 dark:bg-purple-900/30 rounded-lg">
              <TrendingUp className="w-5 h-5 text-purple-600 dark:text-purple-400" />
            </div>
            <ArrowUpRight className="w-4 h-4 text-purple-500" />
          </div>
          <div className="space-y-1">
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
              Credits Used
            </p>
            <p className="text-2xl font-bold text-brand-500 dark:text-white">
              {formatNumber(creditStats.used)}
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {creditStats.usedPercentage}% of total pool
            </p>
          </div>
        </motion.div>

        {/* Team Activity */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="group relative p-6 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl hover:shadow-lg transition-all duration-200"
        >
          <div className="flex items-start justify-between mb-4">
            <div className="p-2.5 bg-amber-50 dark:bg-amber-900/30 rounded-lg">
              <Sparkles className="w-5 h-5 text-amber-600 dark:text-amber-400" />
            </div>
            <Clock className="w-4 h-4 text-amber-500" />
          </div>
          <div className="space-y-1">
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
              Invitations
            </p>
            {refreshing ? (
              <div className="flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin text-gray-400" />
                <span className="text-sm text-gray-500">Updating...</span>
              </div>
            ) : (
              <>
                <p className="text-2xl font-bold text-brand-500 dark:text-white">
                  {teamMetrics?.invitations?.accepted || 0}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {teamMetrics?.invitations?.sent || 0} sent • {Math.max(0, (teamMetrics?.invitations?.sent || 0) - (teamMetrics?.invitations?.accepted || 0))} pending
                </p>
              </>
            )}
          </div>
        </motion.div>
      </div>

      {/* Quick Actions */}
      <QuickActions />

      {/* Team Overview */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
        className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl overflow-hidden"
      >
        <div className="p-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Left Column - Basic Info */}
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold text-brand-500 dark:text-white mb-4 flex items-center gap-2">
                  <Building className="w-5 h-5 text-brand-500" />
                  Team Information
                </h3>
                <div className="space-y-4">
                  {/* Team Name */}
                  <div className="group p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-brand-200 dark:hover:border-brand-700 transition-colors">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">
                          Team Name
                        </p>
                        <p className="text-base font-semibold text-brand-500 dark:text-white">
                          {currentTeam?.name}
                        </p>
                      </div>
                      <div className="p-1.5 bg-white dark:bg-gray-700 rounded-md shadow-sm">
                        <Users className="w-3.5 h-3.5 text-gray-500 dark:text-gray-400" />
                      </div>
                    </div>
                  </div>

                  {/* Organization */}
                  <div className="group p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-brand-200 dark:hover:border-brand-700 transition-colors">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">
                          Organization
                        </p>
                        <p className="text-base font-semibold text-brand-500 dark:text-white">
                          {currentTeam?.organization_name || "No organization"}
                        </p>
                        {!currentTeam?.organization_name && (
                          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                            Independent team
                          </p>
                        )}
                      </div>
                      <div className="p-1.5 bg-white dark:bg-gray-700 rounded-md shadow-sm">
                        <Building className="w-3.5 h-3.5 text-gray-500 dark:text-gray-400" />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Right Column - Leadership & Timeline */}
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold text-brand-500 dark:text-white mb-4 flex items-center gap-2">
                  <User className="w-5 h-5 text-brand-500" />
                  Team Leadership
                </h3>
                <div className="space-y-4">
                  {/* Team Leader */}
                  <div className="group p-4 bg-brand-50 dark:bg-brand-900/20 rounded-lg border border-brand-200 dark:border-brand-800/50 hover:shadow-md transition-all duration-200">
                    <div className="flex items-start gap-3">
                      <div className="p-2 bg-brand-500 rounded-lg">
                        <User className="w-4 h-4 text-white" />
                      </div>
                      <div className="flex-1">
                        <p className="text-xs font-medium text-brand-700 dark:text-brand-400 uppercase tracking-wide mb-2">
                          Team Leader
                        </p>
                        <p className="text-base font-semibold text-brand-500 dark:text-white">
                          {currentTeam?.team_leader_name || "No leader assigned"}
                        </p>
                        {currentTeam?.team_leader_email && (
                          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                            {currentTeam.team_leader_email}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Creation Date */}
                  <div className="group p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-brand-200 dark:hover:border-brand-700 transition-colors">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-gray-200 dark:bg-gray-700 rounded-lg">
                        <Calendar className="w-4 h-4 text-gray-600 dark:text-gray-400" />
                      </div>
                      <div className="flex-1">
                        <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1">
                          Team Created
                        </p>
                        <p className="text-base font-semibold text-brand-500 dark:text-white">
                          {currentTeam?.created_at 
                            ? new Date(currentTeam.created_at).toLocaleDateString('en-US', {
                                month: 'long',
                                day: 'numeric',
                                year: 'numeric'
                              })
                            : "Date not available"
                          }
                        </p>
                        {currentTeam?.created_at && (
                          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                            {getDaysSinceCreation(currentTeam.created_at)} days ago
                          </p>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Pool Reset Date */}
                  {currentTeam?.pool_reset_date && (
                    <div className="group p-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800/50 hover:shadow-md transition-all duration-200">
                      <div className="flex items-center gap-3">
                        <div className="p-2 bg-amber-500 rounded-lg">
                          <Clock className="w-4 h-4 text-white" />
                        </div>
                        <div className="flex-1">
                          <p className="text-xs font-medium text-amber-700 dark:text-amber-400 uppercase tracking-wide mb-1">
                            Next Credit Reset
                          </p>
                          <p className="text-base font-semibold text-brand-500 dark:text-white">
                            {new Date(currentTeam.pool_reset_date).toLocaleDateString('en-US', {
                              month: 'long',
                              day: 'numeric',
                              year: 'numeric'
                            })}
                          </p>
                          <p className="text-xs text-amber-600 dark:text-amber-400 mt-1">
                            {getDaysUntilReset(currentTeam.pool_reset_date)} days remaining
                          </p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}