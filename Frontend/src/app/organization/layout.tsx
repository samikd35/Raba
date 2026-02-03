"use client";

import { useSidebar } from "@/context/SidebarContext";
import AppHeader from "@/layout/organization/AppHeader";
import AppSidebar from "@/layout/organization/AppSidebar";
import Backdrop from "@/layout/organization/Backdrop";
import React, { Suspense, useEffect, useMemo } from "react";
import { SidebarProvider } from '@/context/SidebarContext';
import { ThemeProvider } from '@/context/ThemeContext';
import { NavigationLoadingProvider } from '@/context/NavigationLoadingContext';
import NavigationLoadingOverlay from '@/components/NavigationLoadingOverlay';
import { useAuthStore } from "@/stores/authStore";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";

function LayoutContentBase({ children }: { children: React.ReactNode }) {
  const { isExpanded, isHovered, isMobileOpen } = useSidebar();
  const { user, isAuthenticated, isInitialized } = useAuthStore();
  const router = useRouter();

  // Memoized class for main content margin based on sidebar state
  // IMPORTANT: Hooks must run on every render; keep this before any early returns
  const mainContentMargin = useMemo(() => {
    if (isMobileOpen) return "ml-0";
    return isExpanded || isHovered ? "lg:ml-[290px]" : "lg:ml-[90px]";
  }, [isMobileOpen, isExpanded, isHovered]);

  // Handle authentication in useEffect, not in render
  useEffect(() => {
    if (!isInitialized) return;

    // Case 1: Not authenticated → send to home (or signin), no extra checks
    if (!isAuthenticated) {
      if (process.env.NODE_ENV === 'development') {
        console.log('OrganizationLayout: Unauthenticated, redirecting to /');
      }
      router.replace('/');
      return;
    }

    // Case 2: Authenticated but missing/invalid organization tenant → send to choose-workspace
    const tenantId = (user as any)?.tenant_id;
    const tenantType = (user as any)?.tenant_type;
    if (!tenantId || tenantType !== 'organization') {
      if (process.env.NODE_ENV === 'development') {
        console.log('OrganizationLayout: Missing/invalid organization tenant, redirecting to /choose-workspace');
      }
      router.replace('/choose-workspace?next=/organization');
      return;
    }
  }, [isInitialized, isAuthenticated, router, user]);

  // Show loading while auth is initializing
  if (!isInitialized) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50 dark:bg-gray-950">
        <div className="w-8 h-8 border-4 border-brand-500 dark:border-brand-400 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-gray-50 dark:bg-gray-950">
      {/* Sidebar and Backdrop */}
      <AppSidebar />
      <Backdrop />
      
      {/* Main Content Area */}
      <div className={`flex-1 transition-all duration-300 ease-in-out ${mainContentMargin} flex flex-col`}>
        {/* Header */}
        <AppHeader />

        {/* Page Content */}
        <main className="flex-1 p-4 overflow-auto bg-white/90 dark:bg-gray-900/90">
          <Suspense fallback={
            <div className="flex items-center justify-center h-64">
              <div className="w-8 h-8 border-4 border-brand-500 dark:border-brand-400 border-t-transparent rounded-full animate-spin"></div>
            </div>
          }>
            {children}
          </Suspense>
        </main>
      </div>
      
      {/* Navigation Loading Overlay */}
      <NavigationLoadingOverlay />
    </div>
  );
}

const LayoutContent = React.memo(LayoutContentBase);

export default function OrganizationLayout({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider>
        <NavigationLoadingProvider>
          <SidebarProvider>
            <LayoutContent>{children}</LayoutContent>
          </SidebarProvider>
        </NavigationLoadingProvider>
    </ThemeProvider>
  );
}