'use client';

import React from 'react';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { TrendingUp, Users, UserCheck, Percent } from 'lucide-react';

interface InvitationData {
  sent: number;
  accepted: number;
}

interface InvitationAnalyticsPanelProps {
  invitations: InvitationData | null;
  isLoading?: boolean;
  className?: string;
  showChart?: boolean;
  trendData?: Array<{
    date: string;
    sent: number;
    accepted: number;
  }>;
}

/**
 * InvitationAnalyticsPanel Component
 * 
 * Displays invitation analytics with sent, accepted counts and acceptance rate.
 * Optionally shows a trend chart over time.
 * 
 * Features:
 * - Total invitations sent
 * - Invitations accepted
 * - Calculated acceptance rate percentage
 * - Optional line chart showing trend over time
 * - Loading skeleton state
 * - Responsive design for mobile
 */
export function InvitationAnalyticsPanel({
  invitations,
  isLoading = false,
  className,
  showChart = false,
  trendData,
}: InvitationAnalyticsPanelProps) {
  // Loading state
  if (isLoading || !invitations) {
    return (
      <Card className={cn('w-full', className)}>
        <CardHeader>
          <Skeleton className="h-6 w-40 mb-2" />
          <Skeleton className="h-4 w-56" />
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-24 w-full" />
          </div>
          {showChart && (
            <div className="mt-6">
              <Skeleton className="h-64 w-full" />
            </div>
          )}
        </CardContent>
      </Card>
    );
  }

  // Calculate acceptance rate
  const acceptanceRate = invitations.sent > 0
    ? Math.round((invitations.accepted / invitations.sent) * 100)
    : 0;

  // Determine acceptance rate color
  const getAcceptanceRateColor = (rate: number) => {
    if (rate >= 70) {
      return {
        text: 'text-green-600 dark:text-green-400',
        bg: 'bg-green-50 dark:bg-green-900/20',
        border: 'border-green-200 dark:border-green-800',
      };
    } else if (rate >= 40) {
      return {
        text: 'text-yellow-600 dark:text-yellow-400',
        bg: 'bg-yellow-50 dark:bg-yellow-900/20',
        border: 'border-yellow-200 dark:border-yellow-800',
      };
    } else {
      return {
        text: 'text-red-600 dark:text-red-400',
        bg: 'bg-red-50 dark:bg-red-900/20',
        border: 'border-red-200 dark:border-red-800',
      };
    }
  };

  const rateColors = getAcceptanceRateColor(acceptanceRate);

  // Format numbers with commas
  const formatNumber = (num: number) => {
    return num.toLocaleString('en-US');
  };

  return (
    <Card className={cn('w-full', className)}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <TrendingUp className="h-5 w-5 text-brand-500" />
          Invitation Analytics
        </CardTitle>
        <CardDescription>
          Track invitation performance and acceptance rates
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Metrics Grid */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {/* Total Sent */}
          <div className="flex flex-col space-y-2 rounded-lg border border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900/50 p-4">
            <div className="flex items-center gap-2 text-muted-foreground">
              <Users className="h-4 w-4" />
              <span className="text-xs font-medium">Invitations Sent</span>
            </div>
            <p className="text-3xl font-bold text-brand-500 dark:text-white">
              {formatNumber(invitations.sent)}
            </p>
            <p className="text-xs text-muted-foreground">
              Total invitations sent
            </p>
          </div>

          {/* Total Accepted */}
          <div className="flex flex-col space-y-2 rounded-lg border border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900/50 p-4">
            <div className="flex items-center gap-2 text-muted-foreground">
              <UserCheck className="h-4 w-4" />
              <span className="text-xs font-medium">Invitations Accepted</span>
            </div>
            <p className="text-3xl font-bold text-green-600 dark:text-green-400">
              {formatNumber(invitations.accepted)}
            </p>
            <p className="text-xs text-muted-foreground">
              Successfully accepted
            </p>
          </div>

          {/* Acceptance Rate */}
          <div className={cn(
            'flex flex-col space-y-2 rounded-lg border p-4',
            rateColors.bg,
            rateColors.border
          )}>
            <div className="flex items-center gap-2 text-muted-foreground">
              <Percent className="h-4 w-4" />
              <span className="text-xs font-medium">Acceptance Rate</span>
            </div>
            <p className={cn('text-3xl font-bold', rateColors.text)}>
              {acceptanceRate}%
            </p>
            <p className="text-xs text-muted-foreground">
              {acceptanceRate >= 70 && 'Excellent performance'}
              {acceptanceRate >= 40 && acceptanceRate < 70 && 'Good performance'}
              {acceptanceRate < 40 && invitations.sent > 0 && 'Needs improvement'}
              {invitations.sent === 0 && 'No data yet'}
            </p>
          </div>
        </div>

        {/* Status Message */}
        <div className="rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 p-4">
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0">
              <TrendingUp className="h-5 w-5 text-blue-600 dark:text-blue-400" />
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium text-blue-900 dark:text-blue-100">
                Invitation Summary
              </p>
              <p className="mt-1 text-sm text-blue-700 dark:text-blue-300">
                {invitations.sent === 0 && (
                  'No invitations sent yet. Start inviting members to grow your organization.'
                )}
                {invitations.sent > 0 && invitations.accepted === 0 && (
                  `You have sent ${formatNumber(invitations.sent)} invitation${invitations.sent === 1 ? '' : 's'}, but none have been accepted yet. Follow up with invitees to improve acceptance.`
                )}
                {invitations.sent > 0 && invitations.accepted > 0 && acceptanceRate >= 70 && (
                  `Great job! ${formatNumber(invitations.accepted)} out of ${formatNumber(invitations.sent)} invitations accepted. Your acceptance rate of ${acceptanceRate}% is excellent.`
                )}
                {invitations.sent > 0 && invitations.accepted > 0 && acceptanceRate >= 40 && acceptanceRate < 70 && (
                  `${formatNumber(invitations.accepted)} out of ${formatNumber(invitations.sent)} invitations accepted. Your ${acceptanceRate}% acceptance rate is good, but there's room for improvement.`
                )}
                {invitations.sent > 0 && invitations.accepted > 0 && acceptanceRate < 40 && (
                  `${formatNumber(invitations.accepted)} out of ${formatNumber(invitations.sent)} invitations accepted. Consider reviewing your invitation strategy to improve the ${acceptanceRate}% acceptance rate.`
                )}
              </p>
            </div>
          </div>
        </div>

        {/* Optional Trend Chart */}
        {showChart && trendData && trendData.length > 0 && (
          <div className="space-y-4">
            <div className="border-t border-gray-200 dark:border-gray-800 pt-6">
              <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-4">
                Invitation Trend Over Time
              </h3>
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart
                    data={trendData}
                    margin={{ top: 5, right: 10, left: 0, bottom: 5 }}
                  >
                    <CartesianGrid 
                      strokeDasharray="3 3" 
                      className="stroke-gray-200 dark:stroke-gray-800"
                    />
                    <XAxis
                      dataKey="date"
                      className="text-xs"
                      tick={{ fill: 'currentColor' }}
                      tickLine={{ stroke: 'currentColor' }}
                    />
                    <YAxis
                      className="text-xs"
                      tick={{ fill: 'currentColor' }}
                      tickLine={{ stroke: 'currentColor' }}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'hsl(var(--background))',
                        border: '1px solid hsl(var(--border))',
                        borderRadius: '0.5rem',
                      }}
                      labelStyle={{ color: 'hsl(var(--foreground))' }}
                    />
                    <Legend
                      wrapperStyle={{
                        paddingTop: '1rem',
                      }}
                    />
                    <Line
                      type="monotone"
                      dataKey="sent"
                      stroke="hsl(var(--brand-500))"
                      strokeWidth={2}
                      name="Sent"
                      dot={{ fill: 'hsl(var(--brand-500))', r: 4 }}
                      activeDot={{ r: 6 }}
                    />
                    <Line
                      type="monotone"
                      dataKey="accepted"
                      stroke="rgb(34, 197, 94)"
                      strokeWidth={2}
                      name="Accepted"
                      dot={{ fill: 'rgb(34, 197, 94)', r: 4 }}
                      activeDot={{ r: 6 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
