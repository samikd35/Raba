import { User, LoginCredentials, RegisterCredentials, OrganizationLoginResponse } from '@/types/auth';
import { useAuthStore, UserRole } from '@/stores/authStore';
import { clearAllProjectsCaches } from '@/components/DashboardProjects/cacheUtils';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL;


// Auth service class
export class AuthService {
  private static instance: AuthService;

  public static getInstance(): AuthService {
    if (!AuthService.instance) {
      AuthService.instance = new AuthService();
    }
    return AuthService.instance;
  }

  // Initialize authentication from stored state
  async initialize(): Promise<void> {
    const {
      token,
      initializeAuth,
      setIsLoading
    } = useAuthStore.getState();

    setIsLoading(true);

    try {
      if (!token) {
        console.log('Auth: No token found during initialization');
        initializeAuth();
        return;
      }

      // Validate token and get fresh user data
      try {
        const userData = await this.getCurrentUser(token);
        useAuthStore.getState().setUser(userData);
        console.log('Auth: Initialized successfully with valid token');
      } catch (error: any) {
        console.error('Auth: Token validation failed during initialization:', error);
        if (error.message === 'SESSION_EXPIRED' || error.message?.includes('401')) {
          await this.logout();
        } else {
          // For other errors, keep the user logged in but show stale data
          console.warn('Auth: Could not fetch fresh user data, using stored data');
        }
      }

    } catch (error) {
      console.error('Auth: Initialization error:', error);
      await this.logout();
    } finally {
      useAuthStore.getState().setIsLoading(false);
    }
  }

