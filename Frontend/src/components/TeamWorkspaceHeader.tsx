"use client";

import React, { useEffect, useRef, useState, useCallback, useMemo } from "react";
import { useRouter } from "next/navigation";

import { Coins, RefreshCw, AlertCircle, LayoutDashboard } from "lucide-react";
import { ThemeToggleButton } from "./common/ThemeToggleButton";
import UserDropdown from "./header/UserDropdown";
import { useAuthStore } from "@/stores/authStore";
import { Button } from "@/components/ui/button";
import Rating from "./Rating";

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

interface TeamWorkspaceHeaderProps {
  currentTeam: {
    id: string;
    name: string;
    organization_name?: string;
    credit_pool_remaining?: number;
    credit_pool_total?: number;
  } | null;
  isLoading?: boolean;
  onToggleSidebar?: () => void;
  isSidebarExpanded?: boolean;
}

// Custom hook for credits data management
const useCreditsData = (currentTeam: TeamWorkspaceHeaderProps['currentTeam']) => {
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
        console.log('✅ Credits data fetched successfully:', {
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
        console.error('❌ Error fetching credits:', err);
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

export default function TeamWorkspaceHeader({
  currentTeam,
  isLoading: teamLoading = false,
}: TeamWorkspaceHeaderProps) {
  const router = useRouter();
  const [isNavigating, setIsNavigating] = useState(false);
  const { creditsData, isLoading: creditsLoading, error: creditsError, fetchCreditsData } = useCreditsData(currentTeam);

  // Stable reference to current team ID for effects
  const currentTeamId = currentTeam?.id;

  // Fetch credits only when team changes, not on every render
  useEffect(() => {
    if (!currentTeamId) return;

    // Small startup delay to avoid racing with auth initialization in dev
    const t = setTimeout(() => {
      fetchCreditsData();
    }, 300);

    return () => clearTimeout(t);
  }, [currentTeamId]); // Only depend on team changes; fetch function prevents duplicates

  // Auto-refresh credits - use ref to avoid recreation
  const fetchCreditsDataRef = useRef(fetchCreditsData);
  useEffect(() => {
    fetchCreditsDataRef.current = fetchCreditsData;
  }, [fetchCreditsData]);

  useEffect(() => {
    if (!currentTeamId) return;

    const interval = setInterval(() => {
      fetchCreditsDataRef.current();
    }, 60000); // 60 seconds

    return () => clearInterval(interval);
  }, [currentTeamId]); // Only depend on currentTeamId

  // Memoized credit stats calculation
  const creditStats = useMemo(() => {
    if (!creditsData) {
      return {
        remaining: currentTeam?.credit_pool_remaining || 0,
        total: currentTeam?.credit_pool_total || 0,
        consumed: 0,
        percentage: 0,
      };
    }

    const total = Math.max(creditsData.tenant_total_active_credits + creditsData.user_total_consumed_in_tenant, 1);
    const remaining = Math.max(creditsData.tenant_total_active_credits, 0);
    const consumed = Math.max(creditsData.user_total_consumed_in_tenant, 0);
    const percentage = total > 0 ? (consumed / total) * 100 : 0;

    return { 
      remaining, 
      total, 
      consumed, 
      percentage: Math.min(percentage, 100) 
    };
  }, [creditsData, currentTeam]);

  // Memoized credit formatting
  const formatCredits = useCallback((credits: number) => {
    if (credits >= 1000000) {
      return `${(credits / 1000000).toFixed(1)}M`;
    }
    if (credits >= 1000) {
      return `${(credits / 1000).toFixed(1)}K`;
    }
    return credits.toLocaleString(undefined, { maximumFractionDigits: 0 });
  }, []);

  // Determine credit status for styling
  const creditStatus = useMemo(() => {
    if (creditStats.percentage >= 90) return 'critical';
    if (creditStats.percentage >= 75) return 'warning';
    return 'normal';
  }, [creditStats.percentage]);

  // Status-based styling
  const statusStyles = useMemo(() => ({
    normal: {
      container: "border-green-400/60 bg-gradient-to-r from-green-50 to-green-100 hover:from-green-100 hover:to-green-200 dark:from-green-900/20 dark:to-green-800/20 dark:text-green-200 dark:border-green-500/40 text-green-800",
      dot: "bg-green-500",
    },
    warning: {
      container: "border-amber-400/60 bg-gradient-to-r from-amber-50 to-amber-100 hover:from-amber-100 hover:to-amber-200 dark:from-amber-900/20 dark:to-amber-800/20 dark:text-amber-200 dark:border-amber-500/40 text-amber-800",
      dot: "bg-amber-500",
    },
    critical: {
      container: "border-red-400/60 bg-gradient-to-r from-red-50 to-red-100 hover:from-red-100 hover:to-red-200 dark:from-red-900/20 dark:to-red-800/20 dark:text-red-200 dark:border-red-500/40 text-red-800",
      dot: "bg-red-500",
    },
  }), []);

  const currentStyles = statusStyles[creditStatus];

  // Handle manual refresh
  const handleRefreshCredits = useCallback(() => {
    fetchCreditsData(true); // Force refresh
  }, [fetchCreditsData]);

  const handleChooseWorkspace = useCallback(() => {
    if (isNavigating) return;
    setIsNavigating(true);
    router.push("/choose-workspace");
  }, [isNavigating, router]);

  // Show simplified loading state for team
  if (teamLoading && !currentTeam) {
    return (
      <header className="sticky top-0 z-40 w-full border-b border-gray-200 dark:border-gray-800 bg-white/95 dark:bg-gray-900/95 backdrop-blur supports-[backdrop-filter]:bg-white/60 dark:supports-[backdrop-filter]:bg-gray-900/60">
        <div className="flex h-16 items-center justify-between px-4 sm:px-6">
          <div className="flex items-center gap-4">
            <div className="h-8 w-32 bg-gray-200 dark:bg-gray-700 rounded animate-pulse"></div>
          </div>
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 bg-gray-200 dark:bg-gray-700 rounded-full animate-pulse"></div>
            <div className="h-9 w-9 bg-gray-200 dark:bg-gray-700 rounded-full animate-pulse"></div>
          </div>
        </div>
      </header>
    );
  }

  return (
    <header className="sticky top-0 z-40 w-full border-b border-gray-200 dark:border-gray-800 bg-white/95 dark:bg-gray-900/95 backdrop-blur supports-[backdrop-filter]:bg-white/60 dark:supports-[backdrop-filter]:bg-gray-900/60">
      <div className="flex flex-wrap items-center justify-between gap-2 py-2 px-4 sm:px-6">

        {/* Left Section - Team Info & Credits */}
        <div className="flex items-center gap-2 min-w-0 w-full sm:flex-1">
         
         

          {/* Credit Balance - Hidden on mobile, visible on desktop */}
          {currentTeam && (
            <div className="hidden lg:block">
              <div 
                className={`rounded-lg border px-4 py-2 cursor-pointer shadow-sm hover:shadow-md transition-all duration-200 ${currentStyles.container}`}
                onClick={handleRefreshCredits}
                title="Click to refresh credits"
              >
                <div className="flex items-center gap-2 min-w-0">
                  {creditsLoading ? (
                    <RefreshCw className="w-3 h-3 animate-spin" />
                  ) : creditsError ? (
                    <AlertCircle className="w-3 h-3" />
                  ) : (
                    <div className={`w-2 h-2 rounded-full ${currentStyles.dot} ${!creditsLoading && 'animate-pulse'}`} />
                  )}
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium truncate">
                      {creditsError ? (
                        <span>Error loading credits</span>
                      ) : (
                        <>
                          <span className="font-bold">{formatCredits(creditStats.remaining)}</span>
                          {" "}of{" "}
                          <span className="font-bold">{formatCredits(creditStats.total)}</span>
                          {" "}credits
                          {creditStats.consumed > 0 && (
                            <span className="text-xs ml-1 opacity-75">
                              ({formatCredits(creditStats.consumed)} used)
                            </span>
                          )}
                        </>
                      )}
                    </p>
                  </div>
                  {creditsError && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleRefreshCredits();
                      }}
                      className="ml-2 text-xs hover:underline"
                      title="Retry loading credits"
                    >
                      Retry
                    </button>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right Section - Actions */}
        <div className="flex flex-wrap items-center gap-2 flex-shrink-0 w-full sm:w-auto justify-end">

          {/* Mobile Credit Indicator */}
          {currentTeam && (
            <div className="lg:hidden">
              <button
                onClick={handleRefreshCredits}
                className={`flex items-center gap-1 px-3 py-2 rounded-lg border text-sm font-medium ${currentStyles.container}`}
                title="Credits"
              >
                {creditsLoading ? (
                  <RefreshCw className="w-3 h-3 animate-spin" />
                ) : creditsError ? (
                  <AlertCircle className="w-3 h-3" />
                ) : (
                  <Coins className="w-3 h-3" />
                )}
                <span className="font-bold">{formatCredits(creditStats.remaining)}</span>
              </button>
            </div>
          )}
          <div>

                    <Rating variant="dropdown" />
          </div>

          {/* Theme Toggle */}
          <ThemeToggleButton />

          {/* User Dropdown */}
          <UserDropdown />
        </div>
      </div>
    </header>
  );
}