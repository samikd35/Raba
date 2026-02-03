"use client";

import React from 'react';
import { Badge } from "@/components/ui/badge";

// ============================================
// Badge Utility Components
// ============================================

interface BadgeConfig {
  color: string;
  label: string;
}

/**
 * Severity Badge Component
 */
export const SeverityBadge: React.FC<{ severity: string }> = ({ severity }) => {
  const config: Record<string, BadgeConfig> = {
    high: { color: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300", label: "High Severity" },
    medium: { color: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300", label: "Medium Severity" },
    low: { color: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300", label: "Low Severity" }
  };
  const { color, label } = config[severity] || config.medium;
  return <Badge className={color}>{label}</Badge>;
};

/**
 * Confidence Badge Component
 */
export const ConfidenceBadge: React.FC<{ confidence: number }> = ({ confidence }) => {
  const percentage = Math.round(confidence * 100);
  let color = "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300";
  if (percentage >= 80) color = "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300";
  else if (percentage >= 60) color = "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300";
  return <Badge className={color}>{percentage}% Confidence</Badge>;
};

/**
 * Priority Badge Component
 */
export const PriorityBadge: React.FC<{ priority: string }> = ({ priority }) => {
  const config: Record<string, BadgeConfig> = {
    immediate: { color: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300", label: "Immediate" },
    short_term: { color: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300", label: "Short Term" },
    long_term: { color: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300", label: "Long Term" }
  };
  const { color, label } = config[priority] || config.short_term;
  return <Badge className={color}>{label}</Badge>;
};

/**
 * Effort Badge Component
 */
export const EffortBadge: React.FC<{ effort: string }> = ({ effort }) => {
  const config: Record<string, BadgeConfig> = {
    low: { color: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300", label: "Low Effort" },
    medium: { color: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300", label: "Medium Effort" },
    high: { color: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300", label: "High Effort" }
  };
  const { color, label } = config[effort] || config.medium;
  return <Badge variant="outline" className={color}>{label}</Badge>;
};

/**
 * Impact Badge Component
 */
export const ImpactBadge: React.FC<{ impact: string }> = ({ impact }) => {
  const config: Record<string, BadgeConfig> = {
    high: { color: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300", label: "High Impact" },
    medium: { color: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300", label: "Medium Impact" },
    low: { color: "bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-300", label: "Low Impact" }
  };
  const { color, label } = config[impact] || config.medium;
  return <Badge variant="outline" className={color}>{label}</Badge>;
};
