/**
 * Error Handler for Team Leader Workspace
 * Provides centralized error handling with user-friendly messages and appropriate actions
 */

import { toast } from "react-hot-toast";

/**
 * Enum defining all possible error types in the application
 */
export enum ErrorType {
  AUTHENTICATION_REQUIRED = 'auth_required',
  TOKEN_EXPIRED = 'token_expired',
  TOKEN_INVALID = 'token_invalid',
  INSUFFICIENT_PERMISSIONS = 'insufficient_permissions',
  TEAM_ALREADY_EXISTS = 'team_exists',
  INSUFFICIENT_CREDITS = 'insufficient_credits',
  NETWORK_ERROR = 'network_error',
  VALIDATION_ERROR = 'validation_error',
  NOT_FOUND = 'not_found',
  DUPLICATE_INVITATION = 'duplicate_invitation',
  RATE_LIMIT_EXCEEDED = 'rate_limit_exceeded',
  SERVER_ERROR = 'server_error',
  UNKNOWN_ERROR = 'unknown_error',
}

/**
 * Interface for structured error information
 */
interface ErrorInfo {
  type: ErrorType;
  message: string;
  originalError?: any;
  context?: string;
  statusCode?: number;
}

/**
 * ErrorHandler class provides centralized error handling functionality
 */
export class ErrorHandler {
  /**
   * Main error handling method
   * @param error - The error object to handle
   * @param context - Context where the error occurred (e.g., 'TeamCreation', 'MemberInvitation')
   * @param onAuthRequired - Optional callback for authentication required errors
   * @param onPermissionDenied - Optional callback for permission denied errors
   */
  static handle(
    error: any,
    context: string,
    options?: {
      onAuthRequired?: () => void;
      onPermissionDenied?: () => void;
      onTokenExpired?: () => void;
      silent?: boolean;
    }
  ): ErrorInfo {
    // Log error for debugging
    console.error(`[${context}]`, error);

    // Categorize the error
    const errorInfo = this.categorizeError(error, context);

    // Show user-friendly message (unless silent mode)
    if (!options?.silent) {
      const message = this.getUserMessage(errorInfo);
      toast.error(message);
    }

    // Handle specific error types with appropriate actions
    this.handleSpecificErrorType(errorInfo, options);

    return errorInfo;
  }

  /**
   * Categorize error by analyzing error object
   */
  private static categorizeError(error: any, context: string): ErrorInfo {
    // Handle axios/fetch errors
    if (error.response) {
      const statusCode = error.response.status;
      const data = error.response.data;

      switch (statusCode) {
        case 401:
          return {
            type: ErrorType.AUTHENTICATION_REQUIRED,
            message: data?.message || 'Authentication required',
            originalError: error,
            context,
            statusCode,
          };

        case 403:
          return {
            type: ErrorType.INSUFFICIENT_PERMISSIONS,
            message: data?.message || 'Insufficient permissions',
            originalError: error,
            context,
            statusCode,
          };

        case 404:
          return {
            type: ErrorType.NOT_FOUND,
            message: data?.message || 'Resource not found',
            originalError: error,
            context,
            statusCode,
          };

        case 409:
          // Check for specific conflict types
          if (data?.message?.includes('team already exists')) {
            return {
              type: ErrorType.TEAM_ALREADY_EXISTS,
              message: data.message,
              originalError: error,
              context,
              statusCode,
            };
          }
          if (data?.message?.includes('already invited') || data?.message?.includes('duplicate')) {
            return {
              type: ErrorType.DUPLICATE_INVITATION,
              message: data.message,
              originalError: error,
              context,
              statusCode,
            };
          }
          return {
            type: ErrorType.VALIDATION_ERROR,
            message: data?.message || 'Conflict occurred',
            originalError: error,
            context,
            statusCode,
          };

        case 422:
          return {
            type: ErrorType.VALIDATION_ERROR,
            message: data?.message || 'Validation failed',
            originalError: error,
            context,
            statusCode,
          };

        case 429:
          return {
            type: ErrorType.RATE_LIMIT_EXCEEDED,
            message: data?.message || 'Too many requests. Please try again later.',
            originalError: error,
            context,
            statusCode,
          };

        case 500:
        case 502:
        case 503:
        case 504:
          return {
            type: ErrorType.SERVER_ERROR,
            message: data?.message || 'Server error occurred',
            originalError: error,
            context,
            statusCode,
          };

        default:
          return {
            type: ErrorType.UNKNOWN_ERROR,
            message: data?.message || 'An unexpected error occurred',
            originalError: error,
            context,
            statusCode,
          };
      }
    }

    // Handle network errors
    if (error.message?.includes('Network Error') || error.message?.includes('fetch')) {
      return {
        type: ErrorType.NETWORK_ERROR,
        message: 'Network connection failed. Please check your internet connection.',
        originalError: error,
        context,
      };
    }

    // Handle token-related errors
    if (error.message?.includes('token expired') || error.message?.includes('Token expired')) {
      return {
        type: ErrorType.TOKEN_EXPIRED,
        message: 'Your invitation link has expired. Please request a new invitation.',
        originalError: error,
        context,
      };
    }

    if (error.message?.includes('invalid token') || error.message?.includes('Invalid token')) {
      return {
        type: ErrorType.TOKEN_INVALID,
        message: 'Invalid invitation link. Please check the link and try again.',
        originalError: error,
        context,
      };
    }

    // Handle credit-related errors
    if (error.message?.includes('insufficient credits') || error.message?.includes('Insufficient credits')) {
      return {
        type: ErrorType.INSUFFICIENT_CREDITS,
        message: 'Insufficient credits available. Please request more credits.',
        originalError: error,
        context,
      };
    }

    // Default unknown error
    return {
      type: ErrorType.UNKNOWN_ERROR,
      message: error.message || 'An unexpected error occurred',
      originalError: error,
      context,
    };
  }

