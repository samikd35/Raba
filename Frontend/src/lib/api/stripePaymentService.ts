import { authService } from '../../services/authService';

/**
 * Stripe Payment Service
 * 
 * Handles Stripe-specific payment operations:
 * - Creating checkout sessions for credit purchases
 * - Verifying payment status after redirect
 * - Organization payment verification
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://yuba-backend-prod.azurewebsites.net';

/**
 * Get authentication headers for API requests
 */
const getAuthHeaders = (): HeadersInit => {
  try {
    const token = authService.getCurrentToken();
    if (!token) {
      console.warn('No authentication token available for Stripe API call');
      return {
        'Content-Type': 'application/json',
      };
    }
    return {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    };
  } catch (error) {
    console.warn('Error getting auth token:', error);
    return {
      'Content-Type': 'application/json',
    };
  }
};

/**
 * Handle API errors with proper error messages
 */
const handleApiError = async (response: Response): Promise<void> => {
  if (!response.ok) {
    let errorMessage = `API Error: ${response.status} ${response.statusText}`;
    try {
      const errorData = await response.json();
      // Handle various error response formats
      if (typeof errorData === 'string') {
        errorMessage = errorData;
      } else if (errorData.message) {
        errorMessage = errorData.message;
      } else if (errorData.detail) {
        errorMessage = typeof errorData.detail === 'string' ? errorData.detail : JSON.stringify(errorData.detail);
      } else if (errorData.error) {
        errorMessage = typeof errorData.error === 'string' ? errorData.error : JSON.stringify(errorData.error);
      }
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
 * Stripe Checkout Request
 */
export interface StripeCheckoutRequest {
  credits: number;
  amount_usd: number;
  success_url: string;
  cancel_url: string;
  product?: string;
  metadata?: Record<string, string>;
}

/**
 * Stripe Checkout Response
 */
export interface StripeCheckoutResponse {
  checkout_link?: string;
  checkout_url?: string;
  url?: string;
  session_id?: string;
  tx_ref?: string;
}

/**
 * Stripe Verification Response
 */
export interface StripeVerificationResponse {
  success: boolean;
  message: string;
  session_id?: string;
  payment_intent?: string;
  status: 'complete' | 'expired' | 'open' | 'failed';
  credits_allocated?: number;
  amount_paid?: number;
  currency?: string;
}

// ============================================================================
// Stripe Payment Service
// ============================================================================

export class StripePaymentService {
  /**
   * Create a Stripe checkout session for credit purchase
   * POST /payments-stripe/create
   * 
   * @param data - Checkout request data
   * @returns Checkout response with redirect URL
   */
  static async createCheckoutSession(data: StripeCheckoutRequest): Promise<StripeCheckoutResponse> {
    try {
      // Validate input
      if (!data.credits || data.credits < 100 || data.credits > 800) {
        throw new Error('Credits must be between 100 and 800');
      }
      if (data.credits % 100 !== 0) {
        throw new Error('Credits must be in increments of 100');
      }
      if (!data.amount_usd || data.amount_usd <= 0) {
        throw new Error('Amount must be greater than 0');
      }
      if (!data.success_url || !data.cancel_url) {
        throw new Error('Success and cancel URLs are required');
      }

      if (!API_BASE_URL) {
        throw new Error('API_BASE_URL is not configured. Please set NEXT_PUBLIC_API_URL in your environment variables.');
      }

      console.log('Creating Stripe checkout session with URL:', `${API_BASE_URL}/payments-stripe/create`);

      let response: Response;
      try {
        response = await fetch(`${API_BASE_URL}/payments-stripe/create`, {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify({
            credit_amount: data.credits,
            amount_usd: data.amount_usd,
            success_url: data.success_url,
            cancel_url: data.cancel_url,
            product: data.product || 'credits_pro',
            metadata: data.metadata,
          }),
        });
      } catch (networkError) {
        // Network-level error (CORS, server down, no internet, etc.)
        console.error('Network error during Stripe checkout:', networkError);
        throw new Error('Unable to connect to payment server. Please check your internet connection and try again.');
      }

      await handleApiError(response);
      return await response.json();
    } catch (error) {
      console.error('Error creating Stripe checkout session:', error);
      throw error;
    }
  }

  /**
   * Verify a Stripe payment after redirect
   * GET /payments-stripe/verify
   * 
   * @param sessionId - The Stripe session ID
   * @returns Verification response with payment status
   */
  static async verifyPayment(sessionId: string): Promise<StripeVerificationResponse> {
    try {
      if (!sessionId) {
        throw new Error('Session ID is required');
      }

      const response = await fetch(
        `${API_BASE_URL}/payments-stripe/verify?session_id=${encodeURIComponent(sessionId)}`,
        {
          method: 'GET',
          headers: getAuthHeaders(),
        }
      );

      await handleApiError(response);
      return await response.json();
    } catch (error) {
      console.error('Error verifying Stripe payment:', error);
      throw error;
    }
  }

  /**
   * Verify an organization Stripe payment
   * GET /payments-stripe-org/verify
   * 
   * @param sessionId - The Stripe session ID
   * @returns Verification response with payment status
   */
  static async verifyOrganizationPayment(sessionId: string): Promise<StripeVerificationResponse> {
    try {
      if (!sessionId) {
        throw new Error('Session ID is required');
      }

      const response = await fetch(
        `${API_BASE_URL}/payments-stripe-org/verify?session_id=${encodeURIComponent(sessionId)}`,
        {
          method: 'GET',
          headers: getAuthHeaders(),
        }
      );

      await handleApiError(response);
      return await response.json();
    } catch (error) {
      console.error('Error verifying organization Stripe payment:', error);
      throw error;
    }
  }

  /**
   * Calculate price for a given number of credits
   * Price formula: (credits / 100) * 20
   * 
   * @param credits - Number of credits (100-800)
   * @returns Price in USD
   */
  static calculatePrice(credits: number): number {
    return (credits / 100) * 20;
  }
}

// Export singleton instance
export const stripePaymentService = StripePaymentService;
