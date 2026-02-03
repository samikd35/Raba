import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { Organization } from '@/types/organization';

// Organization Metrics Interface
export interface OrganizationMetrics {
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

// Organization State Interface
interface OrganizationState {
  currentOrganization: Organization | null;
  organizations: Organization[];
  metrics: OrganizationMetrics | null;
  isLoading: boolean;
  error: string | null;
}

// Organization Actions Interface
interface OrganizationActions {
  setCurrentOrganization: (organization: Organization | null) => void;
  setOrganizations: (organizations: Organization[]) => void;
  setMetrics: (metrics: OrganizationMetrics | null) => void;
  clearOrganization: () => void;
  setIsLoading: (isLoading: boolean) => void;
  setError: (error: string | null) => void;
}

// Combined Store Type
type OrganizationStore = OrganizationState & OrganizationActions;

// Create the Zustand store with persist middleware
export const useOrganizationStore = create<OrganizationStore>()(
  persist(
    (set) => ({
      // Initial state
      currentOrganization: null,
      organizations: [],
      metrics: null,
      isLoading: false,
      error: null,

      // Actions
      setCurrentOrganization: (organization) => {
        console.log('OrganizationStore: Setting current organization', {
          hasOrganization: !!organization,
          organizationId: organization?.id,
        });
        set({ currentOrganization: organization, error: null });
      },

      setOrganizations: (organizations) => {
        console.log('OrganizationStore: Setting organizations', {
          count: organizations.length,
        });
        set({ organizations, error: null });
      },

      setMetrics: (metrics) => {
        console.log('OrganizationStore: Setting metrics', {
          hasMetrics: !!metrics,
        });
        set({ metrics, error: null });
      },

      clearOrganization: () => {
        console.log('OrganizationStore: Clearing organization data');
        set({
          currentOrganization: null,
          organizations: [],
          metrics: null,
          isLoading: false,
          error: null,
        });
      },

      setIsLoading: (isLoading) => {
        set({ isLoading });
      },

      setError: (error) => {
        console.error('OrganizationStore: Error set', error);
        set({ error, isLoading: false });
      },
    }),
    {
      name: 'organization-storage',
      storage: createJSONStorage(() => localStorage),
      // Only persist currentOrganization to avoid stale data
      partialize: (state) => ({
        currentOrganization: state.currentOrganization,
      }),
      version: 1,
      // Handle rehydration
      onRehydrateStorage: () => (state) => {
        console.log('OrganizationStore: Storage rehydration completed', {
          hasState: !!state,
          hasCurrentOrganization: state?.currentOrganization ? 'Yes' : 'No',
        });
      },
    }
  )
);

// Selector hooks for better performance and convenience
export const useCurrentOrganization = () =>
  useOrganizationStore((state) => state.currentOrganization);

export const useOrganizations = () =>
  useOrganizationStore((state) => state.organizations);

export const useOrganizationMetrics = () =>
  useOrganizationStore((state) => state.metrics);

export const useOrganizationLoading = () =>
  useOrganizationStore((state) => state.isLoading);

export const useOrganizationError = () =>
  useOrganizationStore((state) => state.error);

// Action hooks
export const useSetCurrentOrganization = () =>
  useOrganizationStore((state) => state.setCurrentOrganization);

export const useSetOrganizations = () =>
  useOrganizationStore((state) => state.setOrganizations);

export const useSetOrganizationMetrics = () =>
  useOrganizationStore((state) => state.setMetrics);

export const useClearOrganization = () =>
  useOrganizationStore((state) => state.clearOrganization);

export const useSetOrganizationLoading = () =>
  useOrganizationStore((state) => state.setIsLoading);

export const useSetOrganizationError = () =>
  useOrganizationStore((state) => state.setError);

// Computed selectors
export const useCurrentOrganizationId = () => {
  const currentOrganization = useOrganizationStore(
    (state) => state.currentOrganization
  );
  return currentOrganization?.id || null;
};

export const useCurrentOrganizationType = () => {
  const currentOrganization = useOrganizationStore(
    (state) => state.currentOrganization
  );
  return currentOrganization?.type || null;
};

export const useIsGrantOrganization = () => {
  const currentOrganization = useOrganizationStore(
    (state) => state.currentOrganization
  );
  return currentOrganization?.type === 'grant_org';
};

export const useIsPrepayOrganization = () => {
  const currentOrganization = useOrganizationStore(
    (state) => state.currentOrganization
  );
  return currentOrganization?.type === 'prepay_org';
};

export const useOrganizationCreditSummary = () => {
  const metrics = useOrganizationStore((state) => state.metrics);
  return metrics?.credits || null;
};

export const useOrganizationMembershipSummary = () => {
  const metrics = useOrganizationStore((state) => state.metrics);
  return metrics?.membership || null;
};

export const useOrganizationInvitationSummary = () => {
  const metrics = useOrganizationStore((state) => state.metrics);
  return metrics?.invitations || null;
};

// Utility function to check if organization has sufficient credits
export const useHasSufficientCredits = (requiredCredits: number) => {
  const metrics = useOrganizationStore((state) => state.metrics);
  if (!metrics?.credits) return false;
  return metrics.credits.remaining >= requiredCredits;
};

// For backward compatibility - combined actions hook
export const useOrganizationActions = () => {
  const setCurrentOrganization = useOrganizationStore(
    (state) => state.setCurrentOrganization
  );
  const setOrganizations = useOrganizationStore(
    (state) => state.setOrganizations
  );
  const setMetrics = useOrganizationStore((state) => state.setMetrics);
  const clearOrganization = useOrganizationStore(
    (state) => state.clearOrganization
  );
  const setIsLoading = useOrganizationStore((state) => state.setIsLoading);
  const setError = useOrganizationStore((state) => state.setError);

  return {
    setCurrentOrganization,
    setOrganizations,
    setMetrics,
    clearOrganization,
    setIsLoading,
    setError,
  };
};
