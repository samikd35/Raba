import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { Team, TeamMetrics } from '@/types/team';

// Cache metadata interface
interface CacheMetadata {
  timestamp: number;
  expiresAt: number;
}

// Cache configuration
const CACHE_CONFIG = {
  TEAM_TTL: 5 * 60 * 1000, // 5 minutes
  TEAMS_LIST_TTL: 10 * 60 * 1000, // 10 minutes
  METRICS_TTL: 2 * 60 * 1000, // 2 minutes
  STALE_WHILE_REVALIDATE: true,
} as const;

// Team State Interface
interface TeamState {
  currentTeam: Team | null;
  teams: Team[];
  teamMetrics: TeamMetrics | null;
  isLoading: boolean;
  error: string | null;
  // Cache metadata
  currentTeamCache: CacheMetadata | null;
  teamsCache: CacheMetadata | null;
  metricsCache: CacheMetadata | null;
  user_role: string | null;
}

// Team Actions Interface
interface TeamActions {
  setCurrentTeam: (team: Team | null, skipCache?: boolean) => void;
  setTeams: (teams: Team[], skipCache?: boolean) => void;
  setTeamMetrics: (metrics: TeamMetrics | null, skipCache?: boolean) => void;
  clearTeam: () => void;
  setIsLoading: (isLoading: boolean) => void;
  setError: (error: string | null) => void;
  // New method to fetch team details using teamService
  fetchTeamDetails: (teamId: string) => Promise<Team | null>;
  // Cache management
  invalidateCurrentTeamCache: () => void;
  invalidateTeamsCache: () => void;
  invalidateMetricsCache: () => void;
  invalidateAllCaches: () => void;
  isCurrentTeamCacheValid: () => boolean;
  isTeamsCacheValid: () => boolean;
  isMetricsCacheValid: () => boolean;
  shouldRevalidateCurrentTeam: () => boolean;
  shouldRevalidateTeams: () => boolean;
  shouldRevalidateMetrics: () => boolean;
  setUserRole: (role: string | null) => void; // Added missing action
}

// Combined Store Type
type TeamStore = TeamState & TeamActions;

// Helper function to create cache metadata
const createCacheMetadata = (ttl: number): CacheMetadata => {
  const now = Date.now();
  return {
    timestamp: now,
    expiresAt: now + ttl,
  };
};

// Helper function to check if cache is valid
const isCacheValid = (cache: CacheMetadata | null): boolean => {
  if (!cache) return false;
  return Date.now() < cache.expiresAt;
};

// Helper function to check if cache should be revalidated (stale-while-revalidate)
const shouldRevalidate = (cache: CacheMetadata | null, ttl: number): boolean => {
  if (!cache) return true;
  const now = Date.now();
  const staleThreshold = cache.timestamp + (ttl * 0.7); // Revalidate at 70% of TTL
  return now > staleThreshold;
};

