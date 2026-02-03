'use client';

import React, { useMemo } from 'react';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { OrganizationMetrics } from '@/stores/organizationStore';
import { cn } from '@/lib/utils';
import { 
  Coins, 
  TrendingUp, 
  TrendingDown, 
  Activity,
  AlertCircle,
  CheckCircle2,
  AlertTriangle,
  CalendarClock
} from 'lucide-react';

interface OrganizationMetricsCardProps {
  metrics: OrganizationMetrics | null;
  isLoading?: boolean;
  className?: string;
}

// Unified, safe credits shape for rendering
interface SafeCredits {
  total: number;
  used: number;
  remaining: number;
  monthly_limit: number; // 0 or less treated as unlimited
  reset_date?: string | null;
}

/**
 * OrganizationMetricsCard Component
 * 
 * Displays organization credit metrics with visual progress indicators
 * and color-coded status based on usage percentage.
 * 
 * Features:
 * - Credit summary (total, used, remaining, monthly limit)
 * - Visual progress bar with color coding
 * - Usage percentage display
 * - Loading skeleton state
 * - Responsive design for mobile
 * - Enhanced shadcn styling with icons and badges
 * - Tolerant to different backend shapes
 * 
 * Color Coding:
 * - Green: < 50% usage
 * - Yellow: 50-80% usage
 * - Red: > 80% usage
 */
