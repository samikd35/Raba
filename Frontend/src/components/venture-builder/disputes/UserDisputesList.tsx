'use client';

import { useState, useEffect } from 'react';
import { AlertTriangle, Loader2, AlertCircle, Filter, FileText, RefreshCw, Calendar, ChevronRight } from 'lucide-react';
import { getMyDisputes } from '@/lib/api/venture-builder';
import { authService } from '@/services/authService';
import { toast } from 'react-hot-toast';
import DisputeStatusBadge from './DisputeStatusBadge';
import UserDisputeDetail from './UserDisputeDetail';
import type { GetDisputesResponse, Dispute, DisputeStatus } from '@/types/ventureBuilder';

const REASON_LABELS: Record<string, string> = {
  missed_session: 'Missed Session',
  time_theft: 'Time Discrepancy',
  other: 'Other Issue',
};

export default function UserDisputesList() {
  const [disputes, setDisputes] = useState<GetDisputesResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<DisputeStatus | 'all'>('all');
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedDisputeId, setSelectedDisputeId] = useState<string | null>(null);
  const pageSize = 10;

  const loadDisputes = async (page: number = 1, status?: DisputeStatus) => {
    try {
      setIsLoading(true);
      setError(null);

      const token = authService.getCurrentToken();
      if (!token) {
        throw new Error('Authentication required');
      }

      const data = await getMyDisputes(token, {
        status: status,
        page,
        page_size: pageSize,
      });
      setDisputes(data);
    } catch (err: any) {
      console.error('Error fetching disputes:', err);
      setError(err.message || 'Failed to load disputes');
      toast.error(err.message || 'Failed to load disputes');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadDisputes(currentPage, statusFilter !== 'all' ? statusFilter : undefined);
  }, [currentPage, statusFilter]);

  const handleRefresh = () => {
    loadDisputes(currentPage, statusFilter !== 'all' ? statusFilter : undefined);
  };

  if (isLoading && !disputes) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="text-center">
          <Loader2 className="w-10 h-10 animate-spin text-brand-500 dark:text-brand-400 mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-400">Loading your disputes...</p>
        </div>
      </div>
    );
  }

  if (error && !disputes) {
    return (
      <div className="p-6 bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-xl">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-full bg-error-100 dark:bg-error-900/30 flex items-center justify-center flex-shrink-0">
            <AlertCircle className="w-5 h-5 text-error-600 dark:text-error-400" />
          </div>
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-error-900 dark:text-error-200 mb-1">
              Error Loading Disputes
            </h3>
            <p className="text-error-700 dark:text-error-300 text-sm mb-4">{error}</p>
            <button
              onClick={handleRefresh}
              className="px-4 py-2 bg-error-600 text-white rounded-lg hover:bg-error-700 transition-colors flex items-center gap-2 text-sm font-medium"
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
          <h2 className="text-xl font-bold text-gray-900 dark:text-white">
            My Disputes
          </h2>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Track the status of your submitted disputes
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-gray-500 dark:text-gray-400" />
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value as DisputeStatus | 'all');
                setCurrentPage(1);
              }}
              className="px-3 py-2 border border-gray-200 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
            >
              <option value="all">All Status</option>
              <option value="submitted">Submitted</option>
              <option value="under_review">Under Review</option>
              <option value="resolved">Resolved</option>
            </select>
          </div>
          <button
            onClick={handleRefresh}
            disabled={isLoading}
            className="p-2 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
            title="Refresh"
          >
            <RefreshCw className={`w-5 h-5 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Disputes List */}
      {!disputes || disputes.disputes.length === 0 ? (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-12 text-center">
          <div className="w-16 h-16 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-4">
            <FileText className="w-8 h-8 text-gray-400" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            No Disputes Found
          </h3>
          <p className="text-gray-600 dark:text-gray-400 max-w-sm mx-auto">
            {statusFilter !== 'all'
              ? `You have no disputes with status "${statusFilter.replace('_', ' ')}"`
              : "You haven't submitted any disputes yet"}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {disputes.disputes.map((dispute) => (
            <button
              key={dispute.id}
              onClick={() => setSelectedDisputeId(dispute.id)}
              className="w-full bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4 sm:p-5 hover:border-gray-300 dark:hover:border-gray-600 hover:shadow-sm transition-all text-left group"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2 sm:gap-3 mb-2">
                    <DisputeStatusBadge status={dispute.status} />
                    <span className="text-sm text-gray-500 dark:text-gray-400">
                      {REASON_LABELS[dispute.reason] || dispute.reason}
                    </span>
                  </div>

                  {dispute.custom_reason && (
                    <p className="text-sm text-gray-700 dark:text-gray-300 mb-2 line-clamp-1">
                      "{dispute.custom_reason}"
                    </p>
                  )}

                  {dispute.description && (
                    <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2 mb-2">
                      {dispute.description}
                    </p>
                  )}

                  <div className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
                    <Calendar className="w-3.5 h-3.5" />
                    Submitted {new Date(dispute.created_at).toLocaleDateString('en-US', {
                      year: 'numeric',
                      month: 'short',
                      day: 'numeric',
                    })}
                  </div>
                </div>

                <ChevronRight className="w-5 h-5 text-gray-400 group-hover:text-gray-600 dark:group-hover:text-gray-300 transition-colors flex-shrink-0" />
              </div>
            </button>
          ))}
        </div>
      )}

      {/* Pagination */}
      {disputes && disputes.total_pages > 1 && (
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 px-4 py-3">
          <div className="text-sm text-gray-600 dark:text-gray-400">
            Page {disputes.page} of {disputes.total_pages} ({disputes.total_count} total)
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
              disabled={currentPage === 1 || isLoading}
              className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Previous
            </button>
            <button
              onClick={() => setCurrentPage((prev) => Math.min(disputes.total_pages, prev + 1))}
              disabled={currentPage === disputes.total_pages || isLoading}
              className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Next
            </button>
          </div>
        </div>
      )}

      {/* Dispute Detail Modal */}
      <UserDisputeDetail
        disputeId={selectedDisputeId || ''}
        isOpen={!!selectedDisputeId}
        onClose={() => setSelectedDisputeId(null)}
      />
    </div>
  );
}
