/**
 * Venture Builder Service
 * Handles fetching venture builder profiles from the backend API
 */

import {
  VBProfile,
  BrowseVBsResponse,
  TenantProject,
  CheckCreditsResponse,
  CreateBookingPayload,
  VBSession,
  WorkExperience,
  CreateDisputePayload,
  SessionNote,
  CreateSessionNotePayload,
  UpdateSessionNotePayload,
  EarningsResponse,
  GetEarningsParams,
  EarningsConfig,
  UpdateEarningsConfigPayload,
  ReconcilePayload,
  ReconcileResponse,
  ReconciliationHistoryResponse,
  CanOpenDisputeResponse,
  Dispute,
  GetDisputesResponse,
  GetDisputesParams,
  GetAdminDisputesParams,
  UpdateDisputePayload,
  VBProject,
  ExpertiseArea,
  CreateExpertiseAreaPayload,
  UpdateExpertiseAreaPayload,
} from '@/types/ventureBuilder';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL;
const VB_BASE_PATH = '/venture-builder';

/**
 * Helper function to unwrap standardized VB API response format
 * All VB endpoints return: {success: true, data: {...}, error: null}
 */
function unwrapVBResponse<T>(response: any): T {
  // If response has success and data fields, unwrap it
  if (response && typeof response === 'object' && 'success' in response) {
    if (response.success === false) {
      throw new Error(response.error || 'API request failed');
    }
    return response.data as T;
  }
  // Otherwise return as-is (for backwards compatibility)
  return response as T;
}

/**
 * Fetches all active venture builders (Requires authentication)
 * @param params - Query parameters for filtering and pagination
 * @param token - Authentication token
 * @returns Promise<BrowseVBsResponse>
 */
export async function fetchVentureBuilders(params?: {
  expertise_ids?: string[];
  search_query?: string;
  page?: number;
  page_size?: number;
  token?: string;
}): Promise<BrowseVBsResponse> {
  if (!API_BASE_URL) {
    throw new Error('API URL is not configured');
  }

  try {
    const queryParams = new URLSearchParams();

    // Add pagination parameters
    queryParams.append('page', (params?.page || 1).toString());
    queryParams.append('page_size', (params?.page_size || 20).toString());

    // Add expertise filter
    if (params?.expertise_ids && params.expertise_ids.length > 0) {
      params.expertise_ids.forEach(id => queryParams.append('expertise_ids', id));
    }

    // Add search query
    if (params?.search_query) {
      queryParams.append('search_query', params.search_query);
    }

    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };

    // Add authorization header if token is provided
    if (params?.token) {
      headers['Authorization'] = `Bearer ${params.token}`;
    }

    const response = await fetch(`${API_BASE_URL}${VB_BASE_PATH}/browse?${queryParams.toString()}`, {
      method: 'GET',
      headers,
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`Backend API error: ${response.status} - ${errorText}`);

      if (response.status === 404) {
        throw new Error('Venture builders not found');
      }

      throw new Error(`Failed to fetch venture builders: ${response.status} ${response.statusText}`);
    }

    const rawResponse = await response.json();
    console.log('fetchVentureBuilders - Raw API response:', rawResponse);

    // Unwrap standardized response format
    const data = unwrapVBResponse<BrowseVBsResponse>(rawResponse);
    console.log('fetchVentureBuilders - Unwrapped data:', data);

    // Map areas_of_expertise to expertise_areas for consistency
    const mappedData = {
      ...data,
      items: (data.items || []).map(item => ({
        ...item,
        expertise_areas: item.areas_of_expertise || item.expertise_areas || [],
        is_active: true, // Browse endpoint only returns active VBs
        full_name: item.name || item.full_name || 'Venture Builder', // Fallback if not provided
      }))
    };

    console.log('fetchVentureBuilders - Mapped data:', mappedData);
    return mappedData;
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('An unexpected error occurred while fetching venture builders');
  }
}

/**
 * Fetches a single venture builder by ID (Requires authentication)
 * @param vbId - The ID of the venture builder
 * @param token - Authentication token (optional)
 * @returns Promise<VBProfile>
 */
