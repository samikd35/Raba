'use client';

import React, { useEffect, useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Loader2, AlertCircle } from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';
import VBProfileWizard from '@/components/venture-builder/vb-profile-wizard/VBProfileWizard';

function OnboardingContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { isAuthenticated, user } = useAuthStore();
  const [token, setToken] = useState<string | null>(null);
  const [email, setEmail] = useState<string | null>(null);
  const [isValidating, setIsValidating] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showWizard, setShowWizard] = useState(false);

  useEffect(() => {
    const invitationToken = searchParams.get('token');
    const invitedEmail = searchParams.get('email'); // Email from invitation link

    if (!invitationToken) {
      setError('No invitation token provided. Please use the link from your invitation email.');
      setIsValidating(false);
      return;
    }

    // Check if user is authenticated
    if (!isAuthenticated) {
      // Redirect to invite page with VB token and email
      const inviteParams = new URLSearchParams();
      inviteParams.set('vb_token', invitationToken);
      if (invitedEmail) {
        inviteParams.set('email', invitedEmail);
      }
      router.push(`/invite/${invitationToken}?${inviteParams.toString()}`);
      return;
    }

    // Check if user has selected a workspace (tenant_id exists)
    if (!user?.tenant_id) {
      // Redirect to workspace selector with return URL
      const redirectUrl = invitedEmail
        ? `/vb-onboarding?token=${invitationToken}&email=${encodeURIComponent(invitedEmail)}`
        : `/vb-onboarding?token=${invitationToken}`;
      router.push(`/choose-workspace?redirect=${encodeURIComponent(redirectUrl)}`);
      return;
    }

    setToken(invitationToken);
    setEmail(invitedEmail);
    setShowWizard(true);
    setIsValidating(false);
  }, [searchParams, isAuthenticated, user, router]);

  const handleSuccess = () => {
    // Redirect to VB dashboard after successful profile creation
    router.push('/workspace');
  };

  const handleClose = () => {
    // Redirect to home if user closes without completing
    router.push('/');
  };

  if (isValidating) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-brand-500 dark:text-brand-400 mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-400">Validating invitation...</p>
        </div>
      </div>
    );
  }

  if (error || !token) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white dark:bg-gray-800 rounded-lg shadow-xl p-8 border border-red-200 dark:border-red-800">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-12 h-12 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center">
              <AlertCircle className="w-6 h-6 text-red-600 dark:text-red-400" />
            </div>
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">
              Invalid Invitation
            </h1>
          </div>
          <p className="text-gray-600 dark:text-gray-400 mb-6">
            {error || 'The invitation link is invalid or has expired.'}
          </p>
          <button
            onClick={() => router.push('/')}
            className="w-full px-6 py-3 bg-brand-500 hover:bg-brand-600 text-white rounded-lg font-semibold transition-colors"
          >
            Go to Home
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-8 px-4 sm:px-6 lg:px-8">
      <VBProfileWizard
        isOpen={showWizard}
        onClose={handleClose}
        onSuccess={handleSuccess}
        invitationToken={token}
        invitedEmail={email}
      />
    </div>
  );
}

export default function OnboardingPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
          <Loader2 className="w-8 h-8 animate-spin text-brand-500 dark:text-brand-400" />
        </div>
      }
    >
      <OnboardingContent />
    </Suspense>
  );
}
