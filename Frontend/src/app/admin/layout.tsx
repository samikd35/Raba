"use client";

import React from 'react';
import { usePathname } from 'next/navigation';
import { SimpleAdminSidebar } from '@/components/admin/SimpleAdminSidebar';
import { OrganizationOwnerSidebar } from '@/components/admin/OrganizationOwnerSidebar';
import { SimpleAdminHeader } from '@/components/admin/SimpleAdminHeader';
import AdminRouteGuard from '@/components/admin/AdminRouteGuard';

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  
  // Check if we're on an organization-specific route
  // const isOrganizationRoute = pathname.match(/^\/admin\/organizations\/[^\/]+(?:\/|$)/);
  
  // Check if we're on the onboarding route (bypass AdminRouteGuard)
  const isOnboardingRoute = pathname === '/admin/onboarding';
  
  // Choose the appropriate sidebar
  // const SidebarComponent = isOrganizationRoute ? OrganizationOwnerSidebar : SimpleAdminSidebar;

  const SidebarComponent = SimpleAdminSidebar;



  
  // If onboarding route, don't apply AdminRouteGuard
  if (isOnboardingRoute) {
    return (
      <>
        {children}
      </>
    );
  }

  return (
    <>
      <div className="flex min-h-screen w-full">
        <SidebarComponent />
        <div className="flex-1 flex flex-col">
          <SimpleAdminHeader />
          <main className="flex-1 p-6 bg-gray-50 dark:bg-gray-900">
            {children}
          </main>
        </div>
      </div>
    </>
  );
}