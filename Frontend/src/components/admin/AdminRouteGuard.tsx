"use client";

import React, { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore, useCurrentWorkspaceInfo, useAuthStatus } from '@/stores/authStore';
import { isAdminUser } from '@/lib/adminRouteGuard';
import { canAccessRoute, RequiredRole, getRedirectPathBasedOnRole } from '@/lib/routeUtils';
import { toast } from "react-hot-toast";

interface AdminRouteGuardProps {
  children: React.ReactNode;
  requiredRole?: RequiredRole; // 'any' means any admin role
}

export default function AdminRouteGuard({
  children,
  requiredRole = 'any'
}: AdminRouteGuardProps) {
  const router = useRouter();
  
  // Use the new auth store hooks
  const {
    isAuthenticated: storeIsAuthenticated,
    isLoading,
    isInitialized,
    user,
    hasRole,
  } = useAuthStore();

  // Use the new workspace info hook
  const {
    currentWorkspace,
    currentWorkspaceType,
    currentWorkspaceId,
    currentWorkspaceRole,
    currentWorkspaceTenantId,
    hasWorkspace
  } = useCurrentWorkspaceInfo();

  // Use the new auth status hook for computed authentication state
  const { isAuthenticated, isTokenValid } = useAuthStatus();

  useEffect(() => {
    // Wait for auth store to initialize to avoid premature redirects
    if (isLoading || !isInitialized) {
      return;
    }

    // Check authentication status using computed auth status
    if (!isAuthenticated || !isTokenValid) {
      console.log('AdminRouteGuard: Authentication check failed', {
        isAuthenticated,
        isTokenValid,
        storeIsAuthenticated
      });
      toast.error('Authentication required. Please sign in.');
      router.push('/signin?redirect=/admin');
      return;
    }

    // Check if user has a workspace context (required for admin routes)
    if (!hasWorkspace || !currentWorkspaceId) {
      console.log('AdminRouteGuard: Workspace context missing', {
        hasWorkspace,
        currentWorkspaceId,
        currentWorkspace,
        currentWorkspaceType
      });
      toast.error('Workspace context required. Please select a workspace.');
      router.push('/choose-workspace');
      return;
    }

    // Enhanced role checking: combine user roles with workspace role for admin access
    const userRoles = user?.roles || [];
    const workspaceRoles = [currentWorkspaceRole].filter(Boolean); // Only if workspace role exists
    const allRoles = [...userRoles, ...workspaceRoles];

    // For organization contexts, prioritize workspace role (e.g., admin in org)
    const effectiveRoles = currentWorkspaceType === 'organization'
      ? (workspaceRoles.length > 0 ? workspaceRoles : userRoles)
      : userRoles;

    const hasRequiredRole = canAccessRoute(effectiveRoles, requiredRole, user || undefined);

    // Debug logging with workspace context
    console.log('AdminRouteGuard Debug:', {
      user: user ? { id: user.id, email: user.email, roles: user.roles } : null,
      userRoles,
      workspace: { 
        currentWorkspace, 
        currentWorkspaceType, 
        currentWorkspaceId, 
        currentWorkspaceRole, 
        currentWorkspaceTenantId 
      },
      effectiveRoles,
      requiredRole,
      hasRequiredRole,
      hasWorkspace,
      authStatus: { isAuthenticated, isTokenValid }
    });

    if (!hasRequiredRole) {
      toast.error('Access denied. Insufficient privileges.');
      // Redirect based on roles and workspace context
      const redirectPath = getRedirectPathBasedOnRole(effectiveRoles, user || undefined);
      console.log('Redirecting to:', redirectPath);
      router.push(redirectPath);
    }
  }, [
    isAuthenticated,
    isTokenValid,
    isLoading,
    isInitialized,
    user,
    currentWorkspace,
    currentWorkspaceType,
    currentWorkspaceId,
    currentWorkspaceRole,
    currentWorkspaceTenantId,
    hasWorkspace,
    router,
    requiredRole
  ]);

  // Show loading state while checking auth status
  if (isLoading || !isInitialized) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-500"></div>
        <span className="ml-3 text-gray-600 dark:text-gray-400">Checking permissions...</span>
      </div>
    );
  }

  // Check authentication
  if (!isAuthenticated || !isTokenValid) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="text-center p-6 bg-white dark:bg-gray-800 rounded-lg shadow-lg max-w-md">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-2">Authentication Required</h2>
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            Please sign in to access this page.
          </p>
          <button
            onClick={() => router.push('/signin')}
            className="px-4 py-2 bg-brand-500 text-white rounded-lg hover:bg-brand-600 transition-colors"
          >
            Sign In
          </button>
        </div>
      </div>
    );
  }

  // Check workspace context
  if (!hasWorkspace || !currentWorkspaceId) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="text-center p-6 bg-white dark:bg-gray-800 rounded-lg shadow-lg max-w-md">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-2">Workspace Required</h2>
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            Please select a workspace to access admin features.
          </p>
          <button
            onClick={() => router.push('/choose-workspace')}
            className="px-4 py-2 bg-brand-500 text-white rounded-lg hover:bg-brand-600 transition-colors"
          >
            Select Workspace
          </button>
        </div>
      </div>
    );
  }

  // Enhanced role check for render
  const userRoles = user?.roles || [];
  const workspaceRoles = [currentWorkspaceRole].filter(Boolean);
  const effectiveRoles = currentWorkspaceType === 'organization'
    ? (workspaceRoles.length > 0 ? workspaceRoles : userRoles)
    : userRoles;
  const hasRequiredRole = canAccessRoute(effectiveRoles, requiredRole, user || undefined);

  // Debug logging for render check
  console.log('AdminRouteGuard Render Check:', {
    user: user ? { id: user.id, email: user.email } : null,
    userRoles,
    workspace: { 
      currentWorkspace, 
      currentWorkspaceType, 
      currentWorkspaceId, 
      currentWorkspaceRole 
    },
    effectiveRoles,
    requiredRole,
    hasRequiredRole,
    hasWorkspace
  });

  if (!hasRequiredRole) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="text-center p-6 bg-white dark:bg-gray-800 rounded-lg shadow-lg max-w-md">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-2">Access Denied</h2>
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            You don't have the required privileges in the <strong>{currentWorkspace}</strong> workspace.
            {currentWorkspaceRole && (
              <span className="block mt-2 text-sm">
                Your role: <strong>{currentWorkspaceRole}</strong>
              </span>
            )}
          </p>
          <div className="flex gap-3 justify-center">
            <button
              onClick={() => {
                const redirectPath = getRedirectPathBasedOnRole(effectiveRoles, user || undefined);
                router.push(redirectPath);
              }}
              className="px-4 py-2 bg-brand-500 text-white rounded-lg hover:bg-brand-600 transition-colors"
            >
              Continue
            </button>
            <button
              onClick={() => router.push('/choose-workspace')}
              className="px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 transition-colors"
            >
              Switch Workspace
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Render debug info in development
  if (process.env.NODE_ENV === 'development') {
    console.log('AdminRouteGuard: Access granted', {
      user: user?.email,
      workspace: currentWorkspace,
      workspaceType: currentWorkspaceType,
      effectiveRoles,
      requiredRole
    });
  }

  return <>{children}</>;
}