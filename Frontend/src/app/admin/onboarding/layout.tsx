"use client";

import React from 'react';

/**
 * Special layout for onboarding page that bypasses AdminRouteGuard
 * This allows any authenticated user with a valid invitation token to access onboarding
 * without requiring admin privileges
 */
export default function OnboardingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      {/* No AdminRouteGuard wrapper - allow any authenticated user */}
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        {children}
      </div>
    </>
  );
}
