"use client";

import React from "react";
import QuickActions from "@/components/workspace/QuickActions";
import { useUser, useIsAuthenticated, useIsLoading } from '@/stores/authStore';
import { DashboardProjects } from "@/components/DashboardProjects";

// Force dynamic rendering to prevent build errors
export const dynamic = 'force-dynamic';

export default function Ecommerce() {
  const user = useUser();
  const isAuthenticated = useIsAuthenticated();
  const isLoading = useIsLoading();



  // Get display name with fallbacks
  const getDisplayName = () => {
    console.log('getDisplayName called:', { isLoading, isAuthenticated, user: user?.full_name });

    // Show loading state while user data is being fetched
    if (isLoading) {
      return '...'; // Loading indicator
    }

    // Check if user exists and has authentication
    if (!user || !isAuthenticated) {
      console.log('No user or not authenticated');
      return 'there'; // Fallback when not authenticated
    }

    // Check if full_name exists and is not empty
    if (user.full_name && user.full_name.trim()) {
      const firstName = user.full_name.trim().split(' ')[0];
      console.log('Using full_name:', firstName);
      return firstName || 'there'; // Fallback if first name is empty
    }

    // Try to get full name from localStorage as fallback
    try {
      const storedFullName = localStorage.getItem('userFullName');
      if (storedFullName && storedFullName.trim()) {
        const firstName = storedFullName.trim().split(' ')[0];
        console.log('Using stored full_name from localStorage:', firstName);
        return firstName || 'there';
      }
    } catch (error) {
      console.warn('Failed to access localStorage:', error);
    }

    console.log('Using final fallback');
    return 'there'; // Final fallback
  };

  return (
    <div className="flex flex-col gap-4 md:gap-6">
      <div className="flex flex-1 flex-col">
        <div className="@container/main flex flex-1 flex-col gap-4">
          <div className="flex flex-col gap-4">
            <div>
              <h2 className="font-semibold text-xl text-brand-500 dark:text-white">
                Hey, {getDisplayName()}
              </h2>
              <p className="text-gray-500">Let's get some work done</p>

            </div>
            {/* <SectionCards /> */}
            <QuickActions />
          </div>
          <DashboardProjects />

        </div>

      </div>
    </div>
  );
}
