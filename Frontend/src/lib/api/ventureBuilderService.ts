// lib/api/ventureBuilderService.ts
/**
 * Venture Builder API Service
 *
 * This service handles all API calls for the Venture Builder feature:
 * - VB profile management
 * - Booking sessions
 * - Session management
 * - Coaching notes
 * - Earnings
 * - Disputes
 *
 * Base API: /api/venture-builder
 */

import { authService } from '@/services/authService';
import type {
  // Expertise
  ExpertiseArea,
  CreateExpertiseAreaPayload,
  UpdateExpertiseAreaPayload,
  // VB Profile
  VBProfile,
  CreateVBProfilePayload,
  UpdateVBProfilePayload,
  ApproveVBPayload,
  UpdateVBPricingPayload,
  PublishVBPayload,
  // Browse
  BrowseVBsParams,
  BrowseVBsResponse,
  // Invitations
  SendVBInvitationPayload,
  SendVBInvitationResponse,
  ValidateInvitationPayload,
  ValidateInvitationResponse,
  // Booking
  TenantProject,
  CheckCreditsResponse,
  CreateBookingPayload,
  // Sessions
  VBSession,
  GetSessionsParams,
  // Notes
  SessionNote,
  CreateSessionNotePayload,
  UpdateSessionNotePayload,
  // Earnings
  EarningsResponse,
  GetEarningsParams,
  EarningsConfig,
  UpdateEarningsConfigPayload,
  // Disputes
  Dispute,
  CanOpenDisputeResponse,
  CreateDisputePayload,
  GetDisputesParams,
  GetDisputesResponse,
  GetAdminDisputesParams,
  UpdateDisputePayload,
  // Google Calendar
  GoogleCalendarConnection,
  GoogleCalendarList,
  ConnectCalendarResponse,
  SelectCalendarPayload,
  DisconnectCalendarResponse,
  // Availability (New API)
  AvailabilitySlot,
  CreateAvailabilitySlotsPayload,
  DeleteAvailabilitySlotsPayload,
  GetAvailabilityParams,
  GetAvailabilityResponse,
  // Legacy (deprecated)
  AvailabilityProfile,
  UpdateAvailabilityProfilePayload,
  // Reschedule
  RescheduleSessionPayload,
  RescheduleSessionResponse,
  ValidateRescheduleTokenResponse,
  RescheduleBookPayload,
  RescheduleBookResponse,
} from '@/types/ventureBuilder';

// ============================================================================
// CONFIGURATION
// ============================================================================

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL;
const VB_BASE_PATH = '/venture-builder';

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
    Authorization: `Bearer ${getAuthToken()}`,
  };
};

/**
 * Get public headers (no auth)
 */
const getPublicHeaders = (): HeadersInit => {
  return {
    'Content-Type': 'application/json',
  };
};

/**
 * Standardized API response wrapper
 */
interface VBApiResponse<T> {
  success: boolean;
  data: T | null;
  error: string | null;
}

/**
 * Handle API errors consistently
 * Updated to handle new standardized response format: {success, data, error}
 */
const handleApiError = async (response: Response): Promise<never> => {
  let errorMessage = `Request failed with status ${response.status}`;

  try {
    const errorData = await response.json();
    console.error('VB API Error Response:', errorData);

    // Handle new standardized format {success: false, data: null, error: "message"}
    if (errorData.error && typeof errorData.error === 'string') {
      errorMessage = errorData.error;
    }
    // Handle FastAPI validation errors (legacy)
    else if (errorData.detail && Array.isArray(errorData.detail)) {
      const validationErrors = errorData.detail
        .map((err: any) => {
          const location = err.loc ? err.loc.join(' -> ') : 'unknown';
          return `${location}: ${err.msg}`;
        })
        .join('\n');
      errorMessage = `Validation Error:\n${validationErrors}`;
    } else if (errorData.detail) {
      errorMessage =
        typeof errorData.detail === 'string'
          ? errorData.detail
          : JSON.stringify(errorData.detail);
    } else if (errorData.message) {
      errorMessage = errorData.message;
    }
  } catch {
    // If response is not JSON, use status text
    errorMessage = response.statusText || errorMessage;
  }

  throw new Error(errorMessage);
};

/**
 * Unwrap standardized API response
 */
const unwrapResponse = async <T>(response: Response): Promise<T> => {
  const jsonData: VBApiResponse<T> = await response.json();

  // If response has the new standardized format
  if ('success' in jsonData && 'data' in jsonData) {
    if (jsonData.success && jsonData.data !== null) {
      return jsonData.data;
    }
  }

  // Otherwise return as-is (backward compatibility)
  return jsonData as unknown as T;
};

