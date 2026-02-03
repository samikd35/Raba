"use client";

import { useCallback, useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { authService } from '@/services/authService';
import toast from 'react-hot-toast';

interface GoogleSignInProps {
  onSuccess?: () => void;
  onError?: (error: string) => void;
  disabled?: boolean;
  className?: string;
  text?: 'signin_with' | 'signup_with' | 'continue_with' | 'signin'; // Dynamic text for the Google button
  skipRedirect?: boolean; // Skip automatic redirect after sign-in (useful for modals/invitations)
}

interface GoogleCredentialResponse {
  credential: string;
  select_by?: string;
}

// Google Sign-In configuration
const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;

declare global {
  interface Window {
    google: {
      accounts: {
        id: {
          initialize: (config: any) => void;
          renderButton: (element: HTMLElement, config: any) => void;
          prompt: () => void;
        };
      };
    };
  }
}

// Extracted Google Icon component to remove duplication
const GoogleIcon = () => (
  <svg
    width="20"
    height="20"
    viewBox="0 0 20 20"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
  >
    <path
      d="M18.7511 10.1944C18.7511 9.47495 18.6915 8.94995 18.5626 8.40552H10.1797V11.6527H15.1003C15.0011 12.4597 14.4654 13.675 13.2749 14.4916L13.2582 14.6003L15.9087 16.6126L16.0924 16.6305C17.7788 15.1041 18.7511 12.8583 18.7511 10.1944Z"
      fill="#4285F4"
    />
    <path
      d="M10.1788 18.75C12.5895 18.75 14.6133 17.9722 16.0915 16.6305L13.274 14.4916C12.5201 15.0068 11.5081 15.3666 10.1788 15.3666C7.81773 15.3666 5.81379 13.8402 5.09944 11.7305L4.99473 11.7392L2.23868 13.8295L2.20264 13.9277C3.67087 16.786 6.68674 18.75 10.1788 18.75Z"
      fill="#34A853"
    />
    <path
      d="M5.10014 11.7305C4.91165 11.186 4.80257 10.6027 4.80257 9.99992C4.80257 9.3971 4.91165 8.81379 5.09022 8.26935L5.08523 8.1534L2.29464 6.02954L2.20333 6.0721C1.5982 7.25823 1.25098 8.5902 1.25098 9.99992C1.25098 11.4096 1.5982 12.7415 2.20333 13.9277L5.10014 11.7305Z"
      fill="#FBBC05"
    />
    <path
      d="M10.1789 4.63331C11.8554 4.63331 12.9864 5.34303 13.6312 5.93612L16.1511 3.525C14.6035 2.11528 12.5895 1.25 10.1789 1.25C6.68676 1.25 3.67088 3.21387 2.20264 6.07218L5.08953 8.26943C5.81381 6.15972 7.81776 4.63331 10.1789 4.63331Z"
      fill="#EB4335"
    />
  </svg>
);

// Extracted error message function
const getErrorMessage = (error: any): string => {
  const message = error.message || '';

  if (message.includes('Invalid Google ID token') || message.includes('401')) {
    return 'Google authentication failed. Please try signing in again.';
  } else if (message.includes('Network') || message.includes('fetch')) {
    return 'Network error. Please check your connection and try again.';
  } else if (message.includes('429')) {
    return 'Too many sign-in attempts. Please wait a moment and try again.';
  } else if (message.includes('500')) {
    return 'Sign-in service is temporarily unavailable. Please try again later.';
  } else if (message.includes('timeout')) {
    return 'Sign-in request timed out. Please try again.';
  } else {
    return message || 'Google sign-in failed. Please try again.';
  }
};

export default function GoogleSignIn({
  onSuccess,
  onError,
  disabled = false,
  className = "",
  text = 'signin_with', // Default to sign in
  skipRedirect = false // Default to redirect after sign-in
}: GoogleSignInProps) {
  const router = useRouter();
  const googleButtonRef = useRef<HTMLDivElement>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isGoogleLoaded, setIsGoogleLoaded] = useState(false);

  // Refs for cleanup and mounting state
  const abortControllerRef = useRef<AbortController | null>(null);
  const redirectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const requestTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const isMountedRef = useRef(true);

  // Handle Google credential response
  const handleCredentialResponse = useCallback(async (response: GoogleCredentialResponse) => {
    if (!response.credential) {
      const errorMsg = 'No credential received from Google';
      toast.error(errorMsg);
      onError?.(errorMsg);
      return;
    }

    // Don't proceed if component is unmounted
    if (!isMountedRef.current) return;

    // Abort any previous request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    try {
      setIsLoading(true);

      // Set request timeout (10 seconds)
      requestTimeoutRef.current = setTimeout(() => {
        if (abortControllerRef.current) {
          abortControllerRef.current.abort();
          toast.error('Sign-in request timed out. Please try again.');
        }
      }, 10000);

      // Use authService to handle Google login
      const user = await authService.loginWithGoogle(response.credential);

      // Clear request timeout
      if (requestTimeoutRef.current) {
        clearTimeout(requestTimeoutRef.current);
        requestTimeoutRef.current = null;
      }

      // Don't proceed if component is unmounted
      if (!isMountedRef.current) return;

      // Success! Show success message
      toast.success(`Welcome back, ${user.full_name || user.email}!`);

      // Call success callback
      onSuccess?.();

      // Small delay to show success message before redirect (unless skipRedirect is true)
      if (!skipRedirect) {
        redirectTimeoutRef.current = setTimeout(() => {
          if (isMountedRef.current) {
            router.push('/choose-workspace');
          }
        }, 500);
      }

    } catch (error: any) {
      // Clear request timeout
      if (requestTimeoutRef.current) {
        clearTimeout(requestTimeoutRef.current);
        requestTimeoutRef.current = null;
      }

      // Don't proceed if component is unmounted
      if (!isMountedRef.current) return;

      console.error('Google Sign-In error:', error);

      const errorMessage = getErrorMessage(error);
      toast.error(errorMessage);
      onError?.(errorMessage);
    } finally {
      if (isMountedRef.current) {
        setIsLoading(false);
        abortControllerRef.current = null;
      }
    }
  }, [router, onSuccess, onError]);

  // Load Google Sign-In script
  useEffect(() => {
    if (!GOOGLE_CLIENT_ID) {
      return;
    }

    const loadGoogleScript = () => {
      // Check if script is already loaded
      if (window.google?.accounts?.id) {
        setIsGoogleLoaded(true);
        return;
      }

      const script = document.createElement('script');
      script.src = 'https://accounts.google.com/gsi/client';
      script.async = true;
      script.defer = true;

      script.onload = () => {
        if (window.google?.accounts?.id && isMountedRef.current) {
          setIsGoogleLoaded(true);
        }
      };

      script.onerror = () => {
        if (isMountedRef.current) {
          toast.error('Failed to load Google Sign-In');
        }
      };

      document.head.appendChild(script);
    };

    loadGoogleScript();
  }, []);

  // Initialize Google Sign-In when script is loaded
  useEffect(() => {
    if (!isGoogleLoaded || !GOOGLE_CLIENT_ID || !googleButtonRef.current) {
      return;
    }

    try {
      window.google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: handleCredentialResponse,
        auto_select: false,
        cancel_on_tap_outside: true,
      });

      // Render the Google Sign-In button
      window.google.accounts.id.renderButton(googleButtonRef.current, {
        theme: 'outline',
        size: 'large',
        width: '100%',
        text: text, // Use the dynamic text prop
        shape: 'rectangular',
        logo_alignment: 'left',
      });

    } catch (error) {
      if (isMountedRef.current) {
        toast.error('Failed to initialize Google Sign-In');
      }
    }
  }, [isGoogleLoaded, handleCredentialResponse]);

  // Set mounted state and cleanup on unmount
  useEffect(() => {
    isMountedRef.current = true;

    return () => {
      isMountedRef.current = false;

      // Cleanup all timeouts and abort controllers
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }

      if (redirectTimeoutRef.current) {
        clearTimeout(redirectTimeoutRef.current);
        redirectTimeoutRef.current = null;
      }

      if (requestTimeoutRef.current) {
        clearTimeout(requestTimeoutRef.current);
        requestTimeoutRef.current = null;
      }
    };
  }, []);

  // Fallback button for when Google script fails to load
  const handleFallbackClick = useCallback(() => {
    if (!GOOGLE_CLIENT_ID) {
      toast.error('Google Sign-In is not configured');
      return;
    }

    toast.error('Google Sign-In is temporarily unavailable. Please try again later.');
  }, []);

  if (!GOOGLE_CLIENT_ID) {
    return (
      <button
        type="button"
        disabled={true}
        className={`inline-flex items-center justify-center gap-3 py-3 text-sm font-normal text-gray-400 bg-gray-100 rounded-lg px-7 cursor-not-allowed ${className}`}
      >
        <GoogleIcon />
        Google Sign-In Not Configured
      </button>
    );
  }

  return (
    <div className={`relative ${className}`}>
      {/* Google Sign-In Button Container */}
      <div
        ref={googleButtonRef}
        className={`${disabled || isLoading ? 'pointer-events-none opacity-50' : ''}`}
        style={{ minHeight: '44px' }}
      />

      {/* Loading Overlay */}
      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-white/80 dark:bg-gray-900/80 rounded-lg">
          <svg className="animate-spin h-5 w-5 text-gray-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
        </div>
      )}

      {/* Fallback button if Google script fails to load */}
      {!isGoogleLoaded && (
        <button
          type="button"
          disabled={disabled || isLoading}
          className="absolute inset-0 inline-flex items-center justify-center gap-3 py-3 text-sm font-normal text-gray-700 transition-colors bg-gray-100 rounded-lg px-7 hover:bg-gray-200 hover:text-gray-800 dark:bg-white/5 dark:text-white/90 dark:hover:bg-white/10 disabled:opacity-50 disabled:cursor-not-allowed"
          onClick={handleFallbackClick}
        >
          <GoogleIcon />
          {text === 'signup_with' ? 'Sign up with Google' :
            text === 'continue_with' ? 'Continue with Google' :
              text === 'signin' ? 'Sign in' : 'Sign in with Google'}
        </button>
      )}
    </div>
  );
}