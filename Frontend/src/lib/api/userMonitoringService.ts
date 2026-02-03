import { authService } from '../../services/authService';

/**
 * User Monitoring Service - Super Admin Only
 * 
 * This service handles all user monitoring API calls including:
 * - Fetching user lists
 * - Onboarding conversion metrics
 * - Activation metrics
 * - Retention and user segmentation
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL;

/**
 * Get authentication headers for API requests
 */
const getAuthHeaders = (): HeadersInit => {
  const token = authService.getCurrentToken();
  if (!token) {
    throw new Error('No authentication token available');
  }
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
  };
};

/**
 * Handle API errors with proper error messages
 */
const handleApiError = async (response: Response): Promise<void> => {
  if (!response.ok) {
    let errorMessage = `API Error: ${response.status} ${response.statusText}`;
    try {
      const errorData = await response.json();
      errorMessage = errorData.message || errorData.detail || errorMessage;
    } catch {
      // If JSON parsing fails, use default error message
    }
    throw new Error(errorMessage);
  }
};

/**
 * Log errors only in development environment
 */
const logError = (context: string, error: unknown): void => {
  if (process.env.NODE_ENV === 'development') {
    console.error(`[UserMonitoringService] ${context}:`, error);
  }
};

// ==========================================
// Type Definitions
// ==========================================

export interface UserSummary {
  id: string;
  email: string;
  full_name: string | null;
  role: string;
  location: string | null;
  created_at: string;
}

export interface UserListResponse {
  users: UserSummary[];
  page: number;
  page_size: number;
  total_count: number;
  has_next: boolean;
}

export interface OnboardingMetrics {
  total_signups: number;
  users_with_first_project: number;
  users_with_first_report: number;
  conversion_to_first_project: number;
  conversion_to_first_report: number;
}

export interface ActivationMetrics {
  total_signups: number;
  activated_users: number;
  activation_rate: number;
}

export interface RetentionMetrics {
  power_users: number;
  healthy_users: number;
  churn_risk_users: number;
  total_tracked_users: number;
}

// ==========================================
// User Monitoring API Service
// ==========================================

export class UserMonitoringService {
  /**
   * Fetch paginated list of users (Super Admin only)
   * GET /api/admin/users
   */
  static async fetchUsers(params?: {
    page?: number;
    page_size?: number;
    search?: string;
  }): Promise<UserListResponse> {
    try {
      const queryParams = new URLSearchParams();
      if (params?.page) queryParams.append('page', params.page.toString());
      if (params?.page_size) queryParams.append('page_size', params.page_size.toString());
      if (params?.search) queryParams.append('search', params.search);

      const url = `${API_BASE_URL}/api/admin/users${queryParams.toString() ? `?${queryParams}` : ''}`;
      const response = await fetch(url, {
        method: 'GET',
        headers: getAuthHeaders(),
      });
      
      await handleApiError(response);
      return await response.json();
    } catch (error) {
      logError('fetchUsers', error);
      throw error;
    }
  }

  /**
   * Get onboarding conversion funnel metrics (Super Admin only)
   * GET /api/admin/monitoring/onboarding
   */
  static async getOnboardingMetrics(params?: {
    from_date?: string;
    to_date?: string;
  }): Promise<OnboardingMetrics> {
    try {
      const queryParams = new URLSearchParams();
      if (params?.from_date) queryParams.append('from_date', params.from_date);
      if (params?.to_date) queryParams.append('to_date', params.to_date);

      const url = `${API_BASE_URL}/api/admin/monitoring/onboarding${queryParams.toString() ? `?${queryParams}` : ''}`;
      const response = await fetch(url, {
        method: 'GET',
        headers: getAuthHeaders(),
      });
      
      await handleApiError(response);
      return await response.json();
    } catch (error) {
      logError('getOnboardingMetrics', error);
      throw error;
    }
  }

  /**
   * Get activation (first value moment) metrics (Super Admin only)
   * GET /api/admin/monitoring/activation
   */
  static async getActivationMetrics(params?: {
    from_date?: string;
    to_date?: string;
  }): Promise<ActivationMetrics> {
    try {
      const queryParams = new URLSearchParams();
      if (params?.from_date) queryParams.append('from_date', params.from_date);
      if (params?.to_date) queryParams.append('to_date', params.to_date);

      const url = `${API_BASE_URL}/api/admin/monitoring/activation${queryParams.toString() ? `?${queryParams}` : ''}`;
      const response = await fetch(url, {
        method: 'GET',
        headers: getAuthHeaders(),
      });
      
      await handleApiError(response);
      return await response.json();
    } catch (error) {
      logError('getActivationMetrics', error);
      throw error;
    }
  }

  /**
   * Get retention and user segmentation metrics (Super Admin only)
   * GET /api/admin/monitoring/retention
   */
  static async getRetentionMetrics(params?: {
    window_days?: number;
  }): Promise<RetentionMetrics> {
    try {
      const queryParams = new URLSearchParams();
      if (params?.window_days) queryParams.append('window_days', params.window_days.toString());

      const url = `${API_BASE_URL}/api/admin/monitoring/retention${queryParams.toString() ? `?${queryParams}` : ''}`;
      const response = await fetch(url, {
        method: 'GET',
        headers: getAuthHeaders(),
      });
      
      await handleApiError(response);
      return await response.json();
    } catch (error) {
      logError('getRetentionMetrics', error);
      throw error;
    }
  }
}

// Export singleton instance
export const userMonitoringService = UserMonitoringService;