export function OrganizationMetricsCard({
  metrics,
  isLoading = false,
  className,
}: OrganizationMetricsCardProps) {
  // Loading state
  if (isLoading || !metrics) {
    return (
      <Card className={cn('w-full border-border/50 shadow-sm', className)}>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="space-y-2">
              <Skeleton className="h-5 w-32" />
              <Skeleton className="h-4 w-48" />
            </div>
            <Skeleton className="h-10 w-10 rounded-full" />
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="space-y-2">
                <Skeleton className="h-3 w-16" />
                <Skeleton className="h-8 w-20" />
              </div>
            ))}
          </div>
          <div className="space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-3 w-full rounded-full" />
          </div>
        </CardContent>
      </Card>
    );
  }

  // Derive a safe, unified credits object from various possible metric shapes
  const credits: SafeCredits = useMemo(() => {
    // Helper to coerce numbers safely
    const num = (v: unknown, fallback = 0): number => {
      const n = typeof v === 'number' ? v : Number(v);
      return Number.isFinite(n) ? n : fallback;
    };

    // Newer backend flat fields (organization/team details style)
    const poolTotal = (metrics as any)?.credit_pool_total;
    const poolUsed = (metrics as any)?.credit_pool_used;
    const poolRemaining = (metrics as any)?.credit_pool_remaining;
    const resetDate = (metrics as any)?.pool_reset_date ?? (metrics as any)?.reset_date ?? null;

    // Legacy nested credits shape
    const legacy = (metrics as any)?.credits;

    let total = 0;
    let used = 0;
    let remaining = 0;
    let monthly_limit = 0;

    if (legacy && typeof legacy === 'object') {
      total = num(legacy.total, num(poolTotal, 0));
      used = num(legacy.used, num(poolUsed, 0));
      remaining = num(legacy.remaining, num(poolRemaining, Math.max(total - used, 0)));
      monthly_limit = num(legacy.monthly_limit, 0);
    } else {
      // Fall back to pool fields and derive if necessary
      total = num(poolTotal, num((metrics as any)?.total_credits, 0));
      used = num(poolUsed, 0);
      // Prefer provided remaining, else compute
      const derivedRemaining = Math.max(total - used, 0);
      remaining = num(poolRemaining, derivedRemaining);
      // No explicit monthly limit in flat shape
      monthly_limit = num((metrics as any)?.monthly_limit, 0);
    }

    // Clamp and normalize to avoid negatives/NaN
    total = Math.max(0, total);
    used = Math.min(Math.max(0, used), total || used); // if total is 0, allow used as-is but non-negative
    // If remaining not provided correctly, compute
    if (!Number.isFinite(remaining) || remaining < 0 || (total > 0 && remaining > total)) {
      remaining = Math.max(total - used, 0);
    }

    return {
      total,
      used,
      remaining,
      monthly_limit: Number.isFinite(monthly_limit) ? monthly_limit : 0,
      reset_date: typeof resetDate === 'string' && resetDate.length > 0 ? resetDate : null,
    } as SafeCredits;
  }, [metrics]);
  
  // Calculate usage percentage safely
  const usagePercentage = credits.total > 0 
    ? Math.round((credits.used / credits.total) * 100)
    : 0;

  // Determine color and status based on usage percentage
  const getStatusInfo = (percentage: number) => {
    if (percentage < 50) {
      return {
        variant: 'default' as const,
        icon: CheckCircle2,
        text: 'text-emerald-600 dark:text-emerald-400',
        bg: 'bg-emerald-500 dark:bg-emerald-400',
        progressBg: 'bg-emerald-50 dark:bg-emerald-950/30',
        badgeBg: 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800',
        message: 'Credit usage is healthy',
        messageIcon: CheckCircle2,
      };
    } else if (percentage < 80) {
      return {
        variant: 'secondary' as const,
        icon: AlertTriangle,
        text: 'text-amber-600 dark:text-amber-400',
        bg: 'bg-amber-500 dark:bg-amber-400',
        progressBg: 'bg-amber-50 dark:bg-amber-950/30',
        badgeBg: 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-800',
        message: 'Credit usage is moderate - consider monitoring',
        messageIcon: AlertTriangle,
      };
    } else {
      return {
        variant: 'destructive' as const,
        icon: AlertCircle,
        text: 'text-red-600 dark:text-red-400',
        bg: 'bg-red-500 dark:bg-red-400',
        progressBg: 'bg-red-50 dark:bg-red-950/30',
        badgeBg: 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 border-red-200 dark:border-red-800',
        message: 'High credit usage - consider allocating more credits',
        messageIcon: AlertCircle,
      };
    }
  };

  const statusInfo = getStatusInfo(usagePercentage);
  const StatusIcon = statusInfo.icon;
  const MessageIcon = statusInfo.messageIcon;

  // Format numbers with commas
  const formatNumber = (num: number) => {
    return Number.isFinite(num) ? num.toLocaleString('en-US') : '0';
  };

  // Optional: humanize reset date if present
  const resetLabel = useMemo(() => {
    if (!credits.reset_date) return null;
    try {
      const d = new Date(credits.reset_date);
      if (isNaN(d.getTime())) return null;
      return d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
    } catch {
      return null;
    }
  }, [credits.reset_date]);

  return (
    <Card className={cn(
      'w-full border-border/50 shadow-sm hover:shadow-md transition-all duration-300',
      
      className
    )}>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <CardTitle className="text-lg font-semibold flex items-center gap-2">
              <Coins className="h-5 w-5 text-brand-500" />
              Credit Summary
            </CardTitle>
            <CardDescription className="text-sm">
              Organization credit usage and allocation
            </CardDescription>
          </div>
          <div className={cn(
            'p-2.5 rounded-full',
            statusInfo.progressBg
          )}>
            <StatusIcon className={cn('h-5 w-5', statusInfo.text)} />
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="space-y-6">
        {/* Credit Details Grid */}
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {/* Total Credits */}
          <div className="space-y-1.5 p-3 rounded-lg bg-muted/50 dark:bg-gray-900/50 border border-border/50 dark:border-gray-800 hover:border-brand-200 dark:hover:border-brand-800 transition-colors">
            <div className="flex items-center gap-1.5">
              <Activity className="h-3.5 w-3.5 text-muted-foreground dark:text-gray-400" />
              <p className="text-xs text-muted-foreground dark:text-gray-400 font-medium">
                Total
              </p>
            </div>
            <p className="text-2xl font-bold text-brand-600 dark:text-brand-400">
              {formatNumber(credits.total)}
            </p>
          </div>

          {/* Used Credits */}
          <div className="space-y-1.5 p-3 rounded-lg bg-muted/50 dark:bg-gray-900/50 border border-border/50 dark:border-gray-800 hover:border-border dark:hover:border-gray-700 transition-colors">
            <div className="flex items-center gap-1.5">
              <TrendingDown className="h-3.5 w-3.5 text-muted-foreground dark:text-gray-400" />
              <p className="text-xs text-muted-foreground dark:text-gray-400 font-medium">
                Used
              </p>
            </div>
            <p className="text-2xl font-bold text-foreground dark:text-gray-200">
              {formatNumber(credits.used)}
            </p>
          </div>

          {/* Remaining Credits */}
          <div className={cn(
            'space-y-1.5 p-3 rounded-lg border transition-colors',
            'bg-muted/50 dark:bg-gray-900/50',
            usagePercentage < 50 
              ? 'border-emerald-200 dark:border-emerald-800 hover:border-emerald-300 dark:hover:border-emerald-700'
              : usagePercentage < 80
              ? 'border-amber-200 dark:border-amber-800 hover:border-amber-300 dark:hover:border-amber-700'
              : 'border-red-200 dark:border-red-800 hover:border-red-300 dark:hover:border-red-700'
          )}>
            <div className="flex items-center gap-1.5">
              <TrendingUp className={cn('h-3.5 w-3.5', statusInfo.text)} />
              <p className="text-xs text-muted-foreground dark:text-gray-400 font-medium">
                Remaining
              </p>
            </div>
            <p className={cn('text-2xl font-bold dark:text-gray-200', statusInfo.text)}>
              {formatNumber(credits.remaining)}
            </p>
          </div>

          {/* Monthly Limit */}
          <div className="space-y-1.5 p-3 rounded-lg bg-muted/50 dark:bg-gray-900/50 border border-border/50 dark:border-gray-800 hover:border-border dark:hover:border-gray-700 transition-colors">
            <div className="flex items-center gap-1.5">
              <Coins className="h-3.5 w-3.5 text-muted-foreground dark:text-gray-400" />
              <p className="text-xs text-muted-foreground dark:text-gray-400 font-medium">
                Monthly
              </p>
            </div>
            <p className="text-2xl font-bold text-foreground dark:text-gray-200">
              {credits.monthly_limit > 0 
                ? formatNumber(credits.monthly_limit)
                : '∞'}
            </p>
          </div>
        </div>

        {/* Optional reset date */}
        {resetLabel && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <CalendarClock className="h-3.5 w-3.5" />
            <span>Pool resets on {resetLabel}</span>
          </div>
        )}

        {/* Progress Bar */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-muted-foreground">
                Usage
              </span>
              <Badge variant="outline" className={cn('text-xs font-semibold', statusInfo.badgeBg)}>
                {usagePercentage}%
              </Badge>
            </div>
            <span className="text-xs text-muted-foreground">
              {formatNumber(credits.used)} / {formatNumber(credits.total)}
            </span>
          </div>
          
          <div className={cn(
            'relative h-2.5 w-full overflow-hidden rounded-full',
            statusInfo.progressBg,
            'ring-1 ring-border/50'
          )}>
            <div
              className={cn(
                'h-full transition-all duration-700 ease-out rounded-full',
                statusInfo.bg,
                'shadow-sm'
              )}
              style={{ width: `${Math.min(Math.max(usagePercentage, 0), 100)}%` }}
            />
          </div>
        </div>

        {/* Usage Status Message */}
        <div className={cn(
          'flex items-start gap-2.5 p-3 rounded-lg border',
          statusInfo.badgeBg
        )}>
          <MessageIcon className={cn('h-4 w-4 mt-0.5 flex-shrink-0', statusInfo.text)} />
          <p className={cn('text-sm font-medium', statusInfo.text)}>
            {statusInfo.message}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