// Create the Zustand store with persist middleware
export const useTeamStore = create<TeamStore>()(
  persist(
    (set, get) => ({
      // Initial state
      currentTeam: null,
      teams: [],
      teamMetrics: null,
      isLoading: false,
      error: null,
      currentTeamCache: null,
      teamsCache: null,
      metricsCache: null,
      user_role: null,

      // Actions
      setCurrentTeam: (team, skipCache = false) => {
        if (process.env.NODE_ENV === 'development') {
          console.log('TeamStore: Setting current team', {
            hasTeam: !!team,
            teamId: team?.id,
            skipCache,
          });
        }
        set({ 
          currentTeam: team, 
          error: null,
          currentTeamCache: skipCache ? null : createCacheMetadata(CACHE_CONFIG.TEAM_TTL),
        });
      },

      setTeams: (teams, skipCache = false) => {
        if (process.env.NODE_ENV === 'development') {
          console.log('TeamStore: Setting teams', {
            count: teams.length,
            skipCache,
          });
        }
        set({ 
          teams, 
          error: null,
          teamsCache: skipCache ? null : createCacheMetadata(CACHE_CONFIG.TEAMS_LIST_TTL),
        });
      },

      setTeamMetrics: (metrics, skipCache = false) => {
        if (process.env.NODE_ENV === 'development') {
          console.log('TeamStore: Setting team metrics', {
            hasMetrics: !!metrics,
            skipCache,
          });
        }
        set({ 
          teamMetrics: metrics, 
          error: null,
          metricsCache: skipCache ? null : createCacheMetadata(CACHE_CONFIG.METRICS_TTL),
        });
      },

      setUserRole: (role: string | null) => {
        set({ user_role: role });
      },

      clearTeam: () => {
        if (process.env.NODE_ENV === 'development') {
          console.log('TeamStore: Clearing team data');
        }
        set({
          currentTeam: null,
          teams: [],
          teamMetrics: null,
          isLoading: false,
          error: null,
          currentTeamCache: null,
          teamsCache: null,
          metricsCache: null,
          user_role: null,
        });
      },

      setIsLoading: (isLoading) => {
        set({ isLoading });
      },

      setError: (error) => {
        if (process.env.NODE_ENV === 'development') {
          // Safe error logging with null handling
          try {
            if (error === null) {
              console.log('TeamStore: Error cleared (set to null)');
            } else if (error instanceof Error) {
              console.error('TeamStore: Error set', error.message, error.stack);
            } else if (typeof error === 'string') {
              console.error('TeamStore: Error set', error);
            } else {
              console.error('TeamStore: Error set', String(error));
            }
          } catch (logError) {
            console.error('TeamStore: Failed to log error', logError);
          }
        }
        set({ error: error === null ? null : (typeof error === 'string' ? error : String(error)), isLoading: false });
      },

      /**
       * Fetch team details using the teamService
       * This method integrates with the new backend API
       */
      fetchTeamDetails: async (teamId: string) => {
        const state = get();
        
        // Validate teamId
        if (!teamId || typeof teamId !== 'string') {
          const errorMessage = 'Invalid team ID provided';
          set({ error: errorMessage, isLoading: false });
          if (process.env.NODE_ENV === 'development') {
            console.error('TeamStore: Invalid team ID', { teamId });
          }
          return null;
        }
        
        // Check if we have valid cached data
        if (state.currentTeam?.id === teamId && isCacheValid(state.currentTeamCache)) {
          if (process.env.NODE_ENV === 'development') {
            console.log('TeamStore: Using cached team data', { teamId });
          }
          return state.currentTeam;
        }

        // Prevent duplicate requests
        if (state.isLoading && state.currentTeam?.id === teamId) {
          if (process.env.NODE_ENV === 'development') {
            console.log('TeamStore: Request already in progress', { teamId });
          }
          return state.currentTeam;
        }

        try {
          if (process.env.NODE_ENV === 'development') {
            console.log('TeamStore: Fetching team details from API', { teamId });
          }

          set({ isLoading: true, error: null });

          // Dynamically import teamService to avoid circular dependency
          const { teamService } = await import('@/lib/api/teamService');
          const teamData = await teamService.getTeamDetails(teamId);

          if (!teamData) {
            throw new Error('No team data received from API');
          }

          if (process.env.NODE_ENV === 'development') {
            console.log('TeamStore: Team details fetched successfully', {
              teamId: teamData.id,
              name: teamData.name,
            });
          }

          // Update store with fetched data
          set({ 
            currentTeam: teamData,
            isLoading: false,
            error: null,
            currentTeamCache: createCacheMetadata(CACHE_CONFIG.TEAM_TTL),
          });

          return teamData;
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Failed to fetch team details';
          
          if (process.env.NODE_ENV === 'development') {
            console.error('TeamStore: Error fetching team details', {
              teamId,
              error: errorMessage,
            });
          }

          set({ 
            isLoading: false, 
            error: errorMessage,
          });

          return null;
        }
      },

      // Cache management actions
      invalidateCurrentTeamCache: () => {
        if (process.env.NODE_ENV === 'development') {
          console.log('TeamStore: Invalidating current team cache');
        }
        set({ currentTeamCache: null });
      },

      invalidateTeamsCache: () => {
        if (process.env.NODE_ENV === 'development') {
          console.log('TeamStore: Invalidating teams cache');
        }
        set({ teamsCache: null });
      },

      invalidateMetricsCache: () => {
        if (process.env.NODE_ENV === 'development') {
          console.log('TeamStore: Invalidating metrics cache');
        }
        set({ metricsCache: null });
      },

      invalidateAllCaches: () => {
        if (process.env.NODE_ENV === 'development') {
          console.log('TeamStore: Invalidating all caches');
        }
        set({
          currentTeamCache: null,
          teamsCache: null,
          metricsCache: null,
        });
      },

      isCurrentTeamCacheValid: () => {
        return isCacheValid(get().currentTeamCache);
      },

      isTeamsCacheValid: () => {
        return isCacheValid(get().teamsCache);
      },

      isMetricsCacheValid: () => {
        return isCacheValid(get().metricsCache);
      },

      shouldRevalidateCurrentTeam: () => {
        return shouldRevalidate(get().currentTeamCache, CACHE_CONFIG.TEAM_TTL);
      },

      shouldRevalidateTeams: () => {
        return shouldRevalidate(get().teamsCache, CACHE_CONFIG.TEAMS_LIST_TTL);
      },

      shouldRevalidateMetrics: () => {
        return shouldRevalidate(get().metricsCache, CACHE_CONFIG.METRICS_TTL);
      },
    }),
    {
      name: 'team-storage',
      storage: createJSONStorage(() => {
        // Safe localStorage access with fallback
        try {
          if (typeof window !== 'undefined' && window.localStorage) {
            return localStorage;
          }
        } catch (error) {
          if (process.env.NODE_ENV === 'development') {
            console.warn('TeamStore: localStorage not available, using memory storage');
          }
        }
        
        // Fallback to memory storage
        return {
          getItem: () => null,
          setItem: () => {},
          removeItem: () => {},
        };
      }),
      // Persist currentTeam and cache metadata
      partialize: (state) => ({
        currentTeam: state.currentTeam,
        currentTeamCache: state.currentTeamCache,
        teams: state.teams, // Added for better UX
        teamsCache: state.teamsCache, // Added for better UX
        user_role: state.user_role, // Added missing field
      }),
      version: 2, // Increment version for cache metadata
      // Handle rehydration
      onRehydrateStorage: () => (state, error) => {
        if (error) {
          console.error('TeamStore: Storage rehydration failed', error);
          return;
        }

        if (process.env.NODE_ENV === 'development') {
          console.log('TeamStore: Storage rehydration completed', {
            hasState: !!state,
            hasCurrentTeam: state?.currentTeam ? 'Yes' : 'No',
            cacheValid: state?.currentTeamCache ? isCacheValid(state.currentTeamCache) : false,
          });
        }
        
        if (!state) return;
        
        // Invalidate cache if expired after rehydration
        if (state.currentTeamCache && !isCacheValid(state.currentTeamCache)) {
          if (process.env.NODE_ENV === 'development') {
            console.log('TeamStore: Current team cache expired after rehydration, invalidating');
          }
          state.currentTeamCache = null;
        }
        
        if (state.teamsCache && !isCacheValid(state.teamsCache)) {
          if (process.env.NODE_ENV === 'development') {
            console.log('TeamStore: Teams cache expired after rehydration, invalidating');
          }
          state.teamsCache = null;
        }
        
        if (state.metricsCache && !isCacheValid(state.metricsCache)) {
          if (process.env.NODE_ENV === 'development') {
            console.log('TeamStore: Metrics cache expired after rehydration, invalidating');
          }
          state.metricsCache = null;
        }
      },
    }
  )
);

