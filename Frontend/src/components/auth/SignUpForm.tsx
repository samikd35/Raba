"use client";
import { useState, useCallback, useMemo } from "react";
import Checkbox from "@/components/form/input/Checkbox";
import Input from "@/components/form/input/InputField";
import Label from "@/components/form/Label";
import Button from "@/components/ui/button/Button";
import { CheckCircleIcon, EnvelopeIcon } from "@/icons";
import Link from "next/link";
import toast from "react-hot-toast";
import GoogleSignIn from "./GoogleSignIn";


// ✅ Constants for better maintainability
const ERROR_MESSAGES = {
  NETWORK_ERROR: 'Network error. Please check your internet connection and try again.',
  CORS_ERROR: 'Connection blocked. Please contact support if this persists.',
  RATE_LIMIT: 'Too many attempts. Please try again in a few minutes.',
  EMAIL_ALREADY_REGISTERED: 'Email is already registered. Please try signing in instead.',
  SERVER_ERROR: 'Server error occurred. Please try again later.',
  SERVICE_UNAVAILABLE: 'Signup service not found. Please contact support.',
  VALIDATION_ERROR: 'Please check your email and try again.',
  UNKNOWN_ERROR: 'Failed to send signup link. Please try again.',
} as const;

const API_ENDPOINTS = {
  SEND_SIGNUP_LINK: '/api/v2/auth/signup/send-link',
} as const;

// ✅ Email validation regex (memoized)
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

interface SignUpFormData {
  email: string;
}

interface ApiError {
  message?: string;
  detail?: string;
  code?: string;
}

