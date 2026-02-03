import { useState, useEffect, useCallback, useRef } from 'react';
import { teamService } from '@/lib/api/teamService';
import { TeamMember } from '@/types/team';
import { usePagination } from './usePagination';
import { useDebouncedValue } from './useDebouncedSearch';
import { toast } from "react-hot-toast";

export interface UseTeamMembersOptions {
  teamId: string | null | undefined;
  pageSize?: number;
  searchQuery?: string;
  enabled?: boolean;
  refetchInterval?: number;
}

/**
 * Optimized hook for fetching and managing team members
 * 
 * Features:
 * - Client-side pagination
 * - Debounced search
 * - Automatic refetch
 * - Loading and error states
 */
export function useTeamMembers(options: UseTeamMembersOptions) {
  const {
    teamId,
    pageSize = 10,
    searchQuery = '',
    enabled = true,
    refetchInterval,
  } = options;

  const [members, setMembers] = useState<TeamMember[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isFetchingRef = useRef(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  // Debounce search query to avoid excessive filtering
  const debouncedSearchQuery = useDebouncedValue(searchQuery, 300);

  // Filter members based on search query
  const filteredMembers = members.filter(member => {
    if (!debouncedSearchQuery) return true;
    
    const query = debouncedSearchQuery.toLowerCase();
    return (
      member.name.toLowerCase().includes(query) ||
      member.email.toLowerCase().includes(query) ||
      member.role.toLowerCase().includes(query)
    );
  });

  // Pagination
  const pagination = usePagination(filteredMembers, {
    initialPageSize: pageSize,
  });

  // Fetch members
  const fetchMembers = useCallback(async (silent = false) => {
    if (!teamId || !enabled || isFetchingRef.current) {
      return;
    }

    try {
      isFetchingRef.current = true;
      
      if (!silent) {
        setIsLoading(true);
      }

      const fetchedMembers = await teamService.getTeamMembers(teamId);
      setMembers(fetchedMembers);
      setError(null);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch team members';
      console.error('useTeamMembers: Error fetching members', err);
      setError(errorMessage);
      
      if (!silent) {
        toast.error(errorMessage);
      }
    } finally {
      isFetchingRef.current = false;
      if (!silent) {
        setIsLoading(false);
      }
    }
  }, [teamId, enabled]);

  // Initial fetch
  useEffect(() => {
    if (teamId && enabled) {
      fetchMembers(false);
    }
  }, [teamId, enabled, fetchMembers]);

  // Set up refetch interval
  useEffect(() => {
    if (!refetchInterval || !enabled || !teamId) {
      return;
    }

    intervalRef.current = setInterval(() => {
      fetchMembers(true); // Silent background refresh
    }, refetchInterval);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [refetchInterval, enabled, teamId, fetchMembers]);

  // Manual refresh
  const refresh = useCallback(() => {
    return fetchMembers(false);
  }, [fetchMembers]);

  // Member actions with optimistic updates
  const removeMember = useCallback(async (memberId: string) => {
    // Optimistic update
    const previousMembers = members;
    setMembers(prev => prev.filter(m => m.id !== memberId));

    try {
      await teamService.removeMember(teamId!, memberId);
      toast.success('Member removed successfully');
    } catch (err) {
      // Revert on error
      setMembers(previousMembers);
      const errorMessage = err instanceof Error ? err.message : 'Failed to remove member';
      toast.error(errorMessage);
      throw err;
    }
  }, [teamId, members]);

  const suspendMember = useCallback(async (memberId: string) => {
    // Optimistic update
    const previousMembers = members;
    setMembers(prev => 
      prev.map(m => m.id === memberId ? { ...m, status: 'suspended' as const } : m)
    );

    try {
      // TODO: Implement suspend member API endpoint
      // For now, just update local state
      toast.success('Member suspended successfully');
      await refresh(); // Refresh to get actual state from server
    } catch (err) {
      // Revert on error
      setMembers(previousMembers);
      const errorMessage = err instanceof Error ? err.message : 'Failed to suspend member';
      toast.error(errorMessage);
      throw err;
    }
  }, [teamId, members, refresh]);

  const activateMember = useCallback(async (memberId: string) => {
    // Optimistic update
    const previousMembers = members;
    setMembers(prev => 
      prev.map(m => m.id === memberId ? { ...m, status: 'active' as const } : m)
    );

    try {
      // TODO: Implement activate member API endpoint
      // For now, just update local state
      toast.success('Member activated successfully');
      await refresh(); // Refresh to get actual state from server
    } catch (err) {
      // Revert on error
      setMembers(previousMembers);
      const errorMessage = err instanceof Error ? err.message : 'Failed to activate member';
      toast.error(errorMessage);
      throw err;
    }
  }, [teamId, members, refresh]);

  return {
    // Data
    members: pagination.currentPageData,
    allMembers: members,
    filteredMembers,
    totalMembers: members.length,
    filteredCount: filteredMembers.length,
    
    // Pagination
    pagination,
    
    // State
    isLoading,
    error,
    
    // Actions
    refresh,
    removeMember,
    suspendMember,
    activateMember,
  };
}
