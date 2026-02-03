/**
 * Loading States Components
 * Provides reusable loading indicators for various async operations
 */

import React from 'react';
import { Skeleton } from '@/components/ui/skeleton';
import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

/**
 * Generic loading spinner component
 */
export function LoadingSpinner({ 
  size = 'default',
  className 
}: { 
  size?: 'sm' | 'default' | 'lg';
  className?: string;
}) {
  const sizeClasses = {
    sm: 'h-4 w-4',
    default: 'h-6 w-6',
    lg: 'h-8 w-8',
  };

  return (
    <Loader2 
      className={cn('animate-spin', sizeClasses[size], className)} 
    />
  );
}

/**
 * Loading spinner with text
 */
export function LoadingSpinnerWithText({ 
  text = 'Loading...',
  size = 'default',
  className 
}: { 
  text?: string;
  size?: 'sm' | 'default' | 'lg';
  className?: string;
}) {
  return (
    <div className={cn('flex items-center gap-2', className)}>
      <LoadingSpinner size={size} />
      <span className="text-sm text-muted-foreground">{text}</span>
    </div>
  );
}

/**
 * Full page loading overlay
 */
export function LoadingOverlay({ 
  text = 'Loading...',
  className 
}: { 
  text?: string;
  className?: string;
}) {
  return (
    <div className={cn(
      'fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm',
      className
    )}>
      <div className="flex flex-col items-center gap-4">
        <LoadingSpinner size="lg" />
        <p className="text-lg font-medium">{text}</p>
      </div>
    </div>
  );
}

/**
 * Skeleton loader for team metrics cards
 */
export function TeamMetricsCardSkeleton() {
  return (
    <div className="rounded-lg border bg-card p-6 space-y-3">
      <Skeleton className="h-4 w-24" />
      <Skeleton className="h-8 w-32" />
      <Skeleton className="h-3 w-full" />
    </div>
  );
}

/**
 * Skeleton loader for team member cards
 */
export function TeamMemberCardSkeleton() {
  return (
    <div className="rounded-lg border bg-card p-4 space-y-3">
      <div className="flex items-center gap-3">
        <Skeleton className="h-10 w-10 rounded-full" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-3 w-48" />
        </div>
      </div>
      <div className="flex items-center justify-between pt-2">
        <Skeleton className="h-3 w-24" />
        <Skeleton className="h-8 w-20" />
      </div>
    </div>
  );
}

/**
 * Skeleton loader for credit request history table
 */
export function CreditRequestTableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-3">
      {/* Table header */}
      <div className="flex items-center gap-4 border-b pb-2">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-4 w-20" />
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-4 w-32" />
      </div>
      
      {/* Table rows */}
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex items-center gap-4 py-2">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-4 w-20" />
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-4 w-32" />
        </div>
      ))}
    </div>
  );
}

/**
 * Skeleton loader for dashboard page
 */
export function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="space-y-2">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-4 w-96" />
      </div>

      {/* Metrics cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <TeamMetricsCardSkeleton />
        <TeamMetricsCardSkeleton />
        <TeamMetricsCardSkeleton />
        <TeamMetricsCardSkeleton />
      </div>

      {/* Content sections */}
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="space-y-4">
          <Skeleton className="h-6 w-48" />
          <div className="space-y-3">
            <TeamMemberCardSkeleton />
            <TeamMemberCardSkeleton />
            <TeamMemberCardSkeleton />
          </div>
        </div>
        <div className="space-y-4">
          <Skeleton className="h-6 w-48" />
          <CreditRequestTableSkeleton rows={3} />
        </div>
      </div>
    </div>
  );
}

/**
 * Skeleton loader for form
 */
export function FormSkeleton({ fields = 5 }: { fields?: number }) {
  return (
    <div className="space-y-4">
      {Array.from({ length: fields }).map((_, i) => (
        <div key={i} className="space-y-2">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-10 w-full" />
        </div>
      ))}
      <Skeleton className="h-10 w-32" />
    </div>
  );
}

/**
 * Button loading state
 */
export function ButtonLoading({ 
  text = 'Loading...',
  className 
}: { 
  text?: string;
  className?: string;
}) {
  return (
    <span className={cn('flex items-center gap-2', className)}>
      <LoadingSpinner size="sm" />
      {text}
    </span>
  );
}

/**
 * Inline loading indicator for actions
 */
export function InlineLoading({ 
  text,
  className 
}: { 
  text?: string;
  className?: string;
}) {
  return (
    <div className={cn('flex items-center gap-2 text-sm text-muted-foreground', className)}>
      <LoadingSpinner size="sm" />
      {text && <span>{text}</span>}
    </div>
  );
}

/**
 * Progress indicator for multi-step operations
 */
export function ProgressIndicator({ 
  currentStep,
  totalSteps,
  stepLabels,
  className 
}: { 
  currentStep: number;
  totalSteps: number;
  stepLabels?: string[];
  className?: string;
}) {
  const progress = (currentStep / totalSteps) * 100;

  return (
    <div className={cn('space-y-2', className)}>
      {/* Progress bar */}
      <div className="relative h-2 w-full overflow-hidden rounded-full bg-secondary">
        <div 
          className="h-full bg-primary transition-all duration-300 ease-in-out"
          style={{ width: `${progress}%` }}
        />
      </div>
      
      {/* Step labels */}
      {stepLabels && (
        <div className="flex justify-between text-xs text-muted-foreground">
          {stepLabels.map((label, i) => (
            <span 
              key={i}
              className={cn(
                'transition-colors',
                i < currentStep && 'text-primary font-medium',
                i === currentStep && 'text-foreground font-medium'
              )}
            >
              {label}
            </span>
          ))}
        </div>
      )}
      
      {/* Step counter */}
      <p className="text-center text-sm text-muted-foreground">
        Step {currentStep} of {totalSteps}
      </p>
    </div>
  );
}

/**
 * Empty state with loading option
 */
export function EmptyState({ 
  title,
  description,
  isLoading = false,
  icon: Icon,
  action,
  className 
}: { 
  title: string;
  description?: string;
  isLoading?: boolean;
  icon?: React.ComponentType<{ className?: string }>;
  action?: React.ReactNode;
  className?: string;
}) {
  if (isLoading) {
    return (
      <div className={cn('flex flex-col items-center justify-center py-12', className)}>
        <LoadingSpinner size="lg" />
        <p className="mt-4 text-sm text-muted-foreground">Loading...</p>
      </div>
    );
  }

  return (
    <div className={cn('flex flex-col items-center justify-center py-12 text-center', className)}>
      {Icon && <Icon className="h-12 w-12 text-muted-foreground/50 mb-4" />}
      <h3 className="text-lg font-semibold">{title}</h3>
      {description && (
        <p className="mt-2 text-sm text-muted-foreground max-w-md">{description}</p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

/**
 * Card loading state
 */
export function CardLoading({ 
  title,
  className 
}: { 
  title?: string;
  className?: string;
}) {
  return (
    <div className={cn('rounded-lg border bg-card p-6', className)}>
      {title && <h3 className="text-sm font-medium mb-4">{title}</h3>}
      <div className="space-y-3">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-4 w-5/6" />
      </div>
    </div>
  );
}

/**
 * List loading state
 */
export function ListLoading({ 
  items = 3,
  className 
}: { 
  items?: number;
  className?: string;
}) {
  return (
    <div className={cn('space-y-3', className)}>
      {Array.from({ length: items }).map((_, i) => (
        <div key={i} className="flex items-center gap-3">
          <Skeleton className="h-10 w-10 rounded-full" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-3 w-1/2" />
          </div>
        </div>
      ))}
    </div>
  );
}
