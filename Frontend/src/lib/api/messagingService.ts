// lib/api/messagingService.ts
/**
 * Messaging API Service
 *
 * This service handles all REST API calls for the messaging feature based on the API documentation:
 * - Thread management (list threads)
 * - Message retrieval (get messages in a thread)
 * - Message sending (POST /api/messaging/send)
 * - Block/unblock users
 * - Can-contact checks
 * - Online status
 *
 * WebSocket connection is handled separately via useWebSocket hook.
 */

import { authService } from '@/services/authService';
import type {
  Message,
  Thread,
  SendMessageRequest,
  SendMessageResponse,
  GetMessagesRequest,
  GetMessagesResponse,
  ThreadsResponse,
  BlockUserRequest,
  BlockUserResponse,
  CanContactResponse,
  BlockedUsersResponse,
  OnlineStatusResponse,
} from '@/types/messaging';

// ============================================================================
// CONFIGURATION
// ============================================================================

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL;
const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_URL || API_BASE_URL?.replace('http', 'ws');

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
 * Per documentation: All endpoints require JWT in Authorization header
 */
const getAuthHeaders = (): HeadersInit => {
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${getAuthToken()}`,
  };
};

/**
 * Handle API errors consistently
 * Supports both string and object error details from API responses
 */
const handleApiError = async (response: Response): Promise<never> => {
  let errorMessage = `Request failed with status ${response.status}`;
  let errorCode: string | undefined;
  let errorDetails: any;

  try {
    const errorData = await response.json();
    errorDetails = errorData;

    console.error('[MessagingAPI] Error response:', {
      status: response.status,
      url: response.url,
      data: errorData,
    });

    // Handle error format from API documentation
    if (errorData.detail) {
      if (typeof errorData.detail === 'string') {
        errorMessage = errorData.detail;
      } else if (errorData.detail.error) {
        errorMessage = errorData.detail.error;
        errorCode = errorData.detail.code;
      } else {
        errorMessage = JSON.stringify(errorData.detail);
      }
    } else if (errorData.error) {
      errorMessage = errorData.error;
      errorCode = errorData.code;
    } else if (errorData.message) {
      errorMessage = errorData.message;
    }
  } catch (parseError) {
    console.error('[MessagingAPI] Failed to parse error response:', parseError);
    errorMessage = response.statusText || errorMessage;
  }

  const error = new Error(errorMessage) as Error & { code?: string; details?: any };
  if (errorCode) {
    error.code = errorCode;
  }
  if (errorDetails) {
    error.details = errorDetails;
  }
  throw error;
};

// ============================================================================
// MESSAGING API - Based on REST API Documentation
// ============================================================================

export class MessagingAPI {
  /**
   * POST /api/messaging/send - Send a message
   * Sends plaintext content; backend encrypts it server-side
   * Rate limits and block rules apply
   *
   * @param request - Recipient ID and message content
   * @returns Response with message_id and thread_id
   */
  static async sendMessage(request: SendMessageRequest): Promise<SendMessageResponse> {
    const response = await fetch(`${API_BASE_URL}/api/messaging/send`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      await handleApiError(response);
    }

    return response.json();
  }

  /**
   * GET /api/messaging/threads - List threads (paginated)
   * Returns all message threads for the current user
   *
   * @param page - Page number (default 1)
   * @param per_page - Items per page (default 20)
   * @returns Paginated list of threads
   */
  static async getThreads(page = 1, per_page = 20): Promise<ThreadsResponse> {
    const params = new URLSearchParams({
      page: String(page),
      per_page: String(per_page),
    });

    const response = await fetch(
      `${API_BASE_URL}/api/messaging/threads?${params.toString()}`,
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
   * POST /api/messaging/messages - Get messages in a thread
   * By default marks retrieved messages as read
   *
   * @param request - Thread ID, pagination, and mark_as_read options
   * @returns List of messages in the thread
   */
  static async getMessages(request: GetMessagesRequest): Promise<GetMessagesResponse> {
    const response = await fetch(`${API_BASE_URL}/api/messaging/messages`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({
        thread_id: request.thread_id,
        page: request.page || 1,
        per_page: request.per_page || 50,
        mark_as_read: request.mark_as_read !== false, // Default true
      }),
    });

    if (!response.ok) {
      await handleApiError(response);
    }

    return response.json();
  }

  /**
   * POST /api/messaging/block - Block or mute a user
   *
   * @param request - User ID to block and whether to only mute
   * @returns Block confirmation
   */
  static async blockUser(request: BlockUserRequest): Promise<BlockUserResponse> {
    const response = await fetch(`${API_BASE_URL}/api/messaging/block`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      await handleApiError(response);
    }

    return response.json();
  }

  /**
   * POST /api/messaging/unblock - Unblock a user
   *
   * @param userId - User ID to unblock
   */
  static async unblockUser(userId: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/api/messaging/unblock`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ user_id: userId }),
    });

    if (!response.ok) {
      await handleApiError(response);
    }
  }

  /**
   * GET /api/messaging/can-contact/{recipient_id} - Check if you can contact a user
   * Checks rate limits, block status, and match status
   *
   * @param recipientId - User ID to check
   * @returns Whether contact is allowed and reason if not
   */
  static async canContact(recipientId: string): Promise<CanContactResponse> {
    const response = await fetch(
      `${API_BASE_URL}/api/messaging/can-contact/${recipientId}`,
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
   * GET /api/messaging/blocked-users - List blocked/muted users
   *
   * @returns List of blocked and muted users
   */
  static async getBlockedUsers(): Promise<BlockedUsersResponse> {
    const response = await fetch(`${API_BASE_URL}/api/messaging/blocked-users`, {
      method: 'GET',
      headers: getAuthHeaders(),
    });

    if (!response.ok) {
      await handleApiError(response);
    }

    return response.json();
  }

  /**
   * GET /api/messaging/online-status/{user_id} - Check if a user is online
   * HTTP helper to check online status without WebSocket
   *
   * @param userId - User ID to check
   * @returns Online status
   */
  static async getOnlineStatus(userId: string): Promise<OnlineStatusResponse> {
    const response = await fetch(
      `${API_BASE_URL}/api/messaging/online-status/${userId}`,
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
   * Get WebSocket URL for messaging
   *
   * Using secure message-based authentication method
   * Based on WEBSOCKET_MESSAGING_GUIDE.md:
   * - Token sent in first message after connection
   * - Endpoint: /api/messaging/ws/connect
   */
  static getWebSocketUrl(): string {
    // Build WebSocket URL from HTTP API URL if WS_URL not set
    let wsBaseUrl = WS_BASE_URL;
    if (!wsBaseUrl) {
      throw new Error('WebSocket URL not configured');
    }

    // Ensure it uses the correct protocol (ws:// for http://, wss:// for https://)
    wsBaseUrl = wsBaseUrl.replace(/^https:/, 'wss:').replace(/^http:/, 'ws:');

    // Use /connect endpoint for secure authentication
    const url = `${wsBaseUrl}/api/messaging/ws/connect`;
    return url;
  }

  /**
   * Get auth token for WebSocket authentication
   * Used in the first WebSocket message after connection
   */
  static getAuthToken(): string {
    return getAuthToken();
  }
}

// ============================================================================
// CONVENIENCE EXPORTS
// ============================================================================

export const messagingAPI = MessagingAPI;
export default messagingAPI;