// Optimized selector hooks with stable references
export const useCurrentTeam = () =>
  useTeamStore((state) => state.currentTeam);

export const useTeams = () =>
  useTeamStore((state) => state.teams);

export const useTeamMetrics = () =>
  useTeamStore((state) => state.teamMetrics);

export const useTeamLoading = () =>
  useTeamStore((state) => state.isLoading);

export const useTeamError = () =>
  useTeamStore((state) => state.error);

export const useUserRole = () =>
  useTeamStore((state) => state.user_role);

// Action hooks
export const useSetCurrentTeam = () =>
  useTeamStore((state) => state.setCurrentTeam);

export const useSetTeams = () =>
  useTeamStore((state) => state.setTeams);

export const useSetTeamMetrics = () =>
  useTeamStore((state) => state.setTeamMetrics);

export const useSetUserRole = () =>
  useTeamStore((state) => state.setUserRole);

export const useClearTeam = () =>
  useTeamStore((state) => state.clearTeam);

export const useSetTeamLoading = () =>
  useTeamStore((state) => state.setIsLoading);

export const useSetTeamError = () =>
  useTeamStore((state) => state.setError);

export const useFetchTeamDetails = () =>
  useTeamStore((state) => state.fetchTeamDetails);

// Computed selectors with memoization considerations
export const useCurrentTeamId = () => {
  const currentTeam = useTeamStore((state) => state.currentTeam);
  return currentTeam?.id || null;
};

