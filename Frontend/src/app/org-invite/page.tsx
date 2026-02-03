// Organization invite redemption page
'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { organizationService } from '@/lib/api/organizationService';
import { authService } from '@/services/authService';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { toast } from "react-hot-toast";

export default function OrganizationInviteRedemptionPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get('token');
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [inviteData, setInviteData] = useState<any>(null);
  const [isAccepting, setIsAccepting] = useState(false);
  const [redirecting, setRedirecting] = useState(false);

  // Auto-redirect behavior: if token exists, redirect depending on auth state.
  useEffect(() => {
    const doRedirect = async () => {
      if (!token) return;
      setRedirecting(true);

      try {
        // existing authService provides synchronous isAuthenticated in this codebase
        const authed = authService.isAuthenticated && authService.isAuthenticated();

        if (authed) {
          // If authenticated, go to admin organization route with token
          const url = `/admin/organization?token=${encodeURIComponent(token)}`;
          router.replace(url);
          return;
        }

          // Dev bypass: if `?direct=1` present or env flag enabled, go straight to onboarding (useful for local integration)
          const search = new URLSearchParams(window.location.search || '');
          const direct = search.get('direct') === '1' || process.env.NEXT_PUBLIC_DEV_SKIP_AUTH === 'true';
          const onboarding = `http://localhost:3000/admin/onboarding?token=${encodeURIComponent(token)}`;
          if (direct) {
            router.replace(onboarding);
            return;
          }

          // Not authenticated: redirect to signin and include `next` so login flow can return to onboarding
          const signinUrl = `/signin?next=${encodeURIComponent(onboarding)}`;
          router.replace(signinUrl);
      } catch (err) {
        // If anything goes wrong, stop redirecting and allow the page to render normally
        console.error('Invite redirect error', err);
        setRedirecting(false);
      }
    };

    doRedirect();
    // only run when token changes
  }, [token, router]);

  useEffect(() => {
    const validateInvite = async () => {
      if (!token) {
        setError('Invalid invite link. Token is missing.');
        setLoading(false);
        return;
      }

      try {
        // In a real implementation, you might want to validate the invite token
        // For now, we'll proceed directly to acceptance
        setLoading(false);
      } catch (err) {
        setError('Invalid or expired organization invite link.');
        setLoading(false);
      }
    };

    validateInvite();
  }, [token]);

  const handleAcceptInvite = async () => {
    if (!token) return;

    try {
      setIsAccepting(true);
      // Accept the organization invite
      await organizationService.acceptInvite(token);
      
      // Check if user is already authenticated
      if (authService.isAuthenticated()) {
        // If already logged in, redirect to organization creation
        router.push(`/admin/onboarding?type=prepay_org&invite_token=${token}`);
      } else {
        // If not logged in, redirect to signup with invite token
        router.push(`/auth/signup?invite_token=${token}&type=organization`);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to accept organization invite');
      toast.error(err.message || 'Failed to accept organization invite');
    } finally {
      setIsAccepting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-screen bg-gray-50 dark:bg-gray-900">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex justify-center items-center min-h-screen bg-gray-50 dark:bg-gray-900 p-4">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="text-2xl font-bold text-center">Invalid Invite</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="bg-red-100 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 mb-4">
              <p className="text-red-800 dark:text-red-200 text-center">{error}</p>
            </div>
            <Button 
              onClick={() => router.push('/')} 
              className="w-full"
            >
              Go to Homepage
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex justify-center items-center min-h-screen bg-gray-50 dark:bg-gray-900 p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto bg-blue-100 dark:bg-blue-900/30 w-16 h-16 rounded-full flex items-center justify-center mb-4">
            <span className="text-2xl">🏢</span>
          </div>
          <CardTitle className="text-2xl font-bold">Organization Invite</CardTitle>
          <CardDescription>
            You've been invited to create a new organization on Yuba Platform
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
            <p className="text-blue-800 dark:text-blue-200 text-center">
              After accepting this invite, you'll be able to set up your organization and start using Yuba.
            </p>
          </div>
          
          <Button
            onClick={handleAcceptInvite}
            disabled={isAccepting}
            className="w-full bg-blue-600 hover:bg-blue-700"
          >
            {isAccepting ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Processing...
              </>
            ) : (
              'Accept Invite & Create Organization'
            )}
          </Button>
          
          <p className="text-center text-sm text-gray-600 dark:text-gray-400">
            By accepting this invite, you agree to our Terms of Service and Privacy Policy.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}