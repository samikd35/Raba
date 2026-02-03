import { authService } from '../../services/authService';

/**
 * Credit Request Service - Real API Integration
 * 
 * This service handles all credit request-related API calls using the new
 * organization-based endpoints:
 * 
 * Team Member Requests:
 * - POST /api/organization/{organization_id}/credit-requests/team
 * 
 * Individual Member Requests:
 * - POST /api/organization/{organization_id}/credit-requests/individual
 * 
 * View Requests:
 * - GET /api/organization/{organization_id}/credit-requests (org admins only)
 * - GET /api/organization/{organization_id}/credit-requests/my-requests
 * 
 * Admin Actions:
 * - PATCH /api/organization/{organization_id}/credit-requests/{request_id}
 * 
 * Grant Organizations:
 * - POST /api/organization/{organization_id}/request-credits-from-yuba
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL;

// =============================================================================
// TYPES
// =============================================================================

export interface CreditRequest {
  id: string;
  user_id: string;
  user_name?: string;
  user_email?: string;
  organization_id: string;
  team_id?: string;
  team_name?: string;
  requested_amount: number;
  reason?: string;
  status: 'pending' | 'approved' | 'rejected' | 'fulfilled';
  reviewed_by?: string;
  reviewed_at?: string;
  review_notes?: string;
  created_at: string;
  updated_at: string;
}

export interface CreditRequestListResponse {
  requests: CreditRequest[];
  total_count: number;
  pending_count: number;
}

export interface TeamMemberCreditRequestCreate {
  team_id: string;
  requested_amount: number;
  reason?: string;
}

export interface IndividualMemberCreditRequestCreate {
  requested_amount: number;
  reason?: string;
}

export interface CreditRequestUpdate {
  status: 'approved' | 'rejected';
  review_notes?: string;
}

export interface OrgAdminCreditRequestCreate {
  requested_amount: number;
  reason: string;
  urgency?: 'normal' | 'high' | 'urgent';
}

export interface CreditRequestApiResponse {
  success: boolean;
  message: string;
  data?: CreditRequest;
}

// =============================================================================
// HELPERS
// =============================================================================

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

// =============================================================================
// CREDIT REQUEST SERVICE
// =============================================================================

/**
 * Credit Request API Service
 * Handles all credit request-related API operations
 */
export class CreditRequestService {
  
  // ===========================================================================
  // CREATE REQUESTS
  // ===========================================================================

  /**
   * Create a credit request for a team member
   * POST /api/organization/{organization_id}/credit-requests/team
   * 
   * @param organizationId - The organization ID
   * @param data - Credit request data (team_id, requested_amount, optional reason)
   * @returns The created credit request
   */
  static async createTeamMemberCreditRequest(
    organizationId: string,
    data: TeamMemberCreditRequestCreate
  ): Promise<CreditRequest> {
    try {
      if (!organizationId) {
        throw new Error('Organization ID is required');
      }
      if (!data.team_id) {
        throw new Error('Team ID is required');
      }
      if (!data.requested_amount || data.requested_amount <= 0) {
        throw new Error('Requested amount must be greater than 0');
      }

      console.log('Creating team member credit request:', { organizationId, ...data });

      const response = await fetch(
        `${API_BASE_URL}/api/organization/${organizationId}/credit-requests/team`,
        {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify(data),
        }
      );
      await handleApiError(response);
      const result: CreditRequestApiResponse = await response.json();
      return result.data!;
    } catch (error) {
      console.error('Error creating team member credit request:', error);
      throw error;
    }
  }

  /**
   * Create a credit request for an individual member (not part of a team)
   * POST /api/organization/{organization_id}/credit-requests/individual
   * 
   * @param organizationId - The organization ID
   * @param data - Credit request data (requested_amount, optional reason)
   * @returns The created credit request
   */
  static async createIndividualMemberCreditRequest(
    organizationId: string,
    data: IndividualMemberCreditRequestCreate
  ): Promise<CreditRequest> {
    try {
      if (!organizationId) {
        throw new Error('Organization ID is required');
      }
      if (!data.requested_amount || data.requested_amount <= 0) {
        throw new Error('Requested amount must be greater than 0');
      }

      console.log('Creating individual member credit request:', { organizationId, ...data });

      const response = await fetch(
        `${API_BASE_URL}/api/organization/${organizationId}/credit-requests/individual`,
        {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify(data),
        }
      );
      await handleApiError(response);
      const result: CreditRequestApiResponse = await response.json();
      return result.data!;
    } catch (error) {
      console.error('Error creating individual member credit request:', error);
      throw error;
    }
  }

  // ===========================================================================
  // VIEW REQUESTS
  // ===========================================================================

  /**
   * Get all credit requests for an organization (org admin/owner view)
   * GET /api/organization/{organization_id}/credit-requests
   * 
   * @param organizationId - The organization ID
   * @param statusFilter - Optional filter by status (pending, approved, rejected, fulfilled)
   * @returns List of all credit requests for the organization
   */
  static async getOrganizationCreditRequests(
    organizationId: string,
    statusFilter?: string
  ): Promise<CreditRequestListResponse> {
    try {
      if (!organizationId) {
        throw new Error('Organization ID is required');
      }

      let url = `${API_BASE_URL}/api/organization/${organizationId}/credit-requests`;
      if (statusFilter) {
        url += `?status_filter=${statusFilter}`;
      }

      const response = await fetch(url, {
        method: 'GET',
        headers: getAuthHeaders(),
      });
      await handleApiError(response);
      return await response.json();
    } catch (error) {
      console.error('Error fetching organization credit requests:', error);
      throw error;
    }
  }

