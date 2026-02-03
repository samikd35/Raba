'use client';

import { useState } from 'react';
import { X, Calendar, Loader2, AlertCircle, CheckCircle } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { ventureBuilderAPI } from '@/lib/api/ventureBuilderService';
import type { VBSession, RescheduleSessionResponse } from '@/types/ventureBuilder';

interface RescheduleInitiateModalProps {
  session: VBSession;
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export default function RescheduleInitiateModal({
  session,
  isOpen,
  onClose,
  onSuccess,
}: RescheduleInitiateModalProps) {
  const [reason, setReason] = useState('');
  const [apologyMessage, setApologyMessage] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [rescheduleResponse, setRescheduleResponse] =
    useState<RescheduleSessionResponse | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!reason.trim()) {
      toast.error('Please provide a reason for rescheduling');
      return;
    }

    try {
      setIsSubmitting(true);

      const response = await ventureBuilderAPI.reschedule.initiateReschedule(session.id, {
        reason: reason.trim(),
        apology_message: apologyMessage.trim() || undefined,
      });

      setRescheduleResponse(response);
      toast.success('Reschedule request sent to founder');
      onSuccess?.();
    } catch (error: any) {
      console.error('Failed to initiate reschedule:', error);
      toast.error(error.message || 'Failed to initiate reschedule');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    setReason('');
    setApologyMessage('');
    setRescheduleResponse(null);
    onClose();
  };

  const copyRescheduleUrl = () => {
    if (rescheduleResponse?.reschedule_url) {
      navigator.clipboard.writeText(rescheduleResponse.reschedule_url);
      toast.success('Reschedule link copied to clipboard');
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-yellow-100 dark:bg-yellow-900/20 rounded-lg">
              <Calendar className="w-5 h-5 text-yellow-600 dark:text-yellow-400" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                Reschedule Session
              </h2>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {new Date(session.session_datetime).toLocaleString('en-US', {
                  weekday: 'long',
                  month: 'long',
                  day: 'numeric',
                  hour: 'numeric',
                  minute: '2-digit',
                  hour12: true,
                })}
              </p>
            </div>
          </div>
          <button
            onClick={handleClose}
            className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {!rescheduleResponse ? (
            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
                <div className="flex items-start gap-2">
                  <AlertCircle className="w-5 h-5 text-yellow-600 dark:text-yellow-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-yellow-800 dark:text-yellow-300">
                      Important Information
                    </p>
                    <ul className="text-sm text-yellow-700 dark:text-yellow-400 mt-2 space-y-1 list-disc list-inside">
                      <li>The founder will receive a reschedule link via email</li>
                      <li>They can rebook without additional credit charges</li>
                      <li>The link expires in 7 days</li>
                      <li>The original session will be canceled once rescheduled</li>
                    </ul>
                  </div>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-900 dark:text-white mb-2">
                  Reason for Rescheduling <span className="text-red-500">*</span>
                </label>
                <textarea
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder="e.g., Unexpected conflict, personal emergency, etc."
                  rows={3}
                  maxLength={500}
                  required
                  className="w-full px-4 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:ring-2 focus:ring-brand-500 focus:border-transparent resize-none"
                />
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  {reason.length}/500 characters
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-900 dark:text-white mb-2">
                  Personalized Message (Optional)
                </label>
                <textarea
                  value={apologyMessage}
                  onChange={(e) => setApologyMessage(e.target.value)}
                  placeholder="Add a personalized apology or message to the founder..."
                  rows={4}
                  maxLength={1000}
                  className="w-full px-4 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:ring-2 focus:ring-brand-500 focus:border-transparent resize-none"
                />
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  {apologyMessage.length}/1000 characters
                </p>
              </div>

              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={handleClose}
                  className="flex-1 px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="flex-1 px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors inline-flex items-center justify-center gap-2"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Sending...
                    </>
                  ) : (
                    <>
                      <Calendar className="w-4 h-4" />
                      Send Reschedule Request
                    </>
                  )}
                </button>
              </div>
            </form>
          ) : (
            <div className="space-y-6">
              <div className="text-center py-6">
                <div className="w-16 h-16 bg-green-100 dark:bg-green-900/20 rounded-full flex items-center justify-center mx-auto mb-4">
                  <CheckCircle className="w-10 h-10 text-green-600 dark:text-green-400" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                  Reschedule Request Sent
                </h3>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  The founder has been notified and can rebook at their convenience.
                </p>
              </div>

              <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                <p className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Reschedule Link
                </p>
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={rescheduleResponse.reschedule_url}
                    readOnly
                    className="flex-1 px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white"
                  />
                  <button
                    onClick={copyRescheduleUrl}
                    className="px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 transition-colors text-sm font-medium"
                  >
                    Copy
                  </button>
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
                  Expires:{' '}
                  {new Date(rescheduleResponse.expires_at).toLocaleDateString('en-US', {
                    month: 'long',
                    day: 'numeric',
                    year: 'numeric',
                    hour: 'numeric',
                    minute: '2-digit',
                  })}
                </p>
              </div>

              <button
                onClick={handleClose}
                className="w-full px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 transition-colors"
              >
                Done
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
