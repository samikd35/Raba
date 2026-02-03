"use client";

import React, { useState, useEffect } from 'react';
import { tokenMonitoringService, ModelUsageMetrics } from '@/lib/api/tokenMonitoringService';
import { DateRangePicker } from '@/components/token-manager/DateRangePicker';
import { LoadingState } from '@/components/token-manager/LoadingState';
import { EmptyState } from '@/components/token-manager/EmptyState';
import { ArrowUpDown, AlertTriangle, Server } from 'lucide-react';
import { toast } from 'react-hot-toast';
import Link from 'next/link';

type SortField = 'total_calls' | 'total_tokens' | 'total_cost' | 'error_rate';
type SortDirection = 'asc' | 'desc';

export default function ModelsPage() {
  const [models, setModels] = useState<ModelUsageMetrics[]>([]);
  const [loading, setLoading] = useState(true);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [sortField, setSortField] = useState<SortField>('total_cost');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

  useEffect(() => {
    // Set default date range (last 30 days)
    const end = new Date();
    const start = new Date();
    start.setDate(start.getDate() - 30);
    
    setStartDate(start.toISOString().split('T')[0]);
    setEndDate(end.toISOString().split('T')[0]);
  }, []);

  useEffect(() => {
    if (startDate && endDate) {
      fetchModels();
    }
  }, [startDate, endDate]);

  const fetchModels = async () => {
    try {
      setLoading(true);
      const response = await tokenMonitoringService.getModelAnalytics({
        start_date: startDate,
        end_date: endDate,
      });
      setModels(response);
    } catch (error: any) {
      console.error('Failed to fetch models:', error);
      toast.error(error.message || 'Failed to load model analytics');
    } finally {
      setLoading(false);
    }
  };

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const sortedModels = [...models].sort((a, b) => {
    let aValue: number, bValue: number;
    
    switch (sortField) {
      case 'total_calls':
        aValue = a.total_calls;
        bValue = b.total_calls;
        break;
      case 'total_tokens':
        aValue = a.total_tokens;
        bValue = b.total_tokens;
        break;
      case 'total_cost':
        aValue = parseFloat(a.total_cost);
        bValue = parseFloat(b.total_cost);
        break;
      case 'error_rate':
        aValue = a.error_rate || 0;
        bValue = b.error_rate || 0;
        break;
      default:
        return 0;
    }
    
    return sortDirection === 'asc' ? aValue - bValue : bValue - aValue;
  });

  const formatNumber = (num: number | undefined): string => {
    if (!num || isNaN(num)) return '0';
    if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
    if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`;
    return num.toLocaleString();
  };

  const formatCost = (cost: string | undefined): string => {
    if (!cost) return '$0.00';
    const numCost = parseFloat(cost);
    if (isNaN(numCost)) return '$0.00';
    if (numCost >= 1000) return `$${(numCost / 1000).toFixed(2)}K`;
    return `$${numCost.toFixed(2)}`;
  };

  const getErrorRateColor = (errorRate: number): string => {
    if (errorRate >= 10) return 'text-red-600 dark:text-red-400';
    if (errorRate >= 5) return 'text-amber-600 dark:text-amber-400';
    return 'text-gray-900 dark:text-white';
  };

  if (loading) {
    return <LoadingState />;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Model Analytics
          </h1>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
            AI usage metrics grouped by model
          </p>
        </div>
        <DateRangePicker
          startDate={startDate}
          endDate={endDate}
          onStartDateChange={setStartDate}
          onEndDateChange={setEndDate}
        />
      </div>

      {/* Table */}
      {sortedModels.length === 0 ? (
        <EmptyState
          title="No model data"
          message="There are no models with AI usage in the selected date range."
          action={{
            label: 'Refresh',
            onClick: fetchModels,
          }}
        />
      ) : (
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Provider
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Model
                  </th>
                  <th
                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:text-gray-700 dark:hover:text-gray-200"
                    onClick={() => handleSort('total_calls')}
                  >
                    <div className="flex items-center gap-1">
                      Calls
                      <ArrowUpDown className="w-3 h-3" />
                    </div>
                  </th>
                  <th
                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:text-gray-700 dark:hover:text-gray-200"
                    onClick={() => handleSort('total_tokens')}
                  >
                    <div className="flex items-center gap-1">
                      Tokens
                      <ArrowUpDown className="w-3 h-3" />
                    </div>
                  </th>
                  <th
                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:text-gray-700 dark:hover:text-gray-200"
                    onClick={() => handleSort('total_cost')}
                  >
                    <div className="flex items-center gap-1">
                      Cost
                      <ArrowUpDown className="w-3 h-3" />
                    </div>
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Avg Latency
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Errors
                  </th>
                  <th
                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:text-gray-700 dark:hover:text-gray-200"
                    onClick={() => handleSort('error_rate')}
                  >
                    <div className="flex items-center gap-1">
                      Error Rate
                      <ArrowUpDown className="w-3 h-3" />
                    </div>
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {sortedModels.map((model) => (
                  <tr
                    key={`${model.provider}-${model.model_name}`}
                    className="hover:bg-gray-50 dark:hover:bg-gray-900 transition-colors"
                  >
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                      <div className="flex items-center gap-2">
                        <Server className="w-4 h-4 text-indigo-500" />
                        {model.provider}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
                      {model.model_name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                      {formatNumber(model.total_calls)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                      {formatNumber(model.total_tokens)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-green-600 dark:text-green-400">
                      {formatCost(model.total_cost)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                      {Math.round(model.avg_latency_ms || 0)}ms
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                      {model.error_count}
                    </td>
                    <td className={`px-6 py-4 whitespace-nowrap text-sm font-semibold ${getErrorRateColor(model.error_rate || 0)}`}>
                      <div className="flex items-center gap-1">
                        {(model.error_rate || 0) >= 5 && <AlertTriangle className="w-4 h-4" />}
                        {(model.error_rate || 0).toFixed(1)}%
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                      <Link
                        href={`/admin/token-manager/pricing?provider=${model.provider}&model=${model.model_name}`}
                        className="text-brand-500 hover:text-brand-600 dark:text-brand-400 dark:hover:text-brand-300 font-medium"
                      >
                        View Pricing →
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Summary */}
      {sortedModels.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
            <p className="text-sm text-blue-800 dark:text-blue-200">
              Showing <span className="font-semibold">{sortedModels.length}</span> model{sortedModels.length !== 1 ? 's' : ''} from {startDate} to {endDate}
            </p>
          </div>
          
          {sortedModels.some(m => (m.error_rate || 0) >= 5) && (
            <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                <p className="text-sm text-amber-800 dark:text-amber-200">
                  <span className="font-semibold">{sortedModels.filter(m => (m.error_rate || 0) >= 5).length}</span> model{sortedModels.filter(m => (m.error_rate || 0) >= 5).length !== 1 ? 's' : ''} with high error rate (≥5%)
                </p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
