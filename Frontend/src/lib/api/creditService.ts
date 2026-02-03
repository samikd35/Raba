import {
  CreditAllocationRequest,
  CreditAllocationResponse,
  CreditLot,
  CreditLotActionResponse,
} from '../../types/organization';
import { authService } from '../../services/authService';

/**
 * Credit Service - Real API Integration
 * 
 * This service handles all credit management API calls including:
 * - Allocating credits to users
 * - Freezing credit lots
 * - Suspending credit lots
 * - Fetching issued credit lots
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ;

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
 * Credit API Service
 * Handles all credit management API operations
 */
export class CreditService {
  /**
   * Allocate credits to a user
   * POST /api/organization/{id}/allocate
   * 
   * @param organizationId - The ID of the organization
   * @param data - Credit allocation data (user_id, credit_amount, optional reason, optional validity_period)
   * @returns The credit allocation response with lot_id
   */
  static async allocateCredits(
    organizationId: string,
    data: CreditAllocationRequest
  ): Promise<CreditAllocationResponse> {
    try {
      // Validate input
      if (!organizationId || typeof organizationId !== 'string') {
        throw new Error('Valid organization ID is required');
      }
      if (!data.user_id || typeof data.user_id !== 'string') {
        throw new Error('Valid user ID is required');
      }
      if (!data.credit_amount || data.credit_amount <= 0) {
        throw new Error('Credit amount must be greater than 0');
      }

      const response = await fetch(`${API_BASE_URL}/api/organization/${organizationId}/allocate`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(data),
      });
      await handleApiError(response);
      return await response.json();
    } catch (error) {
      console.error('Error allocating credits:', error);
      throw error;
    }
  }

  /**
   * Freeze a credit lot
   * POST /api/organization/{id}/lots/{lot_id}/freeze
   * 
   * Freezing a credit lot prevents the user from using the credits but keeps them allocated.
   * The credits remain in the user's account but cannot be spent.
   * 
   * @param organizationId - The ID of the organization
   * @param lotId - The ID of the credit lot to freeze
   * @returns Success response with updated lot status
   */
  static async freezeCreditLot(
    organizationId: string,
    lotId: string
  ): Promise<CreditLotActionResponse> {
    try {
      // Validate input
      if (!organizationId || typeof organizationId !== 'string') {
        throw new Error('Valid organization ID is required');
      }
      if (!lotId || typeof lotId !== 'string') {
        throw new Error('Valid lot ID is required');
      }

      const response = await fetch(
        `${API_BASE_URL}/api/organization/${organizationId}/lots/${lotId}/freeze`,
        {
          method: 'POST',
          headers: getAuthHeaders(),
        }
      );
      await handleApiError(response);
      return await response.json();
    } catch (error) {
      console.error('Error freezing credit lot:', error);
      throw error;
    }
  }

  /**
   * Suspend a credit lot
   * POST /api/organization/{id}/lots/{lot_id}/suspend
   * 
   * Suspending a credit lot removes the unused credits from the user's account
   * and returns them to the organization's credit pool.
   * 
   * @param organizationId - The ID of the organization
   * @param lotId - The ID of the credit lot to suspend
   * @returns Success response with updated lot status and returned credits
   */
  static async suspendCreditLot(
    organizationId: string,
    lotId: string
  ): Promise<CreditLotActionResponse> {
    try {
      // Validate input
      if (!organizationId || typeof organizationId !== 'string') {
        throw new Error('Valid organization ID is required');
      }
      if (!lotId || typeof lotId !== 'string') {
        throw new Error('Valid lot ID is required');
      }

      const response = await fetch(
        `${API_BASE_URL}/api/organization/${organizationId}/lots/${lotId}/suspend`,
        {
          method: 'POST',
          headers: getAuthHeaders(),
        }
      );
      await handleApiError(response);
      return await response.json();
    } catch (error) {
      console.error('Error suspending credit lot:', error);
      throw error;
    }
  }

  /**
   * Get all issued credit lots for an organization
   * GET /api/organization/{id}/lots/issued
   * 
   * Retrieves all credit lots that have been issued to users in the organization,
   * including active, frozen, suspended, and expired lots.
   * 
   * @param organizationId - The ID of the organization
   * @returns Array of credit lots with allocation details
   */
  static async getIssuedCreditLots(organizationId: string): Promise<CreditLot[]> {
    try {
      // Validate input
      if (!organizationId || typeof organizationId !== 'string') {
        throw new Error('Valid organization ID is required');
      }

      const response = await fetch(
        `${API_BASE_URL}/api/organization/${organizationId}/lots/issued`,
        {
          method: 'GET',
          headers: getAuthHeaders(),
        }
      );
      await handleApiError(response);
      return await response.json();
    } catch (error) {
      console.error('Error fetching issued credit lots:', error);
      throw error;
    }
  }
}

// Export singleton instance
export const creditService = CreditService;
