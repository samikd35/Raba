"use client";

import { useSidebar } from "@/context/SidebarContext";
import AppHeader from "@/layout/team/AppHeader";
import AppSidebar from "@/layout/team/AppSidebar";
import Backdrop from "@/layout/Backdrop";
import React, { useEffect, useState } from "react";
import { SidebarProvider } from '@/context/SidebarContext';
import { ThemeProvider } from '@/context/ThemeContext';
import { AuthProvider } from '@/components/AuthProvider';
import { NavigationLoadingProvider } from '@/context/NavigationLoadingContext';
import NavigationLoadingOverlay from '@/components/NavigationLoadingOverlay';
import { authService } from '@/services/authService';
import { useAuthStore } from '@/stores/authStore';
import { useTeamStore } from '@/stores/teamStore';
import { useRouter } from 'next/navigation';
import { Loader2 } from 'lucide-react';
import { useSeenFeatureVideosStore } from '@/lib/featureVideos/seenStore';

function LayoutContent({ children }: { children: React.ReactNode }) {
  const { isExpanded, isHovered, isMobileOpen } = useSidebar();
  const { token, isInitialized, isAuthenticated, user } = useAuthStore();
  const { currentTeam, fetchTeamDetails, isLoading: teamLoading } = useTeamStore();
  const router = useRouter();
  const [isVerifyingTeam, setIsVerifyingTeam] = useState(false);
  const fetchSeenOnce = useSeenFeatureVideosStore((state) => state.fetchSeenOnce);
  
  const expectedTeamId = user?.tenant_id;

  // Fetch seen feature videos once on app load (non-blocking)
  useEffect(() => {
    if (isAuthenticated && token) {
      fetchSeenOnce();
    }
  }, [isAuthenticated, token, fetchSeenOnce]);

  // Auth check
  useEffect(() => {
    const handleAuth = async () => {
      if (!isInitialized || !isAuthenticated) {
        await authService.logout();
        router.push('/signin');
      }
    };
    handleAuth();
  }, [isInitialized, isAuthenticated, router]);
  
  // CRITICAL: Verify cached team matches the expected tenant_id
  // This prevents showing wrong team data when switching workspaces
  useEffect(() => {
    const verifyTeamData = async () => {
      if (!isInitialized || !isAuthenticated || !expectedTeamId || !token) {
        return;
      }
      
      // Check if cached team matches expected team ID
      const teamIdMismatch = currentTeam && currentTeam.id !== expectedTeamId;
      
      if (!currentTeam || teamIdMismatch) {
        if (process.env.NODE_ENV === 'development') {
          console.log('TeamWorkspaceLayout: Team verification required', {
            hasCachedTeam: !!currentTeam,
            cachedTeamId: currentTeam?.id,
            expectedTeamId,
            mismatch: teamIdMismatch,
          });
        }
        
        setIsVerifyingTeam(true);
        try {
          await fetchTeamDetails(expectedTeamId);
        } catch (error) {
          if (process.env.NODE_ENV === 'development') {
            console.error('TeamWorkspaceLayout: Failed to fetch team details', error);
          }
        } finally {
          setIsVerifyingTeam(false);
        }
      }
    };
    
    verifyTeamData();
  }, [isInitialized, isAuthenticated, expectedTeamId, currentTeam, fetchTeamDetails, token]);

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