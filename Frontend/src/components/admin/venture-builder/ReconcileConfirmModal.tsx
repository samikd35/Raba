'use client';

import { useState } from 'react';
import { X, DollarSign, Loader2, AlertTriangle, CheckCircle, Calendar } from 'lucide-react';
import { reconcileVBPayments } from '@/lib/api/venture-builder';
import { authService } from '@/services/authService';
import { toast } from 'react-hot-toast';
import type { ReconcileResponse, ReconcilePayload } from '@/types/ventureBuilder';

interface ReconcileConfirmModalProps {
  vbId: string;
  vbName: string;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (result: ReconcileResponse) => void;
}

export default function ReconcileConfirmModal({
  vbId,
  vbName,
  isOpen,
  onClose,
  onSuccess,
}: ReconcileConfirmModalProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [notes, setNotes] = useState('');
  const [result, setResult] = useState<ReconcileResponse | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      setIsSubmitting(true);

      const token = authService.getCurrentToken();
      if (!token) {
        throw new Error('Authentication required');
      }

      const payload: ReconcilePayload = {
        start_date: startDate || undefined,
        end_date: endDate || undefined,
        notes: notes || undefined,
      };

      const response = await reconcileVBPayments(vbId, payload, token);
      setResult(response);
      toast.success(`Successfully reconciled $${response.amount_reconciled_usd.toFixed(2)} for ${vbName}`);
      onSuccess(response);
    } catch (err: any) {
      console.error('Error reconciling payments:', err);
      toast.error(err.message || 'Failed to reconcile payments');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    setStartDate('');
    setEndDate('');
    setNotes('');
    setResult(null);
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
        <div className="relative w-full max-w-md bg-white dark:bg-gray-900 rounded-xl shadow-2xl border border-gray-200 dark:border-gray-700">
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-success-100 dark:bg-success-900/30 rounded-lg">
                <DollarSign className="w-5 h-5 text-success-600 dark:text-success-400" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Reconcile Payments
                </h2>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {vbName}
                </p>
              </div>
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
            {result ? (
              /* Success Result */
              <div className="space-y-4">
                <div className="flex items-center gap-3 p-4 bg-success-50 dark:bg-success-900/20 border border-success-200 dark:border-success-700 rounded-lg">
                  <CheckCircle className="w-6 h-6 text-success-600 dark:text-success-400 flex-shrink-0" />
                  <div>
                    <h3 className="font-medium text-success-900 dark:text-success-200">
                      Reconciliation Complete
                    </h3>
                    <p className="text-sm text-success-700 dark:text-success-300">
                      Successfully processed payment reconciliation
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                    <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Amount Reconciled</p>
                    <p className="text-xl font-bold text-success-600 dark:text-success-400">
                      ${result.amount_reconciled_usd.toFixed(2)}
                    </p>
                  </div>
                  <div className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                    <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Sessions Settled</p>
                    <p className="text-xl font-bold text-gray-900 dark:text-white">
                      {result.sessions_marked_settled}
                    </p>
                  </div>
                </div>

                <div className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
                  <div className="flex justify-between">
                    <span>Previous Pending:</span>
                    <span className="font-medium text-gray-900 dark:text-white">
                      ${result.pending_amount_before.toFixed(2)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>New Pending:</span>
                    <span className="font-medium text-gray-900 dark:text-white">
                      ${result.pending_amount_after.toFixed(2)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>Total Lifetime Reconciled:</span>
                    <span className="font-medium text-gray-900 dark:text-white">
                      ${result.total_reconciled_lifetime.toFixed(2)}
                    </span>
                  </div>
                </div>
              </div>
            ) : (
              /* Confirm Form */
              <form onSubmit={handleSubmit} className="space-y-5">
                {/* Warning */}
                <div className="p-3 bg-warning-50 dark:bg-warning-900/20 border border-warning-200 dark:border-warning-700 rounded-lg">
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="w-5 h-5 text-warning-600 dark:text-warning-400 flex-shrink-0 mt-0.5" />
                    <p className="text-sm text-warning-700 dark:text-warning-300">
                      This action will mark all pending completed sessions as settled and record the payment.
                      This cannot be undone.
                    </p>
                  </div>
                </div>

                {/* Optional Date Range */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Date Range (Optional)
                  </label>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
                    Leave empty to reconcile all pending sessions
                  </p>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">From</label>
                      <div className="relative">
                        <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                        <input
                          type="date"
                          value={startDate}
                          onChange={(e) => setStartDate(e.target.value)}
                          className="w-full pl-10 pr-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-brand-500 focus:border-transparent"
                        />
                      </div>
                    </div>
                    <div>
                      <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">To</label>
                      <div className="relative">
                        <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                        <input
                          type="date"
                          value={endDate}
                          onChange={(e) => setEndDate(e.target.value)}
                          className="w-full pl-10 pr-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-brand-500 focus:border-transparent"
                        />
                      </div>
                    </div>
                  </div>
                </div>

                {/* Notes */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Notes (Optional)
                  </label>
                  <textarea
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="Add any notes about this reconciliation..."
                    rows={3}
                    className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-brand-500 focus:border-transparent resize-none"
                  />
                </div>
              </form>
            )}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-end gap-3 p-6 border-t border-gray-200 dark:border-gray-700">
            {result ? (
              <button
                onClick={handleClose}
                className="px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white rounded-lg font-medium transition-colors"
              >
                Done
              </button>
            ) : (
              <>
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
                  disabled={isSubmitting}
                  className="px-4 py-2 bg-success-600 hover:bg-success-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Processing...
                    </>
                  ) : (
                    <>
                      <DollarSign className="w-4 h-4" />
                      Confirm Reconciliation
                    </>
                  )}
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