export const useCurrentTeamName = () => {
  const currentTeam = useTeamStore((state) => state.currentTeam);
  return currentTeam?.name || null;
};

export const useCurrentTeamOrganizationId = () => {
  const currentTeam = useTeamStore((state) => state.currentTeam);
  return currentTeam?.organization_id || null;
};

export const useCurrentTeamLeaderId = () => {
  const currentTeam = useTeamStore((state) => state.currentTeam);
  return currentTeam?.team_leader_id || null;
};

export const useCurrentTeamStatus = () => {
  const currentTeam = useTeamStore((state) => state.currentTeam);
  return currentTeam?.status || null;
};

export const useIsTeamActive = () => {
  const currentTeam = useTeamStore((state) => state.currentTeam);
  return currentTeam?.status === 'active';
};

export const useIsTeamSuspended = () => {
  const currentTeam = useTeamStore((state) => state.currentTeam);
  return currentTeam?.status === 'suspended';
};

export const useIsTeamFrozen = () => {
  const currentTeam = useTeamStore((state) => state.currentTeam);
  return currentTeam?.status === 'frozen';
};

export const useTeamCreditPool = () => {
  const currentTeam = useTeamStore((state) => state.currentTeam);
  if (!currentTeam) return null;
  
  return {
    total: currentTeam.credit_pool_total,
    used: currentTeam.credit_pool_used,
    remaining: currentTeam.credit_pool_remaining,
    resetDate: currentTeam.pool_reset_date,
  };
};

export const useTeamCreditUsagePercentage = () => {
  const currentTeam = useTeamStore((state) => state.currentTeam);
  if (!currentTeam || currentTeam.credit_pool_total === 0) return 0;
  
  return (currentTeam.credit_pool_used / currentTeam.credit_pool_total) * 100;
};

export const useIsTeamCreditLow = (threshold: number = 20) => {
  const percentage = useTeamCreditUsagePercentage();
  const currentTeam = useTeamStore((state) => state.currentTeam);
  if (!currentTeam) return false;
  
  const remainingPercentage = 100 - percentage;
  return remainingPercentage < threshold;
};

export const useTeamMemberCount = () => {
  const currentTeam = useTeamStore((state) => state.currentTeam);
  return currentTeam?.member_count || 0;
};

export const useTeamInvitationSummary = () => {
  const metrics = useTeamStore((state) => state.teamMetrics);
  return metrics?.invitations || null;
};

export const useTeamMembershipSummary = () => {
  const metrics = useTeamStore((state) => state.teamMetrics);
  return metrics?.membership || null;
};