export async function fetchVentureBuilderById(vbId: string, token?: string): Promise<VBProfile> {
  if (!API_BASE_URL) {
    throw new Error('API URL is not configured');
  }

  if (!vbId) {
    throw new Error('Venture Builder ID is required');
  }

  try {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };

    // Add authorization header if token is provided
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE_URL}${VB_BASE_PATH}/browse/${vbId}`, {
      method: 'GET',
      headers,
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`Backend API error: ${response.status} - ${errorText}`);

      if (response.status === 404) {
        throw new Error('Venture builder not found');
      }

      throw new Error(`Failed to fetch venture builder: ${response.status} ${response.statusText}`);
    }

    const rawResponse = await response.json();
    console.log('fetchVentureBuilderById - Raw API response:', rawResponse);

    // Handle the wrapped response structure {success: true, data: {...}, error: null}
    const data = unwrapVBResponse<VBProfile>(rawResponse);
    console.log('fetchVentureBuilderById - Extracted data:', data);

    // Map the data to ensure field consistency
    const mappedData: VBProfile = {
      ...data,
      expertise_areas: data.areas_of_expertise || data.expertise_areas || [],
      full_name: data.name || data.full_name || 'Venture Builder',
    };

    console.log('fetchVentureBuilderById - Mapped data:', mappedData);
    return mappedData;
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('An unexpected error occurred while fetching venture builder details');
  }
}

/**
 * Fetches tenant projects for booking (Requires authentication)
 * @param token - Authentication token
 * @returns Promise<TenantProject[]>
 */
export async function fetchTenantProjects(token: string): Promise<TenantProject[]> {
  if (!API_BASE_URL) {
    throw new Error('API URL is not configured');
  }

  if (!token) {
    throw new Error('Authentication token is required');
  }

  try {
    const response = await fetch(`${API_BASE_URL}${VB_BASE_PATH}/booking/projects`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`Backend API error: ${response.status} - ${errorText}`);

      if (response.status === 401) {
        throw new Error('Authentication failed. Please sign in again.');
      }

      if (response.status === 403) {
        throw new Error('Access denied. You do not have permission to view projects.');
      }

      throw new Error(`Failed to fetch projects: ${response.status} ${response.statusText}`);
    }

    const rawResponse = await response.json();
    console.log('fetchTenantProjects - Raw response:', rawResponse);

    // Handle wrapped response format {success: true, data: [...], error: null}
    const data: TenantProject[] = Array.isArray(rawResponse) ? rawResponse : rawResponse.data || [];
    console.log('fetchTenantProjects - Extracted data:', data);

    return data;
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('An unexpected error occurred while fetching projects');
  }
}

/**
 * Checks credit balance for booking a session (Requires authentication)
 * @param vbId - The ID of the venture builder
 * @param token - Authentication token
 * @param vbCreditPrice - The VB's credit price per hour (optional, used to calculate sufficiency)
 * @returns Promise<CheckCreditsResponse>
 */
export async function checkBookingCredits(vbId: string, token: string, vbCreditPrice?: number): Promise<CheckCreditsResponse> {
  if (!API_BASE_URL) {
    throw new Error('API URL is not configured');
  }

  if (!vbId) {
    throw new Error('Venture Builder ID is required');
  }

  if (!token) {
    throw new Error('Authentication token is required');
  }

  try {
    const response = await fetch(`${API_BASE_URL}${VB_BASE_PATH}/booking/credits/${vbId}`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`Backend API error: ${response.status} - ${errorText}`);

      if (response.status === 401) {
        throw new Error('Authentication failed. Please sign in again.');
      }

      if (response.status === 402) {
        throw new Error('Insufficient credits for this booking.');
      }

      throw new Error(`Failed to check credits: ${response.status} ${response.statusText}`);
    }

    const rawData = await response.json();
    console.log('checkBookingCredits - Raw API response:', rawData);

    // Unwrap standardized API response format: {success, data, error}
    const data = rawData.data || rawData;

    // Handle new API response format
    // API returns: { tenant_total_active_credits, user_total_consumed_in_tenant, lots, tenant_id }
    // We need: { has_sufficient_credits, current_balance, required_credits, vb_credit_price }
    if ('tenant_total_active_credits' in data) {
      const currentBalance = data.tenant_total_active_credits || 0;
      const requiredCredits = vbCreditPrice || 0;
      const hasSufficientCredits = currentBalance >= requiredCredits;

      return {
        has_sufficient_credits: hasSufficientCredits,
        current_balance: currentBalance,
        required_credits: requiredCredits,
        vb_credit_price: requiredCredits,
      };
    }

    // Handle response that already has the correct format
    return data as CheckCreditsResponse;
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('An unexpected error occurred while checking credits');
  }
}

/**
 * Creates a booking for a VB session (Requires authentication)
 * @param payload - Booking details
 * @param token - Authentication token
 * @returns Promise<VBSession>
 */
export async function createBooking(payload: CreateBookingPayload, token: string): Promise<VBSession> {
  if (!API_BASE_URL) {
    throw new Error('API URL is not configured');
  }

  if (!token) {
    throw new Error('Authentication token is required');
  }

  const bookingUrl = `${API_BASE_URL}${VB_BASE_PATH}/booking`;

  try {
    try {
      new URL(bookingUrl);
    } catch {
      throw new Error(`Invalid API URL: ${bookingUrl}`);
    }

    const response = await fetch(bookingUrl, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`Backend API error: ${response.status} - ${errorText}`);

      if (response.status === 401) {
        throw new Error('Authentication failed. Please sign in again.');
      }

      if (response.status === 402) {
        throw new Error('Insufficient credits for this booking.');
      }

      if (response.status === 409) {
        throw new Error('Booking conflict. This time slot may already be taken.');
      }

      throw new Error(`Failed to create booking: ${response.status} ${response.statusText}`);
    }

    const data: VBSession = await response.json();
    return data;
  } catch (error) {
    if (error instanceof TypeError && error.message.includes('Failed to fetch')) {
      throw new Error(
        `Failed to reach booking API at ${bookingUrl}. Check NEXT_PUBLIC_API_URL, CORS, and network access.`
      );
    }
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('An unexpected error occurred while creating booking');
  }
}

/**
 * ADMIN: Fetches all venture builders including inactive ones (Requires admin authentication)
 * @param token - Authentication token with admin privileges
 * @param status - Optional status filter
 * @returns Promise<VBProfile[]>
 *
 * NOTE: Uses /admin/vb/pending for pending VBs, /browse for all others
 */
export async function fetchAllVBsAdmin(
  token: string,
  status?: 'pending_profile' | 'pending_admin_review' | 'active' | 'inactive'
): Promise<VBProfile[]> {
  if (!API_BASE_URL) {
    throw new Error('API URL is not configured');
  }

  if (!token) {
    throw new Error('Authentication token is required');
  }

  try {
    // Use /admin/vb/pending for pending approvals (has status field)
    // Use /browse for all VBs (doesn't have status field)
    const url = status === 'pending_admin_review'
      ? `${API_BASE_URL}${VB_BASE_PATH}/admin/vb/pending`
      : `${API_BASE_URL}${VB_BASE_PATH}/browse?page=1&page_size=100`;

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`Backend API error: ${response.status} - ${errorText}`);

      if (response.status === 401) {
        throw new Error('Authentication failed. Please sign in again.');
      }

      if (response.status === 403) {
        throw new Error('Access denied. Admin privileges required.');
      }

      throw new Error(`Failed to fetch VBs: ${response.status} ${response.statusText}`);
    }

    const rawResponse = await response.json();

    // Handle different response formats
    let items: VBProfile[] = [];
    if (status === 'pending_admin_review') {
      // /admin/vb/pending returns {success: true, data: [...], error: null}
      const data = unwrapVBResponse<VBProfile[]>(rawResponse);
      items = Array.isArray(data) ? data : [];
    } else {
      // /browse returns {success: true, data: {items: [...], total, page, page_size}, error: null}
      const data = unwrapVBResponse<BrowseVBsResponse>(rawResponse);
      items = data.items || [];
    }

    // Map the data to ensure field consistency
    const mappedItems = items.map(item => ({
      ...item,
      expertise_areas: item.areas_of_expertise || item.expertise_areas || [],
      full_name: item.name || item.full_name || 'Venture Builder',
    }));

    return mappedItems;
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('An unexpected error occurred while fetching VBs');
  }
}

/**
 * ADMIN: Fetches a single VB by ID with full details (Requires admin authentication)
 * Uses the browse endpoint with authentication for admin access
 * @param vbId - The ID of the venture builder
 * @param token - Authentication token with admin privileges
 * @returns Promise<VBProfile>
 */
export async function fetchVBByIdAdmin(vbId: string, token: string): Promise<VBProfile> {
  if (!API_BASE_URL) {
    throw new Error('API URL is not configured');
  }

  if (!vbId) {
    throw new Error('Venture Builder ID is required');
  }

  if (!token) {
    throw new Error('Authentication token is required');
  }

  try {
    // Use the browse endpoint with admin authentication
    const response = await fetch(`${API_BASE_URL}${VB_BASE_PATH}/browse/${vbId}`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`Backend API error: ${response.status} - ${errorText}`);

      if (response.status === 401) {
        throw new Error('Authentication failed. Please sign in again.');
      }

      if (response.status === 403) {
        throw new Error('Access denied. Admin privileges required.');
      }

      if (response.status === 404) {
        throw new Error('Venture builder not found');
      }

      throw new Error(`Failed to fetch VB: ${response.status} ${response.statusText}`);
    }

    const rawResponse = await response.json();
    const data = unwrapVBResponse<VBProfile>(rawResponse);

    // Map the data to ensure field consistency
    return {
      ...data,
      expertise_areas: data.areas_of_expertise || data.expertise_areas || [],
      full_name: data.name || data.full_name || 'Venture Builder',
    };
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('An unexpected error occurred while fetching VB details');
  }
}

/**
 * ADMIN: Updates VB profile information (Requires admin authentication)
 * @param vbId - The ID of the venture builder
 * @param payload - Updated profile data
 * @param token - Authentication token with admin privileges
 * @returns Promise<VBProfile>
 */
export async function updateVBProfile(
  vbId: string,
  payload: any,
  token: string
): Promise<VBProfile> {
  if (!API_BASE_URL) {
    throw new Error('API URL is not configured');
  }

  if (!vbId) {
    throw new Error('Venture Builder ID is required');
  }

  if (!token) {
    throw new Error('Authentication token is required');
  }

  try {
    const response = await fetch(`${API_BASE_URL}${VB_BASE_PATH}/admin/${vbId}`, {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`Backend API error: ${response.status} - ${errorText}`);

      if (response.status === 401) {
        throw new Error('Authentication failed. Please sign in again.');
      }

      if (response.status === 403) {
        throw new Error('Access denied. Admin privileges required.');
      }

      if (response.status === 404) {
        throw new Error('Venture builder not found');
      }

      throw new Error(`Failed to update VB: ${response.status} ${response.statusText}`);
    }

    const data: VBProfile = await response.json();
    return data;
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('An unexpected error occurred while updating VB');
  }
}

/**
 * ADMIN: Updates VB pricing (Requires admin authentication)
 * @param vbId - The ID of the venture builder
 * @param creditPricePerHour - New credit price per hour
 * @param token - Authentication token with admin privileges
 * @returns Promise<VBProfile>
 */
export async function updateVBPricing(
  vbId: string,
  creditPricePerHour: number,
  token: string
): Promise<VBProfile> {
  if (!API_BASE_URL) {
    throw new Error('API URL is not configured');
  }

  if (!vbId) {
    throw new Error('Venture Builder ID is required');
  }

  if (!token) {
    throw new Error('Authentication token is required');
  }

  try {
    const response = await fetch(`${API_BASE_URL}${VB_BASE_PATH}/admin/vb/${vbId}/pricing`, {
      method: 'PATCH',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ credit_price_per_hour: creditPricePerHour }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`Backend API error: ${response.status} - ${errorText}`);

      if (response.status === 401) {
        throw new Error('Authentication failed. Please sign in again.');
      }

      if (response.status === 403) {
        throw new Error('Access denied. Admin privileges required.');
      }

      if (response.status === 404) {
        throw new Error('Venture builder not found');
      }

      throw new Error(`Failed to update pricing: ${response.status} ${response.statusText}`);
    }

    const data: VBProfile = await response.json();
    return data;
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('An unexpected error occurred while updating pricing');
  }
}

/**
 * ADMIN: Updates VB publish status (Requires admin authentication)
 * @param vbId - The ID of the venture builder
 * @param isActive - Published/unpublished status
 * @param token - Authentication token with admin privileges
 * @returns Promise<VBProfile>
 */
export async function updateVBPublishStatus(
  vbId: string,
  isActive: boolean,
  token: string
): Promise<VBProfile> {
  if (!API_BASE_URL) {
    throw new Error('API URL is not configured');
  }

  if (!vbId) {
    throw new Error('Venture Builder ID is required');
  }

  if (!token) {
    throw new Error('Authentication token is required');
  }

  try {
    const response = await fetch(`${API_BASE_URL}${VB_BASE_PATH}/admin/vb/${vbId}/publish`, {
      method: 'PATCH',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ is_active: isActive }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`Backend API error: ${response.status} - ${errorText}`);

      if (response.status === 401) {
        throw new Error('Authentication failed. Please sign in again.');
      }

      if (response.status === 403) {
        throw new Error('Access denied. Admin privileges required.');
      }

      if (response.status === 404) {
        throw new Error('Venture builder not found');
      }

      throw new Error(`Failed to update publish status: ${response.status} ${response.statusText}`);
    }

    const rawResponse = await response.json();
    return unwrapVBResponse<VBProfile>(rawResponse);
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('An unexpected error occurred while updating publish status');
  }
}

/**
 * ADMIN: Approves a VB profile and sets pricing (Requires admin authentication)
 * Transitions VB from 'pending_admin_review' to 'active'
 * @param vbId - The ID of the venture builder
 * @param creditPricePerHour - Credit price per hour
 * @param token - Authentication token with admin privileges
 * @returns Promise<VBProfile>
 */
export async function approveVBProfile(
  vbId: string,
  creditPricePerHour: number,
  token: string
): Promise<VBProfile> {
  if (!API_BASE_URL) {
    throw new Error('API URL is not configured');
  }

  if (!vbId) {
    throw new Error('Venture Builder ID is required');
  }

  if (!token) {
    throw new Error('Authentication token is required');
  }

  try {
    const response = await fetch(`${API_BASE_URL}${VB_BASE_PATH}/admin/vb/${vbId}/approve`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ credit_price_per_hour: creditPricePerHour }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`Backend API error: ${response.status} - ${errorText}`);

      if (response.status === 401) {
        throw new Error('Authentication failed. Please sign in again.');
      }

      if (response.status === 403) {
        throw new Error('Access denied. Admin privileges required.');
      }

      if (response.status === 404) {
        throw new Error('Venture builder not found');
      }

      if (response.status === 400) {
        throw new Error('Invalid pricing or VB is not in pending_admin_review status');
      }

      throw new Error(`Failed to approve VB: ${response.status} ${response.statusText}`);
    }

    const rawResponse = await response.json();
    return unwrapVBResponse<VBProfile>(rawResponse);
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('An unexpected error occurred while approving VB');
  }
}

/**
 * ADMIN: Rejects a VB profile (Requires admin authentication)
 * @param vbId - The ID of the venture builder
 * @param rejectionReason - Reason for rejection
 * @param token - Authentication token with admin privileges
 * @returns Promise<VBProfile>
 */
export async function rejectVBProfile(
  vbId: string,
  rejectionReason: string,
  token: string
): Promise<VBProfile> {
  if (!API_BASE_URL) {
    throw new Error('API URL is not configured');
  }

  if (!vbId) {
    throw new Error('Venture Builder ID is required');
  }

  if (!rejectionReason) {
    throw new Error('Rejection reason is required');
  }

  if (!token) {
    throw new Error('Authentication token is required');
  }

  try {
    const response = await fetch(`${API_BASE_URL}${VB_BASE_PATH}/admin/vb/${vbId}/reject`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ rejection_reason: rejectionReason }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`Backend API error: ${response.status} - ${errorText}`);

      if (response.status === 401) {
        throw new Error('Authentication failed. Please sign in again.');
      }

      if (response.status === 403) {
        throw new Error('Access denied. Admin privileges required.');
      }

      if (response.status === 404) {
        throw new Error('Venture builder not found');
      }

      if (response.status === 400) {
        throw new Error('VB is not in pending_admin_review status');
      }

      throw new Error(`Failed to reject VB: ${response.status} ${response.statusText}`);
    }

    const rawResponse = await response.json();
    return unwrapVBResponse<VBProfile>(rawResponse);
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('An unexpected error occurred while rejecting VB');
  }
}

/**
 * Fetches all available expertise areas (Public endpoint)
 * @returns Promise<ExpertiseArea[]>
 */
export async function fetchExpertiseAreas(): Promise<any[]> {
  if (!API_BASE_URL) {
    throw new Error('API URL is not configured');
  }

  try {
    const response = await fetch(`${API_BASE_URL}${VB_BASE_PATH}/expertise`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`Backend API error: ${response.status} - ${errorText}`);
      throw new Error(`Failed to fetch expertise areas: ${response.status} ${response.statusText}`);
    }

    const rawResponse = await response.json();
    return unwrapVBResponse(rawResponse);
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('An unexpected error occurred while fetching expertise areas');
  }
}

/**
 * Payload for creating a VB profile via the wizard
 */
export interface CreateVBProfileRequest {
  name: string;
  contact_email: string;
  main_expertise: string;
  short_intro: string;
  biography: string;
  linkedin_url?: string;
  work_experience: WorkExperience[];
  expertise_ids: string[];
}

/**
 * Creates a new VB profile (Requires authentication and invitation token)
 * @param payload - VB profile data
 * @param profilePicture - Optional profile picture file
 * @param token - Authentication token
 * @param invitationToken - Invitation token from email
 * @returns Promise<VBProfile>
 */
export async function createVBProfile(
  payload: CreateVBProfileRequest,
  profilePicture: File | null,
  token: string,
  invitationToken: string
): Promise<VBProfile> {
  if (!API_BASE_URL) {
    throw new Error('API URL is not configured');
  }

  if (!token) {
    throw new Error('Authentication token is required');
  }

  if (!invitationToken) {
    throw new Error('Invitation token is required');
  }

  try {
    const url = `${API_BASE_URL}${VB_BASE_PATH}/profile/create?invitation_token=${encodeURIComponent(invitationToken)}`;

    // Send as multipart/form-data with both data and file
    const formData = new FormData();

    // Add profile data as JSON string
    formData.append('data', JSON.stringify(payload));

    // Add profile picture file if provided
    if (profilePicture) {
      formData.append('profile_picture', profilePicture);
    }

    // Debug: Log final request data
    console.log('createVBProfile request:', { url, data: payload, hasProfilePicture: !!profilePicture });

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        // Don't set Content-Type - browser will set it with boundary for multipart/form-data
      },
      body: formData,
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`Backend API error: ${response.status} - ${errorText}`);

      // Try to parse error message from backend response
      let backendError = '';
      try {
        const errorJson = JSON.parse(errorText);
        backendError = errorJson.error || errorJson.detail || errorJson.message || '';
      } catch {
        backendError = errorText;
      }

      if (response.status === 401) {
        throw new Error('Authentication failed. Please sign in again.');
      }

      if (response.status === 400) {
        throw new Error(backendError || 'Invalid profile data. Please check all fields.');
      }

      if (response.status === 403) {
        throw new Error(backendError || 'Invitation email does not match your account email.');
      }

      if (response.status === 422) {
        throw new Error(backendError || 'Incomplete or invalid profile data. Please fill all required fields.');
      }

      throw new Error(backendError || `Failed to create profile: ${response.status} ${response.statusText}`);
    }

    const rawResponse = await response.json();
    // Handle wrapped response format if present
    const data = rawResponse.data || rawResponse;
    return data as VBProfile;
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('An unexpected error occurred while creating profile');
  }
}

/**
 * Fetches current user's VB profile (Requires authentication)
 * @param token - Authentication token
 * @returns Promise<VBProfile>
 */
export async function fetchMyVBProfile(token: string): Promise<VBProfile> {
  if (!API_BASE_URL) {
    throw new Error('API URL is not configured');
  }

  if (!token) {
    throw new Error('Authentication token is required');
  }

  try {
    const response = await fetch(`${API_BASE_URL}${VB_BASE_PATH}/profile`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`Backend API error: ${response.status} - ${errorText}`);

      if (response.status === 401) {
        throw new Error('Authentication failed. Please sign in again.');
      }

      if (response.status === 404) {
        throw new Error('Profile not found');
      }

      throw new Error(`Failed to fetch profile: ${response.status} ${response.statusText}`);
    }

    const rawResponse = await response.json();
    const data = unwrapVBResponse<VBProfile>(rawResponse);

    // Map the data to ensure field consistency
    return {
      ...data,
      expertise_areas: data.areas_of_expertise || data.expertise_areas || [],
      full_name: data.name || data.full_name || 'Venture Builder',
    };
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('An unexpected error occurred while fetching profile');
  }
}

/**
 * Updates current user's VB profile (Requires VB authentication)
 * @param payload - Updated profile data
 * @param token - Authentication token
 * @returns Promise<VBProfile>
 */
export async function updateMyVBProfile(payload: any, token: string): Promise<VBProfile> {
  if (!API_BASE_URL) {
    throw new Error('API URL is not configured');
  }

  if (!token) {
    throw new Error('Authentication token is required');
  }

  try {
    const response = await fetch(`${API_BASE_URL}${VB_BASE_PATH}/profile`, {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`Backend API error: ${response.status} - ${errorText}`);

      if (response.status === 401) {
        throw new Error('Authentication failed. Please sign in again.');
      }

      if (response.status === 404) {
        throw new Error('Profile not found');
      }

      throw new Error(`Failed to update profile: ${response.status} ${response.statusText}`);
    }

    const rawResponse = await response.json();
    const data = unwrapVBResponse<VBProfile>(rawResponse);

    return {
      ...data,
      expertise_areas: data.areas_of_expertise || data.expertise_areas || [],
      full_name: data.name || data.full_name || 'Venture Builder',
    };
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('An unexpected error occurred while updating profile');
  }
}

/**
 * Deletes current user's VB profile (Requires VB authentication)
 * @param token - Authentication token
 * @returns Promise<void>
 */
export async function deleteMyVBProfile(token: string): Promise<void> {
  if (!API_BASE_URL) {
    throw new Error('API URL is not configured');
  }

  if (!token) {
    throw new Error('Authentication token is required');
  }

  try {
    const response = await fetch(`${API_BASE_URL}${VB_BASE_PATH}/profile`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`Backend API error: ${response.status} - ${errorText}`);

      if (response.status === 401) {
        throw new Error('Authentication failed. Please sign in again.');
      }

      if (response.status === 404) {
        throw new Error('Profile not found');
      }

      throw new Error(`Failed to delete profile: ${response.status} ${response.statusText}`);
    }
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('An unexpected error occurred while deleting profile');
  }
}

/**
 * Fetches VB's sessions (Requires VB or Admin authentication)
 * @param token - Authentication token
 * @param params - Filter parameters
 * @returns Promise<VBSession[]>
 */
export async function fetchVBSessions(
  token: string,
  params?: {
    status_filter?: string;
    start_date?: string;
    end_date?: string;
    page?: number;
    page_size?: number;
  }
): Promise<VBSession[]> {
  if (!API_BASE_URL) {
    throw new Error('API URL is not configured');
  }

  if (!token) {
    throw new Error('Authentication token is required');
  }

  try {
    const queryParams = new URLSearchParams();
    if (params?.status_filter) queryParams.append('status_filter', params.status_filter);
    if (params?.start_date) queryParams.append('start_date', params.start_date);
    if (params?.end_date) queryParams.append('end_date', params.end_date);
    if (params?.page) queryParams.append('page', params.page.toString());
    if (params?.page_size) queryParams.append('page_size', params.page_size.toString());

    const url = `${API_BASE_URL}${VB_BASE_PATH}/sessions/vb${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`Backend API error: ${response.status} - ${errorText}`);
      throw new Error(`Failed to fetch VB sessions: ${response.status} ${response.statusText}`);
    }

    const data: VBSession[] = await response.json();
    return data;
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('An unexpected error occurred while fetching VB sessions');
  }
}

