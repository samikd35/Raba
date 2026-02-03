import { authService } from '../../services/authService';

/**
 * Feature Service - Super Admin Only
 * 
 * This service handles all Feature Credit Management API calls including:
 * - Module Features CRUD (generator, analyzer, validator, reporter)
 * - Feature Credit Costs CRUD (plan-based pricing overrides)
 * - Cost Resolution (determine effective cost for feature + plan)
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
    console.error(`[FeatureService] ${context}:`, error);
  }
};

// ==========================================
// Type Definitions
// ==========================================

export type FeatureType = 'generator' | 'analyzer' | 'validator' | 'reporter';
export type PlanType = 'individual' | 'team' | 'organization';

export interface ModuleFeature {
  id: string;
  name: string;
  display_name: string;
  description: string | null;
  feature_type: FeatureType;
  credit_cost: number;
  is_active: boolean;
  settings: Record<string, any>;
  created_at: string;
}

export interface FeatureCreditCost {
  id: string;
  feature_id: string;
  plan_type: PlanType;
  credit_cost: number;
  is_active: boolean;
  effective_from: string;
  effective_until: string | null;
  created_at: string;
}

export interface ResolvedFeatureCost {
  feature_id: string;
  plan_type: PlanType;
  credit_cost: number;
  source: 'feature_credit_costs' | 'module_features';
  effective_from: string | null;
  effective_until: string | null;
}

export interface CreateFeatureRequest {
  name: string;
  display_name: string;
  description?: string;
  feature_type: FeatureType;
  credit_cost: number;
  is_active?: boolean;
  settings?: Record<string, any>;
}

export interface UpdateFeatureRequest {
  display_name?: string;
  description?: string;
  feature_type?: FeatureType;
  credit_cost?: number;
  is_active?: boolean;
  settings?: Record<string, any>;
}

export interface CreateCreditCostRequest {
  feature_id: string;
  plan_type: PlanType;
  credit_cost: number;
  is_active?: boolean;
  effective_from?: string;
  effective_until?: string;
}

export interface UpdateCreditCostRequest {
  plan_type?: PlanType;
  credit_cost?: number;
  is_active?: boolean;
  effective_from?: string;
  effective_until?: string;
}

export interface ListFeaturesParams {
  limit?: number;
  offset?: number;
  search?: string;
  feature_type?: FeatureType;
  is_active?: boolean;
}

export interface ListCreditCostsParams {
  limit?: number;
  offset?: number;
  feature_id?: string;
  plan_type?: PlanType;
  is_active?: boolean;
  current_only?: boolean;
  as_of?: string;
}

// ==========================================
// Feature Service API
// ==========================================

export class FeatureService {
  // ==========================================
  // Module Features CRUD
  // ==========================================

  /**
   * List all module features with optional filtering
   * GET /api/features/
   */
  static async listFeatures(params?: ListFeaturesParams): Promise<ModuleFeature[]> {
    try {
      const queryParams = new URLSearchParams();
      if (params?.limit) queryParams.append('limit', params.limit.toString());
      if (params?.offset) queryParams.append('offset', params.offset.toString());
      if (params?.search) queryParams.append('search', params.search);
      if (params?.feature_type) queryParams.append('feature_type', params.feature_type);
      if (params?.is_active !== undefined) queryParams.append('is_active', params.is_active.toString());

      const url = `${API_BASE_URL}/api/features/${queryParams.toString() ? `?${queryParams}` : ''}`;
      const response = await fetch(url, {
        method: 'GET',
        headers: getAuthHeaders(),
      });

      await handleApiError(response);
      return await response.json();
    } catch (error) {
      logError('listFeatures', error);
      throw error;
    }
  }

  /**
   * Get a single feature by ID
   * GET /api/features/{feature_id}
   */
  static async getFeature(featureId: string): Promise<ModuleFeature> {
    try {
      const url = `${API_BASE_URL}/api/features/${featureId}`;
      const response = await fetch(url, {
        method: 'GET',
        headers: getAuthHeaders(),
      });

      await handleApiError(response);
      return await response.json();
    } catch (error) {
      logError('getFeature', error);
      throw error;
    }
  }

  /**
   * Create a new module feature
   * POST /api/features/
   */
  static async createFeature(data: CreateFeatureRequest): Promise<ModuleFeature> {
    try {
      const url = `${API_BASE_URL}/api/features/`;
      const response = await fetch(url, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(data),
      });

      await handleApiError(response);
      return await response.json();
    } catch (error) {
      logError('createFeature', error);
      throw error;
    }
  }

  /**
   * Update an existing module feature
   * PUT /api/features/{feature_id}
   */
  static async updateFeature(featureId: string, data: UpdateFeatureRequest): Promise<ModuleFeature> {
    try {
      const url = `${API_BASE_URL}/api/features/${featureId}`;
      const response = await fetch(url, {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify(data),
      });

      await handleApiError(response);
      return await response.json();
    } catch (error) {
      logError('updateFeature', error);
      throw error;
    }
  }

  /**
   * Delete a module feature
   * DELETE /api/features/{feature_id}
   */
  static async deleteFeature(featureId: string): Promise<void> {
    try {
      const url = `${API_BASE_URL}/api/features/${featureId}`;
      const response = await fetch(url, {
        method: 'DELETE',
        headers: getAuthHeaders(),
      });

      await handleApiError(response);
    } catch (error) {
      logError('deleteFeature', error);
      throw error;
    }
  }

  /**
   * Toggle feature active status
   * POST /api/features/{feature_id}/toggle
   */
  static async toggleFeature(featureId: string, isActive: boolean): Promise<ModuleFeature> {
    try {
      const url = `${API_BASE_URL}/api/features/${featureId}/toggle?is_active=${isActive}`;
      const response = await fetch(url, {
        method: 'POST',
        headers: getAuthHeaders(),
      });

      await handleApiError(response);
      return await response.json();
    } catch (error) {
      logError('toggleFeature', error);
      throw error;
    }
  }

  // ==========================================
  // Feature Credit Costs CRUD
  // ==========================================

  /**
   * List all feature credit costs with optional filtering
   * GET /api/features/credit-costs
   */
  static async listCreditCosts(params?: ListCreditCostsParams): Promise<FeatureCreditCost[]> {
    try {
      const queryParams = new URLSearchParams();
      if (params?.limit) queryParams.append('limit', params.limit.toString());
      if (params?.offset) queryParams.append('offset', params.offset.toString());
      if (params?.feature_id) queryParams.append('feature_id', params.feature_id);
      if (params?.plan_type) queryParams.append('plan_type', params.plan_type);
      if (params?.is_active !== undefined) queryParams.append('is_active', params.is_active.toString());
      if (params?.current_only !== undefined) queryParams.append('current_only', params.current_only.toString());
      if (params?.as_of) queryParams.append('as_of', params.as_of);

      const url = `${API_BASE_URL}/api/features/credit-costs${queryParams.toString() ? `?${queryParams}` : ''}`;
      const response = await fetch(url, {
        method: 'GET',
        headers: getAuthHeaders(),
      });

      await handleApiError(response);
      return await response.json();
    } catch (error) {
      logError('listCreditCosts', error);
      throw error;
    }
  }

  /**
   * Get a single credit cost by ID
   * GET /api/features/credit-costs/{cost_id}
   */
  static async getCreditCost(costId: string): Promise<FeatureCreditCost> {
    try {
      const url = `${API_BASE_URL}/api/features/credit-costs/${costId}`;
      const response = await fetch(url, {
        method: 'GET',
        headers: getAuthHeaders(),
      });

      await handleApiError(response);
      return await response.json();
    } catch (error) {
      logError('getCreditCost', error);
      throw error;
    }
  }

  /**
   * Create a new credit cost override
   * POST /api/features/credit-costs
   */
  static async createCreditCost(data: CreateCreditCostRequest): Promise<FeatureCreditCost> {
    try {
      const url = `${API_BASE_URL}/api/features/credit-costs`;
      const response = await fetch(url, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(data),
      });

      await handleApiError(response);
      return await response.json();
    } catch (error) {
      logError('createCreditCost', error);
      throw error;
    }
  }

  /**
   * Update an existing credit cost
   * PUT /api/features/credit-costs/{cost_id}
   */
  static async updateCreditCost(costId: string, data: UpdateCreditCostRequest): Promise<FeatureCreditCost> {
    try {
      const url = `${API_BASE_URL}/api/features/credit-costs/${costId}`;
      const response = await fetch(url, {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify(data),
      });

      await handleApiError(response);
      return await response.json();
    } catch (error) {
      logError('updateCreditCost', error);
      throw error;
    }
  }

  /**
   * Delete a credit cost
   * DELETE /api/features/credit-costs/{cost_id}
   */
  static async deleteCreditCost(costId: string): Promise<void> {
    try {
      const url = `${API_BASE_URL}/api/features/credit-costs/${costId}`;
      const response = await fetch(url, {
        method: 'DELETE',
        headers: getAuthHeaders(),
      });

      await handleApiError(response);
    } catch (error) {
      logError('deleteCreditCost', error);
      throw error;
    }
  }

  /**
   * Toggle credit cost active status
   * POST /api/features/credit-costs/{cost_id}/toggle
   */
  static async toggleCreditCost(costId: string, isActive: boolean): Promise<FeatureCreditCost> {
    try {
      const url = `${API_BASE_URL}/api/features/credit-costs/${costId}/toggle?is_active=${isActive}`;
      const response = await fetch(url, {
        method: 'POST',
        headers: getAuthHeaders(),
      });

      await handleApiError(response);
      return await response.json();
    } catch (error) {
      logError('toggleCreditCost', error);
      throw error;
    }
  }

  // ==========================================
  // Cost Resolution
  // ==========================================

  /**
   * Resolve the effective cost for a feature + plan combination
   * GET /api/features/{feature_id}/resolve-cost
   */
  static async resolveCost(
    featureId: string,
    planType: PlanType,
    asOf?: string
  ): Promise<ResolvedFeatureCost> {
    try {
      const queryParams = new URLSearchParams();
      queryParams.append('plan_type', planType);
      if (asOf) queryParams.append('as_of', asOf);

      const url = `${API_BASE_URL}/api/features/${featureId}/resolve-cost?${queryParams}`;
      const response = await fetch(url, {
        method: 'GET',
        headers: getAuthHeaders(),
      });

      await handleApiError(response);
      return await response.json();
    } catch (error) {
      logError('resolveCost', error);
      throw error;
    }
  }
}

// Export singleton instance
export const featureService = FeatureService;
