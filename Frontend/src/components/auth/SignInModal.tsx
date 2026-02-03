'use client';

import { useState, useRef, useCallback, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { authService } from "@/services/authService";
import GoogleSignIn from "@/components/auth/GoogleSignIn";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import Link from "next/link";
import Image from "next/image";
import { toast } from 'react-hot-toast';
import { Eye, EyeOff } from 'lucide-react';
import { useAuthStore } from "@/stores/authStore";

interface SignInModalProps {
  isOpen?: boolean;
  onOpenChange?: (open: boolean) => void;
  onSuccess?: () => void;
  onClose?: () => void;
  initialEmail?: string;
  lockEmail?: boolean;
}

interface SignUpResponse {
  message: string;
  access_token: string;
  user: {
    id: string;
    email: string;
    tenant_id: string;
    tenant_type: string;
    full_name: string;
    roles: string[];
  };
}

export default function SignInModal({ isOpen, onOpenChange, onSuccess, onClose, initialEmail, lockEmail }: SignInModalProps) {
  const [open, setOpen] = useState(isOpen ?? false);
  const [mode, setMode] = useState<'signin' | 'signup'>('signup');
  const [formData, setFormData] = useState({
    email: initialEmail || "",
    password: "",
    firstName: "",
    lastName: "",
    confirmPassword: ""
  });

  // Update email when initialEmail prop changes
  useEffect(() => {
    if (initialEmail) {
      setFormData(prev => ({ ...prev, email: initialEmail }));
    }
  }, [initialEmail]);
  const [rememberMe, setRememberMe] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);
  const isMountedRef = useRef(true);

  // Get auth store action for registration
  const setToken = useAuthStore((state) => state.setToken);

  // Track mount status
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
    };
  }, []);

  // Sanitize input to prevent XSS
  const sanitizeInput = useCallback((input: string, maxLength: number): string => {
    return input
      .replace(/<[^>]*>/g, '') // Remove HTML tags
      .slice(0, maxLength);
  }, []);

  // Validate sign in form
  const validateSignInForm = useCallback((): boolean => {
    const email = (formData.email || '').trim().toLowerCase();
    if (!email || !formData.password) {
      toast.error("Please fill in all fields");
      return false;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      toast.error("Please enter a valid email address");
      return false;
    }

    if (formData.password.length < 6) {
      toast.error("Password must be at least 6 characters");
      return false;
    }

    // Persist normalized email back into state for consistency
    if (formData.email !== email) {
      setFormData(prev => ({ ...prev, email }));
    }

    return true;
  }, [formData, setFormData]);

  // Validate sign up form
  const validateSignUpForm = useCallback((): string | null => {
    if (!formData.firstName || !formData.lastName) {
      return 'Please enter your first and last name';
    }

    const email = (formData.email || '').trim().toLowerCase();
    if (!email) {
      return 'Please enter your email address';
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      return 'Please enter a valid email address';
    }

    if (!formData.password) {
      return 'Please enter a password';
    }

    if (formData.password.length < 8) {
      return 'Password must be at least 8 characters long';
    }

    const hasUpperCase = /[A-Z]/.test(formData.password);
    const hasLowerCase = /[a-z]/.test(formData.password);
    const hasNumber = /[0-9]/.test(formData.password);
    const hasSpecialChar = /[!@#$%^&*(),.?":{}|<>]/.test(formData.password);

    const missing = [];
    if (!hasUpperCase) missing.push('uppercase letter');
    if (!hasLowerCase) missing.push('lowercase letter');
    if (!hasNumber) missing.push('number');
    if (!hasSpecialChar) missing.push('special character');

    if (missing.length > 0) {
      return `Password must contain: ${missing.join(', ')}`;
    }

    if (formData.password !== formData.confirmPassword) {
      return 'Passwords do not match';
    }

    // Persist normalized email back into state
    if (formData.email !== email) {
      setFormData(prev => ({ ...prev, email }));
    }

    return null;
  }, [formData, setFormData]);

  // Sync local state with prop changes
  useEffect(() => {
    setOpen(isOpen ?? false);
  }, [isOpen]);

  // Handle sign in submission
  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateSignInForm()) return;
    
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
        console.log('🔐 SignInModal: Attempting login with:', { email: sanitizedEmail });
      }

      // Login via authService - this updates the global auth store
      await authService.login({
        email: sanitizedEmail,
        password: sanitizedPassword,
      });

      // Check if request was aborted
      if (abortControllerRef.current?.signal.aborted) {
        return;
      }

      if (process.env.NODE_ENV === 'development') {
        console.log('✅ SignInModal: Login successful, token updated in store');
      }

      toast.success("Login successful!");

      // Store "keep me logged in" preference
      if (rememberMe) {
        localStorage.setItem('rememberMe', 'true');
      } else {
        localStorage.removeItem('rememberMe');
      }

      // Close modal
      const newOpenState = false;
      setOpen(newOpenState);
      if (onOpenChange) {
        onOpenChange(newOpenState);
      }

      // Call success callback if provided
      if (onSuccess) {
        onSuccess();
      }

    } catch (error: any) {
      // Don't show errors if request was aborted
      if (error.name === 'AbortError' || abortControllerRef.current?.signal.aborted) {
        return;
      }

      if (process.env.NODE_ENV === 'development') {
        console.error('❌ SignInModal: Login error:', error);
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
          errorMessage = error.message;
        }
      }
      
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

  // Handle sign up submission
  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault();

    // Validate form
    const validationError = validateSignUpForm();
    if (validationError) {
      toast.error(validationError);
      return;
    }

    // Cancel any existing request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    // Create new AbortController
    abortControllerRef.current = new AbortController();

    setIsLoading(true);
    setIsAuthenticating(true);

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL;
      const full_name = `${formData.firstName} ${formData.lastName}`.trim();

      if (process.env.NODE_ENV === 'development') {
        console.log('📝 Registering user:', { email: formData.email, full_name });
      }

      const response = await fetch(`${API_URL}/api/v2/auth/signup/direct`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: (formData.email || '').trim().toLowerCase(),
          password: formData.password,
          full_name: full_name,
        }),
        signal: abortControllerRef.current.signal,
      });

      // Parse response
      let data: SignUpResponse | any;
      try {
        data = await response.json();
      } catch (parseError) {
        if (process.env.NODE_ENV === 'development') {
          console.error('❌ Failed to parse response:', parseError);
        }
        throw new Error('Invalid response from server');
      }

      // Check if response is OK
      if (!response.ok) {
        const errorMessage = data?.message || data?.detail || data?.error || `Sign up failed (${response.status})`;
        if (process.env.NODE_ENV === 'development') {
          console.error('❌ Sign up failed:', { status: response.status, data });
        }
        throw new Error(errorMessage);
      }

      // Check if component is still mounted
      if (!isMountedRef.current) {
        if (process.env.NODE_ENV === 'development') {
          console.log('⚠️ Component unmounted, skipping state updates');
        }
        return;
      }

      if (process.env.NODE_ENV === 'development') {
        console.log('✅ Registration successful, starting authentication flow');
      }

      // Update the access token
      setToken(data.access_token);

      toast.success('Account created successfully!');

      // Login via authService - this updates the global auth store
      if (process.env.NODE_ENV === 'development') {
        console.log('🔐 Starting auto-login...');
      }

      await authService.login({
        email: formData.email,
        password: formData.password,
      });

      if (process.env.NODE_ENV === 'development') {
        console.log('✅ Auto-login completed successfully');
      }

      // Check if component is still mounted before proceeding
      if (!isMountedRef.current) {
        if (process.env.NODE_ENV === 'development') {
          console.log('⚠️ Component unmounted after login, skipping cleanup');
        }
        return;
      }

      // Reset form
      setFormData({
        email: '',
        password: '',
        firstName: '',
        lastName: '',
        confirmPassword: ''
      });

      if (process.env.NODE_ENV === 'development') {
        console.log('🎉 Authentication complete, preparing to close modal');
      }

      // Wait to ensure all state updates are complete
      await new Promise(resolve => setTimeout(resolve, 300));

      // Mark authentication as complete BEFORE closing
      setIsAuthenticating(false);
      setIsLoading(false);

      // Small additional delay before triggering callbacks
      await new Promise(resolve => setTimeout(resolve, 100));

      // Close modal
      const newOpenState = false;
      setOpen(newOpenState);
      if (onOpenChange) {
        if (process.env.NODE_ENV === 'development') {
          console.log('📤 Calling onOpenChange(false)');
        }
        onOpenChange(newOpenState);
      }

      // Call success callback
      if (onSuccess) {
        if (process.env.NODE_ENV === 'development') {
          console.log('📤 Calling onSuccess()');
        }
        onSuccess();
      }

    } catch (error: any) {
      // Don't show errors if request was aborted or component unmounted
      if (error.name === 'AbortError' || !isMountedRef.current) {
        return;
      }

      if (process.env.NODE_ENV === 'development') {
        console.error('❌ Sign up error:', error);
      }

      // Enhanced error messages
      let errorMessage = 'Failed to create account. Please try again.';
      
      if (error.message) {
        if (error.message.includes('already exists') || error.message.includes('409')) {
          errorMessage = 'An account with this email already exists.';
        } else if (error.message.includes('Invalid') || error.message.includes('422')) {
          errorMessage = 'Invalid input. Please check your information.';
        } else if (error.message.includes('Network') || error.message.includes('fetch')) {
          errorMessage = 'Network error. Please check your connection.';
        } else if (error.message.includes('500')) {
          errorMessage = 'Server error. Please try again later.';
        } else if (error.message !== 'Failed to create account. Please try again.') {
          errorMessage = error.message;
        }
      }

      toast.error(errorMessage);
      
      // Reset authentication state on error
      setIsAuthenticating(false);
      setIsLoading(false);
      
      // Clear password fields on error for security
      setFormData(prev => ({
        ...prev,
        password: '',
        confirmPassword: ''
      }));
    } finally {
      abortControllerRef.current = null;
    }
  };

  const handleOpenChange = useCallback((newOpen: boolean) => {
    // Prevent closing if authenticating
    if (!newOpen && isAuthenticating) {
      if (process.env.NODE_ENV === 'development') {
        console.log('🚫 Blocked modal close - authentication in progress');
      }
      return;
    }

    setOpen(newOpen);
    if (onOpenChange) {
      onOpenChange(newOpen);
    }
    // Call onClose when modal is closed
    if (!newOpen && onClose) {
      onClose();
    }
  }, [onOpenChange, onClose, isAuthenticating]);

  // Toggle between sign in and sign up modes
  const toggleMode = () => {
    setMode(prev => prev === 'signin' ? 'signup' : 'signin');
    // Reset form when switching modes, but preserve email if locked
    setFormData(prev => ({
      email: lockEmail ? prev.email : "",
      password: "",
      firstName: "",
      lastName: "",
      confirmPassword: ""
    }));
  };

  // Determine if we're being controlled externally (no trigger needed)
  const isControlled = isOpen !== undefined;

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      {!isControlled && (
        <DialogTrigger asChild>
          <Button className="w-full" variant="default">Sign in</Button>
        </DialogTrigger>
      )}
      <DialogContent
        onInteractOutside={(e) => {
          // Prevent closing when clicking outside during authentication or when form has data
          if (isAuthenticating || formData.email || formData.firstName || formData.lastName) {
            e.preventDefault();
          }
        }}
        onEscapeKeyDown={(e) => {
          // Prevent closing on Escape key during authentication
          if (isAuthenticating) {
            e.preventDefault();
          }
        }}
      >
        <div className="flex flex-col items-center gap-2">
          <div
            className="flex size-11 shrink-0 items-center justify-center"
            aria-hidden="true"
          >
            <Link href="/" className="inline-block mb-2 hover:opacity-80 transition-opacity">
              <Image src="/images/logo/yuba-logo-icon-colored.png" alt="Yuba" width={80} height={80} priority />
            </Link>
          </div>
          <DialogHeader>
            <DialogTitle className="sm:text-center text-brand-500">
              {mode === 'signin' ? 'Welcome back' : 'Sign up to Yuba'}
            </DialogTitle>
            <DialogDescription className="sm:text-center">
              {mode === 'signin' 
                ? 'Enter your credentials to login to your account.'
                : 'We just need a few details to get you started.'}
            </DialogDescription>
          </DialogHeader>
        </div>

        {mode === 'signin' ? (
          // Sign In Form
          <form onSubmit={handleSignIn} className="space-y-5">
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="modal-email">Email</Label>
                <Input
                  id="modal-email"
                  placeholder="hi@yourcompany.com"
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData(prev => ({ ...prev, email: sanitizeInput(e.target.value, 254).toLowerCase() }))}
                  disabled={isLoading || lockEmail}
                  readOnly={lockEmail}
                  required
                  autoComplete="email"
                  className={lockEmail ? "bg-gray-100 dark:bg-gray-800 cursor-not-allowed" : ""}
                />
                {lockEmail && (
                  <p className="text-xs text-muted-foreground">
                    This email is linked to your invitation
                  </p>
                )}
              </div>
              <div className="space-y-2">
                <Label htmlFor="modal-password">Password</Label>
                <div className="relative">
                  <Input
                    id="modal-password"
                    placeholder="Enter your password"
                    type={showPassword ? 'text' : 'password'}
                    value={formData.password}
                    onChange={(e) => setFormData(prev => ({ ...prev, password: e.target.value }))}
                    disabled={isLoading}
                    required
                    autoComplete="current-password"
                    className="pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((prev) => !prev)}
                    className="absolute inset-y-0 right-2 flex items-center text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                    disabled={isLoading}
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>
            </div>
            <div className="flex justify-between items-center gap-2">
              <div className="flex items-center gap-2">
                <Checkbox 
                  id="modal-remember" 
                  checked={rememberMe}
                  onCheckedChange={(checked) => setRememberMe(checked === true)}
                  disabled={isLoading}
                />
                <Label
                  htmlFor="modal-remember"
                  className="font-normal text-muted-foreground"
                >
                  Remember me
                </Label>
              </div>
              <button
                type="button"
                onClick={toggleMode}
                className="text-sm underline hover:no-underline cursor-pointer text-brand-500 font-bold"
                disabled={isLoading}
              >
                Sign up
              </button>
            </div>
            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading ? "Signing in..." : "Sign in"}
            </Button>

            {/* Divider */}
            <div className="relative my-4">
              <div className="absolute inset-0 flex items-center">
                <span className="w-full border-t border-gray-300 dark:border-gray-600" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-white dark:bg-gray-900 px-2 text-muted-foreground">
                  Or continue with
                </span>
              </div>
            </div>

            {/* Google Sign-In */}
            <GoogleSignIn
              onSuccess={() => {
                const newOpenState = false;
                setOpen(newOpenState);
                if (onOpenChange) {
                  onOpenChange(newOpenState);
                }
                if (onSuccess) {
                  onSuccess();
                }
              }}
              onError={(error) => {
                toast.error(error);
              }}
              disabled={isLoading}
              text="signin_with"
              className="w-full"
              skipRedirect={true}
            />
          </form>
        ) : (
          // Sign Up Form
          <form className="space-y-5" onSubmit={handleSignUp}>
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <Label htmlFor="modal-first-name" className="mb-1">First name</Label>
                  <Input
                    id="modal-first-name"
                    placeholder="Jane"
                    type="text"
                    required
                    value={formData.firstName}
                    onChange={(e) => setFormData(prev => ({ ...prev, firstName: sanitizeInput(e.target.value, 50) }))}
                    disabled={isLoading}
                  />
                </div>
                <div>
                  <Label htmlFor="modal-last-name" className="mb-1">Last name</Label>
                  <Input
                    id="modal-last-name"
                    placeholder="Doe"
                    type="text"
                    required
                    value={formData.lastName}
                    onChange={(e) => setFormData(prev => ({ ...prev, lastName: sanitizeInput(e.target.value, 50) }))}
                    disabled={isLoading}
                  />
                </div>
              </div>
              <div>
                <Label htmlFor="modal-signup-email" className="mb-1">Email</Label>
                <Input
                  id="modal-signup-email"
                  placeholder="hi@yourcompany.com"
                  type="email"
                  required
                  value={formData.email}
                  onChange={(e) => setFormData(prev => ({ ...prev, email: sanitizeInput(e.target.value, 254).toLowerCase() }))}
                  disabled={isLoading || lockEmail}
                  readOnly={lockEmail}
                  className={lockEmail ? "bg-gray-100 dark:bg-gray-800 cursor-not-allowed" : ""}
                />
                {lockEmail && (
                  <p className="text-xs text-muted-foreground">
                    This email is linked to your invitation
                  </p>
                )}
              </div>
              <div>
                <Label htmlFor="modal-signup-password" className="mb-1">Password</Label>
                <div className="relative">
                  <Input
                    id="modal-signup-password"
                    placeholder="Enter your password"
                    type={showPassword ? 'text' : 'password'}
                    required
                    className="pr-10"
                    value={formData.password}
                    onChange={(e) => setFormData(prev => ({ ...prev, password: sanitizeInput(e.target.value, 128) }))}
                    disabled={isLoading}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((prev) => !prev)}
                    className="absolute inset-y-0 right-2 flex items-center text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                    disabled={isLoading}
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  Must be 8+ characters with uppercase, lowercase, number, and special character
                </p>
              </div>
              <div>
                <Label htmlFor="modal-confirm-password" className="mb-1">Confirm password</Label>
                <div className="relative">
                  <Input
                    id="modal-confirm-password"
                    placeholder="Re-enter your password"
                    type={showConfirmPassword ? 'text' : 'password'}
                    required
                    className="pr-10"
                    value={formData.confirmPassword}
                    onChange={(e) => setFormData(prev => ({ ...prev, confirmPassword: sanitizeInput(e.target.value, 128) }))}
                    disabled={isLoading}
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword((prev) => !prev)}
                    className="absolute inset-y-0 right-2 flex items-center text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                    aria-label={showConfirmPassword ? 'Hide confirm password' : 'Show confirm password'}
                    disabled={isLoading}
                  >
                    {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>
            </div>
            <div className="flex justify-between items-center">
              <button
                type="button"
                onClick={toggleMode}
                className="text-sm text-muted-foreground hover:text-foreground"
                disabled={isLoading}
              >
                Already have an account?{" "}
                <span className="underline hover:no-underline text-brand-500 font-bold">
                  Sign in
                </span>
              </button>
            </div>
            <Button type="submit" className="w-full" disabled={isLoading || isAuthenticating}>
              {isLoading ? 'Creating account...' : 'Sign up'}
            </Button>

            {/* Divider */}
            <div className="relative my-4">
              <div className="absolute inset-0 flex items-center">
                <span className="w-full border-t border-gray-300 dark:border-gray-600" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-white dark:bg-gray-900 px-2 text-muted-foreground">
                  Or continue with
                </span>
              </div>
            </div>

            {/* Google Sign-Up */}
            <GoogleSignIn
              onSuccess={() => {
                const newOpenState = false;
                setOpen(newOpenState);
                if (onOpenChange) {
                  onOpenChange(newOpenState);
                }
                if (onSuccess) {
                  onSuccess();
                }
              }}
              onError={(error) => {
                toast.error(error);
              }}
              disabled={isLoading || isAuthenticating}
              text="signup_with"
              className="w-full"
              skipRedirect={true}
            />

            <p className="text-center text-xs text-muted-foreground">
              By signing up you agree to our{" "}
              <a className="underline hover:no-underline" href="#">
                Terms
              </a>
              .
            </p>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
