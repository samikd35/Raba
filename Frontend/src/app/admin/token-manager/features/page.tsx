"use client";

import React, { useState, useEffect } from 'react';
import { tokenMonitoringService, FeatureUsageMetrics } from '@/lib/api/tokenMonitoringService';
import { DateRangePicker } from '@/components/token-manager/DateRangePicker';
import { LoadingState } from '@/components/token-manager/LoadingState';
import { EmptyState } from '@/components/token-manager/EmptyState';
import { ArrowUpDown, Search, Zap } from 'lucide-react';
import { toast } from 'react-hot-toast';

type SortField = 'total_calls' | 'total_tokens' | 'total_cost' | 'avg_latency_ms';
type SortDirection = 'asc' | 'desc';

export default function FeaturesPage() {
  const [features, setFeatures] = useState<FeatureUsageMetrics[]>([]);
  const [filteredFeatures, setFilteredFeatures] = useState<FeatureUsageMetrics[]>([]);
  const [loading, setLoading] = useState(true);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
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
      fetchFeatures();
    }
  }, [startDate, endDate]);

  useEffect(() => {
    // Filter features based on search query
    if (searchQuery) {
      const filtered = features.filter(feature =>
        feature.feature_id.toLowerCase().includes(searchQuery.toLowerCase())
      );
      setFilteredFeatures(filtered);
    } else {
      setFilteredFeatures(features);
    }
  }, [searchQuery, features]);

  const fetchFeatures = async () => {
    try {
      setLoading(true);
      const response = await tokenMonitoringService.getFeatureAnalytics({
        start_date: startDate,
        end_date: endDate,
      });
      setFeatures(response);
      setFilteredFeatures(response);
    } catch (error: any) {
      console.error('Failed to fetch features:', error);
      toast.error(error.message || 'Failed to load feature analytics');
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

  const sortedFeatures = [...filteredFeatures].sort((a, b) => {
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
      case 'avg_latency_ms':
        aValue = a.avg_latency_ms;
        bValue = b.avg_latency_ms;
        break;
      default:
        return 0;
    }
    
    return sortDirection === 'asc' ? aValue - bValue : bValue - aValue;
  });

  const formatNumber = (num: number): string => {
    if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
    if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`;
    return num.toLocaleString();
  };

  const formatCost = (cost: string): string => {
    const numCost = parseFloat(cost);
    if (numCost >= 1000) return `$${(numCost / 1000).toFixed(2)}K`;
    return `$${numCost.toFixed(2)}`;
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
            Feature Analytics
          </h1>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
            AI usage metrics grouped by feature
          </p>
        </div>
        <DateRangePicker
          startDate={startDate}
          endDate={endDate}
          onStartDateChange={setStartDate}
          onEndDateChange={setEndDate}
        />
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          type="text"
          placeholder="Search features..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full pl-10 pr-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md text-sm text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500"
        />
      </div>

      {/* Table */}
      {sortedFeatures.length === 0 ? (
        <EmptyState
          title={searchQuery ? "No matching features" : "No feature data"}
          message={searchQuery ? "Try adjusting your search query." : "There are no features with AI usage in the selected date range."}
          action={{
            label: 'Refresh',
            onClick: fetchFeatures,
          }}
        />
      ) : (
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Feature ID
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
                  <th
                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:text-gray-700 dark:hover:text-gray-200"
                    onClick={() => handleSort('avg_latency_ms')}
                  >
                    <div className="flex items-center gap-1">
                      Avg Latency
                      <ArrowUpDown className="w-3 h-3" />
                    </div>
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Tenants
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Projects
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {sortedFeatures.map((feature) => (
                  <tr
                    key={feature.feature_id}
                    className="hover:bg-gray-50 dark:hover:bg-gray-900 transition-colors"
                  >
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
                      <div className="flex items-center gap-2">
                        <Zap className="w-4 h-4 text-purple-500" />
                        {feature.feature_id}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                      {formatNumber(feature.total_calls)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                      {formatNumber(feature.total_tokens)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-green-600 dark:text-green-400">
                      {formatCost(feature.total_cost)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                      {Math.round(feature.avg_latency_ms)}ms
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                      {feature.distinct_tenants}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                      {feature.distinct_projects}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Summary */}
      {sortedFeatures.length > 0 && (
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
          <p className="text-sm text-blue-800 dark:text-blue-200">
            Showing <span className="font-semibold">{sortedFeatures.length}</span> feature{sortedFeatures.length !== 1 ? 's' : ''} {searchQuery && `matching "${searchQuery}"`} from {startDate} to {endDate}
          </p>
        </div>
      )}
    </div>
  );
}
