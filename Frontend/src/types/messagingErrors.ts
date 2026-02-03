// types/messagingErrors.ts
/**
 * Messaging Error Types and Utilities
 * Based on backend error definitions from src/mint/api/messaging/models.py
 */

export type MessagingErrorType =
  | 'user_blocked'
  | 'user_blocked_by_you'
  | 'rate_limit_exceeded'
  | 'self_message'
  | 'user_not_found'
  | 'thread_not_found'
  | 'unauthorized'
  | 'encryption_failed'
  | 'decryption_failed'
  | 'websocket_auth_failed'
  | 'websocket_timeout'
  | 'unknown';

export interface MessagingError {
  type: MessagingErrorType;
  message: string;
  statusCode?: number;
  details?: string;
}

/**
 * Error message definitions matching backend
 */
export const MESSAGING_ERROR_MESSAGES: Record<MessagingErrorType, string> = {
  user_blocked: "You cannot send messages to this user because you have been blocked.",
  user_blocked_by_you: "You have blocked this user. Unblock them to send messages.",
  rate_limit_exceeded: "You can only initiate conversations with 1 new user every 72 hours. You can message users you've matched with at any time.",
  self_message: "You cannot send messages to yourself.",
  user_not_found: "The recipient user was not found.",
  thread_not_found: "The message thread was not found.",
  unauthorized: "You are not authorized to access this thread.",
  encryption_failed: "Failed to encrypt the message.",
  decryption_failed: "Failed to decrypt the message.",
  websocket_auth_failed: "WebSocket authentication failed. Please reconnect.",
  websocket_timeout: "WebSocket authentication timed out after 10 seconds.",
  unknown: "An unexpected error occurred. Please try again.",
};

/**
 * User-friendly error titles for UI display
 */
export const MESSAGING_ERROR_TITLES: Record<MessagingErrorType, string> = {
  user_blocked: "Cannot Send Message",
  user_blocked_by_you: "User Blocked",
  rate_limit_exceeded: "Rate Limit Reached",
  self_message: "Invalid Action",
  user_not_found: "User Not Found",
  thread_not_found: "Conversation Not Found",
  unauthorized: "Access Denied",
  encryption_failed: "Encryption Error",
  decryption_failed: "Decryption Error",
  websocket_auth_failed: "Connection Error",
  websocket_timeout: "Connection Timeout",
  unknown: "Error",
};

/**
 * User action suggestions for each error type
 */
export const MESSAGING_ERROR_ACTIONS: Record<MessagingErrorType, string[]> = {
  user_blocked: [
    "This user has blocked you from sending messages.",
    "You will not be able to contact them unless they unblock you.",
  ],
  user_blocked_by_you: [
    "Go to your settings to unblock this user.",
    "Once unblocked, you can send messages again.",
  ],
  rate_limit_exceeded: [
    "You can message users you've already matched with at any time.",
    "Wait 72 hours before messaging a new user.",
    "This helps maintain healthy communication on the platform.",
  ],
  self_message: [
    "You cannot send messages to your own account.",
  ],
  user_not_found: [
    "This user may have deleted their account.",
    "Their profile is no longer available.",
  ],
  thread_not_found: [
    "This conversation may have been deleted.",
    "Try refreshing your messages.",
  ],
  unauthorized: [
    "You don't have permission to access this conversation.",
    "Please contact support if you believe this is an error.",
  ],
  encryption_failed: [
    "There was a problem securing your message.",
    "Please try sending again.",
  ],
  decryption_failed: [
    "There was a problem reading this message.",
    "The message may be corrupted.",
  ],
  websocket_auth_failed: [
    "Your connection could not be authenticated.",
    "Try refreshing the page.",
  ],
  websocket_timeout: [
    "Connection timed out after 10 seconds.",
    "Check your internet connection and try again.",
  ],
  unknown: [
    "Something went wrong.",
    "Please try again or contact support if the problem persists.",
  ],
};

/**
 * Parse error from API response
 */
export function parseMessagingError(error: any): MessagingError {
  // Extract error type from response
  let errorType: MessagingErrorType = 'unknown';
  let message = MESSAGING_ERROR_MESSAGES.unknown;
  let statusCode: number | undefined;

  if (error.response) {
    statusCode = error.response.status;
    const detail = error.response.data?.detail || error.response.data?.message || error.message;

    // Match error message to error type
    if (typeof detail === 'string') {
      for (const [type, msg] of Object.entries(MESSAGING_ERROR_MESSAGES)) {
        if (detail.includes(msg) || detail.toLowerCase().includes(type.replace(/_/g, ' '))) {
          errorType = type as MessagingErrorType;
          message = msg;
          break;
        }
      }
    }

    // Special handling for HTTP status codes
    if (statusCode === 403) {
      if (detail.includes('blocked')) {
        errorType = detail.includes('you have blocked') ? 'user_blocked_by_you' : 'user_blocked';
      } else {
        errorType = 'unauthorized';
      }
    } else if (statusCode === 404) {
      errorType = detail.includes('thread') ? 'thread_not_found' : 'user_not_found';
    } else if (statusCode === 429) {
      errorType = 'rate_limit_exceeded';
    } else if (statusCode === 400 && detail.includes('yourself')) {
      errorType = 'self_message';
    } else if (statusCode === 500) {
      if (detail.includes('encrypt')) {
        errorType = 'encryption_failed';
      } else if (detail.includes('decrypt')) {
        errorType = 'decryption_failed';
      }
    }
  } else if (error.message) {
    // Handle WebSocket errors
    if (error.message.includes('authentication') || error.message.includes('auth')) {
      errorType = 'websocket_auth_failed';
    } else if (error.message.includes('timeout')) {
      errorType = 'websocket_timeout';
    }
    message = error.message;
  }

  return {
    type: errorType,
    message: MESSAGING_ERROR_MESSAGES[errorType],
    statusCode,
    details: typeof error.response?.data?.detail === 'string' ? error.response.data.detail : undefined,
  };
}

/**
 * Check if error is recoverable
 */
export function isRecoverableError(errorType: MessagingErrorType): boolean {
  const recoverableErrors: MessagingErrorType[] = [
    'encryption_failed',
    'decryption_failed',
    'websocket_auth_failed',
    'websocket_timeout',
    'unknown',
  ];
  return recoverableErrors.includes(errorType);
}

/**
 * Check if error should show "try again" button
 */
export function shouldShowRetry(errorType: MessagingErrorType): boolean {
  const retryableErrors: MessagingErrorType[] = [
    'encryption_failed',
    'websocket_auth_failed',
    'websocket_timeout',
    'unknown',
  ];
  return retryableErrors.includes(errorType);
}
