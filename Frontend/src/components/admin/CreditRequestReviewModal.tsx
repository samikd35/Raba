"use client";

import React, { useState } from 'react';
import { creditRequestService } from '@/lib/api/creditRequestService';
import { CreditRequest } from '@/types/team';
import { toast } from "react-hot-toast";
import { X, CheckCircle, XCircle, AlertCircle } from 'lucide-react';

interface CreditRequestReviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  request: CreditRequest | null;
  organizationId: string;
  onReviewComplete: () => void;
}

export default function CreditRequestReviewModal({
  isOpen,
  onClose,
  request,
  organizationId,
  onReviewComplete,
}: CreditRequestReviewModalProps) {
  const [action, setAction] = useState<'approve' | 'reject'>('approve');
  const [creditsAllocated, setCreditsAllocated] = useState('');
  const [reviewNotes, setReviewNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen || !request) return null;

  // Initialize credits allocated with requested amount when modal opens
  React.useEffect(() => {
    if (request) {
      setCreditsAllocated(request.requested_credits.toString());
      setAction('approve');
      setReviewNotes('');
    }
  }, [request]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (action === 'approve') {
      const credits = parseInt(creditsAllocated);
      if (!credits || credits <= 0) {
        toast.error('Please enter a valid credit amount');
        return;
      }
    }

    if (action === 'reject' && !reviewNotes.trim()) {
      toast.error('Please provide a reason for rejection');
      return;
    }

    setIsSubmitting(true);

    try {
      await creditRequestService.reviewCreditRequest(
        organizationId,
        request.request_id,
        {
          action,
          credits_allocated: action === 'approve' ? parseInt(creditsAllocated) : undefined,
          review_notes: reviewNotes.trim() || undefined,
        }
      );

      toast.success(
        action === 'approve'
          ? 'Credit request approved successfully'
          : 'Credit request rejected'
      );

      onReviewComplete();
      handleClose();
    } catch (error: any) {
      console.error('Failed to review credit request:', error);
      toast.error(error.message || 'Failed to review request');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    if (!isSubmitting) {
      setAction('approve');
      setCreditsAllocated('');
      setReviewNotes('');
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700 sticky top-0 bg-white dark:bg-gray-800">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            Review Credit Request
          </h2>
          <button
            onClick={handleClose}
            disabled={isSubmitting}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 disabled:opacity-50"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Request Details */}
        <div className="p-6 bg-gray-50 dark:bg-gray-900/50 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-4">
            Request Details
          </h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400">Team</p>
              <p className="text-sm font-medium text-gray-900 dark:text-white">
                {request.team_name || 'Unknown Team'}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400">Requester</p>
              <p className="text-sm font-medium text-gray-900 dark:text-white">
                {request.requester_name}
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {request.requester_email}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400">Credits Requested</p>
              <p className="text-lg font-semibold text-blue-600 dark:text-blue-400">
                {request.requested_credits.toLocaleString()}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400">Submitted</p>
              <p className="text-sm font-medium text-gray-900 dark:text-white">
                {new Date(request.created_at).toLocaleString()}
              </p>
            </div>
          </div>
          {request.reason && (
            <div className="mt-4">
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Reason</p>
              <p className="text-sm text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 p-3 rounded-lg border border-gray-200 dark:border-gray-700">
                {request.reason}
              </p>
            </div>
          )}
        </div>

        {/* Review Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* Action Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
              Decision <span className="text-red-500">*</span>
            </label>
            <div className="grid grid-cols-2 gap-4">
              <button
                type="button"
                onClick={() => setAction('approve')}
                disabled={isSubmitting}
                className={`p-4 border-2 rounded-lg transition-all ${
                  action === 'approve'
                    ? 'border-green-500 bg-green-50 dark:bg-green-900/20'
                    : 'border-gray-300 dark:border-gray-600 hover:border-green-300'
                } disabled:opacity-50`}
              >
                <CheckCircle
                  className={`w-6 h-6 mx-auto mb-2 ${
                    action === 'approve' ? 'text-green-600' : 'text-gray-400'
                  }`}
                />
                <p
                  className={`text-sm font-medium ${
                    action === 'approve'
                      ? 'text-green-700 dark:text-green-300'
                      : 'text-gray-700 dark:text-gray-300'
                  }`}
                >
                  Approve Request
                </p>
              </button>
              <button
                type="button"
                onClick={() => setAction('reject')}
                disabled={isSubmitting}
                className={`p-4 border-2 rounded-lg transition-all ${
                  action === 'reject'
                    ? 'border-red-500 bg-red-50 dark:bg-red-900/20'
                    : 'border-gray-300 dark:border-gray-600 hover:border-red-300'
                } disabled:opacity-50`}
              >
                <XCircle
                  className={`w-6 h-6 mx-auto mb-2 ${
                    action === 'reject' ? 'text-red-600' : 'text-gray-400'
                  }`}
                />
                <p
                  className={`text-sm font-medium ${
                    action === 'reject'
                      ? 'text-red-700 dark:text-red-300'
                      : 'text-gray-700 dark:text-gray-300'
                  }`}
                >
                  Reject Request
                </p>
              </button>
            </div>
          </div>

          {/* Credits to Allocate (only for approve) */}
          {action === 'approve' && (
            <div>
              <label
                htmlFor="credits"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
              >
                Credits to Allocate <span className="text-red-500">*</span>
              </label>
              <input
                id="credits"
                type="number"
                min="1"
                value={creditsAllocated}
                onChange={(e) => setCreditsAllocated(e.target.value)}
                placeholder="Enter amount"
                required
                disabled={isSubmitting}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50"
              />
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                You can allocate a different amount than requested
              </p>
            </div>
          )}

          {/* Review Notes */}
          <div>
            <label
              htmlFor="notes"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
            >
              Review Notes {action === 'reject' && <span className="text-red-500">*</span>}
            </label>
            <textarea
              id="notes"
              value={reviewNotes}
              onChange={(e) => setReviewNotes(e.target.value)}
              placeholder={
                action === 'approve'
                  ? 'Add any notes about this approval (optional)...'
                  : 'Explain why this request is being rejected...'
              }
              rows={4}
              maxLength={1000}
              required={action === 'reject'}
              disabled={isSubmitting}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 resize-none"
            />
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              {reviewNotes.length}/1000 characters
            </p>
          </div>

          {/* Warning for Rejection */}
          {action === 'reject' && (
            <div className="flex items-start space-x-2 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
              <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-red-800 dark:text-red-200">
                The team leader will be notified of this rejection. Make sure to provide a clear explanation.
              </p>
            </div>
          )}

          {/* Actions */}
          <div className="flex justify-end space-x-3 pt-4 border-t border-gray-200 dark:border-gray-700">
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
              disabled={isSubmitting}
              className={`px-4 py-2 rounded-lg text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center space-x-2 ${
                action === 'approve'
                  ? 'bg-green-600 hover:bg-green-700'
                  : 'bg-red-600 hover:bg-red-700'
              }`}
            >
              {isSubmitting ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  <span>Processing...</span>
                </>
              ) : (
                <>
                  {action === 'approve' ? (
                    <>
                      <CheckCircle className="w-4 h-4" />
                      <span>Approve Request</span>
                    </>
                  ) : (
                    <>
                      <XCircle className="w-4 h-4" />
                      <span>Reject Request</span>
                    </>
                  )}
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
