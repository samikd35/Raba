'use client';

import React, { useEffect, useState, useRef } from 'react';
import { CreditCard, AlertCircle, CheckCircle2 } from 'lucide-react';
import { checkBookingCredits } from '@/lib/api/venture-builder';
import { VBProfile, CheckCreditsResponse } from '@/types/ventureBuilder';
import { authService } from '@/services/authService';
import { toast } from 'react-hot-toast';
import { useRouter } from 'next/navigation';

interface Step2CheckCreditsProps {
  ventureBuilder: VBProfile;
  onCreditsChecked: (hasCredits: boolean, creditDetails: {
    currentBalance: number;
    requiredCredits: number;
    vbCreditPrice: number;
  }) => void;
}

export default function Step2CheckCredits({ ventureBuilder, onCreditsChecked }: Step2CheckCreditsProps) {
  const router = useRouter();
  const [creditInfo, setCreditInfo] = useState<CheckCreditsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Use ref to avoid infinite loops from callback changes
  const onCreditsCheckedRef = useRef(onCreditsChecked);
  onCreditsCheckedRef.current = onCreditsChecked;

  const handlePurchaseCredits = () => {
    // Navigate to credits purchase page
    router.push('/credits/purchase');
  };

  useEffect(() => {
    const checkCredits = async () => {
      try {
        setIsLoading(true);
        const token = authService.getCurrentToken();
        if (!token) {
          throw new Error('Authentication required');
        }

        console.log('Step2CheckCredits - VB data:', {
          id: ventureBuilder.id,
          credit_price_per_hour: ventureBuilder.credit_price_per_hour,
          full_name: ventureBuilder.full_name,
        });

        const response = await checkBookingCredits(ventureBuilder.id, token, ventureBuilder.credit_price_per_hour);

        console.log('Step2CheckCredits - API response:', response);

        setCreditInfo(response);
        onCreditsCheckedRef.current(response.has_sufficient_credits, {
          currentBalance: response.current_balance,
          requiredCredits: response.required_credits,
          vbCreditPrice: response.vb_credit_price,
        });
      } catch (error: any) {
        console.error('Error checking credits:', error);
        toast.error(error.message || 'Failed to check credit balance');
        onCreditsCheckedRef.current(false, {
          currentBalance: 0,
          requiredCredits: 0,
          vbCreditPrice: 0,
        });
      } finally {
        setIsLoading(false);
      }
    };

    checkCredits();
  }, [ventureBuilder.id, ventureBuilder.credit_price_per_hour]);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
            Checking Credits
          </h3>
          <p className="text-gray-600 dark:text-gray-400">
            Verifying your credit balance...
          </p>
        </div>
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-500 dark:border-brand-400"></div>
        </div>
      </div>
    );
  }

  if (!creditInfo) {
    return (
      <div className="space-y-6">
        <div>
          <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
            Credit Check Failed
          </h3>
          <p className="text-gray-600 dark:text-gray-400">
            Unable to verify your credit balance. Please try again.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
          Credit Balance
        </h3>
        <p className="text-gray-600 dark:text-gray-400">
          Review your credit balance and session cost.
        </p>
      </div>

      {/* Credit Summary Card */}
      <div className="p-6 bg-gradient-to-br from-brand-50 to-brand-100 dark:from-brand-900/20 dark:to-brand-800/20 rounded-xl border border-brand-200 dark:border-brand-700">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-12 h-12 rounded-lg bg-brand-500 dark:bg-brand-600 flex items-center justify-center">
            <CreditCard className="w-6 h-6 text-white" />
          </div>
          <div>
            <h4 className="text-lg font-semibold text-brand-700 dark:text-brand-200">
              Session Cost
            </h4>
            <p className="text-sm text-brand-600 dark:text-brand-400">
              {ventureBuilder.full_name}
            </p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="p-4 bg-white dark:bg-gray-800 rounded-lg">
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Current Balance</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              {creditInfo.current_balance}
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">credits</p>
          </div>
          <div className="p-4 bg-white dark:bg-gray-800 rounded-lg">
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Session Cost</p>
            <p className="text-2xl font-bold text-brand-600 dark:text-brand-400">
              {creditInfo.required_credits}
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">credits/hour</p>
          </div>
        </div>

        {creditInfo.has_sufficient_credits && (
          <div className="mt-4 p-3 bg-white dark:bg-gray-800 rounded-lg">
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Remaining After Booking</p>
            <p className="text-xl font-semibold text-green-600 dark:text-green-400">
              {creditInfo.current_balance - creditInfo.required_credits} credits
            </p>
          </div>
        )}
      </div>

      {/* Status Message */}
      {creditInfo.has_sufficient_credits ? (
        <div className="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-700 rounded-lg flex items-start gap-3">
          <CheckCircle2 className="w-5 h-5 text-green-600 dark:text-green-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-green-800 dark:text-green-300">
              Sufficient Credits Available
            </p>
            <p className="text-sm text-green-700 dark:text-green-400 mt-1">
              You have enough credits to book this session. Proceed to select your preferred time slot.
            </p>
          </div>
        </div>
      ) : (
        <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700 rounded-lg flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-red-800 dark:text-red-300">
              Insufficient Credits
            </p>
            <p className="text-sm text-red-700 dark:text-red-400 mt-1">
              You need {creditInfo.required_credits - creditInfo.current_balance} more credits to book this session.
              Please purchase additional credits to continue.
            </p>
            <button
              onClick={handlePurchaseCredits}
              className="mt-3 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium transition-colors"
            >
              Purchase Credits
            </button>
          </div>
        </div>
      )}

      {/* Pricing Info */}
      <div className="p-4 bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 rounded-lg">
        <p className="text-xs text-gray-600 dark:text-gray-400">
          <strong>Note:</strong> This VB charges {creditInfo.vb_credit_price} credits per hour.
          Sessions are 60 minutes long. Credits will be deducted upon confirmation.
        </p>
      </div>
    </div>
  );
}
