// Invite acceptance page that handles tokens from email links
'use client';

import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useRouter, useParams, useSearchParams } from 'next/navigation';
import { useAuthStore } from '@/stores/authStore';
import { toast } from "react-hot-toast";
import { motion, AnimatePresence } from 'framer-motion';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import SignInModal from '@/components/auth/SignInModal';
import Image from 'next/image';
import { 
  Users, 
  Crown, 
  Building, 
  Loader2, 
  CheckCircle2, 
  AlertCircle,
  Mail,
  Shield,
  ArrowRight,
  RefreshCw,
  LogIn,
  ExternalLink
} from 'lucide-react';

// TypeScript interfaces for better type safety
interface JoinOrganizationResponse {
  success: boolean;
  message: string;
  data: {
    role: string;
    permissions: {
      can_manage_tenant: boolean;
      can_manage_billing: boolean;
      can_manage_members: boolean;
      can_view_analytics: boolean;
      can_manage_projects: boolean;
    };
    id: string;
    tenant_id: string;
    user_id: string;
    joined_at: string;
    is_active: boolean;
    created_at: string;
    updated_at: string;
  };
  auth: {
    access_token: string;
    tenant_id: string;
    tenant_type: string;
    user_id: string;
    email: string;
    roles: string[];
    user: {
      id: string;
      email: string;
      full_name: string;
      avatar_url: string | null;
      timezone: string;
      preferences: Record<string, any>;
      bio: string;
      website: string;
      location: string;
      role: string;
      created_at: string;
    };
    is_team_leader: boolean;
  };
}

type ProcessingStep = 'validating' | 'authenticating' | 'joining' | 'redirecting' | 'idle';

interface InviteDetails {
  icon: any;
  title: string;
  description: string;
  badgeText: string;
  color: string;
  gradient: string;
}

