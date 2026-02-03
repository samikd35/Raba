"use client";

import React, { useState, useEffect } from 'react';
import { tokenMonitoringService, SystemMetrics } from '@/lib/api/tokenMonitoringService';
import { MetricsCard } from '@/components/token-manager/MetricsCard';
import { DateRangePicker } from '@/components/token-manager/DateRangePicker';
import { LoadingState } from '@/components/token-manager/LoadingState';
import { EmptyState } from '@/components/token-manager/EmptyState';
import { Phone, Zap, DollarSign, Users, Server, Clock } from 'lucide-react';
import { toast } from 'react-hot-toast';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';
import { Line } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

export default function TokenManagerOverview() {
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
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
    if (startDate && endDate) {
      fetchMetrics();
    }
  }, [startDate, endDate]);

  const fetchMetrics = async () => {
    try {
      setLoading(true);
      const data = await tokenMonitoringService.getSystemMetrics({
        start_date: startDate,
        end_date: endDate,
      });
      setMetrics(data);
    } catch (error: any) {
      console.error('Failed to fetch metrics:', error);
      toast.error(error.message || 'Failed to load system metrics');
    } finally {
      setLoading(false);
    }
  };

  const formatNumber = (num: number): string => {
    if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
    if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`;
    return num.toLocaleString();
  };

  const formatCost = (cost: string): string => {
    const numCost = parseFloat(cost);
    if (numCost >= 1000) return `$${(numCost / 1000).toFixed(1)}K`;
    return `$${numCost.toFixed(2)}`;
  };

  const calculateAvgLatency = (): number => {
    if (!metrics || metrics.daily_breakdown.length === 0) return 0;
    const totalLatency = metrics.daily_breakdown.reduce((sum, day) => sum + day.avg_latency_ms, 0);
    return Math.round(totalLatency / metrics.daily_breakdown.length);
  };

  if (loading) {
    return <LoadingState />;
  }

  if (!metrics) {
    return (
      <EmptyState
        title="No data available"
        message="Unable to load system metrics. Please try again later."
        action={{
          label: 'Retry',
          onClick: fetchMetrics,
        }}
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            AI Usage Overview
          </h1>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
            System-wide AI token usage and cost metrics
          </p>
        </div>
        <DateRangePicker
          startDate={startDate}
          endDate={endDate}
          onStartDateChange={setStartDate}
          onEndDateChange={setEndDate}
        />
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <MetricsCard
          title="Total Calls"
          value={formatNumber(metrics.total_calls)}
          subtitle="AI operations"
          icon={Phone}
          iconColor="text-blue-500"
        />

        <MetricsCard
          title="Total Tokens"
          value={formatNumber(metrics.total_tokens)}
          subtitle="Tokens consumed"
          icon={Zap}
          iconColor="text-purple-500"
        />

        <MetricsCard
          title="Total Cost"
          value={formatCost(metrics.total_cost)}
          subtitle="USD spent"
          icon={DollarSign}
          iconColor="text-green-500"
        />

        <MetricsCard
          title="Active Tenants"
          value={formatNumber(metrics.distinct_tenants)}
          subtitle="Organizations"
          icon={Users}
          iconColor="text-amber-500"
        />

        <MetricsCard
          title="Models Used"
          value={formatNumber(metrics.distinct_models)}
          subtitle="AI models"
          icon={Server}
          iconColor="text-indigo-500"
        />

        <MetricsCard
          title="Avg Latency"
          value={`${calculateAvgLatency()}ms`}
          subtitle="Response time"
          icon={Clock}
          iconColor="text-gray-500"
        />
      </div>

      {/* Daily Usage Trend Chart */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Daily Usage Trend
        </h2>
        {metrics.daily_breakdown.length > 0 ? (
          <div className="h-80">
            <Line
              data={{
                labels: metrics.daily_breakdown.map(d => {
                  const date = new Date(d.date);
                  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
                }),
                datasets: [
                  {
                    label: 'Calls',
                    data: metrics.daily_breakdown.map(d => d.calls_count),
                    borderColor: 'rgb(59, 130, 246)',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    yAxisID: 'y',
                    tension: 0.3,
                    fill: true,
                  },
                  {
                    label: 'Cost ($)',
                    data: metrics.daily_breakdown.map(d => parseFloat(d.sum_total_cost)),
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
        ) : (
          <div className="h-64 flex items-center justify-center text-gray-500 dark:text-gray-400">
            No daily breakdown data available
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <a
          href="/admin/token-manager/tenants"
          className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 hover:shadow-md transition-shadow"
        >
          <h3 className="font-semibold text-gray-900 dark:text-white mb-1">
            View Top Tenants
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            See which tenants are using the most AI resources
          </p>
        </a>

        <a
          href="/admin/token-manager/features"
          className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 hover:shadow-md transition-shadow"
        >
          <h3 className="font-semibold text-gray-900 dark:text-white mb-1">
            View Top Features
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Analyze AI usage across different features
          </p>
        </a>

        <a
          href="/admin/token-manager/pricing"
          className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 hover:shadow-md transition-shadow"
        >
          <h3 className="font-semibold text-gray-900 dark:text-white mb-1">
            Manage Pricing
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Configure AI model pricing and costs
          </p>
        </a>
      </div>
    </div>
  );
}