/**
 * Fetches user's sessions (Requires User authentication)
 * @param token - Authentication token
 * @param params - Filter parameters
 * @returns Promise<VBSession[]>
 */
export async function fetchUserSessions(
  token: string,
  params?: {
    status_filter?: string;
    start_date?: string;
    end_date?: string;
    page?: number;
    page_size?: number;
  }
): Promise<VBSession[]> {
  if (!API_BASE_URL) {
    throw new Error('API URL is not configured');
  }

  if (!token) {
    throw new Error('Authentication token is required');
  }

  try {
    const queryParams = new URLSearchParams();
    if (params?.status_filter) queryParams.append('status_filter', params.status_filter);
    if (params?.start_date) queryParams.append('start_date', params.start_date);
    if (params?.end_date) queryParams.append('end_date', params.end_date);
    if (params?.page) queryParams.append('page', params.page.toString());
    if (params?.page_size) queryParams.append('page_size', params.page_size.toString());

    const url = `${API_BASE_URL}${VB_BASE_PATH}/sessions/user${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`Backend API error: ${response.status} - ${errorText}`);
      throw new Error(`Failed to fetch user sessions: ${response.status} ${response.statusText}`);
    }

    const data: VBSession[] = await response.json();
    return data;
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('An unexpected error occurred while fetching user sessions');
  }
}

/**
 * Marks a session as completed (Requires VB or Admin authentication)
 * @param sessionId - Session ID
 * @param token - Authentication token
 * @returns Promise<void>
 */
export async function completeSession(sessionId: string, token: string): Promise<void> {
  if (!API_BASE_URL) {
    throw new Error('API URL is not configured');
  }

  if (!sessionId) {
    throw new Error('Session ID is required');
  }

  if (!token) {
    throw new Error('Authentication token is required');
  }

  try {
    const response = await fetch(`${API_BASE_URL}${VB_BASE_PATH}/sessions/${sessionId}/complete`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`Backend API error: ${response.status} - ${errorText}`);

      if (response.status === 400) {
        throw new Error('Session not yet ended or already completed');
      }

      if (response.status === 403) {
        throw new Error('Not authorized to complete this session');
      }

      throw new Error(`Failed to complete session: ${response.status} ${response.statusText}`);
    }
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('An unexpected error occurred while completing session');
  }
}

/**
 * Cancels a session (Requires VB or Admin authentication ONLY)
 * @param sessionId - Session ID
 * @param cancellationReason - Reason for cancellation (10-500 chars)
 * @param token - Authentication token
 * @returns Promise<void>
 *
 * NOTE: API changed from DELETE to POST with required cancellation_reason
 */
export async function cancelSession(
  sessionId: string,
  cancellationReason: string,
  token: string
): Promise<void> {
  if (!API_BASE_URL) {
    throw new Error('API URL is not configured');
  }

  if (!sessionId) {
    throw new Error('Session ID is required');
  }

  if (!cancellationReason) {
    throw new Error('Cancellation reason is required');
  }

  if (!token) {
    throw new Error('Authentication token is required');
  }

  try {
    const response = await fetch(`${API_BASE_URL}${VB_BASE_PATH}/sessions/${sessionId}/cancel`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ cancellation_reason: cancellationReason }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`Backend API error: ${response.status} - ${errorText}`);

      if (response.status === 400) {
        throw new Error('Session already started or completed, or invalid cancellation reason');
      }

      if (response.status === 403) {
        throw new Error('Only the venture builder or admin can cancel a session');
      }

      throw new Error(`Failed to cancel session: ${response.status} ${response.statusText}`);
    }
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('An unexpected error occurred while canceling session');
  }
}

/**
 * ==============================================================================
 * SESSION NOTES
 * ==============================================================================
 */

/**
 * Creates a session note (VB only)
 * @param payload - Note data
 * @param token - Authentication token
 * @returns Promise<SessionNote>
 */
export async function createSessionNote(payload: CreateSessionNotePayload, token: string): Promise<SessionNote> {
  if (!API_BASE_URL) throw new Error('API URL is not configured');
  if (!token) throw new Error('Authentication token is required');

  try {
    const response = await fetch(`${API_BASE_URL}${VB_BASE_PATH}/notes`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to create session note: ${response.status} ${errorText}`);
    }

    const rawResponse = await response.json();
    return unwrapVBResponse(rawResponse);
  } catch (error) {
    if (error instanceof Error) throw error;
    throw new Error('An unexpected error occurred while creating session note');
  }
}