// Utility function to check if team has sufficient credits
export const useTeamHasSufficientCredits = (requiredCredits: number) => {
  const currentTeam = useTeamStore((state) => state.currentTeam);
  if (!currentTeam) return false;
  return currentTeam.credit_pool_remaining >= requiredCredits;
};

// For backward compatibility - combined actions hook
export const useTeamActions = () => {
  const setCurrentTeam = useTeamStore((state) => state.setCurrentTeam);
  const setTeams = useTeamStore((state) => state.setTeams);
  const setTeamMetrics = useTeamStore((state) => state.setTeamMetrics);
  const setUserRole = useTeamStore((state) => state.setUserRole);
  const clearTeam = useTeamStore((state) => state.clearTeam);
  const setIsLoading = useTeamStore((state) => state.setIsLoading);
  const setError = useTeamStore((state) => state.setError);
  const fetchTeamDetails = useTeamStore((state) => state.fetchTeamDetails);

  return {
    setCurrentTeam,
    setTeams,
    setTeamMetrics,
    setUserRole,
    clearTeam,
    setIsLoading,
    setError,
    fetchTeamDetails,
  };
};

// Cache management hooks
export const useInvalidateCurrentTeamCache = () =>
  useTeamStore((state) => state.invalidateCurrentTeamCache);

export const useInvalidateTeamsCache = () =>
  useTeamStore((state) => state.invalidateTeamsCache);

export const useInvalidateMetricsCache = () =>
  useTeamStore((state) => state.invalidateMetricsCache);

export const useInvalidateAllCaches = () =>
  useTeamStore((state) => state.invalidateAllCaches);

export const useIsCurrentTeamCacheValid = () =>
  useTeamStore((state) => state.isCurrentTeamCacheValid);

export const useIsTeamsCacheValid = () =>
  useTeamStore((state) => state.isTeamsCacheValid);

export const useIsMetricsCacheValid = () =>
  useTeamStore((state) => state.isMetricsCacheValid);

export const useShouldRevalidateCurrentTeam = () =>
  useTeamStore((state) => state.shouldRevalidateCurrentTeam);

export const useShouldRevalidateTeams = () =>
  useTeamStore((state) => state.shouldRevalidateTeams);

export const useShouldRevalidateMetrics = () =>
  useTeamStore((state) => state.shouldRevalidateMetrics);

// Combined cache management hook
export const useTeamCacheManagement = () => {
  const invalidateCurrentTeamCache = useTeamStore((state) => state.invalidateCurrentTeamCache);
  const invalidateTeamsCache = useTeamStore((state) => state.invalidateTeamsCache);
  const invalidateMetricsCache = useTeamStore((state) => state.invalidateMetricsCache);
  const invalidateAllCaches = useTeamStore((state) => state.invalidateAllCaches);
  const isCurrentTeamCacheValid = useTeamStore((state) => state.isCurrentTeamCacheValid);
  const isTeamsCacheValid = useTeamStore((state) => state.isTeamsCacheValid);
  const isMetricsCacheValid = useTeamStore((state) => state.isMetricsCacheValid);
  const shouldRevalidateCurrentTeam = useTeamStore((state) => state.shouldRevalidateCurrentTeam);
  const shouldRevalidateTeams = useTeamStore((state) => state.shouldRevalidateTeams);
  const shouldRevalidateMetrics = useTeamStore((state) => state.shouldRevalidateMetrics);

  return {
    invalidateCurrentTeamCache,
    invalidateTeamsCache,
    invalidateMetricsCache,
    invalidateAllCaches,
    isCurrentTeamCacheValid,
    isTeamsCacheValid,
    isMetricsCacheValid,
    shouldRevalidateCurrentTeam,
    shouldRevalidateTeams,
    shouldRevalidateMetrics,
  };
};

// Performance optimization: Export a hook that selects multiple related values
export const useTeamCoreData = () => {
  return useTeamStore((state) => ({
    currentTeam: state.currentTeam,
    teams: state.teams,
    teamMetrics: state.teamMetrics,
    isLoading: state.isLoading,
    error: state.error,
    user_role: state.user_role,
  }));
};