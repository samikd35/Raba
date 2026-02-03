import { authService } from '../../services/authService';

/**
 * Payment Service - Real API Integration
 * 
 * This service handles all payment-related API calls including:
 * - Fetching available credit packages
 * - Creating payment transactions
 * - Verifying payment status
 * - Creating payment-gated invitations
 * - Verifying organization payment
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

// ============================================================================
// Type Definitions
// ============================================================================

/**
 * Credit Package
 * Represents a purchasable credit package with pricing information
 */
export interface CreditPackage {
  id: string;
  name: string;
  description: string;
  credit_amount: number;
  price_ngn: number;
  price_usd: number;
  tenant_type: 'individual' | 'team' | 'organization';
  is_active: boolean;
}

/**
 * Payment Request
 * Data required to initiate a payment transaction
 */
export interface PaymentRequest {
  amount: number;
  currency: 'NGN' | 'USD';
  email: string;
  name: string;
}

/**
 * Payment Response
 * Response from payment creation containing checkout link
 */
export interface PaymentResponse {
  checkout_link: string;
  tx_ref: string;
}

/**
 * Payment Verification Response
 * Response from payment verification endpoint
 */
export interface PaymentVerificationResponse {
  success: boolean;
  message: string;
  transaction_id: string;
  status: 'successful' | 'failed' | 'pending';
  amount: number;
  currency: string;
  credits_allocated?: number;
}

/**
 * Payment-Gated Invite Request
 * Data for creating payment-gated invitations
 */
export interface PaymentGatedInviteRequest {
  invites: {
    email: string;
    package_id: string;
    is_admin: boolean;
  }[];
}

/**
 * Payment-Gated Invite Response
 * Response containing payment links for each invitee
 */
export interface PaymentGatedInviteResponse {
  success: boolean;
  message: string;
  invites: {
    email: string;
    payment_link: string;
    invite_id: string;
  }[];
}

// ============================================================================
// Payment API Service
// ============================================================================

/**
 * Payment API Service
 * Handles all payment-related API operations
 */
