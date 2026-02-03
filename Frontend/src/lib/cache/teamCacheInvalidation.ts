import { useTeamStore } from '@/stores/teamStore';

/**
 * Cache invalidation utilities for team-related mutations
 * 
 * These functions should be called after successful mutations to ensure
 * the cache is properly invalidated and fresh data is fetched.
 */

/**
 * Invalidate cache after team creation
 */
export const invalidateAfterTeamCreation = () => {
  const store = useTeamStore.getState();
  store.invalidateTeamsCache();
  store.invalidateCurrentTeamCache();
  console.log('Cache invalidated: Team creation');
};

/**
 * Invalidate cache after team update
 */
export const invalidateAfterTeamUpdate = () => {
  const store = useTeamStore.getState();
  store.invalidateCurrentTeamCache();
  store.invalidateTeamsCache();
  console.log('Cache invalidated: Team update');
};

/**
 * Invalidate cache after team deletion
 */
export const invalidateAfterTeamDeletion = () => {
  const store = useTeamStore.getState();
  store.invalidateTeamsCache();
  store.invalidateCurrentTeamCache();
  store.invalidateMetricsCache();
  console.log('Cache invalidated: Team deletion');
};

/**
 * Invalidate cache after member invitation
 */
export const invalidateAfterMemberInvitation = () => {
  const store = useTeamStore.getState();
  store.invalidateMetricsCache();
  store.invalidateCurrentTeamCache(); // Member count may change
  console.log('Cache invalidated: Member invitation');
};

/**
 * Invalidate cache after member joins team
 */
export const invalidateAfterMemberJoin = () => {
  const store = useTeamStore.getState();
  store.invalidateCurrentTeamCache();
  store.invalidateMetricsCache();
  console.log('Cache invalidated: Member join');
};

/**
 * Invalidate cache after member removal
 */
export const invalidateAfterMemberRemoval = () => {
  const store = useTeamStore.getState();
  store.invalidateCurrentTeamCache();
  store.invalidateMetricsCache();
  console.log('Cache invalidated: Member removal');
};

/**
 * Invalidate cache after member suspension
 */
export const invalidateAfterMemberSuspension = () => {
  const store = useTeamStore.getState();
  store.invalidateCurrentTeamCache();
  store.invalidateMetricsCache();
  console.log('Cache invalidated: Member suspension');
};

/**
 * Invalidate cache after credit request
 */
export const invalidateAfterCreditRequest = () => {
  const store = useTeamStore.getState();
  store.invalidateMetricsCache();
  console.log('Cache invalidated: Credit request');
};

/**
 * Invalidate cache after credit allocation
 */
export const invalidateAfterCreditAllocation = () => {
  const store = useTeamStore.getState();
  store.invalidateCurrentTeamCache();
  store.invalidateMetricsCache();
  console.log('Cache invalidated: Credit allocation');
};

/**
 * Invalidate cache after credit usage
 */
export const invalidateAfterCreditUsage = () => {
  const store = useTeamStore.getState();
  store.invalidateCurrentTeamCache();
  store.invalidateMetricsCache();
  console.log('Cache invalidated: Credit usage');
};

/**
 * Invalidate all team-related caches
 * Use this for operations that affect multiple aspects of team data
 */
export const invalidateAllTeamCaches = () => {
  const store = useTeamStore.getState();
  store.invalidateAllCaches();
  console.log('Cache invalidated: All team caches');
};

/**
 * Hook for cache invalidation in React components
 */
export const useTeamCacheInvalidation = () => {
  return {
    invalidateAfterTeamCreation,
    invalidateAfterTeamUpdate,
    invalidateAfterTeamDeletion,
    invalidateAfterMemberInvitation,
    invalidateAfterMemberJoin,
    invalidateAfterMemberRemoval,
    invalidateAfterMemberSuspension,
    invalidateAfterCreditRequest,
    invalidateAfterCreditAllocation,
    invalidateAfterCreditUsage,
    invalidateAllTeamCaches,
  };
};
