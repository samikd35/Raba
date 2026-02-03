'use client';

import React, { useEffect, useState } from 'react';
import { AlertTriangle, CheckCircle, Clock, Loader2, AlertCircle as ErrorIcon, Filter, FileText, RefreshCw } from 'lucide-react';
import { getAllDisputes, updateDispute } from '@/lib/api/venture-builder';
import { authService } from '@/services/authService';
import { toast } from 'react-hot-toast';
import type { GetDisputesResponse, Dispute, DisputeStatus } from '@/types/ventureBuilder';

export default function VBDisputesPanel() {
  const [disputes, setDisputes] = useState<GetDisputesResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<DisputeStatus | 'all'>('all');
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 20;

  const loadDisputes = async (page: number = 1, status?: DisputeStatus) => {
    try {
      setIsLoading(true);
      setError(null);
      const token = authService.getCurrentToken();
      if (!token) {
        throw new Error('Authentication required');
      }

      const data = await getAllDisputes(token, {
        status: status !== 'all' ? status : undefined,
        page,
        page_size: pageSize,
      });
      setDisputes(data);
    } catch (error: any) {
      console.error('Error fetching disputes:', error);
      setError(error.message || 'Failed to load disputes');
      toast.error(error.message || 'Failed to load disputes');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadDisputes(currentPage, statusFilter !== 'all' ? statusFilter : undefined);
  }, [currentPage, statusFilter]);

  const handleStatusUpdate = async (disputeId: string, newStatus: DisputeStatus, adminNotes?: string) => {
    try {
      const token = authService.getCurrentToken();
      if (!token) {
        throw new Error('Authentication required');
      }

      await updateDispute(disputeId, { status: newStatus, admin_notes: adminNotes }, token);
      toast.success('Dispute status updated successfully!');
      loadDisputes(currentPage, statusFilter !== 'all' ? statusFilter : undefined);
    } catch (error: any) {
      console.error('Error updating dispute:', error);
      toast.error(error.message || 'Failed to update dispute');
    }
  };

  const getStatusBadge = (status: DisputeStatus) => {
    const config: Record<DisputeStatus, { label: string; className: string; icon: any }> = {
      submitted: {
        label: 'Submitted',
        className: 'bg-warning-100 dark:bg-warning-900/30 text-warning-700 dark:text-warning-300 border-warning-200 dark:border-warning-700',
        icon: AlertTriangle,
      },
      under_review: {
        label: 'Under Review',
        className: 'bg-brand-100 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300 border-brand-200 dark:border-brand-700',
        icon: Clock,
      },
      resolved: {
        label: 'Resolved',
        className: 'bg-success-100 dark:bg-success-900/30 text-success-700 dark:text-success-300 border-success-200 dark:border-success-700',
        icon: CheckCircle,
      },
    };

    const statusConfig = config[status];
    const Icon = statusConfig.icon;

    return (
      <span className={`inline-flex items-center gap-1 px-2 sm:px-3 py-1 text-xs font-medium rounded-full border ${statusConfig.className}`}>
        <Icon className="w-3 h-3" />
        {statusConfig.label}
      </span>
    );
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-brand-500 dark:text-brand-400 mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-400">Loading disputes...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 sm:p-6 bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-xl">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-full bg-error-100 dark:bg-error-900/30 flex items-center justify-center flex-shrink-0">
            <ErrorIcon className="w-5 h-5 text-error-600 dark:text-error-400" />
          </div>
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-error-900 dark:text-error-200 mb-1">
              Error Loading Disputes
            </h3>
            <p className="text-error-700 dark:text-error-300 text-sm mb-4">{error}</p>
            <button
              onClick={() => loadDisputes(currentPage, statusFilter !== 'all' ? statusFilter : undefined)}
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
            Session Disputes
          </h2>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Review and resolve user disputes
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-gray-500 dark:text-gray-400 hidden sm:block" />
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value as DisputeStatus | 'all');
                setCurrentPage(1);
              }}
              className="px-3 sm:px-4 py-2 border border-gray-200 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400 focus:border-transparent transition-all"
            >
              <option value="all">All Status</option>
              <option value="submitted">Submitted</option>
              <option value="under_review">Under Review</option>
              <option value="resolved">Resolved</option>
            </select>
          </div>
          <div className="flex items-center gap-2 px-3 sm:px-4 py-2 bg-warning-100 dark:bg-warning-900/30 border border-warning-200 dark:border-warning-700 rounded-lg">
            <AlertTriangle className="w-4 h-4 sm:w-5 sm:h-5 text-warning-600 dark:text-warning-400" />
            <span className="text-xs sm:text-sm font-semibold text-warning-700 dark:text-warning-300">
              {disputes?.total_count || 0} Total
            </span>
          </div>
        </div>
      </div>

      {/* Disputes List */}
      <div className="space-y-4">
        {!disputes || disputes.disputes.length === 0 ? (
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-8 sm:p-12 text-center shadow-theme-xs">
            <div className="w-16 h-16 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-4">
              <FileText className="w-8 h-8 text-gray-400" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
              No Disputes Found
            </h3>
            <p className="text-gray-600 dark:text-gray-400 max-w-sm mx-auto">
              {statusFilter !== 'all'
                ? `No disputes with status "${statusFilter.replace('_', ' ')}"`
                : 'No disputes have been submitted yet'}
            </p>
          </div>
        ) : (
          disputes.disputes.map((dispute) => (
            <div
              key={dispute.id}
              className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-theme-xs overflow-hidden"
            >
              <div className="p-4 sm:p-6">
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 mb-4">
                  <div className="flex-1">
                    <div className="flex flex-wrap items-center gap-2 sm:gap-3 mb-2">
                      {getStatusBadge(dispute.status)}
                      <span className="text-xs sm:text-sm text-gray-500 dark:text-gray-400 font-mono">
                        Session: {dispute.session_id.substring(0, 8)}...
                      </span>
                    </div>
                    <p className="text-xs sm:text-sm text-gray-600 dark:text-gray-400">
                      Created: {new Date(dispute.created_at).toLocaleString('en-US', {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </p>
                  </div>
                </div>

                <div className="space-y-3">
                  <div>
                    <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1">
                      Reason: <span className="capitalize">{dispute.reason.replace('_', ' ')}</span>
                    </h4>
                    {dispute.custom_reason && (
                      <p className="text-sm text-gray-600 dark:text-gray-400 italic">
                        {dispute.custom_reason}
                      </p>
                    )}
                  </div>

                  <div>
                    <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1">
                      Description:
                    </h4>
                    <p className="text-sm text-gray-900 dark:text-white">
                      {dispute.description}
                    </p>
                  </div>

                  {dispute.admin_notes && (
                    <div className="p-3 bg-brand-50 dark:bg-brand-900/20 border border-brand-200 dark:border-brand-700 rounded-lg">
                      <h4 className="text-sm font-semibold text-brand-900 dark:text-brand-200 mb-1">
                        Admin Notes:
                      </h4>
                      <p className="text-sm text-brand-800 dark:text-brand-300">
                        {dispute.admin_notes}
                      </p>
                    </div>
                  )}

                  {dispute.status !== 'resolved' && (
                    <div className="flex flex-col sm:flex-row gap-2 pt-3 border-t border-gray-200 dark:border-gray-700">
                      <button
                        onClick={() => handleStatusUpdate(dispute.id, 'under_review', 'Under investigation')}
                        className="flex-1 sm:flex-none flex items-center justify-center gap-2 px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white text-sm rounded-lg transition-all shadow-theme-sm font-medium"
                      >
                        <Clock className="w-4 h-4" />
                        Mark Under Review
                      </button>
                      <button
                        onClick={() => handleStatusUpdate(dispute.id, 'resolved', 'Dispute resolved')}
                        className="flex-1 sm:flex-none flex items-center justify-center gap-2 px-4 py-2 bg-success-500 hover:bg-success-600 text-white text-sm rounded-lg transition-all shadow-theme-sm font-medium"
                      >
                        <CheckCircle className="w-4 h-4" />
                        Mark Resolved
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Pagination */}
      {disputes && disputes.total_pages > 1 && (
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 px-4 sm:px-6 py-4 shadow-theme-xs">
          <div className="text-sm text-gray-600 dark:text-gray-400">
            Page {disputes.page} of {disputes.total_pages}
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
              onClick={() => setCurrentPage((prev) => Math.min(disputes.total_pages, prev + 1))}
              disabled={currentPage === disputes.total_pages}
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
