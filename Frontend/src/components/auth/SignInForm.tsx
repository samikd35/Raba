"use client";
import { useState, useCallback, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { authService } from "@/services/authService";
import Checkbox from "@/components/form/input/Checkbox";
import Input from "@/components/form/input/InputField";
import Label from "@/components/form/Label";
import Button from "@/components/ui/button/Button";
import { EyeCloseIcon, EyeIcon } from "@/icons";
import Link from "next/link";
import toast from "react-hot-toast";
import { useUser } from "@/stores/authStore";
import GoogleSignIn from "./GoogleSignIn";

interface LoginFormData {
  email: string;
  password: string;
}

interface SignInFormProps {
  vbInvitationToken?: string | null;
  redirectUrl?: string | null;
}

// Input sanitization helper
const sanitizeInput = (input: string, maxLength: number): string => {
  return input
    .replace(/<[^>]*>/g, '') // Remove HTML tags
    .slice(0, maxLength)
    .trim();
};

// VB Token storage key
const VB_TOKEN_KEY = 'vb_invitation_token';

export default function SignInForm({ vbInvitationToken, redirectUrl }: SignInFormProps = {}) {
  const [showPassword, setShowPassword] = useState(false);
  const [isChecked, setIsChecked] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [formData, setFormData] = useState<LoginFormData>({
    email: "",
    password: "",
  });

  const router = useRouter();
  const user = useUser();
  const abortControllerRef = useRef<AbortController | null>(null);

  // Store VB token in localStorage when present
  useEffect(() => {
    if (vbInvitationToken) {
      if (process.env.NODE_ENV === 'development') {
        console.log('💾 Storing VB invitation token in localStorage');
      }
      localStorage.setItem(VB_TOKEN_KEY, vbInvitationToken);
    }
  }, [vbInvitationToken]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  // Memoized form validation
  const validateForm = useCallback(() => {
    const email = sanitizeInput(formData.email, 254).toLowerCase();
    const password = formData.password.slice(0, 128);

    if (!email) {
      toast.dismiss();
      toast.error("Email is required");
      return false;
    }

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      toast.dismiss();
      toast.error("Please enter a valid email");
      return false;
    }

    if (!password) {
      toast.dismiss();
      toast.error("Password is required");
      return false;
    }

    if (password.length < 6) {
      toast.dismiss();
      toast.error("Password must be at least 6 characters long");
      return false;
    }

    // Persist normalized email back to state for consistency
    if (formData.email !== email) {
      setFormData((prev) => ({ ...prev, email }));
    }

    return true;
  }, [formData, setFormData]);

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    // Normalize email input to lowercase as the user types
    const nextValue = name === 'email' ? value.toLowerCase() : value;
    setFormData((prev) => ({ ...prev, [name]: nextValue }));
  }, []);

  const togglePasswordVisibility = useCallback(() => {
    setShowPassword(prev => !prev);
  }, []);

  const getDashboardRoute = useCallback((userToCheck?: any) => {
    const currentUser = userToCheck || user;
    if (!currentUser?.roles) return '/choose-workspace';

    const roles = currentUser.roles;

    // Admin and Super Admin go straight to /admin
    if (roles[0] === 'super_admin' || roles[0] === 'admin') {
      return '/admin';
    } else {
      // Default fallback - workspace selection for unassigned users
      return '/choose-workspace';
    }
  }, [user]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) return;

    // Cancel any existing request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    // Create new AbortController for this request
    abortControllerRef.current = new AbortController();

    setIsLoading(true);

    try {
      // Sanitize inputs before sending
      const sanitizedEmail = sanitizeInput(formData.email, 254).toLowerCase();
      const sanitizedPassword = formData.password.slice(0, 128);

      if (process.env.NODE_ENV === 'development') {
        console.log('🔐 Attempting login with:', { email: sanitizedEmail });
      }

      // Login via authService - this returns the user data
      const userData = await authService.login({
        email: sanitizedEmail,
        password: sanitizedPassword,
      });

      // Check if request was aborted
      if (abortControllerRef.current?.signal.aborted) {
        return;
      }

      if (process.env.NODE_ENV === 'development') {
        console.log('✅ Login successful, user:', userData);
        console.log('🎭 User roles:', userData.roles);
        console.log('🏢 Tenant context:', {
          tenant_id: userData.tenant_id,
          tenant_type: userData.tenant_type
        });
      }

      toast.dismiss();
      toast.success("Login successful! Redirecting...");

      // Store "keep me logged in" preference
      if (isChecked) {
        localStorage.setItem('rememberMe', 'true');
      } else {
        localStorage.removeItem('rememberMe');
      }

      // Get the appropriate dashboard route based on user role
      // Use the userData directly since store might not be updated yet
      const dashboardRoute = getDashboardRoute(userData);

      if (process.env.NODE_ENV === 'development') {
        console.log('🚀 Redirecting to:', dashboardRoute);
        console.log('👤 User roles:', userData.roles);
        console.log('🏢 Tenant type:', userData.tenant_type);
      }

      // Add small delay to ensure auth state is fully persisted
      await new Promise(resolve => setTimeout(resolve, 100));

      // Redirect to the appropriate dashboard
      router.push(dashboardRoute);

    } catch (error: any) {
      // Don't show errors if request was aborted
      if (error.name === 'AbortError' || abortControllerRef.current?.signal.aborted) {
        return;
      }

      if (process.env.NODE_ENV === 'development') {
        console.error('❌ Login error:', error);
      }

      // Enhanced error handling with specific messages
      let errorMessage = 'Something went wrong. Please try again.';

      if (error.message) {
        if (error.message.includes('Invalid credentials') ||
          error.message.includes('Invalid email or password') ||
          error.message.includes('401')) {
          errorMessage = 'Invalid email or password. Please check your credentials.';
        } else if (error.message.includes('Network') ||
          error.message.includes('Failed to fetch') ||
          error.message.includes('fetch')) {
          errorMessage = 'Network error. Please check your connection and try again.';
        } else if (error.message.includes('429')) {
          errorMessage = 'Too many login attempts. Please wait a moment and try again.';
        } else if (error.message.includes('422')) {
          errorMessage = 'Invalid input. Please check your email and password format.';
        } else if (error.message.includes('403')) {
          errorMessage = 'Access denied. Please contact support.';
        } else if (error.message.includes('500')) {
          errorMessage = 'Server error. Please try again later.';
        } else {
          // Use the actual error message from the server if available
          errorMessage = error.message;
        }
      }

      toast.dismiss();
      toast.error(errorMessage);

      // Clear password field on error for security
      setFormData(prev => ({
        ...prev,
        password: ""
      }));
    } finally {
      setIsLoading(false);
      abortControllerRef.current = null;
    }
  };

  // Check if this is a VB invitation login
  const isVBInvitation = Boolean(vbInvitationToken);

