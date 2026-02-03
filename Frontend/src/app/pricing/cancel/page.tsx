"use client";

import React from 'react';
import { motion } from 'framer-motion';
import { XCircle, ArrowLeft, CreditCard } from 'lucide-react';
import { Button } from '@/components/ui/button';
import Link from 'next/link';

export default function PaymentCancelPage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.3 }}
        className="w-full max-w-md"
      >
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg p-8 text-center">
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: 'spring', stiffness: 200, delay: 0.1 }}
            className="w-16 h-16 mx-auto mb-6 rounded-full bg-amber-100 dark:bg-amber-500/10 flex items-center justify-center"
          >
            <XCircle className="w-8 h-8 text-amber-500" />
          </motion.div>
          
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
            Payment Cancelled
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mb-6">
            Your payment was cancelled. No charges were made to your account.
          </p>

          {/* Info box */}
          <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4 mb-6 text-left">
            <p className="text-sm text-gray-600 dark:text-gray-400">
              If you experienced any issues during checkout or have questions about our pricing plans, 
              please don&apos;t hesitate to reach out to our support team.
            </p>
          </div>

          {/* Actions */}
          <div className="space-y-3">
            <Button
              asChild
              className="w-full bg-brand-500 hover:bg-brand-600 text-white"
            >
              <Link href="/pricing">
                <CreditCard className="w-4 h-4 mr-2" />
                Try Again
              </Link>
            </Button>
            <Button
              asChild
              variant="outline"
              className="w-full"
            >
              <Link href="/workspace">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back to Dashboard
              </Link>
            </Button>
          </div>

          <p className="text-sm text-gray-500 dark:text-gray-400 mt-6">
            Need help?{' '}
            <a
              href="mailto:info@yubanow.com"
              className="text-brand-500 hover:text-brand-600 underline"
            >
              Contact support
            </a>
          </p>
        </div>
      </motion.div>
    </div>
  );
}
