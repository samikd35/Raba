'use client';

import React, { useEffect, useState } from 'react';
import { DollarSign, TrendingUp, Calendar, Loader2, AlertCircle, Filter, AlertTriangle } from 'lucide-react';
import { getMyEarnings } from '@/lib/api/venture-builder';
import { authService } from '@/services/authService';
import { toast } from 'react-hot-toast';
import type { EarningsResponse } from '@/types/ventureBuilder';
import UserDisputesList from '../disputes/UserDisputesList';

type ViewMode = 'earnings' | 'disputes';

export default function VBEarningsDashboard() {
  const [viewMode, setViewMode] = useState<ViewMode>('earnings');
  const [earnings, setEarnings] = useState<EarningsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  const loadEarnings = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const token = authService.getCurrentToken();
      if (!token) {
        throw new Error('Authentication required');
      }

      // Check if user is a VB
      const currentUser = authService.getCurrentUser();
      console.log('Current user:', currentUser);

      if (!currentUser?.roles?.includes('venture_builder') && !currentUser?.roles?.includes('admin')) {
        throw new Error('You must be a Venture Builder to view earnings. Current roles: ' + (currentUser?.roles?.join(', ') || 'none'));
      }

      const data = await getMyEarnings(token, {
        start_date: startDate || undefined,
        end_date: endDate || undefined,
      });
      setEarnings(data);
    } catch (error: any) {
      console.error('Error fetching earnings:', error);
      setError(error.message || 'Failed to load earnings');
      toast.error(error.message || 'Failed to load earnings');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadEarnings();
  }, []);

  const handleFilterApply = () => {
    loadEarnings();
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-brand-500 dark:text-brand-400 mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-400">Loading earnings...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-4">
        <div className="p-6 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-6 h-6 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-red-900 dark:text-red-200 mb-2">
                Error Loading Earnings
              </h3>
              <p className="text-red-700 dark:text-red-300 mb-3">{error}</p>

              {error.includes('500') && (
                <div className="mt-4 p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-700 rounded text-sm">
                  <p className="text-yellow-800 dark:text-yellow-300 font-medium mb-1">
                    💡 This appears to be a server error
                  </p>
                  <p className="text-yellow-700 dark:text-yellow-400">
                    The backend API is experiencing issues. This could happen if:
                  </p>
                  <ul className="list-disc ml-5 mt-2 text-yellow-700 dark:text-yellow-400 space-y-1">
                    <li>You're a new Venture Builder with no sessions yet</li>
                    <li>The earnings database table hasn't been initialized</li>
                    <li>Your VB profile needs to be fully approved by admin</li>
                  </ul>
                </div>
              )}

              <button
                onClick={loadEarnings}
                className="mt-4 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium transition-colors"
              >
                Try Again
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!earnings) return null;

  return (
    <div className="space-y-6">
      {/* Header with Toggle */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
            {viewMode === 'earnings' ? 'My Earnings' : 'My Disputes'}
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            {viewMode === 'earnings'
              ? 'Track your coaching earnings and payment history'
              : 'Track the status of your submitted disputes'}
          </p>
        </div>

        {/* View Toggle */}
        <div className="flex items-center p-1 bg-gray-100 dark:bg-gray-800 rounded-lg">
          <button
            onClick={() => setViewMode('earnings')}
            className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-md transition-all ${
              viewMode === 'earnings'
                ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
            }`}
          >
            <DollarSign className="w-4 h-4" />
            Earnings
          </button>
          <button
            onClick={() => setViewMode('disputes')}
            className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-md transition-all ${
              viewMode === 'disputes'
                ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
            }`}
          >
            <AlertTriangle className="w-4 h-4" />
            Disputes
          </button>
        </div>
      </div>

      {/* Disputes View */}
      {viewMode === 'disputes' ? (
        <UserDisputesList />
      ) : (
        <>
          {/* Date Range Filter */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-gray-500 dark:text-gray-400" />
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Filter by Date:</span>
          </div>
          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-600 dark:text-gray-400">From:</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="px-3 py-1.5 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>
          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-600 dark:text-gray-400">To:</label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="px-3 py-1.5 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>
          <button
            onClick={handleFilterApply}
            className="px-4 py-1.5 bg-brand-500 hover:bg-brand-600 text-white rounded-lg text-sm font-medium transition-colors"
          >
            Apply Filter
          </button>
          {(startDate || endDate) && (
            <button
              onClick={() => {
                setStartDate('');
                setEndDate('');
                loadEarnings();
              }}
              className="px-4 py-1.5 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg text-sm font-medium transition-colors"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Earned Credits */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
              <TrendingUp className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            </div>
            <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400">
              Total Credits Earned
            </h3>
          </div>
          <p className="text-2xl font-bold text-gray-900 dark:text-white">
            {earnings.total_earned_credits.toLocaleString()}
          </p>
        </div>

        {/* Gross Earnings */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-green-100 dark:bg-green-900/30 rounded-lg">
              <DollarSign className="w-5 h-5 text-green-600 dark:text-green-400" />
            </div>
            <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400">
              Gross Earnings
            </h3>
          </div>
          <p className="text-2xl font-bold text-gray-900 dark:text-white">
            ${earnings.total_earnings_usd.toFixed(2)}
          </p>
        </div>

        {/* Commission */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-orange-100 dark:bg-orange-900/30 rounded-lg">
              <DollarSign className="w-5 h-5 text-orange-600 dark:text-orange-400" />
            </div>
            <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400">
              Platform Commission
            </h3>
          </div>
          <p className="text-2xl font-bold text-orange-600 dark:text-orange-400">
            -${earnings.commission_amount_usd.toFixed(2)}
          </p>
        </div>

        {/* Net Earnings */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
              <DollarSign className="w-5 h-5 text-purple-600 dark:text-purple-400" />
            </div>
            <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400">
              Net Earnings
            </h3>
          </div>
          <p className="text-2xl font-bold text-purple-600 dark:text-purple-400">
            ${earnings.net_earnings_usd.toFixed(2)}
          </p>
        </div>
      </div>

      {/* Payment Status */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-2">
            Total Reconciled
          </h3>
          <p className="text-xl font-bold text-green-600 dark:text-green-400">
            ${earnings.total_reconciled_payments.toFixed(2)}
          </p>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-2">
            Pending Payment
          </h3>
          <p className="text-xl font-bold text-yellow-600 dark:text-yellow-400">
            ${earnings.pending_amount_usd.toFixed(2)}
          </p>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-2">
            Completed Sessions
          </h3>
          <p className="text-xl font-bold text-gray-900 dark:text-white">
            {earnings.completed_sessions_period} / {earnings.total_sessions_all_time}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            Period / All Time
          </p>
        </div>
      </div>

      {/* Session Breakdown */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            Session Earnings Breakdown
          </h2>
        </div>
        <div className="overflow-x-auto">
          {earnings.sessions.length === 0 ? (
            <div className="p-12 text-center">
              <p className="text-gray-600 dark:text-gray-400">
                No completed sessions in this period
              </p>
            </div>
          ) : (
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
                  <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700 dark:text-gray-300">
                    Date
                  </th>
                  <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700 dark:text-gray-300">
                    Credits
                  </th>
                  <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700 dark:text-gray-300">
                    Gross
                  </th>
                  <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700 dark:text-gray-300">
                    Commission
                  </th>
                  <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700 dark:text-gray-300">
                    Net
                  </th>
                  <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700 dark:text-gray-300">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody>
                {earnings.sessions.map((session) => (
                  <tr
                    key={session.id}
                    className="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
                  >
                    <td className="py-4 px-4">
                      <div className="flex items-center gap-2 text-sm">
                        <Calendar className="w-4 h-4 text-gray-400" />
                        <span className="text-gray-900 dark:text-white">
                          {new Date(session.session_datetime).toLocaleDateString('en-US', {
                            month: 'short',
                            day: 'numeric',
                            year: 'numeric',
                          })}
                        </span>
                      </div>
                    </td>
                    <td className="py-4 px-4 text-sm text-gray-900 dark:text-white">
                      {session.credits_charged}
                    </td>
                    <td className="py-4 px-4 text-sm font-semibold text-gray-900 dark:text-white">
                      ${session.earnings_usd.toFixed(2)}
                    </td>
                    <td className="py-4 px-4 text-sm text-orange-600 dark:text-orange-400">
                      -${session.commission_usd.toFixed(2)}
                    </td>
                    <td className="py-4 px-4 text-sm font-semibold text-green-600 dark:text-green-400">
                      ${session.net_earnings_usd.toFixed(2)}
                    </td>
                    <td className="py-4 px-4">
                      <span className={`px-3 py-1 text-xs font-medium rounded-full ${
                        session.status === 'settled'
                          ? 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300'
                          : 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300'
                      }`}>
                        {session.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Date Range Info */}
          {(earnings.date_range_start || earnings.date_range_end) && (
            <div className="text-sm text-gray-500 dark:text-gray-400 text-center">
              Showing data from {earnings.date_range_start || 'beginning'} to {earnings.date_range_end || 'present'}
            </div>
          )}
        </>
      )}
    </div>
  );
}
