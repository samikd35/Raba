import { create } from 'zustand';
import { CreditRequest } from '@/types/team';

// Credit Request State Interface
interface CreditRequestState {
  requests: CreditRequest[];
  pendingCount: number;
  isLoading: boolean;
  error: string | null;
}

// Credit Request Actions Interface
interface CreditRequestActions {
  setRequests: (requests: CreditRequest[]) => void;
  addRequest: (request: CreditRequest) => void;
  updateRequest: (requestId: string, updates: Partial<CreditRequest>) => void;
  removeRequest: (requestId: string) => void;
  setIsLoading: (isLoading: boolean) => void;
  setError: (error: string | null) => void;
  clearRequests: () => void;
}

// Combined Store Type
type CreditRequestStore = CreditRequestState & CreditRequestActions;

// Helper function to calculate pending count
const calculatePendingCount = (requests: CreditRequest[]): number => {
  return requests.filter((request) => request.status === 'pending').length;
};

// Create the Zustand store
export const useCreditRequestStore = create<CreditRequestStore>((set) => ({
  // Initial state
  requests: [],
  pendingCount: 0,
  isLoading: false,
  error: null,

  // Actions
  setRequests: (requests) => {
    console.log('CreditRequestStore: Setting requests', {
      count: requests.length,
      pendingCount: calculatePendingCount(requests),
    });
    set({
      requests,
      pendingCount: calculatePendingCount(requests),
      error: null,
    });
  },

  addRequest: (request) => {
    console.log('CreditRequestStore: Adding request', {
      requestId: request.request_id,
      status: request.status,
    });
    set((state) => {
      const newRequests = [...state.requests, request];
      return {
        requests: newRequests,
        pendingCount: calculatePendingCount(newRequests),
        error: null,
      };
    });
  },

  updateRequest: (requestId, updates) => {
    console.log('CreditRequestStore: Updating request', {
      requestId,
      updates,
    });
    set((state) => {
      const newRequests = state.requests.map((request) =>
        request.request_id === requestId
          ? { ...request, ...updates }
          : request
      );
      return {
        requests: newRequests,
        pendingCount: calculatePendingCount(newRequests),
        error: null,
      };
    });
  },

  removeRequest: (requestId) => {
    console.log('CreditRequestStore: Removing request', {
      requestId,
    });
    set((state) => {
      const newRequests = state.requests.filter(
        (request) => request.request_id !== requestId
      );
      return {
        requests: newRequests,
        pendingCount: calculatePendingCount(newRequests),
        error: null,
      };
    });
  },

  setIsLoading: (isLoading) => {
    set({ isLoading });
  },

  setError: (error) => {
    console.error('CreditRequestStore: Error set', error);
    set({ error, isLoading: false });
  },

  clearRequests: () => {
    console.log('CreditRequestStore: Clearing all requests');
    set({
      requests: [],
      pendingCount: 0,
      isLoading: false,
      error: null,
    });
  },
}));

// Selector hooks for better performance and convenience
export const useCreditRequests = () =>
  useCreditRequestStore((state) => state.requests);

export const usePendingCreditRequestCount = () =>
  useCreditRequestStore((state) => state.pendingCount);

export const useCreditRequestLoading = () =>
  useCreditRequestStore((state) => state.isLoading);

export const useCreditRequestError = () =>
  useCreditRequestStore((state) => state.error);

// Action hooks
export const useSetCreditRequests = () =>
  useCreditRequestStore((state) => state.setRequests);

export const useAddCreditRequest = () =>
  useCreditRequestStore((state) => state.addRequest);

export const useUpdateCreditRequest = () =>
  useCreditRequestStore((state) => state.updateRequest);

export const useRemoveCreditRequest = () =>
  useCreditRequestStore((state) => state.removeRequest);

export const useSetCreditRequestLoading = () =>
  useCreditRequestStore((state) => state.setIsLoading);

export const useSetCreditRequestError = () =>
  useCreditRequestStore((state) => state.setError);

export const useClearCreditRequests = () =>
  useCreditRequestStore((state) => state.clearRequests);

// Computed selectors
export const usePendingCreditRequests = () => {
  const requests = useCreditRequestStore((state) => state.requests);
  return requests.filter((request) => request.status === 'pending');
};

export const useApprovedCreditRequests = () => {
  const requests = useCreditRequestStore((state) => state.requests);
  return requests.filter((request) => request.status === 'approved');
};

export const useRejectedCreditRequests = () => {
  const requests = useCreditRequestStore((state) => state.requests);
  return requests.filter((request) => request.status === 'rejected');
};

export const useCancelledCreditRequests = () => {
  const requests = useCreditRequestStore((state) => state.requests);
  return requests.filter((request) => request.status === 'cancelled');
};

// Filter requests by team
export const useCreditRequestsByTeam = (teamId: string) => {
  const requests = useCreditRequestStore((state) => state.requests);
  return requests.filter((request) => request.team_id === teamId);
};

// Get a specific request by ID
export const useCreditRequestById = (requestId: string) => {
  const requests = useCreditRequestStore((state) => state.requests);
  return requests.find((request) => request.request_id === requestId) || null;
};

// Check if there are any pending requests
export const useHasPendingRequests = () => {
  const pendingCount = useCreditRequestStore((state) => state.pendingCount);
  return pendingCount > 0;
};

// For backward compatibility - combined actions hook
export const useCreditRequestActions = () => {
  const setRequests = useCreditRequestStore((state) => state.setRequests);
  const addRequest = useCreditRequestStore((state) => state.addRequest);
  const updateRequest = useCreditRequestStore((state) => state.updateRequest);
  const removeRequest = useCreditRequestStore((state) => state.removeRequest);
  const setIsLoading = useCreditRequestStore((state) => state.setIsLoading);
  const setError = useCreditRequestStore((state) => state.setError);
  const clearRequests = useCreditRequestStore((state) => state.clearRequests);

  return {
    setRequests,
    addRequest,
    updateRequest,
    removeRequest,
    setIsLoading,
    setError,
    clearRequests,
  };
};