/**
 * Updates a session note (VB only)
 * @param noteId - Note ID
 * @param payload - Updated note data
 * @param token - Authentication token
 * @returns Promise<SessionNote>
 */
export async function updateSessionNote(noteId: string, payload: UpdateSessionNotePayload, token: string): Promise<SessionNote> {
  if (!API_BASE_URL) throw new Error('API URL is not configured');
  if (!noteId) throw new Error('Note ID is required');
  if (!token) throw new Error('Authentication token is required');

  try {
    const response = await fetch(`${API_BASE_URL}${VB_BASE_PATH}/notes/${noteId}`, {
      method: 'PATCH',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to update session note: ${response.status} ${errorText}`);
    }

    const rawResponse = await response.json();
    return unwrapVBResponse(rawResponse);
  } catch (error) {
    if (error instanceof Error) throw error;
    throw new Error('An unexpected error occurred while updating session note');
  }
}

/**
 * Gets session note for a specific session (User)
 * @param sessionId - Session ID
 * @param token - Authentication token
 * @returns Promise<SessionNote | null>
 */
export async function getSessionNoteForUser(sessionId: string, token: string): Promise<SessionNote | null> {
  if (!API_BASE_URL) throw new Error('API URL is not configured');
  if (!sessionId) throw new Error('Session ID is required');
  if (!token) throw new Error('Authentication token is required');

  try {
    const response = await fetch(`${API_BASE_URL}${VB_BASE_PATH}/notes/session/${sessionId}/user`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    if (response.status === 404) return null;

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to get session note: ${response.status} ${errorText}`);
    }

    const rawResponse = await response.json();
    return unwrapVBResponse(rawResponse);
  } catch (error) {
    if (error instanceof Error) throw error;
    throw new Error('An unexpected error occurred while getting session note');
  }
}

