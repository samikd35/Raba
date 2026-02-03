"use client";

import { useSidebar } from "@/context/SidebarContext";
import AppHeader from "@/layout/AppHeader";
import AppSidebar from "@/layout/AppSidebar";
import Backdrop from "@/layout/Backdrop";
import React, { useEffect } from "react";
import { SidebarProvider } from '@/context/SidebarContext';
import { ThemeProvider } from '@/context/ThemeContext';
import { AuthProvider } from '@/components/AuthProvider';
import { NavigationLoadingProvider } from '@/context/NavigationLoadingContext';
import NavigationLoadingOverlay from '@/components/NavigationLoadingOverlay';
import ChatWindow from '@/components/messaging/ChatWindow';
import { usePathname } from 'next/navigation';
import { authService } from '@/services/authService';
import { useAuthStore } from '@/stores/authStore';
import { useRouter } from 'next/navigation';
import { useSeenFeatureVideosStore } from '@/lib/featureVideos/seenStore';




function LayoutContent({ children }: { children: React.ReactNode }) {
  const { isExpanded, isHovered, isMobileOpen } = useSidebar();
  const { token, isInitialized, isAuthenticated } = useAuthStore();
  const pathname = usePathname();
  const router = useRouter();
  const fetchSeenOnce = useSeenFeatureVideosStore((state) => state.fetchSeenOnce);

  useEffect(() => {
    const handleAuth = async () => {
      if (!isInitialized || !isAuthenticated) {
        await authService.logout();
        router.push('/signin');
      }
    };
    handleAuth();
  }, [isInitialized, isAuthenticated, router]);

  useEffect(() => {
    if (isAuthenticated && token) {
      fetchSeenOnce();
    }
  }, [isAuthenticated, token, fetchSeenOnce]);

  // Dynamic class for main content margin based on sidebar state
  const mainContentMargin = isMobileOpen
    ? "ml-0"
    : isExpanded || isHovered
    ? "lg:ml-[290px]"
    : "lg:ml-[90px]";

  return (
    <div className="min-h-screen xl:flex">
      {/* Sidebar and Backdrop */}
      <AppSidebar />
      <Backdrop />
      {/* Main Content Area */}
      <div
        className={`flex-1 transition-all duration-300 ease-in-out ${mainContentMargin}`}
      >
        {/* Header */}
        <AppHeader />
        {/* Page Content */}
        <div className="p-4 mx-auto max-w-(--breakpoint-2xl)">{children}</div>
      </div>
      {/* Navigation Loading Overlay */}
      <NavigationLoadingOverlay />
      {/* Chat Window - Only show on cofounder browse and matches pages */}
      {(pathname?.includes('/cofounder-matching/browse') || pathname?.includes('/cofounder-matching/matches')) && (
        <ChatWindow />
      )}
    </div>
  );
}

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {






  return (
    <div>
      <ThemeProvider>
        <AuthProvider>
          <NavigationLoadingProvider>
            <SidebarProvider>
              <LayoutContent>{children}</LayoutContent>
            </SidebarProvider>
          </NavigationLoadingProvider>
        </AuthProvider>
      </ThemeProvider>
    </div>
  );
}