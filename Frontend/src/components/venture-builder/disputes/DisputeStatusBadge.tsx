'use client';

import { AlertTriangle, Clock, CheckCircle } from 'lucide-react';
import type { DisputeStatus } from '@/types/ventureBuilder';

interface DisputeStatusBadgeProps {
  status: DisputeStatus;
  size?: 'sm' | 'md';
}

const STATUS_CONFIG: Record<DisputeStatus, { label: string; className: string; icon: typeof AlertTriangle }> = {
  submitted: {
    label: 'Submitted',
    className: 'bg-warning-100 dark:bg-warning-900/30 text-warning-700 dark:text-warning-300 border-warning-200 dark:border-warning-700',
    icon: AlertTriangle,
  },
  under_review: {
    label: 'Under Review',
    className: 'bg-brand-100 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300 border-brand-200 dark:border-brand-700',
    icon: Clock,
  },
  resolved: {
    label: 'Resolved',
    className: 'bg-success-100 dark:bg-success-900/30 text-success-700 dark:text-success-300 border-success-200 dark:border-success-700',
    icon: CheckCircle,
  },
};

export default function DisputeStatusBadge({ status, size = 'md' }: DisputeStatusBadgeProps) {
  const config = STATUS_CONFIG[status];
  const Icon = config.icon;

  const sizeClasses = size === 'sm'
    ? 'px-2 py-0.5 text-xs gap-1'
    : 'px-3 py-1 text-xs gap-1.5';

  const iconSize = size === 'sm' ? 'w-3 h-3' : 'w-3.5 h-3.5';

  return (
    <span className={`inline-flex items-center font-medium rounded-full border ${sizeClasses} ${config.className}`}>
      <Icon className={iconSize} />
      {config.label}
    </span>
  );
}