/**
 * Gets session note for a specific session (VB)
 * @param sessionId - Session ID
 * @param token - Authentication token
 * @returns Promise<SessionNote | null>
 */
export async function getSessionNoteForVB(sessionId: string, token: string): Promise<SessionNote | null> {
  if (!API_BASE_URL) throw new Error('API URL is not configured');
  if (!sessionId) throw new Error('Session ID is required');
  if (!token) throw new Error('Authentication token is required');

  try {
    const response = await fetch(`${API_BASE_URL}${VB_BASE_PATH}/notes/session/${sessionId}/vb`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    if (response.status === 404) return null;

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to get session note: ${response.status} ${errorText}`);
    }

    const rawResponse = await response.json();
    return unwrapVBResponse(rawResponse);
  } catch (error) {
    if (error instanceof Error) throw error;
    throw new Error('An unexpected error occurred while getting session note');
  }
}

/**
 * ==============================================================================
 * EARNINGS
 * ==============================================================================
 */

/**
 * Gets VB's earnings (VB or Admin)
 * @param token - Authentication token
 * @param params - Filter parameters
 * @returns Promise<EarningsResponse>
 */
export async function getMyEarnings(token: string, params?: GetEarningsParams): Promise<EarningsResponse> {
  if (!API_BASE_URL) throw new Error('API URL is not configured');
  if (!token) throw new Error('Authentication token is required');

  try {
    const queryParams = new URLSearchParams();
    if (params?.start_date) queryParams.append('start_date', params.start_date);
    if (params?.end_date) queryParams.append('end_date', params.end_date);

    const url = `${API_BASE_URL}${VB_BASE_PATH}/earnings${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to get earnings: ${response.status} ${errorText}`);
    }

    const rawResponse = await response.json();
    console.log('getMyEarnings - Raw API response:', rawResponse);

    // Try unwrapping first, if it fails return as-is
    try {
      return unwrapVBResponse(rawResponse);
    } catch {
      // Backend returns direct response, not wrapped
      return rawResponse as EarningsResponse;
    }
  } catch (error) {
    if (error instanceof Error) throw error;
    throw new Error('An unexpected error occurred while getting earnings');
  }
}

/**
 * Gets earnings config (Admin)
 * @param token - Authentication token
 * @returns Promise<EarningsConfig>
 */
export async function getEarningsConfig(token: string): Promise<EarningsConfig> {
  if (!API_BASE_URL) throw new Error('API URL is not configured');
  if (!token) throw new Error('Authentication token is required');

  try {
    const response = await fetch(`${API_BASE_URL}${VB_BASE_PATH}/admin/earnings/config`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to get earnings config: ${response.status} ${errorText}`);
    }

    const rawResponse = await response.json();
    return unwrapVBResponse(rawResponse);
  } catch (error) {
    if (error instanceof Error) throw error;
    throw new Error('An unexpected error occurred while getting earnings config');
  }
}

