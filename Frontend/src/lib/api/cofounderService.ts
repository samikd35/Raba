// lib/api/cofounderService.ts
/**
 * Cofounder Matching API Service
 *
 * This service handles all API calls for the Cofounder Matching feature:
 * - Profile management (create, read, update, submit)
 * - Draft handling
 * - Version management
 * - Enum managment (industries, responsibilities, langauge, commitment, venture stage.
 *
 * Base API documentation: /profiles/me, /profiles/admin, /profiles/enums
 */

import { authService } from '@/services/authService';
import type {
  ProfileVersion,
  ProfileSummary,
  DraftProfileIn,
  SubmitResponse,
  ProfileVersionsListResponse,
  AdminActionResponse,
  AdminRejectRequest,
  EnumItem,
  EnumListResponse,
  EnumItemResponse,
  EnumItemPayload,
  EnumResource,
  ProfileStatus,
} from '@/types/cofounder';

// ============================================================================
// CONFIGURATION
// ============================================================================

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL;

if (!API_BASE_URL) {
  console.warn('NEXT_PUBLIC_API_URL is not defined. API calls will fail.');
}

/**
 * Get authentication token
 * @throws Error if no token available
 */
const getAuthToken = (): string => {
  if (typeof window === 'undefined') {
    throw new Error('Authentication required. Cannot access token on server side.');
  }

  const token = authService.getCurrentToken();
  if (!token) {
    throw new Error('Authentication required. Please sign in to continue.');
  }
  return token;
};

/**
 * Get auth headers for API requests
 */
