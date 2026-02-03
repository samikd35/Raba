'use client';

import { useState, useEffect } from 'react';
import { DollarSign, Loader2, AlertCircle, RefreshCw, Calendar, FileText, User } from 'lucide-react';
import { getVBReconciliationHistory } from '@/lib/api/venture-builder';
import { authService } from '@/services/authService';
import { toast } from 'react-hot-toast';
import ReconcileConfirmModal from './ReconcileConfirmModal';
import type { ReconciliationHistoryResponse, ReconcileResponse } from '@/types/ventureBuilder';

interface VBReconciliationActionsProps {
  vbId: string;
  vbName: string;
}

export default function VBReconciliationActions({ vbId, vbName }: VBReconciliationActionsProps) {
  const [history, setHistory] = useState<ReconciliationHistoryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [isReconcileModalOpen, setIsReconcileModalOpen] = useState(false);
  const pageSize = 10;

  const loadHistory = async (page: number = 1) => {
    try {
      setIsLoading(true);
      setError(null);

      const token = authService.getCurrentToken();
      if (!token) {
        throw new Error('Authentication required');
      }

      const data = await getVBReconciliationHistory(vbId, token, page, pageSize);
      setHistory(data);
    } catch (err: any) {
      console.error('Error fetching reconciliation history:', err);
      setError(err.message || 'Failed to load reconciliation history');
      toast.error(err.message || 'Failed to load reconciliation history');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadHistory(currentPage);
  }, [currentPage, vbId]);

  const handleReconcileSuccess = (result: ReconcileResponse) => {
    // Refresh history after successful reconciliation
    loadHistory(1);
    setCurrentPage(1);
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (isLoading && !history) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-brand-500 dark:text-brand-400 mx-auto mb-3" />
          <p className="text-sm text-gray-600 dark:text-gray-400">Loading reconciliation history...</p>
        </div>
      </div>
    );
  }

  if (error && !history) {
    return (
      <div className="p-4 bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg">
        <div className="flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-error-600 dark:text-error-400 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <h4 className="text-sm font-semibold text-error-900 dark:text-error-200 mb-1">
              Error Loading History
            </h4>
            <p className="text-sm text-error-700 dark:text-error-300 mb-3">{error}</p>
            <button
              onClick={() => loadHistory(currentPage)}
              className="px-3 py-1.5 bg-error-600 text-white rounded-lg hover:bg-error-700 transition-colors flex items-center gap-2 text-sm font-medium"
            >
              <RefreshCw className="w-4 h-4" />
              Try Again
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header with Reconcile Button */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <DollarSign className="w-5 h-5 text-success-600 dark:text-success-400" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Payment Reconciliation
          </h3>
        </div>
        <button
          onClick={() => setIsReconcileModalOpen(true)}
          className="px-4 py-2 bg-success-600 hover:bg-success-700 text-white rounded-lg font-medium transition-colors flex items-center gap-2 text-sm"
        >
          <DollarSign className="w-4 h-4" />
          Reconcile Payments
        </button>
      </div>

      {/* History Table */}
      {!history || history.reconciliations.length === 0 ? (
        <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700 p-8 text-center">
          <div className="w-12 h-12 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-3">
            <FileText className="w-6 h-6 text-gray-400" />
          </div>
          <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-1">
            No Reconciliation History
          </h4>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            No payments have been reconciled for this venture builder yet.
          </p>
        </div>
      ) : (
        <>
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-gray-50 dark:bg-gray-900/50 border-b border-gray-200 dark:border-gray-700">
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">
                      Date
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">
                      Amount
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">
                      Sessions
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">
                      Reconciled By
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">
                      Notes
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                  {history.reconciliations.map((record) => (
                    <tr key={record.id} className="hover:bg-gray-50 dark:hover:bg-gray-900/30 transition-colors">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2 text-sm text-gray-900 dark:text-white">
                          <Calendar className="w-4 h-4 text-gray-400" />
                          {formatDate(record.created_at)}
                        </div>
                        {(record.start_date || record.end_date) && (
                          <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                            Range: {record.start_date ? formatDate(record.start_date).split(',')[0] : 'Start'} - {record.end_date ? formatDate(record.end_date).split(',')[0] : 'End'}
                          </div>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-sm font-semibold text-success-600 dark:text-success-400">
                          {formatCurrency(record.amount_reconciled_usd)}
                        </span>
                        <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                          Pending before: {formatCurrency(record.pending_amount_before)}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-sm text-gray-900 dark:text-white font-medium">
                          {record.session_count}
                        </span>
                        <span className="text-sm text-gray-500 dark:text-gray-400 ml-1">
                          sessions
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <div className="w-6 h-6 bg-brand-100 dark:bg-brand-900/30 rounded-full flex items-center justify-center">
                            <User className="w-3 h-3 text-brand-600 dark:text-brand-400" />
                          </div>
                          <div>
                            <p className="text-sm text-gray-900 dark:text-white">
                              {record.reconciled_by_name || 'Admin'}
                            </p>
                            {record.reconciled_by_email && (
                              <p className="text-xs text-gray-500 dark:text-gray-400">
                                {record.reconciled_by_email}
                              </p>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        {record.notes ? (
                          <p className="text-sm text-gray-600 dark:text-gray-400 max-w-xs truncate" title={record.notes}>
                            {record.notes}
                          </p>
                        ) : (
                          <span className="text-sm text-gray-400 dark:text-gray-500 italic">
                            No notes
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Pagination */}
          {history.total_pages > 1 && (
            <div className="flex items-center justify-between bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 px-4 py-3">
              <div className="text-sm text-gray-600 dark:text-gray-400">
                Page {history.page} of {history.total_pages} ({history.total_count} total)
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
                  disabled={currentPage === 1 || isLoading}
                  className="px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  Previous
                </button>
                <button
                  onClick={() => setCurrentPage((prev) => Math.min(history.total_pages, prev + 1))}
                  disabled={currentPage === history.total_pages || isLoading}
                  className="px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </>
      )}

      {/* Reconcile Modal */}
      <ReconcileConfirmModal
        vbId={vbId}
        vbName={vbName}
        isOpen={isReconcileModalOpen}
        onClose={() => setIsReconcileModalOpen(false)}
        onSuccess={handleReconcileSuccess}
      />
    </div>
  );
}