return (
  <div className="flex flex-col flex-1 lg:w-1/2 w-full">
    <div className="flex flex-col justify-center flex-1 w-full max-w-md mx-auto">
      <div>
        <div className="mb-5 sm:mb-8">
          <h1 className="mb-2 font-semibold text-gray-900 dark:text-white text-title-sm sm:text-title-md">
            {isVBInvitation ? 'Venture Builder Invitation' : 'Sign In'}
          </h1>
          <p className="text-sm text-gray-600 dark:text-gray-300">
            {isVBInvitation
              ? 'Sign in with your existing account to accept the Venture Builder invitation'
              : 'Enter your email and password to sign in!'}
          </p>
          {isVBInvitation && (
            <div className="mt-3 p-3 bg-brand-50 dark:bg-brand-900/30 border border-brand-200 dark:border-brand-700 rounded-lg">
              <p className="text-xs text-brand-700 dark:text-brand-300">
                <strong>Note:</strong> After signing in, you'll be redirected to complete your Venture Builder profile setup.
              </p>
            </div>
          )}
        </div>
        
        <div>
          {/* Google Sign-In */}
          <GoogleSignIn
            onSuccess={() => {
              if (process.env.NODE_ENV === 'development') {
                console.log('✅ Google Sign-In successful');
              }
            }}
            onError={(error) => {
              toast.error(error);
            }}
            disabled={isLoading}
            text="signin_with"
            className="w-full"
          />

          <div className="relative py-3 sm:py-5">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-200 dark:border-gray-700"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="p-2 text-gray-500 dark:text-gray-400 bg-white dark:bg-gray-950 sm:px-5 sm:py-2 rounded-lg">
                Or
              </span>
            </div>
          </div>

            <form onSubmit={handleSubmit}>
              <div className="space-y-6">
                {/* Email */}
                <div>
                  <Label htmlFor="email">
                    Email <span className="text-error-500">*</span>
                  </Label>
                  <Input
                    id="email"
                    name="email"
                    type="email"
                    placeholder="info@gmail.com"
                    value={formData.email}
                    onChange={handleInputChange}
                    disabled={isLoading}
                    required
                    maxLength={254}
                    autoComplete="email"
                    aria-describedby="email-description"
                  />
                  <p id="email-description" className="sr-only">
                    Enter your email address
                  </p>
                </div>

                {/* Password */}
                <div>
                  <Label htmlFor="password">
                    Password <span className="text-error-500">*</span>
                  </Label>
                  <div className="relative">
                    <Input
                      id="password"
                      name="password"
                      type={showPassword ? "text" : "password"}
                      placeholder="Enter your password"
                      value={formData.password}
                      onChange={handleInputChange}
                      disabled={isLoading}
                      required
                      minLength={6}
                      maxLength={128}
                      autoComplete="current-password"
                      aria-describedby="password-description"
                    />
                    <span
                      onClick={togglePasswordVisibility}
                      className="absolute z-30 -translate-y-1/2 cursor-pointer right-4 top-1/2 p-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                      role="button"
                      tabIndex={0}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          togglePasswordVisibility();
                        }
                      }}
                      aria-label={showPassword ? "Hide password" : "Show password"}
                      aria-controls="password"
                    >
                      {showPassword ? (
                        <EyeIcon className="w-5 h-5 text-gray-600 dark:text-gray-300 hover:text-gray-800 dark:hover:text-white transition-colors" />
                      ) : (
                        <EyeCloseIcon className="w-5 h-5 text-gray-600 dark:text-gray-300 hover:text-gray-800 dark:hover:text-white transition-colors" />
                      )}
                    </span>
                  </div>
                  <p id="password-description" className="sr-only">
                    Enter your password. Must be at least 6 characters long.
                  </p>
                </div>

                {/* Remember Me & Forgot Password */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Checkbox
                      checked={isChecked}
                      onChange={setIsChecked}
                      disabled={isLoading}
                      id="remember-me"
                    />
                    <label
                      htmlFor="remember-me"
                      className="block font-normal text-gray-700 dark:text-gray-300 text-theme-sm cursor-pointer select-none"
                    >
                      Keep me logged in
                    </label>
                  </div>
                  <Link
                    href="/reset-password"
                    className="text-sm text-brand-600 hover:text-brand-700 dark:text-brand-400 dark:hover:text-brand-300 font-medium transition-colors"
                    onClick={(e) => isLoading && e.preventDefault()}
                  >
                    Forgot password?
                  </Link>
                </div>

                {/* Submit Button */}
                <div>
                  <Button
                    type="submit"
                    disabled={isLoading}
                    className="w-full bg-brand-600 hover:bg-brand-700 dark:bg-brand-500 dark:hover:bg-brand-600 text-white font-medium shadow-lg hover:shadow-xl transition-all duration-200"
                    size="sm"
                    aria-describedby="submit-description"
                  >
                    {isLoading ? (
                      <>
                        <svg
                          className="animate-spin -ml-1 mr-3 h-4 w-4 text-white"
                          xmlns="http://www.w3.org/2000/svg"
                          fill="none"
                          viewBox="0 0 24 24"
                          aria-hidden="true"
                        >
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        Signing in...
                      </>
                    ) : (
                      "Sign in"
                    )}
                  </Button>
                  <p id="submit-description" className="sr-only">
                    {isLoading ? "Signing in, please wait" : "Click to sign in"}
                  </p>
                </div>
              </div>
            </form>

            <div className="mt-6">
              <p className="text-sm font-normal text-center text-gray-700 dark:text-gray-300 sm:text-start">
                Don't have an account?{" "}
                <Link
                  href="/signup"
                  className="text-brand-600 hover:text-brand-700 dark:text-brand-400 dark:hover:text-brand-300 font-semibold transition-colors"
                  onClick={(e) => isLoading && e.preventDefault()}
                >
                  Sign Up
                </Link>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}