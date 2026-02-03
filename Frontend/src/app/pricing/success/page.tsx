"use client";

import React, { useEffect, useState, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { motion } from 'framer-motion';
import { CheckCircle2, Loader2, AlertCircle, ArrowRight, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { StripePaymentService, StripeVerificationResponse } from '@/lib/api/stripePaymentService';
import { useAuthStore } from '@/stores/authStore';
import Link from 'next/link';

type VerificationStatus = 'loading' | 'success' | 'error';

export default function PaymentSuccessPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { isAuthenticated } = useAuthStore();
  
  const [status, setStatus] = useState<VerificationStatus>('loading');
  const [verificationData, setVerificationData] = useState<StripeVerificationResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string>('');

  const verifyPayment = useCallback(async () => {
    // Get session_id from query params (Stripe redirects with this)
    const sessionId = searchParams?.get('session_id');
    const paymentIntent = searchParams?.get('payment_intent');
    
    // Use session_id preferentially, fall back to payment_intent
    const verificationId = sessionId || paymentIntent;

    if (!verificationId) {
      setStatus('error');
      setErrorMessage('No payment session found. Please try again or contact support.');
      return;
    }

    try {
      // Try personal payment verification first
      let response: StripeVerificationResponse;
      
      try {
        response = await StripePaymentService.verifyPayment(verificationId);
      } catch (personalError) {
        // If personal verification fails, try organization verification
        // This handles cases where the user is making an org-level purchase
        console.log('Personal verification failed, trying org verification...');
        response = await StripePaymentService.verifyOrganizationPayment(verificationId);
      }

      if (response.success || response.status === 'complete') {
        setVerificationData(response);
        setStatus('success');
      } else {
        setStatus('error');
        setErrorMessage(response.message || 'Payment verification failed. Please contact support.');
      }
    } catch (error) {
      console.error('Payment verification error:', error);
      setStatus('error');
      setErrorMessage(
        error instanceof Error
          ? error.message
          : 'Failed to verify payment. Please try again or contact support.'
      );
    }
  }, [searchParams]);

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/auth');
      return;
    }

    verifyPayment();
  }, [isAuthenticated, verifyPayment, router]);

  const handleRetry = () => {
    setStatus('loading');
    setErrorMessage('');
    verifyPayment();
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.3 }}
        className="w-full max-w-md"
      >
        {/* Loading State */}
        {status === 'loading' && (
          <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg p-8 text-center">
            <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-brand-50 dark:bg-brand-500/10 flex items-center justify-center">
              <Loader2 className="w-8 h-8 text-brand-500 animate-spin" />
            </div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
              Verifying Payment
            </h1>
            <p className="text-gray-600 dark:text-gray-400">
              Please wait while we confirm your payment...
            </p>
          </div>
        )}

        {/* Success State */}
        {status === 'success' && (
          <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg p-8 text-center">
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: 'spring', stiffness: 200, delay: 0.1 }}
              className="w-16 h-16 mx-auto mb-6 rounded-full bg-green-100 dark:bg-green-500/10 flex items-center justify-center"
            >
              <CheckCircle2 className="w-8 h-8 text-green-500" />
            </motion.div>
            
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
              Payment Successful!
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              {verificationData?.message || 'Your payment has been verified and credits have been allocated.'}
            </p>

            {/* Payment Details */}
            {verificationData && (
              <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4 mb-6 text-left">
                {verificationData.credits_allocated && (
                  <div className="flex justify-between items-center py-2 border-b border-gray-200 dark:border-gray-600">
                    <span className="text-sm text-gray-600 dark:text-gray-400">Credits Added</span>
                    <span className="font-semibold text-brand-500">
                      +{verificationData.credits_allocated}
                    </span>
                  </div>
                )}
                {verificationData.amount_paid && (
                  <div className="flex justify-between items-center py-2">
                    <span className="text-sm text-gray-600 dark:text-gray-400">Amount Paid</span>
                    <span className="font-semibold text-gray-900 dark:text-white">
                      ${verificationData.amount_paid} {verificationData.currency?.toUpperCase() || 'USD'}
                    </span>
                  </div>
                )}
              </div>
            )}

            {/* Actions */}
            <div className="space-y-3">
              <Button
                asChild
                className="w-full bg-brand-500 hover:bg-brand-600 text-white"
              >
                <Link href="/workspace">
                  Go to Dashboard
                  <ArrowRight className="w-4 h-4 ml-2" />
                </Link>
              </Button>
              <Button
                asChild
                variant="outline"
                className="w-full"
              >
                <Link href="/pricing">
                  View Pricing Plans
                </Link>
              </Button>
            </div>
          </div>
        )}

        {/* Error State */}
        {status === 'error' && (
          <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg p-8 text-center">
            <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-red-100 dark:bg-red-500/10 flex items-center justify-center">
              <AlertCircle className="w-8 h-8 text-red-500" />
            </div>
            
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
              Verification Failed
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              {errorMessage}
            </p>

            {/* Actions */}
            <div className="space-y-3">
              <Button
                onClick={handleRetry}
                className="w-full bg-brand-500 hover:bg-brand-600 text-white"
              >
                <RefreshCw className="w-4 h-4 mr-2" />
                Try Again
              </Button>
              <Button
                asChild
                variant="outline"
                className="w-full"
              >
                <Link href="/pricing">
                  Back to Pricing
                </Link>
              </Button>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-4">
                Need help?{' '}
                <a
                  href="mailto:info@yubanow.com"
                  className="text-brand-500 hover:text-brand-600 underline"
                >
                  Contact support
                </a>
              </p>
            </div>
          </div>
        )}
      </motion.div>
    </div>
  );
}
