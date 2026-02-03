"use client";

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { authService } from '@/services/authService';
import { InvitationFlowManager } from '@/lib/auth/invitationFlowManager';
import { organizationService } from '@/lib/api/organizationService';
import { useAuthStore } from '@/stores/authStore';
import { Building2, CheckCircle, XCircle, Loader2, AlertCircle } from 'lucide-react';
import toast from 'react-hot-toast';

export default function TokenRedirectClient({ token }: { token: string }) {
  const router = useRouter();
  const { user, isAuthenticated } = useAuthStore();
  const [message, setMessage] = useState('Processing invite...');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [organizationInfo, setOrganizationInfo] = useState<{
    name?: string;
    id?: string;
  } | null>(null);

  useEffect(() => {
    let cancelled = false;

    const handleInvitation = async () => {
      if (!token) {
        setError('Invalid invite token.');
        setIsLoading(false);
        return;
      }

      try {
        // Get organization ID from query parameter
        const urlParams = new URLSearchParams(window.location.search);
        const orgId = urlParams.get('org_id');

        if (!orgId) {
          setError('Organization ID not found in invitation link. Please request a new invitation.');
          setIsLoading(false);
          return;
        }

        // Check if user is authenticated
        const authed = authService.isAuthenticated && authService.isAuthenticated();

        if (!authed) {
          // Store token and redirect to sign-in
          setMessage('Redirecting to sign-in...');
          InvitationFlowManager.storeInvitationToken({
            token,
            type: 'org_member',
            organizationId: orgId,
            timestamp: Date.now(),
          });

          // Preserve the org_id in the return URL
          const returnUrl = `/org-invite/${token}?org_id=${orgId}`;
          router.push(`/signin?returnUrl=${encodeURIComponent(returnUrl)}`);
          return;
        }

        // User is authenticated, proceed with join flow
        setMessage('Joining organization...');

        // Join the organization
        const result = await organizationService.joinOrganization(orgId, token);

        if (!result.success) {
          throw new Error(result.message || 'Failed to join organization');
        }

        // Clear the stored invitation token
        InvitationFlowManager.clearInvitationToken();

        // Check if user is a team leader
        setMessage('Checking your role...');
        const isTeamLeader = await organizationService.isTeamLeader(orgId);

        toast.success('Successfully joined organization!');
        setMessage('Redirecting...');

        // Route based on role
        if (isTeamLeader) {
          // Redirect to team leader onboarding to create their team
          router.push('/admin/team-leader-onboarding');
        } else {
          // Redirect to organization dashboard
          router.push(`/admin/organizations/${orgId}`);
        }

      } catch (err: any) {
        console.error('Failed to join organization:', err);

        // Handle specific error types with user-friendly messages
        let errorMessage = 'Failed to join organization. Please try again.';
        let errorType: 'expired' | 'invalid' | 'already_member' | 'network' | 'generic' = 'generic';

        if (err?.message) {
          const msg = err.message.toLowerCase();

          if (msg.includes('expired') || msg.includes('expire')) {
            errorMessage = 'This invitation link has expired. Invitation links are valid for 48 hours.';
            errorType = 'expired';
          } else if (msg.includes('invalid') || msg.includes('bad signature') || msg.includes('mismatch')) {
            errorMessage = 'This invitation link is invalid or has been tampered with.';
            errorType = 'invalid';
          } else if (msg.includes('already') || msg.includes('existing')) {
            errorMessage = 'You are already a member of this organization.';
            errorType = 'already_member';
          } else if (msg.includes('network') || msg.includes('fetch') || msg.includes('connection')) {
            errorMessage = 'Network error. Please check your connection and try again.';
            errorType = 'network';
          } else if (msg.includes('not found') || msg.includes('doesn\'t have an invite')) {
            errorMessage = 'No invitation found for your account. Please contact the organization admin.';
            errorType = 'invalid';
          } else {
            errorMessage = err.message;
          }
        }

        setError(errorMessage);
        toast.error(errorMessage);
        setIsLoading(false);
      }
    };

    handleInvitation();

    return () => {
      cancelled = true;
    };
  }, [token, router, user, isAuthenticated]);

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50 dark:bg-gray-900">
        <div className="max-w-md w-full mx-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-8">
            <div className="flex items-center justify-center mb-6">
              <div className="w-16 h-16 bg-red-100 dark:bg-red-900/20 rounded-full flex items-center justify-center">
                <XCircle className="w-10 h-10 text-red-600 dark:text-red-400" />
              </div>
            </div>

            <h2 className="text-2xl font-bold text-center text-gray-900 dark:text-white mb-4">
              Invitation Error
            </h2>

            <p className="text-center text-gray-600 dark:text-gray-400 mb-6">
              {error}
            </p>

            {/* Helpful information box */}
            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 mb-6">
              <div className="flex items-start">
                <AlertCircle className="w-5 h-5 text-blue-600 dark:text-blue-400 mt-0.5 mr-3 flex-shrink-0" />
                <div className="text-sm text-blue-800 dark:text-blue-200">
                  <p className="font-semibold mb-1">What to do next:</p>
                  <ul className="list-disc list-inside space-y-1">
                    <li>Contact your organization administrator to request a new invitation</li>
                    <li>Make sure you're using the correct email address</li>
                    <li>Check that you clicked the link within 48 hours of receiving it</li>
                  </ul>
                </div>
              </div>
            </div>

            <div className="space-y-3">
              <button
                onClick={() => router.push('/signin')}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-6 rounded-lg transition-colors"
              >
                Go to Sign In
              </button>

              <button
                onClick={() => window.location.reload()}
                className="w-full bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-900 dark:text-white font-semibold py-3 px-6 rounded-lg transition-colors"
              >
                Try Again
              </button>

              <div className="text-center pt-2">
                <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">
                  Need help?
                </p>
                <div className="flex justify-center space-x-4">
                  <a
                    href="mailto:support@yuba.com"
                    className="text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400 hover:underline"
                  >
                    Email Support
                  </a>
                  <span className="text-gray-300 dark:text-gray-600">|</span>
                  <a
                    href="/help"
                    className="text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400 hover:underline"
                  >
                    Help Center
                  </a>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="max-w-md w-full mx-4">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-8">
          <div className="flex items-center justify-center mb-6">
            <div className="w-16 h-16 bg-blue-100 dark:bg-blue-900/20 rounded-full flex items-center justify-center">
              <Loader2 className="w-10 h-10 text-blue-600 dark:text-blue-400 animate-spin" />
            </div>
          </div>

          <h2 className="text-2xl font-bold text-center text-gray-900 dark:text-white mb-4">
            Processing Invitation
          </h2>

          <p className="text-center text-gray-600 dark:text-gray-400">
            {message}
          </p>
        </div>
      </div>
    </div>
  );
}
