"use client";
import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import Input from "@/components/form/input/InputField";
import Label from "@/components/form/Label";
import Button from "@/components/ui/button/Button";
import Link from "next/link";
import toast from "react-hot-toast";

// ✅ Constants for better maintainability
const ERROR_MESSAGES = {
  NETWORK_ERROR: 'Network error. Please check your internet connection and try again.',
  CORS_ERROR: 'Connection blocked. Please contact support if this persists.',
  RATE_LIMIT: 'Too many attempts. Please try again in a few minutes.',
  USER_NOT_FOUND: 'No account found with this email address.',
  SERVER_ERROR: 'Server error occurred. Please try again later.',
  SERVICE_UNAVAILABLE: 'Reset password service not found. Please contact support.',
  VALIDATION_ERROR: 'Please check your email and try again.',
  UNKNOWN_ERROR: 'Failed to send reset link. Please try again.',
} as const;

const API_ENDPOINTS = {
  SEND_RESET_LINK: '/api/v2/auth/reset-password/send-link',
} as const;

// ✅ Email validation regex
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

interface ForgotPasswordFormData {
  email: string;
}

interface ApiError {
  message?: string;
  detail?: string;
  code?: string;
}

export default function ForgotPasswordForm() {
  const [isLoading, setIsLoading] = useState(false);
  const [emailSent, setEmailSent] = useState(false);
  const [attemptCount, setAttemptCount] = useState(0);
  const [formData, setFormData] = useState<ForgotPasswordFormData>({
    email: "",
  });

  const router = useRouter();

  // ✅ Memoized validation function
  const validateForm = useCallback(() => {
    const { email } = formData;
    
    if (!email.trim()) {
      toast.error("Email is required");
      return false;
    }
    
    if (!EMAIL_REGEX.test(email)) {
      toast.error("Please enter a valid email address");
      return false;
    }
    
    // ✅ Rate limiting check
    if (attemptCount >= 5) {
      toast.error(ERROR_MESSAGES.RATE_LIMIT);
      return false;
    }
    
    return true;
  }, [formData, attemptCount]);

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  }, []);

  // ✅ Comprehensive error handler
  const handleApiError = useCallback((error: any, response?: Response) => {
    if (process.env.NODE_ENV === 'development') {
      console.error('API Error:', { 
        error: error?.message || error, 
        status: response?.status,
        errorName: error?.name,
        fullError: error 
      });
    }

    // Network errors
    if (error?.name === 'TypeError' && error?.message?.includes('fetch')) {
      return ERROR_MESSAGES.NETWORK_ERROR;
    }
    
    if (error?.message?.includes('CORS')) {
      return ERROR_MESSAGES.CORS_ERROR;
    }

    // HTTP status based errors
    if (response) {
      switch (response.status) {
        case 404:
          return ERROR_MESSAGES.USER_NOT_FOUND;
        case 429:
          return ERROR_MESSAGES.RATE_LIMIT;
        case 500:
          return ERROR_MESSAGES.SERVER_ERROR;
        case 503:
          return ERROR_MESSAGES.SERVICE_UNAVAILABLE;
        case 422:
          return ERROR_MESSAGES.VALIDATION_ERROR;
        default:
          return ERROR_MESSAGES.UNKNOWN_ERROR;
      }
    }

    // API error messages
    if (error?.message) {
      return error.message;
    }

    return ERROR_MESSAGES.UNKNOWN_ERROR;
  }, []);

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) return;
    
    setIsLoading(true);
    setAttemptCount(prev => prev + 1);
    
    let response: Response | undefined;
    
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL;
      if (!apiUrl) {
        throw new Error('API URL not configured');
      }

      response = await fetch(`${apiUrl}${API_ENDPOINTS.SEND_RESET_LINK}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: formData.email.trim().toLowerCase(),
        }),
      });

      if (!response.ok) {
        let errorData;
        try {
          errorData = await response.json();
        } catch (jsonError) {
          errorData = { message: `HTTP ${response.status} - ${response.statusText}` };
        }
        
        const error = new Error(errorData.message || `HTTP ${response.status}`);
        error.name = 'APIError';
        throw error;
      }

      const data = await response.json();
      
      // ✅ Success handling
      setEmailSent(true);
      toast.success("Password reset link sent successfully! Check your email.");
      
      if (process.env.NODE_ENV === 'development') {
        console.log('Reset link sent:', data);
      }

    } catch (error: any) {
      const errorMessage = handleApiError(error, response);
      toast.error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, [formData, validateForm, handleApiError]);

  const handleResendEmail = useCallback(() => {
    setEmailSent(false);
    setAttemptCount(0);
  }, []);

  if (emailSent) {
    return (
      <div className="flex flex-col flex-1 lg:w-1/2 w-full">
        <div className="flex flex-col justify-center flex-1 w-full max-w-md mx-auto">
          <div>
            <div className="mb-5 sm:mb-8">
              <h1 className="mb-2 font-semibold text-gray-900 dark:text-white text-title-sm sm:text-title-md">
                Check Your Email
              </h1>
              <p className="text-sm text-gray-600 dark:text-gray-300">
                We've sent a password reset link to <strong className="text-gray-900 dark:text-white">{formData.email}</strong>
              </p>
            </div>

            <div className="space-y-6">
              <div className="p-4 bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-700 rounded-lg shadow-sm">
                <div className="flex">
                  <div className="flex-shrink-0">
                    <svg className="w-5 h-5 text-green-500 dark:text-green-400" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <div className="ml-3">
                    <h3 className="text-sm font-medium text-green-800 dark:text-green-200">
                      Email sent successfully!
                    </h3>
                    <div className="mt-2 text-sm text-green-700 dark:text-green-300">
                      <p>
                        Click the link in your email to reset your password. The link will expire in 1 hour.
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="text-center space-y-4">
                <p className="text-sm text-gray-600 dark:text-gray-300">
                  Didn't receive the email? Check your spam folder or
                </p>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleResendEmail}
                  className="w-full border-brand-500 dark:border-brand-400 text-brand-600 dark:text-brand-400 hover:bg-brand-50 dark:hover:bg-brand-900/20 transition-all duration-200"
                >
                  Send another email
                </Button>
              </div>

              <div className="text-center">
                <Link
                  href="/signin"
                  className="text-sm text-brand-600 hover:text-brand-700 dark:text-brand-400 dark:hover:text-brand-300 font-medium transition-colors inline-flex items-center gap-1"
                >
                  ← Back to Sign In
                </Link>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col flex-1 lg:w-1/2 w-full">
      <div className="flex flex-col justify-center flex-1 w-full max-w-md mx-auto">
        <div>
          <div className="mb-5 sm:mb-8">
            <h1 className="mb-2 font-semibold text-gray-900 dark:text-white text-title-sm sm:text-title-md">
              Forgot Password?
            </h1>
            <p className="text-sm text-gray-600 dark:text-gray-300">
              No worries! Enter your email address and we'll send you a link to reset your password.
            </p>
          </div>

          <form onSubmit={handleSubmit}>
            <div className="space-y-6">
              {/* Email */}
              <div>
                <Label htmlFor="email">
                  Email Address <span className="text-error-500">*</span>
                </Label>
                <Input
                  id="email"
                  name="email"
                  type="email"
                  placeholder="Enter your email address"
                  value={formData.email}
                  onChange={handleInputChange}
                  disabled={isLoading}
                  required
                />
              </div>

              {/* Submit Button */}
              <div>
                <Button 
                  type="submit" 
                  disabled={isLoading}
                  className="w-full bg-brand-600 hover:bg-brand-700 dark:bg-brand-500 dark:hover:bg-brand-600 text-white font-medium shadow-lg hover:shadow-xl transition-all duration-200"
                  size="sm"
                >
                  {isLoading ? (
                    <>
                      <svg className="animate-spin -ml-1 mr-3 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Sending reset link...
                    </>
                  ) : (
                    "Send Reset Link"
                  )}
                </Button>
              </div>
            </div>
          </form>

          <div className="mt-6">
            <p className="text-sm font-normal text-center text-gray-700 dark:text-gray-300 sm:text-start">
              Remember your password?{" "}
              <Link
                href="/signin"
                className="text-brand-600 hover:text-brand-700 dark:text-brand-400 dark:hover:text-brand-300 font-semibold transition-colors"
              >
                Sign In
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}