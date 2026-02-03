"use client";
import { useState, useEffect, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { InvitationFlowManager } from "@/lib/auth/invitationFlowManager";
import Input from "@/components/form/input/InputField";
import Label from "@/components/form/Label";
import { EyeCloseIcon, EyeIcon } from "@/icons";
import Link from "next/link";
import toast from "react-hot-toast";

interface SignUpVerifyData {
  firstName: string;
  lastName: string;
  password: string;
  confirmPassword: string;
  bio?: string;
  website?: string;
  location?: string;
}

export default function SignUpVerifyPage() {
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [tokenValid, setTokenValid] = useState<boolean | null>(null);
  
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get('token');
  
  const [formData, setFormData] = useState<SignUpVerifyData>({
    firstName: "",
    lastName: "",
    password: "",
    confirmPassword: "",
    bio: "",
    website: "",
    location: "",
  });

  // Check if token exists on mount
  useEffect(() => {
    if (!token) {
      setTokenValid(false);
      toast.error('Invalid signup link. Please request a new one.');
    } else {
      setTokenValid(true);
    }
  }, [token]);

  // URL validation utility
  const validateUrl = useCallback((url: string): boolean => {
    if (!url) return true; // Optional field
    try {
      const urlObj = new URL(url);
      return urlObj.protocol === 'http:' || urlObj.protocol === 'https:';
    } catch {
      return false;
    }
  }, []);

  // Enhanced form validation with memoization
  const validateForm = useCallback(() => {
    const { firstName, lastName, password, confirmPassword, website } = formData;
    
    if (!firstName.trim()) {
      toast.error("First name is required");
      return false;
    }
    
    if (firstName.trim().length > 50) {
      toast.error("First name must be less than 50 characters");
      return false;
    }
    
    if (!lastName.trim()) {
      toast.error("Last name is required");
      return false;
    }
    
    if (lastName.trim().length > 50) {
      toast.error("Last name must be less than 50 characters");
      return false;
    }
    
    if (!password) {
      toast.error("Password is required");
      return false;
    }
    
    if (password.length < 8) {
      toast.error("Password must be at least 8 characters long");
      return false;
    }
    
    if (password.length > 128) {
      toast.error("Password must be less than 128 characters");
      return false;
    }
    
    // Enhanced password strength validation
    const hasUpperCase = /[A-Z]/.test(password);
    const hasLowerCase = /[a-z]/.test(password);
    const hasNumbers = /\d/.test(password);
    
    if (!hasUpperCase || !hasLowerCase || !hasNumbers) {
      toast.error("Password must contain at least one uppercase letter, one lowercase letter, and one number");
      return false;
    }
    
    if (password !== confirmPassword) {
      toast.error("Passwords do not match");
      return false;
    }
    
    // Validate website URL if provided
    if (website && !validateUrl(website)) {
      toast.error("Please enter a valid URL starting with http:// or https://");
      return false;
    }
    
    return true;
  }, [formData, validateUrl]);

  // Memoized input change handler
  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    
    // Input sanitization
    let sanitizedValue = value;
    
    // Sanitize text inputs to prevent XSS
    if (name === 'firstName' || name === 'lastName' || name === 'bio' || name === 'location') {
      sanitizedValue = value.replace(/<[^>]*>/g, ''); // Remove HTML tags
    }
    
    // Limit input lengths
    const maxLengths: Record<string, number> = {
      firstName: 50,
      lastName: 50,
      password: 128,
      confirmPassword: 128,
      bio: 500,
      website: 200,
      location: 100
    };
    
    if (maxLengths[name] && sanitizedValue.length > maxLengths[name]) {
      return; // Don't update if exceeds max length
    }
    
    setFormData(prev => ({
      ...prev,
      [name]: sanitizedValue
    }));
  }, []);

  // Reset form function
  const resetForm = useCallback(() => {
    setFormData({
      firstName: "",
      lastName: "",
      password: "",
      confirmPassword: "",
      bio: "",
      website: "",
      location: "",
    });
  }, []);

  const handleCompleteSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) return;
    
    if (!token) {
      toast.error('Invalid signup link. Please request a new one.');
      return;
    }
    
    setIsLoading(true);
    
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL ;
      
      if (process.env.NODE_ENV === 'development') {
        console.log('Completing signup with token:', token);
      }
      
      const response = await fetch(`${apiUrl}/api/v2/auth/signup/verify`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          token: token,
          password: formData.password,
          full_name: `${formData.firstName} ${formData.lastName}`.trim(),
          bio: formData.bio || "",
          website: formData.website || "",
          location: formData.location || "",
          timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
          preferences: {}
        }),
      });

      const data = await response.json();
      
      if (process.env.NODE_ENV === 'development') {
        console.log('Signup verification response:', data);
      }

      if (!response.ok) {
        if (response.status === 400) {
          throw new Error('Invalid or expired signup link. Please request a new one.');
        } else if (response.status === 422) {
          throw new Error('Invalid data provided. Please check your inputs and try again.');
        } else if (response.status === 409) {
          throw new Error('An account with this email already exists. Please sign in instead.');
        } else if (response.status >= 500) {
          throw new Error('Server error. Please try again later.');
        }
        throw new Error(data.message || 'Failed to complete signup');
      }

      toast.success('Account created successfully! Redirecting...');
      
      // Reset form
      resetForm();

      // Check for stored invitation token (from InvitationFlowManager)
      const storedToken = InvitationFlowManager.getStoredInvitationToken();
      
      if (storedToken && !InvitationFlowManager.isTokenExpired(storedToken)) {
        // Redirect to invitation flow based on token type
        const redirectUrl = InvitationFlowManager.getPostAuthRedirectUrl(storedToken);
        router.push(redirectUrl);
        return;
      }

      // Default: Redirect to sign in page
      router.push('/signin');

    } catch (error) {
      if (process.env.NODE_ENV === 'development') {
        console.error('Complete signup error:', error);
      }
      
      const errorMessage = error instanceof Error ? error.message : 'Failed to complete signup. Please try again.';
      toast.error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  // Show loading state while checking token
  if (tokenValid === null) {
    return (
      <div className="flex flex-col flex-1 lg:w-1/2 w-full overflow-y-auto no-scrollbar">
        <div className="flex flex-col justify-center flex-1 w-full max-w-md mx-auto">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-500 mx-auto"></div>
            <p className="mt-4 text-gray-500">Verifying signup link...</p>
          </div>
        </div>
      </div>
    );
  }

  // Show error state for invalid token
  if (tokenValid === false) {
    return (
      <div className="flex flex-col flex-1 lg:w-1/2 w-full overflow-y-auto no-scrollbar">
        <div className="flex flex-col justify-center flex-1 w-full max-w-md mx-auto">
          <div className="text-center">
            <div className="mb-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
              <p className="text-red-700 dark:text-red-300 font-medium">
                Invalid Signup Link
              </p>
              <p className="text-sm text-red-600 dark:text-red-400 mt-2">
                This signup link is invalid or has expired. Please request a new one.
              </p>
            </div>
            
            <Link
              href="/signup"
              className="inline-flex items-center justify-center px-4 py-2 text-sm font-medium text-white transition rounded-lg bg-brand-500 hover:bg-brand-600"
            >
              Request New Signup Link
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // Render signup completion form
  return (
    <div className="flex flex-col flex-1 lg:w-1/2 w-full overflow-y-auto no-scrollbar">
      <div className="flex flex-col justify-center flex-1 w-full max-w-md mx-auto py-16">
        <div>
          <div className="mb-5 sm:mb-8">
            <h1 className="mb-2 font-semibold text-gray-800 text-title-sm dark:text-white/90 sm:text-title-md">
              Complete Your Registration
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Fill in your details to complete your account setup!
            </p>
          </div>
          
          <form onSubmit={handleCompleteSignup}>
            <div className="space-y-5">
              <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
                {/* First Name */}
                <div className="sm:col-span-1">
                  <Label htmlFor="firstName">
                    First Name<span className="text-error-500">*</span>
                  </Label>
                  <Input
                    id="firstName"
                    name="firstName"
                    type="text"
                    placeholder="Enter your first name"
                    value={formData.firstName}
                    onChange={handleInputChange}
                    disabled={isLoading}
                    required
                    maxLength={50}
                  />
                </div>
                
                {/* Last Name */}
                <div className="sm:col-span-1">
                  <Label htmlFor="lastName">
                    Last Name<span className="text-error-500">*</span>
                  </Label>
                  <Input
                    id="lastName"
                    name="lastName"
                    type="text"
                    placeholder="Enter your last name"
                    value={formData.lastName}
                    onChange={handleInputChange}
                    disabled={isLoading}
                    required
                    maxLength={50}
                  />
                </div>
              </div>
              
              {/* Password */}
              <div>
                <Label htmlFor="password">
                  Password<span className="text-error-500">*</span>
                </Label>
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
                  Must be at least 8 characters with uppercase, lowercase, and number
                </p>
                <div className="relative">
                  <Input
                    id="password"
                    name="password"
                    placeholder="Enter your password"
                    type={showPassword ? "text" : "password"}
                    value={formData.password}
                    onChange={handleInputChange}
                    disabled={isLoading}
                    required
                    minLength={8}
                    maxLength={128}
                  />
                  <span
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute z-30 -translate-y-1/2 cursor-pointer right-4 top-1/2"
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        setShowPassword(!showPassword);
                      }
                    }}
                  >
                    {showPassword ? (
                      <EyeIcon className="fill-gray-500 dark:fill-gray-400" />
                    ) : (
                      <EyeCloseIcon className="fill-gray-500 dark:fill-gray-400" />
                    )}
                  </span>
                </div>
              </div>

              {/* Confirm Password */}
              <div>
                <Label htmlFor="confirmPassword">
                  Confirm Password<span className="text-error-500">*</span>
                </Label>
                <div className="relative">
                  <Input
                    id="confirmPassword"
                    name="confirmPassword"
                    placeholder="Confirm your password"
                    type={showConfirmPassword ? "text" : "password"}
                    value={formData.confirmPassword}
                    onChange={handleInputChange}
                    disabled={isLoading}
                    required
                    minLength={8}
                    maxLength={128}
                  />
                  <span
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute z-30 -translate-y-1/2 cursor-pointer right-4 top-1/2"
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        setShowConfirmPassword(!showConfirmPassword);
                      }
                    }}
                  >
                    {showConfirmPassword ? (
                      <EyeIcon className="fill-gray-500 dark:fill-gray-400" />
                    ) : (
                      <EyeCloseIcon className="fill-gray-500 dark:fill-gray-400" />
                    )}
                  </span>
                </div>
              </div>

              {/* Optional Fields */}
              <div>
                <Label htmlFor="bio">Bio (Optional)</Label>
                <Input
                  id="bio"
                  name="bio"
                  type="text"
                  placeholder="Tell us about yourself"
                  value={formData.bio}
                  onChange={handleInputChange}
                  disabled={isLoading}
                  maxLength={500}
                />
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  {formData.bio?.length || 0}/500 characters
                </p>
              </div>

              <div>
                <Label htmlFor="website">Website (Optional)</Label>
                <Input
                  id="website"
                  name="website"
                  type="url"
                  placeholder="https://yourwebsite.com"
                  value={formData.website}
                  onChange={handleInputChange}
                  disabled={isLoading}
                  maxLength={200}
                />
              </div>

              <div>
                <Label htmlFor="location">Location (Optional)</Label>
                <Input
                  id="location"
                  name="location"
                  type="text"
                  placeholder="Your location"
                  value={formData.location}
                  onChange={handleInputChange}
                  disabled={isLoading}
                  maxLength={100}
                />
              </div>

              {/* Submit Button */}
              <div>
                <button 
                  type="submit" 
                  disabled={isLoading}
                  className="flex items-center justify-center w-full px-4 py-3 text-sm font-medium text-white transition rounded-lg bg-brand-500 shadow-theme-xs hover:bg-brand-600 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
                >
                  {isLoading ? (
                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                  ) : null}
                  {isLoading ? "Creating Account..." : "Complete Registration"}
                </button>
              </div>
            </div>
          </form>

          <div className="mt-5">
            <p className="text-sm font-normal text-center text-gray-700 dark:text-gray-400 sm:text-start">
              Already have an account?{" "}
              <Link
                href="/signin"
                className="text-brand-500 hover:text-brand-600 dark:text-brand-400 transition-colors"
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