  /**
   * Generate user-friendly error message
   */
  private static getUserMessage(errorInfo: ErrorInfo): string {
    const contextPrefix = errorInfo.context ? `[${errorInfo.context}] ` : '';

    switch (errorInfo.type) {
      case ErrorType.AUTHENTICATION_REQUIRED:
        return 'Please sign in to continue.';

      case ErrorType.TOKEN_EXPIRED:
        return 'Your invitation link has expired. Please request a new invitation from your administrator.';

      case ErrorType.TOKEN_INVALID:
        return 'Invalid invitation link. Please check the link or contact your administrator.';

      case ErrorType.INSUFFICIENT_PERMISSIONS:
        return 'You do not have permission to perform this action.';

      case ErrorType.TEAM_ALREADY_EXISTS:
        return 'You already own a team in this organization. Redirecting to your dashboard...';

      case ErrorType.INSUFFICIENT_CREDITS:
        return 'Insufficient credits available. Please request more credits from your organization admin.';

      case ErrorType.NETWORK_ERROR:
        return 'Network connection failed. Please check your internet connection and try again.';

      case ErrorType.VALIDATION_ERROR:
        return errorInfo.message || 'Please check your input and try again.';

      case ErrorType.NOT_FOUND:
        return 'The requested resource was not found. It may have been deleted or moved.';

      case ErrorType.DUPLICATE_INVITATION:
        return errorInfo.message || 'This user has already been invited.';

      case ErrorType.RATE_LIMIT_EXCEEDED:
        return 'Too many requests. Please wait a moment and try again.';

      case ErrorType.SERVER_ERROR:
        return 'A server error occurred. Please try again later or contact support if the problem persists.';

      case ErrorType.UNKNOWN_ERROR:
      default:
        return contextPrefix + (errorInfo.message || 'An unexpected error occurred. Please try again.');
    }
  }

  /**
   * Handle specific error types with appropriate actions
   */
  private static handleSpecificErrorType(
    errorInfo: ErrorInfo,
    options?: {
      onAuthRequired?: () => void;
      onPermissionDenied?: () => void;
      onTokenExpired?: () => void;
    }
  ): void {
    switch (errorInfo.type) {
      case ErrorType.AUTHENTICATION_REQUIRED:
        if (options?.onAuthRequired) {
          options.onAuthRequired();
        } else {
          // Default: redirect to sign-in
          if (typeof window !== 'undefined') {
            const currentPath = window.location.pathname;
            window.location.href = `/signin?returnUrl=${encodeURIComponent(currentPath)}`;
          }
        }
        break;

      case ErrorType.INSUFFICIENT_PERMISSIONS:
        if (options?.onPermissionDenied) {
          options.onPermissionDenied();
        } else {
          // Default: redirect to unauthorized page
          if (typeof window !== 'undefined') {
            setTimeout(() => {
              window.location.href = '/unauthorized';
            }, 2000);
          }
        }
        break;

      case ErrorType.TOKEN_EXPIRED:
        if (options?.onTokenExpired) {
          options.onTokenExpired();
        }
        break;

      case ErrorType.TEAM_ALREADY_EXISTS:
        // Redirect to dashboard after showing message
        if (typeof window !== 'undefined') {
          setTimeout(() => {
            window.location.href = '/admin/team-leader-dashboard';
          }, 2000);
        }
        break;

      default:
        // No specific action needed
        break;
    }
  }

  /**
   * Handle validation errors with field-specific messages
   */
  static handleValidationErrors(
    errors: Record<string, string[]> | string,
    context: string
  ): void {
    if (typeof errors === 'string') {
      toast.error(errors);
      return;
    }

    // Show first error for each field
    Object.entries(errors).forEach(([field, messages]) => {
      const message = Array.isArray(messages) ? messages[0] : messages;
      toast.error(`${field}: ${message}`);
    });
  }

  /**
   * Retry logic for failed operations
   */
  static async retry<T>(
    operation: () => Promise<T>,
    maxRetries: number = 2,
    context: string = 'Operation'
  ): Promise<T> {
    let lastError: any;

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        return await operation();
      } catch (error) {
        lastError = error;
        console.warn(`[${context}] Attempt ${attempt}/${maxRetries} failed:`, error);

        // Don't retry on certain error types
        const errorInfo = this.categorizeError(error, context);
        if (
          errorInfo.type === ErrorType.AUTHENTICATION_REQUIRED ||
          errorInfo.type === ErrorType.INSUFFICIENT_PERMISSIONS ||
          errorInfo.type === ErrorType.TOKEN_INVALID ||
          errorInfo.type === ErrorType.VALIDATION_ERROR
        ) {
          throw error;
        }

        // Wait before retrying (exponential backoff)
        if (attempt < maxRetries) {
          await new Promise(resolve => setTimeout(resolve, Math.pow(2, attempt) * 1000));
        }
      }
    }

    throw lastError;
  }
}

/**
 * Convenience function for handling errors in async operations
 */
export async function handleAsyncError<T>(
  operation: () => Promise<T>,
  context: string,
  options?: {
    onAuthRequired?: () => void;
    onPermissionDenied?: () => void;
    onTokenExpired?: () => void;
    silent?: boolean;
    retry?: boolean;
    maxRetries?: number;
  }
): Promise<T | null> {
  try {
    if (options?.retry) {
      return await ErrorHandler.retry(operation, options.maxRetries || 2, context);
    }
    return await operation();
  } catch (error) {
    ErrorHandler.handle(error, context, options);
    return null;
  }
}
