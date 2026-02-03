"use client";

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { tokenMonitoringService, TenantDetailedUsage } from '@/lib/api/tokenMonitoringService';
import { DateRangePicker } from '@/components/token-manager/DateRangePicker';
import { LoadingState } from '@/components/token-manager/LoadingState';
import { EmptyState } from '@/components/token-manager/EmptyState';
import { ArrowLeft, Phone, Zap, DollarSign, TrendingUp, Building2, Users, User, Activity, Box, Brain } from 'lucide-react';
import { toast } from 'react-hot-toast';
import Link from 'next/link';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';
import { Line, Bar } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

export default function TenantDetailsPage() {
  const params = useParams();
  const router = useRouter();
  const tenantId = params.tenant_id as string;
  
  const [tenantData, setTenantData] = useState<TenantDetailedUsage | null>(null);
  const [loading, setLoading] = useState(true);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  useEffect(() => {
    // Set default date range (last 30 days)
    const end = new Date();
    const start = new Date();
    start.setDate(start.getDate() - 30);
    
    setStartDate(start.toISOString().split('T')[0]);
    setEndDate(end.toISOString().split('T')[0]);
  }, []);

  useEffect(() => {
    if (startDate && endDate && tenantId) {
      fetchTenantDetails();
    }
  }, [startDate, endDate, tenantId]);

  const fetchTenantDetails = async () => {
    try {
      setLoading(true);
      const data = await tokenMonitoringService.getTenantDetails(tenantId, {
        start_date: startDate,
        end_date: endDate,
        include_children: true,
      });
      console.log('Received tenant data:', data);
      console.log('Daily breakdown sample:', data.daily_breakdown?.[0]);
      setTenantData(data);
    } catch (error: any) {
      console.error('Failed to fetch tenant details:', error);
      toast.error(error.message || 'Failed to load tenant details');
    } finally {
      setLoading(false);
    }
  };

  const formatNumber = (num: number): string => {
    if (num >= 1000000) {
      return (num / 1000000).toFixed(1) + 'M';
    }
    if (num >= 1000) {
      return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
  };

  const formatCost = (cost: string): string => {
    const num = parseFloat(cost);
    return `$${num.toFixed(2)}`;
  };

  if (loading) {
    return <LoadingState message="Loading tenant details..." />;
  }

  if (!tenantData) {
    return (
      <EmptyState
        title="No Data Available"
        message="Could not load tenant details. The tenant may not exist or has no usage data."
        action={{
          label: "Back to Tenants",
          onClick: () => router.push('/admin/token-manager/tenants')
        }}
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            href="/admin/token-manager/tenants"
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
          >
            <ArrowLeft className="w-5 h-5 text-gray-600 dark:text-gray-400" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              {tenantData.tenant_info.tenant_name}
            </h1>
            <div className="flex items-center gap-2 mt-1">
              <p className="text-sm text-gray-600 dark:text-gray-400 font-mono">
                {tenantId}
              </p>
              <span className="px-2 py-0.5 text-xs font-medium bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300 rounded">
                {tenantData.tenant_info.tenant_type}
              </span>
            </div>
          </div>
        </div>
        <DateRangePicker
          startDate={startDate}
          endDate={endDate}
          onStartDateChange={setStartDate}
          onEndDateChange={setEndDate}
        />
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                Total Calls
              </p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white mt-2">
                {formatNumber(tenantData.usage_summary.total_calls)}
              </p>
            </div>
            <div className="p-3 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
              <Phone className="w-6 h-6 text-blue-500" />
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                Total Tokens
              </p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white mt-2">
                {formatNumber(tenantData.usage_summary.total_tokens)}
              </p>
            </div>
            <div className="p-3 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
              <Zap className="w-6 h-6 text-purple-500" />
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                Total Cost
              </p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white mt-2">
                ${tenantData.usage_summary.total_cost.toFixed(2)}
              </p>
            </div>
            <div className="p-3 bg-green-100 dark:bg-green-900/30 rounded-lg">
              <DollarSign className="w-6 h-6 text-green-500" />
            </div>
          </div>
        </div>
      </div>

      {/* Daily Usage Chart */}
      {tenantData.daily_breakdown && tenantData.daily_breakdown.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Daily Usage Trend
          </h2>
          <div className="h-80">
            <Line
              data={{
                labels: tenantData.daily_breakdown.map(d => {
                  const date = new Date(d.date);
                  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
                }),
                datasets: [
                  {
                    label: 'Calls',
                    data: tenantData.daily_breakdown.map(d => d.calls_count),
                    borderColor: 'rgb(59, 130, 246)',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    yAxisID: 'y',
                    tension: 0.3,
                    fill: true,
                  },
                  {
                    label: 'Cost ($)',
                    data: tenantData.daily_breakdown.map(d => d.sum_total_cost),
                    borderColor: 'rgb(16, 185, 129)',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    yAxisID: 'y1',
                    tension: 0.3,
                    fill: true,
                  },
                ],
              }}
              options={{
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                  mode: 'index',
                  intersect: false,
                },
                plugins: {
                  legend: {
                    position: 'top',
                    labels: {
                      color: 'rgb(107, 114, 128)',
                      usePointStyle: true,
                      padding: 15,
                    },
                  },
                  tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    padding: 12,
                    titleColor: 'rgb(255, 255, 255)',
                    bodyColor: 'rgb(255, 255, 255)',
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    borderWidth: 1,
                  },
                },
                scales: {
                  y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: {
                      display: true,
                      text: 'Number of Calls',
                      color: 'rgb(59, 130, 246)',
                    },
                    ticks: {
                      color: 'rgb(107, 114, 128)',
                    },
                    grid: {
                      color: 'rgba(107, 114, 128, 0.1)',
                    },
                  },
                  y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: {
                      display: true,
                      text: 'Cost (USD)',
                      color: 'rgb(16, 185, 129)',
                    },
                    ticks: {
                      color: 'rgb(107, 114, 128)',
                      callback: function(value) {
                        return '$' + Number(value).toFixed(2);
                      },
                    },
                    grid: {
                      drawOnChartArea: false,
                    },
                  },
                  x: {
                    ticks: {
                      color: 'rgb(107, 114, 128)',
                    },
                    grid: {
                      color: 'rgba(107, 114, 128, 0.1)',
                    },
                  },
                },
              }}
            />
          </div>
        </div>
      )}

      {/* Children Breakdown */}
      {tenantData.children_breakdown && tenantData.children_breakdown.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
          <div className="p-6 border-b border-gray-200 dark:border-gray-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              <Users className="w-5 h-5" />
              Child Tenants Breakdown
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              Usage broken down by individual teams and members under this organization
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 dark:bg-gray-900">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Tenant
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Type
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Calls
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Tokens
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Cost
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {tenantData.children_breakdown.map((child, index) => (
                  <tr key={index} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                    <td className="px-6 py-4 text-sm">
                      <div className="flex flex-col">
                        <span className="font-medium text-gray-900 dark:text-white">{child.tenant_name}</span>
                        <span className="text-xs text-gray-500 dark:text-gray-400 font-mono">{child.tenant_id}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                      <span className="capitalize">{child.tenant_type}</span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-900 dark:text-white">
                      {formatNumber(child.total_calls)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-900 dark:text-white">
                      {formatNumber(child.total_tokens)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-semibold text-green-600 dark:text-green-400">
                      ${child.total_cost.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Feature Breakdown */}
      {tenantData.feature_breakdown && tenantData.feature_breakdown.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
          <div className="p-6 border-b border-gray-200 dark:border-gray-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              <Box className="w-5 h-5" />
              Feature Usage Breakdown
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              AI usage broken down by feature
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 dark:bg-gray-900">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Feature
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Calls
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Tokens
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Cost
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {tenantData.feature_breakdown.map((feature, index) => (
                  <tr key={index} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
                      {feature.feature_id}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-900 dark:text-white">
                      {formatNumber(feature.total_calls)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-900 dark:text-white">
                      {formatNumber(feature.total_tokens)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-semibold text-green-600 dark:text-green-400">
                      ${feature.total_cost.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Model Breakdown */}
      {tenantData.model_breakdown && tenantData.model_breakdown.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
          <div className="p-6 border-b border-gray-200 dark:border-gray-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              <Brain className="w-5 h-5" />
              Model Usage Breakdown
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              AI usage broken down by model
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 dark:bg-gray-900">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Model
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Calls
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Tokens
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Cost
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {tenantData.model_breakdown.map((model, index) => (
                  <tr key={index} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
                      {model.model}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-900 dark:text-white">
                      {formatNumber(model.total_calls)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-900 dark:text-white">
                      {formatNumber(model.total_tokens)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-semibold text-green-600 dark:text-green-400">
                      ${model.total_cost.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Top Users */}
      {tenantData.top_users && tenantData.top_users.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
          <div className="p-6 border-b border-gray-200 dark:border-gray-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              <Activity className="w-5 h-5" />
              Top Users
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              Highest AI usage by individual users
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 dark:bg-gray-900">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    User ID
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Calls
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Tokens
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Cost
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {tenantData.top_users.map((user, index) => (
                  <tr key={index} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-900 dark:text-white">
                      {user.user_id}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-900 dark:text-white">
                      {formatNumber(user.total_calls)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-900 dark:text-white">
                      {formatNumber(user.total_tokens)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-semibold text-green-600 dark:text-green-400">
                      ${user.total_cost.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Daily Breakdown Table */}
      {tenantData.daily_breakdown && tenantData.daily_breakdown.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
          <div className="p-6 border-b border-gray-200 dark:border-gray-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Daily Breakdown
            </h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 dark:bg-gray-900">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Date
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Calls
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Tokens
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Cost
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Avg Latency
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Errors
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {tenantData.daily_breakdown.filter(day => day && day.date).map((day, index) => (
                  <tr key={index} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                      {new Date(day.date).toLocaleDateString('en-US', {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric',
                      })}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-900 dark:text-white">
                      {(day.calls_count || 0).toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-900 dark:text-white">
                      {formatNumber(day.sum_total_tokens || 0)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-900 dark:text-white">
                      ${(day.sum_total_cost || 0).toFixed(2)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-900 dark:text-white">
                      {(day.avg_latency_ms || 0).toFixed(0)}ms
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right">
                      <span className={`${
                        (day.error_count || 0) > 0 
                          ? 'text-red-600 dark:text-red-400 font-medium' 
                          : 'text-gray-900 dark:text-white'
                      }`}>
                        {day.error_count || 0}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
