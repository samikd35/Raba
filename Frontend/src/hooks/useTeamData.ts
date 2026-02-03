import { useEffect, useCallback, useRef } from 'react';
import { useTeamStore } from '@/stores/teamStore';
import { teamService } from '@/lib/api/teamService';
import { toast } from "react-hot-toast";

/**
 * Custom hook that implements stale-while-revalidate pattern for team data
 * 
 * Features:
 * - Returns cached data immediately if available
 * - Revalidates in background if cache is stale
 * - Automatically invalidates cache on mutations
 * - Supports manual refresh
 * 
 * @param organizationId - The organization ID to fetch teams for
 * @param options - Configuration options
 */
export const useTeamData = (
  organizationId: string | null | undefined,
  options: {
    enabled?: boolean;
    refetchInterval?: number;
    onError?: (error: Error) => void;
  } = {}
) => {
  const {
    enabled = true,
    refetchInterval,
    onError,
  } = options;

  const currentTeam = useTeamStore((state) => state.currentTeam);
  const teams = useTeamStore((state) => state.teams);
  const isLoading = useTeamStore((state) => state.isLoading);
  const error = useTeamStore((state) => state.error);
  
  const setCurrentTeam = useTeamStore((state) => state.setCurrentTeam);
  const setTeams = useTeamStore((state) => state.setTeams);
  const setIsLoading = useTeamStore((state) => state.setIsLoading);
  const setError = useTeamStore((state) => state.setError);
  
  const isCurrentTeamCacheValid = useTeamStore((state) => state.isCurrentTeamCacheValid);
  const isTeamsCacheValid = useTeamStore((state) => state.isTeamsCacheValid);
  const shouldRevalidateCurrentTeam = useTeamStore((state) => state.shouldRevalidateCurrentTeam);
  const shouldRevalidateTeams = useTeamStore((state) => state.shouldRevalidateTeams);

  const isFetchingRef = useRef(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const fetchTeams = useCallback(async (silent = false) => {
    if (!organizationId || !enabled || isFetchingRef.current) {
      return;
    }

    try {
      isFetchingRef.current = true;
      
      // Only show loading state if not silent (background revalidation)
      if (!silent) {
        setIsLoading(true);
      }

      const fetchedTeams = await teamService.fetchTeams(organizationId);
      
      // Convert TeamResponse[] to Team[] by providing defaults for optional fields
      const teams = fetchedTeams.map(team => ({
        id: team.id,
        name: team.name,
        organization_id: team.organization_id,
        organization_name: team.organization_name || '',
        team_leader_id: team.team_leader_id || '',
        team_leader_name: team.team_leader_name || '',
        team_leader_email: team.team_leader_email || '',
        member_count: team.member_count || 0,
        credit_pool_total: team.credit_pool_total || 0,
        credit_pool_used: team.credit_pool_used || 0,
        credit_pool_remaining: team.credit_pool_remaining || 0,
        pool_reset_date: team.pool_reset_date || '',
        status: team.status || 'active' as const,
        created_at: team.created_at || new Date().toISOString(),
      }));
      
      setTeams(teams);
      
      // Update current team if it exists in the fetched teams
      if (currentTeam) {
        const updatedCurrentTeam = teams.find(t => t.id === currentTeam.id);
        if (updatedCurrentTeam) {
          setCurrentTeam(updatedCurrentTeam);
        }
      }

      setError(null);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch teams';
      console.error('useTeamData: Error fetching teams', err);
      setError(errorMessage);
      
      if (onError) {
        onError(err instanceof Error ? err : new Error(errorMessage));
      } else if (!silent) {
        toast.error(errorMessage);
      }
    } finally {
      isFetchingRef.current = false;
      if (!silent) {
        setIsLoading(false);
      }
    }
  }, [organizationId, enabled, currentTeam, setTeams, setCurrentTeam, setIsLoading, setError, onError]);

  // Initial fetch or revalidation
  useEffect(() => {
    if (!organizationId || !enabled) {
      return;
    }

    const teamsCacheValid = isTeamsCacheValid();
    const shouldRevalidate = shouldRevalidateTeams();

    // If cache is invalid, fetch immediately
    if (!teamsCacheValid) {
      fetchTeams(false);
    } 
    // If cache is valid but stale, revalidate in background
    else if (shouldRevalidate) {
      fetchTeams(true);
    }
  }, [organizationId, enabled, fetchTeams, isTeamsCacheValid, shouldRevalidateTeams]);

  // Set up refetch interval if specified
  useEffect(() => {
    if (!refetchInterval || !enabled || !organizationId) {
      return;
    }

    intervalRef.current = setInterval(() => {
      fetchTeams(true); // Silent background refresh
    }, refetchInterval);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [refetchInterval, enabled, organizationId, fetchTeams]);

  // Manual refresh function
  const refresh = useCallback(() => {
    return fetchTeams(false);
  }, [fetchTeams]);

  return {
    currentTeam,
    teams,
    isLoading,
    error,
    refresh,
    isCacheValid: isTeamsCacheValid(),
    shouldRevalidate: shouldRevalidateTeams(),
  };
};

/**
 * Custom hook for fetching team metrics with caching
 */
export const useTeamMetrics = (
  teamId: string | null | undefined,
  options: {
    enabled?: boolean;
    refetchInterval?: number;
    onError?: (error: Error) => void;
  } = {}
) => {
  const {
    enabled = true,
    refetchInterval,
    onError,
  } = options;

  const teamMetrics = useTeamStore((state) => state.teamMetrics);
  const isLoading = useTeamStore((state) => state.isLoading);
  const error = useTeamStore((state) => state.error);
  
  const setTeamMetrics = useTeamStore((state) => state.setTeamMetrics);
  const setIsLoading = useTeamStore((state) => state.setIsLoading);
  const setError = useTeamStore((state) => state.setError);
  
  const isMetricsCacheValid = useTeamStore((state) => state.isMetricsCacheValid);
  const shouldRevalidateMetrics = useTeamStore((state) => state.shouldRevalidateMetrics);

  const isFetchingRef = useRef(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const fetchMetrics = useCallback(async (silent = false) => {
    if (!teamId || !enabled || isFetchingRef.current) {
      return;
    }

    try {
      isFetchingRef.current = true;
      
      if (!silent) {
        setIsLoading(true);
      }

      const metrics = await teamService.getTeamMetrics(teamId);
      setTeamMetrics(metrics);
      setError(null);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch team metrics';
      console.error('useTeamMetrics: Error fetching metrics', err);
      setError(errorMessage);
      
      if (onError) {
        onError(err instanceof Error ? err : new Error(errorMessage));
      } else if (!silent) {
        toast.error(errorMessage);
      }
    } finally {
      isFetchingRef.current = false;
      if (!silent) {
        setIsLoading(false);
      }
    }
  }, [teamId, enabled, setTeamMetrics, setIsLoading, setError, onError]);

  // Initial fetch or revalidation
  useEffect(() => {
    if (!teamId || !enabled) {
      return;
    }

    const metricsCacheValid = isMetricsCacheValid();
    const shouldRevalidate = shouldRevalidateMetrics();

    if (!metricsCacheValid) {
      fetchMetrics(false);
    } else if (shouldRevalidate) {
      fetchMetrics(true);
    }
  }, [teamId, enabled, fetchMetrics, isMetricsCacheValid, shouldRevalidateMetrics]);

  // Set up refetch interval if specified
  useEffect(() => {
    if (!refetchInterval || !enabled || !teamId) {
      return;
    }

    intervalRef.current = setInterval(() => {
      fetchMetrics(true);
    }, refetchInterval);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [refetchInterval, enabled, teamId, fetchMetrics]);

  const refresh = useCallback(() => {
    return fetchMetrics(false);
  }, [fetchMetrics]);

  return {
    teamMetrics,
    isLoading,
    error,
    refresh,
    isCacheValid: isMetricsCacheValid(),
    shouldRevalidate: shouldRevalidateMetrics(),
  };
};