export default function InviteAcceptancePage() {
  const router = useRouter();
  const params = useParams();
  const searchParams = useSearchParams();
  
  // Extract invitation token and org_id/team_id from URL
  const { token } = params;
  const invitationToken = token as string;
  const orgId = searchParams.get('org_id');
  const teamId = searchParams.get('team_id');
  const vbToken = searchParams.get('vb_token');
  const invitedEmail = searchParams.get('email');

  // Determine invite type based on which ID is present
  const isTeamInvite = !!teamId && !orgId;
  const isVBInvite = !!vbToken;
  const targetId = orgId || teamId;
  
  // Auth state from Zustand store
  const { isAuthenticated, isInitialized, token: authToken, setToken, setUser, logout } = useAuthStore();
  
  // Component state
  const [loading, setLoading] = useState(true);
  const [processingStep, setProcessingStep] = useState<ProcessingStep>('validating');
  const [error, setError] = useState<string | null>(null);
  const [showSignInModal, setShowSignInModal] = useState(false);
  const [isAccepting, setIsAccepting] = useState(false);
  const [inviteValidated, setInviteValidated] = useState(false);
  const [retryCount, setRetryCount] = useState(0);

  // Refs for cleanup
  const abortControllerRef = useRef<AbortController | null>(null);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  // CRITICAL: Clear auth token FIRST on component mount for org/team invites
  // This prevents issues where a different user might be logged in
  // For VB invites, we don't logout - let the user proceed with their current session
  useEffect(() => {
    if (isVBInvite) {
      if (process.env.NODE_ENV === 'development') {
        console.log('🔐 InviteAcceptancePage: VB invite - keeping existing auth session');
      }
      return;
    }

    if (process.env.NODE_ENV === 'development') {
      console.log('🔐 InviteAcceptancePage: Clearing existing auth token to ensure clean invitation flow');
    }

    // Clear any existing authentication for org/team invites
    logout();

    if (process.env.NODE_ENV === 'development') {
      console.log('✅ Auth token cleared - ready for invitation acceptance');
    }
  }, [isVBInvite, logout]); // Added isVBInvite dependency

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort('Component unmounted');
        abortControllerRef.current = null;
      }
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
    };
  }, []);

  // Enhanced token validation with format checking
  const validateInvitation = useCallback(async () => {
    // VB invites only need the vbToken, org/team invites need targetId
    if (!invitationToken || (!targetId && !isVBInvite)) {
      setError('Invalid invite link - missing required parameters');
      setLoading(false);
      return false;
    }

    // Enhanced token format validation
    if (invitationToken.length < 10) {
      setError('Invalid invitation token format');
      setLoading(false);
      return false;
    }

    // Check for basic JWT structure (header.payload.signature)
    const tokenParts = invitationToken.split('.');
    if (tokenParts.length !== 3 && !invitationToken.includes('-')) {
      // Not a JWT and not a UUID-style token
      if (process.env.NODE_ENV === 'development') {
        console.warn('⚠️ Token format may be invalid:', tokenParts.length, 'parts');
      }
    }

    // Sanitize token to prevent XSS
    const sanitizedToken = invitationToken.replace(/<[^>]*>/g, '').trim();
    if (sanitizedToken !== invitationToken) {
      setError('Invalid token format detected');
      setLoading(false);
      return false;
    }

    setInviteValidated(true);
    return true;
  }, [invitationToken, targetId, isVBInvite]);

  // Check for required params and validate invitation
  useEffect(() => {
    const initValidation = async () => {
      try {
        await validateInvitation();
      } catch (err) {
        setError('Failed to validate invitation');
        if (process.env.NODE_ENV === 'development') {
          console.error('Validation error:', err);
        }
      } finally {
        setLoading(false);
      }
    };

    initValidation();
  }, [validateInvitation]);

  // Show sign-in modal when not authenticated
  useEffect(() => {
    if (isInitialized && !loading && !error && inviteValidated && !isAuthenticated && !showSignInModal) {
      setShowSignInModal(true);
    }
  }, [isInitialized, loading, error, inviteValidated, isAuthenticated, showSignInModal]);

  // Handle successful sign-in from modal
  const handleSignInSuccess = useCallback(async () => {
    if (process.env.NODE_ENV === 'development') {
      console.log('✅ Sign-in successful, user can now accept invite');
    }

    setShowSignInModal(false);

    // For VB invites, redirect to VB onboarding page with token and email
    if (isVBInvite) {
      toast.success('Successfully signed in! Redirecting to complete your profile...');
      const onboardingParams = new URLSearchParams();
      onboardingParams.set('token', vbToken as string);
      if (invitedEmail) {
        onboardingParams.set('email', invitedEmail);
      }
      router.push(`/vb-onboarding?${onboardingParams.toString()}`);
      return;
    }

    toast.success('Successfully signed in! You can now accept the invitation.');
  }, [isVBInvite, vbToken, invitedEmail, router]);

  // Handle sign-in modal close
  const handleSignInClose = useCallback(() => {
    setShowSignInModal(false);
    // If user closes sign-in modal without signing in, show appropriate message
    if (!isAuthenticated) {
      toast.info('Please sign in to accept the organization invitation');
    }
  }, [isAuthenticated]);

  // Get processing step message
  const getProcessingMessage = useMemo(() => {
    const messages = {
      validating: 'Validating your invitation...',
      authenticating: 'Verifying your credentials...',
      joining: 'Joining organization...',
      redirecting: 'Taking you to your workspace...',
      idle: 'Ready to join...'
    };
    return messages[processingStep];
  }, [processingStep]);

  // Handle invite acceptance with enhanced error handling and retry logic
  const handleAcceptInvite = useCallback(async () => {
    if (!invitationToken || !targetId) {
      toast.error('Invalid invitation parameters');
      return;
    }

    // Check authentication before proceeding
    if (!isAuthenticated || !authToken) {
      toast.error('Please sign in to accept this invitation');
      setShowSignInModal(true);
      return;
    }

    let toastId: string | number | undefined;

    try {
      setIsAccepting(true);
      setProcessingStep('joining');
      setError(null);

      // Cancel any ongoing requests
      if (abortControllerRef.current) {
        abortControllerRef.current.abort('New request initiated');
      }

      // Create new abort controller
      abortControllerRef.current = new AbortController();

      toastId = toast.loading('Accepting organization invitation...');

      if (process.env.NODE_ENV === 'development') {
        console.log(`🔍 Joining ${isTeamInvite ? 'team' : 'organization'} with:`, {
          targetId,
          isTeamInvite,
          invitationToken: `${invitationToken.substring(0, 20)}...`,
          hasAuthToken: !!authToken,
          retryAttempt: retryCount
        });
      }

      // Sanitize token before sending
      const sanitizedToken = invitationToken.replace(/<[^>]*>/g, '').trim();

      // Call appropriate join endpoint based on invite type
      const joinEndpoint = isTeamInvite 
        ? `${process.env.NEXT_PUBLIC_API_URL}/api/teams/${targetId}/join`
        : `${process.env.NEXT_PUBLIC_API_URL}/api/organization/${targetId}/join`;
      
      const response = await fetch(
        joinEndpoint,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${authToken}`,
          },
          body: JSON.stringify({
            invite_token: sanitizedToken,
          }),
          signal: abortControllerRef.current.signal,
        }
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const errorMessage = errorData.message || errorData.detail || `Failed to join organization (${response.status})`;
        throw new Error(errorMessage);
      }

      const joinResponse: JoinOrganizationResponse = await response.json();

      if (process.env.NODE_ENV === 'development') {
        console.log('✅ Join organization response:', joinResponse);
      }

      // Update authstore with new access token from response
      if (joinResponse.auth?.access_token) {
        setToken(joinResponse.auth.access_token);
        
        // Update user info if available
        // if (joinResponse.auth.user) {
        //   setUser(joinResponse.auth.user);
        // }
        
        if (process.env.NODE_ENV === 'development') {
          console.log('✅ Updated authstore with new token and user info');
        }
      }

      setProcessingStep('redirecting');
      setRetryCount(0); // Reset retry count on success

      console.log('✅ Join response:', joinResponse);

      // Route based on invite type and is_team_leader flag
      if (isTeamInvite) {
        // Team invite - route to team workspace
        toast.success('Successfully joined the team!', { id: toastId });
        
        if (process.env.NODE_ENV === 'development') {
          console.log('👥 Routing to team workspace...');
        }
        
        timeoutRef.current = setTimeout(() => {
          router.push(`/choose-workspace`);
        }, 1500);
      } else if (joinResponse.auth?.is_team_leader) {
        // Organization invite as team leader - route to team onboarding
        toast.success('Successfully joined as team leader!', { id: toastId });
        
        if (process.env.NODE_ENV === 'development') {
          console.log('👑 Routing to team onboarding...');
        }
        
        timeoutRef.current = setTimeout(() => {
          router.push(`/team-onboarding?token=${joinResponse.auth.access_token}&org_id=${targetId}`);
        }, 1500);
      } else {
        // Organization invite as regular member
        toast.success('Successfully joined the organization!', { id: toastId });
        
        if (process.env.NODE_ENV === 'development') {
          console.log('👥 Routing to organization membership...');
        }
        
        timeoutRef.current = setTimeout(() => {
          router.push(`/organization-membership?org_id=${targetId}`);
        }, 1500);
      }
      
    } catch (err: any) {
      // Ignore abort errors
      if (err.name === 'AbortError') {
        return;
      }
      
      if (process.env.NODE_ENV === 'development') {
        console.error('❌ Error accepting invite:', {
          errorType: err?.constructor?.name,
          errorName: err?.name,
          message: err?.message,
          stack: err?.stack,
          stringified: JSON.stringify(err),
          raw: err,
          retryCount
        });
        console.error('Full error object:', err);
      }
      
      const errorMessage = err?.message || err?.toString() || 'Failed to accept organization invitation';
      
      // Check if error is retryable (network errors)
      const isNetworkError = errorMessage.includes('fetch') || 
                            errorMessage.includes('Network') ||
                            errorMessage.includes('timeout') ||
                            err?.name === 'TypeError' ||
                            !navigator.onLine;
      
      // Implement retry logic for network errors (max 3 attempts)
      if (isNetworkError && retryCount < 3) {
        const nextRetry = retryCount + 1;
        const retryDelay = Math.pow(2, retryCount) * 1000; // Exponential backoff
        
        toast.error(`Network error. Retrying in ${retryDelay / 1000}s... (Attempt ${nextRetry}/3)`, { id: toastId });
        
        timeoutRef.current = setTimeout(() => {
          setRetryCount(nextRetry);
          handleAcceptInvite();
        }, retryDelay);
        
        return;
      }
      
      // Provide more specific error messages
      let userFriendlyMessage = errorMessage;
      if (errorMessage.includes("doesn't have an invite") || errorMessage.includes('not found')) {
        userFriendlyMessage = 'This invitation may have expired, been used already, or was sent to a different email address. Please check that you\'re signed in with the correct account.';
      } else if (errorMessage.includes('expired')) {
        userFriendlyMessage = 'This invitation has expired. Please request a new invitation link.';
      } else if (errorMessage.includes('already used') || errorMessage.includes('already exists')) {
        userFriendlyMessage = 'This invitation has already been used. If you need access, please request a new invitation.';
      } else if (errorMessage.includes('Invalid') || errorMessage.includes('invalid')) {
        userFriendlyMessage = 'This invitation link is invalid. Please check the link or request a new invitation.';
      } else if (errorMessage.includes('401') || errorMessage.includes('unauthorized')) {
        userFriendlyMessage = 'Your session has expired. Please sign in again.';
        setShowSignInModal(true);
      } else if (errorMessage.includes('403') || errorMessage.includes('forbidden') || errorMessage.includes('Access denied')) {
        userFriendlyMessage = 'Access denied. Please check your permissions or sign in with the correct account.';
        setShowSignInModal(true);
      } else if (isNetworkError && retryCount >= 3) {
        userFriendlyMessage = 'Network error after multiple attempts. Please check your connection and try again.';
      } else if (!errorMessage || errorMessage === '[object Object]') {
        userFriendlyMessage = 'An unexpected error occurred. Please try again or contact support.';
      }
      
      setError(userFriendlyMessage);
      toast.error(userFriendlyMessage, { id: toastId });
      setIsAccepting(false);
      setProcessingStep('idle');
    }
  }, [invitationToken, targetId, isTeamInvite, isAuthenticated, authToken, setToken, setUser, router, retryCount]);

  // Handle retry operation
  const handleRetry = useCallback(() => {
    setError(null);
    setLoading(true);
    setTimeout(() => {
      validateInvitation().finally(() => setLoading(false));
    }, 500);
  }, [validateInvitation]);

  // Get invite details based on invite type
  const inviteDetails: InviteDetails = useMemo(() => {
    if (isVBInvite) {
      return {
        icon: Crown,
        title: 'Venture Builder Invitation',
        description: 'You\'ve been invited to join as a Venture Builder',
        badgeText: 'Venture Builder',
        color: 'brand',
        gradient: 'from-purple-500 to-indigo-600'
      };
    }
    if (isTeamInvite) {
      return {
        icon: Users,
        title: 'Team Invitation',
        description: 'You\'ve been invited to join a team workspace',
        badgeText: 'Team Member',
        color: 'brand',
        gradient: 'from-green-500 to-teal-600'
      };
    }
    return {
      icon: Building,
      title: 'Organization Invitation',
      description: 'You\'ve been invited to join an organization workspace',
      badgeText: 'Organization Member',
      color: 'brand',
      gradient: 'from-brand-300 to-brand-500'
    };
  }, [isTeamInvite, isVBInvite]);

  // Loading state with progress indicator
  if (loading || !isInitialized) {
    return (
      <div className="flex justify-center items-center min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
        <Card className="w-full max-w-md mx-4 border-gray-200 dark:border-gray-800 shadow-lg">
          <CardContent className="pt-6">
            <div className="flex flex-col items-center justify-center py-8 space-y-4">
              <div className="relative">
                <div className="w-16 h-16 bg-brand-100 dark:bg-brand-900/30 rounded-full flex items-center justify-center">
                  <Loader2 className="w-8 h-8 text-brand-500 animate-spin" />
                </div>
                <div className="absolute inset-0 bg-brand-500/20 rounded-full animate-ping" />
              </div>
              <div className="text-center space-y-2">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  {getProcessingMessage}
                </h3>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Preparing your invitation...
                </p>
                {/* Progress dots */}
                <div className="flex items-center justify-center gap-2 pt-2">
                  {[0, 1, 2].map((i) => (
                    <div
                      key={i}
                      className="w-2 h-2 bg-brand-500 rounded-full animate-pulse"
                      style={{ animationDelay: `${i * 200}ms` }}
                    />
                  ))}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Error state with retry option
  if (error) {
    return (
      <div className="flex justify-center items-center min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800 p-4">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.3 }}
        >
          <Card className="w-full max-w-md border-red-200 dark:border-red-800 shadow-lg">
            <CardHeader className="text-center pb-4">
              <div className="mx-auto w-16 h-16 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center mb-4">
                <AlertCircle className="w-8 h-8 text-red-600 dark:text-red-400" />
              </div>
              <CardTitle className="text-2xl text-red-600 dark:text-red-400">
                Invitation Error
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <Alert variant="destructive" className="border-red-200 dark:border-red-800">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription className="ml-2">
                  {error}
                </AlertDescription>
              </Alert>
              
              <div className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
                <p className="font-medium">Common issues:</p>
                <ul className="list-disc list-inside space-y-1 ml-2">
                  <li>The invitation link may have expired</li>
                  <li>The link may have already been used</li>
                  <li>The link may be invalid or corrupted</li>
                  <li>You may need to sign in with the correct account</li>
                </ul>
              </div>

              <div className="pt-4 space-y-3">
                <Button
                  onClick={handleRetry}
                  className="w-full"
                  variant="default"
                >
                  <RefreshCw className="w-4 h-4 mr-2" />
                  Try Again
                </Button>
                
                {!isAuthenticated && (
                  <Button
                    onClick={() => setShowSignInModal(true)}
                    className="w-full"
                    variant="outline"
                  >
                    <LogIn className="w-4 h-4 mr-2" />
                    Sign In
                  </Button>
                )}
                
                <Button
                  onClick={() => router.push('/')}
                  className="w-full"
                  variant="ghost"
                >
                  Return to Home
                </Button>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    );
  }

  const IconComponent = inviteDetails.icon;

  // Main invite acceptance UI
  return (
    <>
      <div className="flex justify-center items-center min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800 p-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="w-full max-w-lg"
        >
          <Card className="border-gray-200 dark:border-gray-800 shadow-xl overflow-hidden">
            {/* Gradient header accent */}
            <div className={`h-2 bg-gradient-to-r from-brand-300 to-brand-500`} />
            
            <CardHeader className="text-center flex flex-col items-center justify-center">
             <Image src="/images/logo/yuba-logo-icon-colored.png" alt="Yuba" width={50} height={50} priority />

              

              <CardTitle className="text-2xl font-bold text-brand-500 dark:text-white">
                {inviteDetails.title}
              </CardTitle>
              
              <CardDescription className="text-gray-600 dark:text-gray-400 text-sm">
                {inviteDetails.description}
              </CardDescription>
            </CardHeader>

            <CardContent className="space-y-6 -mt-4">
              {/* Authentication status banner */}
              <AnimatePresence>
                {!isAuthenticated && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                  >
                    <Alert className="border-yellow-200 bg-yellow-50 dark:border-yellow-800 dark:bg-yellow-900/20 mb-4">
                      <AlertCircle className="h-4 w-4 text-yellow-600" />
                      <AlertDescription className="ml-2 text-yellow-800 dark:text-yellow-300">
                        You need to sign in before accepting this invitation.
                      </AlertDescription>
                    </Alert>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Benefits Section */}
              <div className="space-y-4">
                <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-green-600" />
                  What you'll get
                </h3>
                <ul className="space-y-3 text-sm text-gray-600 dark:text-gray-400">
                  {isVBInvite ? (
                    <>
                      <li className="flex items-start gap-3">
                        <CheckCircle2 className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
                        <span>Join as a Venture Builder and showcase your expertise</span>
                      </li>
                      <li className="flex items-start gap-3">
                        <CheckCircle2 className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
                        <span>Connect with startups and organizations</span>
                      </li>
                      <li className="flex items-start gap-3">
                        <CheckCircle2 className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
                        <span>Manage your availability and calendar</span>
                      </li>
                    </>
                  ) : (
                    <>
                      <li className="flex items-start gap-3">
                        <CheckCircle2 className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
                        <span>Access to organization workspace and tools</span>
                      </li>
                      <li className="flex items-start gap-3">
                        <CheckCircle2 className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
                        <span>Collaborate with team members in real-time</span>
                      </li>
                      <li className="flex items-start gap-3">
                        <CheckCircle2 className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
                        <span>Access to shared resources and projects</span>
                      </li>
                    </>
                  )}
                  {isAuthenticated && (
                    <li className="flex items-start gap-3">
                      <CheckCircle2 className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
                      <span className="text-green-600 dark:text-green-400 font-medium">
                        You're signed in and ready to {isVBInvite ? 'complete your profile' : 'join'}
                      </span>
                    </li>
                  )}
                </ul>
              </div>

              {/* Action Buttons */}
              <div className="space-y-3 pt-2">
                {!isAuthenticated ? (
                  <>
                   <SignInModal
        isOpen={showSignInModal}
        onOpenChange={setShowSignInModal}
        onSuccess={handleSignInSuccess}
        onClose={handleSignInClose}
        initialEmail={invitedEmail || undefined}
        lockEmail={!!invitedEmail}
      />
                  </>
                ) : isVBInvite ? (
                  <Button
                    onClick={() => {
                      const onboardingParams = new URLSearchParams();
                      onboardingParams.set('token', vbToken as string);
                      if (invitedEmail) {
                        onboardingParams.set('email', invitedEmail);
                      }
                      router.push(`/vb-onboarding?${onboardingParams.toString()}`);
                    }}
                    className="w-full h-12 text-base font-semibold flex items-center justify-center gap-2"
                    size="lg"
                  >
                    <Crown className="w-5 h-5" />
                    Complete Your Profile
                    <ArrowRight className="w-5 h-5" />
                  </Button>
                ) : (
                  <Button
                    onClick={handleAcceptInvite}
                    disabled={isAccepting}
                    className="w-full h-12 text-base font-semibold flex items-center justify-center gap-2"
                    size="lg"
                  >
                    {isAccepting ? (
                      <>
                        <Loader2 className="w-5 h-5 animate-spin" />
                        {getProcessingMessage}
                      </>
                    ) : (
                      <>
                        <Shield className="w-5 h-5" />
                        Accept Invitation
                        <ArrowRight className="w-5 h-5" />
                      </>
                    )}
                  </Button>
                )}
                
                {/* Secondary action */}
                <Button
                  onClick={() => router.push('/')}
                  variant="outline"
                  className="w-full"
                  disabled={isAccepting}
                >
                  Maybe Later
                </Button>
              </div>

              {/* Security Notice */}
              <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-3 border border-gray-200 dark:border-gray-700">
                <div className="flex items-start gap-2">
                  <Shield className="w-4 h-4 text-gray-500 mt-0.5 flex-shrink-0" />
                  <p className="text-xs text-gray-600 dark:text-gray-400">
                    This invitation is secure and intended for you. Don't share invitation links with others.
                  </p>
                </div>
              </div>

              {/* Terms and Privacy */}
              <div className="pt-2 border-t border-gray-200 dark:border-gray-700">
                <p className="text-xs text-center text-gray-500 dark:text-gray-400 leading-relaxed">
                  By accepting this invitation, you agree to our{' '}
                  <a 
                    href="/terms" 
                    className="text-brand-600 hover:text-brand-700 dark:text-brand-400 dark:hover:text-brand-300 underline inline-flex items-center gap-1"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Terms of Service
                    <ExternalLink className="w-3 h-3" />
                  </a>
                  {' '}and{' '}
                  <a 
                    href="/privacy" 
                    className="text-brand-600 hover:text-brand-700 dark:text-brand-400 dark:hover:text-brand-300 underline inline-flex items-center gap-1"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Privacy Policy
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Additional Help */}
          <div className="mt-6 text-center">
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Need help?{' '}
              <a 
                href="/support" 
                className="text-brand-600 hover:text-brand-700 dark:text-brand-400 dark:hover:text-brand-300 font-medium inline-flex items-center gap-1"
              >
                Contact Support
                <ExternalLink className="w-3 h-3" />
              </a>
            </p>
          </div>
        </motion.div>
      </div>


    </>
  );
}