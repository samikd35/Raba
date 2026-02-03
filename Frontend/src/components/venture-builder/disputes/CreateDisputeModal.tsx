'use client';

import { useState, useEffect } from 'react';
import { X, AlertTriangle, Loader2, AlertCircle, CheckCircle } from 'lucide-react';
import { canOpenDispute, createDispute } from '@/lib/api/venture-builder';
import { authService } from '@/services/authService';
import { toast } from 'react-hot-toast';
import type { Dispute, DisputeReason, CreateDisputePayload } from '@/types/ventureBuilder';

interface CreateDisputeModalProps {
  sessionId: string;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (dispute: Dispute) => void;
}

const DISPUTE_REASONS: { value: DisputeReason; label: string; description: string }[] = [
  {
    value: 'missed_session',
    label: 'Missed Session',
    description: 'The venture builder did not attend the scheduled session',
  },
  {
    value: 'time_theft',
    label: 'Time Discrepancy',
    description: 'The session was significantly shorter than scheduled or there was a billing issue',
  },
  {
    value: 'other',
    label: 'Other Issue',
    description: 'Another issue not covered by the options above',
  },
];

export default function CreateDisputeModal({ sessionId, isOpen, onClose, onSuccess }: CreateDisputeModalProps) {
  const [isCheckingEligibility, setIsCheckingEligibility] = useState(true);
  const [canDispute, setCanDispute] = useState(false);
  const [ineligibleReason, setIneligibleReason] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Form state
  const [reason, setReason] = useState<DisputeReason | ''>('');
  const [customReason, setCustomReason] = useState('');
  const [description, setDescription] = useState('');

  useEffect(() => {
    if (isOpen && sessionId) {
      checkEligibility();
    }
  }, [isOpen, sessionId]);

  const checkEligibility = async () => {
    try {
      setIsCheckingEligibility(true);
      setCanDispute(false);
      setIneligibleReason(null);

      const token = authService.getCurrentToken();
      if (!token) {
        throw new Error('Authentication required');
      }

      const response = await canOpenDispute(sessionId, token);
      setCanDispute(response.can_open_dispute);
      if (!response.can_open_dispute && response.reason) {
        setIneligibleReason(response.reason);
      }
    } catch (err: any) {
      console.error('Error checking dispute eligibility:', err);
      setCanDispute(false);
      setIneligibleReason(err.message || 'Unable to check eligibility');
    } finally {
      setIsCheckingEligibility(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!reason) {
      toast.error('Please select a reason for your dispute');
      return;
    }

    if (reason === 'other' && customReason.length < 10) {
      toast.error('Please provide a custom reason (at least 10 characters)');
      return;
    }

    try {
      setIsSubmitting(true);

      const token = authService.getCurrentToken();
      if (!token) {
        throw new Error('Authentication required');
      }

      const payload: CreateDisputePayload = {
        reason,
        custom_reason: reason === 'other' ? customReason : undefined,
        description: description || undefined,
      };

      const dispute = await createDispute(sessionId, payload, token);
      toast.success('Dispute submitted successfully. Our team will review it shortly.');
      onSuccess(dispute);
      onClose();
    } catch (err: any) {
      console.error('Error creating dispute:', err);
      toast.error(err.message || 'Failed to submit dispute');
    } finally {
      setIsSubmitting(false);
    }
  };

  const resetForm = () => {
    setReason('');
    setCustomReason('');
    setDescription('');
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 backdrop-blur-sm transition-opacity"
        onClick={handleClose}
      />

      {/* Modal */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative w-full max-w-lg bg-white dark:bg-gray-900 rounded-xl shadow-2xl border border-gray-200 dark:border-gray-700">
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-warning-100 dark:bg-warning-900/30 rounded-lg">
                <AlertTriangle className="w-5 h-5 text-warning-600 dark:text-warning-400" />
              </div>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                Report an Issue
              </h2>
            </div>
            <button
              onClick={handleClose}
              className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Content */}
          <div className="p-6">
            {isCheckingEligibility ? (
              <div className="flex flex-col items-center justify-center py-8">
                <Loader2 className="w-8 h-8 animate-spin text-brand-500 dark:text-brand-400 mb-4" />
                <p className="text-gray-600 dark:text-gray-400">Checking eligibility...</p>
              </div>
            ) : !canDispute ? (
              <div className="text-center py-8">
                <div className="w-16 h-16 bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-4">
                  <AlertCircle className="w-8 h-8 text-gray-400" />
                </div>
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                  Cannot Open Dispute
                </h3>
                <p className="text-gray-600 dark:text-gray-400 max-w-sm mx-auto">
                  {ineligibleReason || 'You are not eligible to open a dispute for this session.'}
                </p>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-6">
                {/* Reason Selection */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                    What issue did you experience? <span className="text-error-500">*</span>
                  </label>
                  <div className="space-y-3">
                    {DISPUTE_REASONS.map((option) => (
                      <label
                        key={option.value}
                        className={`flex items-start gap-3 p-4 border rounded-lg cursor-pointer transition-all ${
                          reason === option.value
                            ? 'border-brand-500 bg-brand-50 dark:bg-brand-900/20 dark:border-brand-400'
                            : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                        }`}
                      >
                        <input
                          type="radio"
                          name="reason"
                          value={option.value}
                          checked={reason === option.value}
                          onChange={(e) => setReason(e.target.value as DisputeReason)}
                          className="mt-1 w-4 h-4 text-brand-600 border-gray-300 focus:ring-brand-500"
                        />
                        <div>
                          <span className="block font-medium text-gray-900 dark:text-white">
                            {option.label}
                          </span>
                          <span className="block text-sm text-gray-500 dark:text-gray-400">
                            {option.description}
                          </span>
                        </div>
                      </label>
                    ))}
                  </div>
                </div>

                {/* Custom Reason (if "other" selected) */}
                {reason === 'other' && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Please specify the issue <span className="text-error-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={customReason}
                      onChange={(e) => setCustomReason(e.target.value)}
                      maxLength={200}
                      placeholder="Briefly describe the issue..."
                      className="w-full px-4 py-2.5 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-brand-500 focus:border-transparent transition-all"
                    />
                    <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                      {customReason.length}/200 characters (minimum 10)
                    </p>
                  </div>
                )}

                {/* Description */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Additional details (optional)
                  </label>
                  <textarea
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    maxLength={2000}
                    rows={4}
                    placeholder="Provide any additional context or details that might help us investigate..."
                    className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-brand-500 focus:border-transparent transition-all resize-none"
                  />
                  <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                    {description.length}/2000 characters
                  </p>
                </div>

                {/* Info Note */}
                <div className="p-3 bg-blue-light-50 dark:bg-blue-light-900/20 border border-blue-light-200 dark:border-blue-light-800 rounded-lg">
                  <p className="text-xs text-blue-light-700 dark:text-blue-light-300">
                    <strong>Note:</strong> Our team will review your dispute and respond within 2-3 business days.
                    You will be notified of the outcome.
                  </p>
                </div>
              </form>
            )}
          </div>

          {/* Footer */}
          {!isCheckingEligibility && canDispute && (
            <div className="flex items-center justify-end gap-3 p-6 border-t border-gray-200 dark:border-gray-700">
              <button
                type="button"
                onClick={handleClose}
                disabled={isSubmitting}
                className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg font-medium transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmit}
                disabled={isSubmitting || !reason}
                className="px-4 py-2 bg-warning-600 hover:bg-warning-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Submitting...
                  </>
                ) : (
                  <>
                    <AlertTriangle className="w-4 h-4" />
                    Submit Dispute
                  </>
                )}
              </button>
            </div>
          )}

          {/* Footer for ineligible state */}
          {!isCheckingEligibility && !canDispute && (
            <div className="flex justify-end p-6 border-t border-gray-200 dark:border-gray-700">
              <button
                onClick={handleClose}
                className="px-4 py-2 bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg font-medium transition-colors"
              >
                Close
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
