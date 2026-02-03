import { authService } from '../../services/authService';

/**
 * Token Monitoring Service - Super Admin Only
 * 
 * This service handles all AI token monitoring API calls including:
 * - System-wide usage metrics
 * - Tenant rankings and details
 * - Feature and model analytics
 * - AI model pricing management (CRUD)
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
    console.error(`[TokenMonitoringService] ${context}:`, error);
  }
};

// ==========================================
// Type Definitions
// ==========================================

export interface DailyUsageMetrics {
  date: string;
  calls_count: number;
  sum_prompt_tokens: number;
  sum_completion_tokens: number;
  sum_total_tokens: number;
  sum_input_cost: string;
  sum_output_cost: string;
  sum_total_cost: string;
  avg_latency_ms: number;
  error_count: number;
}

export interface SystemMetrics {
  total_calls: number;
  total_tokens: number;
  total_cost: string;
  distinct_tenants: number;
  distinct_users: number;
  distinct_models: number;
  daily_breakdown: DailyUsageMetrics[];
}

export interface TenantUsageMetrics {
  tenant_id: string;
  tenant_name: string;
  tenant_type: 'individual' | 'team' | 'organization' | 'unknown';
  organization_id: string | null;
  rollup_tenant_ids: string[];
  total_calls: number;
  total_tokens: number;
  total_cost: string;
  daily_breakdown: DailyUsageMetrics[];
}

export interface TenantDetailedUsage {
  tenant_info: {
    tenant_id: string;
    tenant_name: string;
    tenant_type: 'individual' | 'team' | 'organization' | 'unknown';
    organization_id: string | null;
    rollup_tenant_ids: string[];
  };
  usage_summary: {
    total_calls: number;
    total_tokens: number;
    total_cost: number;
    avg_latency_ms: number;
    error_count: number;
  };
  children_breakdown: Array<{
    tenant_id: string;
    tenant_name: string;
    tenant_type: string;
    total_calls: number;
    total_tokens: number;
    total_cost: number;
  }>;
  feature_breakdown: Array<{
    feature_id: string;
    total_calls: number;
    total_tokens: number;
    total_cost: number;
  }>;
  model_breakdown: Array<{
    model: string;
    total_calls: number;
    total_tokens: number;
    total_cost: number;
  }>;
  daily_breakdown: Array<{
    date: string;
    calls_count: number;
    sum_prompt_tokens: number;
    sum_completion_tokens: number;
    sum_total_tokens: number;
    sum_input_cost: number;
    sum_output_cost: number;
    sum_total_cost: number;
    avg_latency_ms: number;
    error_count: number;
  }>;
  top_users: Array<{
    user_id: string;
    total_calls: number;
    total_tokens: number;
    total_cost: number;
  }>;
}

export interface TenantRankingsResponse {
  tenants: TenantUsageMetrics[];
  total_count: number;
  active_count: number;
  returned_count: number;
}

export interface FeatureUsageMetrics {
  feature_id: string;
  total_calls: number;
  total_tokens: number;
  total_cost: string;
  avg_latency_ms: number;
  distinct_tenants: number;
  distinct_projects: number;
}

export interface FeatureAnalyticsResponse {
  features: FeatureUsageMetrics[];
}

export interface ModelUsageMetrics {
  provider: string;
  model_name: string;
  total_calls: number;
  total_tokens: number;
  total_cost: string;
  avg_latency_ms: number;
  error_count: number;
  error_rate: number;
}

export interface ModelAnalyticsResponse {
  models: ModelUsageMetrics[];
}

export interface ProjectUsageMetrics {
  project_id: string;
  total_calls: number;
  total_tokens: number;
  total_cost: string;
  daily_breakdown: DailyUsageMetrics[];
}

export interface UserUsageMetrics {
  user_id: string;
  total_calls: number;
  total_tokens: number;
  total_cost: string;
  daily_breakdown: DailyUsageMetrics[];
}

export interface ModelPricing {
  id: string;
  provider: string;
  model_name: string;
  input_price_per_1k_tokens: string;
  output_price_per_1k_tokens: string;
  embedding_price_per_1k_tokens: string | null;
  currency: string;
  effective_from: string;
  effective_to: string | null;
  is_active: boolean;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreatePricingRequest {
  provider: string;
  model_name: string;
  input_price_per_1k_tokens: number;
  output_price_per_1k_tokens: number;
  embedding_price_per_1k_tokens?: number;
  currency?: string;
  effective_from: string;
  effective_to?: string;
  notes?: string;
}

export interface UpdatePricingRequest {
  input_price_per_1k_tokens?: number;
  output_price_per_1k_tokens?: number;
  embedding_price_per_1k_tokens?: number;
  effective_to?: string;
  notes?: string;
}

// ==========================================
// Token Monitoring API Service
// ==========================================

export class TokenMonitoringService {
  /**
   * Get system-wide AI usage metrics (Super Admin only)
   * GET /api/admin/monitoring/ai-usage/system
   */
  static async getSystemMetrics(params?: {
    start_date?: string;
    end_date?: string;
  }): Promise<SystemMetrics> {
    try {
      const queryParams = new URLSearchParams();
      if (params?.start_date) queryParams.append('start_date', params.start_date);
      if (params?.end_date) queryParams.append('end_date', params.end_date);

      const url = `${API_BASE_URL}/api/admin/monitoring/ai-usage/system${queryParams.toString() ? `?${queryParams}` : ''}`;
      const response = await fetch(url, {
        method: 'GET',
        headers: getAuthHeaders(),
      });
      
      await handleApiError(response);
      return await response.json();
    } catch (error) {
      logError('getSystemMetrics', error);
      throw error;
    }
  }

  /**
   * Get tenant rankings by AI usage (Super Admin only)
   * GET /api/admin/monitoring/ai-usage/tenants
   */
  static async getTenantRankings(params?: {
    limit?: number;
    start_date?: string;
    end_date?: string;
    group_by?: 'organization' | 'tenant';
    include_zero_usage?: boolean;
    tenant_type?: 'organization' | 'team' | 'individual';
  }): Promise<TenantRankingsResponse> {
    try {
      const queryParams = new URLSearchParams();
      if (params?.limit) queryParams.append('limit', params.limit.toString());
      if (params?.start_date) queryParams.append('start_date', params.start_date);
      if (params?.end_date) queryParams.append('end_date', params.end_date);
      if (params?.group_by) queryParams.append('group_by', params.group_by);
      if (params?.include_zero_usage !== undefined) queryParams.append('include_zero_usage', params.include_zero_usage.toString());
      if (params?.tenant_type) queryParams.append('tenant_type', params.tenant_type);

      const url = `${API_BASE_URL}/api/admin/monitoring/ai-usage/tenants${queryParams.toString() ? `?${queryParams}` : ''}`;
      const response = await fetch(url, {
        method: 'GET',
        headers: getAuthHeaders(),
      });
      
      await handleApiError(response);
      return await response.json();
    } catch (error) {
      logError('getTenantRankings', error);
      throw error;
    }
  }

  /**
   * Get detailed usage for a specific tenant (Super Admin only)
   * GET /api/admin/monitoring/ai-usage/tenants/{tenant_id}/detailed
   */
  static async getTenantDetails(
    tenantId: string,
    params?: {
      start_date?: string;
      end_date?: string;
      include_children?: boolean;
    }
  ): Promise<TenantDetailedUsage> {
    try {
      const queryParams = new URLSearchParams();
      if (params?.start_date) queryParams.append('start_date', params.start_date);
      if (params?.end_date) queryParams.append('end_date', params.end_date);
      if (params?.include_children !== undefined) queryParams.append('include_children', params.include_children.toString());

      const url = `${API_BASE_URL}/api/admin/monitoring/ai-usage/tenants/${tenantId}/detailed${queryParams.toString() ? `?${queryParams}` : ''}`;
      const response = await fetch(url, {
        method: 'GET',
        headers: getAuthHeaders(),
      });
      
      await handleApiError(response);
      return await response.json();
    } catch (error) {
      logError('getTenantDetails', error);
      throw error;
    }
  }

  /**
   * Get AI usage analytics by feature (Super Admin only)
   * GET /api/admin/monitoring/ai-usage/features
   */
  static async getFeatureAnalytics(params?: {
    start_date?: string;
    end_date?: string;
  }): Promise<FeatureUsageMetrics[]> {
    try {
      const queryParams = new URLSearchParams();
      if (params?.start_date) queryParams.append('start_date', params.start_date);
      if (params?.end_date) queryParams.append('end_date', params.end_date);

      const url = `${API_BASE_URL}/api/admin/monitoring/ai-usage/features${queryParams.toString() ? `?${queryParams}` : ''}`;
      const response = await fetch(url, {
        method: 'GET',
        headers: getAuthHeaders(),
      });
      
      await handleApiError(response);
      return await response.json();
    } catch (error) {
      logError('getFeatureAnalytics', error);
      throw error;
    }
  }

  /**
   * Get AI usage analytics by model (Super Admin only)
   * GET /api/admin/monitoring/ai-usage/models
   */
  static async getModelAnalytics(params?: {
    start_date?: string;
    end_date?: string;
  }): Promise<ModelUsageMetrics[]> {
    try {
      const queryParams = new URLSearchParams();
      if (params?.start_date) queryParams.append('start_date', params.start_date);
      if (params?.end_date) queryParams.append('end_date', params.end_date);

      const url = `${API_BASE_URL}/api/admin/monitoring/ai-usage/models${queryParams.toString() ? `?${queryParams}` : ''}`;
      const response = await fetch(url, {
        method: 'GET',
        headers: getAuthHeaders(),
      });
      
      await handleApiError(response);
      return await response.json();
    } catch (error) {
      logError('getModelAnalytics', error);
      throw error;
    }
  }

  /**
   * Get AI usage for a specific project (Super Admin only)
   * GET /api/admin/monitoring/ai-usage/projects/{project_id}
   */
  static async getProjectUsage(
    projectId: string,
    params?: {
      start_date?: string;
      end_date?: string;
    }
  ): Promise<ProjectUsageMetrics> {
    try {
      const queryParams = new URLSearchParams();
      if (params?.start_date) queryParams.append('start_date', params.start_date);
      if (params?.end_date) queryParams.append('end_date', params.end_date);

      const url = `${API_BASE_URL}/api/admin/monitoring/ai-usage/projects/${projectId}${queryParams.toString() ? `?${queryParams}` : ''}`;
      const response = await fetch(url, {
        method: 'GET',
        headers: getAuthHeaders(),
      });
      
      await handleApiError(response);
      return await response.json();
    } catch (error) {
      logError('getProjectUsage', error);
      throw error;
    }
  }

  /**
   * Get AI usage for a specific user (Super Admin only)
   * GET /api/admin/monitoring/ai-usage/users/{user_id}
   */
  static async getUserUsage(
    userId: string,
    params?: {
      start_date?: string;
      end_date?: string;
    }
  ): Promise<UserUsageMetrics> {
    try {
      const queryParams = new URLSearchParams();
      if (params?.start_date) queryParams.append('start_date', params.start_date);
      if (params?.end_date) queryParams.append('end_date', params.end_date);

      const url = `${API_BASE_URL}/api/admin/monitoring/ai-usage/users/${userId}${queryParams.toString() ? `?${queryParams}` : ''}`;
      const response = await fetch(url, {
        method: 'GET',
        headers: getAuthHeaders(),
      });
      
      await handleApiError(response);
      return await response.json();
    } catch (error) {
      logError('getUserUsage', error);
      throw error;
    }
  }

  /**
   * List AI model pricing configurations (Super Admin only)
   * GET /api/admin/monitoring/ai-model-pricing
   */
  static async listPricing(params?: {
    provider?: string;
    model_name?: string;
    active_only?: boolean;
  }): Promise<ModelPricing[]> {
    try {
      const queryParams = new URLSearchParams();
      if (params?.provider) queryParams.append('provider', params.provider);
      if (params?.model_name) queryParams.append('model_name', params.model_name);
      if (params?.active_only !== undefined) queryParams.append('active_only', params.active_only.toString());

      const url = `${API_BASE_URL}/api/admin/monitoring/ai-model-pricing${queryParams.toString() ? `?${queryParams}` : ''}`;
      const response = await fetch(url, {
        method: 'GET',
        headers: getAuthHeaders(),
      });
      
      await handleApiError(response);
      return await response.json();
    } catch (error) {
      logError('listPricing', error);
      throw error;
    }
  }

  /**
   * Create new AI model pricing configuration (Super Admin only)
   * POST /api/admin/monitoring/ai-model-pricing
   */
  static async createPricing(data: CreatePricingRequest): Promise<ModelPricing> {
    try {
      const url = `${API_BASE_URL}/api/admin/monitoring/ai-model-pricing`;
      const response = await fetch(url, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(data),
      });
      
      await handleApiError(response);
      return await response.json();
    } catch (error) {
      logError('createPricing', error);
      throw error;
    }
  }

  /**
   * Update existing AI model pricing configuration (Super Admin only)
   * PATCH /api/admin/monitoring/ai-model-pricing/{pricing_id}
   */
  static async updatePricing(
    pricingId: string,
    data: UpdatePricingRequest
  ): Promise<ModelPricing> {
    try {
      const url = `${API_BASE_URL}/api/admin/monitoring/ai-model-pricing/${pricingId}`;
      const response = await fetch(url, {
        method: 'PATCH',
        headers: getAuthHeaders(),
        body: JSON.stringify(data),
      });
      
      await handleApiError(response);
      return await response.json();
    } catch (error) {
      logError('updatePricing', error);
      throw error;
    }
  }

  /**
   * Delete AI model pricing configuration (Super Admin only)
   * DELETE /api/admin/monitoring/ai-model-pricing/{pricing_id}
   */
  static async deletePricing(pricingId: string): Promise<void> {
    try {
      const url = `${API_BASE_URL}/api/admin/monitoring/ai-model-pricing/${pricingId}`;
      const response = await fetch(url, {
        method: 'DELETE',
        headers: getAuthHeaders(),
      });
      
      await handleApiError(response);
    } catch (error) {
      logError('deletePricing', error);
      throw error;
    }
  }
}

// Export singleton instance
export const tokenMonitoringService = TokenMonitoringService;
