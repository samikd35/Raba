import axios, { AxiosError } from 'axios';
import { Tenant, TenantCreateRequest, TenantListResponse } from '@/types/tenant';
import { authService } from '@/services/authService';

// Always use the real API for tenants per user request.
const API_BASE = process.env.NEXT_PUBLIC_API_URL ;

function buildHeaders(): Record<string, string> {
  // Use the same approach as authService for consistency
  const headers = authService.getAuthHeaders();
  
  // Check if we have a valid token
  if (!headers.Authorization) {
    throw new Error('No authentication token available. Please log in again.');
  }
  
  return headers;
}

function extractAxiosError(err: unknown): string {
  if (!err) return 'Unknown error';
  if ((err as AxiosError).isAxiosError) {
    const aerr = err as AxiosError<any>;
    if (aerr.response && aerr.response.data) {
      const data = aerr.response.data as any;
      return data.message || data.error || JSON.stringify(data) || aerr.message;
    }
    return aerr.message;
  }
  return (err as Error).message || String(err);
}

// API response wrapper
interface ApiResponse<T> {
  success: boolean;
  message: string;
  data: T;
  total?: number;
  page?: number;
  page_size?: number;
}

// Update request type (same as create but all fields optional except id)
interface TenantUpdateRequest {
  name?: string;
  description?: string;
  website?: string;
  industry?: string;
  size?: string;
  country?: string;
}

export const tenantService = {
  createTenant(data: TenantCreateRequest): Promise<Tenant> {
    const url = `${API_BASE}/api/v1/tenant/`;
    const headers = buildHeaders();
    return axios
      .post(url, data, { headers })
      .then((resp) => {
        const apiResponse = resp.data as ApiResponse<Tenant>;
        return apiResponse.data;
      })
      .catch((err) => {
        throw new Error(extractAxiosError(err));
      });
  },

  getTenant(id: string): Promise<Tenant> {
    const url = `${API_BASE}/api/v1/tenant/${encodeURIComponent(id)}/`;
    const headers = buildHeaders();
    return axios
      .get(url, { headers })
      .then((resp) => {
        const apiResponse = resp.data as ApiResponse<Tenant>;
        return apiResponse.data;
      })
      .catch((err) => {
        throw new Error(extractAxiosError(err));
      });
  },

  updateTenant(id: string, data: TenantUpdateRequest): Promise<Tenant> {
    const url = `${API_BASE}/api/v1/tenant/${encodeURIComponent(id)}/`;
    const headers = buildHeaders();
    
    return axios
      .put(url, data, { headers })
      .then((resp) => {
        const apiResponse = resp.data as ApiResponse<Tenant>;
        return apiResponse.data;
      })
      .catch((err) => {
        throw new Error(extractAxiosError(err));
      });
  },

  deleteTenant(id: string): Promise<void> {
    const url = `${API_BASE}/api/v1/tenant/${encodeURIComponent(id)}/`;
    const headers = buildHeaders();
    
    return axios
      .delete(url, { headers })
      .then(() => {
        return;
      })
      .catch((err) => {
        throw new Error(extractAxiosError(err));
      });
  },

  listTenants(): Promise<TenantListResponse> {
    const url = `${API_BASE}/api/v1/tenant/`;
    const headers = buildHeaders();
    return axios
      .get(url, { headers })
      .then((resp) => {
        const apiResponse = resp.data as ApiResponse<Tenant[]>;
        return {
          tenants: apiResponse.data,
          total: apiResponse.total
        } as TenantListResponse;
      })
      .catch((err) => {
        throw new Error(extractAxiosError(err));
      });
  },
};