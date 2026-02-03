"use client";

import React, { useState } from 'react';
import { creditRequestService } from '@/lib/api/creditRequestService';
import { useCreditRequestStore } from '@/stores/creditRequestStore';
import { toast } from "react-hot-toast";
import { X, CreditCard, AlertCircle } from 'lucide-react';

interface CreditRequestModalProps {
  isOpen: boolean;
  onClose: () => void;
  teamId: string;
  currentCredits: {
    total: number;
    used: number;
    remaining: number;
  };
}

export default function CreditRequestModal({
  isOpen,
  onClose,
  teamId,
  currentCredits,
}: CreditRequestModalProps) {
  const [requestedCredits, setRequestedCredits] = useState<string>('');
  const [reason, setReason] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { addRequest } = useCreditRequestStore();

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const credits = parseInt(requestedCredits);
    if (!credits || credits <= 0) {
      toast.error('Please enter a valid credit amount');
      return;
    }

    if (credits > 10000) {
      toast.error('Maximum request is 10,000 credits at a time');
      return;
    }

    setIsSubmitting(true);

    try {
      const request = await creditRequestService.createCreditRequest(teamId, {
        requested_credits: credits,
        reason: reason.trim() || undefined,
      });

      addRequest(request);
      toast.success('Credit request submitted successfully');
      
      // Reset form
      setRequestedCredits('');
      setReason('');
      onClose();
    } catch (error: any) {
      console.error('Failed to create credit request:', error);
      toast.error(error.message || 'Failed to submit credit request');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    if (!isSubmitting) {
      setRequestedCredits('');
      setReason('');
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-md mx-4">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white flex items-center space-x-2">
            <CreditCard className="w-5 h-5" />
            <span>Request Additional Credits</span>
          </h2>
          <button
            onClick={handleClose}
            disabled={isSubmitting}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 disabled:opacity-50"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Current Credits Info */}
        <div className="p-6 bg-blue-50 dark:bg-blue-900/20 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
            Current Team Credits
          </h3>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400">Total</p>
              <p className="text-lg font-semibold text-gray-900 dark:text-white">
                {currentCredits.total.toLocaleString()}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400">Used</p>
              <p className="text-lg font-semibold text-orange-600">
                {currentCredits.used.toLocaleString()}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400">Remaining</p>
              <p className="text-lg font-semibold text-green-600">
                {currentCredits.remaining.toLocaleString()}
              </p>
            </div>
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* Credits Requested */}
          <div>
            <label
              htmlFor="credits"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
            >
              Credits Requested <span className="text-red-500">*</span>
            </label>
            <input
              id="credits"
              type="number"
              min="1"
              max="10000"
              value={requestedCredits}
              onChange={(e) => setRequestedCredits(e.target.value)}
              placeholder="Enter amount (e.g., 500)"
              required
              disabled={isSubmitting}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50"
            />
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              Maximum: 10,000 credits per request
            </p>
          </div>

          {/* Reason */}
          <div>
            <label
              htmlFor="reason"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
            >
              Reason (Optional)
            </label>
            <textarea
              id="reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Explain why you need additional credits..."
              rows={4}
              maxLength={1000}
              disabled={isSubmitting}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 resize-none"
            />
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              {reason.length}/1000 characters
            </p>
          </div>

          {/* Info Alert */}
          <div className="flex items-start space-x-2 p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
            <AlertCircle className="w-5 h-5 text-yellow-600 dark:text-yellow-400 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-yellow-800 dark:text-yellow-200">
              Your request will be reviewed by an Organization Admin. You'll be notified once it's approved or rejected.
            </p>
          </div>

          {/* Actions */}
          <div className="flex justify-end space-x-3 pt-4">
            <button
              type="button"
              onClick={handleClose}
              disabled={isSubmitting}
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !requestedCredits || parseInt(requestedCredits) <= 0}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center space-x-2"
            >
              {isSubmitting ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  <span>Submitting...</span>
                </>
              ) : (
                <>
                  <CreditCard className="w-4 h-4" />
                  <span>Submit Request</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