/**
 * Updates earnings config (Admin)
 * @param payload - Updated config
 * @param token - Authentication token
 * @returns Promise<EarningsConfig>
 */
export async function updateEarningsConfig(payload: UpdateEarningsConfigPayload, token: string): Promise<EarningsConfig> {
  if (!API_BASE_URL) throw new Error('API URL is not configured');
  if (!token) throw new Error('Authentication token is required');

  try {
    const response = await fetch(`${API_BASE_URL}${VB_BASE_PATH}/admin/earnings/config`, {
      method: 'PATCH',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to update earnings config: ${response.status} ${errorText}`);
    }

    const rawResponse = await response.json();
    return unwrapVBResponse(rawResponse);
  } catch (error) {
    if (error instanceof Error) throw error;
    throw new Error('An unexpected error occurred while updating earnings config');
  }
}

/**
 * ==============================================================================
 * RECONCILIATION (Admin)
 * ==============================================================================
 */

/**
 * Reconciles VB payments (Admin)
 * @param vbId - Venture Builder ID
 * @param payload - Reconciliation data
 * @param token - Authentication token
 * @returns Promise<ReconcileResponse>
 */
export async function reconcileVBPayments(vbId: string, payload: ReconcilePayload, token: string): Promise<ReconcileResponse> {
  if (!API_BASE_URL) throw new Error('API URL is not configured');
  if (!vbId) throw new Error('VB ID is required');
  if (!token) throw new Error('Authentication token is required');

  try {
    const response = await fetch(`${API_BASE_URL}${VB_BASE_PATH}/admin/vb/${vbId}/reconcile`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to reconcile payments: ${response.status} ${errorText}`);
    }

    const rawResponse = await response.json();
    return unwrapVBResponse(rawResponse);
  } catch (error) {
    if (error instanceof Error) throw error;
    throw new Error('An unexpected error occurred while reconciling payments');
  }
}

/**
 * Gets VB reconciliation history (Admin)
 * @param vbId - Venture Builder ID
 * @param token - Authentication token
 * @param page - Page number
 * @param pageSize - Items per page
 * @returns Promise<ReconciliationHistoryResponse>
 */
export async function getVBReconciliationHistory(
  vbId: string,
  token: string,
  page: number = 1,
  pageSize: number = 20
): Promise<ReconciliationHistoryResponse> {
  if (!API_BASE_URL) throw new Error('API URL is not configured');
  if (!vbId) throw new Error('VB ID is required');
  if (!token) throw new Error('Authentication token is required');

  try {
    const queryParams = new URLSearchParams();
    queryParams.append('page', page.toString());
    queryParams.append('page_size', pageSize.toString());

    const response = await fetch(`${API_BASE_URL}${VB_BASE_PATH}/admin/vb/${vbId}/reconciliations?${queryParams.toString()}`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to get reconciliation history: ${response.status} ${errorText}`);
    }

    const rawResponse = await response.json();
    return unwrapVBResponse(rawResponse);
  } catch (error) {
    if (error instanceof Error) throw error;
    throw new Error('An unexpected error occurred while getting reconciliation history');
  }
}

/**
 * Gets all reconciliations (Admin)
 * @param token - Authentication token
 * @param page - Page number
 * @param pageSize - Items per page
 * @returns Promise<ReconciliationHistoryResponse>
 */
export async function getAllReconciliations(
  token: string,
  page: number = 1,
  pageSize: number = 20
): Promise<ReconciliationHistoryResponse> {
  if (!API_BASE_URL) throw new Error('API URL is not configured');
  if (!token) throw new Error('Authentication token is required');

  try {
    const queryParams = new URLSearchParams();
    queryParams.append('page', page.toString());
    queryParams.append('page_size', pageSize.toString());

    const response = await fetch(`${API_BASE_URL}${VB_BASE_PATH}/admin/reconciliations?${queryParams.toString()}`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to get reconciliations: ${response.status} ${errorText}`);
    }

    const rawResponse = await response.json();
    return unwrapVBResponse(rawResponse);
  } catch (error) {
    if (error instanceof Error) throw error;
    throw new Error('An unexpected error occurred while getting reconciliations');
  }
}

/**
 * ==============================================================================
 * DISPUTES
 * ==============================================================================
 */

