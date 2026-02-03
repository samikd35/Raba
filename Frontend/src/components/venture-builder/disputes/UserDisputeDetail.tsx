'use client';

import { useState, useEffect } from 'react';
import { X, AlertTriangle, Loader2, AlertCircle, Calendar, MessageSquare, User, CheckCircle } from 'lucide-react';
import { getDisputeDetail } from '@/lib/api/venture-builder';
import { authService } from '@/services/authService';
import DisputeStatusBadge from './DisputeStatusBadge';
import type { Dispute } from '@/types/ventureBuilder';

interface UserDisputeDetailProps {
  disputeId: string;
  isOpen: boolean;
  onClose: () => void;
}

const REASON_LABELS: Record<string, string> = {
  missed_session: 'Missed Session',
  time_theft: 'Time Discrepancy',
  other: 'Other Issue',
};

export default function UserDisputeDetail({ disputeId, isOpen, onClose }: UserDisputeDetailProps) {
  const [dispute, setDispute] = useState<Dispute | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && disputeId) {
      loadDispute();
    }
  }, [isOpen, disputeId]);

  const loadDispute = async () => {
    try {
      setIsLoading(true);
      setError(null);

      const token = authService.getCurrentToken();
      if (!token) {
        throw new Error('Authentication required');
      }

      const data = await getDisputeDetail(disputeId, token);
      setDispute(data);
    } catch (err: any) {
      console.error('Error loading dispute:', err);
      setError(err.message || 'Failed to load dispute details');
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 backdrop-blur-sm transition-opacity"
        onClick={onClose}
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
                Dispute Details
              </h2>
            </div>
            <button
              onClick={onClose}
              className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Content */}
          <div className="p-6">
            {isLoading ? (
              <div className="flex flex-col items-center justify-center py-12">
                <Loader2 className="w-8 h-8 animate-spin text-brand-500 dark:text-brand-400 mb-4" />
                <p className="text-gray-600 dark:text-gray-400">Loading dispute details...</p>
              </div>
            ) : error ? (
              <div className="p-4 bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg">
                <div className="flex items-start gap-3">
                  <AlertCircle className="w-5 h-5 text-error-600 dark:text-error-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <h3 className="font-medium text-error-900 dark:text-error-200 mb-1">
                      Unable to load dispute
                    </h3>
                    <p className="text-sm text-error-700 dark:text-error-300">{error}</p>
                  </div>
                </div>
              </div>
            ) : !dispute ? (
              <div className="text-center py-12">
                <AlertCircle className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                  Dispute Not Found
                </h3>
              </div>
            ) : (
              <div className="space-y-6">
                {/* Status and Date */}
                <div className="flex items-center justify-between">
                  <DisputeStatusBadge status={dispute.status} />
                  <div className="flex items-center gap-1.5 text-sm text-gray-500 dark:text-gray-400">
                    <Calendar className="w-4 h-4" />
                    {new Date(dispute.created_at).toLocaleDateString('en-US', {
                      year: 'numeric',
                      month: 'short',
                      day: 'numeric',
                    })}
                  </div>
                </div>

                {/* Reason */}
                <div>
                  <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
                    Reason
                  </h4>
                  <p className="text-gray-900 dark:text-white font-medium">
                    {REASON_LABELS[dispute.reason] || dispute.reason}
                  </p>
                  {dispute.custom_reason && (
                    <p className="text-sm text-gray-600 dark:text-gray-400 mt-1 italic">
                      "{dispute.custom_reason}"
                    </p>
                  )}
                </div>

                {/* Description */}
                {dispute.description && (
                  <div>
                    <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">
                      Description
                    </h4>
                    <div className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                      <p className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                        {dispute.description}
                      </p>
                    </div>
                  </div>
                )}

                {/* Session Info */}
                {dispute.session_datetime && (
                  <div>
                    <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
                      Related Session
                    </h4>
                    <p className="text-gray-900 dark:text-white">
                      {new Date(dispute.session_datetime).toLocaleDateString('en-US', {
                        weekday: 'long',
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </p>
                    {dispute.vb_name && (
                      <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                        with {dispute.vb_name}
                      </p>
                    )}
                  </div>
                )}

                {/* Admin Response (if resolved) */}
                {dispute.admin_notes && (
                  <div className="p-4 bg-brand-50 dark:bg-brand-900/20 border border-brand-200 dark:border-brand-700 rounded-lg">
                    <div className="flex items-center gap-2 mb-2">
                      <MessageSquare className="w-4 h-4 text-brand-600 dark:text-brand-400" />
                      <h4 className="font-medium text-brand-900 dark:text-brand-200">
                        Admin Response
                      </h4>
                    </div>
                    <p className="text-sm text-brand-800 dark:text-brand-300">
                      {dispute.admin_notes}
                    </p>
                  </div>
                )}

                {/* Resolution Info */}
                {dispute.status === 'resolved' && dispute.resolved_at && (
                  <div className="flex items-center gap-2 p-3 bg-success-50 dark:bg-success-900/20 border border-success-200 dark:border-success-700 rounded-lg">
                    <CheckCircle className="w-5 h-5 text-success-600 dark:text-success-400" />
                    <span className="text-sm text-success-700 dark:text-success-300">
                      Resolved on {new Date(dispute.resolved_at).toLocaleDateString('en-US', {
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric',
                      })}
                    </span>
                  </div>
                )}

                {/* Pending Status Note */}
                {dispute.status === 'submitted' && (
                  <div className="p-3 bg-warning-50 dark:bg-warning-900/20 border border-warning-200 dark:border-warning-700 rounded-lg">
                    <p className="text-xs text-warning-700 dark:text-warning-300">
                      Your dispute has been submitted and is awaiting review. We'll notify you once there's an update.
                    </p>
                  </div>
                )}

                {dispute.status === 'under_review' && (
                  <div className="p-3 bg-brand-50 dark:bg-brand-900/20 border border-brand-200 dark:border-brand-700 rounded-lg">
                    <p className="text-xs text-brand-700 dark:text-brand-300">
                      Your dispute is currently being reviewed by our team. We'll notify you once a decision has been made.
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="flex justify-end p-6 border-t border-gray-200 dark:border-gray-700">
            <button
              onClick={onClose}
              className="px-4 py-2 bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg font-medium transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