// ============================================================================
// INVITATIONS
// ============================================================================

export const invitationsAPI = {
  /**
   * Send VB invitation (Admin only)
   * POST /venture-builder/admin/invite
   */
  sendInvitation: async (
    payload: SendVBInvitationPayload
  ): Promise<SendVBInvitationResponse> => {
    const response = await fetch(`${API_BASE_URL}${VB_BASE_PATH}/admin/invite`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      await handleApiError(response);
    }

    return unwrapResponse(response);
  },
};

// ============================================================================
// EXPERTISE AREAS
// ============================================================================

export const expertiseAPI = {
  /**
   * List active expertise areas (Public)
   */
  listActive: async (): Promise<ExpertiseArea[]> => {
    const response = await fetch(`${API_BASE_URL}${VB_BASE_PATH}/expertise`, {
      method: 'GET',
      headers: getPublicHeaders(),
    });

    if (!response.ok) {
      await handleApiError(response);
    }

    return unwrapResponse(response);
  },

  /**
   * List all expertise areas (Admin only)
   */
  listAll: async (includeInactive = false): Promise<ExpertiseArea[]> => {
    const params = new URLSearchParams();
    if (includeInactive) {
      params.append('include_inactive', 'true');
    }

    const response = await fetch(
      `${API_BASE_URL}${VB_BASE_PATH}/admin/expertise?${params}`,
      {
        method: 'GET',
        headers: getAuthHeaders(),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    return unwrapResponse(response);
  },

  /**
   * Create expertise area (Admin only)
   */
  create: async (payload: CreateExpertiseAreaPayload): Promise<ExpertiseArea> => {
    const response = await fetch(`${API_BASE_URL}${VB_BASE_PATH}/admin/expertise`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      await handleApiError(response);
    }

    return unwrapResponse(response);
  },

  /**
   * Update expertise area (Admin only)
   */
  update: async (
    expertiseId: string,
    payload: UpdateExpertiseAreaPayload
  ): Promise<ExpertiseArea> => {
    const response = await fetch(
      `${API_BASE_URL}${VB_BASE_PATH}/admin/expertise/${expertiseId}`,
      {
        method: 'PATCH',
        headers: getAuthHeaders(),
        body: JSON.stringify(payload),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    return unwrapResponse(response);
  },

  /**
   * Delete expertise area (Super Admin only)
   */
  delete: async (expertiseId: string): Promise<void> => {
    const response = await fetch(
      `${API_BASE_URL}${VB_BASE_PATH}/admin/expertise/${expertiseId}`,
      {
        method: 'DELETE',
        headers: getAuthHeaders(),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }
  },
};

// ============================================================================
// VB PROFILE MANAGEMENT
// ============================================================================

export const profileAPI = {
  /**
   * Create VB profile (requires invitation token)
   */
  create: async (
    payload: CreateVBProfilePayload,
    invitationToken: string
  ): Promise<VBProfile> => {
    const params = new URLSearchParams({ invitation_token: invitationToken });

    const response = await fetch(
      `${API_BASE_URL}${VB_BASE_PATH}/profile/create?${params}`,
      {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(payload),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    return unwrapResponse(response);
  },

  /**
   * Get my VB profile (VB or Admin)
   */
  getMyProfile: async (): Promise<VBProfile> => {
    const response = await fetch(`${API_BASE_URL}${VB_BASE_PATH}/profile`, {
      method: 'GET',
      headers: getAuthHeaders(),
    });

    if (!response.ok) {
      await handleApiError(response);
    }

    return unwrapResponse(response);
  },

  /**
   * Update VB profile (VB or Admin)
   */
  update: async (payload: UpdateVBProfilePayload): Promise<VBProfile> => {
    const response = await fetch(`${API_BASE_URL}${VB_BASE_PATH}/profile`, {
      method: 'PATCH',
      headers: getAuthHeaders(),
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      await handleApiError(response);
    }

    return unwrapResponse(response);
  },

  /**
   * Delete VB profile (VB or Super Admin)
   */
  delete: async (): Promise<void> => {
    const response = await fetch(`${API_BASE_URL}${VB_BASE_PATH}/profile`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });

    if (!response.ok) {
      await handleApiError(response);
    }
  },
};

// ============================================================================
// BROWSE VBS
// ============================================================================

export const browseAPI = {
  /**
   * Browse Venture Builders (Public)
   */
  list: async (params: BrowseVBsParams = {}): Promise<BrowseVBsResponse> => {
    const searchParams = new URLSearchParams();

    if (params.expertise_ids && params.expertise_ids.length > 0) {
      params.expertise_ids.forEach((id) => searchParams.append('expertise_ids', id));
    }
    if (params.search_query) {
      searchParams.append('search_query', params.search_query);
    }
    if (params.page) {
      searchParams.append('page', params.page.toString());
    }
    if (params.page_size) {
      searchParams.append('page_size', params.page_size.toString());
    }

    const response = await fetch(
      `${API_BASE_URL}${VB_BASE_PATH}/browse?${searchParams}`,
      {
        method: 'GET',
        headers: getPublicHeaders(),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    return unwrapResponse(response);
  },

  /**
   * Get VB details (Public)
   */
  getDetails: async (vbId: string): Promise<VBProfile> => {
    const response = await fetch(`${API_BASE_URL}${VB_BASE_PATH}/browse/${vbId}`, {
      method: 'GET',
      headers: getPublicHeaders(),
    });

    if (!response.ok) {
      await handleApiError(response);
    }

    return unwrapResponse(response);
  },
};

// ============================================================================
// ADMIN VB MANAGEMENT
// ============================================================================

export const adminAPI = {
  /**
   * List all VB profiles (Admin only)
   * GET /venture-builder/admin/vb
   */
  listVBs: async (params?: {
    status?: string;
    page?: number;
    page_size?: number;
  }): Promise<BrowseVBsResponse> => {
    const searchParams = new URLSearchParams();

    if (params?.status) {
      searchParams.append('status', params.status);
    }
    if (params?.page) {
      searchParams.append('page', params.page.toString());
    }
    if (params?.page_size) {
      searchParams.append('page_size', params.page_size.toString());
    }

    const response = await fetch(
      `${API_BASE_URL}${VB_BASE_PATH}/admin/vb?${searchParams}`,
      {
        method: 'GET',
        headers: getAuthHeaders(),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    return unwrapResponse(response);
  },

  /**
   * List pending VB profiles (Admin only)
   * GET /venture-builder/admin/vb/pending
   */
  listPendingVBs: async (): Promise<VBProfile[]> => {
    const response = await fetch(
      `${API_BASE_URL}${VB_BASE_PATH}/admin/vb/pending`,
      {
        method: 'GET',
        headers: getAuthHeaders(),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    return unwrapResponse(response);
  },

  /**
   * Get VB profile by ID (Admin only)
   * GET /venture-builder/admin/vb/{vb_id}
   */
  getVB: async (vbId: string): Promise<VBProfile> => {
    const response = await fetch(
      `${API_BASE_URL}${VB_BASE_PATH}/admin/vb/${vbId}`,
      {
        method: 'GET',
        headers: getAuthHeaders(),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    return unwrapResponse(response);
  },

  /**
   * Approve VB (Admin only)
   * POST /venture-builder/admin/vb/{vb_id}/approve
   */
  approveVB: async (vbId: string, payload: ApproveVBPayload): Promise<VBProfile> => {
    const response = await fetch(
      `${API_BASE_URL}${VB_BASE_PATH}/admin/vb/${vbId}/approve`,
      {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(payload),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    return unwrapResponse(response);
  },

  /**
   * Update VB pricing (Admin only)
   * PATCH /venture-builder/admin/vb/{vb_id}/pricing
   */
  updatePricing: async (
    vbId: string,
    payload: UpdateVBPricingPayload
  ): Promise<VBProfile> => {
    const response = await fetch(
      `${API_BASE_URL}${VB_BASE_PATH}/admin/vb/${vbId}/pricing`,
      {
        method: 'PATCH',
        headers: getAuthHeaders(),
        body: JSON.stringify(payload),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    return unwrapResponse(response);
  },

  /**
   * Publish/Unpublish VB (Admin only)
   * PATCH /venture-builder/admin/vb/{vb_id}/publish
   */
  publishVB: async (vbId: string, payload: PublishVBPayload): Promise<VBProfile> => {
    const response = await fetch(
      `${API_BASE_URL}${VB_BASE_PATH}/admin/vb/${vbId}/publish`,
      {
        method: 'PATCH',
        headers: getAuthHeaders(),
        body: JSON.stringify(payload),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    return unwrapResponse(response);
  },
};

// ============================================================================
// BOOKING
// ============================================================================

export const bookingAPI = {
  /**
   * Get tenant projects
   */
  getProjects: async (): Promise<TenantProject[]> => {
    const response = await fetch(
      `${API_BASE_URL}${VB_BASE_PATH}/booking/projects`,
      {
        method: 'GET',
        headers: getAuthHeaders(),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    return unwrapResponse(response);
  },

  /**
   * Check booking credits
   */
  checkCredits: async (vbId: string): Promise<CheckCreditsResponse> => {
    const response = await fetch(
      `${API_BASE_URL}${VB_BASE_PATH}/booking/credits/${vbId}`,
      {
        method: 'GET',
        headers: getAuthHeaders(),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    return unwrapResponse(response);
  },

  /**
   * Create booking
   */
  createBooking: async (payload: CreateBookingPayload): Promise<VBSession> => {
    const response = await fetch(`${API_BASE_URL}${VB_BASE_PATH}/booking`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      await handleApiError(response);
    }

    return unwrapResponse(response);
  },
};

// ============================================================================
// SESSIONS
// ============================================================================

export const sessionsAPI = {
  /**
   * Get VB sessions (VB Portal)
   * GET /venture-builder/sessions/vb
   */
  getVBSessions: async (params: GetSessionsParams = {}): Promise<VBSession[]> => {
    const searchParams = new URLSearchParams();

    if (params.status_filter) {
      searchParams.append('status_filter', params.status_filter);
    }
    if (params.start_date) {
      searchParams.append('start_date', params.start_date);
    }
    if (params.end_date) {
      searchParams.append('end_date', params.end_date);
    }
    if (params.page) {
      searchParams.append('page', params.page.toString());
    }
    if (params.page_size) {
      searchParams.append('page_size', params.page_size.toString());
    }

    const response = await fetch(
      `${API_BASE_URL}${VB_BASE_PATH}/sessions/vb?${searchParams}`,
      {
        method: 'GET',
        headers: getAuthHeaders(),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    return unwrapResponse(response);
  },

  /**
   * Get user sessions
   * GET /venture-builder/sessions/user
   */
  getUserSessions: async (params: GetSessionsParams = {}): Promise<VBSession[]> => {
    const searchParams = new URLSearchParams();

    if (params.status_filter) {
      searchParams.append('status_filter', params.status_filter);
    }
    if (params.start_date) {
      searchParams.append('start_date', params.start_date);
    }
    if (params.end_date) {
      searchParams.append('end_date', params.end_date);
    }
    if (params.page) {
      searchParams.append('page', params.page.toString());
    }
    if (params.page_size) {
      searchParams.append('page_size', params.page_size.toString());
    }

    const response = await fetch(
      `${API_BASE_URL}${VB_BASE_PATH}/sessions/user?${searchParams}`,
      {
        method: 'GET',
        headers: getAuthHeaders(),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    return unwrapResponse(response);
  },

  /**
   * Complete a session (VB or Admin)
   * POST /venture-builder/sessions/{session_id}/complete
   */
  completeSession: async (sessionId: string): Promise<{ status: string; message: string }> => {
    const response = await fetch(
      `${API_BASE_URL}${VB_BASE_PATH}/sessions/${sessionId}/complete`,
      {
        method: 'POST',
        headers: getAuthHeaders(),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    return unwrapResponse(response);
  },

  /**
   * Cancel a session (VB or Admin ONLY)
   * POST /venture-builder/sessions/{session_id}/cancel
   *
   * NOTE: API changed from DELETE to POST with required cancellation_reason
   */
  cancelSession: async (
    sessionId: string,
    cancellationReason: string
  ): Promise<{
    id: string;
    status: string;
    credits_refunded: number;
    cancellation_reason: string;
    updated_at: string;
  }> => {
    const response = await fetch(
      `${API_BASE_URL}${VB_BASE_PATH}/sessions/${sessionId}/cancel`,
      {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ cancellation_reason: cancellationReason }),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    return unwrapResponse(response);
  },
};

// ============================================================================
// SESSION NOTES
// ============================================================================

export const notesAPI = {
  /**
   * Create session note (VB or Admin)
   */
  create: async (payload: CreateSessionNotePayload): Promise<SessionNote> => {
    const response = await fetch(`${API_BASE_URL}${VB_BASE_PATH}/notes`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      await handleApiError(response);
    }

    return unwrapResponse(response);
  },

  /**
   * Update session note (VB or Admin)
   */
  update: async (
    noteId: string,
    payload: UpdateSessionNotePayload
  ): Promise<SessionNote> => {
    const response = await fetch(`${API_BASE_URL}${VB_BASE_PATH}/notes/${noteId}`, {
      method: 'PATCH',
      headers: getAuthHeaders(),
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      await handleApiError(response);
    }

    return unwrapResponse(response);
  },

  /**
   * Get session note - User view
   */
  getSessionNoteUser: async (sessionId: string): Promise<SessionNote> => {
    const response = await fetch(
      `${API_BASE_URL}${VB_BASE_PATH}/notes/session/${sessionId}/user`,
      {
        method: 'GET',
        headers: getAuthHeaders(),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    return unwrapResponse(response);
  },

  /**
   * Get session note - VB view
   */
  getSessionNoteVB: async (sessionId: string): Promise<SessionNote> => {
    const response = await fetch(
      `${API_BASE_URL}${VB_BASE_PATH}/notes/session/${sessionId}/vb`,
      {
        method: 'GET',
        headers: getAuthHeaders(),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    return unwrapResponse(response);
  },

  /**
   * Get tenant notes - User view
   */
  getTenantNotesUser: async (): Promise<SessionNote[]> => {
    const response = await fetch(
      `${API_BASE_URL}${VB_BASE_PATH}/notes/tenant/user`,
      {
        method: 'GET',
        headers: getAuthHeaders(),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    return unwrapResponse(response);
  },

  /**
   * Get tenant notes - VB view
   */
  getTenantNotesVB: async (): Promise<SessionNote[]> => {
    const response = await fetch(`${API_BASE_URL}${VB_BASE_PATH}/notes/tenant/vb`, {
      method: 'GET',
      headers: getAuthHeaders(),
    });

    if (!response.ok) {
      await handleApiError(response);
    }

    return unwrapResponse(response);
  },
};

// ============================================================================
// EARNINGS
// ============================================================================

export const earningsAPI = {
  /**
   * Get my earnings (VB or Admin)
   */
  getMyEarnings: async (params: GetEarningsParams = {}): Promise<EarningsResponse> => {
    const searchParams = new URLSearchParams();

    if (params.start_date) {
      searchParams.append('start_date', params.start_date);
    }
    if (params.end_date) {
      searchParams.append('end_date', params.end_date);
    }

    const response = await fetch(
      `${API_BASE_URL}${VB_BASE_PATH}/earnings?${searchParams}`,
      {
        method: 'GET',
        headers: getAuthHeaders(),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    return unwrapResponse(response);
  },

  /**
   * Get earnings config (Admin only)
   */
  getConfig: async (): Promise<EarningsConfig> => {
    const response = await fetch(
      `${API_BASE_URL}${VB_BASE_PATH}/admin/earnings/config`,
      {
        method: 'GET',
        headers: getAuthHeaders(),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    return unwrapResponse(response);
  },

  /**
   * Update earnings config (Admin only)
   */
  updateConfig: async (
    payload: UpdateEarningsConfigPayload
  ): Promise<EarningsConfig> => {
    const response = await fetch(
      `${API_BASE_URL}${VB_BASE_PATH}/admin/earnings/config`,
      {
        method: 'PATCH',
        headers: getAuthHeaders(),
        body: JSON.stringify(payload),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    return unwrapResponse(response);
  },
};

// ============================================================================
// RECONCILIATION
// ============================================================================

export const reconciliationAPI = {
  /**
   * Reconcile VB payments (Admin only)
   * POST /venture-builder/admin/vb/{vb_id}/reconcile
   */
  reconcilePayments: async (
    vbId: string,
    payload?: {
      start_date?: string;
      end_date?: string;
      notes?: string;
    }
  ): Promise<{
    reconciliation_id: string;
    venture_builder_id: string;
    amount_reconciled_usd: string;
    pending_amount_before: string;
    pending_amount_after: string;
    session_count: number;
    sessions_marked_settled: number;
    total_reconciled_lifetime: string;
    created_at: string;
  }> => {
    const response = await fetch(
      `${API_BASE_URL}${VB_BASE_PATH}/admin/vb/${vbId}/reconcile`,
      {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(payload || {}),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    return unwrapResponse(response);
  },

  /**
   * Get VB reconciliation history (Admin only)
   * GET /venture-builder/admin/vb/{vb_id}/reconciliations
   */
  getVBReconciliations: async (
    vbId: string,
    params?: { page?: number; page_size?: number }
  ): Promise<{
    reconciliations: Array<any>;
    total_count: number;
    page: number;
    page_size: number;
  }> => {
    const searchParams = new URLSearchParams();

    if (params?.page) {
      searchParams.append('page', params.page.toString());
    }
    if (params?.page_size) {
      searchParams.append('page_size', params.page_size.toString());
    }

    const response = await fetch(
      `${API_BASE_URL}${VB_BASE_PATH}/admin/vb/${vbId}/reconciliations?${searchParams}`,
      {
        method: 'GET',
        headers: getAuthHeaders(),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    return unwrapResponse(response);
  },

  /**
   * Get all reconciliations (Admin only)
   * GET /venture-builder/admin/reconciliations
   */
  getAllReconciliations: async (
    params?: { page?: number; page_size?: number }
  ): Promise<{
    reconciliations: Array<any>;
    total_count: number;
    page: number;
    page_size: number;
  }> => {
    const searchParams = new URLSearchParams();

    if (params?.page) {
      searchParams.append('page', params.page.toString());
    }
    if (params?.page_size) {
      searchParams.append('page_size', params.page_size.toString());
    }

    const response = await fetch(
      `${API_BASE_URL}${VB_BASE_PATH}/admin/reconciliations?${searchParams}`,
      {
        method: 'GET',
        headers: getAuthHeaders(),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    return unwrapResponse(response);
  },
};

// ============================================================================
// VB PORTAL
// ============================================================================

export const portalAPI = {
  /**
   * Get VB accessible projects
   */
  getAccessibleProjects: async (): Promise<TenantProject[]> => {
    const response = await fetch(`${API_BASE_URL}${VB_BASE_PATH}/portal/projects`, {
      method: 'GET',
      headers: getAuthHeaders(),
    });

    if (!response.ok) {
      await handleApiError(response);
    }

    return unwrapResponse(response);
  },
};

// ============================================================================
// DISPUTES
// ============================================================================

export const disputesAPI = {
  /**
   * Check if can open dispute
   */
  canOpenDispute: async (sessionId: string): Promise<CanOpenDisputeResponse> => {
    const response = await fetch(
      `${API_BASE_URL}${VB_BASE_PATH}/sessions/${sessionId}/can-dispute`,
      {
        method: 'GET',
        headers: getAuthHeaders(),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    return unwrapResponse(response);
  },

  /**
   * Create dispute
   */
  create: async (
    sessionId: string,
    payload: CreateDisputePayload
  ): Promise<Dispute> => {
    const response = await fetch(
      `${API_BASE_URL}${VB_BASE_PATH}/sessions/${sessionId}/disputes`,
      {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(payload),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    return unwrapResponse(response);
  },

  /**
   * Get my disputes
   */
  getMyDisputes: async (
    params: GetDisputesParams = {}
  ): Promise<GetDisputesResponse> => {
    const searchParams = new URLSearchParams();

    if (params.page) {
      searchParams.append('page', params.page.toString());
    }
    if (params.page_size) {
      searchParams.append('page_size', params.page_size.toString());
    }

    const response = await fetch(
      `${API_BASE_URL}${VB_BASE_PATH}/disputes?${searchParams}`,
      {
        method: 'GET',
        headers: getAuthHeaders(),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    return unwrapResponse(response);
  },

  /**
   * Get dispute detail
   */
  getDetail: async (disputeId: string): Promise<Dispute> => {
    const response = await fetch(
      `${API_BASE_URL}${VB_BASE_PATH}/disputes/${disputeId}`,
      {
        method: 'GET',
        headers: getAuthHeaders(),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    return unwrapResponse(response);
  },

  /**
   * Get all disputes (Admin only)
   */
  getAllDisputes: async (
    params: GetAdminDisputesParams = {}
  ): Promise<GetDisputesResponse> => {
    const searchParams = new URLSearchParams();

    if (params.status) {
      searchParams.append('status', params.status);
    }
    if (params.vb_id) {
      searchParams.append('vb_id', params.vb_id);
    }
    if (params.start_date) {
      searchParams.append('start_date', params.start_date);
    }
    if (params.end_date) {
      searchParams.append('end_date', params.end_date);
    }
    if (params.page) {
      searchParams.append('page', params.page.toString());
    }
    if (params.page_size) {
      searchParams.append('page_size', params.page_size.toString());
    }

    const response = await fetch(
      `${API_BASE_URL}${VB_BASE_PATH}/admin/disputes?${searchParams}`,
      {
        method: 'GET',
        headers: getAuthHeaders(),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    return unwrapResponse(response);
  },

  /**
   * Update dispute (Admin only)
   */
  updateDispute: async (
    disputeId: string,
    payload: UpdateDisputePayload
  ): Promise<Dispute> => {
    const response = await fetch(
      `${API_BASE_URL}${VB_BASE_PATH}/admin/disputes/${disputeId}`,
      {
        method: 'PATCH',
        headers: getAuthHeaders(),
        body: JSON.stringify(payload),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    return unwrapResponse(response);
  },
};

// ============================================================================
// GOOGLE CALENDAR INTEGRATION
// ============================================================================

export const calendarAPI = {
  /**
   * Get calendar auth URL (VB only)
   * GET /venture-builder/calendar/auth-url
   */
  getAuthUrl: async (): Promise<{ auth_url: string; state: string }> => {
    const response = await fetch(
      `${API_BASE_URL}${VB_BASE_PATH}/calendar/auth-url`,
      {
        method: 'GET',
        headers: getAuthHeaders(),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    return unwrapResponse(response);
  },

  /**
   * Get calendar connection status (VB only)
   * GET /venture-builder/calendar/status
   */
  getStatus: async (): Promise<{
    connected: boolean;
    calendar_id: string | null;
    calendar_name: string | null;
    time_zone: string | null;
    is_valid: boolean | null;
  }> => {
    const response = await fetch(
      `${API_BASE_URL}${VB_BASE_PATH}/calendar/status`,
      {
        method: 'GET',
        headers: getAuthHeaders(),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    return unwrapResponse(response);
  },

  /**
   * Get list of user's Google Calendars (VB only)
   * GET /venture-builder/calendar/list
   */
  listCalendars: async (): Promise<GoogleCalendarList[]> => {
    const response = await fetch(
      `${API_BASE_URL}${VB_BASE_PATH}/calendar/list`,
      {
        method: 'GET',
        headers: getAuthHeaders(),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    const data = await unwrapResponse<{ calendars: GoogleCalendarList[] }>(response);
    return data.calendars || [];
  },

  /**
   * Select which calendar to use for bookings (VB only)
   * POST /venture-builder/calendar/select
   */
  selectCalendar: async (payload: { calendar_id: string; time_zone?: string }): Promise<{ status: string; message: string }> => {
    const response = await fetch(
      `${API_BASE_URL}${VB_BASE_PATH}/calendar/select`,
      {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          calendar_id: payload.calendar_id,
          time_zone: payload.time_zone || 'UTC',
        }),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    return unwrapResponse(response);
  },

  /**
   * Disconnect Google Calendar (VB only)
   * DELETE /venture-builder/calendar/disconnect
   */
  disconnect: async (): Promise<{ status: string; message: string }> => {
    const response = await fetch(
      `${API_BASE_URL}${VB_BASE_PATH}/calendar/disconnect`,
      {
        method: 'DELETE',
        headers: getAuthHeaders(),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    return unwrapResponse(response);
  },
};

// ============================================================================
// AVAILABILITY SLOTS (NEW API)
// ============================================================================

export const availabilityAPI = {
  /**
   * Create availability slots (VB only)
   * POST /venture-builder/{vb_id}/availability-slots
   *
   * Adds new 1-hour slots without deleting existing ones.
   * Each slot is 1 hour; session_end is computed automatically.
   */
  createSlots: async (vbId: string, payload: CreateAvailabilitySlotsPayload): Promise<AvailabilitySlot[]> => {
    const response = await fetch(
      `${API_BASE_URL}${VB_BASE_PATH}/${vbId}/availability-slots`,
      {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(payload),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    return unwrapResponse(response);
  },

  /**
   * List availability slots (Public)
   * GET /venture-builder/{vb_id}/availability-slots
   *
   * Returns all configured availability slots for a VB.
   */
  listSlots: async (vbId: string): Promise<AvailabilitySlot[]> => {
    const response = await fetch(
      `${API_BASE_URL}${VB_BASE_PATH}/${vbId}/availability-slots`,
      {
        method: 'GET',
        headers: getPublicHeaders(),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    return unwrapResponse(response);
  },

  /**
   * Delete availability slots (VB only)
   * DELETE /venture-builder/{vb_id}/availability-slots
   *
   * Removes specific slots by day_of_week + session_start.
   */
  deleteSlots: async (vbId: string, payload: DeleteAvailabilitySlotsPayload): Promise<{ deleted_count: number }> => {
    const response = await fetch(
      `${API_BASE_URL}${VB_BASE_PATH}/${vbId}/availability-slots`,
      {
        method: 'DELETE',
        headers: getAuthHeaders(),
        body: JSON.stringify(payload),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    return unwrapResponse(response);
  },

  /**
   * Get bookable slots for a date range (Authenticated user)
   * GET /venture-builder/{vb_id}/availability?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
   *
   * Returns computed available slots considering:
   * - VB's configured availability slots
   * - Confirmed VB sessions in Yuba
   * - Google Calendar busy times (if connected)
   */
  getBookableSlots: async (params: GetAvailabilityParams): Promise<GetAvailabilityResponse> => {
    const searchParams = new URLSearchParams({
      start_date: params.start_date,
      end_date: params.end_date,
    });

    const response = await fetch(
      `${API_BASE_URL}${VB_BASE_PATH}/${params.vb_id}/availability?${searchParams}`,
      {
        method: 'GET',
        headers: getAuthHeaders(),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    return unwrapResponse(response);
  },

  // ============================================================================
  // LEGACY METHODS (deprecated - kept for backward compatibility)
  // ============================================================================

  /**
   * @deprecated Use createSlots instead
   */
  updateProfile: async (vbId: string, payload: UpdateAvailabilityProfilePayload): Promise<AvailabilityProfile[]> => {
    console.warn('availabilityAPI.updateProfile is deprecated. Use availabilityAPI.createSlots instead.');
    const response = await fetch(
      `${API_BASE_URL}${VB_BASE_PATH}/${vbId}/availability-profile`,
      {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify(payload),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    return unwrapResponse(response);
  },

  /**
   * @deprecated Use listSlots instead
   */
  getProfile: async (vbId: string): Promise<AvailabilityProfile[]> => {
    console.warn('availabilityAPI.getProfile is deprecated. Use availabilityAPI.listSlots instead.');
    const response = await fetch(
      `${API_BASE_URL}${VB_BASE_PATH}/${vbId}/availability-profile`,
      {
        method: 'GET',
        headers: getPublicHeaders(),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    return unwrapResponse(response);
  },

  /**
   * @deprecated Use deleteSlots instead
   */
  deleteDay: async (vbId: string, dayOfWeek: number): Promise<{ status: string; message: string }> => {
    console.warn('availabilityAPI.deleteDay is deprecated. Use availabilityAPI.deleteSlots instead.');
    const response = await fetch(
      `${API_BASE_URL}${VB_BASE_PATH}/${vbId}/availability-profile/${dayOfWeek}`,
      {
        method: 'DELETE',
        headers: getAuthHeaders(),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    return unwrapResponse(response);
  },

  /**
   * @deprecated Use getBookableSlots instead
   */
  getAvailability: async (params: GetAvailabilityParams): Promise<GetAvailabilityResponse> => {
    console.warn('availabilityAPI.getAvailability is deprecated. Use availabilityAPI.getBookableSlots instead.');
    return availabilityAPI.getBookableSlots(params);
  },
};

// ============================================================================
// RESCHEDULE (DEPRECATED - REMOVED FROM API)
// ============================================================================
// NOTE: These endpoints have been removed from the backend API.
// Rescheduling is now handled via session cancellation and rebooking.
// Kept for backward compatibility but will throw errors if called.

/**
 * @deprecated Reschedule endpoints have been removed from the API
 */
export const rescheduleAPI = {
  /**
   * VB initiates a reschedule
   */
  initiateReschedule: async (
    sessionId: string,
    payload: RescheduleSessionPayload
  ): Promise<RescheduleSessionResponse> => {
    const response = await fetch(
      `${API_BASE_URL}${VB_BASE_PATH}/sessions/${sessionId}/reschedule`,
      {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(payload),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    return unwrapResponse(response);
  },

  /**
   * Validate reschedule token (Public)
   */
  validateToken: async (token: string): Promise<ValidateRescheduleTokenResponse> => {
    const response = await fetch(
      `${API_BASE_URL}${VB_BASE_PATH}/reschedule/${token}`,
      {
        method: 'GET',
        headers: getPublicHeaders(),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    return unwrapResponse(response);
  },

  /**
   * Complete reschedule booking (Founder with token)
   */
  completeReschedule: async (
    token: string,
    payload: RescheduleBookPayload
  ): Promise<RescheduleBookResponse> => {
    const response = await fetch(
      `${API_BASE_URL}${VB_BASE_PATH}/reschedule/${token}/book`,
      {
        method: 'POST',
        headers: getPublicHeaders(),
        body: JSON.stringify(payload),
      }
    );

    if (!response.ok) {
      await handleApiError(response);
    }

    return unwrapResponse(response);
  },
};

// ============================================================================
// MAIN EXPORT
// ============================================================================

export const ventureBuilderAPI = {
  invitations: invitationsAPI,
  expertise: expertiseAPI,
  profile: profileAPI,
  browse: browseAPI,
  admin: adminAPI,
  booking: bookingAPI,
  sessions: sessionsAPI,
  notes: notesAPI,
  earnings: earningsAPI,
  reconciliation: reconciliationAPI,
  portal: portalAPI,
  disputes: disputesAPI,
  calendar: calendarAPI,
  availability: availabilityAPI,
  reschedule: rescheduleAPI,
};
