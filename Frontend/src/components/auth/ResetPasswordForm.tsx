"use client";
import Input from "@/components/form/input/InputField";
import Label from "@/components/form/Label";
import Button from "@/components/ui/button/Button";
import { ChevronLeftIcon, EyeIcon, EyeCloseIcon } from "@/icons";
import Link from "next/link";
import React, { useState, useCallback, useMemo, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";

// ✅ Constants for better maintainability
const ERROR_MESSAGES = {
  EMAIL_REQUIRED: "Email is required",
  INVALID_EMAIL: "Please enter a valid email address",
  PASSWORD_REQUIRED: "Password is required",
  PASSWORD_TOO_SHORT: "Password must be at least 8 characters long",
  PASSWORD_TOO_LONG: "Password must be less than 128 characters",
  PASSWORD_WEAK: "Password must contain uppercase, lowercase, and numbers",
  CONFIRM_PASSWORD_REQUIRED: "Please confirm your password",
  PASSWORDS_DONT_MATCH: "Passwords don't match",
  INVALID_TOKEN: "Invalid or expired reset token",
  TOKEN_EXPIRED: "Reset token has expired. Please request a new one.",
  NETWORK_ERROR: "Network error. Please check your internet connection and try again.",
  RATE_LIMIT: "Too many attempts. Please try again in a few minutes.",
  USER_NOT_FOUND: "No account found with this email address.",
  SERVER_ERROR: "Server error occurred. Please try again later.",
  SERVICE_UNAVAILABLE: "Password reset service is currently unavailable. Please try again later.",
  UNKNOWN_ERROR: "Failed to send reset instructions. Please try again or contact support if the problem persists.",
} as const;

const SUCCESS_MESSAGES = {
  DEFAULT: "Password reset link sent successfully",
  PASSWORD_RESET: "Password has been reset successfully",
  CHECK_SPAM: "Didn't receive the email? Check your spam folder or try again in a few minutes.",
} as const;

// ✅ Email validation regex
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

// ✅ Password validation regex
const PASSWORD_REGEX = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$/;

// ✅ Get API URL from environment with fallback
const getApiUrl = () => {
  return process.env.NEXT_PUBLIC_API_URL;
};

// ✅ Pure validation functions (no memoization needed for simple regex tests)
const validateEmail = (email: string): boolean => {
  return EMAIL_REGEX.test(email);
};

const validatePassword = (password: string): boolean => {
  return PASSWORD_REGEX.test(password);
};

export default function ResetPasswordForm() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = searchParams?.get('token');
  const isResetMode = !!token;

  // Forgot password state
  const [email, setEmail] = useState("");
  
  // Reset password state
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  
  // Common state
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [attemptCount, setAttemptCount] = useState(0);
  const [lastAttemptTime, setLastAttemptTime] = useState<number | null>(null);

  // ✅ Basic token validation - only check if token exists
  useEffect(() => {
    if (isResetMode && (!token || token.length === 0)) {
      setError(ERROR_MESSAGES.INVALID_TOKEN);
    }
  }, [isResetMode, token]);

  // ✅ Input sanitization function (simplified)
  const sanitizeInput = useCallback((input: string): string => {
    return input.trim().slice(0, 254);
  }, []);

  // ✅ Password sanitization
  const sanitizePassword = useCallback((input: string): string => {
    return input.slice(0, 128);
  }, []);

  // ✅ Comprehensive error handler
  const handleApiError = useCallback((error: any, response?: Response): string => {
    if (process.env.NODE_ENV === 'development') {
      console.error('Password reset error:', error);
    }

    // Network errors
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      return ERROR_MESSAGES.NETWORK_ERROR;
    }
    
    if (error.name === 'AbortError') {
      return 'Request timed out. Please try again.';
    }

    // API response errors
    if (response) {
      const status = response.status;
      
      switch (status) {
        case 400:
          return isResetMode ? ERROR_MESSAGES.INVALID_TOKEN : ERROR_MESSAGES.INVALID_EMAIL;
        case 404:
          return ERROR_MESSAGES.USER_NOT_FOUND;
        case 422:
          return isResetMode ? ERROR_MESSAGES.TOKEN_EXPIRED : ERROR_MESSAGES.INVALID_EMAIL;
        case 429:
          return ERROR_MESSAGES.RATE_LIMIT;
        case 500:
          return ERROR_MESSAGES.SERVER_ERROR;
        case 503:
          return ERROR_MESSAGES.SERVICE_UNAVAILABLE;
        default:
          return ERROR_MESSAGES.UNKNOWN_ERROR;
      }
    }

    // Generic error with message
    if (error.message && typeof error.message === 'string') {
      return error.message;
    }

    return ERROR_MESSAGES.UNKNOWN_ERROR;
  }, [isResetMode]);

  // ✅ Rate limiting check
  const checkRateLimit = useCallback((): boolean => {
    const now = Date.now();
    
    // Reset attempt count after 15 minutes
    if (lastAttemptTime && now - lastAttemptTime > 15 * 60 * 1000) {
      setAttemptCount(0);
      setLastAttemptTime(null);
      return true;
    }

    // Allow max 5 attempts
    if (attemptCount >= 5) {
      setError(ERROR_MESSAGES.RATE_LIMIT);
      return false;
    }

    // Minimum 30 seconds between attempts
    if (lastAttemptTime && now - lastAttemptTime < 30000) {
      setError("Please wait 30 seconds before trying again.");
      return false;
    }

    return true;
  }, [attemptCount, lastAttemptTime]);

  // ✅ Pure validation functions that return error messages
  const validateForgotPasswordForm = useCallback((): string | null => {
    const sanitizedEmail = sanitizeInput(email);

    if (!sanitizedEmail) {
      return ERROR_MESSAGES.EMAIL_REQUIRED;
    }

    if (!validateEmail(sanitizedEmail)) {
      return ERROR_MESSAGES.INVALID_EMAIL;
    }

    if (!checkRateLimit()) {
      return null; // checkRateLimit already sets the error
    }

    return null;
  }, [email, checkRateLimit, sanitizeInput]);

  // ✅ Pure validation functions that return error messages
  const validateResetPasswordForm = useCallback((): string | null => {
    if (!password) {
      return ERROR_MESSAGES.PASSWORD_REQUIRED;
    }

    if (password.length < 8) {
      return ERROR_MESSAGES.PASSWORD_TOO_SHORT;
    }

    if (password.length > 128) {
      return ERROR_MESSAGES.PASSWORD_TOO_LONG;
    }

    if (!validatePassword(password)) {
      return ERROR_MESSAGES.PASSWORD_WEAK;
    }

    if (!confirmPassword) {
      return ERROR_MESSAGES.CONFIRM_PASSWORD_REQUIRED;
    }

    if (password !== confirmPassword) {
      return ERROR_MESSAGES.PASSWORDS_DONT_MATCH;
    }

    if (!checkRateLimit()) {
      return null; // checkRateLimit already sets the error
    }

    return null;
  }, [password, confirmPassword, checkRateLimit]);

  // ✅ Reset form completely
  const resetForm = useCallback(() => {
    setIsSubmitted(false);
    setEmail("");
    setPassword("");
    setConfirmPassword("");
    setMessage("");
    setError("");
    setIsLoading(false);
  }, []);

  // ✅ Send password reset request
  const sendPasswordResetRequest = useCallback(async (email: string, signal?: AbortSignal) => {
    const apiUrl = getApiUrl();
    const response = await fetch(`${apiUrl}/api/v2/auth/reset-password/send-link`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email }),
      signal,
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    return { response, data };
  }, []);

  // ✅ Reset password with token
  const resetPasswordWithToken = useCallback(async (token: string, password: string, signal?: AbortSignal) => {
    const apiUrl = getApiUrl();
    const response = await fetch(`${apiUrl}/api/v2/auth/reset-password/confirm`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ token, new_password: password }),
      signal,
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    return { response, data };
  }, []);

  // ✅ Handle forgot password submission
  const handleForgotPasswordSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    
    setError("");
    const validationError = validateForgotPasswordForm();
    if (validationError) {
      setError(validationError);
      return;
    }

    setIsLoading(true);

    const sanitizedEmail = sanitizeInput(email);

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 30000);

      const { response, data } = await sendPasswordResetRequest(sanitizedEmail, controller.signal);
      
      clearTimeout(timeoutId);

      setAttemptCount(prev => prev + 1);
      setLastAttemptTime(Date.now());

      setMessage(data.message || SUCCESS_MESSAGES.DEFAULT);
      setIsSubmitted(true);

    } catch (error: unknown) {
      let errorMessage = ERROR_MESSAGES.UNKNOWN_ERROR;
      let response: Response | undefined;

      if (error instanceof Error) {
        if ('response' in error) {
          response = error.response as Response;
        }
        errorMessage = handleApiError(error, response);
      } else if (typeof error === 'string') {
        errorMessage = error;
      }

      setError(errorMessage);
      
      setAttemptCount(prev => prev + 1);
      setLastAttemptTime(Date.now());
    } finally {
      setIsLoading(false);
    }
  }, [email, validateForgotPasswordForm, sanitizeInput, sendPasswordResetRequest, handleApiError]);

  // ✅ Handle reset password submission
  const handleResetPasswordSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    
    setError("");
    const validationError = validateResetPasswordForm();
    if (validationError) {
      setError(validationError);
      return;
    }

    if (!token) {
      setError(ERROR_MESSAGES.INVALID_TOKEN);
      return;
    }

    setIsLoading(true);

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 30000);

      const { response, data } = await resetPasswordWithToken(token, password, controller.signal);
      
      clearTimeout(timeoutId);

      setAttemptCount(prev => prev + 1);
      setLastAttemptTime(Date.now());

      setMessage(data.message || SUCCESS_MESSAGES.PASSWORD_RESET);
      setIsSubmitted(true);

    } catch (error: unknown) {
      let errorMessage = ERROR_MESSAGES.UNKNOWN_ERROR;
      let response: Response | undefined;

      if (error instanceof Error) {
        if ('response' in error) {
          response = error.response as Response;
        }
        errorMessage = handleApiError(error, response);
      } else if (typeof error === 'string') {
        errorMessage = error;
      }

      setError(errorMessage);
      
      setAttemptCount(prev => prev + 1);
      setLastAttemptTime(Date.now());
    } finally {
      setIsLoading(false);
    }
  }, [password, token, validateResetPasswordForm, resetPasswordWithToken, handleApiError]);

  // ✅ Handle resend (only for forgot password mode)
  const handleResend = useCallback(async () => {
    setError("");
    const validationError = validateForgotPasswordForm();
    if (validationError) {
      setError(validationError);
      return;
    }

    setIsLoading(true);

    const sanitizedEmail = sanitizeInput(email);

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 30000);

      const { data } = await sendPasswordResetRequest(sanitizedEmail, controller.signal);
      
      clearTimeout(timeoutId);

      setAttemptCount(prev => prev + 1);
      setLastAttemptTime(Date.now());
      
      setMessage(data.message || "Reset instructions sent again. " + SUCCESS_MESSAGES.CHECK_SPAM);
      
    } catch (error: unknown) {
      let errorMessage = ERROR_MESSAGES.UNKNOWN_ERROR;
      let response: Response | undefined;

      if (error instanceof Error) {
        if ('response' in error) {
          response = error.response as Response;
        }
        errorMessage = handleApiError(error, response);
      }
      
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, [email, validateForgotPasswordForm, sanitizeInput, sendPasswordResetRequest, handleApiError]);

  // ✅ Handle input changes with sanitization
  const handleEmailChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const sanitizedValue = sanitizeInput(e.target.value);
    setEmail(sanitizedValue);
    if (error) {
      setError("");
    }
  }, [sanitizeInput, error]);

  const handlePasswordChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const sanitizedValue = sanitizePassword(e.target.value);
    setPassword(sanitizedValue);
    if (error) {
      setError("");
    }
  }, [sanitizePassword, error]);

  const handleConfirmPasswordChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const sanitizedValue = sanitizePassword(e.target.value);
    setConfirmPassword(sanitizedValue);
    if (error) {
      setError("");
    }
  }, [sanitizePassword, error]);

  // ✅ Password visibility toggles (no memoization needed)
  const togglePasswordVisibility = () => {
    setShowPassword(prev => !prev);
  };

  const toggleConfirmPasswordVisibility = () => {
    setShowConfirmPassword(prev => !prev);
  };

  // ✅ Redirect timeout with cleanup
  useEffect(() => {
    if (isSubmitted && isResetMode) {
      const timeoutId = setTimeout(() => {
        router.push('/signin');
      }, 2000);
      
      return () => clearTimeout(timeoutId);
    }
  }, [isSubmitted, isResetMode, router]);

  // ✅ Memoized success component
  const SuccessView = useMemo(() => (
    <div className="flex flex-col flex-1 lg:w-1/2 w-full">
      <div className="flex flex-col justify-center flex-1 w-full max-w-md mx-auto">
        <div className="text-center">
          <div className="mb-6">
            <div className="w-16 h-16 mx-auto mb-4 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center">
              <svg className="w-8 h-8 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h1 className="mb-2 font-semibold text-gray-900 dark:text-white text-title-sm sm:text-title-md">
              {isResetMode ? "Password Reset" : "Check Your Email"}
            </h1>
            <p className="text-sm text-gray-600 dark:text-gray-300 mb-4">
              {message}
            </p>
            {isResetMode ? (
              <p className="text-xs text-gray-400 dark:text-gray-500">
                You will be redirected to the signin page in 2 seconds.
              </p>
            ) : (
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {SUCCESS_MESSAGES.CHECK_SPAM}
              </p>
            )}
          </div>

          <div className="space-y-4">
            {isResetMode ? (
              <div className="text-center">
                <Link
                  href="/signin"
                  className="text-brand-600 hover:text-brand-700 dark:text-brand-400 dark:hover:text-brand-300 font-medium transition-colors"
                  prefetch={false}
                >
                  Go to Sign In
                </Link>
              </div>
            ) : (
              <Button 
                onClick={handleResend}
                disabled={isLoading || attemptCount >= 5}
                variant="outline"
                className="w-full border-brand-500 dark:border-brand-400 text-brand-600 dark:text-brand-400 hover:bg-brand-50 dark:hover:bg-brand-900/20 transition-all duration-200"
                size="sm"
              >
                {isLoading ? (
                  <div className="flex items-center justify-center">
                    <svg className="animate-spin -ml-1 mr-3 h-4 w-4 text-current" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Resending...
                  </div>
                ) : (
                  "Resend Instructions"
                )}
              </Button>
            )}
            
            <Button 
              onClick={resetForm}
              variant="ghost"
              className="w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
              size="sm"
            >
              Try Different Email
            </Button>
            
            <div className="text-center">
              <Link
                href="/signin"
                className="text-sm text-brand-600 hover:text-brand-700 dark:text-brand-400 dark:hover:text-brand-300 font-medium transition-colors inline-flex items-center"
                prefetch={false}
              >
                <ChevronLeftIcon className="w-4 h-4 mr-1" />
                Back to Sign In
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  ), [message, isLoading, attemptCount, handleResend, resetForm, isResetMode]);

  // ✅ Memoized form components for better performance
  const PasswordField = useMemo(() => (
    <div className="relative">
      <Label htmlFor="reset-password">
        New Password <span className="text-error-500 dark:text-red-400">*</span>
      </Label>
      <Input 
        id="reset-password"
        type={showPassword ? "text" : "password"}
        value={password}
        onChange={handlePasswordChange}
        disabled={isLoading}
        maxLength={128}
        className={error ? "border-red-300 focus:border-red-500 focus:ring-red-500 dark:border-red-600 dark:focus:border-red-500" : ""}
        aria-describedby={error ? "reset-error" : "reset-help"}
        aria-invalid={!!error}
      />
      <button 
        type="button"
        className="absolute right-3 top-8 p-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors cursor-pointer"
        onClick={togglePasswordVisibility}
        aria-label={showPassword ? "Hide password" : "Show password"}
      >
        {showPassword ? (
          <EyeCloseIcon className="w-5 h-5 text-gray-600 dark:text-gray-300 hover:text-gray-800 dark:hover:text-white transition-colors" />
        ) : (
          <EyeIcon className="w-5 h-5 text-gray-600 dark:text-gray-300 hover:text-gray-800 dark:hover:text-white transition-colors" />
        )}
      </button>
    </div>
  ), [password, showPassword, error, isLoading, handlePasswordChange]);

  const ConfirmPasswordField = useMemo(() => (
    <div className="relative">
      <Label htmlFor="reset-confirm-password">
        Confirm New Password <span className="text-error-500 dark:text-red-400">*</span>
      </Label>
      <Input 
        id="reset-confirm-password"
        type={showConfirmPassword ? "text" : "password"}
        value={confirmPassword}
        onChange={handleConfirmPasswordChange}
        disabled={isLoading}
        maxLength={128}
        className={error ? "border-red-300 focus:border-red-500 focus:ring-red-500 dark:border-red-600 dark:focus:border-red-500" : ""}
        aria-describedby={error ? "reset-error" : "reset-help"}
        aria-invalid={!!error}
      />
      <button 
        type="button"
        className="absolute right-3 top-8 p-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors cursor-pointer"
        onClick={toggleConfirmPasswordVisibility}
        aria-label={showConfirmPassword ? "Hide password" : "Show password"}
      >
        {showConfirmPassword ? (
          <EyeCloseIcon className="w-5 h-5 text-gray-600 dark:text-gray-300 hover:text-gray-800 dark:hover:text-white transition-colors" />
        ) : (
          <EyeIcon className="w-5 h-5 text-gray-600 dark:text-gray-300 hover:text-gray-800 dark:hover:text-white transition-colors" />
        )}
      </button>
    </div>
  ), [confirmPassword, showConfirmPassword, error, isLoading, handleConfirmPasswordChange]);

  const EmailField = useMemo(() => (
    <div>
      <Label htmlFor="reset-email">
        Email <span className="text-error-500 dark:text-red-400">*</span>
      </Label>
      <Input 
        id="reset-email"
        placeholder="info@gmail.com" 
        type="email"
        value={email}
        onChange={handleEmailChange}
        disabled={isLoading}
        maxLength={254}
        className={error ? "border-red-300 focus:border-red-500 focus:ring-red-500 dark:border-red-600 dark:focus:border-red-500" : ""}
        aria-describedby={error ? "reset-error" : "reset-help"}
        aria-invalid={!!error}
      />
    </div>
  ), [email, error, isLoading, handleEmailChange]);

  const ErrorMessage = useMemo(() => (
    error ? (
      <p id="reset-error" className="mt-2 text-sm text-red-600 dark:text-red-400" role="alert">
        {error}
      </p>
    ) : (
      <p id="reset-help" className="sr-only">
        {isResetMode ? "Enter your new password" : "Enter your email address to receive password reset instructions"}
      </p>
    )
  ), [error, isResetMode]);

  const RateLimitWarning = useMemo(() => (
    <>
      {attemptCount > 0 && attemptCount < 5 && (
        <p className="text-xs text-amber-600 dark:text-amber-400 mt-1">
          Attempt {attemptCount} of 5
        </p>
      )}
      {attemptCount >= 5 && (
        <p className="text-xs text-red-600 dark:text-red-400 mt-1">
          Too many attempts. Please try again in 15 minutes.
        </p>
      )}
    </>
  ), [attemptCount]);

  // ✅ Form view with optimized structure
  const FormView = useMemo(() => (
    <div className="flex flex-col flex-1 lg:w-1/2 w-full">
      <div className="flex flex-col justify-center flex-1 w-full max-w-md mx-auto">
        <div>
          <div className="mb-5 sm:mb-8">
            <h1 className="mb-2 font-semibold text-gray-900 dark:text-white text-title-sm sm:text-title-md">
              {isResetMode ? "Reset Password" : "Forgot Password"}
            </h1>
            <p className="text-sm text-gray-600 dark:text-gray-300">
              {isResetMode ? (
                "Enter your new password to reset your account."
              ) : (
                "Enter your email address and we'll send you instructions to reset your password."
              )}
            </p>
            {RateLimitWarning}
          </div>
          
          <div>
            <form onSubmit={isResetMode ? handleResetPasswordSubmit : handleForgotPasswordSubmit}>
              <div className="space-y-6">
                {isResetMode ? (
                  <>
                    {PasswordField}
                    {ConfirmPasswordField}
                  </>
                ) : (
                  EmailField
                )}
                
                {ErrorMessage}
                
                <div>
                  <Button 
                    type="submit"
                    className="w-full bg-brand-600 hover:bg-brand-700 dark:bg-brand-500 dark:hover:bg-brand-600 text-white font-medium shadow-lg hover:shadow-xl transition-all duration-200" 
                    size="sm"
                    disabled={isLoading || attemptCount >= 5}
                    aria-label={isLoading ? (isResetMode ? "Resetting password" : "Sending reset instructions") : (isResetMode ? "Reset Password" : "Send Reset Instructions")}
                  >
                    {isLoading ? (
                      <div className="flex items-center justify-center">
                        <svg className="animate-spin -ml-1 mr-3 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        {isResetMode ? "Resetting..." : "Sending..."}
                      </div>
                    ) : (
                      isResetMode ? (
                        attemptCount >= 5 ? "Too Many Attempts" : "Reset Password"
                      ) : (
                        attemptCount >= 5 ? "Too Many Attempts" : "Send Reset Instructions"
                      )
                    )}
                  </Button>
                </div>
              </div>
            </form>

            <div className="mt-6">
              <p className="text-sm font-normal text-center text-gray-700 dark:text-gray-300 sm:text-start">
                {isResetMode ? (
                  "Remember your old password? "
                ) : (
                  "Remember your password? "
                )}
                <Link
                  href="/signin"
                  className="text-brand-600 hover:text-brand-700 dark:text-brand-400 dark:hover:text-brand-300 font-semibold transition-colors"
                  prefetch={false}
                >
                  Sign In
                </Link>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  ), [
    isResetMode,
    RateLimitWarning,
    handleResetPasswordSubmit,
    handleForgotPasswordSubmit,
    PasswordField,
    ConfirmPasswordField,
    EmailField,
    ErrorMessage,
    isLoading,
    attemptCount
  ]);

  return isSubmitted ? SuccessView : FormView;
}