export default function SignUpForm() {
  const [isChecked, setIsChecked] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [emailSent, setEmailSent] = useState(false);
  const [attemptCount, setAttemptCount] = useState(0);
  const [emailError, setEmailError] = useState<string | null>(null);

  const [formData, setFormData] = useState<SignUpFormData>({
    email: "",
  });

  // ✅ Memoized validation function
  const validateEmailStep = useCallback(() => {
    const { email } = formData;
    const normalizedEmail = email.trim().toLowerCase();

    setEmailError(null);

    if (!normalizedEmail) {
      const error = "Email is required";
      setEmailError(error);
      toast.error(error);
      return false;
    }

    if (!EMAIL_REGEX.test(normalizedEmail)) {
      const error = "Please enter a valid email address";
      setEmailError(error);
      toast.error(error);
      return false;
    }

    if (!isChecked) {
      toast.error("You must agree to the Terms and Conditions");
      return false;
    }

    // ✅ Rate limiting check
    if (attemptCount >= 5) {
      toast.error(ERROR_MESSAGES.RATE_LIMIT);
      return false;
    }

    // ✅ Persist normalized lowercase email back to state
    if (email !== normalizedEmail) {
      setFormData((prev) => ({ ...prev, email: normalizedEmail }));
    }

    return true;
  }, [formData, isChecked, attemptCount, setFormData]);

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    // Clear error when user types
    if (name === 'email') setEmailError(null);
    const nextValue = name === 'email' ? value.toLowerCase() : value;
    setFormData(prev => ({
      ...prev,
      [name]: nextValue
    }));
  }, []);

  // ✅ Comprehensive error handler
  const handleApiError = useCallback((error: any, response?: Response) => {
    console.error('API Error:', { error, status: response?.status });

    // Network errors
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      return ERROR_MESSAGES.NETWORK_ERROR;
    }

    if (error.message.includes('CORS')) {
      return ERROR_MESSAGES.CORS_ERROR;
    }

    // HTTP status based errors
    if (response) {
      switch (response.status) {
        case 400:
          return ERROR_MESSAGES.EMAIL_ALREADY_REGISTERED;
        case 429:
          return ERROR_MESSAGES.RATE_LIMIT;
        case 500:
          return ERROR_MESSAGES.SERVER_ERROR;
        case 403:
          return ERROR_MESSAGES.SERVICE_UNAVAILABLE;
        case 404:
          return ERROR_MESSAGES.SERVICE_UNAVAILABLE;
        case 422:
          return ERROR_MESSAGES.VALIDATION_ERROR;
        default:
          return error.message || ERROR_MESSAGES.UNKNOWN_ERROR;
      }
    }

    return error.message || ERROR_MESSAGES.UNKNOWN_ERROR;
  }, []);

  // ✅ Send signup link with improved error handling
  const handleSendSignupLink = async (e?: React.FormEvent) => {
    e?.preventDefault();

    if (!validateEmailStep()) return;

    setIsLoading(true);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL;

      // ✅ Add timeout protection
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 30000); // 30s timeout

      const response = await fetch(`${apiUrl}${API_ENDPOINTS.SEND_SIGNUP_LINK}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: formData.email.trim().toLowerCase() // ✅ Normalize email
        }),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      let data: ApiError;
      try {
        data = await response.json();
      } catch (parseError) {
        console.error('JSON Parse Error:', parseError);
        throw new Error(`Server returned invalid response (Status: ${response.status})`);
      }

      if (!response.ok) {
        // ✅ Increment attempt count for rate limiting
        setAttemptCount(prev => prev + 1);

        const errorMessage = handleApiError(
          new Error(data?.message || data?.detail || `Server error (Status: ${response.status})`),
          response
        );
        throw new Error(errorMessage);
      }

      // ✅ Reset attempt count on success
      setAttemptCount(0);
      toast.success('Signup link sent! Please check your email to complete registration.');
      setEmailSent(true);

    } catch (error: any) {
      console.error('Send signup link error:', error);

      const errorMessage = handleApiError(error);
      toast.error(errorMessage);

      // ✅ Special handling for abort (timeout)
      if (error.name === 'AbortError') {
        toast.error('Request timed out. Please try again.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  // ✅ Reset form completely
  const handleResetForm = useCallback(() => {
    setEmailSent(false);
    setFormData({ email: '' });
    setIsChecked(false);
    setEmailError(null);
  }, []);

  // ✅ Memoized success component
  const SuccessMessage = useMemo(() => (
    <div className="flex flex-col items-center justify-center text-center animate-in fade-in zoom-in duration-300">
      <div className="w-16 h-16 bg-success-50 dark:bg-success-900/20 text-success-500 rounded-full flex items-center justify-center mb-5 ring-8 ring-success-50/50 dark:ring-success-900/10">
        <CheckCircleIcon className="w-8 h-8" />
      </div>

      <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2">
        Check your mail
      </h3>

      <p className="text-gray-600 dark:text-gray-300 max-w-sm mx-auto mb-6">
        We've sent a signup link to <span className="font-semibold text-gray-900 dark:text-white">{formData.email}</span>. Click the link to complete your registration.
      </p>

      <div className="w-full space-y-3">
        <Button
          onClick={handleSendSignupLink}
          disabled={isLoading}
          variant="outline"
          className="w-full justify-center"
        >
          {isLoading ? "Resending..." : "Resend email"}
        </Button>

        <button
          onClick={handleResetForm}
          className="text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 font-medium transition-colors"
        >
          Use a different email
        </button>
      </div>
    </div>
  ), [formData.email, isLoading, handleResetForm, handleSendSignupLink]);

  return (
    <div className="flex flex-col flex-1 lg:w-1/2 w-full overflow-y-auto no-scrollbar">
      <div className="flex flex-col justify-center flex-1 w-full max-w-md mx-auto">
        <div>


          <div className="mb-4">
            <h1 className="mb-2 font-bold text-brand-500 dark:text-white text-title-sm sm:text-title-md tracking-tight">
              Sign Up
            </h1>
            <p className="text-sm text-gray-600 dark:text-gray-300">
              {emailSent ?
                "Check your email for the signup link to complete registration!" :
                "Enter your email to get started!"
              }
            </p>



            {!emailSent && (
              <>
                <div className="my-2 mt-4">
                  <GoogleSignIn
                    onError={(error: string) => toast.error(error)}
                    disabled={isLoading}
                    className="w-full"
                    text="signup_with"
                  />
                </div>

                <div className="relative py-1">
                  <div className="absolute inset-0 flex items-center">
                    <div className="w-full border-t border-gray-200 dark:border-gray-700"></div>
                  </div>
                  <div className="relative flex justify-center text-sm">
                    <span className="px-4 py-1 text-gray-500 dark:text-gray-400 bg-white dark:bg-gray-950 text-xs tracking-wider font-medium rounded-lg">
                      Or
                    </span>
                  </div>
                </div>
              </>
            )}

            {/* ✅ Rate limit warning */}
            {attemptCount > 0 && attemptCount < 3 && (
              <div className="bg-amber-50 dark:bg-amber-900/20 text-amber-600 dark:text-amber-400 p-3 rounded-lg text-sm border border-amber-200 dark:border-amber-800 flex items-center gap-2">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                Attempt {attemptCount} of 5
              </div>
            )}
          </div>

          {!emailSent ? (
            <div>
              <form onSubmit={handleSendSignupLink}>
                <div className="space-y-3.5">
                  <div>
                    <Label htmlFor="email" className="mb-1">
                      Email address <span className="text-error-500">*</span>
                    </Label>
                    <div className="relative">
                      <Input
                        id="email"
                        name="email"
                        type="email"
                        placeholder="name@example.com"
                        value={formData.email}
                        onChange={handleInputChange}
                        disabled={isLoading}
                        required
                        error={!!emailError}
                        aria-describedby="email-help"
                        aria-invalid={!!emailError}
                        className="pl-4 pr-10"
                      />
                      <div className="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none text-gray-400">
                        <EnvelopeIcon className="w-5 h-5" />
                      </div>
                    </div>
                    {emailError && (
                      <p className="mt-1.5 text-xs text-error-500">{emailError}</p>
                    )}
                  </div>

                  <div className="flex items-start gap-3">
                    <Checkbox
                      id="terms"
                      className="w-5 h-5 mt-0.5"
                      checked={isChecked}
                      onChange={setIsChecked}
                      disabled={isLoading}
                    />
                    <Label htmlFor="terms" className="!text-sm font-normal text-gray-600 dark:text-gray-300 cursor-pointer select-none leading-tight">
                      By creating an account, you agree to the{" "}
                      <Link
                        href="/terms"
                        className="text-brand-600 dark:text-brand-400 font-medium hover:text-brand-700 dark:hover:text-brand-300 transition-colors hover:underline"
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        Terms and Conditions
                      </Link>{" "}
                      and{" "}
                      <Link
                        href="/privacy"
                        className="text-brand-600 dark:text-brand-400 font-medium hover:text-brand-700 dark:hover:text-brand-300 transition-colors hover:underline"
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        Privacy Policy
                      </Link>
                    </Label>
                  </div>

                  <div>
                    <Button
                      type="submit"
                      disabled={isLoading || attemptCount >= 5}
                      className="w-full bg-brand-600 hover:bg-brand-700 text-white shadow-lg hover:shadow-xl transition-all duration-200 py-3"
                    >
                      {isLoading ? (
                        <>
                          <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                          Sending Link...
                        </>
                      ) : (
                        attemptCount >= 5 ? "Too Many Attempts" : "Create Account"
                      )}
                    </Button>
                  </div>
                </div>
              </form>
            </div>
          ) : (
            SuccessMessage
          )}

          <div className="mt-4 pt-4 border-t border-gray-100 dark:border-gray-800">
            <p className="text-sm font-normal text-center text-gray-600 dark:text-gray-400">
              Already have an account?{" "}
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
  );
}