  /**
   * Get my credit requests in an organization
   * GET /api/organization/{organization_id}/credit-requests/my-requests
   * 
   * @param organizationId - The organization ID
   * @returns List of user's credit requests
   */
  static async getMyCreditRequests(
    organizationId: string
  ): Promise<{ requests: CreditRequest[]; total_count: number }> {
    try {
      if (!organizationId) {
        throw new Error('Organization ID is required');
      }

      const response = await fetch(
        `${API_BASE_URL}/api/organization/${organizationId}/credit-requests/my-requests`,
        {
          method: 'GET',
          headers: getAuthHeaders(),
        }
      );
      await handleApiError(response);
      return await response.json();
    } catch (error) {
      console.error('Error fetching my credit requests:', error);
      throw error;
    }
  }

  // ===========================================================================
  // ADMIN ACTIONS
  // ===========================================================================

  /**
   * Update credit request status (approve/reject) - Org admin/owner only
   * PATCH /api/organization/{organization_id}/credit-requests/{request_id}
   * 
   * @param organizationId - The organization ID
   * @param requestId - The credit request ID
   * @param updateData - Status update data (status, optional review_notes)
   * @returns The updated credit request
   */
  static async updateCreditRequestStatus(
    organizationId: string,
    requestId: string,
    updateData: CreditRequestUpdate
  ): Promise<CreditRequest> {
    try {
      if (!organizationId) {
        throw new Error('Organization ID is required');
      }
      if (!requestId) {
        throw new Error('Request ID is required');
      }
      if (!['approved', 'rejected'].includes(updateData.status)) {
        throw new Error('Status must be "approved" or "rejected"');
      }

      console.log('Updating credit request status:', { organizationId, requestId, ...updateData });

      const response = await fetch(
        `${API_BASE_URL}/api/organization/${organizationId}/credit-requests/${requestId}`,
        {
          method: 'PATCH',
          headers: getAuthHeaders(),
          body: JSON.stringify(updateData),
        }
      );
      await handleApiError(response);
      const result: CreditRequestApiResponse = await response.json();
      return result.data!;
    } catch (error) {
      console.error('Error updating credit request status:', error);
      throw error;
    }
  }

  // ===========================================================================
  // GRANT ORGANIZATION - REQUEST FROM YUBA
  // ===========================================================================

  /**
   * Request credits from Yuba (grant organizations only)
   * POST /api/organization/{organization_id}/request-credits-from-yuba
   * 
   * @param organizationId - The organization ID
   * @param data - Request data (requested_amount, reason, optional urgency)
   * @returns Success response with reference ID
   */
  static async requestCreditsFromYuba(
    organizationId: string,
    data: OrgAdminCreditRequestCreate
  ): Promise<{ success: boolean; message: string; request_reference?: string }> {
    try {
      if (!organizationId) {
        throw new Error('Organization ID is required');
      }
      if (!data.requested_amount || data.requested_amount <= 0) {
        throw new Error('Requested amount must be greater than 0');
      }
      if (!data.reason || data.reason.length < 10) {
        throw new Error('Reason must be at least 10 characters');
      }

      console.log('Requesting credits from Yuba:', { organizationId, ...data });

      const response = await fetch(
        `${API_BASE_URL}/api/organization/${organizationId}/request-credits-from-yuba`,
        {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify(data),
        }
      );
      await handleApiError(response);
      return await response.json();
    } catch (error) {
      console.error('Error requesting credits from Yuba:', error);
      throw error;
    }
  }

  // ===========================================================================
  // LEGACY COMPATIBILITY METHODS
  // These methods maintain backward compatibility with existing code
  // ===========================================================================

  /**
   * @deprecated Use createTeamMemberCreditRequest or createIndividualMemberCreditRequest instead
   * Legacy method - creates a credit request using the old team-based endpoint pattern
   */
  static async createCreditRequest(
    teamId: string,
    data: { requested_credits: number; reason?: string }
  ): Promise<CreditRequest> {
    // This maps to the team member credit request
    // The teamId is actually the organization_id in most cases
    console.warn('Using legacy createCreditRequest - consider using createTeamMemberCreditRequest');
    
    return this.createTeamMemberCreditRequest(teamId, {
      team_id: teamId,
      requested_amount: data.requested_credits,
      reason: data.reason,
    });
  }

  /**
   * @deprecated Use getMyCreditRequests instead
   * Legacy method - gets credit requests for a team
   */
  static async getCreditRequests(teamId: string): Promise<CreditRequest[]> {
    console.warn('Using legacy getCreditRequests - consider using getMyCreditRequests');
    const result = await this.getMyCreditRequests(teamId);
    return result.requests;
  }

  /**
   * @deprecated Use updateCreditRequestStatus with 'rejected' status instead
   * Legacy method - cancels a pending credit request
   */
  static async cancelCreditRequest(
    teamId: string,
    requestId: string
  ): Promise<{ success: boolean; message: string }> {
    console.warn('Using legacy cancelCreditRequest - consider using updateCreditRequestStatus');
    await this.updateCreditRequestStatus(teamId, requestId, {
      status: 'rejected',
      review_notes: 'Cancelled by user',
    });
    return { success: true, message: 'Request cancelled successfully' };
  }

  /**
   * @deprecated Use updateCreditRequestStatus instead
   * Legacy method - reviews a credit request
   */
  static async reviewCreditRequest(
    organizationId: string,
    requestId: string,
    reviewData: { action: 'approve' | 'reject'; credits_allocated?: number; review_notes?: string }
  ): Promise<CreditRequest> {
    console.warn('Using legacy reviewCreditRequest - consider using updateCreditRequestStatus');
    return this.updateCreditRequestStatus(organizationId, requestId, {
      status: reviewData.action === 'approve' ? 'approved' : 'rejected',
      review_notes: reviewData.review_notes,
    });
  }
}

// Export singleton instance
export const creditRequestService = CreditRequestService;