  // Login user
  async login(credentials: LoginCredentials): Promise<User> {
    const { setIsLoading, login: storeLogin } = useAuthStore.getState();

    try {
      setIsLoading(true);

      const response = await fetch(`${API_BASE_URL}/api/v2/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify(credentials),
      });

      if (!response.ok) {
        let errorMessage = 'Login failed';

        try {
          const errorData = await response.json();
          if (response.status === 401) {
            errorMessage = errorData.detail?.message || errorData.message || 'Invalid email or password.';
          } else if (response.status === 422) {
            errorMessage = errorData.detail?.[0]?.msg || errorData.message || 'Validation error';
          } else if (response.status === 429) {
            errorMessage = errorData.message || 'Too many requests. Please try again later';
          } else {
            errorMessage = errorData.message || `Server error: ${response.status}`;
          }
        } catch {
          errorMessage = `Server error: ${response.status}`;
        }

        throw new Error(errorMessage);
      }

      const data = await response.json();
      const { access_token, user: userData } = data;

      if (!access_token) {
        throw new Error('No access token received from server');
      }

      if (!userData) {
        throw new Error('No user data received from server');
      }

      // Ensure user data has required fields with proper role handling
      const completeUserData: User = {
        id: userData.id || '',
        email: userData.email || '',
        full_name: userData.full_name || '',
        avatar_url: userData.avatar_url || null,
        timezone: userData.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone,
        preferences: userData.preferences || {},
        bio: userData.bio || '',
        website: userData.website || '',
        location: userData.location || '',
        roles: Array.isArray(userData.roles) ? userData.roles : [userData.roles].filter(Boolean),
        tenant_id: userData.tenant_id || '',
        tenant_type: userData.tenant_type || '',
        can_skip_module: userData.can_skip_module ?? null
      };

      // Debug: Log can_skip_module value
      console.log('🔐 [Auth] Login - can_skip_module:', {
        rawValue: userData.can_skip_module,
        storedValue: completeUserData.can_skip_module,
        type: typeof userData.can_skip_module
      });

      // Update store using the store's login method
      storeLogin(completeUserData, access_token);

      return completeUserData;

    } catch (error: any) {
      console.error('Login error:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }

  // Google OAuth login
  async loginWithGoogle(idToken: string): Promise<User> {
    const { setIsLoading, login: storeLogin } = useAuthStore.getState();

    console.log('Google Sign-In Token:', idToken);

    try {
      setIsLoading(true);

      const response = await fetch(`${API_BASE_URL}/api/v2/auth/google-signin`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify({ id_token: idToken }),
      });

      if (!response.ok) {
        let errorMessage = 'Google sign-in failed';

        try {
          const errorData = await response.json();
          console.error('❌ Google Sign-In Backend Error:', JSON.stringify({
            status: response.status,
            data: errorData
          }, null, 2));

          if (response.status === 401) {
            errorMessage = 'Invalid Google ID token. Please try signing in again.';
          } else if (response.status === 422) {
            if (errorData.detail && typeof errorData.detail === 'string') {
              errorMessage = errorData.detail;
            } else if (errorData.detail && Array.isArray(errorData.detail)) {
              const validationErrors = errorData.detail.map((err: any) => err.msg || err.message).join(', ');
              errorMessage = `Validation error: ${validationErrors}`;
            } else if (errorData.message) {
              errorMessage = errorData.message;
            } else {
              errorMessage = 'Invalid request format. Please try again.';
            }
          } else if (response.status === 500) {
            errorMessage = errorData.message || 'Google sign-in failed. Please try again later.';
          } else if (response.status === 429) {
            errorMessage = 'Too many requests. Please try again later';
          } else {
            errorMessage = errorData.message || `Server error: ${response.status}`;
          }
        } catch (parseError) {
          if (response.status === 401) {
            errorMessage = 'Invalid Google ID token. Please try signing in again.';
          } else if (response.status === 422) {
            errorMessage = 'Invalid request format. Please check your Google sign-in configuration.';
          } else if (response.status === 500) {
            errorMessage = 'Google sign-in failed. Please try again later.';
          } else {
            errorMessage = `Server error: ${response.status}`;
          }
        }

        throw new Error(errorMessage);
      }

      const data = await response.json();
      const { access_token, user: userData } = data;

      if (!access_token) {
        throw new Error('No access token received from server');
      }

      if (!userData) {
        throw new Error('No user data received from server');
      }

      // Map backend response to frontend User interface with proper role handling
      const completeUserData: User = {
        id: userData.id,
        email: userData.email,
        full_name: userData.full_name,
        avatar_url: userData.avatar_url || null,
        timezone: userData.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone,
        preferences: userData.preferences || {},
        bio: userData.bio || '',
        website: userData.website || '',
        location: userData.location || '',
        roles: Array.isArray(userData.roles) ? userData.roles : [userData.roles].filter(Boolean),
        tenant_id: userData.tenant_id || '',
        tenant_type: userData.tenant_type || '',
        can_skip_module: userData.can_skip_module ?? null
      };

      // Debug: Log can_skip_module value
      console.log('🔐 [Auth] Google Login - can_skip_module:', {
        rawValue: userData.can_skip_module,
        storedValue: completeUserData.can_skip_module,
        type: typeof userData.can_skip_module
      });

      // Store token and user data
      storeLogin(completeUserData, access_token);

      return completeUserData;
    } finally {
      setIsLoading(false);
    }
  }

  // Get current user data
  async getCurrentUser(token: string): Promise<User> {
    const response = await fetch(`${API_BASE_URL}/api/v2/auth/me`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Accept': 'application/json',
      },
    });

    if (!response.ok) {
      if (response.status === 401) {
        console.warn('AuthService: Session expired during getCurrentUser');
        throw new Error('SESSION_EXPIRED');
      }
      throw new Error(`Failed to fetch user data: ${response.status}`);
    }

    const userData = await response.json();

    // Debug: Log can_skip_module value
    console.log('🔐 [Auth] getCurrentUser - can_skip_module:', {
      rawValue: userData.can_skip_module,
      storedValue: userData.can_skip_module ?? null,
      type: typeof userData.can_skip_module
    });

    // Ensure all required fields are present with proper role handling
    return {
      id: userData.id || '',
      email: userData.email || '',
      full_name: userData.full_name || '',
      avatar_url: userData.avatar_url || null,
      timezone: userData.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone,
      preferences: userData.preferences || {},
      bio: userData.bio || '',
      website: userData.website || '',
      location: userData.location || '',
      roles: Array.isArray(userData.roles) ? userData.roles : [userData.roles].filter(Boolean),
      tenant_id: userData.tenant_id || '',
      tenant_type: userData.tenant_type || '',
      can_skip_module: userData.can_skip_module ?? null
    };
  }

  // Logout user
  async logout(): Promise<void> {
    const { token, logout: storeLogout } = useAuthStore.getState();

    try {
      // Call logout endpoint if we have a token
      if (token) {
        await fetch(`${API_BASE_URL}/api/v2/auth/logout`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        }).catch(error => {
          console.warn('Logout API call failed, but continuing with local logout:', error);
        });
      }
    } finally {
      // Clear all cached data to prevent cross-tenant data leakage
      clearAllProjectsCaches();
      // Always perform local logout
      storeLogout();
    }
  }

  // Update user profile
  async updateProfile(userId: string, updates: Partial<User>): Promise<User> {
    const { token, updateUser } = useAuthStore.getState();

    if (!token) {
      throw new Error('No authentication token available');
    }

    const response = await fetch(`${API_BASE_URL}/api/v2/auth/users/${userId}`, {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(updates),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.message || `Failed to update profile: ${response.status}`);
    }

    const updatedUser = await response.json();

    // Update store
    updateUser(updatedUser);

    return updatedUser;
  }

  // Change password
  async changePassword(newPassword: string): Promise<void> {
    const { token, user } = useAuthStore.getState();

    if (!token) {
      throw new Error('No authentication token available');
    }

    if (!user?.id) {
      throw new Error('User ID not available');
    }

    try {
      const response = await fetch(`${API_BASE_URL}/api/v2/auth/users/${user.id}/password`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify({
          new_password: newPassword,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));

        if (process.env.NODE_ENV === 'development') {
          console.error('Change password error:', {
            status: response.status,
            statusText: response.statusText,
            errorData
          });
        }

        // Handle specific error codes from backend
        if (response.status === 403) {
          throw new Error('Not allowed to change password');
        } else if (response.status === 404) {
          throw new Error('User not found');
        } else if (response.status === 500) {
          throw new Error('Failed to update password. Please try again later.');
        }

        throw new Error(errorData.message || errorData.detail || `Failed to change password: ${response.status}`);
      }

      const data = await response.json();

      if (process.env.NODE_ENV === 'development') {
        console.log('Password changed successfully:', data);
      }
    } catch (error) {
      if (process.env.NODE_ENV === 'development') {
        console.error('Change password request failed:', error);
      }
      throw error;
    }
  }

  // Refresh user profile
  async refreshProfile(): Promise<User | null> {
    const { token, setUser } = useAuthStore.getState();

    if (!token) {
      console.warn('No auth token found for profile refresh');
      return null;
    }

    try {
      const userData = await this.getCurrentUser(token);
      setUser(userData);
      return userData;
    } catch (error: any) {
      console.error('Error refreshing user profile:', error);

      // If token is invalid, clear authentication state
      if (error.message === 'SESSION_EXPIRED' || error.message?.includes('401')) {
        await this.logout();
      }
      throw error;
    }
  }

  // Register user
  async register(userData: RegisterCredentials): Promise<{ message: string }> {
    const response = await fetch(`${API_BASE_URL}/api/v2/auth/signup/send-link`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify({ email: userData.email }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.message || `Registration failed: ${response.status}`);
    }

    return await response.json();
  }

  // Verify email
  async verifyEmail(token: string): Promise<{ message: string }> {
    const response = await fetch(`${API_BASE_URL}/api/v2/auth/verify-email`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify({ token }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.message || `Email verification failed: ${response.status}`);
    }

    return await response.json();
  }

  // Request password reset
  async requestPasswordReset(email: string): Promise<{ message: string }> {
    const response = await fetch(`${API_BASE_URL}/api/v2/auth/forgot-password`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify({ email }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.message || `Password reset request failed: ${response.status}`);
    }

    return await response.json();
  }

  // Reset password with token
  async resetPassword(token: string, newPassword: string): Promise<{ message: string }> {
    const response = await fetch(`${API_BASE_URL}/api/v2/auth/reset-password`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify({
        token,
        new_password: newPassword
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.message || `Password reset failed: ${response.status}`);
    }

    return await response.json();
  }

  // Check authentication status
  async checkAuthStatus(): Promise<boolean> {
    const { token, isAuthenticated, validateToken } = useAuthStore.getState();

    if (!token || !isAuthenticated) {
      return false;
    }

    // Check if token is expired using store's validation
    if (!validateToken()) {
      console.log('Auth: Token expired during status check');
      await this.logout();
      return false;
    }

    // Optionally validate with server
    try {
      await this.getCurrentUser(token);
      return true;
    } catch (error) {
      console.error('Auth: Status check failed:', error);
      await this.logout();
      return false;
    }
  }

  // Get authentication headers for API calls
  getAuthHeaders(): Record<string, string> {
    const { token } = useAuthStore.getState();

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    return headers;
  }

  // Enhanced role checking using the store's computed role system
  hasRole(role: UserRole | UserRole[]): boolean {
    return useAuthStore.getState().hasRole(role);
  }

  // Get user ID
  getUserId(): string | null {
    return useAuthStore.getState().getUserId();
  }

  // Get current user
  getCurrentUserFromStore(): User | null {
    return useAuthStore.getState().user;
  }

  // Get current token
  getCurrentToken(): string | null {
    return useAuthStore.getState().token;
  }

  // Check if user is authenticated
  isAuthenticated(): boolean {
    const { isAuthenticated, token, validateToken } = useAuthStore.getState();
    return isAuthenticated && !!token && validateToken();
  }

  // Get computed role
  getComputedRole(): UserRole {
    return useAuthStore.getState().getComputedRole();
  }

  // Role-specific helpers
  isSuperAdmin(): boolean {
    return useAuthStore.getState().isSuperAdmin();
  }

  isAdmin(): boolean {
    return useAuthStore.getState().isAdmin();
  }

  isOrganizationOwner(): boolean {
    return useAuthStore.getState().isOrganizationOwner();
  }

  isOrganizationMember(): boolean {
    return useAuthStore.getState().isOrganizationMember();
  }

  isTeamLeader(): boolean {
    return useAuthStore.getState().isTeamLeader();
  }

  isTeamMember(): boolean {
    return useAuthStore.getState().isTeamMember();
  }

  isRegularUser(): boolean {
    return useAuthStore.getState().isRegularUser();
  }

  // Switch to a specific tenant context
  async switchToTenant(tenantId: string): Promise<User> {
    const { token, login: storeLogin } = useAuthStore.getState();

    if (!token) {
      throw new Error('No authentication token available');
    }

    const response = await fetch(`${API_BASE_URL}/api/v2/auth/login/${tenantId}`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.message || `Failed to switch tenant: ${response.status}`);
    }

    const data = await response.json();
    const { access_token, tenant_id, tenant_type, user_id, email } = data;

    if (!access_token) {
      throw new Error('No access token received from tenant login');
    }

    // Get updated user data with new tenant context
    const userData = await this.getCurrentUser(access_token);

    // Update store with new token and user data
    storeLogin(userData, access_token);

    return userData;
  }

  // Refresh tokens
  async refreshTokens(): Promise<void> {
    const { token, refreshToken, refreshTokens: storeRefreshTokens } = useAuthStore.getState();

    if (!token || !refreshToken) {
      throw new Error('No tokens available for refresh');
    }

    const response = await fetch(`${API_BASE_URL}/api/v2/auth/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify({
        refresh_token: refreshToken,
      }),
    });

    if (!response.ok) {
      throw new Error('Failed to refresh tokens');
    }

    const data = await response.json();
    const { access_token, refresh_token } = data;

    storeRefreshTokens(access_token, refresh_token);
  }

  // Login to organization
  async loginToOrganization(organizationId: string): Promise<OrganizationLoginResponse> {
    const { token } = useAuthStore.getState();

    if (!token) {
      throw new Error('No authentication token available');
    }

    const response = await fetch(`${API_BASE_URL}/api/v2/auth/login/${organizationId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => null);
      throw new Error(errorData?.message || `Login to organization failed: ${response.status}`);
    }

    const data: OrganizationLoginResponse = await response.json();

    // Update the current token with the new organization-scoped token
    this.setToken(data.access_token);

    return data;
  }

  // Set current token
  setToken(token: string): void {
    const currentToken = useAuthStore.getState().token;
    if (currentToken !== token) {
      if (process.env.NODE_ENV === 'development') {
        console.log('🔄 AuthService: Token changed', {
          from: currentToken?.substring(0, 20) + '...',
          to: token?.substring(0, 20) + '...',
          timestamp: new Date().toISOString()
        });
      }
      useAuthStore.getState().setToken(token);
    } else {
      if (process.env.NODE_ENV === 'development') {
        console.log('🔄 AuthService: Token unchanged, skipping update');
      }
    }
  }
}

// Export singleton instance
export const authService = AuthService.getInstance();