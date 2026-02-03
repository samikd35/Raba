import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { User } from '@/types/auth';
import { useMemo } from 'react';
import React from 'react';

interface AuthState {
  user: User | null;
  token: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  isInitialized: boolean;
  lastActivity: number;
}

// Enhanced role types based on your logic
export type UserRole =
  | 'super_admin'
  | 'admin'
  | 'organization_owner'
  | 'organization_member'
  | 'team_leader'
  | 'team_member'
  | 'user';

interface AuthActions {
  // Core state setters
  setUser: (user: User | null) => void;
  setToken: (token: string | null) => void;
  setRefreshToken: (refreshToken: string | null) => void;
  setIsAuthenticated: (isAuthenticated: boolean) => void;
  setIsLoading: (isLoading: boolean) => void;
  setIsInitialized: (isInitialized: boolean) => void;
  setLastActivity: (timestamp: number) => void;

  // User management
  updateUser: (updates: Partial<User>) => void;
  login: (user: User, token: string, refreshToken?: string) => void;
  logout: () => void;
  refreshTokens: (token: string, refreshToken?: string) => void;

  // Auth utilities
  validateToken: () => boolean;
  initializeAuth: () => void;

  // Enhanced role system
  getComputedRole: () => UserRole;
  hasRole: (role: UserRole | UserRole[]) => boolean;
  hasExactRole: (role: UserRole) => boolean;
  getUserId: () => string | null;

  // Role helpers
  isSuperAdmin: () => boolean;
  isAdmin: () => boolean;
  isOrganizationOwner: () => boolean;
  isOrganizationMember: () => boolean;
  isTeamLeader: () => boolean;
  isTeamMember: () => boolean;
  isRegularUser: () => boolean;

  // Module skip helpers
  canSkipModule: () => boolean | null;
  getCanSkipModuleValue: () => boolean | null;
}

type AuthStore = AuthState & AuthActions;

// Token utilities
const isTokenExpired = (token: string | null): boolean => {
  if (!token) return true;

  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    return Date.now() >= payload.exp * 1000 - 60000;
  } catch {
    return true;
  }
};

