"use client";

import React, { useState, useEffect } from 'react';
import { creditRequestService } from '@/lib/api/creditRequestService';
import { useCreditRequestStore } from '@/stores/creditRequestStore';
import { CreditRequest } from '@/types/team';
import { toast } from "react-hot-toast";
import { Clock, CheckCircle, XCircle, Ban, Trash2, Filter } from 'lucide-react';

interface CreditRequestHistoryTableProps {
  teamId: string;
}

export default function CreditRequestHistoryTable({ teamId }: CreditRequestHistoryTableProps) {
  const [isLoading, setIsLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'pending' | 'approved' | 'rejected' | 'cancelled'>('all');
  const { requests, setRequests, removeRequest } = useCreditRequestStore();

  useEffect(() => {
    fetchRequests();
  }, [teamId]);

  const fetchRequests = async () => {
    setIsLoading(true);
    try {
      const data = await creditRequestService.getCreditRequests(teamId);
      setRequests(data);
    } catch (error: any) {
      console.error('Failed to fetch credit requests:', error);
      toast.error('Failed to load credit requests');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancelRequest = async (requestId: string) => {
    if (!confirm('Are you sure you want to cancel this request?')) {
      return;
    }

    try {
      await creditRequestService.cancelCreditRequest(teamId, requestId);
      removeRequest(requestId);
      toast.success('Request cancelled successfully');
    } catch (error: any) {
      console.error('Failed to cancel request:', error);
      toast.error(error.message || 'Failed to cancel request');
    }
  };

  const getStatusBadge = (status: CreditRequest['status']) => {
    const styles = {
      pending: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
      approved: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
      rejected: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
      cancelled: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200',
    };

    const icons = {
      pending: <Clock className="w-3 h-3" />,
      approved: <CheckCircle className="w-3 h-3" />,
      rejected: <XCircle className="w-3 h-3" />,
      cancelled: <Ban className="w-3 h-3" />,
    };

    return (
      <span className={`inline-flex items-center space-x-1 px-2 py-1 rounded-full text-xs font-medium ${styles[status]}`}>
        {icons[status]}
        <span className="capitalize">{status}</span>
      </span>
    );
  };

  const filteredRequests = filter === 'all' 
    ? requests 
    : requests.filter(req => req.status === filter);

  if (isLoading) {
    return (
      <div className="flex justify-center items-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Filter Tabs */}
      <div className="flex items-center space-x-2 border-b border-gray-200 dark:border-gray-700">
        <Filter className="w-4 h-4 text-gray-400" />
        <button
          onClick={() => setFilter('all')}
          className={`px-3 py-2 text-sm font-medium border-b-2 transition-colors ${
            filter === 'all'
              ? 'border-blue-500 text-blue-600 dark:text-blue-400'
              : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
          }`}
        >
          All ({requests.length})
        </button>
        <button
          onClick={() => setFilter('pending')}
          className={`px-3 py-2 text-sm font-medium border-b-2 transition-colors ${
            filter === 'pending'
              ? 'border-blue-500 text-blue-600 dark:text-blue-400'
              : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
          }`}
        >
          Pending ({requests.filter(r => r.status === 'pending').length})
        </button>
        <button
          onClick={() => setFilter('approved')}
          className={`px-3 py-2 text-sm font-medium border-b-2 transition-colors ${
            filter === 'approved'
              ? 'border-blue-500 text-blue-600 dark:text-blue-400'
              : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
          }`}
        >
          Approved ({requests.filter(r => r.status === 'approved').length})
        </button>
        <button
          onClick={() => setFilter('rejected')}
          className={`px-3 py-2 text-sm font-medium border-b-2 transition-colors ${
            filter === 'rejected'
              ? 'border-blue-500 text-blue-600 dark:text-blue-400'
              : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
          }`}
        >
          Rejected ({requests.filter(r => r.status === 'rejected').length})
        </button>
      </div>

      {/* Table */}
      {filteredRequests.length === 0 ? (
        <div className="text-center py-12">
          <Clock className="w-12 h-12 text-gray-400 mx-auto mb-3" />
          <p className="text-gray-500 dark:text-gray-400">
            {filter === 'all' ? 'No credit requests yet' : `No ${filter} requests`}
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700">
                <th className="text-left py-3 px-4 text-sm font-medium text-gray-700 dark:text-gray-300">
                  Request ID
                </th>
                <th className="text-left py-3 px-4 text-sm font-medium text-gray-700 dark:text-gray-300">
                  Credits
                </th>
                <th className="text-left py-3 px-4 text-sm font-medium text-gray-700 dark:text-gray-300">
                  Reason
                </th>
                <th className="text-left py-3 px-4 text-sm font-medium text-gray-700 dark:text-gray-300">
                  Status
                </th>
                <th className="text-left py-3 px-4 text-sm font-medium text-gray-700 dark:text-gray-300">
                  Submitted
                </th>
                <th className="text-left py-3 px-4 text-sm font-medium text-gray-700 dark:text-gray-300">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {filteredRequests.map((request) => (
                <tr
                  key={request.request_id}
                  className="border-b border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50"
                >
                  <td className="py-3 px-4">
                    <span className="text-sm font-mono text-gray-600 dark:text-gray-400">
                      {request.request_id.slice(0, 8)}...
                    </span>
                  </td>
                  <td className="py-3 px-4">
                    <div className="text-sm">
                      <div className="font-medium text-gray-900 dark:text-white">
                        {request.requested_credits.toLocaleString()}
                      </div>
                      {request.status === 'approved' && request.credits_allocated && (
                        <div className="text-xs text-green-600 dark:text-green-400">
                          Allocated: {request.credits_allocated.toLocaleString()}
                        </div>
                      )}
                    </div>
                  </td>
                  <td className="py-3 px-4">
                    <div className="text-sm text-gray-600 dark:text-gray-400 max-w-xs truncate">
                      {request.reason || '—'}
                    </div>
                  </td>
                  <td className="py-3 px-4">
                    {getStatusBadge(request.status)}
                  </td>
                  <td className="py-3 px-4">
                    <div className="text-sm text-gray-600 dark:text-gray-400">
                      {new Date(request.created_at).toLocaleDateString()}
                    </div>
                    {request.reviewed_at && (
                      <div className="text-xs text-gray-500 dark:text-gray-500">
                        Reviewed: {new Date(request.reviewed_at).toLocaleDateString()}
                      </div>
                    )}
                  </td>
                  <td className="py-3 px-4">
                    {request.status === 'pending' && (
                      <button
                        onClick={() => handleCancelRequest(request.request_id)}
                        className="text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 p-1"
                        title="Cancel request"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                    {request.status !== 'pending' && request.review_notes && (
                      <button
                        onClick={() => alert(request.review_notes)}
                        className="text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 text-xs"
                      >
                        View Notes
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