const getAuthHeaders = (): HeadersInit => {
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${getAuthToken()}`,
  };
};

/**
 * Handle API errors consistently
 */
const handleApiError = async (response: Response): Promise<never> => {
  let errorMessage = `Request failed with status ${response.status}`;

  try {
    const errorData = await response.json();
    console.error('API Error Response:', errorData);
    console.error('API Error Response (stringified):', JSON.stringify(errorData, null, 2));

    // Handle FastAPI validation errors
    if (errorData.detail && Array.isArray(errorData.detail)) {
      const validationErrors = errorData.detail.map((err: any) => {
        const location = err.loc ? err.loc.join(' -> ') : 'unknown';
        return `${location}: ${err.msg}`;
      }).join('\n');
      errorMessage = `Validation Error:\n${validationErrors}`;
    } else if (errorData.detail) {
      errorMessage = typeof errorData.detail === 'string' ? errorData.detail : JSON.stringify(errorData.detail);
    } else if (errorData.message) {
      errorMessage = errorData.message;
    }
  } catch {
    // If response is not JSON, use status text
    errorMessage = response.statusText || errorMessage;
  }

  throw new Error(errorMessage);
};

// ============================================================================
// PROFILES.ME API - Self-service profile management
// ============================================================================

export class ProfilesMeAPI {
  /**
   * GET /profiles/me/ - Get my profile summary
   * Returns: profile metadata, last approved version, and latest version
   */
  static async getMyProfileSummary(): Promise<ProfileSummary> {
    const response = await fetch(`${API_BASE_URL}/profiles/me/`, {
      method: 'GET',
      headers: getAuthHeaders(),
    });

    if (!response.ok) {
      await handleApiError(response);
    }

    return response.json();
  }

  /**
   * POST /profiles/me/save-draft - Save a new draft version
   * Creates an immutable draft version
   * @param draft - Draft profile data
   * @param profilePicture - Optional profile picture file
   * @returns The created ProfileVersion
   */
  static async saveDraft(draft: Partial<DraftProfileIn>, profilePicture?: File): Promise<ProfileVersion> {
    const token = getAuthToken();

    
    // Send as multipart/form-data with both data and file
    const formData = new FormData();

    // Remove profile_picture from draft data if it exists
    const { profile_picture, ...draftWithoutPicture } = draft as any;

    // Add profile data as JSON string
    formData.append('data', JSON.stringify(draftWithoutPicture));

    // Add profile picture file only if provided
    if (profilePicture) {
      formData.append('profile_picture', profilePicture);
    }

    const response = await fetch(`${API_BASE_URL}/profiles/me/save-draft`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
      body: formData,
    });

    if (!response.ok) {
      await handleApiError(response);
    }

    return response.json();

  }

  /**
   * POST /profiles/me/submit - Submit my latest draft for review
   * Submits the most recent draft version
   */
  static async submitLatestDraft(): Promise<SubmitResponse> {
    const response = await fetch(`${API_BASE_URL}/profiles/me/submit`, {
      method: 'POST',
      headers: getAuthHeaders(),
    });

    if (!response.ok) {
      await handleApiError(response);
    }

    return response.json();
  }

  /**
   * GET /profiles/me/{profile_id} - PUBLIC: Get approved profile by ID
   * No authentication required - returns only approved profiles
   * @param profileId - Profile ID to fetch
   */
  static async getPublicProfile(profileId: string): Promise<ProfileVersion> {
    const response = await fetch(`${API_BASE_URL}/profiles/me/${profileId}`, {
      method: 'GET',
      // No auth header for public endpoint
    });

    if (!response.ok) {
      if (response.status === 404) {
        throw new Error('Profile not found or not approved');
      }
      await handleApiError(response);
    }

    return response.json();
  }

  /**
   * GET /profiles/me/versions - List my profile versions
   * @param status - Filter by status (default: 'all')
   * @param limit - Max items to return (1-200, default 50)
   */
  static async listMyVersions(
    status: ProfileStatus | 'all' = 'all',
    limit = 50
  ): Promise<ProfileVersion[]> {
    const params = new URLSearchParams({
      status,
      limit: String(limit),
    });

    const response = await fetch(
      `${API_BASE_URL}/profiles/me/versions?${params.toString()}`,
      {
        method: 'GET',
        headers: getAuthHeaders(),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    const data: ProfileVersionsListResponse = await response.json();
    return data.items;
  }

  /**
   * GET /profiles/me/versions/latest - Get my latest version
   * @param status - Optional status filter
   */
  static async getLatestVersion(
    status: ProfileStatus | 'all' = 'all'
  ): Promise<ProfileVersion> {
    const params = new URLSearchParams({ status });

    const response = await fetch(
      `${API_BASE_URL}/profiles/me/versions/latest?${params.toString()}`,
      {
        method: 'GET',
        headers: getAuthHeaders(),
      }
    );

    if (!response.ok) {
      if (response.status === 404) {
        throw new Error('No profile version found');
      }
      await handleApiError(response);
    }

    return response.json();
  }

  /**
   * GET /profiles/me/drafts - List my draft versions only
   * @param limit - Max items to return (1-200, default 50)
   */
  static async listDrafts(limit = 50): Promise<ProfileVersion[]> {
    const params = new URLSearchParams({ limit: String(limit) });

    const response = await fetch(
      `${API_BASE_URL}/profiles/me/drafts?${params.toString()}`,
      {
        method: 'GET',
        headers: getAuthHeaders(),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    const data: ProfileVersionsListResponse = await response.json();
    return data.items;
  }

  /**
   * GET /profiles/me/versions/{version_id} - Get a specific version of mine
   * @param versionId - Version ID to fetch
   */
  static async getVersion(versionId: string): Promise<ProfileVersion> {
    const response = await fetch(
      `${API_BASE_URL}/profiles/me/versions/${versionId}`,
      {
        method: 'GET',
        headers: getAuthHeaders(),
      }
    );

    if (!response.ok) {
      if (response.status === 404) {
        throw new Error('Version not found or does not belong to you');
      }
      await handleApiError(response);
    }

    return response.json();
  }

  /**
   * POST /profiles/me/me/versions/{version_id}/submit - Submit a specific draft
   * Note: Route contains /me/me/ as per backend API
   * @param versionId - Draft version ID to submit
   */
  static async submitDraftById(versionId: string): Promise<SubmitResponse> {
    const response = await fetch(
      `${API_BASE_URL}/profiles/me/me/versions/${versionId}/submit`,
      {
        method: 'POST',
        headers: getAuthHeaders(),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    return response.json();
  }

  /**
   * GET /profiles/me/me/approved - Get my currently approved version
   * Note: Route contains /me/me/ as per backend API
   */
  static async getMyApprovedVersion(): Promise<ProfileVersion> {
    const response = await fetch(`${API_BASE_URL}/profiles/me/me/approved`, {
      method: 'GET',
      headers: getAuthHeaders(),
    });

    if (!response.ok) {
      if (response.status === 404) {
        throw new Error('No approved profile version found');
      }
      await handleApiError(response);
    }

    return response.json();
  }

  /**
   * POST /profiles/directory/search - Search directory of approved profiles
   * IMPORTANT: Only accessible to users with approved profiles (enforced by backend)
   * Server-side filtering with non-negotiables respected
   * @param filters - Search filters
   * @param page - Page number (1-indexed)
   * @param limit - Number of results per page
   */
  static async searchDirectory(filters?: {
    country?: string;
    countries?: string[];
    languages?: string[];
    age_min?: number;
    age_max?: number;
    preferred_commitment?: string;
    preferred_venture_stage?: string[];
  }, page: number = 1, limit: number = 20): Promise<{
    total: number;
    page: number;
    total_pages: number;
    limit: number;
    items: Array<ProfileVersion & { user_id: string; version_id: string }>;
  }> {
    const payload: Record<string, any> = {
      ...filters,
      page,
      limit,
    };

    if (filters?.country && (!filters.countries || filters.countries.length === 0)) {
      payload.countries = [filters.country];
    }

    if (payload.country) {
      delete payload.country;
    }

    if (payload.countries) {
      payload.countries = payload.countries
        .filter((country: string) => Boolean(country))
        .map((country: string) => country.toLowerCase());
    }

    const response = await fetch(`${API_BASE_URL}/profiles/directory/search`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      await handleApiError(response);
    }

    return response.json();
  }

  /**
   * GET /profiles/directory/versions/{version_id} - Get full profile from directory by version ID
   * Fetches complete profile data excluding personal information
   * @param versionId - Version ID to fetch
   */
  static async getDirectoryProfileByVersion(versionId: string): Promise<ProfileVersion> {
    const response = await fetch(
      `${API_BASE_URL}/profiles/directory/versions/${versionId}`,
      {
        method: 'GET',
        headers: getAuthHeaders(),
      }
    );

    if (!response.ok) {
      if (response.status === 404) {
        throw new Error('Profile not found');
      }
      await handleApiError(response);
    }

    return response.json();
  }

  /**
   * Check if current user has an approved profile
   * Required to access the directory
   */
  static async hasApprovedProfile(): Promise<boolean> {
    try {
      await this.getMyApprovedVersion();
      return true;
    } catch (error) {
      return false;
    }
  }

  /**
   * GET /profiles/me/matches - Get top K matches for current user
   * @param k - Number of top matches to return (default: 20, max: 100)
   */
  static async getTopMatches(k: number = 20): Promise<any[]> {
    const params = new URLSearchParams({ k: String(k) });

    const response = await fetch(
      `${API_BASE_URL}/profiles/me/matches?${params.toString()}`,
      {
        method: 'GET',
        headers: getAuthHeaders(),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    const data = await response.json();
    return data.matches || [];
  }

  /**
   * GET /profiles/me/matches/by-threshold - Get matches above threshold
   * @param threshold - Minimum match score (default: 70.0, range: 0-100)
   */
  static async getMatchesByThreshold(threshold: number = 70.0): Promise<any[]> {
    const params = new URLSearchParams({ threshold: String(threshold) });

    const response = await fetch(
      `${API_BASE_URL}/profiles/me/matches/by-threshold?${params.toString()}`,
      {
        method: 'GET',
        headers: getAuthHeaders(),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    const data = await response.json();
    return data.matches || [];
  }
}

// ============================================================================
// PROFILES.ADMIN API - Admin moderation (requires admin role)
// ============================================================================

export class ProfilesAdminAPI {
  /**
   * GET /profiles/admin/profile-versions - List profile versions for review
   * @param status - Filter by status (default: 'submitted')
   * @param limit - Max items to return (1-200, default 50)
   */
  static async listProfileVersions(
    status: ProfileStatus = 'submitted',
    limit = 50
  ): Promise<ProfileVersion[]> {
    const params = new URLSearchParams({
      status,
      limit: String(limit),
    });

    const response = await fetch(
      `${API_BASE_URL}/profiles/admin/profile-versions?${params.toString()}`,
      {
        method: 'GET',
        headers: getAuthHeaders(),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    const data: ProfileVersionsListResponse = await response.json();
    return data.items;
  }

  /**
   * POST /profiles/admin/profile-versions/{version_id}/approve - Approve a version
   * @param versionId - Version ID to approve
   */
  static async approveVersion(versionId: string): Promise<AdminActionResponse> {
    const response = await fetch(
      `${API_BASE_URL}/profiles/admin/profile-versions/${versionId}/approve`,
      {
        method: 'POST',
        headers: getAuthHeaders(),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    return response.json();
  }

  /**
   * POST /profiles/admin/profile-versions/{version_id}/reject - Reject a version
   * @param versionId - Version ID to reject
   * @param reason - Rejection reason
   */
  static async rejectVersion(
    versionId: string,
    reason: string
  ): Promise<AdminActionResponse> {
    const payload: AdminRejectRequest = { reason };

    const response = await fetch(
      `${API_BASE_URL}/profiles/admin/profile-versions/${versionId}/reject`,
      {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(payload),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    return response.json();
  }
}

// ============================================================================
// PROFILES.ENUMS API - Enumerated options for dropdowns
// ============================================================================

export class ProfilesEnumsAPI {
  /**
   * GET /profiles/enums/{resource} - List active enum items
   * Returns only is_active=true items for end users
   *
   * @param resource - Resource type (industries, responsibilities, commitment, venture_stages)
   * @param search - Optional search term
   * @param page - Page number (1-based, default 1)
   * @param pageSize - Items per page (1-500, default 100)
   */
  static async listEnums(
    resource: EnumResource,
    options?: {
      search?: string;
      page?: number;
      pageSize?: number;
    }
  ): Promise<EnumListResponse> {
    const params = new URLSearchParams({
      page: String(options?.page ?? 1),
      page_size: String(options?.pageSize ?? 100),
    });

    if (options?.search) {
      params.set('search', options.search);
    }

    const response = await fetch(
      `${API_BASE_URL}/profiles/enums/${resource}?${params.toString()}`,
      {
        method: 'GET',
        headers: getAuthHeaders(),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    return response.json();
  }

  /**
   * GET /profiles/enums/industries - List active industries
   */
  static async listIndustries(options?: {
    search?: string;
    page?: number;
    pageSize?: number;
  }): Promise<EnumListResponse> {
    return this.listEnums('industries', options);
  }

  /**
   * GET /profiles/enums/responsibilities - List active responsibilities
   */
  static async listResponsibilities(options?: {
    search?: string;
    page?: number;
    pageSize?: number;
  }): Promise<EnumListResponse> {
    return this.listEnums('responsibilities', options);
  }

  /**
   * GET /profiles/enums/commitment - List active commitment options
   * ⚠️ Note: Path is singular "commitment" not "commitments"
   */
  static async listCommitment(options?: {
    search?: string;
    page?: number;
    pageSize?: number;
  }): Promise<EnumListResponse> {
    return this.listEnums('commitment', options);
  }

  /**
   * GET /profiles/enums/venture_stages - List active venture stages
   */
  static async listVentureStages(options?: {
    search?: string;
    page?: number;
    pageSize?: number;
  }): Promise<EnumListResponse> {
    return this.listEnums('venture_stages', options);
  }

  /**
   * GET /profiles/enums/languages - List active languages
   */
  static async listLanguages(options?: {
    search?: string;
    page?: number;
    pageSize?: number;
  }): Promise<EnumListResponse> {
    return this.listEnums('languages', options);
  }

  /**
   * GET /profiles/enums/admin/{resource} - Admin list (includes inactive)
   * @param resource - Resource type
   * @param options - Query options including is_active filter
   */
  static async adminListEnums(
    resource: EnumResource,
    options?: {
      search?: string;
      isActive?: boolean;
      page?: number;
      pageSize?: number;
    }
  ): Promise<EnumListResponse> {
    const params = new URLSearchParams({
      page: String(options?.page ?? 1),
      page_size: String(options?.pageSize ?? 100),
    });

    if (options?.search) {
      params.set('search', options.search);
    }

    if (typeof options?.isActive === 'boolean') {
      params.set('is_active', String(options.isActive));
    }

    const response = await fetch(
      `${API_BASE_URL}/profiles/enums/admin/${resource}?${params.toString()}`,
      {
        method: 'GET',
        headers: getAuthHeaders(),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    return response.json();
  }

  /**
   * POST /profiles/enums/{resource} - Create enum item (admin only)
   */
  static async createEnumItem(
    resource: EnumResource,
    payload: EnumItemPayload
  ): Promise<EnumItemResponse> {
    const response = await fetch(`${API_BASE_URL}/profiles/enums/${resource}`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      await handleApiError(response);
    }

    return response.json();
  }

  /**
   * GET /profiles/enums/{resource}/{id} - Get one enum item (admin only)
   */
  static async getEnumItem(
    resource: EnumResource,
    id: string
  ): Promise<EnumItemResponse> {
    const response = await fetch(
      `${API_BASE_URL}/profiles/enums/${resource}/${id}`,
      {
        method: 'GET',
        headers: getAuthHeaders(),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    return response.json();
  }

  /**
   * PUT /profiles/enums/{resource}/{id} - Update enum item (admin only)
   */
  static async updateEnumItem(
    resource: EnumResource,
    id: string,
    payload: Partial<EnumItemPayload>
  ): Promise<EnumItemResponse> {
    const response = await fetch(
      `${API_BASE_URL}/profiles/enums/${resource}/${id}`,
      {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify(payload),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    return response.json();
  }

  /**
   * POST /profiles/enums/{resource}/{id}/activate - Activate enum item (admin only)
   */
  static async activateEnumItem(
    resource: EnumResource,
    id: string
  ): Promise<EnumItemResponse> {
    const response = await fetch(
      `${API_BASE_URL}/profiles/enums/${resource}/${id}/activate`,
      {
        method: 'POST',
        headers: getAuthHeaders(),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    return response.json();
  }

  /**
   * POST /profiles/enums/{resource}/{id}/deactivate - Deactivate enum item (admin only)
   */
  static async deactivateEnumItem(
    resource: EnumResource,
    id: string
  ): Promise<EnumItemResponse> {
    const response = await fetch(
      `${API_BASE_URL}/profiles/enums/${resource}/${id}/deactivate`,
      {
        method: 'POST',
        headers: getAuthHeaders(),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    return response.json();
  }

  /**
   * DELETE /profiles/enums/{resource}/{id} - Delete enum item (super_admin only)
   */
  static async deleteEnumItem(
    resource: EnumResource,
    id: string
  ): Promise<{ success: boolean; message: string }> {
    const response = await fetch(
      `${API_BASE_URL}/profiles/enums/${resource}/${id}`,
      {
        method: 'DELETE',
        headers: getAuthHeaders(),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    return response.json();
  }
}

// ============================================================================
// CONVENIENCE EXPORTS
// ============================================================================

/**
 * Combined API client for Cofounder Matching
 */
export const cofounderAPI = {
  profiles: ProfilesMeAPI,
  admin: ProfilesAdminAPI,
  enums: ProfilesEnumsAPI,
};

export default cofounderAPI;