// Migration function to handle state version changes
const migrateAuthState = (persistedState: any, version: number): AuthState => {
  console.log('AuthStore: Migrating state', { version, persistedState });

  // Version 0 -> 1 migration (initial migration)
  if (version === 0) {
    return {
      user: persistedState.user || null,
      token: persistedState.token || null,
      refreshToken: persistedState.refreshToken || null,
      isAuthenticated: persistedState.isAuthenticated || false,
      isLoading: false, // Reset loading state
      isInitialized: true, // Mark as initialized after migration
      lastActivity: persistedState.lastActivity || Date.now(),
    };
  }

  // For future version migrations, add more cases here
  // if (version === 1) { ... }

  // If no migration needed, return the state as is
  return persistedState;
};

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      // Initial state
      user: null,
      token: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: true,
      isInitialized: false,
      lastActivity: Date.now(),

      // Core state setters
      setUser: (user) => set({ user }),
      setToken: (token) => set({ token }),
      setRefreshToken: (refreshToken) => set({ refreshToken }),
      setIsAuthenticated: (isAuthenticated) => set({ isAuthenticated }),
      setIsLoading: (isLoading) => set({ isLoading }),
      setIsInitialized: (isInitialized) => set({ isInitialized }),
      setLastActivity: (timestamp) => set({ lastActivity: timestamp }),

      // User management
      updateUser: (updates) => {
        const { user } = get();
        if (user) {
          set({ user: { ...user, ...updates } });
        }
      },

      login: (user, token, refreshToken) => {
        set({
          user,
          token,
          refreshToken: refreshToken || null,
          isAuthenticated: true,
          isLoading: false,
          isInitialized: true,
          lastActivity: Date.now(),
        });
      },

      logout: () => {
        set({
          user: null,
          token: null,
          refreshToken: null,
          isAuthenticated: false,
          isLoading: false,
          isInitialized: true,
          lastActivity: Date.now(),
        });
      },

      refreshTokens: (token, refreshToken) => {
        set({
          token,
          refreshToken: refreshToken || get().refreshToken,
          lastActivity: Date.now(),
        });
      },

      validateToken: (): boolean => {
        const { token, isAuthenticated } = get();

        if (!token || !isAuthenticated) {
          return false;
        }

        const isValid = !isTokenExpired(token);

        if (!isValid) {
          get().logout();
        } else {
          set({ lastActivity: Date.now() });
        }

        return isValid;
      },

      initializeAuth: () => {
        const { token } = get();

        if (!token || isTokenExpired(token)) {
          set({
            user: null,
            token: null,
            refreshToken: null,
            isAuthenticated: false,
            isLoading: false,
            isInitialized: true,
          });
        } else {
          set({
            isAuthenticated: true,
            isLoading: false,
            isInitialized: true,
          });
        }
      },

      // Enhanced Role System
      getComputedRole: (): UserRole => {
        const { user } = get();

        if (!user) return 'user';

        const globalRole = user.roles[0];
        const tenantRole = user.roles[1];

        // Admin/Super Admin have highest priority
        if (globalRole === 'super_admin') return 'super_admin';
        if (globalRole === 'admin') return 'admin';

        // For regular users, check tenant context
        if (globalRole === 'user') {
          if (user.tenant_type === 'organization') {
            if (tenantRole === 'owner') return 'organization_owner';
            if (tenantRole === 'user') return 'organization_member';
          }

          if (user.tenant_type === 'team') {
            if (tenantRole === 'owner') return 'team_leader';
            if (tenantRole === 'user') return 'team_member';
          }
        }

        return 'user';
      },

      hasRole: (role: UserRole | UserRole[]): boolean => {
        const computedRole = get().getComputedRole();

        if (Array.isArray(role)) {
          return role.includes(computedRole);
        }

        return computedRole === role;
      },

      hasExactRole: (role: UserRole): boolean => {
        return get().getComputedRole() === role;
      },

      getUserId: (): string | null => {
        const { user } = get();
        return user?.id || null;
      },

      // Role-specific helpers
      isSuperAdmin: (): boolean => get().hasRole('super_admin'),
      isAdmin: (): boolean => get().hasRole(['super_admin', 'admin']),
      isOrganizationOwner: (): boolean => get().hasRole('organization_owner'),
      isOrganizationMember: (): boolean => get().hasRole('organization_member'),
      isTeamLeader: (): boolean => get().hasRole('team_leader'),
      isTeamMember: (): boolean => get().hasRole('team_member'),
      isRegularUser: (): boolean => {
        const role = get().getComputedRole();
        return !['super_admin', 'admin'].includes(role);
      },

      // Module skip helpers
      canSkipModule: (): boolean | null => {
        const { user } = get();
        return user?.can_skip_module ?? null;
      },

      getCanSkipModuleValue: (): boolean | null => {
        const { user } = get();
        return user?.can_skip_module ?? null;
      },
    }),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
        lastActivity: state.lastActivity,
      }),
      // Add migration function to handle version changes
      migrate: migrateAuthState,
      version: 1, // Increment this when you change the state structure
      onRehydrateStorage: () => (state) => {
        console.log('AuthStore: Storage rehydration completed', {
          hasState: !!state,
          hasToken: state?.token ? 'Yes' : 'No',
          isAuthenticated: state?.isAuthenticated,
        });

        if (state) {
          // Set initialized flag after rehydration
          state.isInitialized = true;
          state.isLoading = false;
        }
      },
    }
  )
);

// Activity tracking
export const updateUserActivity = () => {
  useAuthStore.getState().setLastActivity(Date.now());
};

// Simple selectors
export const useUser = () => useAuthStore((state) => state.user);
export const useToken = () => useAuthStore((state) => state.token);
export const useRefreshToken = () => useAuthStore((state) => state.refreshToken);
export const useIsAuthenticated = () => useAuthStore((state) => state.isAuthenticated);
export const useIsLoading = () => useAuthStore((state) => state.isLoading);
export const useIsInitialized = () => useAuthStore((state) => state.isInitialized);
export const useLastActivity = () => useAuthStore((state) => state.lastActivity);

// Module skip hook
export const useCanSkipModule = () => useAuthStore((state) => state.user?.can_skip_module ?? null);

