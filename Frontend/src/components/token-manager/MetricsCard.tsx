"use client";

import React from 'react';
import { LucideIcon } from 'lucide-react';

interface MetricsCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  trend?: {
    value: number;
    direction: 'up' | 'down';
  };
  iconColor?: string;
  loading?: boolean;
}

export function MetricsCard({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  iconColor = 'text-brand-500',
  loading = false,
}: MetricsCardProps) {
  if (loading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 animate-pulse">
        <div className="flex items-center justify-between">
          <div className="flex-1 space-y-3">
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-24"></div>
            <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-32"></div>
            <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-20"></div>
          </div>
          <div className="w-12 h-12 bg-gray-200 dark:bg-gray-700 rounded-full"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
            {title}
          </p>
          <p className="mt-2 text-3xl font-semibold text-gray-900 dark:text-white">
            {value}
          </p>
          {subtitle && (
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              {subtitle}
            </p>
          )}
          {trend && (
            <div className={`mt-2 flex items-center text-sm font-medium ${
              trend.direction === 'up' ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
            }`}>
              <span>{trend.direction === 'up' ? '↑' : '↓'} {Math.abs(trend.value)}%</span>
              <span className="ml-1 text-gray-500 dark:text-gray-400">vs last period</span>
            </div>
          )}
        </div>
        <div className={`p-3 rounded-full bg-gray-100 dark:bg-gray-700 ${iconColor}`}>
          <Icon className="w-6 h-6" />
        </div>
      </div>
    </div>
  );
}
