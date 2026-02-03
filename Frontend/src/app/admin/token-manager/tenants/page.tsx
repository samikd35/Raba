"use client";

import React, { useState, useEffect } from 'react';
import { tokenMonitoringService, TenantUsageMetrics } from '@/lib/api/tokenMonitoringService';
import { DateRangePicker } from '@/components/token-manager/DateRangePicker';
import { LoadingState } from '@/components/token-manager/LoadingState';
import { EmptyState } from '@/components/token-manager/EmptyState';
import { ArrowUpDown, Download, TrendingUp, Building2, Users, User, HelpCircle, AlertCircle } from 'lucide-react';
import { toast } from 'react-hot-toast';
import Link from 'next/link';

type SortField = 'total_calls' | 'total_tokens' | 'total_cost';
type SortDirection = 'asc' | 'desc';

export default function TenantsPage() {
  const [tenants, setTenants] = useState<TenantUsageMetrics[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [activeCount, setActiveCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [limit, setLimit] = useState(50);
  const [sortField, setSortField] = useState<SortField>('total_cost');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const [includeZeroUsage, setIncludeZeroUsage] = useState(true);
  const [viewMode, setViewMode] = useState<'organizations' | 'all' | 'individuals'>('organizations');

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
      fetchTenants();
    }
  }, [startDate, endDate, limit, includeZeroUsage, viewMode]);

  const fetchTenants = async () => {
    try {
      setLoading(true);
      
      // Map viewMode to backend parameters
      const groupBy = viewMode === 'organizations' ? 'organization' : 'tenant';
      const tenantType = viewMode === 'organizations' 
        ? 'organization' as const
        : viewMode === 'individuals' 
        ? 'individual' as const
        : undefined; // 'all' mode - no type filter
      
      const response = await tokenMonitoringService.getTenantRankings({
        limit: 500, // Increased backend max to 500
        start_date: startDate,
        end_date: endDate,
        group_by: groupBy,
        include_zero_usage: includeZeroUsage,
        tenant_type: tenantType,
      });
      
      // Backend now handles filtering, so we can use results directly
      const limitedTenants = response.tenants.slice(0, limit);
      
      setTenants(limitedTenants);
      setTotalCount(response.total_count);
      setActiveCount(response.active_count);
    } catch (error: any) {
      console.error('Failed to fetch tenants:', error);
      toast.error(error.message || 'Failed to load tenant rankings');
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

  const sortedTenants = [...tenants].sort((a, b) => {
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

  const getTenantTypeIcon = (type: string) => {
    switch (type) {
      case 'organization':
        return <Building2 className="w-4 h-4" />;
      case 'team':
        return <Users className="w-4 h-4" />;
      case 'individual':
        return <User className="w-4 h-4" />;
      case 'unknown':
        return <HelpCircle className="w-4 h-4" />;
      default:
        return null;
    }
  };

  const getTenantTypeBadgeColor = (type: string) => {
    switch (type) {
      case 'organization':
        return 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300';
      case 'team':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300';
      case 'individual':
        return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300';
      case 'unknown':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-300';
    }
  };

  const inactiveCount = totalCount - activeCount;

  const exportToCSV = () => {
    const headers = ['Rank', 'Tenant ID', 'Tenant Name', 'Type', 'Total Calls', 'Total Tokens', 'Total Cost', 'Organization'];
    const rows = sortedTenants.map((tenant, index) => [
      index + 1,
      tenant.tenant_id,
      tenant.tenant_name,
      tenant.tenant_type,
      tenant.total_calls,
      tenant.total_tokens,
      tenant.total_cost,
      tenant.organization_id || 'N/A',
    ]);
    
    const csv = [
      headers.join(','),
      ...rows.map(row => row.join(','))
    ].join('\n');
    
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `tenant-rankings-${startDate}-to-${endDate}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
    toast.success('CSV exported successfully');
  };

  if (loading) {
    return <LoadingState />;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              Tenant Rankings
            </h1>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
              Top tenants by AI usage and cost
            </p>
          </div>
          <DateRangePicker
            startDate={startDate}
            endDate={endDate}
            onStartDateChange={setStartDate}
            onEndDateChange={setEndDate}
          />
        </div>

        {/* View Toggle */}
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">View:</span>
          <div className="inline-flex rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 p-1">
            <button
              onClick={() => setViewMode('all')}
              className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                viewMode === 'all'
                  ? 'bg-brand-500 text-white shadow-sm'
                  : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
              }`}
            >
              <div className="flex items-center gap-2">
                <Users className="w-4 h-4" />
                All Tenants
              </div>
            </button>
            <button
              onClick={() => setViewMode('organizations')}
              className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                viewMode === 'organizations'
                  ? 'bg-brand-500 text-white shadow-sm'
                  : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
              }`}
            >
              <div className="flex items-center gap-2">
                <Building2 className="w-4 h-4" />
                Organizations
              </div>
            </button>
            <button
              onClick={() => setViewMode('individuals')}
              className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                viewMode === 'individuals'
                  ? 'bg-brand-500 text-white shadow-sm'
                  : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
              }`}
            >
              <div className="flex items-center gap-2">
                <User className="w-4 h-4" />
                Individuals
              </div>
            </button>
          </div>
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {viewMode === 'all'
              ? 'All tenants individually (orgs, teams, individuals)'
              : viewMode === 'organizations' 
              ? 'Organizations with teams & individuals rolled up' 
              : 'Individual tenants only'}
          </span>
        </div>
      </div>

      {/* Stats Banner */}
      {totalCount > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900/20 dark:to-blue-800/20 border border-blue-200 dark:border-blue-700 rounded-lg p-4">
            <p className="text-sm font-medium text-blue-800 dark:text-blue-300">Total Tenants</p>
            <p className="text-2xl font-bold text-blue-900 dark:text-blue-100 mt-1">{totalCount}</p>
          </div>
          <div className="bg-gradient-to-br from-green-50 to-green-100 dark:from-green-900/20 dark:to-green-800/20 border border-green-200 dark:border-green-700 rounded-lg p-4">
            <p className="text-sm font-medium text-green-800 dark:text-green-300">Active Tenants</p>
            <p className="text-2xl font-bold text-green-900 dark:text-green-100 mt-1">{activeCount}</p>
          </div>
          <div className="bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900/20 dark:to-gray-800/20 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <p className="text-sm font-medium text-gray-800 dark:text-gray-300">Inactive Tenants</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-gray-100 mt-1">{inactiveCount}</p>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Show:
            </label>
            <select
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value))}
              className="px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              <option value={10}>Top 10</option>
              <option value={25}>Top 25</option>
              <option value={50}>Top 50</option>
              <option value={100}>Top 100</option>
            </select>
          </div>
          
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={includeZeroUsage}
              onChange={(e) => setIncludeZeroUsage(e.target.checked)}
              className="w-4 h-4 text-brand-500 border-gray-300 rounded focus:ring-brand-500"
            />
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Include zero usage
            </span>
          </label>
        </div>

        <button
          onClick={exportToCSV}
          disabled={tenants.length === 0}
          className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <Download className="w-4 h-4" />
          Export CSV
        </button>
      </div>

      {/* Table */}
      {tenants.length === 0 ? (
        <EmptyState
          title="No tenant data"
          message="There are no tenants with AI usage in the selected date range."
          action={{
            label: 'Refresh',
            onClick: fetchTenants,
          }}
        />
      ) : (
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Rank
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Tenant
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Type
                  </th>
                  <th
                    className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:text-gray-700 dark:hover:text-gray-200"
                    onClick={() => handleSort('total_calls')}
                  >
                    <div className="flex items-center justify-end gap-1">
                      Calls
                      <ArrowUpDown className="w-3 h-3" />
                    </div>
                  </th>
                  <th
                    className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:text-gray-700 dark:hover:text-gray-200"
                    onClick={() => handleSort('total_tokens')}
                  >
                    <div className="flex items-center justify-end gap-1">
                      Tokens
                      <ArrowUpDown className="w-3 h-3" />
                    </div>
                  </th>
                  <th
                    className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:text-gray-700 dark:hover:text-gray-200"
                    onClick={() => handleSort('total_cost')}
                  >
                    <div className="flex items-center justify-end gap-1">
                      Cost
                      <ArrowUpDown className="w-3 h-3" />
                    </div>
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {sortedTenants.map((tenant, index) => {
                  const isActive = parseFloat(tenant.total_cost) > 0;
                  const isUnknown = tenant.tenant_type === 'unknown';
                  
                  return (
                    <tr
                      key={tenant.tenant_id}
                      className={`hover:bg-gray-50 dark:hover:bg-gray-900 transition-colors ${
                        !isActive ? 'opacity-60' : ''
                      }`}
                    >
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{index + 1}</span>
                          {index < 3 && isActive && <TrendingUp className="w-4 h-4 text-green-500" />}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex flex-col gap-1">
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-gray-900 dark:text-white">
                              {tenant.tenant_name}
                            </span>
                            {isUnknown && (
                              <div title="No tenant_id in AI usage events">
                                <AlertCircle className="w-4 h-4 text-yellow-500" />
                              </div>
                            )}
                            {!isActive && (
                              <span className="px-2 py-0.5 text-xs font-medium bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 rounded">
                                No usage
                              </span>
                            )}
                          </div>
                          <span className="text-xs text-gray-500 dark:text-gray-400 font-mono">
                            {tenant.tenant_id}
                          </span>
                          {tenant.rollup_tenant_ids && tenant.rollup_tenant_ids.length > 1 && (
                            <span className="text-xs text-blue-600 dark:text-blue-400">
                              Includes {tenant.rollup_tenant_ids.length} tenant{tenant.rollup_tenant_ids.length !== 1 ? 's' : ''}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${getTenantTypeBadgeColor(tenant.tenant_type)}`}>
                          {getTenantTypeIcon(tenant.tenant_type)}
                          {tenant.tenant_type.charAt(0).toUpperCase() + tenant.tenant_type.slice(1)}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-900 dark:text-white">
                        {formatNumber(tenant.total_calls)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-900 dark:text-white">
                        {formatNumber(tenant.total_tokens)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-semibold">
                        <span className={isActive ? 'text-green-600 dark:text-green-400' : 'text-gray-400 dark:text-gray-600'}>
                          {formatCost(tenant.total_cost)}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                        <Link
                          href={`/admin/token-manager/tenants/${tenant.tenant_id}`}
                          className="text-brand-500 hover:text-brand-600 dark:text-brand-400 dark:hover:text-brand-300 font-medium"
                        >
                          View Details →
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Summary */}
      {tenants.length > 0 && (
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
          <p className="text-sm text-blue-800 dark:text-blue-200">
            Showing <span className="font-semibold">{tenants.length}</span> tenant{tenants.length !== 1 ? 's' : ''} with AI usage from {startDate} to {endDate}
          </p>
        </div>
      )}
    </div>
  );
}