// Role system hooks
export const useComputedRole = () => useAuthStore((state) => state.getComputedRole());
export const useHasRole = () => useAuthStore((state) => state.hasRole);
export const useHasExactRole = () => useAuthStore((state) => state.hasExactRole);

// Fixed action hooks - memoized to prevent infinite re-renders
export const useAuthActions = () => {
  const setUser = useAuthStore((state) => state.setUser);
  const setToken = useAuthStore((state) => state.setToken);
  const setRefreshToken = useAuthStore((state) => state.setRefreshToken);
  const setIsAuthenticated = useAuthStore((state) => state.setIsAuthenticated);
  const setIsLoading = useAuthStore((state) => state.setIsLoading);
  const setIsInitialized = useAuthStore((state) => state.setIsInitialized);
  const setLastActivity = useAuthStore((state) => state.setLastActivity);
  const updateUser = useAuthStore((state) => state.updateUser);
  const login = useAuthStore((state) => state.login);
  const logout = useAuthStore((state) => state.logout);
  const refreshTokens = useAuthStore((state) => state.refreshTokens);
  const validateToken = useAuthStore((state) => state.validateToken);
  const initializeAuth = useAuthStore((state) => state.initializeAuth);
  const hasRole = useAuthStore((state) => state.hasRole);
  const hasExactRole = useAuthStore((state) => state.hasExactRole);
  const getUserId = useAuthStore((state) => state.getUserId);
  const getComputedRole = useAuthStore((state) => state.getComputedRole);
  const isSuperAdmin = useAuthStore((state) => state.isSuperAdmin);
  const isAdmin = useAuthStore((state) => state.isAdmin);
  const isOrganizationOwner = useAuthStore((state) => state.isOrganizationOwner);
  const isOrganizationMember = useAuthStore((state) => state.isOrganizationMember);
  const isTeamLeader = useAuthStore((state) => state.isTeamLeader);
  const isTeamMember = useAuthStore((state) => state.isTeamMember);
  const isRegularUser = useAuthStore((state) => state.isRegularUser);

  return useMemo(() => ({
    setUser,
    setToken,
    setRefreshToken,
    setIsAuthenticated,
    setIsLoading,
    setIsInitialized,
    setLastActivity,
    updateUser,
    login,
    logout,
    refreshTokens,
    validateToken,
    initializeAuth,
    hasRole,
    hasExactRole,
    getUserId,
    getComputedRole,
    isSuperAdmin,
    isAdmin,
    isOrganizationOwner,
    isOrganizationMember,
    isTeamLeader,
    isTeamMember,
    isRegularUser,
  }), [
    setUser, setToken, setRefreshToken, setIsAuthenticated, setIsLoading,
    setIsInitialized, setLastActivity, updateUser, login, logout,
    refreshTokens, validateToken, initializeAuth, hasRole, hasExactRole,
    getUserId, getComputedRole, isSuperAdmin, isAdmin, isOrganizationOwner,
    isOrganizationMember, isTeamLeader, isTeamMember, isRegularUser
  ]);
};

// Individual action hooks for better performance
export const useLogout = () => useAuthStore((state) => state.logout);
export const useLogin = () => useAuthStore((state) => state.login);
export const useUpdateUser = () => useAuthStore((state) => state.updateUser);
export const useInitializeAuth = () => useAuthStore((state) => state.initializeAuth);

// Computed selectors
export const useAuthStatus = () => {
  const isAuthenticated = useIsAuthenticated();
  const isLoading = useIsLoading();
  const isInitialized = useIsInitialized();
  const validateToken = useAuthStore((state) => state.validateToken);
  const token = useToken();

  return useMemo(() => ({
    isAuthenticated: isAuthenticated && (!token || validateToken()),
    isLoading,
    isInitialized,
  }), [isAuthenticated, isLoading, isInitialized, validateToken, token]);
};

export const useUserDisplayName = () => {
  const user = useUser();
  return useMemo(() => {
    if (!user) return 'User';
    return user.full_name || user.email || 'User';
  }, [user]);
};

export const useUserRoles = () => {
  const user = useUser();
  return useMemo(() => user?.roles || [], [user]);
};

// Export token utilities
export { isTokenExpired };