export class PaymentService {
  /**
   * Get available credit packages
   * GET /api/packages
   * 
   * Retrieves all available credit packages that can be purchased.
   * Packages are filtered by tenant type and active status.
   * 
   * @returns Array of available credit packages
   */
  static async getPackages(): Promise<CreditPackage[]> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/packages`, {
        method: 'GET',
        headers: getAuthHeaders(),
      });
      await handleApiError(response);
      return await response.json();
    } catch (error) {
      console.error('Error fetching credit packages:', error);
      throw error;
    }
  }

  /**
   * Create a payment transaction
   * POST /payments/create
   * 
   * Initiates a payment transaction and returns a checkout link.
   * The user will be redirected to Flutterwave to complete the payment.
   * 
   * @param data - Payment request data (amount, currency, email, name)
   * @returns Payment response with checkout link and transaction reference
   */
  static async createPayment(data: PaymentRequest): Promise<PaymentResponse> {
    try {
      // Validate input
      if (!data.amount || data.amount <= 0) {
        throw new Error('Payment amount must be greater than 0');
      }
      if (!data.currency || !['NGN', 'USD'].includes(data.currency)) {
        throw new Error('Currency must be either NGN or USD');
      }
      if (!data.email || !data.email.includes('@')) {
        throw new Error('Valid email is required');
      }
      if (!data.name || data.name.trim().length === 0) {
        throw new Error('Name is required');
      }

      const response = await fetch(`${API_BASE_URL}/payments/create`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(data),
      });
      await handleApiError(response);
      return await response.json();
    } catch (error) {
      console.error('Error creating payment:', error);
      throw error;
    }
  }

  /**
   * Verify payment status
   * GET /payments/verify
   * 
   * Verifies the status of a payment transaction after the user completes
   * the payment flow. This should be called after the user returns from
   * the payment gateway.
   * 
   * @param transactionId - The transaction ID to verify
   * @param txRef - The transaction reference from payment creation
   * @returns Payment verification response with status and credit allocation
   */
  static async verifyPayment(
    transactionId: string,
    txRef: string
  ): Promise<PaymentVerificationResponse> {
    try {
      // Validate input
      if (!transactionId || typeof transactionId !== 'string') {
        throw new Error('Valid transaction ID is required');
      }
      if (!txRef || typeof txRef !== 'string') {
        throw new Error('Valid transaction reference is required');
      }

      const response = await fetch(
        `${API_BASE_URL}/payments/verify?transaction_id=${encodeURIComponent(transactionId)}&tx_ref=${encodeURIComponent(txRef)}`,
        {
          method: 'GET',
          headers: getAuthHeaders(),
        }
      );
      await handleApiError(response);
      return await response.json();
    } catch (error) {
      console.error('Error verifying payment:', error);
      throw error;
    }
  }

  /**
   * Create payment-gated invitations
   * POST /api/organization/{id}/payment-invites
   * 
   * Creates invitations that require payment before the invitee can join.
   * Each invitee receives a unique payment link. Once they complete payment,
   * they will receive their invitation to join the organization.
   * 
   * @param organizationId - The ID of the organization
   * @param data - Payment-gated invite request with invitee details
   * @returns Response with payment links for each invitee
   */
  static async createPaymentGatedInvites(
    organizationId: string,
    data: PaymentGatedInviteRequest
  ): Promise<PaymentGatedInviteResponse> {
    try {
      // Validate input
      if (!organizationId || typeof organizationId !== 'string') {
        throw new Error('Valid organization ID is required');
      }
      if (!data.invites || !Array.isArray(data.invites) || data.invites.length === 0) {
        throw new Error('At least one invite is required');
      }

      // Validate each invite
      for (const invite of data.invites) {
        if (!invite.email || !invite.email.includes('@')) {
          throw new Error(`Invalid email: ${invite.email}`);
        }
        if (!invite.package_id || typeof invite.package_id !== 'string') {
          throw new Error(`Package ID is required for ${invite.email}`);
        }
        if (typeof invite.is_admin !== 'boolean') {
          throw new Error(`is_admin must be a boolean for ${invite.email}`);
        }
      }

      const response = await fetch(
        `${API_BASE_URL}/api/organization/${organizationId}/payment-invites`,
        {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify(data),
        }
      );
      await handleApiError(response);
      return await response.json();
    } catch (error) {
      console.error('Error creating payment-gated invites:', error);
      throw error;
    }
  }

  /**
   * Verify organization payment
   * GET /payments-org/verify
   * 
   * Verifies payment for organization-level transactions (e.g., payment-gated invites).
   * This is called after an invitee completes their payment to verify the transaction
   * and trigger the invitation email.
   * 
   * @param transactionId - The transaction ID to verify
   * @param txRef - The transaction reference from payment creation
   * @param inviteId - The invitation ID associated with this payment
   * @returns Payment verification response with invitation status
   */
  static async verifyOrganizationPayment(
    transactionId: string,
    txRef: string,
    inviteId: string
  ): Promise<PaymentVerificationResponse> {
    try {
      // Validate input
      if (!transactionId || typeof transactionId !== 'string') {
        throw new Error('Valid transaction ID is required');
      }
      if (!txRef || typeof txRef !== 'string') {
        throw new Error('Valid transaction reference is required');
      }
      if (!inviteId || typeof inviteId !== 'string') {
        throw new Error('Valid invite ID is required');
      }

      const response = await fetch(
        `${API_BASE_URL}/payments-org/verify?transaction_id=${encodeURIComponent(transactionId)}&tx_ref=${encodeURIComponent(txRef)}&invite_id=${encodeURIComponent(inviteId)}`,
        {
          method: 'GET',
          headers: getAuthHeaders(),
        }
      );
      await handleApiError(response);
      return await response.json();
    } catch (error) {
      console.error('Error verifying organization payment:', error);
      throw error;
    }
  }
}

// Export singleton instance
export const paymentService = PaymentService;