/**
 * Checks if user can open a dispute for a session
 * @param sessionId - Session ID
 * @param token - Authentication token
 * @returns Promise<CanOpenDisputeResponse>
 */
export async function canOpenDispute(sessionId: string, token: string): Promise<CanOpenDisputeResponse> {
  if (!API_BASE_URL) throw new Error('API URL is not configured');
  if (!sessionId) throw new Error('Session ID is required');
  if (!token) throw new Error('Authentication token is required');

  try {
    const response = await fetch(`${API_BASE_URL}${VB_BASE_PATH}/sessions/${sessionId}/can-dispute`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to check dispute eligibility: ${response.status} ${errorText}`);
    }

    const rawResponse = await response.json();
    return unwrapVBResponse(rawResponse);
  } catch (error) {
    if (error instanceof Error) throw error;
    throw new Error('An unexpected error occurred while checking dispute eligibility');
  }
}

/**
 * Creates a dispute for a session (User)
 * @param sessionId - Session ID
 * @param payload - Dispute data
 * @param token - Authentication token
 * @returns Promise<Dispute>
 */
export async function createDispute(sessionId: string, payload: CreateDisputePayload, token: string): Promise<Dispute> {
  if (!API_BASE_URL) throw new Error('API URL is not configured');
  if (!sessionId) throw new Error('Session ID is required');
  if (!token) throw new Error('Authentication token is required');

  try {
    const response = await fetch(`${API_BASE_URL}${VB_BASE_PATH}/sessions/${sessionId}/disputes`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to create dispute: ${response.status} ${errorText}`);
    }

    const rawResponse = await response.json();
    return unwrapVBResponse(rawResponse);
  } catch (error) {
    if (error instanceof Error) throw error;
    throw new Error('An unexpected error occurred while creating dispute');
  }
}

/**
 * Gets user's disputes (User)
 * @param token - Authentication token
 * @param params - Filter parameters
 * @returns Promise<GetDisputesResponse>
 */
export async function getMyDisputes(token: string, params?: GetDisputesParams): Promise<GetDisputesResponse> {
  if (!API_BASE_URL) throw new Error('API URL is not configured');
  if (!token) throw new Error('Authentication token is required');

  try {
    const queryParams = new URLSearchParams();
    if (params?.page) queryParams.append('page', params.page.toString());
    if (params?.page_size) queryParams.append('page_size', params.page_size.toString());

    const url = `${API_BASE_URL}${VB_BASE_PATH}/disputes${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to get disputes: ${response.status} ${errorText}`);
    }

    const rawResponse = await response.json();
    return unwrapVBResponse(rawResponse);
  } catch (error) {
    if (error instanceof Error) throw error;
    throw new Error('An unexpected error occurred while getting disputes');
  }
}

/**
 * Gets dispute details (User)
 * @param disputeId - Dispute ID
 * @param token - Authentication token
 * @returns Promise<Dispute>
 */
export async function getDisputeDetail(disputeId: string, token: string): Promise<Dispute> {
  if (!API_BASE_URL) throw new Error('API URL is not configured');
  if (!disputeId) throw new Error('Dispute ID is required');
  if (!token) throw new Error('Authentication token is required');

  try {
    const response = await fetch(`${API_BASE_URL}${VB_BASE_PATH}/disputes/${disputeId}`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to get dispute: ${response.status} ${errorText}`);
    }

    const rawResponse = await response.json();
    return unwrapVBResponse(rawResponse);
  } catch (error) {
    if (error instanceof Error) throw error;
    throw new Error('An unexpected error occurred while getting dispute');
  }
}

/**
 * Gets all disputes (Admin)
 * @param token - Authentication token
 * @param params - Filter parameters
 * @returns Promise<GetDisputesResponse>
 */
export async function getAllDisputes(token: string, params?: GetAdminDisputesParams): Promise<GetDisputesResponse> {
  if (!API_BASE_URL) throw new Error('API URL is not configured');
  if (!token) throw new Error('Authentication token is required');

  try {
    const queryParams = new URLSearchParams();
    if (params?.status) queryParams.append('status', params.status);
    if (params?.vb_id) queryParams.append('vb_id', params.vb_id);
    if (params?.start_date) queryParams.append('start_date', params.start_date);
    if (params?.end_date) queryParams.append('end_date', params.end_date);
    if (params?.page) queryParams.append('page', params.page.toString());
    if (params?.page_size) queryParams.append('page_size', params.page_size.toString());

    const url = `${API_BASE_URL}${VB_BASE_PATH}/admin/disputes${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to get disputes: ${response.status} ${errorText}`);
    }

    const rawResponse = await response.json();
    return unwrapVBResponse(rawResponse);
  } catch (error) {
    if (error instanceof Error) throw error;
    throw new Error('An unexpected error occurred while getting disputes');
  }
}

/**
 * Updates a dispute (Admin)
 * @param disputeId - Dispute ID
 * @param payload - Update data
 * @param token - Authentication token
 * @returns Promise<Dispute>
 */
export async function updateDispute(disputeId: string, payload: UpdateDisputePayload, token: string): Promise<Dispute> {
  if (!API_BASE_URL) throw new Error('API URL is not configured');
  if (!disputeId) throw new Error('Dispute ID is required');
  if (!token) throw new Error('Authentication token is required');

  try {
    const response = await fetch(`${API_BASE_URL}${VB_BASE_PATH}/admin/disputes/${disputeId}`, {
      method: 'PATCH',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to update dispute: ${response.status} ${errorText}`);
    }

    const rawResponse = await response.json();
    return unwrapVBResponse(rawResponse);
  } catch (error) {
    if (error instanceof Error) throw error;
    throw new Error('An unexpected error occurred while updating dispute');
  }
}

/**
 * ==============================================================================
 * VB PORTAL - PROJECTS
 * ==============================================================================
 */

/**
 * Gets VB accessible projects (VB)
 * @param token - Authentication token
 * @returns Promise<VBProject[]>
 */
