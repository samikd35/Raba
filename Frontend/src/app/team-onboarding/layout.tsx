"use client";

import React from 'react';

/**
 * Special layout for team onboarding page that bypasses AdminRouteGuard
 * This allows team leaders with valid invitation tokens to create teams
 * without requiring system-wide admin privileges
 */
export default function TeamOnboardingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      {/* No AdminRouteGuard wrapper - allow team leaders */}
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        {children}
      </div>
    </>
  );
}
