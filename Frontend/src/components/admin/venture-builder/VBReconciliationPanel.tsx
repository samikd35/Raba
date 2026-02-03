'use client';

import React, { useEffect, useState } from 'react';
import { DollarSign, Calendar, Loader2, AlertCircle, History, FileText, RefreshCw, User, ChevronRight } from 'lucide-react';
import { getAllReconciliations } from '@/lib/api/venture-builder';
import { authService } from '@/services/authService';
import { toast } from 'react-hot-toast';
import type { ReconciliationHistoryResponse } from '@/types/ventureBuilder';

export default function VBReconciliationPanel() {
  const [reconciliations, setReconciliations] = useState<ReconciliationHistoryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 20;

  const loadReconciliations = async (page: number = 1) => {
    try {
      setIsLoading(true);
      setError(null);
      const token = authService.getCurrentToken();
      if (!token) {
        throw new Error('Authentication required');
      }

      const data = await getAllReconciliations(token, page, pageSize);
      setReconciliations(data);
    } catch (error: any) {
      console.error('Error fetching reconciliations:', error);
      setError(error.message || 'Failed to load reconciliations');
      toast.error(error.message || 'Failed to load reconciliations');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadReconciliations(currentPage);
  }, [currentPage]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-brand-500 dark:text-brand-400 mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-400">Loading reconciliations...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 sm:p-6 bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-xl">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-full bg-error-100 dark:bg-error-900/30 flex items-center justify-center flex-shrink-0">
            <AlertCircle className="w-5 h-5 text-error-600 dark:text-error-400" />
          </div>
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-error-900 dark:text-error-200 mb-1">
              Error Loading Reconciliations
            </h3>
            <p className="text-error-700 dark:text-error-300 text-sm mb-4">{error}</p>
            <button
              onClick={() => loadReconciliations(currentPage)}
              className="px-4 py-2 bg-error-600 dark:bg-error-500 text-white rounded-lg hover:bg-error-700 dark:hover:bg-error-600 transition-all flex items-center gap-2 text-sm font-medium"
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
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white">
            Payment Reconciliations
          </h2>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            View all payment reconciliation records
          </p>
        </div>
        <div className="flex items-center gap-2 px-3 sm:px-4 py-2 bg-brand-100 dark:bg-brand-900/30 border border-brand-200 dark:border-brand-700 rounded-lg">
          <History className="w-4 h-4 sm:w-5 sm:h-5 text-brand-600 dark:text-brand-400" />
          <span className="text-xs sm:text-sm font-semibold text-brand-700 dark:text-brand-300">
            {reconciliations?.total_count || 0} Total Records
          </span>
        </div>
      </div>

      {/* Empty State */}
      {!reconciliations || reconciliations.reconciliations.length === 0 ? (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-8 sm:p-12 text-center shadow-theme-xs">
          <div className="w-16 h-16 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-4">
            <FileText className="w-8 h-8 text-gray-400" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            No Reconciliations Found
          </h3>
          <p className="text-gray-600 dark:text-gray-400 max-w-sm mx-auto">
            No payment reconciliations have been processed yet
          </p>
        </div>
      ) : (
        <>
          {/* Mobile Card View */}
          <div className="block lg:hidden space-y-3">
            {reconciliations.reconciliations.map((record) => (
              <div
                key={record.id}
                className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-theme-xs overflow-hidden"
              >
                <div className="p-4">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded-lg bg-success-100 dark:bg-success-900/30 flex items-center justify-center">
                        <DollarSign className="w-4 h-4 text-success-600 dark:text-success-400" />
                      </div>
                      <span className="text-lg font-bold text-success-600 dark:text-success-400">
                        ${record.amount_reconciled_usd.toFixed(2)}
                      </span>
                    </div>
                    <span className="text-xs text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded">
                      {record.session_count} sessions
                    </span>
                  </div>

                  <div className="space-y-2 text-sm">
                    <div className="flex items-center gap-2 text-gray-600 dark:text-gray-400">
                      <Calendar className="w-4 h-4 flex-shrink-0" />
                      <span>
                        {new Date(record.created_at).toLocaleDateString('en-US', {
                          year: 'numeric',
                          month: 'short',
                          day: 'numeric',
                        })}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-gray-600 dark:text-gray-400">
                      <User className="w-4 h-4 flex-shrink-0" />
                      <span className="truncate">{record.reconciled_by_name || 'Unknown'}</span>
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400 font-mono">
                      VB: {record.venture_builder_id.substring(0, 8)}...
                    </div>
                    {record.notes && (
                      <p className="text-xs text-gray-500 dark:text-gray-400 pt-2 border-t border-gray-100 dark:border-gray-700">
                        {record.notes}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Desktop Table View */}
          <div className="hidden lg:block bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-theme-xs overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
                    <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700 dark:text-gray-300">
                      Date
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700 dark:text-gray-300">
                      VB ID
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700 dark:text-gray-300">
                      Amount Reconciled
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700 dark:text-gray-300">
                      Sessions
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700 dark:text-gray-300">
                      Reconciled By
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700 dark:text-gray-300">
                      Notes
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {reconciliations.reconciliations.map((record) => (
                    <tr
                      key={record.id}
                      className="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
                    >
                      <td className="py-4 px-4">
                        <div className="flex items-center gap-2 text-sm">
                          <Calendar className="w-4 h-4 text-gray-400" />
                          <span className="text-gray-900 dark:text-white">
                            {new Date(record.created_at).toLocaleDateString('en-US', {
                              year: 'numeric',
                              month: 'short',
                              day: 'numeric',
                            })}
                          </span>
                        </div>
                      </td>
                      <td className="py-4 px-4">
                        <span className="text-sm font-mono text-gray-600 dark:text-gray-400">
                          {record.venture_builder_id.substring(0, 8)}...
                        </span>
                      </td>
                      <td className="py-4 px-4">
                        <div className="flex items-center gap-1">
                          <DollarSign className="w-4 h-4 text-success-500" />
                          <span className="text-sm font-semibold text-success-600 dark:text-success-400">
                            ${record.amount_reconciled_usd.toFixed(2)}
                          </span>
                        </div>
                      </td>
                      <td className="py-4 px-4">
                        <span className="text-sm text-gray-900 dark:text-white">
                          {record.session_count} sessions
                        </span>
                      </td>
                      <td className="py-4 px-4">
                        <div className="text-sm">
                          <div className="text-gray-900 dark:text-white">
                            {record.reconciled_by_name || 'Unknown'}
                          </div>
                          {record.reconciled_by_email && (
                            <div className="text-gray-500 dark:text-gray-400 text-xs">
                              {record.reconciled_by_email}
                            </div>
                          )}
                        </div>
                      </td>
                      <td className="py-4 px-4">
                        <span className="text-sm text-gray-600 dark:text-gray-400">
                          {record.notes || '-'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {/* Pagination */}
      {reconciliations && reconciliations.total_pages > 1 && (
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 px-4 sm:px-6 py-4 shadow-theme-xs">
          <div className="text-sm text-gray-600 dark:text-gray-400">
            Page {reconciliations.page} of {reconciliations.total_pages}
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
              disabled={currentPage === 1}
              className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              Previous
            </button>
            <button
              onClick={() => setCurrentPage((prev) => Math.min(reconciliations.total_pages, prev + 1))}
              disabled={currentPage === reconciliations.total_pages}
              className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