export async function getVBProjects(token: string): Promise<VBProject[]> {
  if (!API_BASE_URL) throw new Error('API URL is not configured');
  if (!token) throw new Error('Authentication token is required');

  try {
    const response = await fetch(`${API_BASE_URL}${VB_BASE_PATH}/portal/projects`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to get projects: ${response.status} ${errorText}`);
    }

    const rawResponse = await response.json();
    return unwrapVBResponse(rawResponse);
  } catch (error) {
    if (error instanceof Error) throw error;
    throw new Error('An unexpected error occurred while getting projects');
  }
}

/**
 * ==============================================================================
 * ADMIN - EXPERTISE MANAGEMENT
 * ==============================================================================
 */

/**
 * Gets all expertise areas (Admin)
 * @param token - Authentication token
 * @param includeInactive - Include inactive areas
 * @returns Promise<ExpertiseArea[]>
 */
export async function getAllExpertiseAreasAdmin(token: string, includeInactive: boolean = false): Promise<ExpertiseArea[]> {
  if (!API_BASE_URL) throw new Error('API URL is not configured');
  if (!token) throw new Error('Authentication token is required');

  try {
    const queryParams = new URLSearchParams();
    if (includeInactive) queryParams.append('include_inactive', 'true');

    const url = `${API_BASE_URL}${VB_BASE_PATH}/admin/expertise${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to get expertise areas: ${response.status} ${errorText}`);
    }

    const rawResponse = await response.json();
    return unwrapVBResponse(rawResponse);
  } catch (error) {
    if (error instanceof Error) throw error;
    throw new Error('An unexpected error occurred while getting expertise areas');
  }
}

/**
 * Creates expertise area (Admin)
 * @param payload - Expertise area data
 * @param token - Authentication token
 * @returns Promise<ExpertiseArea>
 */
export async function createExpertiseArea(payload: CreateExpertiseAreaPayload, token: string): Promise<ExpertiseArea> {
  if (!API_BASE_URL) throw new Error('API URL is not configured');
  if (!token) throw new Error('Authentication token is required');

  try {
    const response = await fetch(`${API_BASE_URL}${VB_BASE_PATH}/admin/expertise`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to create expertise area: ${response.status} ${errorText}`);
    }

    const rawResponse = await response.json();
    return unwrapVBResponse(rawResponse);
  } catch (error) {
    if (error instanceof Error) throw error;
    throw new Error('An unexpected error occurred while creating expertise area');
  }
}

/**
 * Updates expertise area (Admin)
 * @param expertiseId - Expertise area ID
 * @param payload - Update data
 * @param token - Authentication token
 * @returns Promise<ExpertiseArea>
 */
export async function updateExpertiseArea(expertiseId: string, payload: UpdateExpertiseAreaPayload, token: string): Promise<ExpertiseArea> {
  if (!API_BASE_URL) throw new Error('API URL is not configured');
  if (!expertiseId) throw new Error('Expertise ID is required');
  if (!token) throw new Error('Authentication token is required');

  try {
    const response = await fetch(`${API_BASE_URL}${VB_BASE_PATH}/admin/expertise/${expertiseId}`, {
      method: 'PATCH',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to update expertise area: ${response.status} ${errorText}`);
    }

    const rawResponse = await response.json();
    return unwrapVBResponse(rawResponse);
  } catch (error) {
    if (error instanceof Error) throw error;
    throw new Error('An unexpected error occurred while updating expertise area');
  }
}

/**
 * Deletes expertise area (Super Admin)
 * @param expertiseId - Expertise area ID
 * @param token - Authentication token
 * @returns Promise<void>
 */
export async function deleteExpertiseArea(expertiseId: string, token: string): Promise<void> {
  if (!API_BASE_URL) throw new Error('API URL is not configured');
  if (!expertiseId) throw new Error('Expertise ID is required');
  if (!token) throw new Error('Authentication token is required');

  try {
    const response = await fetch(`${API_BASE_URL}${VB_BASE_PATH}/admin/expertise/${expertiseId}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to delete expertise area: ${response.status} ${errorText}`);
    }
  } catch (error) {
    if (error instanceof Error) throw error;
    throw new Error('An unexpected error occurred while deleting expertise area');
  }
}

/**
 * Fetches user's coaching sessions (sessions they booked as a founder)
 * @param token - Authentication token
 * @param params - Filter parameters
 * @returns Promise<VBSession[]>
 */
export async function getUserSessions(
  token: string,
  params?: {
    status_filter?: string;
    start_date?: string;
    end_date?: string;
    page?: number;
    page_size?: number;
  }
): Promise<VBSession[]> {
  if (!API_BASE_URL) {
    throw new Error('API URL is not configured');
  }

  if (!token) {
    throw new Error('Authentication token is required');
  }

  try {
    const queryParams = new URLSearchParams();
    if (params?.status_filter) queryParams.append('status_filter', params.status_filter);
    if (params?.start_date) queryParams.append('start_date', params.start_date);
    if (params?.end_date) queryParams.append('end_date', params.end_date);
    if (params?.page) queryParams.append('page', params.page.toString());
    if (params?.page_size) queryParams.append('page_size', params.page_size.toString());

    const url = `${API_BASE_URL}${VB_BASE_PATH}/sessions/user${queryParams.toString() ? '?' + queryParams.toString() : ''}`;

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`Backend API error: ${response.status} - ${errorText}`);

      if (response.status === 401) {
        throw new Error('Authentication failed. Please sign in again.');
      }

      if (response.status === 404) {
        return []; // No sessions found
      }

      throw new Error(`Failed to fetch user sessions: ${response.status} ${response.statusText}`);
    }

    const rawResponse = await response.json();
    const data = unwrapVBResponse<VBSession[]>(rawResponse);
    return data;
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('An unexpected error occurred while fetching user sessions');
  }
}

/**
 * Fetches VB's coaching sessions (sessions where they are the coach)
 * @param token - Authentication token
 * @param params - Filter parameters
 * @returns Promise<VBSession[]>
 */
export async function getVBSessions(
  token: string,
  params?: {
    status_filter?: string;
    start_date?: string;
    end_date?: string;
    page?: number;
    page_size?: number;
  }
): Promise<VBSession[]> {
  if (!API_BASE_URL) {
    throw new Error('API URL is not configured');
  }

  if (!token) {
    throw new Error('Authentication token is required');
  }

  try {
    const queryParams = new URLSearchParams();
    if (params?.status_filter) queryParams.append('status_filter', params.status_filter);
    if (params?.start_date) queryParams.append('start_date', params.start_date);
    if (params?.end_date) queryParams.append('end_date', params.end_date);
    if (params?.page) queryParams.append('page', params.page.toString());
    if (params?.page_size) queryParams.append('page_size', params.page_size.toString());

    const url = `${API_BASE_URL}${VB_BASE_PATH}/sessions/vb${queryParams.toString() ? '?' + queryParams.toString() : ''}`;

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`Backend API error: ${response.status} - ${errorText}`);

      if (response.status === 401) {
        throw new Error('Authentication failed. Please sign in again.');
      }

      if (response.status === 404) {
        return []; // No sessions found
      }

      throw new Error(`Failed to fetch VB sessions: ${response.status} ${response.statusText}`);
    }

    const rawResponse = await response.json();
    const data = unwrapVBResponse<VBSession[]>(rawResponse);
    return data;
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('An unexpected error occurred while fetching VB sessions');
  }
}

/**
 * Type exports
 */
export type {
  VBProfile,
  TenantProject,
  CheckCreditsResponse,
  VBSession,
  SessionNote,
  CreateSessionNotePayload,
  UpdateSessionNotePayload,
  EarningsResponse,
  EarningsConfig,
  UpdateEarningsConfigPayload,
  ReconcilePayload,
  ReconcileResponse,
  ReconciliationHistoryResponse,
  Dispute,
  CreateDisputePayload,
  GetDisputesResponse,
  GetAdminDisputesParams,
  UpdateDisputePayload,
  VBProject,
  ExpertiseArea,
  CreateExpertiseAreaPayload,
  UpdateExpertiseAreaPayload,
};
